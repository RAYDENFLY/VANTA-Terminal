from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ExperimentRecord(BaseModel):
    run_id: str
    config_hash: str
    dataset_version: str
    strategy_family: str
    model_architecture: str
    status: str  # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
    created_at: str
    runtime_seconds: Optional[float] = None
    peak_memory_mb: Optional[float] = None
    sample_size_trades: Optional[int] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    win_rate_pct: Optional[float] = None
    brier_score: Optional[float] = None
    is_demo_data: bool = True
    notes: str

class ExperimentsListResponse(BaseModel):
    total_count: int
    active_run: Optional[ExperimentRecord] = None
    experiments: List[ExperimentRecord]
    is_demo_data: bool = True
    storage_engine: str = "In-Memory Registry (Phase 1 MVP)"
