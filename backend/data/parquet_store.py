"""
VANTA Terminal — Parquet Storage & Manifest Engine
==================================================
Writes strongly-typed Apache Parquet datasets using PyArrow.
Generates SHA-256 cryptographic manifests for reproducibility.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq

# Strongly typed schema for futures OHLCV
CANDLE_ARROW_SCHEMA = pa.schema([
    ("open_time", pa.int64()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("volume", pa.float64()),
    ("close_time", pa.int64()),
    ("quote_volume", pa.float64()),
    ("trades_count", pa.int64()),
    ("taker_buy_base", pa.float64()),
    ("taker_buy_quote", pa.float64()),
])

def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def candles_to_arrow_table(raw_candles: List[List[Any]]) -> pa.Table:
    """Converts raw list of candle lists into a typed PyArrow Table."""
    open_time = [int(c[0]) for c in raw_candles]
    open_p = [float(c[1]) for c in raw_candles]
    high_p = [float(c[2]) for c in raw_candles]
    low_p = [float(c[3]) for c in raw_candles]
    close_p = [float(c[4]) for c in raw_candles]
    volume = [float(c[5]) for c in raw_candles]
    close_time = [int(c[6]) for c in raw_candles]
    quote_vol = [float(c[7]) for c in raw_candles]
    trades_count = [int(c[8]) for c in raw_candles]
    taker_buy_base = [float(c[9]) for c in raw_candles]
    taker_buy_quote = [float(c[10]) for c in raw_candles]

    data = [
        pa.array(open_time, type=pa.int64()),
        pa.array(open_p, type=pa.float64()),
        pa.array(high_p, type=pa.float64()),
        pa.array(low_p, type=pa.float64()),
        pa.array(close_p, type=pa.float64()),
        pa.array(volume, type=pa.float64()),
        pa.array(close_time, type=pa.int64()),
        pa.array(quote_vol, type=pa.float64()),
        pa.array(trades_count, type=pa.int64()),
        pa.array(taker_buy_base, type=pa.float64()),
        pa.array(taker_buy_quote, type=pa.float64()),
    ]
    return pa.Table.from_arrays(data, schema=CANDLE_ARROW_SCHEMA)

def write_parquet_dataset(
    raw_candles: List[List[Any]],
    output_path: Path,
    compression: str = "SNAPPY"
) -> Tuple[int, str]:
    """
    Writes raw candles to an optimized Parquet file with Snappy compression.
    Returns (row_count, sha256_checksum).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = candles_to_arrow_table(raw_candles)
    pq.write_table(table, output_path, compression=compression)
    sha256 = compute_sha256(output_path)
    return len(raw_candles), sha256

def read_parquet_dataset(file_path: Path) -> Tuple[pa.Table, Dict[str, Any]]:
    """Reads a Parquet dataset and returns (table, summary_metadata)."""
    table = pq.read_table(file_path)
    sha256 = compute_sha256(file_path)
    first_time = table["open_time"][0].as_py() if table.num_rows > 0 else 0
    last_time = table["open_time"][-1].as_py() if table.num_rows > 0 else 0
    size_bytes = file_path.stat().st_size
    return table, {
        "num_rows": table.num_rows,
        "first_timestamp_ms": first_time,
        "last_timestamp_ms": last_time,
        "file_size_bytes": size_bytes,
        "sha256": sha256
    }

def create_manifest(
    dataset_id: str,
    symbol: str,
    timeframe: str,
    req_start_ms: int,
    req_end_ms: int,
    actual_first_ms: int,
    actual_last_ms: int,
    row_count: int,
    missing_intervals: int,
    duplicate_count: int,
    parquet_path: Path,
    sha256: str,
    validation_status: str = "PASSED",
    unresolved_limitations: Optional[str] = None
) -> Path:
    """Generates an immutable JSON manifest companion file for the Parquet dataset."""
    manifest_dir = Path("D:/vanta-terminal/data/manifests")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{dataset_id}.manifest.json"

    file_size_bytes = parquet_path.stat().st_size if parquet_path.exists() else 0

    manifest_payload = {
        "manifest_version": "1.0.0",
        "dataset_id": dataset_id,
        "exchange": "AsterDEX Futures V3 (Pro API)",
        "endpoint_source": "https://fapi.asterdex.com/fapi/v1/klines",
        "symbol": symbol,
        "timeframe": timeframe,
        "date_ranges": {
            "requested_start_utc": datetime.fromtimestamp(req_start_ms / 1000, timezone.utc).isoformat(),
            "requested_end_utc": datetime.fromtimestamp(req_end_ms / 1000, timezone.utc).isoformat(),
            "actual_start_utc": datetime.fromtimestamp(actual_first_ms / 1000, timezone.utc).isoformat(),
            "actual_end_utc": datetime.fromtimestamp(actual_last_ms / 1000, timezone.utc).isoformat(),
            "requested_start_ms": req_start_ms,
            "requested_end_ms": req_end_ms,
            "actual_first_ms": actual_first_ms,
            "actual_last_ms": actual_last_ms,
        },
        "row_count": row_count,
        "gap_count": missing_intervals,
        "duplicate_count": duplicate_count,
        "storage": {
            "file_path": str(parquet_path),
            "file_size_bytes": file_size_bytes,
            "file_size_kb": round(file_size_bytes / 1024, 2),
            "compression": "SNAPPY",
            "format": "Apache Parquet",
            "sha256": sha256
        },
        "columns": [field.name for field in CANDLE_ARROW_SCHEMA],
        "validation_status": validation_status,
        "is_demo_data": False,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "unresolved_limitations": unresolved_limitations
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)

    return manifest_path
