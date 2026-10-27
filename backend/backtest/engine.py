"""
VANTA Terminal — Deterministic Backtest Engine
=============================================
Vector-indexed discrete bar event loop with zero lookahead bias,
intrabar barrier evaluation, transaction friction accounting,
and reproducible trade ledger generation.
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import hashlib

from backend.backtest.schemas import (
    BacktestConfig,
    BacktestResult,
    RunStatus,
    OrderSide,
    OrderType,
    PositionSide,
    ExitReason,
    ExecutionPolicy
)
from backend.backtest.events import BarEvent, SignalEvent, OrderEvent, FillEvent
from backend.backtest.costs import TransactionCostModel
from backend.backtest.funding import FundingAccountingModel, FundingDataMissingException
from backend.backtest.position import PositionTracker
from backend.backtest.portfolio import PortfolioManager
from backend.backtest.execution import ExecutionSimulator
from backend.backtest.ledger import TradeLedger
from backend.backtest.metrics import calculate_performance_metrics
from backend.data.parquet_store import read_parquet_dataset, compute_sha256
from backend.data.ingestion_engine import check_disk_space_guard


class BaseStrategy:
    """Abstract strategy interface for backtesting."""
    def on_bar(self, bar: BarEvent, position: PositionTracker) -> Optional[SignalEvent]:
        raise NotImplementedError


class DeterministicBacktestEngine:
    """
    Core deterministic event-driven backtesting engine.
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.config_hash = config.compute_config_hash()
        self.cost_model = TransactionCostModel(
            maker_fee_bps=config.maker_fee_bps,
            taker_fee_bps=config.taker_fee_bps,
            slippage_bps=config.slippage_bps
        )
        self.funding_model = FundingAccountingModel(
            symbol=config.symbol,
            use_funding=config.use_funding
        )
        self.position = PositionTracker(symbol=config.symbol)
        self.portfolio = PortfolioManager(config=config)
        self.execution = ExecutionSimulator(config=config, cost_model=self.cost_model)

    def run(
        self,
        candles_or_parquet_path: Any,
        strategy: BaseStrategy,
        run_id: Optional[str] = None,
        is_synthetic: bool = False,
        dataset_id: str = "SYNTHETIC_DATASET"
    ) -> BacktestResult:
        """
        Executes a deterministic backtest run.
        """
        # Step 1: Pre-flight disk space safety check
        check_disk_space_guard(Path("D:/vanta-terminal/data/backtests"), min_free_gb=10.0)

        if run_id is None:
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            run_id = f"RUN_{self.config.symbol}_{self.config.timeframe}_{ts_str}_{uuid.uuid4().hex[:6]}"

        ledger = TradeLedger(run_id=run_id)

        # Step 2: Load and verify dataset
        dataset_sha256 = "N/A_IN_MEMORY"
        if isinstance(candles_or_parquet_path, (str, Path)):
            p_path = Path(candles_or_parquet_path)
            if not p_path.exists():
                raise FileNotFoundError(f"Parquet dataset not found at {p_path}")

            # Verify dataset against its manifest
            dataset_sha256 = compute_sha256(p_path)
            manifest_file = Path(f"D:/vanta-terminal/data/manifests/{dataset_id}.manifest.json")
            if manifest_file.exists():
                import json
                with open(manifest_file, "r") as mf:
                    mdata = json.load(mf)
                expected_sha = mdata.get("storage", {}).get("sha256")
                if expected_sha and expected_sha != dataset_sha256:
                    raise ValueError(
                        f"CRITICAL: Dataset SHA-256 mismatch for {dataset_id}! "
                        f"Expected {expected_sha}, got {dataset_sha256}."
                    )

            table, meta = read_parquet_dataset(p_path)
            pydict = table.to_pydict()
            row_count = len(pydict["open_time"])
            raw_candles = []
            for i in range(row_count):
                raw_candles.append([
                    pydict["open_time"][i],
                    float(pydict["open"][i]),
                    float(pydict["high"][i]),
                    float(pydict["low"][i]),
                    float(pydict["close"][i]),
                    float(pydict["volume"][i]),
                    int(pydict["close_time"][i])
                ])
        else:
            raw_candles = candles_or_parquet_path

        if not raw_candles:
            raise ValueError("Cannot run backtest on empty candle dataset.")

        start_time_ms = int(raw_candles[0][0])
        end_time_ms = int(raw_candles[-1][0])

        # Step 3: Check Funding Prerequisite
        if self.config.use_funding:
            is_funding_ready, funding_status = self.funding_model.verify_funding_prerequisite(start_time_ms, end_time_ms)
            if not is_funding_ready:
                # Return blocked status
                return BacktestResult(
                    run_id=run_id,
                    config_hash=self.config_hash,
                    config=self.config,
                    dataset_id=dataset_id,
                    dataset_sha256=dataset_sha256,
                    status=RunStatus.BLOCKED_MISSING_FUNDING_DATA,
                    validation_warnings=[
                        f"BLOCKED_MISSING_FUNDING_DATA: Complete historical funding rates for {self.config.symbol} "
                        "have not been ingested into local Parquet archive. Simulation blocked."
                    ],
                    created_at_utc=datetime.now(timezone.utc).isoformat(),
                    is_synthetic_test=is_synthetic
                )

        # Step 4: Deterministic Bar Event Loop
        pending_order: Optional[OrderEvent] = None
        next_order_id = 1

        for idx, row in enumerate(raw_candles):
            bar = BarEvent(
                timestamp_ms=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                close_time_ms=int(row[6]),
                bar_index=idx
            )

            # Sub-step 4A: Execute pending order generated on bar t-1 (Fills at bar t Open)
            if pending_order is not None:
                if not self.position.is_open() and pending_order.reason != "SIGNAL_EXIT":
                    # Execute entry order at bar Open with slippage
                    fill = self.execution.execute_market_order(pending_order, bar)
                    pos_side = PositionSide.LONG if pending_order.side == OrderSide.BUY else PositionSide.SHORT

                    self.position.open(
                        side=pos_side,
                        quantity=fill.quantity,
                        fill_price=fill.fill_price,
                        timestamp_ms=bar.timestamp_ms,
                        bar_index=bar.bar_index,
                        entry_fee=fill.fee,
                        entry_slippage=fill.slippage_cost,
                        stop_loss=pending_order.stop_loss,
                        take_profit=pending_order.take_profit,
                        expiry_bar_index=pending_order.expiry_bar_index
                    )
                elif self.position.is_open() and pending_order.reason == "SIGNAL_EXIT":
                    # Execute signal-initiated exit at bar Open with slippage (strict zero lookahead)
                    fill = self.execution.execute_market_order(pending_order, bar, exit_reason=ExitReason.SIGNAL_EXIT)
                    equity_before = self.portfolio.cash
                    trade = self.position.close(
                        exit_price=fill.fill_price,
                        timestamp_ms=bar.timestamp_ms,
                        bar_index=bar.bar_index,
                        exit_fee=fill.fee,
                        exit_slippage=fill.slippage_cost,
                        exit_reason=ExitReason.SIGNAL_EXIT,
                        run_id=run_id,
                        trade_id=ledger.get_next_trade_id(),
                        equity_before=equity_before,
                        is_ambiguous=False
                    )
                    ledger.add_trade(trade)
                    self.portfolio.apply_trade_cashflow(trade.net_pnl)

                pending_order = None

            # Sub-step 4B: Process 8-hour funding cashflow if position is open
            if self.config.use_funding and self.position.is_open():
                pos_notional = self.position.calculate_notional(bar.open)
                f_event = self.funding_model.process_funding_settlement(
                    current_time_ms=bar.timestamp_ms,
                    position_side=self.position.side,
                    position_notional=pos_notional
                )
                if f_event is not None:
                    self.position.apply_funding_payment(f_event.payment)
                    self.portfolio.apply_trade_cashflow(f_event.payment)

            # Sub-step 4C: Intrabar Barrier Evaluation (SL, TP, Time Expiry)
            barrier_res = self.execution.evaluate_barriers(bar, self.position)
            if barrier_res is not None:
                exit_price, exit_reason, is_ambiguous, exit_slippage = barrier_res
                exit_notional = exit_price * self.position.quantity
                exit_fee = self.cost_model.calculate_fee(notional=exit_notional, is_maker=(exit_reason == ExitReason.TAKE_PROFIT))

                equity_before = self.portfolio.cash
                trade = self.position.close(
                    exit_price=exit_price,
                    timestamp_ms=bar.timestamp_ms,
                    bar_index=bar.bar_index,
                    exit_fee=exit_fee,
                    exit_slippage=exit_slippage,
                    exit_reason=exit_reason,
                    run_id=run_id,
                    trade_id=ledger.get_next_trade_id(),
                    equity_before=equity_before,
                    is_ambiguous=is_ambiguous
                )
                ledger.add_trade(trade)
                self.portfolio.apply_trade_cashflow(trade.net_pnl)

            # Sub-step 4D: Update bar-end mark-to-market equity point
            eq_point = self.portfolio.update_bar_equity(
                timestamp_ms=bar.timestamp_ms,
                bar_index=bar.bar_index,
                current_price=bar.close,
                position=self.position
            )
            ledger.add_equity_point(eq_point)

            # Sub-step 4E: Strategy generates signal for bar t+1 execution (Strict Zero Lookahead)
            signal = strategy.on_bar(bar, self.position)
            if signal is not None:
                if signal.direction != PositionSide.FLAT and not self.position.is_open():
                    order_side = OrderSide.BUY if signal.direction == PositionSide.LONG else OrderSide.SELL
                    qty = self.portfolio.calculate_position_size(bar.close, self.position)

                    if qty > 0.0:
                        expiry_bar = (idx + 1 + signal.time_expiry_bars) if signal.time_expiry_bars else None
                        pending_order = OrderEvent(
                            order_id=next_order_id,
                            timestamp_ms=bar.close_time_ms + 1,  # Submits for bar t+1
                            symbol=self.config.symbol,
                            side=order_side,
                            order_type=OrderType.MARKET,
                            quantity=qty,
                            stop_loss=signal.stop_loss,
                            take_profit=signal.take_profit,
                            expiry_bar_index=expiry_bar,
                            reason=signal.tag
                        )
                        next_order_id += 1

                elif signal.direction == PositionSide.FLAT and self.position.is_open():
                    # Queue market exit order for bar t+1 Open (strict zero lookahead)
                    order_side = OrderSide.SELL if self.position.side == PositionSide.LONG else OrderSide.BUY
                    pending_order = OrderEvent(
                        order_id=next_order_id,
                        timestamp_ms=bar.close_time_ms + 1,
                        symbol=self.config.symbol,
                        side=order_side,
                        order_type=OrderType.MARKET,
                        quantity=self.position.quantity,
                        reason="SIGNAL_EXIT"
                    )
                    next_order_id += 1

        # Step 5: Force close any remaining open position at end of backtest window
        if self.position.is_open():
            last_bar = raw_candles[-1]
            exit_p = float(last_bar[4])
            exit_notional = exit_p * self.position.quantity
            exit_fee = self.cost_model.calculate_fee(exit_notional, is_maker=False)
            equity_before = self.portfolio.cash
            trade = self.position.close(
                exit_price=exit_p,
                timestamp_ms=int(last_bar[0]),
                bar_index=len(raw_candles) - 1,
                exit_fee=exit_fee,
                exit_slippage=0.0,
                exit_reason=ExitReason.BOUNDARY_FLAT,
                run_id=run_id,
                trade_id=ledger.get_next_trade_id(),
                equity_before=equity_before,
                is_ambiguous=False
            )
            ledger.add_trade(trade)
            self.portfolio.apply_trade_cashflow(trade.net_pnl)

        # Step 6: Compute Performance Metrics & Cost Breakdown
        metrics, cost_breakdown = calculate_performance_metrics(
            trades=ledger.trades,
            equity_curve=ledger.equity_curve,
            initial_equity=self.config.initial_equity,
            annualization_factor=self.config.annualization_factor
        )

        dt_start = datetime.fromtimestamp(start_time_ms / 1000, timezone.utc).isoformat()
        dt_end = datetime.fromtimestamp(end_time_ms / 1000, timezone.utc).isoformat()

        result = BacktestResult(
            run_id=run_id,
            config_hash=self.config_hash,
            config=self.config,
            dataset_id=dataset_id,
            dataset_sha256=dataset_sha256,
            status=RunStatus.SUCCESS,
            metrics=metrics,
            cost_breakdown=cost_breakdown,
            trades_count=len(ledger.trades),
            trade_ledger=ledger.trades,
            equity_curve=ledger.equity_curve,
            validation_warnings=ledger.warnings,
            start_time_utc=dt_start,
            end_time_utc=dt_end,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            is_synthetic_test=is_synthetic
        )

        # Step 7: Persist Run Artifacts to HDD D:
        ledger.save_run_artifacts(result)

        return result
