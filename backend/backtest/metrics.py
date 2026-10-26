"""
VANTA Terminal — Quantitative Performance Metrics & Risk Analytics
==================================================================
Deterministic calculation of PnL, Drawdown, Expectancy, Profit Factor,
and documented Sharpe/Sortino ratios with strict variance guards.
"""

import math
from typing import List, Tuple
from backend.backtest.schemas import (
    TradeRecord,
    EquityPoint,
    PerformanceMetrics,
    CostBreakdown
)


def calculate_performance_metrics(
    trades: List[TradeRecord],
    equity_curve: List[EquityPoint],
    initial_equity: float,
    annualization_factor: float
) -> Tuple[PerformanceMetrics, CostBreakdown]:
    """
    Computes deterministic quantitative metrics from the trade ledger and equity curve.
    """
    total_trades = len(trades)
    final_equity = equity_curve[-1].equity if equity_curve else initial_equity
    net_profit = final_equity - initial_equity
    net_return_pct = (net_profit / initial_equity) * 100.0 if initial_equity > 0.0 else 0.0

    # Trade ledger aggregations
    winning_trades = [t for t in trades if t.net_pnl > 0.0]
    losing_trades = [t for t in trades if t.net_pnl < 0.0]
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate_pct = (win_count / total_trades) * 100.0 if total_trades > 0 else 0.0

    total_gross_pnl = sum(t.gross_pnl for t in trades)
    total_fees_paid = sum(t.total_fee for t in trades)
    total_slippage_cost = sum(t.slippage_cost for t in trades)
    total_funding_paid = sum(abs(t.funding_payment) for t in trades if t.funding_payment < 0.0)
    total_funding_received = sum(t.funding_payment for t in trades if t.funding_payment > 0.0)

    gross_wins = sum(t.net_pnl for t in winning_trades)
    gross_losses = sum(abs(t.net_pnl) for t in losing_trades)

    profit_factor = (gross_wins / gross_losses) if gross_losses > 0.0 else (999.0 if gross_wins > 0.0 else 0.0)
    expectancy = (net_profit / total_trades) if total_trades > 0 else 0.0
    avg_win = (gross_wins / win_count) if win_count > 0 else 0.0
    avg_loss = (gross_losses / loss_count) if loss_count > 0 else 0.0
    win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0.0 else 0.0
    avg_holding_bars = (sum(t.holding_duration_bars for t in trades) / total_trades) if total_trades > 0 else 0.0
    ambiguous_count = sum(1 for t in trades if t.is_ambiguous)

    # Max Drawdown & Duration from Equity Curve
    max_dd_pct = 0.0
    max_dd_duration = 0
    current_dd_duration = 0

    for pt in equity_curve:
        if pt.drawdown_pct > max_dd_pct:
            max_dd_pct = pt.drawdown_pct
        if pt.drawdown_pct > 0.0001:
            current_dd_duration += 1
            if current_dd_duration > max_dd_duration:
                max_dd_duration = current_dd_duration
        else:
            current_dd_duration = 0

    # Sharpe and Sortino Ratios calculated from bar-by-bar returns
    # Sampling frequency matches candle timeframe, annualized via annualization_factor
    bar_returns = []
    if len(equity_curve) > 1:
        for i in range(1, len(equity_curve)):
            prev_eq = equity_curve[i - 1].equity
            curr_eq = equity_curve[i].equity
            if prev_eq > 0.0:
                bar_returns.append((curr_eq - prev_eq) / prev_eq)

    sharpe_ratio = 0.0
    sortino_ratio = 0.0

    if len(bar_returns) >= 2:
        mean_return = sum(bar_returns) / len(bar_returns)
        variance = sum((r - mean_return) ** 2 for r in bar_returns) / (len(bar_returns) - 1)
        stdev = math.sqrt(variance)

        if stdev > 1e-12:
            sharpe_ratio = (mean_return / stdev) * math.sqrt(annualization_factor)

        downside_returns = [r for r in bar_returns if r < 0.0]
        if len(downside_returns) >= 1:
            downside_variance = sum(r ** 2 for r in downside_returns) / len(bar_returns)
            downside_stdev = math.sqrt(downside_variance)
            if downside_stdev > 1e-12:
                sortino_ratio = (mean_return / downside_stdev) * math.sqrt(annualization_factor)

    calmar_ratio = (net_return_pct / max_dd_pct) if max_dd_pct > 0.0 else 0.0

    metrics = PerformanceMetrics(
        initial_equity=round(initial_equity, 2),
        final_equity=round(final_equity, 2),
        net_profit=round(net_profit, 2),
        net_return_pct=round(net_return_pct, 4),
        max_drawdown_pct=round(max_dd_pct, 4),
        max_drawdown_duration_bars=max_dd_duration,
        total_trades=total_trades,
        winning_trades=win_count,
        losing_trades=loss_count,
        win_rate_pct=round(win_rate_pct, 2),
        profit_factor=round(profit_factor, 4),
        expectancy=round(expectancy, 4),
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        win_loss_ratio=round(win_loss_ratio, 4),
        avg_holding_bars=round(avg_holding_bars, 2),
        sharpe_ratio=round(sharpe_ratio, 4),
        sortino_ratio=round(sortino_ratio, 4),
        calmar_ratio=round(calmar_ratio, 4),
        ambiguous_trade_count=ambiguous_count
    )

    cost_breakdown = CostBreakdown(
        total_gross_pnl=round(total_gross_pnl, 4),
        total_fees_paid=round(total_fees_paid, 4),
        maker_fees_paid=0.0,
        taker_fees_paid=round(total_fees_paid, 4),
        total_slippage_cost=round(total_slippage_cost, 4),
        total_funding_paid=round(total_funding_paid, 4),
        total_funding_received=round(total_funding_received, 4),
        net_pnl=round(net_profit, 4)
    )

    return metrics, cost_breakdown
