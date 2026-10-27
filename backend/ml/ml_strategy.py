"""
VANTA Terminal — Supervised ML Strategy Adapter for Canonical Portfolio Engine
==============================================================================
Implements the Prediction-to-Trade policy specified in Section 5 of Phase 5A / 5A.1:
1. Signal Timing: Model prediction y_hat_t is generated upon bar t close.
2. Order Execution: Dispatches SignalEvent for Market fill at bar t+1 Open with 10% sizing.
3. Active Barriers:
   - Long: Take Profit at C_t * (1 + 1.5 * delta_ATR + 0.0014), Stop Loss at C_t * (1 - 1.0 * delta_ATR).
   - Short: Take Profit at C_t * (1 - 1.5 * delta_ATR - 0.0014), Stop Loss at C_t * (1 + 1.0 * delta_ATR).
   - Expiry: time_expiry_bars = 12 (12-hour holding horizon).
4. Neutral Signals (y_hat_t = 0): Flat positions stay flat; open positions remain managed by active barriers.
"""

from typing import Dict, Any, Optional
import numpy as np

from backend.backtest.engine import BaseStrategy
from backend.backtest.events import BarEvent, SignalEvent
from backend.backtest.schemas import PositionSide
from backend.backtest.position import PositionTracker


class MLModelStrategy(BaseStrategy):
    """
    Adapts an ML candidate's pre-computed predictions to the CanonicalPortfolioEngine event loop.
    """

    def __init__(
        self,
        symbol: str,
        predictions_by_time: Dict[int, int],
        atr_by_time: Dict[int, float],
        friction_hurdle_bps: float = 14.0
    ):
        self.symbol = symbol
        self.predictions = predictions_by_time
        self.atr_map = atr_by_time
        self.friction_hurdle_rate = friction_hurdle_bps / 10000.0

    def on_bar(self, bar: BarEvent, position: PositionTracker) -> Optional[SignalEvent]:
        """
        Called on bar t close. Evaluates model prediction for next-bar execution.
        """
        # Look up discrete model prediction at bar timestamp
        y_hat = self.predictions.get(bar.timestamp_ms, 0)

        # If neutral (0), no new order
        if y_hat == 0:
            return None

        # Only enter new position if currently flat
        if position.is_open():
            return None

        atr_val = self.atr_map.get(bar.timestamp_ms, 0.0)
        close_p = bar.close

        if np.isnan(atr_val) or atr_val <= 0.0 or close_p <= 0.0:
            return None

        delta_atr = atr_val / close_p

        if y_hat == 1:
            # Bullish Breakout -> Market Long Entry at t+1 Open
            tp_price = close_p * (1.0 + 1.5 * delta_atr + self.friction_hurdle_rate)
            sl_price = close_p * (1.0 - 1.0 * delta_atr)

            return SignalEvent(
                timestamp_ms=bar.timestamp_ms,
                symbol=self.symbol,
                direction=PositionSide.LONG,
                stop_loss=round(float(sl_price), 4),
                take_profit=round(float(tp_price), 4),
                time_expiry_bars=12,
                tag="ML_LONG"
            )

        elif y_hat == -1:
            # Bearish Breakout -> Market Short Entry at t+1 Open
            tp_price = close_p * (1.0 - 1.5 * delta_atr - self.friction_hurdle_rate)
            sl_price = close_p * (1.0 + 1.0 * delta_atr)

            return SignalEvent(
                timestamp_ms=bar.timestamp_ms,
                symbol=self.symbol,
                direction=PositionSide.SHORT,
                stop_loss=round(float(sl_price), 4),
                take_profit=round(float(tp_price), 4),
                time_expiry_bars=12,
                tag="ML_SHORT"
            )

        return None
