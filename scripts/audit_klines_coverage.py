import urllib.request
import json
import ssl
from datetime import datetime, timezone

ctx = ssl.create_default_context()
BASE_URL = "https://fapi.asterdex.com"

def fetch_json(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"
    if params:
        query_str = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "VANTA-Research-Audit/1.0"})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8")), resp.getheaders()

print("--- TESTING KLINES ENDPOINT STRUCTURE ---")
# 1. Test standard klines call
sample_klines, headers = fetch_json("/fapi/v1/klines", {"symbol": "BTCUSDT", "interval": "15m", "limit": 5})
print(f"Sample klines returned: {len(sample_klines)} bars")
if sample_klines:
    first_bar = sample_klines[0]
    print(f"Candle schema (len={len(first_bar)}): {first_bar}")
    t_open = first_bar[0]
    t_close = first_bar[6]
    print(f"Open Time: {t_open} ({datetime.fromtimestamp(t_open/1000, timezone.utc).isoformat()})")
    print(f"Close Time: {t_close} ({datetime.fromtimestamp(t_close/1000, timezone.utc).isoformat()})")
    print(f"Delta: {(t_close - t_open + 1) / 1000} seconds (Expected 900s for 15m)")

# 2. Test Max Limit per request
print("\n--- TESTING MAX LIMIT PER REQUEST ---")
for limit_candidate in [500, 1000, 1500, 2000]:
    try:
        klines, _ = fetch_json("/fapi/v1/klines", {"symbol": "BTCUSDT", "interval": "15m", "limit": limit_candidate})
        print(f"Limit {limit_candidate}: SUCCESS, returned {len(klines)} bars")
    except Exception as e:
        print(f"Limit {limit_candidate}: ERROR -> {e}")

# 3. Test Oldest Historical Candle Discovery (Querying from startTime=0)
print("\n--- TESTING EARLIEST CANDLE DISCOVERY (startTime=0) ---")
for sym in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XMRUSDT"]:
    try:
        # Querying with startTime=1 to find listing candle
        oldest_klines, _ = fetch_json("/fapi/v1/klines", {"symbol": sym, "interval": "1d", "startTime": 1, "limit": 5})
        if oldest_klines:
            earliest_ms = oldest_klines[0][0]
            earliest_dt = datetime.fromtimestamp(earliest_ms/1000, timezone.utc)
            print(f"Symbol {sym}: Earliest 1d candle = {earliest_ms} -> {earliest_dt.isoformat()}")
        else:
            print(f"Symbol {sym}: returned empty list for startTime=1")
    except Exception as e:
        print(f"Symbol {sym}: Error querying earliest candle -> {e}")

# 4. Test Funding Rate History endpoint
print("\n--- TESTING FUNDING RATE HISTORY ---")
try:
    funding_data, _ = fetch_json("/fapi/v1/fundingRate", {"symbol": "BTCUSDT", "limit": 5})
    print(f"Funding rate history records returned: {len(funding_data)}")
    if funding_data:
        print(f"Sample funding record: {funding_data[0]}")
except Exception as e:
    print(f"Funding rate endpoint error: {e}")

# 5. Test Mark Price / Premium Index
print("\n--- TESTING MARK PRICE / PREMIUM INDEX ---")
try:
    premium_data, _ = fetch_json("/fapi/v1/premiumIndex", {"symbol": "BTCUSDT"})
    print(f"Premium index record: {premium_data}")
except Exception as e:
    print(f"Premium index endpoint error: {e}")
