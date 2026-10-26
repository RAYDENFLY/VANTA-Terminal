"""
VANTA Terminal — Market Data Integrity Validator
=================================================
Rigorous deterministic validation for OHLCV candlestick series.
Enforces no lookahead, zero synthetic filling, and mathematical OHLC consistency.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class ValidationReport:
    is_valid: bool
    total_candles: int
    duplicate_count: int
    gap_count: int
    ohlc_violations: int
    alignment_violations: int
    gaps: List[Dict[str, Any]]
    first_timestamp_ms: int
    last_timestamp_ms: int
    errors: List[str]

TIMEFRAME_STEP_MS = {
    "15m": 15 * 60 * 1000,    # 900,000 ms
    "1H": 60 * 60 * 1000,     # 3,600,000 ms
    "4H": 4 * 60 * 60 * 1000, # 14,400,000 ms
    "1d": 24 * 60 * 60 * 1000 # 86,400,000 ms
}

def validate_candles(raw_candles: List[List[Any]], timeframe: str = "15m") -> ValidationReport:
    """
    Validates a list of raw 12-item candle rows from AsterDEX /fapi/v1/klines.
    Format: [open_time, open, high, low, close, volume, close_time, quote_vol, trades, ...]
    """
    if not raw_candles:
        return ValidationReport(
            is_valid=False,
            total_candles=0,
            duplicate_count=0,
            gap_count=0,
            ohlc_violations=0,
            alignment_violations=0,
            gaps=[],
            first_timestamp_ms=0,
            last_timestamp_ms=0,
            errors=["Empty candle series provided."]
        )

    expected_step_ms = TIMEFRAME_STEP_MS.get(timeframe, 900000)
    seen_timestamps = set()
    duplicates = 0
    ohlc_violations = 0
    alignment_violations = 0
    gaps = []
    errors = []

    prev_open_time = None

    for idx, c in enumerate(raw_candles):
        open_time = int(c[0])
        o = float(c[1])
        h = float(c[2])
        l = float(c[3])
        cl = float(c[4])
        vol = float(c[5])
        close_time = int(c[6])

        # 1. Duplicate check
        if open_time in seen_timestamps:
            duplicates += 1
            errors.append(f"Row {idx}: Duplicate open_time {open_time}")
        seen_timestamps.add(open_time)

        # 2. Timeframe boundary alignment check (must start on modulo expected step)
        if open_time % expected_step_ms != 0:
            alignment_violations += 1
            errors.append(f"Row {idx}: Open time {open_time} misaligned for timeframe {timeframe}")

        # 3. Candle Invariant checks
        # High must be >= max(Open, Close)
        # Low must be <= min(Open, Close)
        # High must be >= Low > 0
        # Volume must be >= 0
        if not (h >= max(o, cl) and l <= min(o, cl) and h >= l and l > 0 and vol >= 0):
            ohlc_violations += 1
            errors.append(
                f"Row {idx} ({open_time}): OHLC invariant violation -> O:{o}, H:{h}, L:{l}, C:{cl}, V:{vol}"
            )

        # 4. Close time check (close_time must equal open_time + step - 1)
        expected_close = open_time + expected_step_ms - 1
        if close_time != expected_close:
            errors.append(
                f"Row {idx} ({open_time}): Close time mismatch (Got {close_time}, expected {expected_close})"
            )

        # 5. Gap and Chronological order check
        if prev_open_time is not None:
            delta = open_time - prev_open_time
            if delta <= 0:
                errors.append(f"Row {idx}: Non-chronological sequence {open_time} <= {prev_open_time}")
            elif delta > expected_step_ms:
                missing_bars = (delta // expected_step_ms) - 1
                gaps.append({
                    "gap_start_open_ms": prev_open_time + expected_step_ms,
                    "gap_end_open_ms": open_time - expected_step_ms,
                    "missing_bars": missing_bars,
                    "delta_ms": delta
                })

        prev_open_time = open_time

    is_valid = (duplicates == 0 and ohlc_violations == 0 and len(errors) == 0)

    return ValidationReport(
        is_valid=is_valid,
        total_candles=len(raw_candles),
        duplicate_count=duplicates,
        gap_count=len(gaps),
        ohlc_violations=ohlc_violations,
        alignment_violations=alignment_violations,
        gaps=gaps,
        first_timestamp_ms=int(raw_candles[0][0]),
        last_timestamp_ms=int(raw_candles[-1][0]),
        errors=errors[:20]  # Cap error list to first 20 for readability
    )
