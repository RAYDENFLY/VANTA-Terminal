"""
VANTA Terminal — Independent Accounting Audit & Hand-Calculated Scenarios
=========================================================================
Independent mathematical verification of PnL, fees, slippage, gap-through-stop,
and same-candle ambiguity against exact pre-calculated pen-and-paper values.
"""

import pytest
import math
from backend.backtest.schemas import (
    BacktestConfig,
    SizingType,
    PositionSide,
    ExitReason,
    ExecutionPolicy,
    RunStatus
)
from backend.backtest.events import BarEvent, SignalEvent
from backend.backtest.position import PositionTracker
from backend.backtest.engine import DeterministicBacktestEngine, BaseStrategy


def make_bar(open_time_ms: int, o: float, h: float, l: float, c: float, v: float = 10.0, step_ms: int = 900000):
    return [open_time_ms, o, h, l, c, v, open_time_ms + step_ms - 1]


class SignalAtBarStrategy(BaseStrategy):
    def __init__(self, entry_bar: int, exit_bar: int, direction: PositionSide, sl: float = None, tp: float = None):
        self.entry_bar = entry_bar
        self.exit_bar = exit_bar
        self.direction = direction
        self.sl = sl
        self.tp = tp

    def on_bar(self, bar: BarEvent, position: PositionTracker):
        if bar.bar_index == self.entry_bar and not position.is_open():
            return SignalEvent(
                timestamp_ms=bar.close_time_ms,
                symbol="BTCUSDT",
                direction=self.direction,
                stop_loss=self.sl,
                take_profit=self.tp
            )
        elif bar.bar_index == self.exit_bar and position.is_open():
            return SignalEvent(
                timestamp_ms=bar.close_time_ms,
                symbol="BTCUSDT",
                direction=PositionSide.FLAT
            )
        return None


