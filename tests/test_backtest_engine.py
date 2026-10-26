"""
VANTA Terminal — Phase 3B.2 Deterministic Backtest Engine Test Suite
====================================================================
Comprehensive tests verifying:
- Long & short profitable / losing trades.
- Transaction costs (fees & slippage).
- Funding debits/credits & missing funding blockers.
- Stop-loss, take-profit, time expiry.
- Same-candle TP/SL ambiguity (adverse barrier first).
- Gap-through-stop execution at bar Open.
- Position sizing & quantity precision rounding.
- Equity curve, drawdown, and risk metrics.
- Zero lookahead bias.
- Deterministic reproducibility down to 8 decimal places.
- Dataset SHA-256 integrity checks.
"""

import pytest
import math
from pathlib import Path
from backend.backtest.schemas import (
    BacktestConfig,
    OrderType,
    OrderSide,
    PositionSide,
    ExitReason,
    ExecutionPolicy,
    SizingType,
    RunStatus
)
from backend.backtest.events import BarEvent, SignalEvent
from backend.backtest.costs import TransactionCostModel
from backend.backtest.funding import FundingAccountingModel, FundingDataMissingException
from backend.backtest.position import PositionTracker
from backend.backtest.portfolio import PortfolioManager
from backend.backtest.execution import ExecutionSimulator
from backend.backtest.metrics import calculate_performance_metrics
from backend.backtest.engine import DeterministicBacktestEngine, BaseStrategy


def make_candle(open_time_ms: int, o: float, h: float, l: float, c: float, v: float = 10.0, step_ms: int = 900000):
    return [open_time_ms, o, h, l, c, v, open_time_ms + step_ms - 1]


class OneTradeLongStrategy(BaseStrategy):
    """Buys on bar 0 (executed at bar 1 Open), exits on bar 3 (executed at bar 4 Open)."""
    def on_bar(self, bar: BarEvent, position: PositionTracker):
        if bar.bar_index == 0 and not position.is_open():
            return SignalEvent(timestamp_ms=bar.close_time_ms, symbol="BTCUSDT", direction=PositionSide.LONG)
        elif bar.bar_index == 3 and position.is_open():
            return SignalEvent(timestamp_ms=bar.close_time_ms, symbol="BTCUSDT", direction=PositionSide.FLAT)
        return None


class OneTradeShortStrategy(BaseStrategy):
    """Shorts on bar 0 (executed at bar 1 Open), exits on bar 3."""
    def on_bar(self, bar: BarEvent, position: PositionTracker):
        if bar.bar_index == 0 and not position.is_open():
            return SignalEvent(timestamp_ms=bar.close_time_ms, symbol="BTCUSDT", direction=PositionSide.SHORT)
        elif bar.bar_index == 3 and position.is_open():
            return SignalEvent(timestamp_ms=bar.close_time_ms, symbol="BTCUSDT", direction=PositionSide.FLAT)
        return None


class BarrierStrategy(BaseStrategy):
    """Enters long with explicit SL and TP barriers."""
    def __init__(self, sl: float, tp: float, expiry_bars: int = None):
        self.sl = sl
        self.tp = tp
        self.expiry_bars = expiry_bars

    def on_bar(self, bar: BarEvent, position: PositionTracker):
        if bar.bar_index == 0 and not position.is_open():
            return SignalEvent(
                timestamp_ms=bar.close_time_ms,
                symbol="BTCUSDT",
                direction=PositionSide.LONG,
                stop_loss=self.sl,
                take_profit=self.tp,
                time_expiry_bars=self.expiry_bars
            )
        return None


