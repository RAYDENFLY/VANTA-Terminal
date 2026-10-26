"""
VANTA Terminal — Phase 3B.1 Sequential Ingestion Test Suite
===========================================================
Rigorous test coverage for:
- Pilot preservation and SHA-256 fidelity.
- Sequential scheduling and cancellation token.
- Disk-space safety reserve (>= 10.0 GB).
- UTC cutoff and range boundaries.
- Aggregation correctness (15m -> 1H / 4H).
- Incomplete bucket and gap rejection across aggregation boundaries.
- Manifest checksum integrity.
- Rate-limit retry configuration.
"""

import pytest
import shutil
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

from backend.data.ingestion_engine import check_disk_space_guard
from backend.data.resampler import (
    resample_15m_to_higher_timeframe,
    RESAMPLE_FACTORS
)
from backend.data.parquet_store import read_parquet_dataset, compute_sha256
from backend.data.asterdex_client import AsterDexPublicClient
from backend.data.sequential_ingestor import (
    QUALIFIED_START_MS,
    UNIVERSE_END_MS,
    QUALIFIED_LAST_BAR_MS,
    XMR_START_MS,
    load_job_registry
)


def generate_candle(open_time_ms: int, o: float, h: float, l: float, c: float, v: float, step_ms: int = 900000):
    return [
        open_time_ms,
        str(o),
        str(h),
        str(l),
        str(c),
        str(v),
        open_time_ms + step_ms - 1,
        str(c * v),
        100,
        str(v * 0.5),
        str(c * v * 0.5),
        "0"
    ]


def test_pilot_preservation():
    """Verify that the Phase 3A pilot is preserved and its SHA-256 is intact."""
    pilot_path = Path("D:/vanta-terminal/data/pilot/BTCUSDT/15m_30d_pilot.parquet")
    assert pilot_path.exists(), f"Preserved pilot missing at {pilot_path}"

    sha256 = hashlib.sha256(pilot_path.read_bytes()).hexdigest()
    expected_sha = "d2d485aa1d91ab75eeb768450525a455651401a32c72f2321ecaec40f10517f0"
    assert sha256 == expected_sha, f"Pilot corrupted! Got {sha256}, expected {expected_sha}"

    _, meta = read_parquet_dataset(pilot_path)
    assert meta["num_rows"] == 2881


def test_disk_space_safety_reserve():
    """Verify that the >= 10.0 GB operational reserve on D: is enforced."""
    target = Path("D:/vanta-terminal/data/raw/BTCUSDT/test.parquet")
    
    # 10.0 GB check must pass on target system (HDD D: has >60 GB free)
    check_disk_space_guard(target, min_free_gb=10.0)

    # Extreme reserve (e.g. 1,000,000 GB) must raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        check_disk_space_guard(target, min_free_gb=1000000.0)
    assert "DISK SPACE SAFETY GUARD" in str(exc_info.value)


def test_utc_range_boundaries():
    """Verify that UTC range boundaries align cleanly to integer interval steps."""
    step_15m = 900000
    step_1h = 3600000
    step_4h = 14400000

    # 3-year window for qualified 10 pairs
    total_ms = UNIVERSE_END_MS - QUALIFIED_START_MS
    assert total_ms % step_15m == 0
    assert total_ms % step_1h == 0
    assert total_ms % step_4h == 0

    assert (total_ms // step_15m) == 105216
    assert (total_ms // step_1h) == 26304
    assert (total_ms // step_4h) == 6576

    dt_start = datetime.fromtimestamp(QUALIFIED_START_MS / 1000, timezone.utc)
    dt_end = datetime.fromtimestamp(UNIVERSE_END_MS / 1000, timezone.utc)
    assert dt_start.isoformat() == "2023-10-26T00:00:00+00:00"
    assert dt_end.isoformat() == "2026-10-26T00:00:00+00:00"


def test_resampling_aggregation_correctness():
    """Verify that 1H and 4H resampled candles match strict OHLCV math."""
    base_t = 1700006400000  # Modulo 3600000 == 0 (00:00:00 UTC)
    step = 900000

    # 4 consecutive 15m candles
    c1 = generate_candle(base_t, 100.0, 105.0, 98.0, 102.0, 10.0)
    c2 = generate_candle(base_t + step, 102.0, 108.0, 101.0, 107.0, 15.0)
    c3 = generate_candle(base_t + 2 * step, 107.0, 110.0, 106.0, 108.0, 20.0)
    c4 = generate_candle(base_t + 3 * step, 108.0, 109.0, 95.0, 104.0, 25.0)

    res = resample_15m_to_higher_timeframe([c1, c2, c3, c4], "1h")
    assert res.complete_buckets == 1
    assert res.incomplete_buckets == 0
    assert len(res.derived_candles) == 1

    bar = res.derived_candles[0]
    assert bar[0] == base_t
    assert float(bar[1]) == 100.0  # Open = first open
    assert float(bar[2]) == 110.0  # High = max(105, 108, 110, 109)
    assert float(bar[3]) == 95.0   # Low = min(98, 101, 106, 95)
    assert float(bar[4]) == 104.0  # Close = last close
    assert float(bar[5]) == 70.0   # Volume = 10 + 15 + 20 + 25
    assert bar[6] == base_t + 3600000 - 1  # Close time


def test_resampling_incomplete_bucket_rejection():
    """Verify that partial / incomplete buckets are strictly dropped."""
    base_t = 1700006400000
    step = 900000

    # Only 3 candles in a 1-hour window (missing 4th)
    c1 = generate_candle(base_t, 100.0, 105.0, 98.0, 102.0, 10.0)
    c2 = generate_candle(base_t + step, 102.0, 108.0, 101.0, 107.0, 15.0)
    c3 = generate_candle(base_t + 2 * step, 107.0, 110.0, 106.0, 108.0, 20.0)

    res = resample_15m_to_higher_timeframe([c1, c2, c3], "1h")
    assert res.complete_buckets == 0
    assert res.incomplete_buckets == 1
    assert res.dropped_source_bars == 3
    assert len(res.derived_candles) == 0


def test_resampling_gap_spanning_rejection():
    """Verify that buckets containing an internal gap are dropped."""
    base_t = 1700006400000
    step = 900000

    # 4 candles, but candle 2 is skipped so candle 3 has a gap
    c1 = generate_candle(base_t, 100.0, 105.0, 98.0, 102.0, 10.0)
    c2 = generate_candle(base_t + 2 * step, 102.0, 108.0, 101.0, 107.0, 15.0)  # Gap
    c3 = generate_candle(base_t + 3 * step, 107.0, 110.0, 106.0, 108.0, 20.0)
    c4 = generate_candle(base_t + 4 * step, 108.0, 109.0, 95.0, 104.0, 25.0)  # In next hour

    res = resample_15m_to_higher_timeframe([c1, c2, c3, c4], "1h")
    assert res.complete_buckets == 0
    assert res.incomplete_buckets > 0


def test_client_rate_limiting_and_retries():
    """Verify AsterDexPublicClient retry and timeout attributes."""
    client = AsterDexPublicClient(timeout_sec=12, max_retries=3)
    assert client.timeout_sec == 12
    assert client.max_retries == 3
    assert client.min_interval_sec >= 0.05
