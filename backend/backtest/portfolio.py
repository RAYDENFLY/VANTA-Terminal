"""
VANTA Terminal — Portfolio Accounting & Position Sizing
======================================================
Manages cash, equity mark-to-market, drawdown high-watermark,
margin requirements, and conservative position sizing.
"""

from typing import Tuple, Optional
from backend.backtest.schemas import BacktestConfig, SizingType, EquityPoint
from backend.backtest.position import PositionTracker


class PortfolioManager:
    """
    Tracks portfolio equity and enforces sizing constraints.
    Prevents double-counting, nonpositive equity, and over-leverage.
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.initial_equity = config.initial_equity
        self.cash = config.initial_equity
        self.high_watermark = config.initial_equity
        self.max_drawdown_pct = 0.0

    def get_equity(self, current_price: float, position: PositionTracker) -> float:
        """Total current equity = cash + unrealized PnL."""
        unrealized = position.calculate_unrealized_pnl(current_price)
        return self.cash + unrealized

    def calculate_position_size(
        self,
        entry_price: float,
        position: PositionTracker
    ) -> float:
        """
        Calculates actionable order quantity based on configured sizing method.
        Rounds to configured step decimals and enforces min trade size.
        """
        if entry_price <= 0.0:
            return 0.0

        current_equity = self.get_equity(entry_price, position)
        if current_equity <= 0.0:
            return 0.0

        if self.config.sizing_type == SizingType.FIXED_NOTIONAL:
            target_notional = min(self.config.sizing_value, current_equity * self.config.max_leverage)
            raw_qty = target_notional / entry_price

        elif self.config.sizing_type == SizingType.PERCENT_EQUITY:
            pct = min(100.0, max(0.1, self.config.sizing_value)) / 100.0
            target_notional = current_equity * pct * self.config.max_leverage
            raw_qty = target_notional / entry_price

        elif self.config.sizing_type == SizingType.FIXED_UNITS:
            raw_qty = self.config.sizing_value
            if (raw_qty * entry_price) > (current_equity * self.config.max_leverage):
                raw_qty = (current_equity * self.config.max_leverage) / entry_price

        else:
            raw_qty = 0.0

        # Round down to exchange quantity precision
        decimals = self.config.qty_step_decimals
        factor = 10 ** decimals
        rounded_qty = int(raw_qty * factor) / factor

        if rounded_qty < self.config.min_trade_size:
            return 0.0

        return rounded_qty

    def update_bar_equity(
        self,
        timestamp_ms: int,
        bar_index: int,
        current_price: float,
        position: PositionTracker
    ) -> EquityPoint:
        """
        Records mark-to-market equity point and calculates drawdown.
        """
        equity = self.get_equity(current_price, position)
        unrealized = position.calculate_unrealized_pnl(current_price)

        if equity > self.high_watermark:
            self.high_watermark = equity

        drawdown_pct = 0.0
        if self.high_watermark > 0.0:
            drawdown_pct = ((self.high_watermark - equity) / self.high_watermark) * 100.0
            if drawdown_pct > self.max_drawdown_pct:
                self.max_drawdown_pct = drawdown_pct

        return EquityPoint(
            timestamp_ms=timestamp_ms,
            bar_index=bar_index,
            equity=round(equity, 2),
            cash=round(self.cash, 2),
            unrealized_pnl=round(unrealized, 2),
            drawdown_pct=round(drawdown_pct, 4),
            high_watermark=round(self.high_watermark, 2)
        )

    def apply_trade_cashflow(self, net_pnl: float) -> None:
        """Adjusts realized cash balance upon trade close."""
        self.cash += net_pnl
