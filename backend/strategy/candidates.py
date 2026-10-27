"""
VANTA Terminal — Candidate Strategy Implementations (High-Performance Causal)
=============================================================================
Deterministic, strictly causal, O(1) streaming implementations of the 3 pre-registered candidates:
1. Strategy A: Sweep-Reclaim (Liquidity Sweep & Absorption)
2. Strategy B: Breakout / Trend-Following (Donchian + Volume + EMA)
3. Strategy C: Mean Reversion (Bollinger Bands + RSI Hook)
"""

import math
from typing import List, Optional, Deque, Any
from collections import deque

from backend.backtest.engine import BaseStrategy
from backend.backtest.events import BarEvent, SignalEvent
from backend.backtest.schemas import PositionSide
from backend.backtest.position import PositionTracker
from backend.strategy.configurations import StrategyAConfig, StrategyBConfig, StrategyCConfig


class SweepReclaimStrategy(BaseStrategy):
    """
    Candidate Strategy A: Sweep-Reclaim
    Detects wicks sweeping rolling N-period High/Low by >= delta*ATR,
    followed by Close back inside range.
    Streaming O(1) state tracking.
    """

    def __init__(self, config: StrategyAConfig):
        self.config = config
        self.n = config.lookback_n
        self.highs_deque: Deque[float] = deque(maxlen=self.n)
        self.lows_deque: Deque[float] = deque(maxlen=self.n)
        self.tr_deque: Deque[float] = deque(maxlen=14)
        self.tr_sum: float = 0.0
        self.prev_close: Optional[float] = None
        self.bars_count: int = 0

    def on_bar(self, bar: BarEvent, position: PositionTracker) -> Optional[SignalEvent]:
        # 1. Update running True Range
        if self.prev_close is not None:
            tr = max(
                bar.high - bar.low,
                abs(bar.high - self.prev_close),
                abs(bar.low - self.prev_close)
            )
        else:
            tr = bar.high - bar.low

        if len(self.tr_deque) == 14:
            self.tr_sum -= self.tr_deque[0]
        self.tr_deque.append(tr)
        self.tr_sum += tr
        self.bars_count += 1

        signal = None

        # 2. Check if we have sufficient history for reference levels
        if len(self.highs_deque) == self.n and len(self.tr_deque) == 14:
            # highs_deque and lows_deque contain bars t-N .. t-1 (strictly excluding bar t)
            l_ref = min(self.lows_deque)
            h_ref = max(self.highs_deque)
            atr = self.tr_sum / 14.0

            if atr > 0.0 and not position.is_open():
                sweep_thresh = self.config.sweep_delta * atr
                bullish_sweep = (bar.low < l_ref) and ((l_ref - bar.low) >= sweep_thresh)
                bullish_reclaim = bar.close > l_ref

                bearish_sweep = (bar.high > h_ref) and ((bar.high - h_ref) >= sweep_thresh)
                bearish_reclaim = bar.close < h_ref

                # Outside-bar tie-breaking: reject conflict if both sweep
                if not (bullish_sweep and bearish_sweep):
                    buf = 0.10 * atr
                    if bullish_sweep and bullish_reclaim:
                        sl = bar.low - buf
                        risk = bar.close - sl
                        if risk > 0:
                            tp = bar.close + self.config.risk_reward * risk
                            signal = SignalEvent(
                                timestamp_ms=bar.timestamp_ms,
                                symbol=position.symbol,
                                direction=PositionSide.LONG,
                                stop_loss=round(sl, 4),
                                take_profit=round(tp, 4),
                                time_expiry_bars=24,
                                tag="SWEEP_RECLAIM_LONG"
                            )
                    elif bearish_sweep and bearish_reclaim:
                        sl = bar.high + buf
                        risk = sl - bar.close
                        if risk > 0:
                            tp = bar.close - self.config.risk_reward * risk
                            signal = SignalEvent(
                                timestamp_ms=bar.timestamp_ms,
                                symbol=position.symbol,
                                direction=PositionSide.SHORT,
                                stop_loss=round(sl, 4),
                                take_profit=round(tp, 4),
                                time_expiry_bars=24,
                                tag="SWEEP_RECLAIM_SHORT"
                            )

        # 3. Append current completed bar to reference queue for future bars
        self.highs_deque.append(bar.high)
        self.lows_deque.append(bar.low)
        self.prev_close = bar.close

        return signal


