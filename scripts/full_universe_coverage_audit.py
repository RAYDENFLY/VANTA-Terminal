import urllib.request
import json
import ssl
import time
from datetime import datetime, timezone

ctx = ssl.create_default_context()
BASE_URL = "https://fapi.asterdex.com"

TARGET_PAIRS = [
    ("BTCUSDT.P", "BTCUSDT"),
    ("ETHUSDT.P", "ETHUSDT"),
    ("SOLUSDT.P", "SOLUSDT"),
    ("BNBUSDT.P", "BNBUSDT"),
    ("XRPUSDT.P", "XRPUSDT"),
    ("ADAUSDT.P", "ADAUSDT"),
    ("AVAXUSDT.P", "AVAXUSDT"),
    ("LINKUSDT.P", "LINKUSDT"),
    ("DOGEUSDT.P", "DOGEUSDT"),
    ("LTCUSDT.P", "LTCUSDT"),
    ("XMRUSDT.P", "XMRUSDT"),
]

def fetch_json(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"
    if params:
        query_str = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "VANTA-Research-Audit/1.0"})
    time.sleep(0.05)  # Safe rate limit throttle (well under 2400 weight/min)
    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))

results = []

print("=== STARTING FULL 11-PAIR COVERAGE AUDIT ===")
now_ms = int(time.time() * 1000)

for req_sym, ex_sym in TARGET_PAIRS:
    print(f"\nAuditing {req_sym} -> Native: {ex_sym}...")
    pair_report = {
        "requested_symbol": req_sym,
        "exchange_symbol": ex_sym,
        "status": "TRADING",
        "timeframes": {}
    }

    # 1. Earliest Listing Detection via 1d
    try:
        earliest_1d = fetch_json("/fapi/v1/klines", {"symbol": ex_sym, "interval": "1d", "startTime": 1, "limit": 1})
        if earliest_1d:
            earliest_ms = earliest_1d[0][0]
            earliest_dt = datetime.fromtimestamp(earliest_ms/1000, timezone.utc)
            pair_report["earliest_ms"] = earliest_ms
            pair_report["earliest_date"] = earliest_dt.strftime("%Y-%m-%d %H:%M UTC")
            
            # Latest candle
            latest_1d = fetch_json("/fapi/v1/klines", {"symbol": ex_sym, "interval": "1d", "limit": 1})
            latest_ms = latest_1d[0][0] if latest_1d else now_ms
            latest_dt = datetime.fromtimestamp(latest_ms/1000, timezone.utc)
            pair_report["latest_ms"] = latest_ms
            pair_report["latest_date"] = latest_dt.strftime("%Y-%m-%d %H:%M UTC")
            
            total_days = round((latest_ms - earliest_ms) / (1000 * 86400), 1)
            total_years = round(total_days / 365.25, 2)
            pair_report["total_days"] = total_days
            pair_report["total_years"] = total_years
            pair_report["has_3_years"] = total_years >= 3.0
            pair_report["coverage_category"] = "VERIFIED (>=3Y)" if total_years >= 3.0 else "PARTIAL (<3Y)"
        else:
            pair_report["earliest_date"] = "UNAVAILABLE"
            pair_report["total_years"] = 0
            pair_report["has_3_years"] = False
            pair_report["coverage_category"] = "UNAVAILABLE"
    except Exception as e:
        pair_report["earliest_date"] = f"ERROR: {e}"
        pair_report["coverage_category"] = "ERROR"

    # 2. Timeframe Audits (15m, 1H, 4H)
    for tf in ["15m", "1H", "4H"]:
        tf_delta_ms = 900000 if tf == "15m" else (3600000 if tf == "1H" else 14400000)
        try:
            # Query earliest
            earliest_tf = fetch_json("/fapi/v1/klines", {"symbol": ex_sym, "interval": tf, "startTime": 1, "limit": 2})
            # Query latest
            latest_tf = fetch_json("/fapi/v1/klines", {"symbol": ex_sym, "interval": tf, "limit": 2})
            
            if earliest_tf and latest_tf:
                t0 = earliest_tf[0][0]
                t1 = earliest_tf[1][0] if len(earliest_tf) > 1 else t0 + tf_delta_ms
                is_step_valid = (t1 - t0) == tf_delta_ms
                
                pair_report["timeframes"][tf] = {
                    "available": True,
                    "earliest": datetime.fromtimestamp(t0/1000, timezone.utc).strftime("%Y-%m-%d %H:%M"),
                    "latest": datetime.fromtimestamp(latest_tf[-1][0]/1000, timezone.utc).strftime("%Y-%m-%d %H:%M"),
                    "step_valid": is_step_valid,
                }
            else:
                pair_report["timeframes"][tf] = {"available": False}
        except Exception as e:
            pair_report["timeframes"][tf] = {"available": False, "error": str(e)}

    # 3. Pagination Test on 15m (fetch 2 contiguous batches of 100 bars)
    try:
        batch1 = fetch_json("/fapi/v1/klines", {"symbol": ex_sym, "interval": "15m", "limit": 50})
        if len(batch1) == 50:
            next_start = batch1[-1][6] + 1  # end of last candle in ms
            batch2 = fetch_json("/fapi/v1/klines", {"symbol": ex_sym, "interval": "15m", "startTime": next_start, "limit": 50})
            if batch2:
                continuous = batch2[0][0] == next_start
                pair_report["pagination_verified"] = continuous
                pair_report["pagination_gap_ms"] = batch2[0][0] - next_start
            else:
                pair_report["pagination_verified"] = False
        else:
            pair_report["pagination_verified"] = False
    except Exception as e:
        pair_report["pagination_verified"] = False
        pair_report["pagination_error"] = str(e)

    # 4. Funding rate check
    try:
        fr = fetch_json("/fapi/v1/fundingRate", {"symbol": ex_sym, "limit": 1})
        pair_report["funding_rate_supported"] = len(fr) > 0
    except Exception:
        pair_report["funding_rate_supported"] = False

    results.append(pair_report)
    print(f"  Result: {ex_sym} -> Earliest: {pair_report.get('earliest_date')}, Span: {pair_report.get('total_years')} yrs, Category: {pair_report.get('coverage_category')}")

# Save full audit json
with open("data/manifests/asterdex_v3_coverage_audit.json", "w", encoding="utf-8") as f:
    json.dump({
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "exchange": "AsterDEX Futures V3 (Pro API)",
        "base_url": BASE_URL,
        "endpoint_klines": "/fapi/v1/klines",
        "results": results
    }, f, indent=2)

print("\nAudit saved to data/manifests/asterdex_v3_coverage_audit.json")
