"""
VANTA Terminal — Feature Engineering Pipeline (Phase 5B)
========================================================
Implements the 21 pre-registered, dimensionless, leakage-safe features specified
in docs/PHASE_5A_FEATURE_CATALOG.md across the 7 feature families:
1. Lagged returns and momentum (RET_1, RET_4, RET_12, RET_24)
2. Volatility and true range (NATR_14, VOLAT_24, GK_VOL_12)
3. Trend and moving average distance (DIST_EMA_20, DIST_EMA_50, SPREAD_EMA_20_50)
4. Relative volume (RVOL_12, RVOL_24, VOL_MOM_4)
5. Candle body and wick structure (BODY_RATIO, UPPER_SHADOW, LOWER_SHADOW)
6. Rolling range and breakout distance (DONCH_POS_24, DIST_HIGH_24, DIST_LOW_24)
7. Cross-sectional relative strength and beta (XS_REL_RET_4, XS_BETA_24)

Invariants:
- Zero lookahead: Feature values at time t utilize strictly information available by bar t close.
- Point-in-time calculation: All indicators use rolling past-only windows.
- Purely deterministic and vectorized.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd

from backend.data.loader import HOLDOUT_CUTOFF_MS, QuarantinedHoldoutViolationError

# The 21 Pre-Registered Feature Column Names in Deterministic Order
REGISTERED_FEATURE_NAMES: List[str] = [
    # Family 1: Lagged Returns & Multi-Horizon Momentum
    "RET_1",
    "RET_4",
    "RET_12",
    "RET_24",
    # Family 2: Volatility & True Range
    "NATR_14",
    "VOLAT_24",
    "GK_VOL_12",
    # Family 3: Trend & Moving Average Distance
    "DIST_EMA_20",
    "DIST_EMA_50",
    "SPREAD_EMA_20_50",
    # Family 4: Relative Volume
    "RVOL_12",
    "RVOL_24",
    "VOL_MOM_4",
    # Family 5: Candle Microstructure
    "BODY_RATIO",
    "UPPER_SHADOW",
    "LOWER_SHADOW",
    # Family 6: Rolling Range & Breakout Proximity
    "DONCH_POS_24",
    "DIST_HIGH_24",
    "DIST_LOW_24",
    # Family 7: Cross-Sectional Dynamics
    "XS_REL_RET_4",
    "XS_BETA_24"
]

EPSILON: float = 1e-8


def compute_wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    """
    Computes Wilder's Smoothed Average True Range (ATR).
    TR_t = max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)
    ATR_t = (ATR_{t-1} * 13 + TR_t) / 14
    """
    n = len(close)
    if n == 0:
        return np.array([], dtype=np.float64)

    tr = np.zeros(n, dtype=np.float64)
    tr[0] = high[0] - low[0]

    prev_close = close[:-1]
    curr_high = high[1:]
    curr_low = low[1:]

    h_l = curr_high - curr_low
    h_pc = np.abs(curr_high - prev_close)
    l_pc = np.abs(curr_low - prev_close)

    tr[1:] = np.maximum(h_l, np.maximum(h_pc, l_pc))

    atr = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return atr

    # Seed ATR with simple average of first 'period' true ranges
    atr[period - 1] = np.mean(tr[:period])
    alpha = 1.0 / period

    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) * alpha

    return atr


def compute_ema(series: np.ndarray, period: int) -> np.ndarray:
    """
    Computes Exponential Moving Average with smoothing factor alpha = 2 / (period + 1).
    Seeds with initial simple mean over 'period' observations.
    """
    n = len(series)
    ema = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return ema

    alpha = 2.0 / (period + 1)
    ema[period - 1] = np.mean(series[:period])

    for i in range(period, n):
        ema[i] = alpha * series[i] + (1.0 - alpha) * ema[i - 1]

    return ema


def compute_single_pair_features(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Computes the 19 pair-specific features from OHLCV series.
    Input DataFrame must contain: ['open', 'high', 'low', 'close', 'volume'].
    """
    df = df_input.copy()
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            raise ValueError(f"Missing required input column: {col}")

    c = df["close"].values.astype(np.float64)
    o = df["open"].values.astype(np.float64)
    h = df["high"].values.astype(np.float64)
    l = df["low"].values.astype(np.float64)
    v = df["volume"].values.astype(np.float64)
    n = len(c)

    feat_df = pd.DataFrame(index=df.index)

    # -------------------------------------------------------------------------
    # Family 1: Lagged Returns & Momentum
    # -------------------------------------------------------------------------
    feat_df["RET_1"] = np.nan
    feat_df["RET_4"] = np.nan
    feat_df["RET_12"] = np.nan
    feat_df["RET_24"] = np.nan

    if n > 1:
        feat_df.iloc[1:, feat_df.columns.get_loc("RET_1")] = np.log(c[1:] / (c[:-1] + EPSILON))
    if n > 4:
        feat_df.iloc[4:, feat_df.columns.get_loc("RET_4")] = np.log(c[4:] / (c[:-4] + EPSILON))
    if n > 12:
        feat_df.iloc[12:, feat_df.columns.get_loc("RET_12")] = np.log(c[12:] / (c[:-12] + EPSILON))
    if n > 24:
        feat_df.iloc[24:, feat_df.columns.get_loc("RET_24")] = np.log(c[24:] / (c[:-24] + EPSILON))

    # -------------------------------------------------------------------------
    # Family 2: Volatility & True Range Measures
    # -------------------------------------------------------------------------
    atr14 = compute_wilder_atr(h, l, c, period=14)
    feat_df["NATR_14"] = (atr14 / (c + EPSILON)) * 100.0

    # VOLAT_24: Rolling 24-period sample std of RET_1 (ddof=1)
    ret1_series = feat_df["RET_1"]
    feat_df["VOLAT_24"] = ret1_series.rolling(window=24, min_periods=24).std(ddof=1).values

    # GK_VOL_12: Garman-Klass volatility over 12 bars
    hl_ratio = np.log(np.maximum(h / (l + EPSILON), 1.0))
    co_ratio = np.log(np.maximum(c / (o + EPSILON), EPSILON))
    gk_terms = 0.5 * (hl_ratio ** 2) - (2.0 * np.log(2.0) - 1.0) * (co_ratio ** 2)
    gk_series = pd.Series(gk_terms, index=df.index)
    rolling_gk_mean = gk_series.rolling(window=12, min_periods=12).mean().values
    feat_df["GK_VOL_12"] = np.sqrt(np.maximum(rolling_gk_mean, 0.0))

    # -------------------------------------------------------------------------
    # Family 3: Trend & Moving Average Distance
    # -------------------------------------------------------------------------
    ema20 = compute_ema(c, period=20)
    ema50 = compute_ema(c, period=50)

    # Protect against ATR <= 0
    safe_atr = np.where(np.isnan(atr14) | (atr14 <= 0), np.nan, atr14)
    feat_df["DIST_EMA_20"] = (c - ema20) / safe_atr
    feat_df["DIST_EMA_50"] = (c - ema50) / safe_atr
    feat_df["SPREAD_EMA_20_50"] = (ema20 - ema50) / safe_atr

    # -------------------------------------------------------------------------
    # Family 4: Relative Volume Baseline
    # -------------------------------------------------------------------------
    vol_series = pd.Series(v, index=df.index)
    vol_sma12 = vol_series.rolling(window=12, min_periods=12).mean().values
    vol_sma24 = vol_series.rolling(window=24, min_periods=24).mean().values

    feat_df["RVOL_12"] = v / (vol_sma12 + EPSILON)
    feat_df["RVOL_24"] = v / (vol_sma24 + EPSILON)

    # VOL_MOM_4: sum(V_{t-3..t}) / (sum(V_{t-7..t-4}) + eps)
    sum_recent = vol_series.rolling(window=4, min_periods=4).sum().values
    sum_prior = vol_series.shift(4).rolling(window=4, min_periods=4).sum().values
    feat_df["VOL_MOM_4"] = sum_recent / (sum_prior + EPSILON)

    # -------------------------------------------------------------------------
    # Family 5: Candle Body & Wick Microstructure
    # -------------------------------------------------------------------------
    full_range = h - l + EPSILON
    feat_df["BODY_RATIO"] = np.clip(np.abs(c - o) / full_range, 0.0, 1.0)
    feat_df["UPPER_SHADOW"] = np.clip((h - np.maximum(o, c)) / full_range, 0.0, 1.0)
    feat_df["LOWER_SHADOW"] = np.clip((np.minimum(o, c) - l) / full_range, 0.0, 1.0)

    # -------------------------------------------------------------------------
    # Family 6: Rolling Range & Breakout Proximity
    # -------------------------------------------------------------------------
    h_series = pd.Series(h, index=df.index)
    l_series = pd.Series(l, index=df.index)

    high24 = h_series.rolling(window=24, min_periods=24).max().values
    low24 = l_series.rolling(window=24, min_periods=24).min().values

    donch_range = high24 - low24 + EPSILON
    feat_df["DONCH_POS_24"] = np.clip((c - low24) / donch_range, 0.0, 1.0)
    feat_df["DIST_HIGH_24"] = (high24 - c) / safe_atr
    feat_df["DIST_LOW_24"] = (c - low24) / safe_atr

    return feat_df


