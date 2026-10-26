"""
VANTA Terminal — Transaction Cost & Execution Friction Model
============================================================
Accurately accounts for exchange maker/taker fee tiers and market slippage.
Provides clear separation between gross PnL and execution frictions.
"""

from typing import Tuple, Dict, Any
from backend.backtest.schemas import OrderSide, OrderType


class TransactionCostModel:
    """
    Simulates exchange fee tiers and market slippage.
    Defaults to conservative Taker fee (5.0 bps) for market orders.
    """

    def __init__(
        self,
        maker_fee_bps: float = 2.0,
        taker_fee_bps: float = 5.0,
        slippage_bps: float = 2.0,
        fee_schedule_source: str = "ASTERDEX_V3_STANDARD_TIER_ASSUMPTION"
    ):
        self.maker_fee_rate = maker_fee_bps / 10000.0
        self.taker_fee_rate = taker_fee_bps / 10000.0
        self.slippage_rate = slippage_bps / 10000.0
        self.fee_schedule_source = fee_schedule_source

    def calculate_slippage(
        self,
        base_price: float,
        side: OrderSide,
        order_type: OrderType
    ) -> Tuple[float, float]:
        """
        Calculates execution price and slippage dollar amount.
        Market orders suffer adverse slippage. Limit orders experience zero slippage.
        Returns: (fill_price, slippage_per_unit)
        """
        if order_type == OrderType.LIMIT:
            return base_price, 0.0

        if side == OrderSide.BUY:
            fill_price = base_price * (1.0 + self.slippage_rate)
            slippage_unit = fill_price - base_price
        else:
            fill_price = base_price * (1.0 - self.slippage_rate)
            slippage_unit = base_price - fill_price

        return fill_price, slippage_unit

    def calculate_fee(
        self,
        notional: float,
        is_maker: bool = False
    ) -> float:
        """
        Calculates commission fee in quotation currency (USDT).
        """
        rate = self.maker_fee_rate if is_maker else self.taker_fee_rate
        return round(notional * rate, 6)

    def get_assumptions_summary(self) -> Dict[str, Any]:
        return {
            "maker_fee_bps": self.maker_fee_rate * 10000.0,
            "taker_fee_bps": self.taker_fee_rate * 10000.0,
            "slippage_bps": self.slippage_rate * 10000.0,
            "source": self.fee_schedule_source,
            "classification": "ASSUMPTION_BASED"
        }
