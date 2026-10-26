"""
VANTA Terminal — Pre-Benchmark Implementation Gate Verification Tests
=====================================================================
Lightweight unit tests verifying:
1. Exact 12-configuration budget per candidate strategy.
2. Frozen qualification gate denominators (10 pairs) and zero-trade handling.
3. Holdout quarantine boundary timestamp protection.
4. 48-hour purge and embargo walk-forward semantics.
5. Baseline (14 bps) vs. Stress (21 bps) cost model replacement.
"""

import pytest
from datetime import datetime, timezone

from backend.strategy.configurations import (
    STRATEGY_A_GRID,
    STRATEGY_B_GRID,
    STRATEGY_C_GRID,
    get_strategy_grid
)
from backend.strategy.qualification import (
    QUALIFIED_PAIRS,
    PARTIAL_HISTORY_PAIRS,
    PairLifecycleState,
    evaluate_qualification_gates,
    calculate_net_expectancy_ci
)
from backend.data.loader import (
    HOLDOUT_CUTOFF_MS,
    PURGE_DURATION_MS,
    EMBARGO_DURATION_MS,
    is_in_quarantined_holdout,
    filter_candles_holdout_guard,
    generate_walk_forward_splits,
    QuarantinedHoldoutViolationError
)
from backend.backtest.costs import TransactionCostModel
from backend.backtest.schemas import OrderSide, OrderType


# =========================================================================
# 1. Parameter Grid Integrity Tests
# =========================================================================

def test_strategy_a_grid_exactly_twelve_configurations():
    grid = get_strategy_grid("STRAT-SWEEP-01")
    assert len(grid) == 12
    unique_ids = set(c.config_id for c in grid)
    assert len(unique_ids) == 12
    # Verify baseline config is A-01
    assert grid[0].config_id == "A-01"
    assert grid[0].lookback_n == 20
    assert grid[0].sweep_delta == 0.10
    assert grid[0].risk_reward == 2.0


def test_strategy_b_grid_exactly_twelve_configurations():
    grid = get_strategy_grid("STRAT-BREAK-01")
    assert len(grid) == 12
    unique_ids = set(c.config_id for c in grid)
    assert len(unique_ids) == 12
    # Verify baseline config is B-01
    assert grid[0].config_id == "B-01"
    assert grid[0].channel_m == 20
    assert grid[0].volume_mult == 1.20
    assert grid[0].ema_filter == 50


def test_strategy_c_grid_exactly_twelve_configurations():
    grid = get_strategy_grid("STRAT-MEAN-01")
    assert len(grid) == 12
    unique_ids = set(c.config_id for c in grid)
    assert len(unique_ids) == 12
    # Verify baseline config is C-01
    assert grid[0].config_id == "C-01"
    assert grid[0].band_len == 20
    assert grid[0].band_std == 2.0
    assert grid[0].rsi_oversold == 30.0
    assert grid[0].rsi_overbought == 70.0


def test_unknown_strategy_raises_error():
    with pytest.raises(ValueError, match="Unknown strategy family"):
        get_strategy_grid("UNKNOWN-STRATEGY")


# =========================================================================
# 2. Pair Eligibility and Qualification Gate Denominator Tests
# =========================================================================

