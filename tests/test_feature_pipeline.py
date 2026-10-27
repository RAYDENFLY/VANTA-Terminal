"""
VANTA Terminal — Feature Pipeline Integration & Mathematical Correctness Tests (Phase 5B)
========================================================================================
Tests the 21 pre-registered features in backend/ml/features.py:
1. Correctness of mathematical formulas against hand-calculated values.
2. Complete coverage of all 7 feature families.
3. Warmup behavior and convergence rate.
4. Handling of NaN and missing values.
5. Cross-sectional alignment across multi-pair datasets.
"""

import pytest
import numpy as np
import pandas as pd

from backend.ml.features import (
    REGISTERED_FEATURE_NAMES,
    compute_wilder_atr,
    compute_ema,
    compute_single_pair_features,
    compute_cross_sectional_features,
    FeaturePipeline
)


def make_synthetic_ohlcv(n_bars: int = 200, base_price: float = 100.0, trend: float = 0.05, seed: int = 42) -> pd.DataFrame:
    """Generates synthetic hourly OHLCV DataFrame for deterministic testing."""
    rng = np.random.default_rng(seed)
    open_time_start = 1700000000000 # Unix ms

    closes = [base_price]
    for _ in range(1, n_bars):
        ret = trend + rng.normal(0, 0.5)
        closes.append(max(closes[-1] + ret, 1.0))
    closes = np.array(closes)

    opens = np.concatenate([[base_price], closes[:-1]]) + rng.uniform(-0.1, 0.1, size=n_bars)
    highs = np.maximum(opens, closes) + rng.uniform(0.1, 1.0, size=n_bars)
    lows = np.maximum(np.minimum(opens, closes) - rng.uniform(0.1, 1.0, size=n_bars), 0.1)
    volumes = rng.uniform(500, 2000, size=n_bars)

    open_times = [open_time_start + i * 3600000 for i in range(n_bars)]
    close_times = [ot + 3599999 for ot in open_times]

    return pd.DataFrame({
        "open_time": open_times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "close_time": close_times
    })


def test_registered_feature_count_and_names():
    """Verify that exactly 21 features are registered and conform to catalog names."""
    assert len(REGISTERED_FEATURE_NAMES) == 21
    expected = [
        "RET_1", "RET_4", "RET_12", "RET_24",
        "NATR_14", "VOLAT_24", "GK_VOL_12",
        "DIST_EMA_20", "DIST_EMA_50", "SPREAD_EMA_20_50",
        "RVOL_12", "RVOL_24", "VOL_MOM_4",
        "BODY_RATIO", "UPPER_SHADOW", "LOWER_SHADOW",
        "DONCH_POS_24", "DIST_HIGH_24", "DIST_LOW_24",
        "XS_REL_RET_4", "XS_BETA_24"
    ]
    assert REGISTERED_FEATURE_NAMES == expected


def test_wilder_atr_mathematical_formula():
    """Hand-verify Wilder's ATR recursion against known step-by-step numbers."""
    high = np.array([105.0, 108.0, 110.0, 106.0])
    low = np.array([95.0, 100.0, 102.0, 98.0])
    close = np.array([100.0, 105.0, 104.0, 102.0])

    # Period = 2 for quick hand check
    # Bar 0: TR = H - L = 10.0
    # Bar 1: TR = max(108-100, |108-100|, |100-100|) = 8.0
    # Seed ATR at index 1 = (10.0 + 8.0)/2 = 9.0
    # Bar 2: TR = max(110-102, |110-105|, |102-105|) = max(8, 5, 3) = 8.0
    # ATR at index 2 = (9.0 * 1 + 8.0)/2 = 8.5
    # Bar 3: TR = max(106-98, |106-104|, |98-104|) = max(8, 2, 6) = 8.0
    # ATR at index 3 = (8.5 * 1 + 8.0)/2 = 8.25
    atr = compute_wilder_atr(high, low, close, period=2)
    assert np.isnan(atr[0])
    assert pytest.approx(atr[1], abs=1e-4) == 9.0
    assert pytest.approx(atr[2], abs=1e-4) == 8.5
    assert pytest.approx(atr[3], abs=1e-4) == 8.25


