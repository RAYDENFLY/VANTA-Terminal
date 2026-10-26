from fastapi import APIRouter, HTTPException
from pathlib import Path
from backend.schemas.data import DataCoverageResponse
from backend.data.coverage_audit import get_coverage_response
from backend.data.ingestion_engine import run_bounded_ingestion, CURRENT_INGESTION_STATE
from backend.data.sequential_ingestor import load_job_registry, CANCEL_SIGNAL_FILE

router = APIRouter(prefix="/data", tags=["Data Center"])

@router.get("/coverage", response_model=DataCoverageResponse)
def get_data_coverage():
    return get_coverage_response()

@router.get("/ingestion/current")
def get_current_ingestion_state():
    return CURRENT_INGESTION_STATE

@router.get("/ingestion/registry")
def get_ingestion_registry():
    """Returns the persistent 33-dataset sequential ingestion registry."""
    try:
        return load_job_registry()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingestion/cancel")
def cancel_ingestion_job():
    """Signals the running sequential ingestion job to gracefully halt."""
    CANCEL_SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    CANCEL_SIGNAL_FILE.touch()
    return {"status": "CANCEL_SIGNAL_ISSUED", "message": "Sequential ingestion will halt after the current dataset completes."}

@router.post("/ingestion/pilot")
def run_pilot_ingestion():
    """
    Executes or verifies the Phase 3A authorized bounded pilot:
    BTCUSDT 15m for 30 days. Uses preserved pilot location.
    """
    try:
        start_ms = 1790461800000
        end_ms = 1793053800000
        dataset_id = "ASTERDEX_BTCUSDT_15M_30D_PILOT"
        output_file = Path("D:/vanta-terminal/data/pilot/BTCUSDT/15m_30d_pilot.parquet")

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