def compute_cross_sectional_features(
    pair_features: Dict[str, pd.DataFrame],
    btc_symbol: str = "BTCUSDT"
) -> Dict[str, pd.DataFrame]:
    """
    Computes Family 7 cross-sectional features across all pairs in the universe:
    - XS_REL_RET_4: pair RET_4 minus cross-sectional mean RET_4
    - XS_BETA_24: 24-period rolling beta against BTCUSDT
    """
    symbols = sorted(pair_features.keys())
    if not symbols:
        return {}

    has_timestamps = all("open_time" in pair_features[s].columns for s in symbols)
    if has_timestamps:
        ret4_df = pd.DataFrame({s: pair_features[s].set_index("open_time")["RET_4"] for s in symbols})
        xs_mean_ret4 = ret4_df.mean(axis=1)
        ret1_df = pd.DataFrame({s: pair_features[s].set_index("open_time")["RET_1"] for s in symbols})
    else:
        ret4_df = pd.DataFrame({s: pair_features[s]["RET_4"] for s in symbols})
        xs_mean_ret4 = ret4_df.mean(axis=1)
        ret1_df = pd.DataFrame({s: pair_features[s]["RET_1"] for s in symbols})

    has_btc = btc_symbol in symbols
    btc_ret1 = ret1_df[btc_symbol] if has_btc else None
    if has_btc:
        btc_var24 = btc_ret1.rolling(window=24, min_periods=24).var(ddof=1)

    for s in symbols:
        df = pair_features[s]
        # XS_REL_RET_4
        if has_timestamps:
            df["XS_REL_RET_4"] = (df["RET_4"] - df["open_time"].map(xs_mean_ret4)).values
        else:
            df["XS_REL_RET_4"] = df["RET_4"] - xs_mean_ret4

        # XS_BETA_24
        if s == btc_symbol:
            df["XS_BETA_24"] = np.where(df["RET_1"].notna(), 1.0, np.nan)
        elif has_btc:
            pair_ret1 = df.set_index("open_time")["RET_1"] if has_timestamps else df["RET_1"]
            cov24 = pair_ret1.rolling(window=24, min_periods=24).cov(btc_ret1)
            beta24 = cov24 / (btc_var24 + EPSILON)
            if has_timestamps:
                df["XS_BETA_24"] = df["open_time"].map(beta24).values
            else:
                df["XS_BETA_24"] = beta24.values
        else:
            df["XS_BETA_24"] = 1.0

    return pair_features