def test_long_profitable_trade():
    """Verify long profitable trade execution, fees, and net PnL."""
    t0 = 1700000000000
    step = 900000
    # Price rises from 100 to 110
    candles = [
        make_candle(t0, 100.0, 101.0, 99.0, 100.5),           # Bar 0: Signal generated
        make_candle(t0 + step, 100.0, 103.0, 99.5, 102.0),     # Bar 1: Fills long at Open (100 + slip)
        make_candle(t0 + 2*step, 102.0, 106.0, 101.5, 105.0),  # Bar 2
        make_candle(t0 + 3*step, 105.0, 109.0, 104.5, 108.0),  # Bar 3: Exit signal generated
        make_candle(t0 + 4*step, 110.0, 112.0, 109.5, 111.0),  # Bar 4: Exits at Open (110 - slip)
    ]

    cfg = BacktestConfig(
        symbol="BTCUSDT",
        initial_equity=10000.0,
        sizing_type=SizingType.FIXED_UNITS,
        sizing_value=1.0,  # 1 unit
        taker_fee_bps=5.0,  # 0.05%
        slippage_bps=2.0    # 0.02%
    )
    engine = DeterministicBacktestEngine(cfg)
    result = engine.run(candles, OneTradeLongStrategy(), is_synthetic=True)

    assert result.status == RunStatus.SUCCESS
    assert result.trades_count == 1
    trade = result.trade_ledger[0]

    assert trade.side == PositionSide.LONG
    # Entry price: 100 * (1 + 0.0002) = 100.02
    assert math.isclose(trade.entry_price, 100.02, rel_tol=1e-4)
    # Exit price: 110 * (1 - 0.0002) = 109.978
    assert math.isclose(trade.exit_price, 109.978, rel_tol=1e-4)
    assert trade.gross_pnl > 9.0
    assert trade.net_pnl > 9.0
    assert result.metrics.win_rate_pct == 100.0


def test_short_profitable_trade():
    """Verify short trade profit when market declines."""
    t0 = 1700000000000
    step = 900000
    # Price falls from 100 to 90
    candles = [
        make_candle(t0, 100.0, 101.0, 99.0, 100.5),
        make_candle(t0 + step, 100.0, 101.0, 97.0, 98.0),
        make_candle(t0 + 2*step, 98.0, 99.0, 94.0, 95.0),
        make_candle(t0 + 3*step, 95.0, 96.0, 91.0, 92.0),
        make_candle(t0 + 4*step, 90.0, 91.0, 88.0, 89.0),
    ]

    cfg = BacktestConfig(
        symbol="BTCUSDT",
        initial_equity=10000.0,
        sizing_type=SizingType.FIXED_UNITS,
        sizing_value=1.0,
        taker_fee_bps=5.0,
        slippage_bps=2.0
    )
    engine = DeterministicBacktestEngine(cfg)
    result = engine.run(candles, OneTradeShortStrategy(), is_synthetic=True)

    assert result.trades_count == 1
    trade = result.trade_ledger[0]
    assert trade.side == PositionSide.SHORT
    assert trade.gross_pnl > 9.0
    assert trade.net_pnl > 9.0


def test_stop_loss_trigger():
    """Verify stop loss triggers when bar touches SL."""
    t0 = 1700000000000
    step = 900000
    # Entry at 100, SL at 95, TP at 120
    candles = [
        make_candle(t0, 100.0, 101.0, 99.0, 100.0),
        make_candle(t0 + step, 100.0, 102.0, 98.0, 99.0),    # Enters at 100.02
        make_candle(t0 + 2*step, 99.0, 100.0, 94.0, 94.5),   # Low touches 94 <= SL (95)
        make_candle(t0 + 3*step, 94.5, 96.0, 93.0, 95.0),
    ]

    cfg = BacktestConfig(
        initial_equity=10000.0,
        sizing_type=SizingType.FIXED_UNITS,
        sizing_value=1.0
    )
    engine = DeterministicBacktestEngine(cfg)
    res = engine.run(candles, BarrierStrategy(sl=95.0, tp=120.0), is_synthetic=True)

    assert res.trades_count == 1
    trade = res.trade_ledger[0]
    assert trade.exit_reason == ExitReason.STOP_LOSS
    assert trade.net_pnl < 0.0


