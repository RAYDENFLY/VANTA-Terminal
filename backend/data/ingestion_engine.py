"""
VANTA Terminal — Bounded Ingestion Engine
=========================================
Orchestrates rate-limited, bounded historical market data downloads from AsterDEX V3.
Enforces disk space guards, idempotent resume, and mathematical validation.
"""

import time
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.data.asterdex_client import AsterDexPublicClient
from backend.data.validator import validate_candles, TIMEFRAME_STEP_MS
from backend.data.parquet_store import (
    write_parquet_dataset,
    read_parquet_dataset,
    create_manifest,
    compute_sha256
)

# Active Ingestion Job Telemetry (for Data Center UI)
CURRENT_INGESTION_STATE: Dict[str, Any] = {
    "status": "IDLE",
    "job_id": None,
    "symbol": None,
    "timeframe": None,
    "progress_pct": 0.0,
    "downloaded_rows": 0,
    "target_rows": 0,
    "current_timestamp_utc": None,
    "gaps_detected": 0,
    "errors": [],
    "file_size_kb": 0.0,
    "sha256": None,
    "manifest_id": None,
    "is_demo_data": False
}

def check_disk_space_guard(target_path: Path, min_free_gb: float = 10.0) -> None:
    """Verifies target drive has sufficient free headroom before ingestion (strictly >= 10 GB)."""
    drive_root = target_path.anchor or "D:\\"
    total, used, free = shutil.disk_usage(drive_root)
    free_gb = free / (1024 ** 3)
    if free_gb < min_free_gb:
        raise RuntimeError(
            f"DISK SPACE SAFETY GUARD: Target drive {drive_root} has only {free_gb:.2f} GB free. "
            f"Minimum safety reserve of {min_free_gb} GB required."
        )

