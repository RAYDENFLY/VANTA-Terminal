"""
VANTA Terminal — Machine Learning Dataset Builder & Partition Preprocessor
===========================================================================
Prepares point-in-time training and evaluation datasets across the 10 qualified pairs:
1. Loads 1H raw Parquet datasets with strict holdout quarantine enforcement.
2. Slices In-Sample (IS) and Out-of-Sample (OOS) partitions with 150-bar warmup buffers.
3. Computes the 21 pre-registered features via FeaturePipeline.
4. Generates cost-aware Triple-Barrier target labels via TripleBarrierLabeler.
5. Enforces label window boundary isolation (last 12 bars of IS masked to NaN).
6. Fits PartitionAwareScaler strictly on In-Sample training partitions (partition="IS").
7. Transforms Out-of-Sample evaluation matrices using frozen In-Sample statistics.
"""

from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import pandas as pd
import numpy as np

from backend.strategy.qualification import QUALIFIED_PAIRS
from backend.data.loader import load_research_dataset, HOLDOUT_CUTOFF_MS, QuarantinedHoldoutViolationError
from backend.ml.walk_forward import FOLDS_SCHEDULE, WalkForwardFold, WARMUP_BARS, WARMUP_MS
from backend.ml.features import FeaturePipeline, REGISTERED_FEATURE_NAMES, compute_wilder_atr
from backend.ml.labels import TripleBarrierLabeler, TargetLabel
from backend.ml.scaling import PartitionAwareScaler

DATA_DIR = Path("D:/vanta-terminal/data/raw")


def load_universe_1h_candles(
    symbols: Optional[List[str]] = None,
    enforce_holdout_guard: bool = True
) -> Dict[str, List[List[Any]]]:
    """
    Loads raw 1H candle datasets for the universe with holdout protection.
    Returns {symbol: [[open_time, open, high, low, close, volume, close_time], ...]}.
    """
    syms = symbols or QUALIFIED_PAIRS
    universe: Dict[str, List[List[Any]]] = {}

    for sym in syms:
        p_path = DATA_DIR / sym / "1h.parquet"
        if not p_path.exists():
            raise FileNotFoundError(f"Parquet file not found for {sym} at {p_path}")

        candles, meta = load_research_dataset(p_path, enforce_holdout_guard=enforce_holdout_guard)
        universe[sym] = candles

    return universe


def slice_candles(
    candles: List[List[Any]],
    start_ms: int,
    end_ms: int,
    include_warmup_ms: int = 0
) -> List[List[Any]]:
    """
    Extracts candles in [start_ms - include_warmup_ms, end_ms).
    Clamps strictly < HOLDOUT_CUTOFF_MS.
    """
    min_time = start_ms - include_warmup_ms
    sliced = [
        c for c in candles
        if c[0] >= min_time and c[0] < end_ms and c[0] < HOLDOUT_CUTOFF_MS
    ]
    return sliced


