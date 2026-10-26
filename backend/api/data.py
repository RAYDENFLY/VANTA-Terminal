from fastapi import APIRouter
from backend.schemas.data import DataCoverageResponse
from backend.data.coverage_audit import get_coverage_response

router = APIRouter(prefix="/data", tags=["Data Center"])

@router.get("/coverage", response_model=DataCoverageResponse)
def get_data_coverage():
    return get_coverage_response()
