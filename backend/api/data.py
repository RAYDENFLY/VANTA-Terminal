from fastapi import APIRouter
from backend.core.telemetry import get_disk_usage
from backend.schemas.data import DataCoverageResponse
from backend.fixtures.demo_data import get_demo_coverage

router = APIRouter(prefix="/data", tags=["Data Center"])

@router.get("/coverage", response_model=DataCoverageResponse)
def get_data_coverage():
    coverage_list = get_demo_coverage()
    disk_info = get_disk_usage("D:\\")
    return DataCoverageResponse(
        total_pairs=len(coverage_list),
        verified_pairs=0,
        pending_audit_pairs=len(coverage_list),
        total_raw_storage_mb=0.0,
        disk_free_gb=disk_info.get("free_gb") or 0.0,
        coverage=coverage_list,
        is_demo_data=True,
        notice="Awaiting Phase 2 AsterDEX data coverage audit"
    )
