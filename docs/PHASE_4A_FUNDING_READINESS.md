# VANTA Terminal — Historical Funding Data Readiness & Audit
**Document ID:** DOC-FUNDING-P4A  
**Phase:** 4A (Pre-Strategy Research Protocol)  
**Verification Date:** 2026-10-27  

---

## 1. Executive Summary

AsterDEX Futures V3 public endpoints were systematically audited across all 11 target universe instruments to verify the availability, depth, and schema of historical 8-hour funding rate settlement records.

### Key Finding:
- **Exchange Coverage Depth**: **100.0% Available**. Historical 8-hour funding rates for all 10 qualified pairs date back to `2023-10-26 00:00:00 UTC` (and earlier to August 2021). `XMRUSDT` records are available from its listing at `2026-01-13 17:00:00 UTC`.
- **Local Storage State**: In Phase 3B.1, only OHLCV candlesticks were authorized and persisted. Historical funding records have **not yet been serialized into local Parquet on disk**.
- **Prerequisite Enforcement**: In strict compliance with instructions, the backtest engine enforces `BLOCKED_MISSING_FUNDING_DATA` whenever `use_funding = True` is requested, preventing synthetic or zero-assumed funding.

---

## 2. Exchange Endpoint Audit & Parameters

| Parameter | Observed Specification | Verification / Source |
| :--- | :--- | :--- |
| **Public Endpoint** | `GET /fapi/v1/fundingRate` | Official AsterDEX Futures V3 Pro API |
| **Base URL** | `https://fapi.asterdex.com` | Air-gapped public query (no signing) |
| **Query Parameters** | `symbol`, `startTime`, `endTime`, `limit` | Max limit: `1,000` records/call |
| **Settlement Timestamps** | `00:00:00 UTC`, `08:00:00 UTC`, `16:00:00 UTC` | Exactly every $28,800,000\text{ ms}$ (8.0h) |
| **Rate Sign Convention** | Float string (e.g. `"0.00010000"`) | $>0$: Long pays Short; $<0$: Short pays Long |
| **Rate Limits** | 2,400 weight/min | Endpoint weight = 1 per request |

---

## 3. Historical Funding Coverage Across Universe

| Instrument Symbol | Target Start (UTC) | Earliest Verified Record | Latest Record (UTC) | Step Size | Coverage Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`BTCUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`ETHUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`SOLUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`BNBUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`XRPUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`ADAUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`AVAXUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`LINKUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`DOGEUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`LTCUSDT`** | `2023-10-26 00:00` | `2023-10-26T00:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 3Y** |
| **`XMRUSDT`** | `2026-01-13 16:45` | `2026-01-13T17:00:00Z` | `2026-10-26T16:00:00Z` | 8.0h | **VERIFIED $\ge$ 286D** |

---

## 4. Ingestion Specification & Storage Budget for Future Authorization

To unblock historical funding-aware backtests, an ingestion job can be executed under the following documented parameters:

1. **Storage Target**: HDD `D:\vanta-terminal\data\funding\{symbol}\funding.parquet`.
2. **PyArrow Schema**:
   - `funding_time`: `int64` (unix ms, aligned to 8h)
   - `funding_rate`: `float64`
   - `symbol`: `string`
3. **Data Volume**:
   - 3 settlements / day $\times$ 1,096 days = 3,288 records per qualified pair.
   - Total rows across 11 pairs: **`33,738 rows`**.
   - Total Parquet Storage Footprint: **`< 250 KB total`** on HDD D:.
4. **Network Impact**:
   - $\lceil 3,288 / 1,000 \rceil = 4$ HTTP GET requests per symbol.
   - Total requests across universe: **`44 requests total`** ($< 2\%$ of 1-minute rate limit).
   - Ingestion runtime: $< 6.0\text{ seconds}$.

---

## 5. Protocol for Phase 4 Strategy Comparison

Until local funding ingestion is authorized and executed:
1. **Primary Benchmark**: Strategy candidates will be evaluated under a **funding-neutral baseline** (`use_funding = False`), accounting strictly for Taker Fee ($5\text{ bps}$), Maker Fee ($2\text{ bps}$), and Slippage ($2\text{ bps}$).
2. **Clear Labeling**: All strategy comparison tear sheets will carry the label `COST_MODEL: TAKER_5BPS_SLIPPAGE_2BPS (FUNDING_INDEPENDENT)`.
3. **Zero Fabrication**: No synthetic funding payments will be added to backtest ledgers.
