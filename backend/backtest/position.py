"""
VANTA Terminal — Position State & PnL Accounting
================================================
Tracks active perpetual position, notional exposure, entry parameters,
unrealized PnL, cumulative frictions, and barrier parameters.
"""

from typing import Optional, Tuple
from backend.backtest.schemas import PositionSide, ExitReason, TradeRecord


class PositionTracker:
    """
    Manages the lifecycle of a single perpetual position (Long or Short).
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.side = PositionSide.FLAT
        self.quantity = 0.0
        self.entry_price = 0.0
        self.entry_time_ms = 0
        self.entry_fee = 0.0
        self.entry_slippage = 0.0
        self.cumulative_funding = 0.0
        self.stop_loss: Optional[float] = None
        self.take_profit: Optional[float] = None
        self.expiry_bar_index: Optional[int] = None
        self.entry_bar_index: int = 0
        self.is_ambiguous: bool = False

    def is_open(self) -> bool:
        return self.side != PositionSide.FLAT and self.quantity > 0.0

    def open(
        self,
        side: PositionSide,
        quantity: float,
        fill_price: float,
        timestamp_ms: int,
        bar_index: int,
        entry_fee: float,
        entry_slippage: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        expiry_bar_index: Optional[int] = None
    ) -> None:
        """Opens a new position."""
        if self.is_open():
            raise RuntimeError(f"Cannot open new position for {self.symbol}; existing position is already open.")

        if quantity <= 0.0 or fill_price <= 0.0:
            raise ValueError(f"Invalid position open parameters: qty={quantity}, price={fill_price}")

        self.side = side
        self.quantity = quantity
        self.entry_price = fill_price
        self.entry_time_ms = timestamp_ms
        self.entry_bar_index = bar_index
        self.entry_fee = entry_fee
        self.entry_slippage = entry_slippage
        self.cumulative_funding = 0.0
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.expiry_bar_index = expiry_bar_index
        self.is_ambiguous = False

    def apply_funding_payment(self, payment: float) -> None:
        """Accumulates an 8-hour funding cashflow (positive = received, negative = paid)."""
        self.cumulative_funding += payment

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculates mark-to-market unrealized profit or loss."""
        if not self.is_open():
            return 0.0

        if self.side == PositionSide.LONG:
            return (current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - current_price) * self.quantity

    def calculate_notional(self, current_price: float) -> float:
        """Calculates current position notional."""
        if not self.is_open():
            return 0.0
        return current_price * self.quantity

    def close(
        self,
        exit_price: float,
        timestamp_ms: int,
        bar_index: int,
        exit_fee: float,
        exit_slippage: float,
        exit_reason: ExitReason,
        run_id: str,
        trade_id: int,
        equity_before: float,
        is_ambiguous: bool = False
    ) -> TradeRecord:
        """
        Closes position and returns an immutable TradeRecord.
        """
        if not self.is_open():
            raise RuntimeError(f"Cannot close position for {self.symbol}; no active position open.")

        if exit_price <= 0.0:
            raise ValueError(f"Invalid exit price: {exit_price}")

        # Gross PnL calculation
        if self.side == PositionSide.LONG:
            gross_pnl = (exit_price - self.entry_price) * self.quantity
        else:
            gross_pnl = (self.entry_price - exit_price) * self.quantity

        notional_entry = self.entry_price * self.quantity
        total_fees = self.entry_fee + exit_fee
        total_slippage = self.entry_slippage + exit_slippage
        
        # Net PnL = Gross PnL - Total Fees - Total Slippage + Cumulative Funding
        net_pnl = gross_pnl - total_fees - total_slippage + self.cumulative_funding
        return_pct = (net_pnl / notional_entry) * 100.0 if notional_entry > 0.0 else 0.0

        holding_bars = bar_index - self.entry_bar_index
        holding_ms = timestamp_ms - self.entry_time_ms
        equity_after = equity_before + net_pnl

        record = TradeRecord(
            trade_id=trade_id,
            run_id=run_id,
            symbol=self.symbol,
            side=self.side,
            entry_time_ms=self.entry_time_ms,
            exit_time_ms=timestamp_ms,
            entry_price=round(self.entry_price, 4),
            exit_price=round(exit_price, 4),
            quantity=round(self.quantity, 6),
            notional=round(notional_entry, 2),
            gross_pnl=round(gross_pnl, 4),
            entry_fee=round(self.entry_fee, 4),
            exit_fee=round(exit_fee, 4),
            total_fee=round(total_fees, 4),
            slippage_cost=round(total_slippage, 4),
            funding_payment=round(self.cumulative_funding, 4),
            net_pnl=round(net_pnl, 4),
            return_pct=round(return_pct, 4),
            holding_duration_bars=holding_bars,
            holding_duration_ms=holding_ms,
            exit_reason=exit_reason,
            is_ambiguous=is_ambiguous or self.is_ambiguous,
            equity_before=round(equity_before, 2),
            equity_after=round(equity_after, 2)
        )

        # Reset position to flat
        self.side = PositionSide.FLAT
        self.quantity = 0.0
        self.entry_price = 0.0
        self.entry_time_ms = 0
        self.entry_fee = 0.0
        self.entry_slippage = 0.0
        self.cumulative_funding = 0.0
        self.stop_loss = None
        self.take_profit = None
        self.expiry_bar_index = None
        self.is_ambiguous = False

        return record
