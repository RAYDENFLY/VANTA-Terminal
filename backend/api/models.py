from fastapi import APIRouter
from backend.schemas.models import ModelArenaResponse
from backend.fixtures.demo_data import get_demo_models

router = APIRouter(prefix="/models", tags=["Model Arena"])

@router.get("", response_model=ModelArenaResponse)
def get_models():
    configs = get_demo_models()
    return ModelArenaResponse(
        frozen_strategy_reference="STRAT-SWEEP-01",
        target_definition="Triple-Barrier TP before SL/Expiry (Binary)",
        configurations=configs,
        oos_unlocked=False,
        is_demo_data=True,
        notice="PRE-COMPUTATION BENCHMARK DEMO FIXTURES · PENDING PHASE 5"
    )
