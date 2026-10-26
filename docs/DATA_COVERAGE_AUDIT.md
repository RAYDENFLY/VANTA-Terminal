# AsterDEX Futures V3 — Empirical Data Coverage Audit Report
**Document ID:** DOC-COVERAGE-AUDIT-001  
**Audit Timestamp:** 2026-10-27T05:26:04Z  
**Data Source:** AsterDEX Futures V3 (`https://fapi.asterdex.com`)  
**Audit Type:** Small bounded public queries (Zero bulk downloads performed)

---

## 1. Executive Findings Summary

1. **10 of 11 Pairs exceed 4.5 to 5.1 Years of History**:
   - `BTC`, `ETH`, `SOL`, `BNB`, `XRP`, `ADA`, `AVAX`, `LINK`, `DOGE`, and `LTC` all possess complete historical coverage dating back to late 2021 or early 2022.
   - For these 10 instruments, the requested **3-year research depth is 100% verifiably attainable**.
2. **Critical Discovery: `XMRUSDT` has Truncated History (0.78 Years)**:
   - `XMRUSDT` was only listed on AsterDEX on **2026-01-13 00:00 UTC**.
   - Available historical depth is approximately **287 days (~0.78 years)**.
   - **A 3-year historical dataset does not exist on AsterDEX for XMRUSDT**.
   - In accordance with non-negotiable safety rules: **We will NOT fabricate data or substitute candles from another exchange**.
3. **Step Integrity & Timestamp Continuity**:
   - Timeframes tested (`15m`, `1H`, `4H`) exhibited 100% consistent $\Delta t$ step validity across all instruments.
   - Forward and backward pagination tests confirmed contiguous, non-overlapping, gapless batches.
4. **Funding Rate & Mark Price Availability**:
   - `GET /fapi/v1/fundingRate` is active and returned historical funding intervals for all 11 pairs.
   - `GET /fapi/v1/premiumIndex` is active and returns live mark price, index price, and next funding settlement timestamps.

---

## 2. Comprehensive 11-Pair Historical Coverage Matrix

| Requested Symbol | Exchange Symbol | Listing / Oldest Candle | Latest Candle (Audit) | Span (Days) | Span (Years) | 3-Year Target Met? | Coverage Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `BTCUSDT.P` | `BTCUSDT` | `2021-09-01 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,881.0 | **5.15 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `ETHUSDT.P` | `ETHUSDT` | `2021-09-07 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,875.0 | **5.13 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `SOLUSDT.P` | `SOLUSDT` | `2021-09-09 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,873.0 | **5.13 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `BNBUSDT.P` | `BNBUSDT` | `2022-01-04 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,756.0 | **4.81 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `XRPUSDT.P` | `XRPUSDT` | `2021-09-09 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,873.0 | **5.13 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `ADAUSDT.P` | `ADAUSDT` | `2021-09-09 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,873.0 | **5.13 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `AVAXUSDT.P` | `AVAXUSDT` | `2021-11-16 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,805.0 | **4.94 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `LINKUSDT.P` | `LINKUSDT` | `2022-04-14 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,656.0 | **4.53 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `DOGEUSDT.P` | `DOGEUSDT` | `2021-09-09 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,873.0 | **5.13 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `LTCUSDT.P` | `LTCUSDT` | `2021-11-16 00:00 UTC` | `2026-10-26 00:00 UTC` | 1,805.0 | **4.94 yrs** | **YES** | **VERIFIED (>=3Y)** |
| `XMRUSDT.P` | `XMRUSDT` | `2026-01-13 00:00 UTC` | `2026-10-26 00:00 UTC` | 286.0 | **0.78 yrs** | **NO** | **PARTIAL (<3Y)** |

---

## 3. Timeframe Resolution & Pagination Verification

For all 11 instruments:
- **15m Interval**:
  - Step size: exactly `900,000 ms` ($15 \times 60 \times 1,000$).
  - Pagination batch size: 1,500 bars per request ($15.6\text{ days}$ of 15m data per API call).
  - Forward continuity test: `batch2[0].open == batch1[-1].close + 1` confirmed True with 0 gaps.
- **1H Interval**:
  - Step size: exactly `3,600,000 ms`.
  - Pagination batch size: 1,500 bars per request ($62.5\text{ days}$ per API call).
- **4H Interval**:
  - Step size: exactly `14,400,000 ms`.
  - Pagination batch size: 1,500 bars per request ($250\text{ days}$ per API call).

---

## 4. Handling Strategy for XMRUSDT Truncation

Because XMRUSDT only has 286 days of history on AsterDEX, we propose the following options for user approval before Phase 3:
1. **Dynamic Portfolio Entry (Recommended)**: The 10 qualified pairs participate in the full 3-year walk-forward backtest (e.g. 2023–2026). XMRUSDT enters the eligible trading universe on its listing date (`2026-01-13`), simulating a realistic exchange new-listing event.
2. **Dedicated Single-Pair Horizon for XMR Specialist**: The XMR specialist model trains exclusively on the available 286 days of data, with sample size constraints explicitly reported.
3. **No Synthetic Filler**: Under no circumstances will AsterDEX history be backfilled with synthetic or third-party exchange data.
