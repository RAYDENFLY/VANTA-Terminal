"""
VANTA Terminal — Triple Barrier Target Deterministic Tests (Phase 5B)
====================================================================
Tests the deterministic target labeling engine (TARGET-C-BARRIER) against all
required barrier interaction invariants:
1. TP-First: Price reaches Take Profit barrier before Stop Loss -> Class +1.
2. SL-First: Price reaches Stop Loss barrier before Take Profit -> Class 0 (or -1 for Short).
3. Collision: Same-candle touch of both TP and SL triggers CONSERVATIVE_SL_FIRST.
4. Gap-Through-Stop: Bar opens beyond stop barrier.
5. Time Expiry: Neither barrier reached within 12 bars -> Class 0.
6. Execution Timing: Entry reference price starts at bar t+1 Open with slippage.
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


def test_triple_barrier_tp_first():
    """Verify clean Take Profit barrier hit before Stop Loss assigns Class +1."""
    # We create 20 warmup bars (price = 100, ATR ~ 2.0)
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    # Prediction at bar 19 (close = 100.0, ATR ~ 2.0)
    # Entry at bar 20 Open = 100.0
    # Long TP barrier is ~ 100 * (1 + 1.5 * (2/100) + 0.0014) = 103.14
    # Long SL barrier is ~ 100 * (1 - 1.0 * (2/100)) = 98.0
    # Forward path:
    # Bar 20: Open 100, High 101, Low 99.5, Close 100.5
    # Bar 21: Open 100.5, High 105.0 (TP reached!), Low 100.0, Close 104.0
    # Bars 22-35: neutral
    forward = [
        [100.0, 101.0, 99.5, 100.5],
        [100.5, 105.0, 100.0, 104.0],
    ] + [[104.0, 104.5, 103.5, 104.0]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    # Label at bar 19 must be +1 (LONG_BREAKOUT)
    assert labels.iloc[19] == TargetLabel.LONG_BREAKOUT


def test_triple_barrier_sl_first():
    """Verify Stop Loss hit before Take Profit assigns Class 0 (or Short win)."""
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    # Prediction at bar 19.
    # Bar 20: Open 100, High 100.5, Low 96.0 (Long SL hit, Short TP hit!), Close 97.0
    forward = [
        [100.0, 100.5, 96.0, 97.0]
    ] + [[97.0, 97.5, 96.5, 97.0]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    # In this scenario, price dropped to 96.0, reaching Short TP -> Short Breakout wins!
    assert labels.iloc[19] == TargetLabel.SHORT_BREAKOUT


def test_triple_barrier_same_candle_collision_conservative_sl_first():
    """Verify CONSERVATIVE_SL_FIRST: Same-candle reach of both TP and SL triggers Stop Loss."""
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    # Prediction at bar 19.
    # Bar 20: Huge volatility spike: Open 100, High 110.0 (touches TP), Low 90.0 (touches SL), Close 100
    forward = [
        [100.0, 110.0, 90.0, 100.0]
    ] + [[100.0, 100.5, 99.5, 100.0]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    # Both Long and Short experience same-candle collision.
    # Under CONSERVATIVE_SL_FIRST, both side trades are stopped out!
    # Therefore, neither side wins TP -> label must be NEUTRAL_EXPIRY (0).
    assert labels.iloc[19] == TargetLabel.NEUTRAL_EXPIRY


def test_triple_barrier_time_expiry():
    """Verify that if neither barrier is touched within 12 bars, label is Class 0."""
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    # Tight range: price stays between 99.8 and 100.2 for 15 bars
    forward = [[100.0, 100.2, 99.8, 100.0]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    # Never reached either TP (103.14) or SL (98.0) within 12 bars
    assert labels.iloc[19] == TargetLabel.NEUTRAL_EXPIRY


def test_triple_barrier_gap_through_stop():
    """Verify gap-through stop handling when bar opens beyond stop barrier."""
    warmup = [[100.0, 101.0, 99.0, 100.0]] * 20
    # Prediction at bar 19 (Close = 100.0, ATR ~ 2.0)
    # Bar 20: Entry at Open = 100.0 (Long entry ~100.02, Long SL ~98.02; Short entry ~99.98, Short TP ~96.84)
    # Bar 21: Market gaps down violently at Open = 95.0 (gaps through Long SL and triggers Short TP!)
    forward = [
        [100.0, 100.5, 99.5, 100.0],
        [95.0, 95.5, 94.0, 94.5]
    ] + [[94.5, 95.0, 94.0, 94.5]] * 15

    df = make_dummy_candles(warmup + forward)
    labeler = TripleBarrierLabeler(horizon_bars=12)
    labels = labeler.compute_labels(df)

    # Long stops out on gap down; Short reaches TP -> Short Breakout wins (-1)
    assert labels.iloc[19] == TargetLabel.SHORT_BREAKOUT
