"""
VANTA Terminal — Chained Equity & Multi-Fold MDD Calculator (Phase 5B)
=====================================================================
Implements the mathematically continuous chained equity formula specified in
docs/PHASE_5A2_FINAL_PROTOCOL_INTEGRITY_CHECK.md (Section 4).

Features:
1. Strict equity continuity across independent $10,000 fold boundaries.
2. Multiplicative return compounding: K_f = prod_{k=1}^{f-1} (1 + NetPnL_k / 10000).
3. Full chained candle-level MTM drawdown tracking from cumulative high-watermark.
4. Robust division-by-zero protection and bankruptcy clamping.
"""

from typing import List, Dict, Any, Tuple
import numpy as np


def build_chained_equity_curve(
    fold_curves: List[List[float]],
    fold_net_pnls: List[float],
    initial_equity: float = 10000.0
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Constructs the continuous chained equity curve across multiple walk-forward folds.

    Parameters:
    - fold_curves: List of lists containing instantaneous equity points for each fold.
                   Each fold curve must start with initial_equity ($10,000).
    - fold_net_pnls: Net dollar PnL of each completed fold (including boundary flatten costs).
    - initial_equity: Base starting capital (default $10,000.00).

    Returns:
    - chained_equity: 1D numpy array of the continuous compounded equity curve.
    - chained_drawdowns: 1D numpy array of percentage drawdowns from the global high-watermark.
    - chained_mdd_pct: Maximum peak-to-trough mark-to-market drawdown percentage.
    """
    num_folds = len(fold_curves)
    if num_folds == 0:
        return np.array([]), np.array([]), 0.0

    if len(fold_net_pnls) != num_folds:
        raise ValueError(f"Length mismatch: {num_folds} fold curves but {len(fold_net_pnls)} net PnLs provided.")

    chained_segments = []
    current_multiplier = 1.0

    for f_idx in range(num_folds):
        curve = np.array(fold_curves[f_idx], dtype=np.float64)
        if len(curve) == 0:
            continue

        # Scale fold curve by current cumulative compounding multiplier
        scaled_segment = curve * current_multiplier
        chained_segments.append(scaled_segment)

        # Update multiplier for the NEXT fold using this fold's completed net return
        fold_pnl = fold_net_pnls[f_idx]
        fold_return = fold_pnl / initial_equity
        # Guard against multiplier collapsing below 0
        current_multiplier = max(0.0, current_multiplier * (1.0 + fold_return))

    if not chained_segments:
        return np.array([]), np.array([]), 0.0

    chained_equity = np.concatenate(chained_segments)

    # Compute continuous Mark-to-Market Drawdown from cumulative high-watermark
    n_points = len(chained_equity)
    hwm = initial_equity
    drawdowns = np.zeros(n_points, dtype=np.float64)
    max_dd = 0.0

    for i in range(n_points):
        val = chained_equity[i]
        if val <= 0.0:
            # Bankruptcy clamp
            drawdowns[i] = 100.0
            max_dd = 100.0
            continue

        if val > hwm:
            hwm = val

        if hwm > 0.0:
            dd = ((hwm - val) / hwm) * 100.0
            drawdowns[i] = dd
            if dd > max_dd:
                max_dd = dd

    return chained_equity, drawdowns, round(float(max_dd), 4)