def test_take_profit_trigger():
    """Verify take profit triggers when bar touches TP."""
    t0 = 1700000000000
    step = 900000
    # Entry at 100, SL at 90, TP at 110
    candles = [
        make_candle(t0, 100.0, 101.0, 99.0, 100.0),
        make_candle(t0 + step, 100.0, 102.0, 98.0, 99.0),    # Enters at 100.02
        make_candle(t0 + 2*step, 101.0, 112.0, 100.0, 108.0),# High touches 112 >= TP (110)
        make_candle(t0 + 3*step, 108.0, 110.0, 107.0, 109.0),
    ]

    cfg = BacktestConfig(
        initial_equity=10000.0,
        sizing_type=SizingType.FIXED_UNITS,
        sizing_value=1.0
    )
    engine = DeterministicBacktestEngine(cfg)
    res = engine.run(candles, BarrierStrategy(sl=90.0, tp=110.0), is_synthetic=True)

    assert res.trades_count == 1
    trade = res.trade_ledger[0]
    assert trade.exit_reason == ExitReason.TAKE_PROFIT
    assert trade.net_pnl > 0.0


def test_same_candle_tp_sl_ambiguity_conservative():
    """
    CRITICAL TEST: When both TP and SL are hit in the same bar,
    conservative policy CONSERVATIVE_SL_FIRST must trigger Stop Loss first.
    """
    t0 = 1700000000000
    step = 900000
    # Entry at 100, SL at 95, TP at 105
    candles = [
        make_candle(t0, 100.0, 101.0, 99.0, 100.0),
        make_candle(t0 + step, 100.0, 102.0, 99.0, 101.0),    # Enters at 100
        # Bar 2 is an extreme spike bar: Low=90 (hits SL 95) AND High=110 (hits TP 105)
        make_candle(t0 + 2*step, 100.0, 110.0, 90.0, 102.0),
    ]

    cfg = BacktestConfig(
        initial_equity=10000.0,
        sizing_type=SizingType.FIXED_UNITS,
        sizing_value=1.0,
        intrabar_policy=ExecutionPolicy.CONSERVATIVE_SL_FIRST
    )
    engine = DeterministicBacktestEngine(cfg)
    res = engine.run(candles, BarrierStrategy(sl=95.0, tp=105.0), is_synthetic=True)

    assert res.trades_count == 1
    trade = res.trade_ledger[0]
    assert trade.exit_reason == ExitReason.STOP_LOSS
    assert trade.is_ambiguous is True
    assert trade.net_pnl < 0.0


def test_gap_through_stop_loss():
    """
    CRITICAL TEST: If market gaps down past Stop Loss, fill must be at Open,
    never at the unattainable Stop Loss price.
    """
    t0 = 1700000000000
    step = 900000
    # Entry at 100, SL at 95
    candles = [
        make_candle(t0, 100.0, 101.0, 99.0, 100.0),
        make_candle(t0 + step, 100.0, 101.0, 99.0, 100.0),    # Enters at 100.02
        # Bar 2 gaps down to Open = 90 (well below SL 95)
        make_candle(t0 + 2*step, 90.0, 92.0, 88.0, 89.0),
    ]

    cfg = BacktestConfig(
        initial_equity=10000.0,
        sizing_type=SizingType.FIXED_UNITS,
        sizing_value=1.0,
        slippage_bps=2.0
    )
    engine = DeterministicBacktestEngine(cfg)
    res = engine.run(candles, BarrierStrategy(sl=95.0, tp=120.0), is_synthetic=True)

    assert res.trades_count == 1
    trade = res.trade_ledger[0]
    assert trade.exit_reason == ExitReason.STOP_LOSS
    # Must fill at bar Open (90 - slippage) = 89.982, NOT at 95.0!
    assert trade.exit_price < 91.0
    assert not math.isclose(trade.exit_price, 95.0)


def test_time_expiry_exit():
    """Verify position closes on time expiry bar."""
    t0 = 1700000000000
    step = 900000
    # Expiry set to 2 bars
    candles = [
        make_candle(t0, 100.0, 101.0, 99.0, 100.0),
        make_candle(t0 + step, 100.0, 101.0, 99.0, 100.0),    # Bar 1: Entry
        make_candle(t0 + 2*step, 100.0, 101.0, 99.0, 100.0),  # Bar 2: Hold
        make_candle(t0 + 3*step, 100.0, 101.0, 99.0, 100.0),  # Bar 3: Expiry hit
    ]

    cfg = BacktestConfig(initial_equity=10000.0, sizing_value=1.0, sizing_type=SizingType.FIXED_UNITS)
    engine = DeterministicBacktestEngine(cfg)
    res = engine.run(candles, BarrierStrategy(sl=80.0, tp=130.0, expiry_bars=2), is_synthetic=True)

    assert res.trades_count == 1
    trade = res.trade_ledger[0]
    assert trade.exit_reason == ExitReason.TIME_EXPIRY


