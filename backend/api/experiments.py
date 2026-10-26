from fastapi import APIRouter, Query
from typing import Optional
from backend.schemas.experiments import ExperimentsListResponse
from backend.fixtures.demo_data import get_demo_experiments

router = APIRouter(prefix="/experiments", tags=["Experiment Registry"])

# In-memory registry for Phase 1 MVP (clearly documented as non-persistent demo registry)
_DEMO_EXPERIMENTS = get_demo_experiments()

@router.get("", response_model=ExperimentsListResponse)
def list_experiments(status: Optional[str] = Query(None)):
    filtered = _DEMO_EXPERIMENTS
    if status:
        filtered = [exp for exp in _DEMO_EXPERIMENTS if exp.status.upper() == status.upper()]
    
    active_run = next((exp for exp in _DEMO_EXPERIMENTS if exp.status in ["RUNNING", "QUEUED"]), None)
    
    return ExperimentsListResponse(
        total_count=len(filtered),
        active_run=active_run,
        experiments=filtered,
        is_demo_data=True,
        storage_engine="In-Memory Registry (Phase 1 MVP)"
    )
