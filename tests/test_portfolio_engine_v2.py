"""
VANTA Terminal — Phase 4B.4 Portfolio Engine V2 Integration & Validation Test Suite
===================================================================================
Tests the canonical multi-pair shared-margin engine against the 12 required invariants:
1. Shared capital across multiple symbols.
2. Chronological interleaving of pair events.
3. Deterministic ordering of equal-timestamp events.
4. Simultaneous exits and entries.
5. Capital rejection when free collateral is insufficient.
6. Open-position mark-to-market drawdown.
7. Gap-through-stop and same-candle SL/TP ambiguity.
8. Fees and slippage reconciliation.
9. Bankruptcy and zero-equity behavior.
10. Fold resets and boundary flattening.
11. Missing funding data exception guard.
12. Identical outputs and checksums on deterministic replay.
"""

import pytest
import math
import hashlib
import json
from typing import List, Dict, Any, Optional

from backend.backtest.schemas import (
    PositionSide,
    ExitReason,
    OrderSide,
    OrderType,
    ExecutionPolicy
)
from backend.backtest.events import BarEvent, SignalEvent
from backend.backtest.portfolio_engine import (
    CanonicalPortfolioEngine,
    PortfolioEngineConfig,
    PortfolioRunResult
)
from backend.backtest.event_queue import MultiStreamEventQueue, BarFrame
from backend.backtest.funding import FundingDataMissingException
from backend.backtest.position import PositionTracker


# ============================================================================
# Synthetic Strategy Fixtures
# ============================================================================

class MockMultiStrategy:
    """Configurable synthetic strategy for deterministic integration testing."""
    def __init__(self, symbol: str, signal_plan: Dict[int, SignalEvent]):
        self.symbol = symbol
        self.signal_plan = signal_plan

    def on_bar(self, bar: BarEvent, position: PositionTracker) -> Optional[SignalEvent]:
        return self.signal_plan.get(bar.bar_index)


def make_candle(open_time: int, o: float, h: float, l: float, c: float, v: float = 1000.0, close_time: Optional[int] = None) -> List[Any]:
    ct = close_time if close_time is not None else (open_time + 3600000 - 1)
    return [open_time, o, h, l, c, v, ct]


# ============================================================================
# 12 Integration Test Invariants
# ============================================================================

def test_1_shared_capital_across_multiple_symbols():
    """Verify that multiple pairs draw capital from a single shared $10,000 pool."""
    cfg = PortfolioEngineConfig(initial_equity=10000.0, target_position_pct=10.0, max_leverage=1.0)
    engine = CanonicalPortfolioEngine(cfg)

    # 3 bars: BTC and ETH
    btc_candles = [
        make_candle(1000, 50000, 50100, 49900, 50000),
        make_candle(2000, 50000, 50100, 49900, 50000),
        make_candle(3000, 50000, 50100, 49900, 50000)
    ]
    eth_candles = [
        make_candle(1000, 3000, 3010, 2990, 3000),
        make_candle(2000, 3000, 3010, 2990, 3000),
        make_candle(3000, 3000, 3010, 2990, 3000)
    ]

    # Signal on bar 0 for both: buy at bar 1 Open
    sig_btc = {0: SignalEvent(timestamp_ms=1000, symbol="BTCUSDT", direction=PositionSide.LONG)}
    sig_eth = {0: SignalEvent(timestamp_ms=1000, symbol="ETHUSDT", direction=PositionSide.LONG)}

    def factory(sym):
        return MockMultiStrategy(sym, sig_btc if sym == "BTCUSDT" else sig_eth)

    res = engine.run({"BTCUSDT": btc_candles, "ETHUSDT": eth_candles}, factory)

    # Both positions opened: ~$1,000 notional each
    assert "BTCUSDT" in res.trades_count_by_symbol or len(res.trade_ledger) == 2
    # Check that free collateral was reduced by both positions (~$2,000 reserved)
    eq_pt = res.equity_curve[1] # Bar 1 close
    assert pytest.approx(eq_pt.reserved_margin, abs=50.0) == 2000.0
    assert pytest.approx(eq_pt.free_collateral, abs=50.0) == 8000.0


