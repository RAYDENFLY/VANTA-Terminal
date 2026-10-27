"""
VANTA Terminal — Canonical Multi-Pair Shared-Margin Portfolio Engine (Phase 4B.4)
================================================================================
Implements the frozen Phase 4B.3 portfolio accounting specification:
1. Single shared $10,000 cash pool.
2. 1.0x gross leverage cap with strict capital rationing.
3. Deterministic chronological dispatch across all pair streams.
4. Candle-level mark-to-market equity and drawdown tracking.
5. Intrabar barrier evaluation with CONSERVATIVE_SL_FIRST and gap-through-stop fills.
6. Bankruptcy-floor clamping at $0.00 cash (100.0% max drawdown).
"""

import math
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.backtest.schemas import (
    BacktestConfig,
    OrderSide,
    OrderType,
    PositionSide,
    ExitReason,
    ExecutionPolicy,
    SizingType,
    TradeRecord,
    CostBreakdown
)
from backend.backtest.events import BarEvent, SignalEvent, OrderEvent, FillEvent
from backend.backtest.costs import TransactionCostModel
from backend.backtest.funding import FundingAccountingModel, FundingDataMissingException
from backend.backtest.position import PositionTracker
from backend.backtest.execution import ExecutionSimulator
from backend.backtest.event_queue import MultiStreamEventQueue, BarFrame


class PortfolioEngineConfig(BaseModel):
    initial_equity: float = Field(default=10000.0, gt=0.0)
    target_position_pct: float = Field(default=10.0, gt=0.0, le=100.0)  # 10% of portfolio equity
    max_leverage: float = Field(default=1.0, ge=1.0, le=5.0)           # 1.0x unleveraged futures cap
    max_simultaneous_positions: int = Field(default=10, ge=1)
    maker_fee_bps: float = Field(default=2.0, ge=0.0)
    taker_fee_bps: float = Field(default=5.0, ge=0.0)
    slippage_bps: float = Field(default=2.0, ge=0.0)
    use_funding: bool = False
    intrabar_policy: ExecutionPolicy = ExecutionPolicy.CONSERVATIVE_SL_FIRST
    min_notional_usd: float = Field(default=10.0, gt=0.0)
    min_trade_size: float = Field(default=0.0001, gt=0.0)
    qty_step_decimals: int = Field(default=4, ge=0)


class RejectionRecord(BaseModel):
    timestamp_ms: int
    symbol: str
    direction: PositionSide
    target_notional: float
    free_collateral: float
    reason: str


class PortfolioEquityPoint(BaseModel):
    timestamp_ms: int
    cash: float
    unrealized_pnl: float
    equity: float
    reserved_margin: float
    free_collateral: float
    gross_leverage: float
    drawdown_pct: float
    high_watermark: float
    open_positions_count: int


class PortfolioRunResult(BaseModel):
    run_id: str
    config: PortfolioEngineConfig
    initial_equity: float
    final_equity: float
    net_profit: float
    net_return_pct: float
    mtm_max_drawdown_pct: float
    closed_trade_max_drawdown_pct: float
    clamped_drawdown_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    expectancy: float
    trades_count_by_symbol: Dict[str, int]
    net_pnl_by_symbol: Dict[str, float]
    total_fees_paid: float
    total_slippage_cost: float
    total_funding_paid: float
    total_funding_received: float
    rejected_orders_count: int
    rejected_orders: List[RejectionRecord]
    is_bankrupt: bool
    trade_ledger: List[TradeRecord]
    equity_curve: List[PortfolioEquityPoint]
    start_time_utc: str
    end_time_utc: str