def test_hand_calculated_long_winner():
    """
    HAND-CALCULATED AUDIT SCENARIO 1:
    Initial Equity: 10,000.00 USDT
    Entry at Open of Bar 1 = 100.00
    Slippage (2 bps) -> Fill Price = 100.0200
    Taker Fee (5 bps) -> Entry Fee = 0.05001
    Exit at Open of Bar 3 = 110.00
    Slippage (2 bps) -> Exit Price = 109.9780
    Taker Fee (5 bps) -> Exit Fee = 0.054989
    Gross PnL = (109.9780 - 100.0200) * 1.0 = 9.9580
    Total Fees = 0.05001 + 0.054989 = 0.104999 (~0.1050)
    Total Slippage = 0.0200 + 0.0220 = 0.0420
    Net PnL = 9.9580 - 0.1050 - 0.0420 = 9.8110
    Final Equity = 10,009.81 USDT
    """
    t0 = 1700000000000
    step = 900000
    candles = [
        make_bar(t0, 100.0, 101.0, 99.0, 100.0),           # Bar 0: Signal emitted
        make_bar(t0 + step, 100.0, 105.0, 99.5, 104.0),     # Bar 1: Fills Long at Open=100.0
        make_bar(t0 + 2*step, 104.0, 108.0, 103.0, 106.0),  # Bar 2: Exit signal emitted
        make_bar(t0 + 3*step, 110.0, 112.0, 109.0, 111.0),  # Bar 3: Fills Exit at Open=110.0
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
    strategy = SignalAtBarStrategy(entry_bar=0, exit_bar=2, direction=PositionSide.LONG)
    res = engine.run(candles, strategy, is_synthetic=True)

    assert res.trades_count == 1
    t = res.trade_ledger[0]

    # Verify every component against hand calculation
    assert math.isclose(t.entry_price, 100.0200, abs_tol=1e-4)
    assert math.isclose(t.exit_price, 109.9780, abs_tol=1e-4)
    assert math.isclose(t.gross_pnl, 9.9580, abs_tol=1e-4)
    assert math.isclose(t.total_fee, 0.1050, abs_tol=1e-3)
    assert math.isclose(t.slippage_cost, 0.0420, abs_tol=1e-4)
    assert math.isclose(t.net_pnl, 9.8110, abs_tol=1e-3)
    assert math.isclose(res.metrics.final_equity, 10009.81, abs_tol=1e-2)
    assert res.metrics.max_drawdown_pct == 0.0


def test_hand_calculated_short_winner():
    """
    HAND-CALCULATED AUDIT SCENARIO 2:
    Initial Equity: 10,000.00 USDT
    Entry at Open of Bar 1 = 100.00
    Slippage (2 bps) -> Fill Price = 99.9800
    Taker Fee (5 bps) -> Entry Fee = 0.04999
    Exit at Open of Bar 3 = 90.00
    Slippage (2 bps) -> Exit Price = 90.0180
    Taker Fee (5 bps) -> Exit Fee = 0.045009
    Gross PnL = (99.9800 - 90.0180) * 1.0 = 9.9620
    Total Fees = 0.04999 + 0.045009 = 0.094999 (~0.0950)
    Total Slippage = 0.0200 + 0.0180 = 0.0380
    Net PnL = 9.9620 - 0.0950 - 0.0380 = 9.8290
    Final Equity = 10,009.83 USDT
    """
    t0 = 1700000000000
    step = 900000
    candles = [
        make_bar(t0, 100.0, 101.0, 99.0, 100.0),           # Bar 0: Signal emitted
        make_bar(t0 + step, 100.0, 101.0, 95.0, 96.0),      # Bar 1: Fills Short at Open=100.0
        make_bar(t0 + 2*step, 96.0, 97.0, 92.0, 93.0),      # Bar 2: Exit signal emitted
        make_bar(t0 + 3*step, 90.0, 91.0, 88.0, 89.0),      # Bar 3: Fills Exit at Open=90.0
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
    strategy = SignalAtBarStrategy(entry_bar=0, exit_bar=2, direction=PositionSide.SHORT)
    res = engine.run(candles, strategy, is_synthetic=True)

    assert res.trades_count == 1
    t = res.trade_ledger[0]

    assert math.isclose(t.entry_price, 99.9800, abs_tol=1e-4)
    assert math.isclose(t.exit_price, 90.0180, abs_tol=1e-4)
    assert math.isclose(t.gross_pnl, 9.9620, abs_tol=1e-4)
    assert math.isclose(t.total_fee, 0.0950, abs_tol=1e-3)
    assert math.isclose(t.slippage_cost, 0.0380, abs_tol=1e-4)
    assert math.isclose(t.net_pnl, 9.8290, abs_tol=1e-3)
    assert math.isclose(res.metrics.final_equity, 10009.83, abs_tol=1e-2)


def test_hand_calculated_gap_through_stop():
    """
    HAND-CALCULATED AUDIT SCENARIO 3:
    Long entered at 100.02. Stop Loss set at 95.00.
    Next bar opens at 90.00 (gaps down past 95.00).
    Expected execution: Fills at Bar Open with slippage = 90.0 * (1 - 0.0002) = 89.9820
    NOT at 95.00.
    Gross loss = 89.9820 - 100.0200 = -10.0380
    """
    t0 = 1700000000000
    step = 900000
    candles = [
        make_bar(t0, 100.0, 101.0, 99.0, 100.0),
        make_bar(t0 + step, 100.0, 101.0, 99.0, 100.0),    # Bar 1: Fills at 100.02
        make_bar(t0 + 2*step, 90.0, 92.0, 88.0, 89.0),     # Bar 2: Gaps down to Open=90.0
    ]

    cfg = BacktestConfig(
        symbol="BTCUSDT",
        initial_equity=10000.0,
        sizing_type=SizingType.FIXED_UNITS,
        sizing_value=1.0,
        slippage_bps=2.0
    )
    engine = DeterministicBacktestEngine(cfg)
    strategy = SignalAtBarStrategy(entry_bar=0, exit_bar=10, direction=PositionSide.LONG, sl=95.0, tp=120.0)
    res = engine.run(candles, strategy, is_synthetic=True)

    assert res.trades_count == 1
    t = res.trade_ledger[0]
    assert t.exit_reason == ExitReason.STOP_LOSS
    assert math.isclose(t.exit_price, 89.9820, abs_tol=1e-4)
    assert math.isclose(t.gross_pnl, -10.0380, abs_tol=1e-4)


def test_hand_calculated_same_candle_ambiguity():
    """
    HAND-CALCULATED AUDIT SCENARIO 4:
    Long entered at 100.02. SL=95.0, TP=105.0.
    Bar 2 has Low=90.0 (hits SL) and High=110.0 (hits TP).
    Under CONSERVATIVE_SL_FIRST policy:
    Exit must be STOP_LOSS, not TP.
    Exit price = 95.0 * (1 - 0.0002) = 94.9810
    Gross loss = 94.9810 - 100.0200 = -5.0390
    Ambiguity flag is True.
    """
    t0 = 1700000000000
    step = 900000
    candles = [
        make_bar(t0, 100.0, 101.0, 99.0, 100.0),
        make_bar(t0 + step, 100.0, 101.0, 99.0, 100.0),     # Bar 1: Fills at 100.02
        make_bar(t0 + 2*step, 100.0, 110.0, 90.0, 101.0),   # Bar 2: Hits both TP and SL
    ]

    cfg = BacktestConfig(
        symbol="BTCUSDT",
        initial_equity=10000.0,
        sizing_type=SizingType.FIXED_UNITS,
        sizing_value=1.0,
        intrabar_policy=ExecutionPolicy.CONSERVATIVE_SL_FIRST,
        slippage_bps=2.0
    )
    engine = DeterministicBacktestEngine(cfg)
    strategy = SignalAtBarStrategy(entry_bar=0, exit_bar=10, direction=PositionSide.LONG, sl=95.0, tp=105.0)
    res = engine.run(candles, strategy, is_synthetic=True)

    assert res.trades_count == 1
    t = res.trade_ledger[0]
    assert t.exit_reason == ExitReason.STOP_LOSS
    assert t.is_ambiguous is True
    assert math.isclose(t.exit_price, 94.9810, abs_tol=1e-4)
    assert math.isclose(t.gross_pnl, -5.0390, abs_tol=1e-4)
