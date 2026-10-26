from fastapi import APIRouter, HTTPException
from pathlib import Path
from backend.schemas.data import DataCoverageResponse
from backend.data.coverage_audit import get_coverage_response
from backend.data.ingestion_engine import run_bounded_ingestion, CURRENT_INGESTION_STATE

router = APIRouter(prefix="/data", tags=["Data Center"])

@router.get("/coverage", response_model=DataCoverageResponse)
def get_data_coverage():
    return get_coverage_response()

@router.get("/ingestion/current")
def get_current_ingestion_state():
    return CURRENT_INGESTION_STATE

@router.post("/ingestion/pilot")
def run_pilot_ingestion():
    """
    Executes the Phase 3A authorized bounded pilot:
    BTCUSDT 15m for 30 days.
    """
    try:
        # Bounded 30 days window: 2026-09-26 22:30 UTC to 2026-10-26 22:30 UTC
        start_ms = 1790461800000
        end_ms = 1793053800000
        dataset_id = "ASTERDEX_BTCUSDT_15M_30D_PILOT"
        output_file = Path("D:/vanta-terminal/data/raw/BTCUSDT/15m.parquet")

        result = run_bounded_ingestion(
            symbol="BTCUSDT",
            timeframe="15m",
            start_time_ms=start_ms,
            end_time_ms=end_ms,
            dataset_id=dataset_id,
            output_path=output_file
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