def run_bounded_ingestion(
    symbol: str,
    timeframe: str,
    start_time_ms: int,
    end_time_ms: int,
    dataset_id: str,
    output_path: Optional[Path] = None,
    client: Optional[AsterDexPublicClient] = None
) -> Dict[str, Any]:
    """
    Executes a bounded, restartable ingestion run for a single symbol and timeframe.
    """
    global CURRENT_INGESTION_STATE

    if output_path is None:
        output_path = Path(f"D:/vanta-terminal/data/raw/{symbol}/{timeframe}.parquet")

    # Step 1: Pre-flight disk space safety check (operational safety reserve >= 10.0 GB)
    check_disk_space_guard(output_path, min_free_gb=10.0)

    step_ms = TIMEFRAME_STEP_MS.get(timeframe, 900000)
    expected_candles = int((end_time_ms - start_time_ms) // step_ms) + 1

    # Step 2: Idempotent resume / duplicate check
    manifest_path = Path(f"D:/vanta-terminal/data/manifests/{dataset_id}.manifest.json")
    if output_path.exists() and manifest_path.exists():
        try:
            _, meta = read_parquet_dataset(output_path)
            if meta["first_timestamp_ms"] <= start_time_ms and meta["last_timestamp_ms"] >= end_time_ms:
                CURRENT_INGESTION_STATE.update({
                    "status": "ALREADY_VALIDATED",
                    "job_id": dataset_id,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "progress_pct": 100.0,
                    "downloaded_rows": meta["num_rows"],
                    "target_rows": expected_candles,
                    "file_size_kb": round(meta["file_size_bytes"] / 1024, 2),
                    "sha256": meta["sha256"],
                    "manifest_id": dataset_id,
                    "is_demo_data": False
                })
                return {
                    "status": "ALREADY_VALIDATED",
                    "dataset_id": dataset_id,
                    "message": "Dataset already exists, verified and covers requested window.",
                    "row_count": meta["num_rows"],
                    "file_path": str(output_path),
                    "sha256": meta["sha256"],
                    "manifest_path": str(manifest_path)
                }
        except Exception:
            pass  # Fall through to re-ingest if corrupted

    if client is None:
        client = AsterDexPublicClient()

    CURRENT_INGESTION_STATE.update({
        "status": "RUNNING",
        "job_id": dataset_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "progress_pct": 0.0,
        "downloaded_rows": 0,
        "target_rows": expected_candles,
        "errors": [],
        "is_demo_data": False
    })

    start_wall_time = time.time()
    collected_candles = []
    curr_start = start_time_ms
    request_count = 0

    try:
        while curr_start <= end_time_ms:
            # Query AsterDEX V3 public klines
            batch = client.get_klines(
                symbol=symbol,
                interval=timeframe,
                start_time=curr_start,
                end_time=end_time_ms,
                limit=1500
            )
            request_count += 1

            if not batch:
                break

            for bar in batch:
                bar_open = int(bar[0])
                if bar_open <= end_time_ms and (not collected_candles or bar_open > collected_candles[-1][0]):
                    collected_candles.append(bar)

            last_open = int(batch[-1][0])
            last_close = int(batch[-1][6])

            # Advance cursor
            curr_start = last_close + 1

            # Update live state
            pct = min(100.0, round((len(collected_candles) / max(1, expected_candles)) * 100, 1))
            CURRENT_INGESTION_STATE.update({
                "progress_pct": pct,
                "downloaded_rows": len(collected_candles),
                "current_timestamp_utc": datetime.fromtimestamp(last_open / 1000, timezone.utc).isoformat()
            })

            # If returned batch is less than limit, we have reached the latest available candle
            if len(batch) < 1500:
                break

            time.sleep(0.05)  # Safe rate-limiting throttle

        # Step 3: Validate collected candles
        report = validate_candles(collected_candles, timeframe=timeframe)
        if not report.is_valid:
            raise ValueError(f"Market data validation failed for {symbol} {timeframe}: {report.errors}")

        # Step 4: Write strongly-typed Parquet
        row_count, sha256 = write_parquet_dataset(collected_candles, output_path, compression="SNAPPY")

        # Step 5: Write cryptographic manifest
        actual_first = report.first_timestamp_ms
        actual_last = report.last_timestamp_ms
        manifest_file = create_manifest(
            dataset_id=dataset_id,
            symbol=symbol,
            timeframe=timeframe,
            req_start_ms=start_time_ms,
            req_end_ms=end_time_ms,
            actual_first_ms=actual_first,
            actual_last_ms=actual_last,
            row_count=row_count,
            missing_intervals=report.gap_count,
            duplicate_count=report.duplicate_count,
            parquet_path=output_path,
            sha256=sha256,
            validation_status="PASSED",
            ohlc_violations=report.ohlc_violations,
            anomaly_count=report.anomaly_count,
            anomalies=report.anomalies,
            timeframe_type="EXCHANGE_NATIVE"
        )

        elapsed = round(time.time() - start_wall_time, 2)
        file_size_kb = round(output_path.stat().st_size / 1024, 2)

        CURRENT_INGESTION_STATE.update({
            "status": "COMPLETED",
            "progress_pct": 100.0,
            "downloaded_rows": row_count,
            "gaps_detected": report.gap_count,
            "file_size_kb": file_size_kb,
            "sha256": sha256,
            "manifest_id": dataset_id,
            "is_demo_data": False
        })

        return {
            "status": "COMPLETED",
            "dataset_id": dataset_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "row_count": row_count,
            "expected_rows": expected_candles,
            "gap_count": report.gap_count,
            "duplicate_count": report.duplicate_count,
            "file_path": str(output_path),
            "file_size_kb": file_size_kb,
            "sha256": sha256,
            "manifest_path": str(manifest_file),
            "elapsed_seconds": elapsed,
            "network_requests": request_count,
            "actual_start_utc": datetime.fromtimestamp(actual_first / 1000, timezone.utc).isoformat(),
            "actual_end_utc": datetime.fromtimestamp(actual_last / 1000, timezone.utc).isoformat(),
        }

    except Exception as e:
        CURRENT_INGESTION_STATE.update({
            "status": "FAILED",
            "errors": [str(e)]
        })
        raise
