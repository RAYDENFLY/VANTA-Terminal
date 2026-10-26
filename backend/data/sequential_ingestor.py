"""
VANTA Terminal — Sequential Historical Data Ingestor
====================================================
Orchestrates sequential, low-memory ingestion of the 11-pair crypto futures universe
from AsterDEX Futures V3 public API, followed by deterministic 1H and 4H resampling.
Enforces:
- Single-worker sequential execution (VANTA_MAX_WORKERS=1).
- Operational safety reserve >= 10.0 GB free on D:.
- Zero SSD C: storage usage.
- Pilot preservation (BTCUSDT 30D pilot untouched).
- Idempotent resumption and safe cancellation.
- Master job registry for UI telemetry.
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.data.ingestion_engine import run_bounded_ingestion, check_disk_space_guard
from backend.data.resampler import resample_and_store_dataset
from backend.data.parquet_store import read_parquet_dataset, compute_sha256

# Target Universe
QUALIFIED_10_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "LTCUSDT"
]
DYNAMIC_ENTRY_PAIR = "XMRUSDT"
ALL_11_PAIRS = QUALIFIED_10_PAIRS + [DYNAMIC_ENTRY_PAIR]

# Clean UTC Boundaries
# 3 Years for Qualified 10: 2023-10-26 00:00:00 UTC to 2026-10-26 00:00:00 UTC
QUALIFIED_START_MS = 1698278400000  # 2023-10-26 00:00:00 UTC
UNIVERSE_END_MS    = 1792972800000  # 2026-10-26 00:00:00 UTC (exclusive boundary, last bar starts at 1792971900000)
QUALIFIED_LAST_BAR_MS = 1792971900000  # 2026-10-25 23:45:00 UTC

# XMR Listing: 2026-01-13 16:45:00 UTC
XMR_START_MS       = 1768322700000  # 2026-01-13 16:45:00 UTC
XMR_LAST_BAR_MS    = 1792971900000  # 2026-10-25 23:45:00 UTC

REGISTRY_PATH = Path("D:/vanta-terminal/data/manifests/ingestion_job_registry.json")
CANCEL_SIGNAL_FILE = Path("D:/vanta-terminal/.runtime/.cancel_ingestion")


def load_job_registry() -> Dict[str, Any]:
    """Loads the persistent ingestion job registry or initializes a new one."""
    if REGISTRY_PATH.exists():
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Initialize empty template
    registry = {
        "registry_version": "1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "operational_reserve_gb": 10.0,
        "active_job": None,
        "is_cancelled": False,
        "datasets": {}
    }

    # Pre-populate all 33 target dataset slots
    for sym in ALL_11_PAIRS:
        is_xmr = (sym == DYNAMIC_ENTRY_PAIR)
        start_ms = XMR_START_MS if is_xmr else QUALIFIED_START_MS
        end_ms = XMR_LAST_BAR_MS if is_xmr else QUALIFIED_LAST_BAR_MS

        for tf in ["15m", "1h", "4h"]:
            dataset_key = f"{sym}_{tf.upper()}"
            is_native = (tf == "15m")
            registry["datasets"][dataset_key] = {
                "symbol": sym,
                "timeframe": tf,
                "timeframe_type": "EXCHANGE_NATIVE" if is_native else "DERIVED_FROM_15M",
                "status": "QUEUED",  # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED, ALREADY_VALIDATED
                "target_start_utc": datetime.fromtimestamp(start_ms / 1000, timezone.utc).isoformat(),
                "target_end_utc": datetime.fromtimestamp(end_ms / 1000, timezone.utc).isoformat(),
                "row_count": 0,
                "gap_count": 0,
                "duplicate_count": 0,
                "file_path": None,
                "file_size_kb": 0.0,
                "sha256": None,
                "manifest_path": None,
                "error": None,
                "updated_at": None
            }

    save_job_registry(registry)
    return registry


def save_job_registry(registry: Dict[str, Any]) -> None:
    """Safely writes the job registry to disk atomically."""
    registry["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = REGISTRY_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    shutil.move(temp_path, REGISTRY_PATH)


def run_sequential_universe_ingestion(
    symbols: Optional[List[str]] = None,
    timeframes: Optional[List[str]] = None,
    stop_on_first_error: bool = False
) -> Dict[str, Any]:
    """
    Sequentially processes each symbol and timeframe in strict single-worker mode.
    """
    if symbols is None:
        symbols = ALL_11_PAIRS
    if timeframes is None:
        timeframes = ["15m", "1h", "4h"]

    registry = load_job_registry()

    # Pre-flight disk space safety check
    check_disk_space_guard(Path("D:/vanta-terminal/data/raw"), min_free_gb=10.0)

    total_datasets = len(symbols) * len(timeframes)
    processed_count = 0
    completed_count = 0
    failed_count = 0

    print(f"=== Starting VANTA Sequential Ingestion: {len(symbols)} pairs, {total_datasets} target datasets ===")

    for sym in symbols:
        is_xmr = (sym == DYNAMIC_ENTRY_PAIR)
        start_ms = XMR_START_MS if is_xmr else QUALIFIED_START_MS
        end_ms = XMR_LAST_BAR_MS if is_xmr else QUALIFIED_LAST_BAR_MS

        # Check for user cancellation request
        if CANCEL_SIGNAL_FILE.exists():
            print(f"[CANCELLATION REQUEST DETECTED] Gracefully halting sequential ingestion.")
            registry["is_cancelled"] = True
            save_job_registry(registry)
            break

        # Re-check disk space before every instrument
        check_disk_space_guard(Path("D:/vanta-terminal/data/raw"), min_free_gb=10.0)

        # ------------------------------------------------------------------
        # Step A: 15m Exchange-Native Ingestion
        # ------------------------------------------------------------------
        if "15m" in timeframes:
            key_15m = f"{sym}_15M"
            current_job = registry["datasets"].get(key_15m, {})
            dataset_id = f"ASTERDEX_{sym}_15M_ARCHIVE"
            output_15m = Path(f"D:/vanta-terminal/data/raw/{sym}/15m.parquet")

            # Check if already completed and intact
            manifest_15m = Path(f"D:/vanta-terminal/data/manifests/{dataset_id}.manifest.json")
            if output_15m.exists() and manifest_15m.exists() and current_job.get("status") == "COMPLETED":
                print(f"[{sym} 15m] Already validated. Skipping.")
            else:
                print(f"[{sym} 15m] Ingesting exchange-native 15m history ({'286 days' if is_xmr else '3 years'})...")
                registry["active_job"] = key_15m
                registry["datasets"][key_15m]["status"] = "RUNNING"
                save_job_registry(registry)

                try:
                    res_15m = run_bounded_ingestion(
                        symbol=sym,
                        timeframe="15m",
                        start_time_ms=start_ms,
                        end_time_ms=end_ms,
                        dataset_id=dataset_id,
                        output_path=output_15m
                    )
                    registry["datasets"][key_15m].update({
                        "status": "COMPLETED",
                        "row_count": res_15m["row_count"],
                        "gap_count": res_15m.get("gap_count", 0),
                        "duplicate_count": res_15m.get("duplicate_count", 0),
                        "file_path": res_15m["file_path"],
                        "file_size_kb": res_15m["file_size_kb"],
                        "sha256": res_15m["sha256"],
                        "manifest_path": res_15m["manifest_path"],
                        "error": None,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    completed_count += 1
                except Exception as e:
                    print(f"[{sym} 15m] FAILED: {e}")
                    registry["datasets"][key_15m].update({
                        "status": "FAILED",
                        "error": str(e),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    failed_count += 1
                    save_job_registry(registry)
                    if stop_on_first_error:
                        raise e
                    continue

                save_job_registry(registry)

        # ------------------------------------------------------------------
        # Step B: 1H Deterministic Derivation from Validated 15m
        # ------------------------------------------------------------------
        if "1h" in timeframes:
            key_1h = f"{sym}_1H"
            current_job = registry["datasets"].get(key_1h, {})
            dataset_id_1h = f"ASTERDEX_{sym}_1H_ARCHIVE"
            out_1h_derived = Path(f"D:/vanta-terminal/data/derived/{sym}/1h.parquet")
            out_1h_raw = Path(f"D:/vanta-terminal/data/raw/{sym}/1h.parquet")
            manifest_1h = Path(f"D:/vanta-terminal/data/manifests/{dataset_id_1h}.manifest.json")

            if out_1h_raw.exists() and manifest_1h.exists() and current_job.get("status") == "COMPLETED":
                print(f"[{sym} 1H] Already derived and validated. Skipping.")
            else:
                print(f"[{sym} 1H] Deriving 1H candles from validated 15m...")
                registry["active_job"] = key_1h
                registry["datasets"][key_1h]["status"] = "RUNNING"
                save_job_registry(registry)

                try:
                    res_1h = resample_and_store_dataset(
                        symbol=sym,
                        target_timeframe="1h",
                        source_15m_path=output_15m,
                        output_path=out_1h_raw,
                        dataset_id=dataset_id_1h
                    )
                    # Also keep a copy in data/derived for explicit separation
                    out_1h_derived.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(out_1h_raw, out_1h_derived)

                    registry["datasets"][key_1h].update({
                        "status": "COMPLETED",
                        "row_count": res_1h["row_count"],
                        "gap_count": res_1h.get("gap_count", 0),
                        "duplicate_count": res_1h.get("duplicate_count", 0),
                        "file_path": res_1h["file_path"],
                        "file_size_kb": res_1h["file_size_kb"],
                        "sha256": res_1h["sha256"],
                        "manifest_path": res_1h["manifest_path"],
                        "error": None,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    completed_count += 1
                except Exception as e:
                    print(f"[{sym} 1H] FAILED: {e}")
                    registry["datasets"][key_1h].update({
                        "status": "FAILED",
                        "error": str(e),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    failed_count += 1
                    save_job_registry(registry)
                    if stop_on_first_error:
                        raise e

                save_job_registry(registry)

        # ------------------------------------------------------------------
        # Step C: 4H Deterministic Derivation from Validated 15m
        # ------------------------------------------------------------------
        if "4h" in timeframes:
            key_4h = f"{sym}_4H"
            current_job = registry["datasets"].get(key_4h, {})
            dataset_id_4h = f"ASTERDEX_{sym}_4H_ARCHIVE"
            out_4h_derived = Path(f"D:/vanta-terminal/data/derived/{sym}/4h.parquet")
            out_4h_raw = Path(f"D:/vanta-terminal/data/raw/{sym}/4h.parquet")
            manifest_4h = Path(f"D:/vanta-terminal/data/manifests/{dataset_id_4h}.manifest.json")

            if out_4h_raw.exists() and manifest_4h.exists() and current_job.get("status") == "COMPLETED":
                print(f"[{sym} 4H] Already derived and validated. Skipping.")
            else:
                print(f"[{sym} 4H] Deriving 4H candles from validated 15m...")
                registry["active_job"] = key_4h
                registry["datasets"][key_4h]["status"] = "RUNNING"
                save_job_registry(registry)

                try:
                    res_4h = resample_and_store_dataset(
                        symbol=sym,
                        target_timeframe="4h",
                        source_15m_path=output_15m,
                        output_path=out_4h_raw,
                        dataset_id=dataset_id_4h
                    )
                    # Also keep a copy in data/derived for explicit separation
                    out_4h_derived.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(out_4h_raw, out_4h_derived)

                    registry["datasets"][key_4h].update({
                        "status": "COMPLETED",
                        "row_count": res_4h["row_count"],
                        "gap_count": res_4h.get("gap_count", 0),
                        "duplicate_count": res_4h.get("duplicate_count", 0),
                        "file_path": res_4h["file_path"],
                        "file_size_kb": res_4h["file_size_kb"],
                        "sha256": res_4h["sha256"],
                        "manifest_path": res_4h["manifest_path"],
                        "error": None,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    completed_count += 1
                except Exception as e:
                    print(f"[{sym} 4H] FAILED: {e}")
                    registry["datasets"][key_4h].update({
                        "status": "FAILED",
                        "error": str(e),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    failed_count += 1
                    save_job_registry(registry)
                    if stop_on_first_error:
                        raise e

                save_job_registry(registry)

        processed_count += len(timeframes)

    registry["active_job"] = None
    save_job_registry(registry)

    return {
        "status": "HALTED_BY_USER" if registry.get("is_cancelled") else "SUCCESS",
        "completed_count": completed_count,
        "failed_count": failed_count,
        "total_targets": total_datasets,
        "registry_path": str(REGISTRY_PATH)
    }


if __name__ == "__main__":
    run_sequential_universe_ingestion()
