"""
VANTA Terminal — Triple-Barrier Target Labeling Engine (Phase 5B)
================================================================
Implements the pre-registered cost-aware Triple Barrier labeling engine (TARGET-C-BARRIER)
specified in docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md and audited in Phase 5A.1/5A.2.

Key Invariants:
1. Entry Reference Price: Bar t+1 Open with 2.0 bps adverse slippage (s = 0.0002).
2. Horizon: Exactly 12 bars (12 hours on 1H timeframe).
3. Profit Barrier: 1.5 * ATR_14 + 14.0 bps friction hurdle (guarantees positive net PnL).
4. Stop Barrier: 1.0 * ATR_14.
5. Intrabar Priority: CONSERVATIVE_SL_FIRST (same-candle collision triggers Stop Loss first).
6. Gap Handling: Open gaps beyond stop fill at Open.
7. Classes: +1 (LONG_BREAKOUT), -1 (SHORT_BREAKOUT), 0 (NEUTRAL_EXPIRY).
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd
from enum import IntEnum

from backend.ml.features import compute_wilder_atr


class TargetLabel(IntEnum):
    SHORT_BREAKOUT = -1
    NEUTRAL_EXPIRY = 0
    LONG_BREAKOUT = 1


class TripleBarrierLabeler:
    """
    Deterministic, leakage-safe Triple Barrier target generator.
    """

    def __init__(
        self,
        horizon_bars: int = 12,
        profit_atr_mult: float = 1.5,
        stop_atr_mult: float = 1.0,
        friction_hurdle_bps: float = 14.0,
        slippage_bps: float = 2.0
    ):
        self.horizon_bars = horizon_bars
        self.profit_atr_mult = profit_atr_mult
        self.stop_atr_mult = stop_atr_mult
        self.friction_hurdle_rate = friction_hurdle_bps / 10000.0  # 0.0014
        self.slippage_rate = slippage_bps / 10000.0                # 0.0002

    def compute_barriers(
        self,
        open_next: float,
        close_t: float,
        atr_t: float
    ) -> Dict[str, float]:
        """
        Computes exact reference entry and barrier prices according to frozen Phase 5A.2 formulas:
        Long TP:  entry * (1 + 1.5 * ATR14 / close + 0.0014)
        Long SL:  entry * (1 - 1.0 * ATR14 / close)
        Short TP: entry * (1 - 1.5 * ATR14 / close - 0.0014)
        Short SL: entry * (1 + 1.0 * ATR14 / close)
        """
        p_entry_long = open_next * (1.0 + self.slippage_rate)
        p_entry_short = open_next * (1.0 - self.slippage_rate)
        delta_atr = atr_t / close_t

        long_tp = p_entry_long * (1.0 + self.profit_atr_mult * delta_atr + self.friction_hurdle_rate)
        long_sl = p_entry_long * (1.0 - self.stop_atr_mult * delta_atr)

        short_tp = p_entry_short * (1.0 - self.profit_atr_mult * delta_atr - self.friction_hurdle_rate)
        short_sl = p_entry_short * (1.0 + self.stop_atr_mult * delta_atr)

        return {
            "p_entry_long": p_entry_long,
            "p_entry_short": p_entry_short,
            "delta_atr": delta_atr,
            "long_tp": long_tp,
            "long_sl": long_sl,
            "short_tp": short_tp,
            "short_sl": short_sl,
        }

    def compute_labels(self, df_ohlcv: pd.DataFrame) -> pd.Series:
        """
        Computes the 3-class target label for each bar t.
        Input DataFrame must contain: ['open', 'high', 'low', 'close'].
        Returns a Series of integers in {-1, 0, 1} aligned with input df index.
        Last `horizon_bars` rows are assigned NaN because forward path is incomplete.
        """
        for col in ["open", "high", "low", "close"]:
            if col not in df_ohlcv.columns:
                raise ValueError(f"Missing required column: {col}")

        n = len(df_ohlcv)
        labels = pd.Series(np.nan, index=df_ohlcv.index, dtype=np.float64)

        if n <= self.horizon_bars + 1:
            return labels

        o = df_ohlcv["open"].values.astype(np.float64)
        h = df_ohlcv["high"].values.astype(np.float64)
        l = df_ohlcv["low"].values.astype(np.float64)
        c = df_ohlcv["close"].values.astype(np.float64)

        # 1. Compute Wilder's ATR_14
        atr14 = compute_wilder_atr(h, l, c, period=14)

        # 2. Iterate through each valid prediction bar t
        for t in range(n - self.horizon_bars):
            atr_t = atr14[t]
            close_t = c[t]

            # If ATR is uninitialized, label cannot be determined
            if np.isnan(atr_t) or atr_t <= 0.0 or close_t <= 0.0:
                continue

            open_next = o[t + 1]
            barriers = self.compute_barriers(open_next=open_next, close_t=close_t, atr_t=atr_t)
            long_tp = barriers["long_tp"]
            long_sl = barriers["long_sl"]
            short_tp = barriers["short_tp"]
            short_sl = barriers["short_sl"]

            # Evaluate forward path over bars t+1, t+2, ..., t+H
            long_outcome: Optional[str] = None  # "TP", "SL", or None
            long_hit_step: int = 999

            short_outcome: Optional[str] = None # "TP", "SL", or None
            short_hit_step: int = 999

            for step in range(1, self.horizon_bars + 1):
                idx = t + step
                bar_o = o[idx]
                bar_h = h[idx]
                bar_l = l[idx]

                # Check Long Barriers
                if long_outcome is None:
                    # Check gap through stop
                    is_gap_sl = bar_o <= long_sl
                    is_touch_sl = bar_l <= long_sl or is_gap_sl
                    is_touch_tp = bar_h >= long_tp

                    # Same-candle collision policy: CONSERVATIVE_SL_FIRST
                    if is_touch_sl and is_touch_tp:
                        long_outcome = "SL"
                        long_hit_step = step
                    elif is_touch_sl:
                        long_outcome = "SL"
                        long_hit_step = step
                    elif is_touch_tp:
                        long_outcome = "TP"
                        long_hit_step = step

                # Check Short Barriers
                if short_outcome is None:
                    is_gap_sl_s = bar_o >= short_sl
                    is_touch_sl_s = bar_h >= short_sl or is_gap_sl_s
                    is_touch_tp_s = bar_l <= short_tp

                    # Same-candle collision policy: CONSERVATIVE_SL_FIRST
                    if is_touch_sl_s and is_touch_tp_s:
                        short_outcome = "SL"
                        short_hit_step = step
                    elif is_touch_sl_s:
                        short_outcome = "SL"
                        short_hit_step = step
                    elif is_touch_tp_s:
                        short_outcome = "TP"
                        short_hit_step = step

                # Early break if both sides have reached a definitive barrier
                if long_outcome is not None and short_outcome is not None:
                    break

            # Resolve Final Target Label
            assigned_label = TargetLabel.NEUTRAL_EXPIRY

            is_long_winner = (long_outcome == "TP")
            is_short_winner = (short_outcome == "TP")

            if is_long_winner and not is_short_winner:
                assigned_label = TargetLabel.LONG_BREAKOUT
            elif is_short_winner and not is_long_winner:
                assigned_label = TargetLabel.SHORT_BREAKOUT
            elif is_long_winner and is_short_winner:
                # Both hit TP at some point: the one that hit TP strictly earlier wins
                if long_hit_step < short_hit_step:
                    assigned_label = TargetLabel.LONG_BREAKOUT
                elif short_hit_step < long_hit_step:
                    assigned_label = TargetLabel.SHORT_BREAKOUT
                else:
                    assigned_label = TargetLabel.NEUTRAL_EXPIRY
            else:
                assigned_label = TargetLabel.NEUTRAL_EXPIRY

            labels.iloc[t] = int(assigned_label)

        return labels