def test_2_chronological_interleaving_of_pair_events():
    """Verify that events across multiple pairs advance in lockstep chronologically."""
    btc_candles = [make_candle(1000, 100, 105, 95, 100), make_candle(2000, 100, 105, 95, 100)]
    eth_candles = [make_candle(1000, 200, 205, 195, 200), make_candle(2000, 200, 205, 195, 200)]

    queue = MultiStreamEventQueue({"BTCUSDT": btc_candles, "ETHUSDT": eth_candles})
    frames = list(queue.iter_frames())

    assert len(frames) == 2
    assert frames[0].timestamp_ms == 1000
    assert frames[1].timestamp_ms == 2000
    assert set(frames[0].bars.keys()) == {"BTCUSDT", "ETHUSDT"}
    assert set(frames[1].bars.keys()) == {"BTCUSDT", "ETHUSDT"}


def test_3_deterministic_ordering_of_equal_timestamp_events():
    """Verify deterministic tie-breaking: confidence -> volume -> symbol."""
    sig_a = SignalEvent(timestamp_ms=1000, symbol="SOLUSDT", direction=PositionSide.LONG, tag="A")
    sig_b = SignalEvent(timestamp_ms=1000, symbol="ADAUSDT", direction=PositionSide.LONG, tag="B")
    sig_c = SignalEvent(timestamp_ms=1000, symbol="BTCUSDT", direction=PositionSide.LONG, tag="C")

    # Set confidence or volumes: SOL (vol=100), ADA (vol=200), BTC (vol=200)
    # Between ADA and BTC (equal vol), ADA precedes BTC alphabetically
    vols = {"SOLUSDT": 100.0, "ADAUSDT": 200.0, "BTCUSDT": 200.0}
    sorted_sigs = MultiStreamEventQueue.sort_signals_deterministically([sig_a, sig_b, sig_c], vols)

    assert sorted_sigs[0].symbol == "ADAUSDT"
    assert sorted_sigs[1].symbol == "BTCUSDT"
    assert sorted_sigs[2].symbol == "SOLUSDT"


def test_4_simultaneous_exits_and_entries():
    """Verify that exits executed at bar Open free collateral for entries executed at the same bar Open."""
    cfg = PortfolioEngineConfig(initial_equity=10000.0, target_position_pct=100.0, max_leverage=1.0) # 100% margin
    engine = CanonicalPortfolioEngine(cfg)

    btc_candles = [
        make_candle(1000, 100, 105, 95, 100),
        make_candle(2000, 100, 105, 95, 100),
        make_candle(3000, 100, 105, 95, 100)
    ]
    eth_candles = [
        make_candle(1000, 200, 205, 195, 200),
        make_candle(2000, 200, 205, 195, 200),
        make_candle(3000, 200, 205, 195, 200)
    ]

    # Bar 0: Enter BTC (uses 100% collateral)
    # Bar 1: Exit BTC, and Enter ETH
    # Bar 2: Hold ETH
    sig_btc = {
        0: SignalEvent(timestamp_ms=1000, symbol="BTCUSDT", direction=PositionSide.LONG),
        1: SignalEvent(timestamp_ms=2000, symbol="BTCUSDT", direction=PositionSide.FLAT)
    }
    sig_eth = {
        1: SignalEvent(timestamp_ms=2000, symbol="ETHUSDT", direction=PositionSide.LONG)
    }

    def factory(sym):
        return MockMultiStrategy(sym, sig_btc if sym == "BTCUSDT" else sig_eth)

    res = engine.run({"BTCUSDT": btc_candles, "ETHUSDT": eth_candles}, factory)

    # ETH entry should succeed because BTC exit at bar 1 Open released margin before ETH entered
    assert len(res.trade_ledger) == 2
    symbols_traded = [t.symbol for t in res.trade_ledger]
    assert "BTCUSDT" in symbols_traded
    assert "ETHUSDT" in symbols_traded
    assert res.rejected_orders_count == 0


def test_5_capital_rejection_when_free_collateral_is_insufficient():
    """Verify that orders exceeding available free collateral are cleanly rejected with INSUFFICIENT_COLLATERAL."""
    # Sizing = 50% per position, max leverage = 1.0x -> max 2 positions
    cfg = PortfolioEngineConfig(initial_equity=10000.0, target_position_pct=50.0, max_leverage=1.0)
    engine = CanonicalPortfolioEngine(cfg)

    candles = [
        make_candle(1000, 100, 105, 95, 100),
        make_candle(2000, 100, 105, 95, 100),
        make_candle(3000, 100, 105, 95, 100)
    ]

    # 3 pairs signal simultaneously at bar 0
    symbols = ["PAIR_A", "PAIR_B", "PAIR_C"]
    raw_datasets = {s: candles for s in symbols}

    def factory(sym):
        return MockMultiStrategy(sym, {0: SignalEvent(timestamp_ms=1000, symbol=sym, direction=PositionSide.LONG)})

    res = engine.run(raw_datasets, factory)

    # First two should succeed (~$5,000 each = 100% margin). Third must be rejected!
    assert res.rejected_orders_count >= 1
    rejected = res.rejected_orders[0]
    assert rejected.reason == "INSUFFICIENT_COLLATERAL"
    assert rejected.symbol == "PAIR_C"


