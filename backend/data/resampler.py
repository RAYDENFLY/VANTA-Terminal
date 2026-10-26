"""
VANTA Terminal — Deterministic Multi-Timeframe Resampler
========================================================
Deterministically resamples validated 15m candles into 1H and 4H intervals.
Enforces calendar-boundary UTC alignment, strict candle count per bucket,
and zero-tolerance for incomplete or gap-spanning higher timeframe bars.
"""

from typing import List, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime, timezone

from backend.data.validator import validate_candles, ValidationReport
from backend.data.parquet_store import (
    write_parquet_dataset,
    read_parquet_dataset,
    create_manifest,
    compute_sha256
)

RESAMPLE_FACTORS = {
    "1h": {"step_ms": 3600000, "source_bars": 4, "name": "1H"},
    "4h": {"step_ms": 14400000, "source_bars": 16, "name": "4H"},
}


class ResampleResult:
    def __init__(
        self,
        derived_candles: List[List[Any]],
        total_source_bars: int,
        complete_buckets: int,
        incomplete_buckets: int,
        dropped_source_bars: int,
        target_timeframe: str
    ):
        self.derived_candles = derived_candles
        self.total_source_bars = total_source_bars
        self.complete_buckets = complete_buckets
        self.incomplete_buckets = incomplete_buckets
        self.dropped_source_bars = dropped_source_bars
        self.target_timeframe = target_timeframe


def resample_15m_to_higher_timeframe(
    candles_15m: List[List[Any]],
    target_timeframe: str
) -> ResampleResult:
    """
    Deterministically aggregates complete 15m candles into 1H or 4H.
    
    Invariants:
    1. Buckets are aligned to UTC midnight: open_time % step_ms == 0.
    2. 1H requires exactly 4 contiguous 15m candles.
    3. 4H requires exactly 16 contiguous 15m candles.
    4. Incomplete buckets (e.g. at listing start or due to missing intervals)
       are strictly dropped. Zero synthetic interpolation.
    """
    tf_lower = target_timeframe.lower()
    if tf_lower not in RESAMPLE_FACTORS:
        raise ValueError(f"Unsupported resample target timeframe '{target_timeframe}'. Supported: 1h, 4h.")

    cfg = RESAMPLE_FACTORS[tf_lower]
    step_ms = cfg["step_ms"]
    expected_bars = cfg["source_bars"]
    step_15m = 900000

    if not candles_15m:
        return ResampleResult([], 0, 0, 0, 0, target_timeframe)

    # Group 15m candles into target calendar buckets
    buckets: Dict[int, List[List[Any]]] = {}
    for bar in candles_15m:
        open_time = int(bar[0])
        bucket_key = open_time - (open_time % step_ms)
        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(bar)

    derived_candles = []
    incomplete_count = 0
    dropped_bars_count = 0

    sorted_keys = sorted(buckets.keys())

    for b_key in sorted_keys:
        bars = buckets[b_key]
        # Incomplete bucket check: must have exactly expected_bars (4 for 1h, 16 for 4h)
        if len(bars) != expected_bars:
            incomplete_count += 1
            dropped_bars_count += len(bars)
            continue

        # Continuity check inside the bucket: each bar must be exactly 900,000 ms apart
        continuous = True
        for idx in range(len(bars) - 1):
            if int(bars[idx + 1][0]) != int(bars[idx][0]) + step_15m:
                continuous = False
                break

        if not continuous:
            incomplete_count += 1
            dropped_bars_count += len(bars)
            continue

        # Aggregation of OHLCV
        first_bar = bars[0]
        last_bar = bars[-1]

        o_open_time = b_key
        o_open = float(first_bar[1])
        o_high = max(float(b[2]) for b in bars)
        o_low = min(float(b[3]) for b in bars)
        o_close = float(last_bar[4])
        o_volume = sum(float(b[5]) for b in bars)
        o_close_time = b_key + step_ms - 1
        o_quote_volume = sum(float(b[7]) for b in bars)
        o_trades_count = sum(int(b[8]) for b in bars)
        o_taker_buy_base = sum(float(b[9]) for b in bars)
        o_taker_buy_quote = sum(float(b[10]) for b in bars)

        derived_candles.append([
            o_open_time,
            str(o_open),
            str(o_high),
            str(o_low),
            str(o_close),
            str(o_volume),
            o_close_time,
            str(o_quote_volume),
            o_trades_count,
            str(o_taker_buy_base),
            str(o_taker_buy_quote),
            "0"
        ])

    return ResampleResult(
        derived_candles=derived_candles,
        total_source_bars=len(candles_15m),
        complete_buckets=len(derived_candles),
        incomplete_buckets=incomplete_count,
        dropped_source_bars=dropped_bars_count,
        target_timeframe=target_timeframe
    )


