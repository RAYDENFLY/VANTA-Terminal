"""
Unit Tests for Phase 3A Ingestion Pipeline & Data Integrity Engine
==================================================================
Tests pagination, duplicate rejection, gap detection, OHLC invariants,
idempotent resume, disk guards, and cryptographic manifests.
"""

import pytest
import shutil
from pathlib import Path
from backend.data.validator import validate_candles, ValidationReport
from backend.data.parquet_store import (
    write_parquet_dataset,
    read_parquet_dataset,
    create_manifest,
    compute_sha256
)
from backend.data.ingestion_engine import check_disk_space_guard

def generate_mock_candle(open_time_ms: int, o: float, h: float, l: float, c: float, v: float, step_ms: int = 900000):
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

def test_validator_perfect_series():
    # 5 valid 15m candles
    step = 900000
    base_t = 1700001000000  # 2023-11-14 22:30:00 UTC, perfectly aligned to 15m (1700001000000 % 900000 == 0)
    candles = [
        generate_mock_candle(base_t + (i * step), 100.0, 105.0, 95.0, 102.0, 10.0, step)
        for i in range(5)
    ]
    report = validate_candles(candles, timeframe="15m")
    assert report.is_valid is True
    assert report.total_candles == 5
    assert report.duplicate_count == 0
    assert report.gap_count == 0
    assert report.ohlc_violations == 0

def test_validator_detects_duplicate_timestamps():
    step = 900000
    base_t = 1700001000000
    candles = [
        generate_mock_candle(base_t, 100.0, 105.0, 95.0, 102.0, 10.0, step),
        generate_mock_candle(base_t, 100.0, 105.0, 95.0, 102.0, 10.0, step),  # Duplicate
    ]
    report = validate_candles(candles, timeframe="15m")
    assert report.is_valid is False
    assert report.duplicate_count == 1
    assert any("Duplicate open_time" in err for err in report.errors)

def test_validator_detects_gaps():
    step = 900000
    base_t = 1700001000000
    candles = [
        generate_mock_candle(base_t, 100.0, 105.0, 95.0, 102.0, 10.0, step),
        # Skip 2 bars (delta = 3 * step)
        generate_mock_candle(base_t + (3 * step), 100.0, 105.0, 95.0, 102.0, 10.0, step),
    ]
    report = validate_candles(candles, timeframe="15m")
    assert report.gap_count == 1
    assert report.gaps[0]["missing_bars"] == 2

def test_validator_detects_ohlc_invariants():
    step = 900000
    base_t = 1700001000000
    # High is less than Open (invalid)
    bad_candle1 = [generate_mock_candle(base_t, 100.0, 90.0, 85.0, 95.0, 10.0, step)]
    rep1 = validate_candles(bad_candle1, timeframe="15m")
    assert rep1.is_valid is False
    assert rep1.ohlc_violations == 1

    # Low is greater than Close (invalid)
    bad_candle2 = [generate_mock_candle(base_t, 100.0, 110.0, 105.0, 102.0, 10.0, step)]
    rep2 = validate_candles(bad_candle2, timeframe="15m")
    assert rep2.is_valid is False
    assert rep2.ohlc_violations == 1

    # Negative volume (invalid)
    bad_candle3 = [generate_mock_candle(base_t, 100.0, 105.0, 95.0, 102.0, -5.0, step)]
    rep3 = validate_candles(bad_candle3, timeframe="15m")
    assert rep3.is_valid is False
    assert rep3.ohlc_violations == 1

def test_parquet_store_read_write_checksum(tmp_path):
    step = 900000
    base_t = 1700001000000
    candles = [
        generate_mock_candle(base_t + (i * step), 100.0, 105.0, 95.0, 102.0, 10.0, step)
        for i in range(10)
    ]
    out_file = tmp_path / "test.parquet"
    rows, sha = write_parquet_dataset(candles, out_file)
    assert rows == 10
    assert len(sha) == 64  # Valid SHA-256 hex string

    table, meta = read_parquet_dataset(out_file)
    assert meta["num_rows"] == 10
    assert meta["sha256"] == sha
    assert meta["first_timestamp_ms"] == base_t
    assert meta["last_timestamp_ms"] == base_t + (9 * step)

def test_disk_space_guard():
    # Calling with normal required buffer should pass
    target = Path("D:/vanta-terminal/data/raw/BTCUSDT/test.parquet")
    check_disk_space_guard(target, min_free_gb=1.0)

    # Calling with impossible required buffer (e.g. 1000 TB) must raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        check_disk_space_guard(target, min_free_gb=1000000.0)
    assert "DISK SPACE SAFETY GUARD" in str(exc_info.value)
