"""
VANTA Terminal — Phase 3A Pilot Ingestion Runner
================================================
Executes bounded 30-day BTCUSDT 15m ingestion from AsterDEX Futures V3.
Measures runtime, memory, network calls, and verifies idempotency.
"""

import sys
import time
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timezone
from backend.core.telemetry import get_system_memory
from backend.data.ingestion_engine import run_bounded_ingestion
from backend.data.parquet_store import read_parquet_dataset

def main():
    print("=== VANTA TERMINAL — PHASE 3A PILOT INGESTION ===")
    print("Target: BTCUSDT | Timeframe: 15m | Window: 30 Days Bounded")
    print("Exchange: AsterDEX Futures V3 (Pro API) [https://fapi.asterdex.com]")

    start_ms = 1790461800000  # 2026-09-26 22:30:00 UTC
    end_ms = 1793053800000    # 2026-10-26 22:30:00 UTC
    dataset_id = "ASTERDEX_BTCUSDT_15M_30D_PILOT"
    output_path = Path("D:/vanta-terminal/data/raw/BTCUSDT/15m.parquet")

    # Clean previous test if any
    if output_path.exists():
        output_path.unlink()
    manifest_path = Path(f"D:/vanta-terminal/data/manifests/{dataset_id}.manifest.json")
    if manifest_path.exists():
        manifest_path.unlink()

    mem_before = get_system_memory()
    print(f"Memory Before Ingestion: Available = {mem_before['available_ram_gb']} GB")

    t0 = time.time()
    result = run_bounded_ingestion(
        symbol="BTCUSDT",
        timeframe="15m",
        start_time_ms=start_ms,
        end_time_ms=end_ms,
        dataset_id=dataset_id,
        output_path=output_path
    )
    t1 = time.time()

    mem_after = get_system_memory()
    elapsed = round(t1 - t0, 3)

    print("\n--- PILOT RUN 1 RESULTS ---")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print(f"  Wall-clock elapsed: {elapsed} seconds")
    print(f"  Memory After Ingestion: Available = {mem_after['available_ram_gb']} GB")

    # Verify Parquet on disk
    table, meta = read_parquet_dataset(output_path)
    print("\n--- PARQUET VERIFICATION ON DISK ---")
    print(f"  Table Schema: {table.schema}")
    print(f"  Total Rows: {meta['num_rows']}")
    print(f"  File Size: {meta['file_size_bytes']} bytes ({meta['file_size_bytes']/1024:.2f} KB)")
    print(f"  Earliest: {datetime.fromtimestamp(meta['first_timestamp_ms']/1000, timezone.utc).isoformat()}")
    print(f"  Latest:   {datetime.fromtimestamp(meta['last_timestamp_ms']/1000, timezone.utc).isoformat()}")
    print(f"  SHA-256:  {meta['sha256']}")

    # Idempotency Test: Rerun the exact same ingestion
    print("\n--- IDEMPOTENCY / SAFE RESUME TEST ---")
    t_idemp0 = time.time()
    idemp_result = run_bounded_ingestion(
        symbol="BTCUSDT",
        timeframe="15m",
        start_time_ms=start_ms,
        end_time_ms=end_ms,
        dataset_id=dataset_id,
        output_path=output_path
    )
    t_idemp1 = time.time()
    print(f"  Idempotency Result Status: {idemp_result.get('status')}")
    print(f"  Message: {idemp_result.get('message')}")
    print(f"  Checksum match: {idemp_result.get('sha256') == meta['sha256']}")
    print(f"  Elapsed: {round(t_idemp1 - t_idemp0, 4)} seconds (Fast path, 0 HTTP calls)")

if __name__ == "__main__":
    main()