def resample_and_store_dataset(
    symbol: str,
    target_timeframe: str,
    source_15m_path: Path,
    output_path: Path,
    dataset_id: str
) -> Dict[str, Any]:
    """
    Reads 15m Parquet dataset, resamples to higher timeframe, validates,
    and writes out versioned Parquet dataset and cryptographic manifest.
    """
    # 1. Read source 15m dataset
    table, meta = read_parquet_dataset(source_15m_path)
    
    # Extract rows as list of lists
    pydict = table.to_pydict()
    source_count = len(pydict["open_time"])
    candles_15m = []
    for i in range(source_count):
        candles_15m.append([
            pydict["open_time"][i],
            str(pydict["open"][i]),
            str(pydict["high"][i]),
            str(pydict["low"][i]),
            str(pydict["close"][i]),
            str(pydict["volume"][i]),
            pydict["close_time"][i],
            str(pydict["quote_volume"][i]),
            pydict["trades_count"][i],
            str(pydict["taker_buy_base"][i]),
            str(pydict["taker_buy_quote"][i]),
            "0"
        ])

    # 2. Deterministic Resampling
    res = resample_15m_to_higher_timeframe(candles_15m, target_timeframe)

    if not res.derived_candles:
        raise ValueError(f"No valid {target_timeframe} candles could be derived from {source_15m_path}")

    # 3. Mathematical validation of derived series
    report = validate_candles(res.derived_candles, timeframe=target_timeframe)
    if not report.is_valid:
        raise ValueError(f"Derived {target_timeframe} candles failed validation: {report.errors}")

    # 4. Write strongly-typed Parquet
    row_count, sha256 = write_parquet_dataset(res.derived_candles, output_path, compression="SNAPPY")

    # 5. Write Manifest with explicit timeframe derivation statement
    req_start = int(res.derived_candles[0][0])
    req_end = int(res.derived_candles[-1][0])
    actual_first = report.first_timestamp_ms
    actual_last = report.last_timestamp_ms

    manifest_file = create_manifest(
        dataset_id=dataset_id,
        symbol=symbol,
        timeframe=target_timeframe,
        req_start_ms=req_start,
        req_end_ms=req_end,
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
        timeframe_type="DERIVED_FROM_15M"
    )

    # Enrich manifest with derivation metadata
    import json
    with open(manifest_file, "r") as mf:
        mdata = json.load(mf)
    
    mdata["timeframe_type"] = "DERIVED_FROM_15M"
    mdata["derivation_metadata"] = {
        "source_dataset": str(source_15m_path),
        "source_row_count": source_count,
        "complete_buckets": res.complete_buckets,
        "incomplete_buckets_dropped": res.incomplete_buckets,
        "dropped_source_bars": res.dropped_source_bars,
        "rule": f"Strict {RESAMPLE_FACTORS[target_timeframe.lower()]['source_bars']}x15m per bucket, UTC aligned, zero synthetic filling"
    }

    with open(manifest_file, "w") as mf:
        json.dump(mdata, mf, indent=2)

    return {
        "dataset_id": dataset_id,
        "symbol": symbol,
        "timeframe": target_timeframe,
        "timeframe_type": "DERIVED_FROM_15M",
        "row_count": row_count,
        "gap_count": report.gap_count,
        "duplicate_count": report.duplicate_count,
        "file_path": str(output_path),
        "file_size_kb": round(output_path.stat().st_size / 1024, 2),
        "sha256": sha256,
        "manifest_path": str(manifest_file),
        "incomplete_buckets_dropped": res.incomplete_buckets
    }
