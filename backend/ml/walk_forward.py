"""
VANTA Terminal — Machine Learning Walk-Forward Schedule & Slicing
==================================================================
Defines the frozen 3-fold Walk-Forward evaluation partitions according to
docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md (Section 6).

Key Invariants:
1. Strict 48-Hour Purge: Guarantees zero label leakage (H=12h << 48h).
2. Strict 48-Hour Embargo: Prevents information overlap prior to OOS.
3. Universal Holdout Quarantine: open_time >= 2026-04-26T00:00:00Z (1777161600000) is strictly blocked.
4. 150-Bar Warmup Buffer: Pre-pended before each partition start to ensure >99.75% convergence.
5. In-Sample Label Window Boundary Isolation: Last 12 bars of IS are masked to NaN.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np

from backend.data.loader import HOLDOUT_CUTOFF_MS, QuarantinedHoldoutViolationError


@dataclass(frozen=True)
class WalkForwardFold:
    fold_id: int
    is_start_utc: str
    is_end_utc: str
    purge_start_utc: str
    purge_end_utc: str
    embargo_start_utc: str
    embargo_end_utc: str
    oos_start_utc: str
    oos_end_utc: str

    is_start_ms: int
    is_end_ms: int
    purge_start_ms: int
    purge_end_ms: int
    embargo_start_ms: int
    embargo_end_ms: int
    oos_start_ms: int
    oos_end_ms: int


# Pre-registered 3-fold walk-forward schedule (timestamps in epoch ms)
FOLDS_SCHEDULE: List[WalkForwardFold] = [
    WalkForwardFold(
        fold_id=1,
        is_start_utc="2023-10-26 00:00:00 UTC",
        is_end_utc="2024-10-24 00:00:00 UTC",
        purge_start_utc="2024-10-24 00:00:00 UTC",
        purge_end_utc="2024-10-26 00:00:00 UTC",
        embargo_start_utc="2024-10-26 00:00:00 UTC",
        embargo_end_utc="2024-10-28 00:00:00 UTC",
        oos_start_utc="2024-10-28 00:00:00 UTC",
        oos_end_utc="2025-04-26 00:00:00 UTC",
        is_start_ms=1698278400000,
        is_end_ms=1729728000000,
        purge_start_ms=1729728000000,
        purge_end_ms=1729900800000,
        embargo_start_ms=1729900800000,
        embargo_end_ms=1730073600000,
        oos_start_ms=1730073600000,
        oos_end_ms=1745625600000,
    ),
    WalkForwardFold(
        fold_id=2,
        is_start_utc="2024-04-26 00:00:00 UTC",
        is_end_utc="2025-04-24 00:00:00 UTC",
        purge_start_utc="2025-04-24 00:00:00 UTC",
        purge_end_utc="2025-04-26 00:00:00 UTC",
        embargo_start_utc="2025-04-26 00:00:00 UTC",
        embargo_end_utc="2025-04-28 00:00:00 UTC",
        oos_start_utc="2025-04-28 00:00:00 UTC",
        oos_end_utc="2025-10-26 00:00:00 UTC",
        is_start_ms=1714089600000,
        is_end_ms=1745452800000,
        purge_start_ms=1745452800000,
        purge_end_ms=1745625600000,
        embargo_start_ms=1745625600000,
        embargo_end_ms=1745798400000,
        oos_start_ms=1745798400000,
        oos_end_ms=1761436800000,
    ),
    WalkForwardFold(
        fold_id=3,
        is_start_utc="2024-10-26 00:00:00 UTC",
        is_end_utc="2025-10-24 00:00:00 UTC",
        purge_start_utc="2025-10-24 00:00:00 UTC",
        purge_end_utc="2025-10-26 00:00:00 UTC",
        embargo_start_utc="2025-10-26 00:00:00 UTC",
        embargo_end_utc="2025-10-28 00:00:00 UTC",
        oos_start_utc="2025-10-28 00:00:00 UTC",
        oos_end_utc="2026-04-26 00:00:00 UTC",
        is_start_ms=1729900800000,
        is_end_ms=1761264000000,
        purge_start_ms=1761264000000,
        purge_end_ms=1761436800000,
        embargo_start_ms=1761436800000,
        embargo_end_ms=1761609600000,
        oos_start_ms=1761609600000,
        oos_end_ms=1777161600000,
    ),
]

WARMUP_BARS: int = 150
WARMUP_MS: int = WARMUP_BARS * 3600 * 1000  # 150 hours = 540,000,000 ms


def get_fold_schedule(fold_id: int) -> WalkForwardFold:
    """Returns the WalkForwardFold specification for fold_id."""
    for f in FOLDS_SCHEDULE:
        if f.fold_id == fold_id:
            return f
    raise ValueError(f"Invalid fold_id {fold_id}. Must be 1, 2, or 3.")