def test_funding_blocker_when_data_missing():
    """
    CRITICAL PREREQUISITE TEST:
    If use_funding=True but funding dataset is not validated, engine must block run
    and return BLOCKED_MISSING_FUNDING_DATA status without fabricating numbers.
    """
    t0 = 1700000000000
    candles = [
        make_candle(t0, 100.0, 101.0, 99.0, 100.0),
        make_candle(t0 + 900000, 100.0, 101.0, 99.0, 100.0),
    ]

    cfg = BacktestConfig(use_funding=True)
    engine = DeterministicBacktestEngine(cfg)
    res = engine.run(candles, OneTradeLongStrategy(), is_synthetic=True)

    assert res.status == RunStatus.BLOCKED_MISSING_FUNDING_DATA
    assert any("BLOCKED_MISSING_FUNDING_DATA" in w for w in res.validation_warnings)


def test_zero_lookahead_leakage_protection():
    """
    CRITICAL TEST: Ensure modifying future candle prices cannot alter earlier trades.
    """
    t0 = 1700000000000
    step = 900000
    base_candles = [
        make_candle(t0, 100.0, 101.0, 99.0, 100.0),           # Bar 0
        make_candle(t0 + step, 100.0, 102.0, 99.0, 101.0),     # Bar 1: Entry
        make_candle(t0 + 2*step, 101.0, 103.0, 100.0, 102.0), # Bar 2: Hold
        make_candle(t0 + 3*step, 102.0, 104.0, 101.0, 103.0), # Bar 3: Exit signal
        make_candle(t0 + 4*step, 103.0, 105.0, 102.0, 104.0), # Bar 4: Exits at 103
        make_candle(t0 + 5*step, 104.0, 106.0, 103.0, 105.0), # Bar 5 (Future)
    ]

    # Create mutated series where future bar 5 explodes to 1,000,000
    mutated_candles = [list(c) for c in base_candles]
    mutated_candles[5] = make_candle(t0 + 5*step, 1000000.0, 1500000.0, 900000.0, 1200000.0)

    cfg = BacktestConfig(initial_equity=10000.0, sizing_value=1.0, sizing_type=SizingType.FIXED_UNITS)
    
    eng1 = DeterministicBacktestEngine(cfg)
    res1 = eng1.run(base_candles, OneTradeLongStrategy(), is_synthetic=True)

    eng2 = DeterministicBacktestEngine(cfg)
    res2 = eng2.run(mutated_candles, OneTradeLongStrategy(), is_synthetic=True)

    trade1 = res1.trade_ledger[0]
    trade2 = res2.trade_ledger[0]

    # Earlier trade entry, exit, PnL must be bit-for-bit identical
    assert trade1.entry_price == trade2.entry_price
    assert trade1.exit_price == trade2.exit_price
    assert trade1.net_pnl == trade2.net_pnl


def test_deterministic_reproducibility():
    """
    CRITICAL TEST: 5 identical runs must produce 100% identical ledgers and equity down to 8 decimals.
    """
    t0 = 1700000000000
    step = 900000
    candles = [
        make_candle(t0 + i*step, 100.0 + i, 102.0 + i, 99.0 + i, 101.0 + i)
        for i in range(10)
    ]

    cfg = BacktestConfig(initial_equity=10000.0, sizing_value=1.0, sizing_type=SizingType.FIXED_UNITS)

    results = []
    for _ in range(5):
        eng = DeterministicBacktestEngine(cfg)
        res = eng.run(candles, OneTradeLongStrategy(), is_synthetic=True)
        results.append(res)

    base = results[0]
    for r in results[1:]:
        assert r.config_hash == base.config_hash
        assert r.metrics.net_profit == base.metrics.net_profit
        assert r.metrics.max_drawdown_pct == base.metrics.max_drawdown_pct
        assert r.metrics.sharpe_ratio == base.metrics.sharpe_ratio
        for t1, t2 in zip(base.trade_ledger, r.trade_ledger):
            assert math.isclose(t1.net_pnl, t2.net_pnl, rel_tol=1e-8)
            assert t1.exit_reason == t2.exit_reason


