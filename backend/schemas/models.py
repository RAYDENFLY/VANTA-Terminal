from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ModelConfigResult(BaseModel):
    config_id: str
    name: str
    architecture: str
    description: str
    training_scope: str
    features_count: int
    val_brier_score: float
    val_roc_auc: float
    val_sharpe: float
    val_max_drawdown_pct: float
    val_win_rate_pct: float
    sample_size_trades: int
    bootstrap_sharpe_ci95: List[float]
    status: str  # CANDIDATE, BENCHMARKED, NOT_EVALUATED
    is_demo_data: bool = True

class ModelArenaResponse(BaseModel):
    frozen_strategy_reference: Optional[str] = "SWEEP_RECLAIM_V1"
    target_definition: str = "Triple-Barrier TP before SL/Expiry (Binary)"
    configurations: List[ModelConfigResult]
    oos_unlocked: bool = False
    is_demo_data: bool = True
    notice: str = "PRE-COMPUTATION BENCHMARK DEMO FIXTURES · PENDING PHASE 5"
