"""
VANTA Terminal — Triple Barrier Target Deterministic Tests (Phase 5B.1 Conformance)
===================================================================================
Tests the deterministic target labeling engine (TARGET-C-BARRIER) against all
required barrier interaction invariants and frozen Phase 5A.2 specifications:
1. Exact Barrier Formulas: Mathematical verification of TP/SL and adverse slippage formulas.
2. TP-First: Price reaches Take Profit barrier before Stop Loss -> Class +1.
3. SL-First: Price reaches Stop Loss barrier before Take Profit -> Class -1.
4. Collision: Same-candle touch of both TP and SL triggers CONSERVATIVE_SL_FIRST -> Class 0.
5. Gap-Through-Stop: Bar opens beyond stop barrier.
6. Expiry Semantics (Neither Barrier Touched): Class 0.
7. Expiry Semantics (Price Exceeds 14 bps Hurdle without Barrier Touch): Class 0.
8. Directional Symmetry: Long and Short mirror scenarios produce symmetric outputs.
9. Partition Boundary Isolation: Last 12 bars are NaN to prevent crossing partition boundaries.
"""

from typing import List, Dict, Any, Optional
import pytest
import numpy as np
import pandas as pd

from backend.ml.labels import TripleBarrierLabeler, TargetLabel


def make_dummy_candles(rows: List[List[float]]) -> pd.DataFrame:
    """Helper to convert list of [open, high, low, close] into DataFrame."""
    open_times = [1700000000000 + i * 3600000 for i in range(len(rows))]
    close_times = [ot + 3599999 for ot in open_times]
    return pd.DataFrame({
        "open_time": open_times,
        "open": [r[0] for r in rows],
        "high": [r[1] for r in rows],
        "low": [r[2] for r in rows],
        "close": [r[3] for r in rows],
        "volume": [1000.0] * len(rows),
        "close_time": close_times
    })


def test_exact_barrier_formulas_and_slippage():
    """
    Audit A Conformance: Asserts the exact frozen Phase 5A.2 mathematical formulas:
    - Long entry:  O_{t+1} * (1 + 0.0002)
    - Short entry: O_{t+1} * (1 - 0.0002)
    - Long TP:  P_entry_long * (1 + 1.5 * delta_ATR + 0.0014)
    - Long SL:  P_entry_long * (1 - 1.0 * delta_ATR)
    - Short TP: P_entry_short * (1 - 1.5 * delta_ATR - 0.0014)
    - Short SL: P_entry_short * (1 + 1.0 * delta_ATR)
    """
    labeler = TripleBarrierLabeler(
        horizon_bars=12,
        profit_atr_mult=1.5,
        stop_atr_mult=1.0,
        friction_hurdle_bps=14.0,
        slippage_bps=2.0
    )

    open_next = 100.0
    close_t = 100.0
    atr_t = 2.0  # delta_ATR = 2.0 / 100.0 = 0.0200

    barriers = labeler.compute_barriers(open_next=open_next, close_t=close_t, atr_t=atr_t)

    # 1. Reference Entry Prices with 2.0 bps adverse slippage
    expected_entry_long = 100.0 * (1.0 + 0.0002)  # 100.0200
    expected_entry_short = 100.0 * (1.0 - 0.0002) # 99.9800
    assert pytest.approx(barriers["p_entry_long"], rel=1e-12) == expected_entry_long
    assert pytest.approx(barriers["p_entry_short"], rel=1e-12) == expected_entry_short

    # 2. Delta ATR
    assert pytest.approx(barriers["delta_atr"], rel=1e-12) == 0.0200

    # 3. Long Barriers
    # Long TP = 100.02 * (1 + 1.5 * 0.02 + 0.0014) = 100.02 * 1.0314 = 103.160628
    expected_long_tp = expected_entry_long * (1.0 + 1.5 * 0.02 + 0.0014)
    # Long SL = 100.02 * (1 - 1.0 * 0.02) = 100.02 * 0.98 = 98.0196
    expected_long_sl = expected_entry_long * (1.0 - 1.0 * 0.02)
    assert pytest.approx(barriers["long_tp"], rel=1e-12) == expected_long_tp
    assert pytest.approx(barriers["long_sl"], rel=1e-12) == expected_long_sl

    # 4. Short Barriers
    # Short TP = 99.98 * (1 - 1.5 * 0.02 - 0.0014) = 99.98 * 0.9686 = 96.840628
    expected_short_tp = expected_entry_short * (1.0 - 1.5 * 0.02 - 0.0014)
    # Short SL = 99.98 * (1 + 1.0 * 0.02) = 99.98 * 1.02 = 101.9796
    expected_short_sl = expected_entry_short * (1.0 + 1.0 * 0.02)
    assert pytest.approx(barriers["short_tp"], rel=1e-12) == expected_short_tp
    assert pytest.approx(barriers["short_sl"], rel=1e-12) == expected_short_sl