def build_fold_matrices(
    fold: WalkForwardFold,
    universe_candles: Dict[str, List[List[Any]]],
    side: str = "LONG"
) -> Dict[str, Any]:
    """
    Constructs clean, leakage-free training and evaluation matrices for a single fold.
    """
    pipeline = FeaturePipeline(warmup_bars=WARMUP_BARS)
    labeler = TripleBarrierLabeler(
        horizon_bars=12,
        profit_atr_mult=1.5,
        stop_atr_mult=1.0,
        friction_hurdle_bps=14.0,
        slippage_bps=2.0
    )

    # 1. Prepare In-Sample Data with Warmup
    is_raw: Dict[str, List[List[Any]]] = {}
    for sym, candles in universe_candles.items():
        is_raw[sym] = slice_candles(
            candles,
            start_ms=fold.is_start_ms,
            end_ms=fold.is_end_ms,
            include_warmup_ms=WARMUP_MS
        )

    # Compute IS features and labels
    is_features_dict = pipeline.process_universe(is_raw)

    is_records = []
    is_labels_list = []
    is_timestamps = []
    is_symbols = []

    for sym in sorted(universe_candles.keys()):
        raw_is_df = pd.DataFrame(
            is_raw[sym],
            columns=["open_time", "open", "high", "low", "close", "volume", "close_time"]
        ).drop_duplicates(subset=["open_time"], keep="last").sort_values("open_time").reset_index(drop=True)

        feat_df = is_features_dict[sym]
        labels_series = labeler.compute_labels(raw_is_df, side=side)

        # Enforce Label Window Boundary Isolation:
        # Mask the last 12 bars before the purge boundary to NaN so no label looks into purge
        if len(labels_series) >= 12:
            labels_series.iloc[-12:] = np.nan

        # Filter strictly to valid prediction window: open_time >= fold.is_start_ms and < fold.is_end_ms
        valid_time_mask = (feat_df["open_time"] >= fold.is_start_ms) & (feat_df["open_time"] < fold.is_end_ms)
        valid_feat_mask = ~feat_df[REGISTERED_FEATURE_NAMES].isna().any(axis=1)
        valid_label_mask = labels_series.notna()

        total_valid_mask = valid_time_mask & valid_feat_mask & valid_label_mask

        sub_feats = feat_df.loc[total_valid_mask, REGISTERED_FEATURE_NAMES].values
        sub_labels = labels_series.loc[total_valid_mask].values.astype(int)
        sub_times = feat_df.loc[total_valid_mask, "open_time"].values
        sub_syms = [sym] * len(sub_feats)

        is_records.append(sub_feats)
        is_labels_list.append(sub_labels)
        is_timestamps.append(sub_times)
        is_symbols.extend(sub_syms)

    X_train_raw = np.vstack(is_records)
    y_train = np.concatenate(is_labels_list)
    train_times = np.concatenate(is_timestamps)

    # 2. Fit Scaler strictly on In-Sample
    scaler = PartitionAwareScaler(clip_min=-5.0, clip_max=5.0)
    scaler.fit(X_train_raw, partition="IS")
    X_train_scaled = scaler.transform(X_train_raw, partition="IS")

    # 3. Prepare Out-of-Sample Data with Warmup
    oos_raw: Dict[str, List[List[Any]]] = {}
    for sym, candles in universe_candles.items():
        oos_raw[sym] = slice_candles(
            candles,
            start_ms=fold.oos_start_ms,
            end_ms=fold.oos_end_ms,
            include_warmup_ms=WARMUP_MS
        )

    oos_features_dict = pipeline.process_universe(oos_raw)

    oos_eval_data: Dict[str, Dict[str, Any]] = {}
    total_oos_samples = 0

    for sym in sorted(universe_candles.keys()):
        raw_oos_df = pd.DataFrame(
            oos_raw[sym],
            columns=["open_time", "open", "high", "low", "close", "volume", "close_time"]
        ).drop_duplicates(subset=["open_time"], keep="last").sort_values("open_time").reset_index(drop=True)

        feat_df = oos_features_dict[sym]
        labels_series = labeler.compute_labels(raw_oos_df, side=side)

        # Mask out warmup rows so evaluation evaluates strictly open_time >= fold.oos_start_ms
        eval_mask = (raw_oos_df["open_time"] >= fold.oos_start_ms) & (raw_oos_df["open_time"] < fold.oos_end_ms)

        eval_raw_df = raw_oos_df.loc[eval_mask].reset_index(drop=True)
        eval_df = feat_df.loc[eval_mask].reset_index(drop=True)
        eval_labels = labels_series.loc[eval_mask].reset_index(drop=True)

        X_eval_raw = eval_df[REGISTERED_FEATURE_NAMES].values
        # Transform OOS features using frozen In-Sample scaler
        X_eval_scaled = scaler.transform(X_eval_raw, partition="OOS")

        # Compute ATR and barrier prices for each bar in OOS
        close_vals = eval_raw_df["close"].values
        high_vals = eval_raw_df["high"].values
        low_vals = eval_raw_df["low"].values
        atr14_vals = compute_wilder_atr(high_vals, low_vals, close_vals, period=14)

        oos_eval_data[sym] = {
            "df": eval_raw_df,
            "X_scaled": X_eval_scaled,
            "y_true": eval_labels,
            "atr14": atr14_vals,
            "open_times": eval_raw_df["open_time"].values,
            "close_prices": close_vals,
        }
        total_oos_samples += len(eval_raw_df)

    return {
        "fold_id": fold.fold_id,
        "fold": fold,
        "scaler": scaler,
        "X_train_scaled": X_train_scaled,
        "y_train": y_train,
        "train_timestamps": train_times,
        "train_samples_count": len(X_train_scaled),
        "oos_eval_data": oos_eval_data,
        "total_oos_samples_count": total_oos_samples
    }
