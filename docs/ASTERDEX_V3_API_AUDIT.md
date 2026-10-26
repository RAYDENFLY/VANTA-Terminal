# AsterDEX Futures V3 (Pro API) — Comprehensive API & Instrument Discovery Audit
**Document ID:** DOC-AUDIT-V3-001  
**Verification Date:** 2026-10-27  
**Official Documentation Reference:**
- Repository: [https://github.com/asterdex/api-docs](https://github.com/asterdex/api-docs)
- Futures V3 General Info: [https://asterdex.github.io/aster-api-website/futures-v3/general-info/](https://asterdex.github.io/aster-api-website/futures-v3/general-info/)

---

## 1. Public Market Data Base URLs & Connectivity Verification

- **Production Base URL**: `https://fapi.asterdex.com` (Verified active and responsive)
- **Testnet Base URL**: `https://fapi.asterdex-testnet.com`
- **Exchange Timezone**: UTC (Returned from `/fapi/v1/exchangeInfo`)
- **Server Timestamp**: Unix millisecond precision (e.g. `1793047713114`)
- **Total Instruments on Exchange**: 643 active trading contracts.

---

## 2. Rate Limits & Governance

Extracted directly from public `GET /fapi/v1/exchangeInfo`:
- **REQUEST_WEIGHT**: `2,400` weight units per `1 MINUTE`.
- **ORDERS**: `1,200` orders per `1 MINUTE` (Irrelevant for VANTA; order placement is disabled).
- **ORDERS**: `300` orders per `10 SECONDS`.
- **Throttling Guidance**:
  - `429 Too Many Requests`: Client has exceeded request weight limits.
  - `418 IP Auto-Ban`: Triggered if requests continue after `429` response.
  - VANTA Adapter Policy: Bounded sleep intervals of $\ge 50\text{ ms}$ between requests, well within the 2,400 weight limit.

---

## 3. Endpoint Classification & Schema Verification

| Capability / Endpoint | HTTP Method | Path | Auth Required | Parameters & Limits |
| :--- | :--- | :--- | :--- | :--- |
| **System Ping** | `GET` | `/fapi/v1/ping` | **NO** | Returns `{}` (Health check) |
| **Server Time** | `GET` | `/fapi/v1/time` | **NO** | Returns `{"serverTime": <unix_ms>}` |
| **Exchange Info** | `GET` | `/fapi/v1/exchangeInfo` | **NO** | Symbols, precision, filters, rate limits |
| **Klines / Candlesticks** | `GET` | `/fapi/v1/klines` | **NO** | `symbol`, `interval`, `startTime`, `endTime`, `limit` (Max: 1500) |
| **Funding Rate History** | `GET` | `/fapi/v1/fundingRate` | **NO** | `symbol`, `startTime`, `endTime`, `limit` (Max: 1000) |
| **Mark Price / Premium Index**| `GET` | `/fapi/v1/premiumIndex` | **NO** | `symbol` (Returns mark price, index, funding rate) |
| **24h Ticker Price Change** | `GET` | `/fapi/v1/ticker/24hr` | **NO** | `symbol` (Volume, VWAP, high, low) |
| **Order Book Depth** | `GET` | `/fapi/v1/depth` | **NO** | `symbol`, `limit` (5, 10, 20, 50, 100, 500, 1000) |
| **Recent Public Trades** | `GET` | `/fapi/v1/trades` | **NO** | `symbol`, `limit` (Max: 1000) |
| **User Data / Balance** | `GET` | `/fapi/v3/balance` | **YES (Agent Wallet)** | Requires EIP-712 Agent signature (Disabled in Phase 1/2) |
| **Order Placement** | `POST` | `/fapi/v3/order` | **YES (Signed)** | **PERMANENTLY DISABLED IN VANTA TERMINAL** |

---

## 4. Instrument Discovery: 11 Requested Crypto-Futures Pairs

All 11 requested assets were audited against AsterDEX Futures V3 public `exchangeInfo`.

### Key Discovery: Exchange Native Identifiers
The exchange native format is uppercase standard pairing **without** the `.P` suffix. (e.g. `BTCUSDT`, not `BTCUSDT.P`).

| Requested Symbol | Exchange Native Symbol | Status | Contract Type | Base / Quote | Price Precision | Qty Precision | Tick Size | Step Size | Min Notional |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `BTCUSDT.P` | **`BTCUSDT`** | `TRADING` | `PERPETUAL` | BTC / USDT | 1 | 3 | 0.1 | 0.001 | 5.0 USDT |
| `ETHUSDT.P` | **`ETHUSDT`** | `TRADING` | `PERPETUAL` | ETH / USDT | 2 | 3 | 0.01 | 0.001 | 5.0 USDT |
| `SOLUSDT.P` | **`SOLUSDT`** | `TRADING` | `PERPETUAL` | SOL / USDT | 4 | 2 | 0.0100 | 0.01 | 5.0 USDT |
| `BNBUSDT.P` | **`BNBUSDT`** | `TRADING` | `PERPETUAL` | BNB / USDT | 3 | 2 | 0.010 | 0.01 | 5.0 USDT |
| `XRPUSDT.P` | **`XRPUSDT`** | `TRADING` | `PERPETUAL` | XRP / USDT | 4 | 1 | 0.0001 | 0.1 | 5.0 USDT |
| `ADAUSDT.P` | **`ADAUSDT`** | `TRADING` | `PERPETUAL` | ADA / USDT | 5 | 0 | 0.00010 | 1 | 5.0 USDT |
| `AVAXUSDT.P` | **`AVAXUSDT`** | `TRADING` | `PERPETUAL` | AVAX / USDT | 4 | 0 | 0.0010 | 1 | 5.0 USDT |
| `LINKUSDT.P` | **`LINKUSDT`** | `TRADING` | `PERPETUAL` | LINK / USDT | 3 | 2 | 0.001 | 0.01 | 5.0 USDT |
| `DOGEUSDT.P` | **`DOGEUSDT`** | `TRADING` | `PERPETUAL` | DOGE / USDT | 6 | 0 | 0.000010 | 1 | 5.0 USDT |
| `LTCUSDT.P` | **`LTCUSDT`** | `TRADING` | `PERPETUAL` | LTC / USDT | 2 | 3 | 0.01 | 0.001 | 5.0 USDT |
| `XMRUSDT.P` | **`XMRUSDT`** | `TRADING` | `PERPETUAL` | XMR / USDT | 2 | 3 | 0.01 | 0.001 | 5.0 USDT |

*All 11 instruments are active perpetual futures settled in USDT with standard 5 USDT minimum notional.*

---

## 5. Kline Endpoint Behavior & Schema

The endpoint `/fapi/v1/klines` returns an array of 12 fields per bar:
```json
[
  1793049300000,          // 0: Open time (unix ms)
  "79932.2",              // 1: Open price
  "80047.5",              // 2: High price
  "79904.1",              // 3: Low price
  "80047.1",              // 4: Close price
  "9.481",                // 5: Volume (base asset)
  1793050199999,          // 6: Close time (unix ms, inclusive)
  "758487.5759",          // 7: Quote asset volume
  321,                    // 8: Number of trades
  "3.689",                // 9: Taker buy base asset volume
  "295126.7669",          // 10: Taker buy quote asset volume
  "0"                     // 11: Ignore
]
```
- **Interval Support**: `15m` (900s), `1h` (3600s), `4h` (14400s), `1d` (86400s).
- **Max Page Size**: Exactly 1,500 bars per query.
- **Pagination**: Deterministic forward pagination via `startTime = last_bar_close_time + 1`. Backward pagination via `endTime = target_ms`. Zero overlap and zero gap between consecutive batches.
