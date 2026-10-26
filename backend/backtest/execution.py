"""
VANTA Terminal — Execution Simulator & Intrabar Barrier Evaluation
==================================================================
Simulates order fills, slippage, and conservative same-candle barrier resolution.
Enforces zero lookahead and realistic fill prices during market gaps.
"""

from typing import Optional, Tuple
from backend.backtest.schemas import (
    BacktestConfig,
    OrderSide,
    OrderType,
    PositionSide,
    ExitReason,
    ExecutionPolicy
)
from backend.backtest.events import BarEvent, OrderEvent, FillEvent
from backend.backtest.costs import TransactionCostModel
from backend.backtest.position import PositionTracker


class ExecutionSimulator:
    """
    Evaluates order execution and active position barriers against price action.
    """

    def __init__(self, config: BacktestConfig, cost_model: TransactionCostModel):
        self.config = config
        self.cost_model = cost_model

    def execute_market_order(
        self,
        order: OrderEvent,
        bar: BarEvent,
        exit_reason: Optional[ExitReason] = None
    ) -> FillEvent:
        """
        Executes a market order strictly at the current bar's Open price + adverse slippage.
        """
        fill_price, slip_per_unit = self.cost_model.calculate_slippage(
            base_price=bar.open,
            side=order.side,
            order_type=OrderType.MARKET
        )
        notional = fill_price * order.quantity
        fee = self.cost_model.calculate_fee(notional=notional, is_maker=False)
        total_slippage = slip_per_unit * order.quantity

        return FillEvent(
            order_id=order.order_id,
            timestamp_ms=bar.timestamp_ms,
            symbol=order.symbol,
            side=order.side,
            fill_price=round(fill_price, 4),
            quantity=order.quantity,
            fee=round(fee, 4),
            slippage_cost=round(total_slippage, 4),
            is_maker=False,
            exit_reason=exit_reason,
            is_ambiguous=False
        )

    def evaluate_barriers(
        self,
        bar: BarEvent,
        position: PositionTracker
    ) -> Optional[Tuple[float, ExitReason, bool, float]]:
        """
        Evaluates Stop Loss, Take Profit, and Time Expiry against bar OHLC.
        
        Returns None if no barrier hit, or tuple:
        (exit_price, ExitReason, is_ambiguous, slippage_cost)
        """
        if not position.is_open():
            return None

        # 1. Time Expiry check
        if position.expiry_bar_index is not None and bar.bar_index >= position.expiry_bar_index:
            # Time expiry exit executed at current bar Open with adverse slippage
            side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
            exit_p, slip_unit = self.cost_model.calculate_slippage(bar.open, side, OrderType.MARKET)
            return exit_p, ExitReason.TIME_EXPIRY, False, slip_unit * position.quantity

        # 2. Intrabar Barrier Evaluation for LONG Position
        if position.side == PositionSide.LONG:
            sl_hit = (position.stop_loss is not None and bar.low <= position.stop_loss)
            tp_hit = (position.take_profit is not None and bar.high >= position.take_profit)

            # Intrabar Ambiguity: Both TP and SL touched in same bar
            if sl_hit and tp_hit:
                if self.config.intrabar_policy == ExecutionPolicy.CONSERVATIVE_SL_FIRST:
                    # Adverse barrier (Stop Loss) assumed hit first
                    exit_p, slip_cost = self._resolve_long_sl(bar, position.stop_loss, position.quantity)
                    return exit_p, ExitReason.STOP_LOSS, True, slip_cost
                else:
                    exit_p, slip_cost = self._resolve_long_tp(bar, position.take_profit, position.quantity)
                    return exit_p, ExitReason.TAKE_PROFIT, True, slip_cost

            if sl_hit:
                exit_p, slip_cost = self._resolve_long_sl(bar, position.stop_loss, position.quantity)
                return exit_p, ExitReason.STOP_LOSS, False, slip_cost

            if tp_hit:
                exit_p, slip_cost = self._resolve_long_tp(bar, position.take_profit, position.quantity)
                return exit_p, ExitReason.TAKE_PROFIT, False, slip_cost

        # 3. Intrabar Barrier Evaluation for SHORT Position
        elif position.side == PositionSide.SHORT:
            sl_hit = (position.stop_loss is not None and bar.high >= position.stop_loss)
            tp_hit = (position.take_profit is not None and bar.low <= position.take_profit)

            # Intrabar Ambiguity: Both TP and SL touched in same bar
            if sl_hit and tp_hit:
                if self.config.intrabar_policy == ExecutionPolicy.CONSERVATIVE_SL_FIRST:
                    # Adverse barrier (Stop Loss) assumed hit first
                    exit_p, slip_cost = self._resolve_short_sl(bar, position.stop_loss, position.quantity)
                    return exit_p, ExitReason.STOP_LOSS, True, slip_cost
                else:
                    exit_p, slip_cost = self._resolve_short_tp(bar, position.take_profit, position.quantity)
                    return exit_p, ExitReason.TAKE_PROFIT, True, slip_cost

            if sl_hit:
                exit_p, slip_cost = self._resolve_short_sl(bar, position.stop_loss, position.quantity)
                return exit_p, ExitReason.STOP_LOSS, False, slip_cost

            if tp_hit:
                exit_p, slip_cost = self._resolve_short_tp(bar, position.take_profit, position.quantity)
                return exit_p, ExitReason.TAKE_PROFIT, False, slip_cost

        return None

    def _resolve_long_sl(self, bar: BarEvent, sl: float, qty: float) -> Tuple[float, float]:
        """Resolves Long Stop Loss with gap-through-stop protection."""
        if bar.open < sl:
            # Market gapped down below stop price -> fills at bar Open with slippage
            fill_p, slip_unit = self.cost_model.calculate_slippage(bar.open, OrderSide.SELL, OrderType.MARKET)
            return fill_p, slip_unit * qty
        else:
            # Normal stop trigger at configured barrier level
            fill_p, slip_unit = self.cost_model.calculate_slippage(sl, OrderSide.SELL, OrderType.MARKET)
            return fill_p, slip_unit * qty

    def _resolve_long_tp(self, bar: BarEvent, tp: float, qty: float) -> Tuple[float, float]:
        """Resolves Long Take Profit (limit exit)."""
        if bar.open > tp:
            # Gapped up above TP -> fills at favorable Open
            return bar.open, 0.0
        return tp, 0.0

    def _resolve_short_sl(self, bar: BarEvent, sl: float, qty: float) -> Tuple[float, float]:
        """Resolves Short Stop Loss with gap-through-stop protection."""
        if bar.open > sl:
            # Market gapped up above stop price -> fills at bar Open with slippage
            fill_p, slip_unit = self.cost_model.calculate_slippage(bar.open, OrderSide.BUY, OrderType.MARKET)
            return fill_p, slip_unit * qty
        else:
            fill_p, slip_unit = self.cost_model.calculate_slippage(sl, OrderSide.BUY, OrderType.MARKET)
            return fill_p, slip_unit * qty

    def _resolve_short_tp(self, bar: BarEvent, tp: float, qty: float) -> Tuple[float, float]:
        """Resolves Short Take Profit (limit exit)."""
        if bar.open < tp:
            # Gapped down below TP -> fills at favorable Open
            return bar.open, 0.0
        return tp, 0.0