def test_gate_denominators_and_zero_trade_handling():
    # Setup: 10 qualified pairs
    assert len(QUALIFIED_PAIRS) == 10
    assert "XMRUSDT" not in QUALIFIED_PAIRS
    assert "XMRUSDT" in PARTIAL_HISTORY_PAIRS

    # Case A: Ideal candidate passing all gates
    pair_trades_perfect = {
        sym: [10.0] * 25 for sym in QUALIFIED_PAIRS
    }
    pair_trades_perfect["XMRUSDT"] = [5.0] * 10  # auxiliary

    res_perfect = evaluate_qualification_gates(
        strategy_id="TEST-PERFECT",
        max_drawdown_pct=10.0,
        trade_notionals=[1000.0] * 250,
        net_pnls=[10.0] * 250,
        pair_trades=pair_trades_perfect,
        fold_net_pnls=[500.0, 600.0, 700.0],
        stress_net_pnl=1200.0,
        stress_profit_factor=1.45
    )
    assert res_perfect.certified_baseline is True
    assert res_perfect.status == "QUALIFIED_BASELINE"

    # Case B: One pair has 0 trades -> must fail GATE-5, count as FAIL in GATE-7
    pair_trades_with_zero = {sym: [10.0] * 25 for sym in QUALIFIED_PAIRS}
    pair_trades_with_zero["ADAUSDT"] = []  # Zero trades for ADAUSDT

    res_zero = evaluate_qualification_gates(
        strategy_id="TEST-ZERO-TRADE",
        max_drawdown_pct=10.0,
        trade_notionals=[1000.0] * 225,
        net_pnls=[10.0] * 225,
        pair_trades=pair_trades_with_zero,
        fold_net_pnls=[500.0, 600.0, 700.0],
        stress_net_pnl=1200.0,
        stress_profit_factor=1.45
    )
    # GATE-5 must fail because ADAUSDT has 0 trades (< 20)
    g5 = next(g for g in res_zero.gates if g.gate_id == "GATE-5")
    assert g5.passed is False
    assert "ADAUSDT" in g5.details
    assert res_zero.pair_states["ADAUSDT"] == PairLifecycleState.INSUFFICIENT_SAMPLE

    # GATE-7: ADAUSDT counts as FAIL, but other 9 pairs pass -> 9 of 10 passed
    g7 = next(g for g in res_zero.gates if g.gate_id == "GATE-7")
    assert g7.passed is True
    assert "9 of 10 pairs" in g7.observed_value
    assert g7.denominator == "10 Qualified Pairs (Frozen Denominator)"

    # But overall status is NO_QUALIFIED_STRATEGY because GATE-5 failed!
    assert res_zero.certified_baseline is False
    assert res_zero.status == "NO_QUALIFIED_STRATEGY"
    assert "MANDATORY FALLBACK TRIGGERED" in res_zero.fallback_notice


def test_insufficient_sample_cannot_shrink_spatial_denominator():
    # If 4 pairs have insufficient sample (< 20 trades), only 6 pass -> GATE-7 must fail (6 < 7)
    pair_trades_sparse = {sym: [10.0] * 25 for sym in QUALIFIED_PAIRS}
    pair_trades_sparse["ADAUSDT"] = [5.0] * 5  # 5 trades
    pair_trades_sparse["AVAXUSDT"] = [5.0] * 12 # 12 trades
    pair_trades_sparse["LINKUSDT"] = []        # 0 trades
    pair_trades_sparse["DOGEUSDT"] = [5.0] * 8  # 8 trades

    res_sparse = evaluate_qualification_gates(
        strategy_id="TEST-SPARSE",
        max_drawdown_pct=12.0,
        trade_notionals=[1000.0] * 175,
        net_pnls=[10.0] * 175,
        pair_trades=pair_trades_sparse,
        fold_net_pnls=[200.0, 300.0, 400.0],
        stress_net_pnl=500.0,
        stress_profit_factor=1.20
    )
    g7 = next(g for g in res_sparse.gates if g.gate_id == "GATE-7")
    assert g7.passed is False
    # Exactly 6 of 10 passed
    assert "6 of 10 pairs" in g7.observed_value
    assert g7.denominator == "10 Qualified Pairs (Frozen Denominator)"


# =========================================================================
# 3. Holdout Quarantine Timestamp Guard Tests
# =========================================================================

def test_holdout_boundary_timestamp_protection():
    # Exactly 2026-04-26T00:00:00Z in ms
    cutoff = HOLDOUT_CUTOFF_MS
    fifteen_min_ms = 15 * 60 * 1000  # 900,000 ms

    t_before = cutoff - fifteen_min_ms  # 2026-04-25 23:45:00 UTC
    t_exact = cutoff                   # 2026-04-26 00:00:00 UTC
    t_after = cutoff + fifteen_min_ms   # 2026-04-26 00:15:00 UTC

    # 1. is_in_quarantined_holdout boolean check
    assert is_in_quarantined_holdout(t_before) is False
    assert is_in_quarantined_holdout(t_exact) is True
    assert is_in_quarantined_holdout(t_after) is True

    # 2. Filter test
    dummy_candles = [
        [t_before, 100.0, 105.0, 95.0, 102.0, 10.0, t_before + 899999],
        [t_exact, 102.0, 106.0, 101.0, 104.0, 12.0, t_exact + 899999],
        [t_after, 104.0, 108.0, 103.0, 107.0, 15.0, t_after + 899999],
    ]
    filtered = filter_candles_holdout_guard(dummy_candles, raise_on_holdout_access=False)
    assert len(filtered) == 1
    assert filtered[0][0] == t_before

    # 3. Raise exception check when holdout attempted
    with pytest.raises(QuarantinedHoldoutViolationError, match="CRITICAL SECURITY GUARD"):
        filter_candles_holdout_guard(dummy_candles, raise_on_holdout_access=True)

    # 4. Split generator holdout breach check
    with pytest.raises(QuarantinedHoldoutViolationError, match="breaches holdout boundary"):
        generate_walk_forward_splits(
            candles=dummy_candles,
            is_start_ms=t_before - 10000000,
            is_end_ms=t_before,
            oos_end_ms=t_after  # Breaches holdout
        )


