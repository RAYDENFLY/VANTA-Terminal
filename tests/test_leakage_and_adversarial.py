"""
VANTA Terminal — Feature Leakage & Adversarial Safety Tests (Phase 5B)
======================================================================
Tests the leakage safety, chronological partition guard, and holdout protection:
1. Adversarial Future Modification Test: Proves that mutating future bars has zero effect on past features.
2. Partition-Aware Scaler: Proves that Out-of-Sample features are transformed using only training statistics.
3. Holdout Cutoff Guard: Verifies that synthetic candles at or after 2026-04-26T00:00:00Z are blocked.
4. Timestamp gaps and synchronization robustness.
"""

import pytest
import numpy as np
import pandas as pd

from backend.ml.features import (
    compute_single_pair_features,
    compute_cross_sectional_features,
    FeaturePipeline,
    REGISTERED_FEATURE_NAMES
)
from backend.ml.scaling import PartitionAwareScaler
from backend.data.loader import (
    HOLDOUT_CUTOFF_MS,
    filter_candles_holdout_guard,
    QuarantinedHoldoutViolationError
)


def make_clean_series(n_bars: int = 150, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    open_times = [1700000000000 + i * 3600000 for i in range(n_bars)]
    close_times = [ot + 3599999 for ot in open_times]

    closes = 100.0 + np.cumsum(rng.normal(0, 1.0, size=n_bars))
    highs = closes + rng.uniform(0.5, 1.5, size=n_bars)
    lows = closes - rng.uniform(0.5, 1.5, size=n_bars)
    opens = np.concatenate([[100.0], closes[:-1]])
    volumes = rng.uniform(100, 1000, size=n_bars)

    return pd.DataFrame({
        "open_time": open_times,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "close_time": close_times
    })


def test_adversarial_future_modification_single_pair():
    """
    Adversarial Leakage Proof:
    Mutating future bars (from bar k to end) must have exactly ZERO effect
    on any of the 19 single-pair features at or before bar k-1.
    """
    df_original = make_clean_series(n_bars=150, seed=123)
    feat_orig = compute_single_pair_features(df_original)

    # Cut point: bar 100
    k = 100

    # Create mutated future dataframe
    df_mutated = df_original.copy()
    # Drastically mutate future prices and volumes starting at bar k
    df_mutated.loc[k:, "close"] = df_mutated.loc[k:, "close"] * 50.0
    df_mutated.loc[k:, "high"] = df_mutated.loc[k:, "high"] * 100.0
    df_mutated.loc[k:, "low"] = df_mutated.loc[k:, "low"] * 0.01
    df_mutated.loc[k:, "volume"] = df_mutated.loc[k:, "volume"] * 1000.0

    feat_mutated = compute_single_pair_features(df_mutated)

    # Compare past slice (0 to k-1) across all single-pair features
    for col in feat_orig.columns:
        past_orig = feat_orig.loc[:k - 1, col].values
        past_mut = feat_mutated.loc[:k - 1, col].values

        # Must be identical to machine precision (handling NaNs equally)
        np.testing.assert_allclose(
            np.nan_to_num(past_orig, nan=-999.0),
            np.nan_to_num(past_mut, nan=-999.0),
            rtol=1e-12,
            atol=1e-12,
            err_msg=f"Leakage detected in feature {col}: past values changed when future was mutated!"
        )


def test_adversarial_future_modification_cross_sectional():
    """
    Adversarial Leakage Proof for Cross-Sectional Features:
    Mutating future bars in any pair must not alter past cross-sectional features in any pair.
    """
    universe_orig = {
        "BTCUSDT": make_clean_series(n_bars=150, seed=1),
        "ETHUSDT": make_clean_series(n_bars=150, seed=2)
    }

    pipeline = FeaturePipeline()
    feat_orig = pipeline.process_universe(universe_orig)

    k = 100
    universe_mut = {
        "BTCUSDT": universe_orig["BTCUSDT"].copy(),
        "ETHUSDT": universe_orig["ETHUSDT"].copy()
    }
    # Mutate future BTC drastically from bar k onwards
    universe_mut["BTCUSDT"].loc[k:, "close"] *= 10.0
    universe_mut["BTCUSDT"].loc[k:, "high"] *= 15.0

    feat_mut = pipeline.process_universe(universe_mut)

    for sym in ["BTCUSDT", "ETHUSDT"]:
        df_o = feat_orig[sym]
        df_m = feat_mut[sym]
        for col in ["XS_REL_RET_4", "XS_BETA_24"]:
            past_o = df_o.loc[:k - 1, col].values
            past_m = df_m.loc[:k - 1, col].values
            np.testing.assert_allclose(
                np.nan_to_num(past_o, nan=-999.0),
                np.nan_to_num(past_m, nan=-999.0),
                rtol=1e-12,
                atol=1e-12,
                err_msg=f"Leakage detected in cross-sectional feature {col} for {sym}!"
            )


def test_partition_aware_scaler_isolation():
    """Verify that scaler fits exclusively on In-Sample and transforms OOS cleanly."""
    scaler = PartitionAwareScaler()
    assert not scaler.is_fitted

    # Attempting to transform before fitting must raise RuntimeError
    with pytest.raises(RuntimeError):
        scaler.transform(np.array([[1.0, 2.0]]))

    # Fit on synthetic training slice
    X_train = np.array([
        [10.0, 100.0],
        [20.0, 200.0],
        [30.0, 300.0],
        [40.0, 400.0],
        [50.0, 500.0]
    ])
    scaler.fit(X_train)
    assert scaler.is_fitted

    # Check fitted medians and scales
    params = scaler.get_params_dict()
    assert params["fitted"] is True
    assert params["center"] == [30.0, 300.0]  # Medians of train

    # Transform OOS data
    X_oos = np.array([[30.0, 300.0], [50.0, 500.0], [1000.0, 10000.0]])
    scaled_oos = scaler.transform(X_oos)

    # Row 0 equals median -> must be 0.0
    assert pytest.approx(scaled_oos[0, 0], abs=1e-5) == 0.0
    assert pytest.approx(scaled_oos[0, 1], abs=1e-5) == 0.0

    # Row 2 is an extreme outlier -> must be clipped to max (+5.0)
    assert scaled_oos[2, 0] == 5.0
    assert scaled_oos[2, 1] == 5.0

    # Fitting on OOS partition must raise ValueError
    with pytest.raises(ValueError, match="In-Sample"):
        scaler.fit(X_train, partition="OOS")

    # Transforming holdout data must raise ValueError
    with pytest.raises(ValueError, match="Holdout"):
        scaler.transform(X_oos, partition="HOLDOUT")


def test_holdout_quarantine_guard_interception():
    """Verify that synthetic candles at or after HOLDOUT_CUTOFF_MS are intercepted."""
    cutoff = HOLDOUT_CUTOFF_MS
    synthetic_candles = [
        [cutoff - 7200000, 100, 105, 95, 100, 500, cutoff - 3600001], # Valid (2h prior)
        [cutoff - 3600000, 100, 105, 95, 100, 500, cutoff - 1],       # Valid (1h prior)
        [cutoff, 100, 105, 95, 100, 500, cutoff + 3599999],           # FORBIDDEN (at cutoff)
        [cutoff + 3600000, 100, 105, 95, 100, 500, cutoff + 7199999]  # FORBIDDEN (after cutoff)
    ]

    # Filter with raise_on_holdout_access=False
    filtered = filter_candles_holdout_guard(synthetic_candles, raise_on_holdout_access=False)
    assert len(filtered) == 2
    assert all(c[0] < cutoff for c in filtered)

    # Filter with raise_on_holdout_access=True must raise QuarantinedHoldoutViolationError
    with pytest.raises(QuarantinedHoldoutViolationError):
        filter_candles_holdout_guard(synthetic_candles, raise_on_holdout_access=True)

    # FeaturePipeline must also directly raise QuarantinedHoldoutViolationError
    pipeline = FeaturePipeline()
    with pytest.raises(QuarantinedHoldoutViolationError):
        pipeline.process_universe({"BTCUSDT": synthetic_candles})


def test_feature_pipeline_timestamp_deduplication():
    """Verify that duplicate timestamps in input OHLCV are deterministically deduplicated."""
    candles = [
        [1700000000000, 100.0, 101.0, 99.0, 100.0, 500.0, 1700003599999],
        [1700003600000, 100.0, 101.0, 99.0, 100.0, 500.0, 1700007199999],
        [1700003600000, 100.5, 101.5, 99.5, 100.5, 600.0, 1700007199999], # Duplicate timestamp!
        [1700007200000, 101.0, 102.0, 100.0, 101.0, 500.0, 1700010799999],
    ]
    pipeline = FeaturePipeline()
    res = pipeline.process_universe({"BTCUSDT": candles})
    df_btc = res["BTCUSDT"]

    # 4 rows input with 1 duplicate -> exactly 3 unique timestamps output
    assert len(df_btc) == 3
    assert df_btc["open_time"].is_monotonic_increasing
    assert len(df_btc["open_time"].unique()) == 3
