"""
VANTA Terminal — Meta-Labeling Candidate Dataset Builder (Phase 5D.1)
=====================================================================
Extracts deterministic candidate trade records from the frozen primary strategy
(STRAT-B-01 Donchian Breakout 1H) and binds point-in-time features and canonical
trade outcomes into binary meta-labels (y in {0, 1}).

Key Invariants:
1. Strict Identity: Deterministic, collision-free candidate_id based on stable attributes.
2. Direction Preservation: LONG and SHORT candidate directions are strictly preserved.
3. Zero Feature Lookahead: feature_max_timestamp <= signal_timestamp < planned_entry_timestamp.
4. Canonical Outcome Grounding: Label 1 denotes strictly positive realized net PnL (> $0.00).
   Label 0 denotes zero or negative realized net PnL (<= $0.00).
5. Unresolved Integrity: Unresolved/missing outcomes remain None; never silently defaulted to 0.
6. Holdout Quarantine: open_time >= 2026-04-26T00:00:00Z (1777161600000) is strictly blocked.
7. Purge/Embargo Isolation: Candidates whose trade lifecycles cross partition boundaries are purged.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
import hashlib
import numpy as np
import pandas as pd

from backend.backtest.schemas import PositionSide, TradeRecord
from backend.backtest.events import BarEvent, SignalEvent
from backend.strategy.configurations import StrategyBConfig
from backend.strategy.candidates import DonchianBreakoutStrategy
from backend.ml.features import FeaturePipeline, REGISTERED_FEATURE_NAMES
from backend.ml.walk_forward import WalkForwardFold, WARMUP_BARS
from backend.data.loader import HOLDOUT_CUTOFF_MS, QuarantinedHoldoutViolationError


class DataLeakageError(ValueError):
    """Raised when feature or outcome timestamps violate point-in-time invariants."""
    pass


class CandidateOrderingError(ValueError):
    """Raised when candidate timestamps violate causal ordering."""
    pass


class DuplicateCandidateError(ValueError):
    """Raised when duplicate candidate records are detected."""
    pass


@dataclass
class CandidateTradeRecord:
    """
    Immutable specification of a single candidate trade opportunity emitted
    by the primary breakout strategy.
    """
    candidate_id: str                   # Deterministic SHA-256 hash digest
    symbol: str                         # Symbol name (e.g. 'BTCUSDT')
    signal_timestamp: int               # Bar t Open time in epoch ms (T_open,t)
    signal_close_timestamp: int         # Bar t Close time in epoch ms (T_close,t)
    direction: str                      # 'LONG' or 'SHORT'
    signal_reference_price: float       # Close price C_t of signal bar
    planned_entry_timestamp: int        # Bar t+1 Open time in epoch ms (T_open,t+1)
    planned_entry_price: float          # Anticipated entry price at O_{t+1} with slippage
    stop_price: float                   # Fixed stop loss price from signal
    target_price: Optional[float]       # None for Strategy B (uses midline trailing exit)
    expiry_timestamp: int               # Expiry timestamp (48 bars after entry)
    fold_id: int                        # Walk-forward fold identifier
    features: Optional[Dict[str, float]] = None  # 21 point-in-time features at signal_timestamp
    label_resolution_timestamp: Optional[int] = None  # Actual exit timestamp from execution
    realized_net_pnl: Optional[float] = None          # Realized net PnL from canonical execution
    exit_reason: Optional[str] = None                 # Exit reason (STOP_LOSS, MIDLINE, EXPIRY, etc.)
    meta_label: Optional[int] = None                  # 1 if net PnL > 0, 0 if net PnL <= 0, None if unresolved

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_candidate_id(fold_id: int, symbol: str, signal_timestamp: int, direction: str) -> str:
    """
    Generates a deterministic 16-character hexadecimal candidate ID.
    """
    raw_key = f"{fold_id}_{symbol}_{signal_timestamp}_{direction}"
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
    return f"CAND_{digest}"


class MetaCandidateExtractor:
    """
    Extracts candidate trades from raw OHLCV series using the frozen primary strategy.
    """

    def __init__(self, slippage_bps: float = 2.0):
        self.slippage_rate = slippage_bps / 10000.0

    def extract_candidates_from_bars(
        self,
        symbol: str,
        df_ohlcv: pd.DataFrame,
        config: StrategyBConfig,
        fold_id: int,
        feature_df: Optional[pd.DataFrame] = None
    ) -> List[CandidateTradeRecord]:
        """
        Extracts candidate trade records sequentially using DonchianBreakoutStrategy.
        """
        if df_ohlcv.empty:
            return []

        # Validate required columns
        for col in ["open_time", "open", "high", "low", "close", "volume"]:
            if col not in df_ohlcv.columns:
                raise ValueError(f"Missing required column in df_ohlcv: {col}")

        # Active holdout guard
        max_time = int(df_ohlcv["open_time"].max())
        if max_time >= HOLDOUT_CUTOFF_MS:
            raise QuarantinedHoldoutViolationError(
                f"Quarantine violation: Candle open_time {max_time} reaches or exceeds "
                f"holdout cutoff {HOLDOUT_CUTOFF_MS} (2026-04-26T00:00:00Z)."
            )

        # Pre-index features by open_time if provided
        feat_by_time: Dict[int, Dict[str, float]] = {}
        if feature_df is not None:
            if "open_time" not in feature_df.columns:
                raise ValueError("feature_df must contain 'open_time' column for alignment.")
            for col in REGISTERED_FEATURE_NAMES:
                if col not in feature_df.columns:
                    raise ValueError(f"Missing registered feature in feature_df: {col}")

            feat_records = feature_df.set_index("open_time")[REGISTERED_FEATURE_NAMES].to_dict(orient="index")
            feat_by_time = {int(k): v for k, v in feat_records.items()}

        candidates: List[CandidateTradeRecord] = []
        seen_ids = set()

        strat = DonchianBreakoutStrategy(config)
        from backend.backtest.position import PositionTracker
        dummy_pos = PositionTracker(symbol=symbol)

        n = len(df_ohlcv)
        for i in range(n):
            row = df_ohlcv.iloc[i]
            open_time = int(row["open_time"])
            close_time = int(row["close_time"]) if "close_time" in row else open_time + 3599999
            o = float(row["open"])
            h = float(row["high"])
            l = float(row["low"])
            c = float(row["close"])
            v = float(row["volume"])

            bar = BarEvent(
                timestamp_ms=open_time,
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
                close_time_ms=close_time,
                bar_index=i
            )

            # Evaluate strategy on bar
            sig = strat.on_bar(bar, dummy_pos)

            if sig is not None and sig.direction != PositionSide.FLAT:
                # Causal entry timing: Next bar open is at close_time + 1 ms
                planned_entry_time = close_time + 1
                if i + 1 < n:
                    next_open = float(df_ohlcv.iloc[i + 1]["open"])
                else:
                    next_open = c  # Fallback for terminal bar

                dir_str = "LONG" if sig.direction == PositionSide.LONG else "SHORT"
                cid = generate_candidate_id(fold_id, symbol, open_time, dir_str)

                if cid in seen_ids:
                    raise DuplicateCandidateError(f"Duplicate candidate detected: {cid}")
                seen_ids.add(cid)

                # Direction-specific planned entry price with adverse slippage
                if sig.direction == PositionSide.LONG:
                    planned_entry_p = next_open * (1.0 + self.slippage_rate)
                else:
                    planned_entry_p = next_open * (1.0 - self.slippage_rate)

                # Expiry after 48 bars (48 hours = 172,800,000 ms)
                expiry_time = planned_entry_time + (48 * 3600 * 1000)

                # Validate causal timestamp ordering
                if not (open_time < planned_entry_time <= expiry_time):
                    raise CandidateOrderingError(
                        f"Invalid timestamp sequence for candidate {cid}: "
                        f"signal={open_time}, entry={planned_entry_time}, expiry={expiry_time}"
                    )

                # Point-in-time features
                feats = None
                if feat_by_time:
                    if open_time not in feat_by_time:
                        raise DataLeakageError(
                            f"Missing feature vector for candidate {cid} at signal timestamp {open_time}."
                        )
                    feats = feat_by_time[open_time]

                cand = CandidateTradeRecord(
                    candidate_id=cid,
                    symbol=symbol,
                    signal_timestamp=open_time,
                    signal_close_timestamp=close_time,
                    direction=dir_str,
                    signal_reference_price=c,
                    planned_entry_timestamp=planned_entry_time,
                    planned_entry_price=round(planned_entry_p, 4),
                    stop_price=float(sig.stop_loss) if sig.stop_loss is not None else 0.0,
                    target_price=None,
                    expiry_timestamp=expiry_time,
                    fold_id=fold_id,
                    features=feats,
                    label_resolution_timestamp=None,
                    realized_net_pnl=None,
                    exit_reason=None,
                    meta_label=None
                )
                candidates.append(cand)

        return candidates


def bind_trade_outcomes(
    candidates: List[CandidateTradeRecord],
    trades: List[TradeRecord]
) -> List[CandidateTradeRecord]:
    """
    Binds canonical realized trade outcomes to candidate trade records.
    
    Invariants:
    - Matches candidate to trade by (symbol, entry_time_ms, direction).
    - Realized Net PnL > $0.00 -> meta_label = 1
    - Realized Net PnL <= $0.00 -> meta_label = 0
    - Missing / Unmatched outcomes -> meta_label = None (NEVER silently converted to 0)
    """
    # Index trades by (symbol, entry_time_ms, side)
    trade_map: Dict[Tuple[str, int, str], TradeRecord] = {}
    for t in trades:
        side_str = "LONG" if t.side == PositionSide.LONG else "SHORT"
        key = (t.symbol, t.entry_time_ms, side_str)
        trade_map[key] = t

    updated: List[CandidateTradeRecord] = []
    for c in candidates:
        key = (c.symbol, c.planned_entry_timestamp, c.direction)
        trade = trade_map.get(key)

        if trade is not None:
            net_pnl = float(trade.net_pnl)
            # Binary label: 1 if strictly positive net PnL, else 0
            label = 1 if net_pnl > 0.0 else 0
            exit_reason_str = (
                trade.exit_reason.value if hasattr(trade.exit_reason, "value") else str(trade.exit_reason)
            )

            # Ensure label resolution timestamp >= entry timestamp
            if trade.exit_time_ms < c.planned_entry_timestamp:
                raise CandidateOrderingError(
                    f"Trade exit time {trade.exit_time_ms} precedes planned entry {c.planned_entry_timestamp}."
                )

            rec = CandidateTradeRecord(
                candidate_id=c.candidate_id,
                symbol=c.symbol,
                signal_timestamp=c.signal_timestamp,
                signal_close_timestamp=c.signal_close_timestamp,
                direction=c.direction,
                signal_reference_price=c.signal_reference_price,
                planned_entry_timestamp=c.planned_entry_timestamp,
                planned_entry_price=c.planned_entry_price,
                stop_price=c.stop_price,
                target_price=c.target_price,
                expiry_timestamp=c.expiry_timestamp,
                fold_id=c.fold_id,
                features=c.features,
                label_resolution_timestamp=trade.exit_time_ms,
                realized_net_pnl=round(net_pnl, 4),
                exit_reason=exit_reason_str,
                meta_label=label
            )
        else:
            # Unresolved or missing outcome remains None
            rec = CandidateTradeRecord(
                candidate_id=c.candidate_id,
                symbol=c.symbol,
                signal_timestamp=c.signal_timestamp,
                signal_close_timestamp=c.signal_close_timestamp,
                direction=c.direction,
                signal_reference_price=c.signal_reference_price,
                planned_entry_timestamp=c.planned_entry_timestamp,
                planned_entry_price=c.planned_entry_price,
                stop_price=c.stop_price,
                target_price=c.target_price,
                expiry_timestamp=c.expiry_timestamp,
                fold_id=c.fold_id,
                features=c.features,
                label_resolution_timestamp=None,
                realized_net_pnl=None,
                exit_reason=None,
                meta_label=None
            )
        updated.append(rec)

    return updated


def filter_partition_candidates(
    candidates: List[CandidateTradeRecord],
    partition: str,
    fold: WalkForwardFold,
    purge_boundary_overlap: bool = True
) -> List[CandidateTradeRecord]:
    """
    Filters candidates by walk-forward partition and enforces zero label leakage across boundaries.
    
    Rules:
    - IS: signal_timestamp in [fold.is_start_ms, fold.is_end_ms).
          If purge_boundary_overlap is True, purges candidates whose outcome resolves after fold.is_end_ms
          or whose outcome is unresolved.
    - OOS: signal_timestamp in [fold.oos_start_ms, fold.oos_end_ms).
    """
    part_upper = partition.upper()
    filtered: List[CandidateTradeRecord] = []

    for c in candidates:
        # Quarantine enforcement
        if c.signal_timestamp >= HOLDOUT_CUTOFF_MS:
            raise QuarantinedHoldoutViolationError(
                f"Candidate {c.candidate_id} signal timestamp {c.signal_timestamp} violates holdout cutoff."
            )

        if part_upper == "IS":
            if fold.is_start_ms <= c.signal_timestamp < fold.is_end_ms:
                if purge_boundary_overlap:
                    # Drop unlabelled or boundary-crossing trades
                    if c.label_resolution_timestamp is None:
                        continue
                    if c.label_resolution_timestamp > fold.is_end_ms:
                        continue
                filtered.append(c)

        elif part_upper == "OOS":
            if fold.oos_start_ms <= c.signal_timestamp < fold.oos_end_ms:
                filtered.append(c)
        else:
            raise ValueError(f"Unsupported partition '{partition}'. Must be 'IS' or 'OOS'.")

    return filtered


def candidates_to_matrices(
    candidates: List[CandidateTradeRecord]
) -> Tuple[np.ndarray, np.ndarray, List[CandidateTradeRecord]]:
    """
    Converts labelled candidates into feature matrix X and binary target vector y.
    Only includes candidates with valid features and non-None meta_labels.
    """
    valid_cands: List[CandidateTradeRecord] = []
    x_rows = []
    y_vals = []

    for c in candidates:
        if c.features is None or c.meta_label is None:
            continue

        # Extract features in exact registered order
        row = []
        has_nan = False
        for fname in REGISTERED_FEATURE_NAMES:
            val = c.features.get(fname)
            if val is None or np.isnan(val):
                has_nan = True
                break
            row.append(float(val))

        if not has_nan:
            x_rows.append(row)
            y_vals.append(int(c.meta_label))
            valid_cands.append(c)

    if not x_rows:
        return (
            np.empty((0, len(REGISTERED_FEATURE_NAMES)), dtype=np.float64),
            np.empty(0, dtype=int),
            []
        )

    X = np.array(x_rows, dtype=np.float64)
    y = np.array(y_vals, dtype=int)
    return X, y, valid_cands