def test_6_open_position_mark_to_market_drawdown():
    """Verify candle-level mark-to-market drawdown reflects unrealized losses during holding periods."""
    cfg = PortfolioEngineConfig(initial_equity=10000.0, target_position_pct=50.0, max_leverage=1.0)
    engine = CanonicalPortfolioEngine(cfg)

    # Bar 0: Signal emitted at close of bar 0
    # Bar 1: Fills Long at Open=100.0, price closes at 80.0 (20% loss on $5,000 position = -$1,000 unrealized, ~10% MTM DD)
    # Bar 2: Price recovers to Open=80.0, Close=100.0 (unrealized loss erased before exit)
    candles = [
        make_candle(1000, 100, 105, 95, 100),
        make_candle(2000, 100, 105, 75, 80),
        make_candle(3000, 80, 105, 80, 100)
    ]

    def factory(sym):
        return MockMultiStrategy(sym, {0: SignalEvent(timestamp_ms=1000, symbol=sym, direction=PositionSide.LONG)})

    res = engine.run({"BTCUSDT": candles}, factory)

    # Candle 1 MTM drawdown must reflect the unrealized drop (~10%)
    assert pytest.approx(res.mtm_max_drawdown_pct, abs=1.0) == 10.0
    # Closed trade drawdown is near 0.0% because it recovered before exiting
    assert res.closed_trade_max_drawdown_pct < 1.0


def test_7_gap_through_stop_and_same_candle_sl_tp_ambiguity():
    """Verify gap-through-stop fill at market open and CONSERVATIVE_SL_FIRST resolution."""
    cfg = PortfolioEngineConfig(
        initial_equity=10000.0,
        target_position_pct=10.0,
        intrabar_policy=ExecutionPolicy.CONSERVATIVE_SL_FIRST
    )
    engine = CanonicalPortfolioEngine(cfg)

    # Bar 0: Enter at 100 with SL=95, TP=110
    # Bar 1: Market gaps down to 90 Open (SL was 95)
    candles = [
        make_candle(1000, 100, 105, 95, 100),
        make_candle(2000, 90, 115, 85, 100) # Gapped to 90, touches both 85 (SL hit) and 115 (TP hit)
    ]

    sig = {
        0: SignalEvent(timestamp_ms=1000, symbol="BTCUSDT", direction=PositionSide.LONG, stop_loss=95.0, take_profit=110.0)
    }

    res = engine.run({"BTCUSDT": candles}, lambda s: MockMultiStrategy(s, sig))

    assert len(res.trade_ledger) == 1
    trade = res.trade_ledger[0]
    # Exit reason must be STOP_LOSS due to CONSERVATIVE_SL_FIRST
    assert trade.exit_reason == ExitReason.STOP_LOSS
    # Exit price must reflect gap Open (<= 90), not pegged to 95
    assert trade.exit_price <= 90.0


def test_8_fees_and_slippage_reconciliation():
    """Verify that cash, gross PnL, fees, and slippage reconcile exactly."""
    cfg = PortfolioEngineConfig(initial_equity=10000.0, target_position_pct=10.0, taker_fee_bps=5.0, slippage_bps=2.0)
    engine = CanonicalPortfolioEngine(cfg)

    candles = [
        make_candle(1000, 100, 105, 95, 100),
        make_candle(2000, 110, 115, 105, 110),
        make_candle(3000, 110, 115, 105, 110)
    ]

    sig = {
        0: SignalEvent(timestamp_ms=1000, symbol="BTCUSDT", direction=PositionSide.LONG),
        1: SignalEvent(timestamp_ms=2000, symbol="BTCUSDT", direction=PositionSide.FLAT)
    }

    res = engine.run({"BTCUSDT": candles}, lambda s: MockMultiStrategy(s, sig))

    assert len(res.trade_ledger) == 1
    trade = res.trade_ledger[0]
    expected_cash = cfg.initial_equity + trade.net_pnl
    assert pytest.approx(res.final_equity, abs=1e-2) == expected_cash
    assert res.total_fees_paid > 0.0
    assert res.total_slippage_cost > 0.0