class DonchianBreakoutStrategy(BaseStrategy):
    """
    Candidate Strategy B: Breakout / Trend-Following
    Donchian channel breakout with volume expansion and EMA trend filter.
    Stop loss frozen to Fill Price - 1.5 ATR. Midline serves as dynamic exit.
    """

    def __init__(self, config: StrategyBConfig):
        self.config = config
        self.m = config.channel_m
        self.highs_deque: Deque[float] = deque(maxlen=self.m)
        self.lows_deque: Deque[float] = deque(maxlen=self.m)
        self.vol_deque: Deque[float] = deque(maxlen=20)
        self.vol_sum: float = 0.0
        self.tr_deque: Deque[float] = deque(maxlen=14)
        self.tr_sum: float = 0.0
        self.prev_close: Optional[float] = None
        self.ema_filter = config.ema_filter
        self.ema_alpha = 2.0 / (config.ema_filter + 1)
        self.ema_val: Optional[float] = None
        self.ema_prev: Optional[float] = None
        self.bars_count: int = 0

    def on_bar(self, bar: BarEvent, position: PositionTracker) -> Optional[SignalEvent]:
        # 1. Update TR
        if self.prev_close is not None:
            tr = max(
                bar.high - bar.low,
                abs(bar.high - self.prev_close),
                abs(bar.low - self.prev_close)
            )
        else:
            tr = bar.high - bar.low

        if len(self.tr_deque) == 14:
            self.tr_sum -= self.tr_deque[0]
        self.tr_deque.append(tr)
        self.tr_sum += tr

        # 2. Update EMA
        self.ema_prev = self.ema_val
        if self.ema_val is None:
            self.ema_val = bar.close
        else:
            self.ema_val = self.ema_alpha * bar.close + (1.0 - self.ema_alpha) * self.ema_val

        self.bars_count += 1
        signal = None

        # 3. Check reference levels (strictly excluding bar t)
        if len(self.highs_deque) == self.m and self.bars_count > self.ema_filter:
            d_upper = max(self.highs_deque)
            d_lower = min(self.lows_deque)
            d_mid = (d_upper + d_lower) / 2.0

            # Dynamic Midline Exit if position is open
            if position.is_open():
                if position.side == PositionSide.LONG and bar.close < d_mid:
                    signal = SignalEvent(
                        timestamp_ms=bar.timestamp_ms,
                        symbol=position.symbol,
                        direction=PositionSide.FLAT,
                        tag="MIDLINE_EXIT_LONG"
                    )
                elif position.side == PositionSide.SHORT and bar.close > d_mid:
                    signal = SignalEvent(
                        timestamp_ms=bar.timestamp_ms,
                        symbol=position.symbol,
                        direction=PositionSide.FLAT,
                        tag="MIDLINE_EXIT_SHORT"
                    )
            else:
                # Check entry conditions
                if len(self.vol_deque) == 20:
                    avg_vol = self.vol_sum / 20.0
                    vol_ok = (avg_vol > 0.0) and (bar.volume >= self.config.volume_mult * avg_vol)
                    ema_up = self.ema_prev is not None and self.ema_val > self.ema_prev
                    ema_down = self.ema_prev is not None and self.ema_val < self.ema_prev
                    atr = self.tr_sum / 14.0 if len(self.tr_deque) == 14 else 0.0

                    if vol_ok and atr > 0.0:
                        # Long Breakout
                        if bar.close > d_upper and bar.close > self.ema_val and ema_up and bar.close >= d_lower:
                            sl = bar.close - 1.50 * atr
                            signal = SignalEvent(
                                timestamp_ms=bar.timestamp_ms,
                                symbol=position.symbol,
                                direction=PositionSide.LONG,
                                stop_loss=round(sl, 4),
                                take_profit=None,
                                time_expiry_bars=48,
                                tag="DONCHIAN_BREAKOUT_LONG"
                            )
                        # Short Breakdown
                        elif bar.close < d_lower and bar.close < self.ema_val and ema_down and bar.close <= d_upper:
                            sl = bar.close + 1.50 * atr
                            signal = SignalEvent(
                                timestamp_ms=bar.timestamp_ms,
                                symbol=position.symbol,
                                direction=PositionSide.SHORT,
                                stop_loss=round(sl, 4),
                                take_profit=None,
                                time_expiry_bars=48,
                                tag="DONCHIAN_BREAKOUT_SHORT"
                            )

        # 4. Append bar to deques for next bar
        self.highs_deque.append(bar.high)
        self.lows_deque.append(bar.low)
        if len(self.vol_deque) == 20:
            self.vol_sum -= self.vol_deque[0]
        self.vol_deque.append(bar.volume)
        self.vol_sum += bar.volume
        self.prev_close = bar.close

        return signal