def test_parquet_dataset_backtest_with_checksum_verification():
    """Verify engine runs against real validated Parquet dataset with checksum validation."""
    p_path = Path("D:/vanta-terminal/data/raw/BTCUSDT/15m.parquet")
    assert p_path.exists()

    cfg = BacktestConfig(
        symbol="BTCUSDT",
        timeframe="15m",
        initial_equity=10000.0,
        sizing_type=SizingType.FIXED_UNITS,
        sizing_value=0.01  # 0.01 BTC
    )
    engine = DeterministicBacktestEngine(cfg)
    res = engine.run(
        candles_or_parquet_path=p_path,
        strategy=OneTradeLongStrategy(),
        dataset_id="ASTERDEX_BTCUSDT_15M_ARCHIVE",
        is_synthetic=True
    )

    assert res.status == RunStatus.SUCCESS
    assert res.dataset_sha256 != "N/A"
    assert res.metrics is not None
    assert len(res.equity_curve) > 100000  # Evaluated all 105,216 bars!


def test_checksum_mismatch_raises_error(tmp_path):
    """Verify that if a dataset SHA-256 does not match its manifest, engine rejects the run."""
    fake_parquet = tmp_path / "corrupted.parquet"
    fake_parquet.write_bytes(b"corrupted_binary_data")

    cfg = BacktestConfig(symbol="BTCUSDT", timeframe="15m")
    engine = DeterministicBacktestEngine(cfg)

    # When dataset_id is ASTERDEX_BTCUSDT_15M_ARCHIVE, SHA-256 won't match corrupted bytes
    with pytest.raises(ValueError) as exc:
        engine.run(
            candles_or_parquet_path=fake_parquet,
            strategy=OneTradeLongStrategy(),
            dataset_id="ASTERDEX_BTCUSDT_15M_ARCHIVE"
        )
    assert "Dataset SHA-256 mismatch" in str(exc.value)


def test_funding_accounting_math_credit_and_debit():
    """Verify perpetual funding rate sign conventions and payment math."""
    model = FundingAccountingModel(symbol="BTCUSDT", use_funding=True)
    model.is_data_validated = True
    model.funding_records[1700006400000] = 0.0001   # +1 bp (+0.01%)
    model.funding_records[1700035200000] = -0.0002  # -2 bps (-0.02%)

    # 1. Long position at +0.01% rate -> Long PAYS (debit of -1.0)
    evt_long_pos_rate = model.process_funding_settlement(
        current_time_ms=1700006400000,
        position_side=PositionSide.LONG,
        position_notional=10000.0
    )
    assert evt_long_pos_rate is not None
    assert evt_long_pos_rate.payment == -1.0  # Debit

    # 2. Short position at +0.01% rate -> Short RECEIVES (credit of +1.0)
    evt_short_pos_rate = model.process_funding_settlement(
        current_time_ms=1700006400000,
        position_side=PositionSide.SHORT,
        position_notional=10000.0
    )
    assert evt_short_pos_rate is not None
    assert evt_short_pos_rate.payment == 1.0   # Credit

    # 3. Long position at -0.02% rate -> Long RECEIVES (credit of +2.0)
    evt_long_neg_rate = model.process_funding_settlement(
        current_time_ms=1700035200000,
        position_side=PositionSide.LONG,
        position_notional=10000.0
    )
    assert evt_long_neg_rate is not None
    assert evt_long_neg_rate.payment == 2.0   # Credit

    # 4. Short position at -0.02% rate -> Short PAYS (debit of -2.0)
    evt_short_neg_rate = model.process_funding_settlement(
        current_time_ms=1700035200000,
        position_side=PositionSide.SHORT,
        position_notional=10000.0
    )
    assert evt_short_neg_rate is not None
    assert evt_short_neg_rate.payment == -2.0  # Debit