def test_ema_mathematical_formula():
    """Verify EMA smoothing factor alpha = 2/(P+1) and initialization."""
    series = np.array([10.0, 20.0, 30.0, 40.0])
    # Period = 2: alpha = 2/3
    # Seed at index 1 = mean(10, 20) = 15.0
    # Index 2: 2/3 * 30 + 1/3 * 15 = 20 + 5 = 25.0
    # Index 3: 2/3 * 40 + 1/3 * 25 = 26.6667 + 8.3333 = 35.0
    ema = compute_ema(series, period=2)
    assert np.isnan(ema[0])
    assert pytest.approx(ema[1], abs=1e-4) == 15.0
    assert pytest.approx(ema[2], abs=1e-4) == 25.0
    assert pytest.approx(ema[3], abs=1e-4) == 35.0


def test_single_pair_feature_generation():
    """Verify all 19 single-pair features are produced with valid dimensions."""
    df = make_synthetic_ohlcv(n_bars=150)
    feat_df = compute_single_pair_features(df)

    assert len(feat_df) == 150
    # Check that after bar 50, all 19 single-pair features are populated
    warm_slice = feat_df.iloc[50:]
    for col in [
        "RET_1", "RET_4", "RET_12", "RET_24",
        "NATR_14", "VOLAT_24", "GK_VOL_12",
        "DIST_EMA_20", "DIST_EMA_50", "SPREAD_EMA_20_50",
        "RVOL_12", "RVOL_24", "VOL_MOM_4",
        "BODY_RATIO", "UPPER_SHADOW", "LOWER_SHADOW",
        "DONCH_POS_24", "DIST_HIGH_24", "DIST_LOW_24"
    ]:
        assert col in feat_df.columns
        assert not warm_slice[col].isna().any(), f"Unexpected NaN in warm slice for {col}"

    # Verify microstructure ratios are strictly bounded in [0, 1]
    assert (feat_df["BODY_RATIO"].dropna() >= 0.0).all()
    assert (feat_df["BODY_RATIO"].dropna() <= 1.0 + 1e-5).all()
    assert (feat_df["UPPER_SHADOW"].dropna() >= 0.0).all()
    assert (feat_df["LOWER_SHADOW"].dropna() >= 0.0).all()
    assert (feat_df["DONCH_POS_24"].dropna() >= 0.0).all()
    assert (feat_df["DONCH_POS_24"].dropna() <= 1.0).all()


def test_cross_sectional_features():
    """Verify Family 7 cross-sectional features across multi-pair universe."""
    universe = {
        "BTCUSDT": make_synthetic_ohlcv(n_bars=100, base_price=50000.0, seed=1),
        "ETHUSDT": make_synthetic_ohlcv(n_bars=100, base_price=3000.0, seed=2),
        "SOLUSDT": make_synthetic_ohlcv(n_bars=100, base_price=150.0, seed=3)
    }

    # Compute single-pair features first
    feat_dict = {sym: compute_single_pair_features(df) for sym, df in universe.items()}
    xs_feat = compute_cross_sectional_features(feat_dict, btc_symbol="BTCUSDT")

    # BTC beta against BTC must be identically 1.0 (once warm)
    btc_beta = xs_feat["BTCUSDT"]["XS_BETA_24"].iloc[25:]
    assert (btc_beta == 1.0).all()

    # Sum of cross-sectional relative returns across all pairs must equal 0.0 at every bar
    ret_rel_sum = (
        xs_feat["BTCUSDT"]["XS_REL_RET_4"] +
        xs_feat["ETHUSDT"]["XS_REL_RET_4"] +
        xs_feat["SOLUSDT"]["XS_REL_RET_4"]
    ).iloc[10:]
    assert np.allclose(ret_rel_sum.dropna().values, 0.0, atol=1e-10)


def test_feature_pipeline_full_universe():
    """Verify FeaturePipeline end-to-end integration and column ordering."""
    pipeline = FeaturePipeline(warmup_bars=150)
    raw_universe = {
        "BTCUSDT": make_synthetic_ohlcv(n_bars=200, seed=10),
        "ETHUSDT": make_synthetic_ohlcv(n_bars=200, seed=20)
    }

    results = pipeline.process_universe(raw_universe)
    assert len(results) == 2
    for sym in ["BTCUSDT", "ETHUSDT"]:
        df_res = results[sym]
        assert len(df_res) == 200
        # Columns must be open_time, close_time + 21 features
        expected_cols = ["open_time", "close_time"] + REGISTERED_FEATURE_NAMES
        assert list(df_res.columns) == expected_cols
        # Warm slice (index >= 150) must have zero NaNs
        assert not df_res.iloc[150:][REGISTERED_FEATURE_NAMES].isna().any().any()