def test_triple_barrier_tp_first():
    """Verify clean Take Profit barrier hit before Stop Loss assigns Class +1."""
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    forward = [
        [100.0, 101.0, 99.5, 100.5],
        [100.5, 105.0, 100.0, 104.0],  # Long TP barrier reached
    ] + [[104.0, 104.5, 103.5, 104.0]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    assert labels.iloc[19] == TargetLabel.LONG_BREAKOUT


def test_triple_barrier_sl_first():
    """Verify Stop Loss hit before Take Profit assigns Class -1 (Short Breakout win)."""
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    forward = [
        [100.0, 100.5, 96.0, 97.0]     # Long SL hit and Short TP hit
    ] + [[97.0, 97.5, 96.5, 97.0]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    assert labels.iloc[19] == TargetLabel.SHORT_BREAKOUT


def test_triple_barrier_long_same_candle_collision_conservative_sl_first():
    """
    Phase 5B.2 Gate: In same-candle reach of both TP and SL, CONSERVATIVE_SL_FIRST
    causes the LONG stop-loss to trigger first -> Class -1 (BEARISH_DOWN / Long Stopout).
    """
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    forward = [
        [100.0, 110.0, 90.0, 100.0]    # Volatility spike touches both TP and SL
    ] + [[100.0, 100.5, 99.5, 100.0]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df, side="LONG")

    # Under CONSERVATIVE_SL_FIRST, Long SL triggers first -> -1
    assert labels.iloc[19] == TargetLabel.BEARISH_DOWN


def test_triple_barrier_short_same_candle_collision_conservative_sl_first():
    """
    Phase 5B.2 Gate: In same-candle reach of both TP and SL, CONSERVATIVE_SL_FIRST
    causes the SHORT stop-loss to trigger first -> Class +1 (BULLISH_UP / Short Stopout).
    """
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    forward = [
        [100.0, 110.0, 90.0, 100.0]    # Volatility spike touches both TP and SL
    ] + [[100.0, 100.5, 99.5, 100.0]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df, side="SHORT")

    # Under CONSERVATIVE_SL_FIRST, Short SL triggers first -> +1
    assert labels.iloc[19] == TargetLabel.BULLISH_UP


def test_triple_barrier_time_expiry_neither_barrier_touched():
    """Audit B Conformance: If neither barrier is touched within 12 bars, label is strictly Class 0."""
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    forward = [[100.0, 100.2, 99.8, 100.0]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    assert labels.iloc[19] == TargetLabel.NEUTRAL_EXPIRY


def test_price_movement_at_expiry_exceeding_14bps_without_barrier_touch():
    """
    Audit B Conformance: Price movement at expiry exceeding 14 bps without touching
    the ATR Take Profit barrier must still be assigned Class 0 (NEUTRAL_EXPIRY).
    """
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20

    # Over 12 bars, price drifts upward by +50 bps (Close = 100.50 > 100.0 + 14 bps),
    # but does NOT reach Long TP (103.16) and does NOT touch Long SL (98.02).
    forward = [[100.0 + i * 0.04, 100.0 + i * 0.04 + 0.1, 100.0 + i * 0.04 - 0.1, 100.0 + i * 0.04] for i in range(1, 16)]

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    # Under frozen Phase 5A.2 protocol, non-touch MUST produce NEUTRAL_EXPIRY (0)
    assert labels.iloc[19] == TargetLabel.NEUTRAL_EXPIRY


def test_triple_barrier_directional_symmetry():
    """
    Audit B Conformance: Proves exact directional symmetry between Long and Short.
    Mirroring upward and downward price trajectories yields symmetric +1 and -1 labels.
    """
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20

    # Scenario 1: Clean Upward Trend reaching Long TP
    forward_up = [
        [100.0, 101.0, 99.5, 100.5],
        [100.5, 104.5, 100.0, 104.0],
    ] + [[104.0, 104.5, 103.5, 104.0]] * 15

    df_up = make_dummy_candles(warmup + forward_up)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels_up = labeler.compute_labels(df_up)
    assert labels_up.iloc[19] == TargetLabel.LONG_BREAKOUT  # +1

    # Scenario 2: Clean Downward Trend reaching Short TP (mirror of up)
    forward_down = [
        [100.0, 100.5, 99.0, 99.5],
        [99.5, 100.0, 95.5, 96.0],
    ] + [[96.0, 96.5, 95.5, 96.0]] * 15

    df_down = make_dummy_candles(warmup + forward_down)
    labels_down = labeler.compute_labels(df_down)
    assert labels_down.iloc[19] == TargetLabel.SHORT_BREAKOUT # -1


def test_triple_barrier_gap_through_stop():
    """Verify gap-through stop handling when bar opens beyond stop barrier."""
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    forward = [
        [100.0, 100.5, 99.5, 100.0],
        [95.0, 95.5, 94.0, 94.5]      # Market gaps down through Long SL
    ] + [[94.5, 95.0, 94.0, 94.5]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    assert labels.iloc[19] == TargetLabel.SHORT_BREAKOUT


def test_triple_barrier_partition_boundary_isolation():
    """
    Audit E Conformance: Asserts that the last H=12 bars of any partition are
    assigned NaN, guaranteeing that label calculation never crosses fold boundaries.
    """
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 40
    df = make_dummy_candles(warmup)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    # Last 12 bars (indices 28 to 39) must be NaN
    assert labels.iloc[-12:].isna().all()
    # Prior bars should have non-NaN labels
    assert labels.iloc[19:28].notna().all()
