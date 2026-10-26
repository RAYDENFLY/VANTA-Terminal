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
        "min_trades": 100,
        "min_sharpe": 1.0,
        "max_drawdown_pct": 25.0,
        "min_profit_factor": 1.25
    }
    is_demo_data: bool = True
    notice: str = "SIMULATION VALIDATION FIXTURES · SELECTION PENDING PHASE 4"
