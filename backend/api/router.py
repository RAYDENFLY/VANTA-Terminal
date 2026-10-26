from fastapi import APIRouter
from backend.api.health import router as health_router
from backend.api.pairs import router as pairs_router
from backend.api.experiments import router as experiments_router
from backend.api.data import router as data_router
from backend.api.strategies import router as strategies_router
from backend.api.models import router as models_router
from backend.api.backtest import router as backtest_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(pairs_router)
api_router.include_router(experiments_router)
api_router.include_router(data_router)
api_router.include_router(strategies_router)
api_router.include_router(models_router)
api_router.include_router(backtest_router)