class MeanReversionStrategy(BaseStrategy):
    """
    Candidate Strategy C: Mean Reversion
    Statistical dispersion beyond Bollinger Bands with RSI extreme and hook.
    Exit target is return to Bollinger centerline.
    """

    def __init__(self, config: StrategyCConfig):
        self.config = config
        self.k = config.band_len
        self.closes_deque: Deque[float] = deque(maxlen=self.k)
        self.sum_c: float = 0.0
        self.sum_c2: float = 0.0
        self.tr_deque: Deque[float] = deque(maxlen=14)
        self.tr_sum: float = 0.0
        self.prev_close: Optional[float] = None

        # Wilder RSI state
        self.avg_gain: float = 0.0
        self.avg_loss: float = 0.0
        self.rsi_prev: Optional[float] = None
        self.rsi_curr: Optional[float] = None
        self.rsi_warmup_gains: List[float] = []
        self.rsi_warmup_losses: List[float] = []

        # Prior bar Bollinger bands state
        self.prior_lower: Optional[float] = None
        self.prior_upper: Optional[float] = None
        self.prev_bar_close: Optional[float] = None
        self.bars_count: int = 0

    def on_bar(self, bar: BarEvent, position: PositionTracker) -> Optional[SignalEvent]:
        # 1. Update TR
        if self.prev_close is not None:
            tr = max(
                bar.high - bar.low,
                abs(bar.high - self.prev_close),
                abs(bar.low - self.prev_close)
            )
            diff = bar.close - self.prev_close
            gain = max(0.0, diff)
            loss = max(0.0, -diff)
        else:
            tr = bar.high - bar.low
            gain = 0.0
            loss = 0.0

        if len(self.tr_deque) == 14:
            self.tr_sum -= self.tr_deque[0]
        self.tr_deque.append(tr)
        self.tr_sum += tr

        # 2. Update Wilder RSI
        self.rsi_prev = self.rsi_curr
        if self.bars_count < 14:
            self.rsi_warmup_gains.append(gain)
            self.rsi_warmup_losses.append(loss)
            if len(self.rsi_warmup_gains) == 14:
                self.avg_gain = sum(self.rsi_warmup_gains) / 14.0
                self.avg_loss = sum(self.rsi_warmup_losses) / 14.0
                rs = self.avg_gain / self.avg_loss if self.avg_loss > 0 else 1.0
                self.rsi_curr = 100.0 - (100.0 / (1.0 + rs))
        else:
            self.avg_gain = (self.avg_gain * 13.0 + gain) / 14.0
            self.avg_loss = (self.avg_loss * 13.0 + loss) / 14.0
            rs = self.avg_gain / self.avg_loss if self.avg_loss > 0 else 1.0
            self.rsi_curr = 100.0 - (100.0 / (1.0 + rs))

        self.bars_count += 1
        signal = None

        # 3. Calculate Bollinger Bands at current bar t
        if len(self.closes_deque) == self.k:
            mean = self.sum_c / self.k
            var = max(0.0, (self.sum_c2 / self.k) - (mean ** 2))
            std = math.sqrt(var)
            bb_upper = mean + self.config.band_std * std
            bb_lower = mean - self.config.band_std * std

            # Dynamic Centerline Exit
            if position.is_open():
                if position.side == PositionSide.LONG and bar.close >= mean:
                    signal = SignalEvent(
                        timestamp_ms=bar.timestamp_ms,
                        symbol=position.symbol,
                        direction=PositionSide.FLAT,
                        tag="CENTERLINE_TP_LONG"
                    )
                elif position.side == PositionSide.SHORT and bar.close <= mean:
                    signal = SignalEvent(
                        timestamp_ms=bar.timestamp_ms,
                        symbol=position.symbol,
                        direction=PositionSide.FLAT,
                        tag="CENTERLINE_TP_SHORT"
                    )
            else:
                # Entry evaluation (requires prior bar's bands and RSI)
                if (self.prior_lower is not None and self.prior_upper is not None and
                    self.prev_bar_close is not None and self.rsi_prev is not None and self.rsi_curr is not None):
                    atr = self.tr_sum / 14.0 if len(self.tr_deque) == 14 else 0.0
                    if atr > 0.0:
                        # Long Oversold Hook
                        if (self.prev_bar_close <= self.prior_lower and self.rsi_prev < self.config.rsi_oversold and
                            bar.close > bb_lower and self.rsi_curr > self.rsi_prev and self.prev_bar_close < self.prior_upper):
                            sl = bar.close - 1.50 * atr
                            signal = SignalEvent(
                                timestamp_ms=bar.timestamp_ms,
                                symbol=position.symbol,
                                direction=PositionSide.LONG,
                                stop_loss=round(sl, 4),
                                take_profit=round(mean, 4),
                                time_expiry_bars=16,
                                tag="MEAN_REVERSION_LONG"
                            )
                        # Short Overbought Hook
                        elif (self.prev_bar_close >= self.prior_upper and self.rsi_prev > self.config.rsi_overbought and
                              bar.close < bb_upper and self.rsi_curr < self.rsi_prev and self.prev_bar_close > self.prior_lower):
                            sl = bar.close + 1.50 * atr
                            signal = SignalEvent(
                                timestamp_ms=bar.timestamp_ms,
                                symbol=position.symbol,
                                direction=PositionSide.SHORT,
                                stop_loss=round(sl, 4),
                                take_profit=round(mean, 4),
                                time_expiry_bars=16,
                                tag="MEAN_REVERSION_SHORT"
                            )

            # Store current bands as prior bands for next bar
            self.prior_lower = bb_lower
            self.prior_upper = bb_upper

        # 4. Update closes queue
        if len(self.closes_deque) == self.k:
            oldest = self.closes_deque[0]
            self.sum_c -= oldest
            self.sum_c2 -= oldest ** 2
        self.closes_deque.append(bar.close)
        self.sum_c += bar.close
        self.sum_c2 += bar.close ** 2

        self.prev_bar_close = bar.close
        self.prev_close = bar.close

        return signal


def create_strategy_instance(strategy_id: str, config: Any) -> BaseStrategy:
    """Factory creating strategy instance from ID and typed config."""
    sid = strategy_id.upper()
    if "SWEEP" in sid or sid == "A":
        return SweepReclaimStrategy(config)
    elif "BREAK" in sid or sid == "B":
        return DonchianBreakoutStrategy(config)
    elif "MEAN" in sid or sid == "C":
        return MeanReversionStrategy(config)
    else:
        raise ValueError(f"Unknown strategy ID: {strategy_id}")