class FeaturePipeline:
    """
    Deterministic, leakage-safe pipeline that processes raw candle datasets
    and outputs the 21 registered features for each pair in the universe.
    """

    def __init__(self, warmup_bars: int = 150):
        self.warmup_bars = warmup_bars

    def process_universe(
        self,
        raw_universe_data: Dict[str, Union[List[List[Any]], pd.DataFrame]],
        btc_symbol: str = "BTCUSDT"
    ) -> Dict[str, pd.DataFrame]:
        """
        Processes multi-pair OHLCV datasets and returns feature matrices for all pairs.
        Each resulting DataFrame has exactly the 21 registered columns and preserves
        timestamp alignment.
        """
        pair_dfs: Dict[str, pd.DataFrame] = {}

        # 1. Standardize input to DataFrames
        for symbol, data in raw_universe_data.items():
            if isinstance(data, list):
                df = pd.DataFrame(
                    data,
                    columns=["open_time", "open", "high", "low", "close", "volume", "close_time"]
                )
            elif isinstance(data, pd.DataFrame):
                df = data.copy()
            else:
                raise TypeError(f"Unsupported data format for symbol {symbol}: {type(data)}")

            if "open_time" in df.columns and len(df) > 0:
                # Active holdout quarantine interception
                max_time = df["open_time"].max()
                if max_time >= HOLDOUT_CUTOFF_MS:
                    raise QuarantinedHoldoutViolationError(
                        f"CRITICAL PROTOCOL VIOLATION: Candle for {symbol} has open_time={max_time} "
                        f"which reaches or exceeds the holdout cutoff {HOLDOUT_CUTOFF_MS} (2026-04-26T00:00:00Z)."
                    )
                # Deduplicate and sort
                df = df.drop_duplicates(subset=["open_time"], keep="last").sort_values("open_time").reset_index(drop=True)
            else:
                df = df.reset_index(drop=True)

            pair_dfs[symbol] = df

        # 2. Compute 19 single-pair features per symbol
        feat_dict: Dict[str, pd.DataFrame] = {}
        for symbol, df in pair_dfs.items():
            feat_df = compute_single_pair_features(df)
            feat_df["open_time"] = df["open_time"].values
            feat_df["close_time"] = df["close_time"].values
            feat_dict[symbol] = feat_df

        # 3. Compute 2 cross-sectional features across the universe
        feat_dict = compute_cross_sectional_features(feat_dict, btc_symbol=btc_symbol)

        # 4. Final verification and column ordering
        final_dict: Dict[str, pd.DataFrame] = {}
        for symbol, fdf in feat_dict.items():
            # Ensure exact ordering: metadata columns followed by the 21 features
            cols = ["open_time", "close_time"] + REGISTERED_FEATURE_NAMES
            ordered_df = fdf[cols].copy()
            final_dict[symbol] = ordered_df

        return final_dict