# =========================================================================
# 4. Walk-Forward Boundary, Purge & Embargo Semantics
# =========================================================================

def test_walk_forward_48h_purge_and_embargo():
    # 48 hours = 172,800,000 ms
    assert PURGE_DURATION_MS == 48 * 3600 * 1000
    assert EMBARGO_DURATION_MS == 48 * 3600 * 1000

    # On 15m (900,000 ms): 172,800,000 / 900,000 = 192 bars
    bars_15m = PURGE_DURATION_MS / (15 * 60 * 1000)
    assert bars_15m == 192.0

    # On 1H (3,600,000 ms): 172,800,000 / 3,600,000 = 48 bars
    bars_1h = PURGE_DURATION_MS / (3600 * 1000)
    assert bars_1h == 48.0

    # Generate split verify cutoffs
    t_split = 1730000000000
    splits = generate_walk_forward_splits(
        candles=[],
        is_start_ms=t_split - (365 * 24 * 3600 * 1000),
        is_end_ms=t_split,
        oos_end_ms=t_split + (180 * 24 * 3600 * 1000)
    )
    assert splits["is_signal_cutoff_ms"] == t_split - PURGE_DURATION_MS
    assert splits["oos_signal_start_ms"] == t_split + EMBARGO_DURATION_MS


# =========================================================================
# 5. Cost Model & Stress Replacement Semantics
# =========================================================================

def test_cost_model_baseline_and_stress_replacement():
    # Baseline: 5.0 bps taker fee, 2.0 bps slippage
    baseline_model = TransactionCostModel(
        maker_fee_bps=2.0,
        taker_fee_bps=5.0,
        slippage_bps=2.0
    )
    # Entry Buy: slippage is adverse (+2.0 bps)
    entry_fill, entry_slip = baseline_model.calculate_slippage(100.0, OrderSide.BUY, OrderType.MARKET)
    assert entry_fill == 100.02
    assert entry_slip == pytest.approx(0.02, rel=1e-5)

    # Entry Fee: 5.0 bps on fill notional
    entry_fee = baseline_model.calculate_fee(entry_fill * 1.0, is_maker=False)
    assert entry_fee == pytest.approx(0.05001, rel=1e-5)

    # Exit Sell: slippage is adverse (-2.0 bps)
    exit_fill, exit_slip = baseline_model.calculate_slippage(110.0, OrderSide.SELL, OrderType.MARKET)
    assert exit_fill == pytest.approx(109.978, rel=1e-5)
    assert exit_slip == pytest.approx(0.022, rel=1e-5)

    # Exit Fee: 5.0 bps on fill notional
    exit_fee = baseline_model.calculate_fee(exit_fill * 1.0, is_maker=False)
    assert exit_fee == pytest.approx(0.054989, rel=1e-5)

    # Total round-trip drag ~ 14.0 bps
    total_friction = entry_fee + exit_fee + entry_slip + exit_slip
    # Baseline total friction is ~0.147 USDT on ~100-110 USDT notional = ~14 bps
    assert 0.14 <= (total_friction / 100.0) * 100 <= 0.15

    # Stress Test: 7.5 bps fee, 3.0 bps slippage
    # MUST REPLACE baseline values, NOT stack on top
    stress_model = TransactionCostModel(
        maker_fee_bps=3.0,
        taker_fee_bps=7.5,
        slippage_bps=3.0
    )
    assert stress_model.taker_fee_rate == 0.00075
    assert stress_model.slippage_rate == 0.00030
    s_entry_fill, s_entry_slip = stress_model.calculate_slippage(100.0, OrderSide.BUY, OrderType.MARKET)
    assert s_entry_fill == 100.03
    assert s_entry_slip == pytest.approx(0.03, rel=1e-5)

    s_entry_fee = stress_model.calculate_fee(s_entry_fill * 1.0, is_maker=False)
    assert s_entry_fee == pytest.approx(0.0750225, rel=1e-5)
