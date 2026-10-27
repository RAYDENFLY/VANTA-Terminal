"""
VANTA Terminal — Chained Equity & Portfolio Accounting Acceptance Tests (Phase 5B)
=================================================================================
Validates the mathematical properties of the multi-fold chained equity curve:
1. Strict equity continuity at fold transition boundaries (no jump discontinuity).
2. Proper compounding of independently reset $10,000 folds.
3. Accounting for boundary flatten costs within fold net PnL.
4. Chained MDD correctly captures drawdowns relative to peaks established in prior folds.
5. Zero-return and negative-return fold transitions.
6. Numerical safety against division by zero and extreme capital loss.
"""

import pytest
import numpy as np

from backend.ml.chained_equity import build_chained_equity_curve


def test_chained_equity_boundary_continuity():
    """Verify that E_chained is strictly continuous at fold transitions."""
    # Fold 1: Starts at 10,000, grows to 11,000 (+$1,000 PnL, R1 = +10%)
    f1_curve = [10000.0, 10500.0, 11000.0]
    f1_pnl = 1000.0

    # Fold 2: Starts at 10,000, grows to 10,500 (+$500 PnL, R2 = +5%)
    f2_curve = [10000.0, 10200.0, 10500.0]
    f2_pnl = 500.0

    chained_eq, dds, mdd = build_chained_equity_curve(
        fold_curves=[f1_curve, f2_curve],
        fold_net_pnls=[f1_pnl, f2_pnl],
        initial_equity=10000.0
    )

    assert len(chained_eq) == 6
    # Last point of Fold 1
    f1_end = chained_eq[2]
    # First point of Fold 2
    f2_start = chained_eq[3]

    assert pytest.approx(f1_end, abs=1e-4) == 11000.0
    assert pytest.approx(f2_start, abs=1e-4) == 11000.0  # 10,000 * 1.10 = 11,000!
    assert pytest.approx(f1_end, abs=1e-4) == f2_start    # Strict mathematical continuity!


def test_chained_equity_negative_and_zero_return_folds():
    """Verify transitions with losing and flat folds."""
    # Fold 1: Drops from 10k to 9k (-$1,000 PnL, R1 = -10%)
    f1_curve = [10000.0, 9500.0, 9000.0]
    f1_pnl = -1000.0

    # Fold 2: Flat fold: starts at 10k, ends at 10k ($0 PnL, R2 = 0%)
    f2_curve = [10000.0, 10100.0, 10000.0]
    f2_pnl = 0.0

    # Fold 3: Gains +20%: starts at 10k, ends at 12k (+$2,000 PnL)
    f3_curve = [10000.0, 11000.0, 12000.0]
    f3_pnl = 2000.0

    chained_eq, dds, mdd = build_chained_equity_curve(
        fold_curves=[f1_curve, f2_curve, f3_curve],
        fold_net_pnls=[f1_pnl, f2_pnl, f3_pnl],
        initial_equity=10000.0
    )

    # Check continuity at Fold 1 -> Fold 2
    assert pytest.approx(chained_eq[2], abs=1e-4) == 9000.0
    assert pytest.approx(chained_eq[3], abs=1e-4) == 9000.0

    # Check continuity at Fold 2 -> Fold 3
    assert pytest.approx(chained_eq[5], abs=1e-4) == 9000.0
    assert pytest.approx(chained_eq[6], abs=1e-4) == 9000.0

    # Final equity: 10,000 * 0.90 * 1.0 * 1.20 = 10,800.0
    assert pytest.approx(chained_eq[-1], abs=1e-4) == 10800.0


def test_chained_mdd_captures_prior_fold_peaks():
    """
    Verify that chained MDD correctly evaluates drawdowns against peaks established
    in prior folds.
    """
    # Fold 1: Peaks at 12,000, ends at 12,000 (+$2,000 PnL, R1 = +20%)
    f1_curve = [10000.0, 11000.0, 12000.0]
    f1_pnl = 2000.0

    # Fold 2: Starts at 10,000, crashes to 8,000, ends at 8,000 (-$2,000 PnL)
    # Scaled curve in Fold 2: starts at 12,000, drops to 12,000 * 0.8 = 9,600!
    # Drawdown from peak (12,000): (12000 - 9600)/12000 = 2400 / 12000 = 20.0%!
    f2_curve = [10000.0, 9000.0, 8000.0]
    f2_pnl = -2000.0

    chained_eq, dds, mdd = build_chained_equity_curve(
        fold_curves=[f1_curve, f2_curve],
        fold_net_pnls=[f1_pnl, f2_pnl],
        initial_equity=10000.0
    )

    assert pytest.approx(mdd, abs=1e-2) == 20.00


def test_chained_equity_bankruptcy_clamping():
    """Verify numerical safety and 100% MDD clamping if a fold experiences bankruptcy."""
    # Fold 1: Equity crashes to 0
    f1_curve = [10000.0, 5000.0, 0.0]
    f1_pnl = -10000.0

    # Fold 2: Even if fold 2 curve is provided, multiplier is clamped to 0
    f2_curve = [10000.0, 10500.0]
    f2_pnl = 500.0

    chained_eq, dds, mdd = build_chained_equity_curve(
        fold_curves=[f1_curve, f2_curve],
        fold_net_pnls=[f1_pnl, f2_pnl],
        initial_equity=10000.0
    )

    assert mdd == 100.0
    assert chained_eq[2] == 0.0
    assert chained_eq[3] == 0.0


def test_chained_equity_boundary_flatten_cost_inclusion():
    """
    Audit F Conformance: Verify that boundary flatten costs incurred when flattening
    open positions at fold boundaries are reflected in fold_net_pnls and compounded.
    """
    # Gross trading PnL was +$1,000, but boundary flatten cost $3.50 was deducted -> net PnL = $996.50
    f1_curve = [10000.0, 10500.0, 10996.50]
    f1_net_pnl = 996.50

    f2_curve = [10000.0, 10100.0]
    f2_net_pnl = 100.0

    chained_eq, dds, mdd = build_chained_equity_curve(
        fold_curves=[f1_curve, f2_curve],
        fold_net_pnls=[f1_net_pnl, f2_net_pnl],
        initial_equity=10000.0
    )

    expected_f2_start = 10000.0 * (1.0 + 996.50 / 10000.0) # 10,996.50
    assert pytest.approx(chained_eq[2], abs=1e-4) == expected_f2_start
    assert pytest.approx(chained_eq[3], abs=1e-4) == expected_f2_start
