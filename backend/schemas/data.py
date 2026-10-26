from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TimeframeCoverage(BaseModel):
    timeframe: str
    available_bars: int
    earliest_candle: Optional[str] = None
    latest_candle: Optional[str] = None
    gap_count: int = 0
    coverage_pct: float = 0.0
    status: str = "PENDING_AUDIT"

class PairCoverageSummary(BaseModel):
    symbol: str
    target_history_years: float = 3.0
    verified_history_years: float = 0.0
    audit_status: str = "PENDING_PHASE_2"
    timeframes: Dict[str, TimeframeCoverage]
    raw_storage_mb: float = 0.0
    manifest_checksum: Optional[str] = None
    is_demo_data: bool = True

class DataCoverageResponse(BaseModel):
    total_pairs: int = 11
    verified_pairs: int = 0
    pending_audit_pairs: int = 11
    total_raw_storage_mb: float = 0.0
    disk_free_gb: float
    coverage: List[PairCoverageSummary]
    is_demo_data: bool = True
    notice: str = "Awaiting Phase 2 AsterDEX data coverage audit"
