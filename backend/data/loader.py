"""
VANTA Terminal — Research Dataset Loader & Holdout Quarantine Guard
===================================================================
Enforces the strict chronological quarantine boundary for Phase 4 and Phase 5.
Guarantees that no candle at or after 2026-04-26T00:00:00Z enters training,
parameter selection, or validation.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import pyarrow.parquet as pq

from backend.data.parquet_store import read_parquet_dataset, compute_sha256

# Exactly 2026-04-26T00:00:00Z in Unix Epoch Milliseconds
HOLDOUT_CUTOFF_MS: int = 1777161600000

# 48-Hour Purge & Embargo Milliseconds
PURGE_DURATION_MS: int = 48 * 3600 * 1000   # 172,800,000 ms
EMBARGO_DURATION_MS: int = 48 * 3600 * 1000 # 172,800,000 ms


class QuarantinedHoldoutViolationError(Exception):
    """Raised when an operation attempts to access or process candles from the Phase 6 quarantined holdout."""
    pass


def is_in_quarantined_holdout(timestamp_ms: int) -> bool:
    """Returns True if the timestamp falls at or after the holdout quarantine boundary."""
    return timestamp_ms >= HOLDOUT_CUTOFF_MS


def filter_candles_holdout_guard(
    raw_candles: List[List[Any]],
    raise_on_holdout_access: bool = False
) -> List[List[Any]]:
    """
    Applies the quarantine guard to a list of raw candles.
    Returns only candles strictly before 2026-04-26T00:00:00Z.
    """
    filtered = []
    quarantined_detected = 0

    for candle in raw_candles:
        open_time = int(candle[0])
        if open_time < HOLDOUT_CUTOFF_MS:
            filtered.append(candle)
        else:
            quarantined_detected += 1

    if quarantined_detected > 0 and raise_on_holdout_access:
        raise QuarantinedHoldoutViolationError(
            f"CRITICAL SECURITY GUARD: {quarantined_detected} candles at or after "
            f"2026-04-26T00:00:00Z (timestamp {HOLDOUT_CUTOFF_MS}) were intercepted. "
            "Quarantined holdout access is strictly prohibited in Phase 4 and Phase 5."
        )

    return filtered


def load_research_dataset(
    parquet_path: Path,
    enforce_holdout_guard: bool = True
) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """
    Loads historical candles from a Parquet dataset for research/backtesting.
    When enforce_holdout_guard=True, guarantees no candle at or after the holdout boundary is loaded.
    """
    table, meta = read_parquet_dataset(parquet_path)
    pydict = table.to_pydict()
    row_count = len(pydict["open_time"])

    raw_candles = []
    for i in range(row_count):
        raw_candles.append([
            int(pydict["open_time"][i]),
            float(pydict["open"][i]),
            float(pydict["high"][i]),
            float(pydict["low"][i]),
            float(pydict["close"][i]),
            float(pydict["volume"][i]),
            int(pydict["close_time"][i])
        ])

    if enforce_holdout_guard:
        raw_candles = filter_candles_holdout_guard(raw_candles, raise_on_holdout_access=False)

    summary = {
        "loaded_candles": len(raw_candles),
        "holdout_guarded": enforce_holdout_guard,
        "holdout_cutoff_utc": "2026-04-26T00:00:00Z",
        "first_timestamp_ms": raw_candles[0][0] if raw_candles else 0,
        "last_timestamp_ms": raw_candles[-1][0] if raw_candles else 0,
        "sha256": meta["sha256"]
    }

    return raw_candles, summary


def generate_walk_forward_splits(
    candles: List[List[Any]],
    is_start_ms: int,
    is_end_ms: int,
    oos_end_ms: int,
    purge_ms: int = PURGE_DURATION_MS,
    embargo_ms: int = EMBARGO_DURATION_MS
) -> Dict[str, List[List[Any]]]:
    """
    Generates In-Sample and Out-Of-Sample candle slices with 48h purge and embargo.
    Enforces the holdout guard so oos_end_ms cannot exceed HOLDOUT_CUTOFF_MS.
    """
    if oos_end_ms > HOLDOUT_CUTOFF_MS:
        raise QuarantinedHoldoutViolationError(
            f"Requested OOS end {oos_end_ms} breaches holdout boundary {HOLDOUT_CUTOFF_MS}."
        )

    # In-Sample signal generation stops at (is_end_ms - purge_ms)
    is_signal_cutoff_ms = is_end_ms - purge_ms
    # Out-of-Sample signal evaluation starts at (is_end_ms + embargo_ms)
    oos_signal_start_ms = is_end_ms + embargo_ms

    is_candles = [c for c in candles if is_start_ms <= c[0] < is_end_ms]
    oos_candles = [c for c in candles if is_end_ms <= c[0] < oos_end_ms]

    return {
        "in_sample": is_candles,
        "out_of_sample": oos_candles,
        "is_signal_cutoff_ms": is_signal_cutoff_ms,
        "oos_signal_start_ms": oos_signal_start_ms,
        "purge_ms": purge_ms,
        "embargo_ms": embargo_ms
    }
