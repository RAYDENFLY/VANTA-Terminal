"""
VANTA Terminal — Strategy Qualification Gates & Evaluator
=========================================================
Implements the frozen acceptance gates, exact pair denominators,
zero-trade failure rules, and mandatory fallback protocol.
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import math
from pydantic import BaseModel, Field

# The 10 Qualified Pairs with >=3-year verified history
QUALIFIED_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "LTCUSDT"
]

# Partial history pair (Auxiliary observer, excluded from spatial denominator)
PARTIAL_HISTORY_PAIRS = ["XMRUSDT"]


class PairLifecycleState(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    PARTIAL_HISTORY = "PARTIAL_HISTORY"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"


class GateResult(BaseModel):
    gate_id: str
    gate_name: str
    hurdle: str
    observed_value: Any
    denominator: str
    passed: bool
    details: str = ""


class UniverseEvaluationSummary(BaseModel):
    strategy_id: str
    certified_baseline: bool
    status: str  # QUALIFIED_BASELINE or NO_QUALIFIED_STRATEGY
    gates: List[GateResult]
    pair_states: Dict[str, PairLifecycleState]
    summary_metrics: Dict[str, Any]
    fallback_notice: Optional[str] = None


def calculate_net_expectancy_ci(
    net_returns: List[float],
    confidence: float = 0.95
) -> Tuple[float, float, Tuple[float, float]]:
    """
    Calculates sample mean, standard error, and Student's t 95% confidence interval
    for trade net returns relative to entry notional.
    """
    n = len(net_returns)
    if n == 0:
        return 0.0, 0.0, (0.0, 0.0)

    mean = sum(net_returns) / n
    if n == 1:
        return mean, 0.0, (mean, mean)

    var = sum((x - mean) ** 2 for x in net_returns) / (n - 1)
    std = math.sqrt(var)
    sem = std / math.sqrt(n)

    # 95% t-critical approximation for large n or exact for standard sizes
    # (for n >= 30, t_0.975 ~ 1.96-2.04)
    t_crit = 1.96 if n >= 120 else 2.00
    ci_lower = mean - t_crit * sem
    ci_upper = mean + t_crit * sem

    return mean, sem, (ci_lower, ci_upper)


def evaluate_qualification_gates(
    strategy_id: str,
    max_drawdown_pct: float,
    trade_notionals: List[float],
    net_pnls: List[float],
    pair_trades: Dict[str, List[float]],  # symbol -> list of net_pnls
    fold_net_pnls: List[float],           # length 3 (Folds 1, 2, 3)
    stress_net_pnl: float,
    stress_profit_factor: float
) -> UniverseEvaluationSummary:
    """
    Evaluates a candidate strategy against the 8 frozen qualification gates.
    """
    # 1. GATE-1: Maximum Drawdown (<= 15.0%)
    gate1_pass = max_drawdown_pct <= 15.0
    g1 = GateResult(
        gate_id="GATE-1",
        gate_name="Maximum Drawdown (MDD)",
        hurdle="<= 15.0%",
        observed_value=round(max_drawdown_pct, 2),
        denominator="Continuous Equity Curve",
        passed=gate1_pass,
        details="Passes" if gate1_pass else f"Exceeds 15.0% threshold (Observed: {max_drawdown_pct:.2f}%)"
    )

    # 2. GATE-2: Net Expectancy per Trade (>= +8.0 bps on Entry Notional)
    net_returns = []
    for notional, pnl in zip(trade_notionals, net_pnls):
        if notional > 0:
            net_returns.append(pnl / notional)

    mean_exp, sem_exp, ci = calculate_net_expectancy_ci(net_returns)
    mean_bps = mean_exp * 10000.0
    gate2_pass = mean_bps >= 8.0
    g2 = GateResult(
        gate_id="GATE-2",
        gate_name="Net Expectancy per Trade",
        hurdle=">= +8.0 bps (+0.08%)",
        observed_value=f"{mean_bps:.2f} bps (95% CI: [{ci[0]*10000:.2f}, {ci[1]*10000:.2f}] bps)",
        denominator=f"Total Trades ({len(net_returns)})",
        passed=gate2_pass,
        details="Passes hurdle after 14 bps friction" if gate2_pass else "Fails hurdle"
    )

    # 3. GATE-3: Profit Factor (>= 1.25)
    gross_wins = sum(p for p in net_pnls if p > 0)
    gross_losses = sum(abs(p) for p in net_pnls if p < 0)
    if gross_losses == 0:
        pf = float("inf") if gross_wins > 0 else 0.0
    else:
        pf = gross_wins / gross_losses

    gate3_pass = pf >= 1.25
    g3 = GateResult(
        gate_id="GATE-3",
        gate_name="Profit Factor (PF)",
        hurdle=">= 1.25",
        observed_value=round(pf, 3) if not math.isinf(pf) else "INF",
        denominator="Net Realized PnL",
        passed=gate3_pass,
        details="Passes" if gate3_pass else f"Below 1.25 (Observed: {pf:.2f})"
    )

    # 4. GATE-4: Aggregate Trade Count (>= 150 across Qualified Pairs)
    total_qual_trades = sum(len(pair_trades.get(sym, [])) for sym in QUALIFIED_PAIRS)
    gate4_pass = total_qual_trades >= 150
    g4 = GateResult(
        gate_id="GATE-4",
        gate_name="Aggregate Trade Count",
        hurdle=">= 150 trades",
        observed_value=total_qual_trades,
        denominator="10 Qualified Pairs (OOS Folds 1-3)",
        passed=gate4_pass,
        details="Passes" if gate4_pass else f"Insufficient sample size ({total_qual_trades} < 150)"
    )

    # 5. GATE-5: Per-Pair Trade Count (>= 20 trades for each qualified pair)
    pair_states: Dict[str, PairLifecycleState] = {}
    failing_pairs = []
    for sym in QUALIFIED_PAIRS:
        trades = pair_trades.get(sym, [])
        count = len(trades)
        if count >= 20:
            pair_states[sym] = PairLifecycleState.ELIGIBLE
        else:
            pair_states[sym] = PairLifecycleState.INSUFFICIENT_SAMPLE
            failing_pairs.append(f"{sym} ({count} trades)")

    # XMRUSDT auxiliary state
    xmr_count = len(pair_trades.get("XMRUSDT", []))
    pair_states["XMRUSDT"] = PairLifecycleState.PARTIAL_HISTORY

    gate5_pass = len(failing_pairs) == 0
    g5 = GateResult(
        gate_id="GATE-5",
        gate_name="Per-Pair Minimum Trade Count",
        hurdle=">= 20 trades per qualified pair",
        observed_value=f"{10 - len(failing_pairs)} of 10 pairs >= 20",
        denominator="10 Qualified Pairs",
        passed=gate5_pass,
        details="All pairs satisfy minimum activity" if gate5_pass else f"Pairs with < 20 trades: {', '.join(failing_pairs)}"
    )

    # 6. GATE-6: Walk-Forward Consistency (>= 2 of 3 Folds Net Positive)
    positive_folds = sum(1 for pnl in fold_net_pnls if pnl > 0)
    gate6_pass = positive_folds >= 2
    g6 = GateResult(
        gate_id="GATE-6",
        gate_name="Walk-Forward Consistency",
        hurdle=">= 2 of 3 Folds Profitable",
        observed_value=f"{positive_folds} of 3 folds",
        denominator="3 Rolling WF Folds",
        passed=gate6_pass,
        details="Passes temporal stability" if gate6_pass else f"Only {positive_folds} of 3 folds profitable"
    )

    # 7. GATE-7: Spatial Robustness (>= 7 of 10 Qualified Pairs Net Positive)
    # FROZEN DENOMINATOR: Exactly 10 Qualified Pairs.
    # INSUFFICIENT_SAMPLE or 0 trades counts strictly as Net PnL <= 0 (FAIL).
    positive_pairs = 0
    pair_breakdown = {}
    for sym in QUALIFIED_PAIRS:
        pnls = pair_trades.get(sym, [])
        p_net = sum(pnls)
        # Pair must have >= 20 trades AND positive net PnL to count as pass
        if len(pnls) >= 20 and p_net > 0:
            positive_pairs += 1
            pair_breakdown[sym] = "PASS"
        else:
            pair_breakdown[sym] = "FAIL"

    gate7_pass = positive_pairs >= 7
    g7 = GateResult(
        gate_id="GATE-7",
        gate_name="Spatial Robustness",
        hurdle=">= 7 of 10 Qualified Pairs Profitable",
        observed_value=f"{positive_pairs} of 10 pairs",
        denominator="10 Qualified Pairs (Frozen Denominator)",
        passed=gate7_pass,
        details="Cross-pair generalizability confirmed" if gate7_pass else f"Only {positive_pairs} of 10 qualified pairs profitable"
    )

    # 8. GATE-8: Friction Stress Tolerance (Net PnL > 0 and PF > 1.0 at 1.5x friction)
    gate8_pass = (stress_net_pnl > 0) and (stress_profit_factor > 1.0)
    g8 = GateResult(
        gate_id="GATE-8",
        gate_name="Friction Stress Tolerance",
        hurdle="Net PnL > 0 and PF > 1.0 at 21.0 bps friction",
        observed_value=f"Net PnL: ${stress_net_pnl:.2f}, PF: {stress_profit_factor:.2f}",
        denominator="Stress Configuration (7.5 bps fee + 3.0 bps slip)",
        passed=gate8_pass,
        details="Passes friction resilience test" if gate8_pass else "Fragile to elevated execution friction"
    )

    all_gates = [g1, g2, g3, g4, g5, g6, g7, g8]
    all_passed = all(g.passed for g in all_gates)

    if all_passed:
        status = "QUALIFIED_BASELINE"
        fallback_notice = None
    else:
        status = "NO_QUALIFIED_STRATEGY"
        fallback_notice = (
            "MANDATORY FALLBACK TRIGGERED: Strategy failed one or more frozen qualification gates. "
            "Designated as UNQUALIFIED_BASELINE for reference only. Thresholds remain non-negotiable."
        )

    return UniverseEvaluationSummary(
        strategy_id=strategy_id,
        certified_baseline=all_passed,
        status=status,
        gates=all_gates,
        pair_states=pair_states,
        summary_metrics={
            "max_drawdown_pct": max_drawdown_pct,
            "net_expectancy_bps": mean_bps,
            "profit_factor": pf,
            "total_qualified_trades": total_qual_trades,
            "positive_folds": positive_folds,
            "positive_qualified_pairs": positive_pairs,
            "stress_net_pnl": stress_net_pnl,
            "stress_profit_factor": stress_profit_factor
        },
        fallback_notice=fallback_notice
    )
