"""
VANTA Terminal — Synchronized Multi-Pair Stationary Block Bootstrap
===================================================================
Implements the institutional inference protocol specified in
docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md (Section 2):
1. Atomic Resampling Unit: 24-hour synchronous daily time slices across all pairs.
2. Stationary Block Length Distribution: Geometric distribution with p = 0.20 (mean 5 days).
3. Number of Replicates: B = 2,000.
4. Paired Resampling: Evaluates incremental ML vs Benchmark-0 performance (Delta_ML).
5. Robust Handling: Handles empty replicates and zero-division safely.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd


def build_daily_pnl_matrix(
    trades: List[Dict[str, Any]],
    start_ms: int,
    end_ms: int
) -> Tuple[np.ndarray, List[int]]:
    """
    Aggregates trade PnLs into a synchronous 1D daily net PnL array.
    Day index d = (exit_timestamp - start_ms) // 86_400_000.
    """
    total_days = max(1, int(np.ceil((end_ms - start_ms) / 86400000.0)))
    daily_pnl = np.zeros(total_days, dtype=np.float64)
    daily_trades = np.zeros(total_days, dtype=np.int64)
    daily_gross_win = np.zeros(total_days, dtype=np.float64)
    daily_gross_loss = np.zeros(total_days, dtype=np.float64)

    for tr in trades:
        exit_ts = tr.get("exit_time_ms", tr.get("exit_timestamp_ms", tr.get("timestamp_ms", 0)))
        if exit_ts < start_ms or exit_ts >= end_ms:
            continue
        day_idx = min(total_days - 1, max(0, int((exit_ts - start_ms) // 86400000)))
        net_pnl = tr.get("net_pnl", 0.0)
        daily_pnl[day_idx] += net_pnl
        daily_trades[day_idx] += 1
        if net_pnl > 0:
            daily_gross_win[day_idx] += net_pnl
        else:
            daily_gross_loss[day_idx] += abs(net_pnl)

    # Matrix columns: [daily_net_pnl, daily_trades_count, daily_gross_win, daily_gross_loss]
    matrix = np.column_stack([daily_pnl, daily_trades, daily_gross_win, daily_gross_loss])
    return matrix


def run_paired_stationary_bootstrap(
    ml_trades: List[Dict[str, Any]],
    benchmark_trades: List[Dict[str, Any]],
    start_ms: int,
    end_ms: int,
    num_replicates: int = 2000,
    expected_block_days: int = 5,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Executes paired synchronized stationary block bootstrap for ML Candidate vs Benchmark-0.
    """
    rng = np.random.default_rng(seed)
    p = 1.0 / expected_block_days

    mat_ml = build_daily_pnl_matrix(ml_trades, start_ms, end_ms)
    mat_bm = build_daily_pnl_matrix(benchmark_trades, start_ms, end_ms)

    T = len(mat_ml)
    if T == 0:
        return {}

    ml_pnl_reps = np.zeros(num_replicates, dtype=np.float64)
    bm_pnl_reps = np.zeros(num_replicates, dtype=np.float64)
    delta_pnl_reps = np.zeros(num_replicates, dtype=np.float64)

    ml_exp_reps = np.zeros(num_replicates, dtype=np.float64)
    bm_exp_reps = np.zeros(num_replicates, dtype=np.float64)
    delta_exp_reps = np.zeros(num_replicates, dtype=np.float64)

    ml_pf_reps = np.zeros(num_replicates, dtype=np.float64)
    bm_pf_reps = np.zeros(num_replicates, dtype=np.float64)
    delta_pf_reps = np.zeros(num_replicates, dtype=np.float64)

    for b in range(num_replicates):
        resampled_indices = []
        curr_idx = rng.integers(0, T)

        while len(resampled_indices) < T:
            resampled_indices.append(curr_idx)
            if rng.random() < p:
                curr_idx = rng.integers(0, T)
            else:
                curr_idx = (curr_idx + 1) % T

        sample_ml = mat_ml[resampled_indices]
        sample_bm = mat_bm[resampled_indices]

        # 1. Net PnL
        pnl_ml = float(sample_ml[:, 0].sum())
        pnl_bm = float(sample_bm[:, 0].sum())
        ml_pnl_reps[b] = pnl_ml
        bm_pnl_reps[b] = pnl_bm
        delta_pnl_reps[b] = pnl_ml - pnl_bm

        # 2. Expectancy (bps): (Net PnL / Total Trades / $1000 notional) * 10,000 or per trade
        n_tr_ml = sample_ml[:, 1].sum()
        n_tr_bm = sample_bm[:, 1].sum()
        exp_ml = (pnl_ml / (n_tr_ml * 1000.0) * 10000.0) if n_tr_ml > 0 else 0.0
        exp_bm = (pnl_bm / (n_tr_bm * 1000.0) * 10000.0) if n_tr_bm > 0 else 0.0
        ml_exp_reps[b] = exp_ml
        bm_exp_reps[b] = exp_bm
        delta_exp_reps[b] = exp_ml - exp_bm

        # 3. Profit Factor
        win_ml = sample_ml[:, 2].sum()
        loss_ml = sample_ml[:, 3].sum()
        pf_ml = (win_ml / loss_ml) if loss_ml > 0 else (10.0 if win_ml > 0 else 1.0)

        win_bm = sample_bm[:, 2].sum()
        loss_bm = sample_bm[:, 3].sum()
        pf_bm = (win_bm / loss_bm) if loss_bm > 0 else (10.0 if win_bm > 0 else 1.0)

        ml_pf_reps[b] = pf_ml
        bm_pf_reps[b] = pf_bm
        delta_pf_reps[b] = pf_ml - pf_bm

    # Compute percentiles
    def get_ci(arr: np.ndarray) -> Dict[str, float]:
        return {
            "mean": round(float(np.mean(arr)), 2),
            "median": round(float(np.median(arr)), 2),
            "std": round(float(np.std(arr)), 2),
            "ci_95_lower": round(float(np.percentile(arr, 2.5)), 2),
            "ci_95_upper": round(float(np.percentile(arr, 97.5)), 2),
        }

    p_value_pnl = float(np.mean(delta_pnl_reps <= 0.0))

    return {
        "num_replicates": num_replicates,
        "expected_block_days": expected_block_days,
        "seed": seed,
        "pnl_ml": get_ci(ml_pnl_reps),
        "pnl_bm": get_ci(bm_pnl_reps),
        "delta_pnl": get_ci(delta_pnl_reps),
        "delta_expectancy_bps": get_ci(delta_exp_reps),
        "delta_profit_factor": get_ci(delta_pf_reps),
        "p_value_one_tailed": round(p_value_pnl, 4),
        "statistically_significant": bool(np.percentile(delta_pnl_reps, 2.5) > 0.0)
    }
