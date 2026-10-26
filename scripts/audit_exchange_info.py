import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
req = urllib.request.Request(
    'https://fapi.asterdex.com/fapi/v1/exchangeInfo',
    headers={'User-Agent': 'VANTA-Research-Audit/1.0'}
)

with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
    data = json.loads(resp.read().decode('utf-8'))

print("Exchange Timezone:", data.get("timezone"))
print("Server Time:", data.get("serverTime"))
print("Rate Limits count:", len(data.get("rateLimits", [])))
for rl in data.get("rateLimits", []):
    print("  Rate Limit:", rl)

symbols = data.get("symbols", [])
print(f"Total Instruments on Exchange: {len(symbols)}")

target_bases = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "LINK", "DOGE", "LTC", "XMR"]
found = {}

print("\n--- TARGET ASSETS DISCOVERY ---")
for s in symbols:
    base = s.get("baseAsset")
    quote = s.get("quoteAsset")
    sym = s.get("symbol")
    if base in target_bases:
        found[f"{base}_{quote}"] = s
        print(f"Match: Base={base}, Quote={quote}, Symbol={sym}, Status={s.get('status')}, ContractType={s.get('contractType')}, PricePrecision={s.get('pricePrecision')}, QtyPrecision={s.get('quantityPrecision')}")
        # Print filters
        for f in s.get("filters", []):
            if f.get("filterType") in ["PRICE_FILTER", "LOT_SIZE", "MIN_NOTIONAL"]:
                print(f"    Filter {f.get('filterType')}: {f}")

missing = set(target_bases) - set(s.get("baseAsset") for s in found.values() if s.get("quoteAsset") == "USDT")
print("\nMissing USDT perpetuals from requested 11:", missing)
