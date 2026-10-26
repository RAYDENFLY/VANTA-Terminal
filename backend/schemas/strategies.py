from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CostAssumptions(BaseModel):
    maker_fee_pct: float = 0.02
    taker_fee_pct: float = 0.05
    base_slippage_bps: float = 2.0
    funding_accrual_hours: int = 8
    same_bar_ambiguity: str = "WORST_CASE_STOP_FIRST"

class StrategyCandidate(BaseModel):
    id: str
    name: str
    family: str
    description: str
    status: str  # CANDIDATE, FROZEN, REJECTED, PENDING_EVALUATION
    entry_logic: str
    stop_loss_logic: str
    take_profit_logic: str
    trades_count: int
    win_rate_pct: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown_pct: float
    expectancy_r: float
    avg_holding_bars: float
    is_demo_data: bool = True

class StrategyLabResponse(BaseModel):
    frozen_strategy_id: Optional[str] = None
    cost_framework: CostAssumptions
    candidates: List[StrategyCandidate]
    qualification_criteria: Dict[str, Any] = {
        "max_drawdown_pct": 15.0,
        "min_net_expectancy_bps": 8.0,
        "min_profit_factor": 1.25,
        "min_total_trades": 150,
        "min_pair_trades": 20,
        "min_wf_consistency_folds": "2 of 3",
        "min_cross_pair_positive": "7 of 11",
        "friction_stress_tolerance": "Profitable at 1.5x friction (7.5 bps fee, 3.0 bps slip)",
        "fallback_protocol": "NO_QUALIFIED_STRATEGY"
    }
    is_demo_data: bool = True
    notice: str = "PHASE 4A PROTOCOL SPECIFIED · BENCHMARK EXECUTION PENDING PHASE 4B"