class CanonicalPortfolioEngine:
    """
    Core deterministic multi-pair portfolio backtesting engine.
    Maintains a single shared collateral pool across all instrument streams.
    """

    def __init__(self, config: PortfolioEngineConfig):
        self.config = config
        self.cost_model = TransactionCostModel(
            maker_fee_bps=config.maker_fee_bps,
            taker_fee_bps=config.taker_fee_bps,
            slippage_bps=config.slippage_bps
        )
        self.dummy_bt_config = BacktestConfig(
            symbol="MULTI_PORTFOLIO",
            initial_equity=config.initial_equity,
            maker_fee_bps=config.maker_fee_bps,
            taker_fee_bps=config.taker_fee_bps,
            slippage_bps=config.slippage_bps,
            use_funding=config.use_funding,
            intrabar_policy=config.intrabar_policy,
            max_leverage=config.max_leverage
        )
        self.execution = ExecutionSimulator(config=self.dummy_bt_config, cost_model=self.cost_model)
        self.positions: Dict[str, PositionTracker] = {}
        self.funding_models: Dict[str, FundingAccountingModel] = {}

        # Portfolio accounting state
        self.cash = config.initial_equity
        self.high_watermark = config.initial_equity
        self.mtm_max_drawdown_pct = 0.0
        self.is_bankrupt = False

        # Metrics tracking
        self.trade_ledger: List[TradeRecord] = []
        self.equity_curve: List[PortfolioEquityPoint] = []
        self.rejected_orders: List[RejectionRecord] = []
        self.next_trade_id = 1
        self.next_order_id = 1

        self.total_fees_paid = 0.0
        self.total_slippage_cost = 0.0
        self.total_funding_paid = 0.0
        self.total_funding_received = 0.0

    def get_position(self, symbol: str) -> Optional[PositionTracker]:
        return self.positions.get(symbol)

    def is_position_open(self, symbol: str) -> bool:
        pos = self.positions.get(symbol)
        return pos is not None and pos.is_open()

    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """Calculates aggregate unrealized PnL across all open positions."""
        total_unrealized = 0.0
        for sym, pos in self.positions.items():
            if pos.is_open() and sym in current_prices:
                total_unrealized += pos.calculate_unrealized_pnl(current_prices[sym])
        return total_unrealized

    def get_portfolio_equity(self, current_prices: Dict[str, float]) -> float:
        """Mark-to-market equity = Cash + sum(Unrealized PnL). Clamped at 0.0 if bankrupt."""
        if self.is_bankrupt:
            return 0.0
        eq = self.cash + self.get_unrealized_pnl(current_prices)
        if eq <= 0.0:
            self.is_bankrupt = True
            return 0.0
        return eq

    def get_reserved_margin(self, current_prices: Dict[str, float]) -> float:
        """Sum of position notional exposures (under 1.0x unleveraged futures)."""
        margin = 0.0
        for sym, pos in self.positions.items():
            if pos.is_open() and sym in current_prices:
                margin += pos.calculate_notional(current_prices[sym])
        return margin

    def get_free_collateral(self, current_prices: Dict[str, float]) -> float:
        """Free Collateral = Portfolio Equity * MaxLeverage - Reserved Margin."""
        if self.is_bankrupt:
            return 0.0
        eq = self.get_portfolio_equity(current_prices)
        reserved = self.get_reserved_margin(current_prices)
        total_borrowable = eq * self.config.max_leverage
        return max(0.0, total_borrowable - reserved)

    def calculate_order_quantity(self, symbol: str, entry_price: float, current_prices: Dict[str, float]) -> float:
        """
        Calculates position quantity subject to target portfolio sizing and free collateral constraint.
        """
        if self.is_bankrupt or entry_price <= 0.0:
            return 0.0
        eq = self.get_portfolio_equity(current_prices)
        if eq <= 0.0:
            return 0.0

        target_notional = eq * (self.config.target_position_pct / 100.0)
        free_collateral = self.get_free_collateral(current_prices)
        allocable_notional = min(target_notional, free_collateral)

        if allocable_notional < self.config.min_notional_usd:
            return 0.0

        raw_qty = allocable_notional / entry_price
        # Round down to exchange quantity precision
        factor = 10 ** self.config.qty_step_decimals
        rounded_qty = math.floor(raw_qty * factor) / factor
        if rounded_qty < self.config.min_trade_size:
            return 0.0
        return rounded_qty

    def run(
        self,
        raw_datasets: Dict[str, List[List[Any]]],
        strategy_factory: Any,
        run_id: Optional[str] = None
    ) -> PortfolioRunResult:
        """
        Executes deterministic multi-pair portfolio simulation across the synchronized event queue.
        """
        if run_id is None:
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            run_id = f"RUN_PORTFOLIO_{ts_str}_{uuid.uuid4().hex[:6]}"

        # Step 0: Pre-flight funding prerequisite check if use_funding=True
        if self.config.use_funding:
            for sym in raw_datasets.keys():
                model = FundingAccountingModel(symbol=sym, use_funding=True)
                candles = raw_datasets[sym]
                if not candles:
                    continue
                st_ms = int(candles[0][0])
                et_ms = int(candles[-1][0])
                is_ready, msg = model.verify_funding_prerequisite(st_ms, et_ms)
                if not is_ready:
                    raise FundingDataMissingException(
                        f"BLOCKED_MISSING_FUNDING_DATA: Complete historical funding rates for {sym} "
                        "are not ingested into local Parquet archive. Multi-pair simulation blocked."
                    )
                self.funding_models[sym] = model

        # Instantiate strategy instances per symbol
        strategies = {sym: strategy_factory(sym) for sym in raw_datasets.keys()}

        # Build Multi-Stream Event Queue
        queue = MultiStreamEventQueue(raw_datasets)
        if len(queue) == 0:
            raise ValueError("Cannot run simulation on empty candle datasets.")

        # Pending orders for execution at next bar Open
        pending_exit_orders: Dict[str, OrderEvent] = {}
        pending_entry_signals: List[SignalEvent] = []

        all_bars_processed: List[BarFrame] = []

        # ====================================================================
        # Master Discrete Bar Chronological Event Loop
        # ====================================================================
        for frame in queue.iterframes() if hasattr(queue, "iterframes") else queue.iter_frames():
            all_bars_processed.append(frame)
            frame_open_prices = {s: b.open for s, b in frame.bars.items()}
            frame_close_prices = {s: b.close for s, b in frame.bars.items()}

            # ----------------------------------------------------------------
            # Sub-Step 1: Execute Pending Market Exits at Bar Open (Free Margin)
            # ----------------------------------------------------------------
            if pending_exit_orders:
                for sym, order in list(pending_exit_orders.items()):
                    bar = frame.get_bar(sym)
                    if bar is not None and self.is_position_open(sym):
                        fill = self.execution.execute_market_order(order, bar, exit_reason=ExitReason.SIGNAL_EXIT)
                        self._close_position_fill(fill, bar.bar_index, run_id)
                pending_exit_orders.clear()

            # ----------------------------------------------------------------
            # Sub-Step 2: Process Funding Settlement (if enabled at 00, 08, 16 UTC)
            # ----------------------------------------------------------------
            if self.config.use_funding:
                for sym, pos in list(self.positions.items()):
                    bar = frame.get_bar(sym)
                    if bar is not None and pos.is_open() and sym in self.funding_models:
                        notional = pos.calculate_notional(bar.open)
                        fevent = self.funding_models[sym].process_funding_settlement(
                            current_time_ms=bar.timestamp_ms,
                            position_side=pos.side,
                            position_notional=notional
                        )
                        if fevent is not None:
                            pos.apply_funding_payment(fevent.payment)
                            self.cash += fevent.payment
                            if fevent.payment > 0:
                                self.total_funding_received += fevent.payment
                            else:
                                self.total_funding_paid += abs(fevent.payment)

            # ----------------------------------------------------------------
            # Sub-Step 3: Execute Pending Market Entries (Deterministic Rationing)
            # ----------------------------------------------------------------
            if pending_entry_signals:
                # Sort simultaneous signals deterministically
                vols = {s: frame.get_bar(s).volume for s in frame.bars.keys()}
                sorted_signals = MultiStreamEventQueue.sort_signals_deterministically(pending_entry_signals, vols)

                for sig in sorted_signals:
                    bar = frame.get_bar(sig.symbol)
                    if bar is None:
                        continue

                    # Validation checks
                    if self.is_bankrupt:
                        self.rejected_orders.append(RejectionRecord(
                            timestamp_ms=bar.timestamp_ms,
                            symbol=sig.symbol,
                            direction=sig.direction,
                            target_notional=0.0,
                            free_collateral=0.0,
                            reason="BANKRUPTCY_HALT"
                        ))
                        continue

                    if self.is_position_open(sig.symbol):
                        self.rejected_orders.append(RejectionRecord(
                            timestamp_ms=bar.timestamp_ms,
                            symbol=sig.symbol,
                            direction=sig.direction,
                            target_notional=0.0,
                            free_collateral=self.get_free_collateral(frame_open_prices),
                            reason="ALREADY_IN_POSITION"
                        ))
                        continue

                    active_count = sum(1 for p in self.positions.values() if p.is_open())
                    if active_count >= self.config.max_simultaneous_positions:
                        self.rejected_orders.append(RejectionRecord(
                            timestamp_ms=bar.timestamp_ms,
                            symbol=sig.symbol,
                            direction=sig.direction,
                            target_notional=0.0,
                            free_collateral=self.get_free_collateral(frame_open_prices),
                            reason="MAX_POSITIONS_REACHED"
                        ))
                        continue

                    qty = self.calculate_order_quantity(sig.symbol, bar.open, frame_open_prices)
                    target_notional = self.get_portfolio_equity(frame_open_prices) * (self.config.target_position_pct / 100.0)
                    free_collat = self.get_free_collateral(frame_open_prices)

                    if qty <= 0.0:
                        self.rejected_orders.append(RejectionRecord(
                            timestamp_ms=bar.timestamp_ms,
                            symbol=sig.symbol,
                            direction=sig.direction,
                            target_notional=round(target_notional, 2),
                            free_collateral=round(free_collat, 2),
                            reason="INSUFFICIENT_COLLATERAL"
                        ))
                        continue

                    order_side = OrderSide.BUY if sig.direction == PositionSide.LONG else OrderSide.SELL
                    expiry_bar = (bar.bar_index + sig.time_expiry_bars) if sig.time_expiry_bars else None
                    order = OrderEvent(
                        order_id=self.next_order_id,
                        timestamp_ms=bar.timestamp_ms,
                        symbol=sig.symbol,
                        side=order_side,
                        order_type=OrderType.MARKET,
                        quantity=qty,
                        stop_loss=sig.stop_loss,
                        take_profit=sig.take_profit,
                        expiry_bar_index=expiry_bar,
                        reason=sig.tag
                    )
                    self.next_order_id += 1

                    # Execute market fill at bar Open with slippage
                    fill = self.execution.execute_market_order(order, bar)
                    self._open_position_fill(fill, bar.bar_index, order)

                pending_entry_signals.clear()

            # ----------------------------------------------------------------
            # Sub-Step 4: Intrabar Barrier Evaluation (SL, TP, Time Expiry)
            # ----------------------------------------------------------------
            for sym, pos in list(self.positions.items()):
                bar = frame.get_bar(sym)
                if bar is not None and pos.is_open():
                    barrier_res = self.execution.evaluate_barriers(bar, pos)
                    if barrier_res is not None:
                        exit_price, exit_reason, is_ambiguous, exit_slippage = barrier_res
                        exit_notional = exit_price * pos.quantity
                        exit_fee = self.cost_model.calculate_fee(
                            notional=exit_notional,
                            is_maker=(exit_reason == ExitReason.TAKE_PROFIT)
                        )
                        fill = FillEvent(
                            order_id=self.next_order_id,
                            timestamp_ms=bar.timestamp_ms,
                            symbol=sym,
                            side=OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY,
                            fill_price=round(exit_price, 4),
                            quantity=pos.quantity,
                            fee=round(exit_fee, 4),
                            slippage_cost=round(exit_slippage, 4),
                            is_maker=(exit_reason == ExitReason.TAKE_PROFIT),
                            exit_reason=exit_reason,
                            is_ambiguous=is_ambiguous
                        )
                        self.next_order_id += 1
                        self._close_position_fill(fill, bar.bar_index, run_id)

            # ----------------------------------------------------------------
            # Sub-Step 5: Bar-End Mark-to-Market Equity Point & Drawdown
            # ----------------------------------------------------------------
            eq = self.get_portfolio_equity(frame_close_prices)
            if eq > self.high_watermark:
                self.high_watermark = eq

            dd_pct = 0.0
            if self.high_watermark > 0.0:
                dd_pct = ((self.high_watermark - eq) / self.high_watermark) * 100.0
                if self.is_bankrupt:
                    dd_pct = 100.0
                if dd_pct > self.mtm_max_drawdown_pct:
                    self.mtm_max_drawdown_pct = dd_pct

            reserved = self.get_reserved_margin(frame_close_prices)
            free_collat = self.get_free_collateral(frame_close_prices)
            gross_lev = (reserved / eq) if eq > 0.0 else 0.0
            active_pos_count = sum(1 for p in self.positions.values() if p.is_open())

            eq_point = PortfolioEquityPoint(
                timestamp_ms=frame.timestamp_ms,
                cash=round(self.cash, 2),
                unrealized_pnl=round(eq - self.cash, 2),
                equity=round(eq, 2),
                reserved_margin=round(reserved, 2),
                free_collateral=round(free_collat, 2),
                gross_leverage=round(gross_lev, 4),
                drawdown_pct=round(dd_pct, 4),
                high_watermark=round(self.high_watermark, 2),
                open_positions_count=active_pos_count
            )
            self.equity_curve.append(eq_point)

            # ----------------------------------------------------------------
            # Sub-Step 6: Strategy Signal Generation for Next Bar
            # ----------------------------------------------------------------
            if not self.is_bankrupt:
                for sym, strat in strategies.items():
                    bar = frame.get_bar(sym)
                    if bar is not None:
                        pos = self.positions.get(sym)
                        if pos is None:
                            pos = PositionTracker(symbol=sym)
                            self.positions[sym] = pos

                        sig = strat.on_bar(bar, pos)
                        if sig is not None:
                            if sig.direction != PositionSide.FLAT and not pos.is_open():
                                pending_entry_signals.append(sig)
                            elif sig.direction == PositionSide.FLAT and pos.is_open():
                                side = OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY
                                pending_exit_orders[sym] = OrderEvent(
                                    order_id=self.next_order_id,
                                    timestamp_ms=bar.close_time_ms + 1,
                                    symbol=sym,
                                    side=side,
                                    order_type=OrderType.MARKET,
                                    quantity=pos.quantity,
                                    reason="SIGNAL_EXIT"
                                )
                                self.next_order_id += 1

        # ====================================================================
        # Step 7: Force-Flatten Open Positions at End of Simulation
        # ====================================================================
        if all_bars_processed:
            last_frame = all_bars_processed[-1]
            for sym, pos in list(self.positions.items()):
                if pos.is_open():
                    last_bar = last_frame.get_bar(sym)
                    exit_p = last_bar.close if last_bar is not None else pos.entry_price
                    exit_notional = exit_p * pos.quantity
                    exit_fee = self.cost_model.calculate_fee(exit_notional, is_maker=False)
                    fill = FillEvent(
                        order_id=self.next_order_id,
                        timestamp_ms=last_frame.timestamp_ms,
                        symbol=sym,
                        side=OrderSide.SELL if pos.side == PositionSide.LONG else OrderSide.BUY,
                        fill_price=exit_p,
                        quantity=pos.quantity,
                        fee=exit_fee,
                        slippage_cost=0.0,
                        is_maker=False,
                        exit_reason=ExitReason.BOUNDARY_FLAT,
                        is_ambiguous=False
                    )
                    self.next_order_id += 1
                    self._close_position_fill(fill, last_bar.bar_index if last_bar else 0, run_id)

        # ====================================================================
        # Step 8: Compile Performance Analytics
        # ====================================================================
        return self._compile_results(run_id, all_bars_processed)

    def _open_position_fill(self, fill: FillEvent, bar_index: int, order: OrderEvent) -> None:
        pos = self.positions.get(fill.symbol)
        if pos is None:
            pos = PositionTracker(symbol=fill.symbol)
            self.positions[fill.symbol] = pos

        pos_side = PositionSide.LONG if fill.side == OrderSide.BUY else PositionSide.SHORT
        pos.open(
            side=pos_side,
            quantity=fill.quantity,
            fill_price=fill.fill_price,
            timestamp_ms=fill.timestamp_ms,
            bar_index=bar_index,
            entry_fee=fill.fee,
            entry_slippage=fill.slippage_cost,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            expiry_bar_index=order.expiry_bar_index
        )
        self.total_fees_paid += fill.fee
        self.total_slippage_cost += fill.slippage_cost

    def _close_position_fill(self, fill: FillEvent, bar_index: int, run_id: str) -> None:
        pos = self.positions.get(fill.symbol)
        if pos is None or not pos.is_open():
            return

        equity_before = self.cash
        trade = pos.close(
            exit_price=fill.fill_price,
            timestamp_ms=fill.timestamp_ms,
            bar_index=bar_index,
            exit_fee=fill.fee,
            exit_slippage=fill.slippage_cost,
            exit_reason=fill.exit_reason or ExitReason.SIGNAL_EXIT,
            run_id=run_id,
            trade_id=self.next_trade_id,
            equity_before=equity_before,
            is_ambiguous=fill.is_ambiguous
        )
        self.next_trade_id += 1
        self.trade_ledger.append(trade)

        self.cash += trade.net_pnl
        self.total_fees_paid += fill.fee
        self.total_slippage_cost += fill.slippage_cost

        if self.cash <= 0.0:
            self.is_bankrupt = True
            self.cash = 0.0

    def _compile_results(self, run_id: str, all_bars: List[BarFrame]) -> PortfolioRunResult:
        total_trades = len(self.trade_ledger)
        winning_trades = [t for t in self.trade_ledger if t.net_pnl > 0.0]
        losing_trades = [t for t in self.trade_ledger if t.net_pnl < 0.0]
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_wins = sum(t.net_pnl for t in winning_trades)
        gross_losses = sum(abs(t.net_pnl) for t in losing_trades)
        pf = (gross_wins / gross_losses) if gross_losses > 0.0 else (999.0 if gross_wins > 0 else 0.0)

        final_eq = self.cash
        net_profit = final_eq - self.config.initial_equity
        net_return_pct = (net_profit / self.config.initial_equity) * 100.0
        expectancy = (net_profit / total_trades) if total_trades > 0 else 0.0

        trades_by_sym: Dict[str, int] = {}
        pnl_by_sym: Dict[str, float] = {}
        for t in self.trade_ledger:
            trades_by_sym[t.symbol] = trades_by_sym.get(t.symbol, 0) + 1
            pnl_by_sym[t.symbol] = round(pnl_by_sym.get(t.symbol, 0.0) + t.net_pnl, 2)

        # Chronological trade-close drawdown
        cum_trade_cash = self.config.initial_equity
        hwm_trade = self.config.initial_equity
        closed_trade_dd = 0.0
        for t in self.trade_ledger:
            cum_trade_cash += t.net_pnl
            if cum_trade_cash > hwm_trade:
                hwm_trade = cum_trade_cash
            if hwm_trade > 0.0:
                dd = (hwm_trade - cum_trade_cash) / hwm_trade * 100.0
                if dd > closed_trade_dd:
                    closed_trade_dd = dd

        clamped_dd = min(100.0, self.mtm_max_drawdown_pct) if self.is_bankrupt else self.mtm_max_drawdown_pct

        st_utc = datetime.fromtimestamp(all_bars[0].timestamp_ms / 1000, timezone.utc).isoformat() if all_bars else ""
        et_utc = datetime.fromtimestamp(all_bars[-1].timestamp_ms / 1000, timezone.utc).isoformat() if all_bars else ""

        return PortfolioRunResult(
            run_id=run_id,
            config=self.config,
            initial_equity=round(self.config.initial_equity, 2),
            final_equity=round(final_eq, 2),
            net_profit=round(net_profit, 2),
            net_return_pct=round(net_return_pct, 4),
            mtm_max_drawdown_pct=round(self.mtm_max_drawdown_pct, 4),
            closed_trade_max_drawdown_pct=round(closed_trade_dd, 4),
            clamped_drawdown_pct=round(clamped_dd, 4),
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate_pct=round(win_rate, 2),
            profit_factor=round(pf, 4),
            expectancy=round(expectancy, 4),
            trades_count_by_symbol=trades_by_sym,
            net_pnl_by_symbol=pnl_by_sym,
            total_fees_paid=round(self.total_fees_paid, 2),
            total_slippage_cost=round(self.total_slippage_cost, 2),
            total_funding_paid=round(self.total_funding_paid, 2),
            total_funding_received=round(self.total_funding_received, 2),
            rejected_orders_count=len(self.rejected_orders),
            rejected_orders=self.rejected_orders,
            is_bankrupt=self.is_bankrupt,
            trade_ledger=self.trade_ledger,
            equity_curve=self.equity_curve,
            start_time_utc=st_utc,
            end_time_utc=et_utc
        )