def test_9_bankruptcy_and_zero_equity_behavior():
    """Verify that equity is clamped to 0.0 upon bankruptcy, capping MDD at 100%."""
    cfg = PortfolioEngineConfig(initial_equity=1000.0, target_position_pct=100.0)
    engine = CanonicalPortfolioEngine(cfg)

    # Bar 0: Signal at 100
    # Bar 1: Fills Long at Open=100.0, Close=100.0
    # Bar 2: Market crashes to 0.001 (99.99% loss on $1,000 position)
    candles = [
        make_candle(1000, 100, 105, 95, 100),
        make_candle(2000, 100, 105, 95, 100),
        make_candle(3000, 0.001, 0.01, 0.0001, 0.001)
    ]

    sig = {0: SignalEvent(timestamp_ms=1000, symbol="SHITUSDT", direction=PositionSide.LONG)}
    res = engine.run({"SHITUSDT": candles}, lambda s: MockMultiStrategy(s, sig))

    assert res.is_bankrupt is True
    assert res.final_equity == 0.0
    assert res.clamped_drawdown_pct == 100.0


def test_10_fold_resets_and_boundary_flattening():
    """Verify that boundary flattening closes positions and independent fold resets isolate capital."""
    cfg = PortfolioEngineConfig(initial_equity=10000.0, target_position_pct=10.0)

    # Fold 1 run
    engine_f1 = CanonicalPortfolioEngine(cfg)
    candles_f1 = [make_candle(1000, 100, 105, 95, 100), make_candle(2000, 100, 105, 95, 100)]
    sig_f1 = {0: SignalEvent(timestamp_ms=1000, symbol="BTCUSDT", direction=PositionSide.LONG)}
    res_f1 = engine_f1.run({"BTCUSDT": candles_f1}, lambda s: MockMultiStrategy(s, sig_f1))

    # Must be flattened at end with BOUNDARY_FLAT
    assert len(res_f1.trade_ledger) == 1
    assert res_f1.trade_ledger[0].exit_reason == ExitReason.BOUNDARY_FLAT

    # Fold 2 run: Fresh independent engine with $10k initial equity
    engine_f2 = CanonicalPortfolioEngine(cfg)
    assert engine_f2.cash == 10000.0
    assert engine_f2.high_watermark == 10000.0
    assert len(engine_f2.positions) == 0


def test_11_missing_funding_data_exception_guard():
    """Verify that use_funding=True raises FundingDataMissingException when Parquet archive is absent."""
    cfg = PortfolioEngineConfig(initial_equity=10000.0, use_funding=True)
    engine = CanonicalPortfolioEngine(cfg)
    candles = [make_candle(1000, 100, 105, 95, 100)]

    with pytest.raises(FundingDataMissingException):
        engine.run({"BTCUSDT": candles}, lambda s: MockMultiStrategy(s, {}))


def test_12_identical_outputs_and_checksums_on_deterministic_replay():
    """Verify bit-for-bit reproducibility and identical SHA-256 equity checksums across repeated runs."""
    def run_simulation():
        cfg = PortfolioEngineConfig(initial_equity=10000.0, target_position_pct=10.0)
        engine = CanonicalPortfolioEngine(cfg)
        btc = [
            make_candle(1000, 100, 105, 95, 100),
            make_candle(2000, 102, 107, 101, 105),
            make_candle(3000, 105, 110, 104, 108)
        ]
        eth = [
            make_candle(1000, 50, 52, 48, 50),
            make_candle(2000, 49, 51, 47, 48),
            make_candle(3000, 48, 50, 46, 49)
        ]
        sig_btc = {0: SignalEvent(timestamp_ms=1000, symbol="BTCUSDT", direction=PositionSide.LONG)}
        sig_eth = {1: SignalEvent(timestamp_ms=2000, symbol="ETHUSDT", direction=PositionSide.LONG)}
        factory = lambda s: MockMultiStrategy(s, sig_btc if s == "BTCUSDT" else sig_eth)
        res = engine.run({"BTCUSDT": btc, "ETHUSDT": eth}, factory)
        eq_json = json.dumps([p.model_dump(mode="json") for p in res.equity_curve], sort_keys=True)
        return hashlib.sha256(eq_json.encode()).hexdigest(), res

    h1, res1 = run_simulation()
    h2, res2 = run_simulation()

    assert h1 == h2
    assert res1.final_equity == res2.final_equity
    assert res1.mtm_max_drawdown_pct == res2.mtm_max_drawdown_pct
    assert len(res1.trade_ledger) == len(res2.trade_ledger)
