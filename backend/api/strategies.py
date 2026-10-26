from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.schemas.strategies import StrategyLabResponse, CostAssumptions
from backend.fixtures.demo_data import get_demo_strategies

router = APIRouter(prefix="/strategies", tags=["Strategy Lab"])

# In-memory candidate registry for Phase 1
_STRATEGY_CANDIDATES = get_demo_strategies()
_FROZEN_STRATEGY_ID: Optional[str] = None

class FreezeStrategyRequest(BaseModel):
    strategy_id: str

@router.get("", response_model=StrategyLabResponse)
def get_strategies():
    return StrategyLabResponse(
        frozen_strategy_id=_FROZEN_STRATEGY_ID,
        cost_framework=CostAssumptions(),
        candidates=_STRATEGY_CANDIDATES,
        is_demo_data=True,
        notice="SIMULATION VALIDATION FIXTURES · SELECTION PENDING PHASE 4"
    )

@router.post("/freeze")
def freeze_strategy(payload: FreezeStrategyRequest):
    global _FROZEN_STRATEGY_ID
    target = next((s for s in _STRATEGY_CANDIDATES if s.id == payload.strategy_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Strategy '{payload.strategy_id}' not found.")
    
    _FROZEN_STRATEGY_ID = payload.strategy_id
    for s in _STRATEGY_CANDIDATES:
        if s.id == payload.strategy_id:
            s.status = "FROZEN"
        else:
            s.status = "REJECTED"
            
    return {
        "status": "frozen",
        "strategy_id": _FROZEN_STRATEGY_ID,
        "strategy_name": target.name,
        "message": f"Strategy {target.name} frozen as base for ML model arena.",
        "is_demo_data": True
    }
