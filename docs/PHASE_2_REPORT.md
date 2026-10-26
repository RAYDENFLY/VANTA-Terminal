# VANTA Terminal — Phase 2 Implementation & Audit Report
**Document ID:** DOC-REPORT-P2  
**Audit Timestamp:** 2026-10-27T05:28:00+07:00  
**Phase Status:** COMPLETED · AUDIT VERIFIED · ZERO BULK DATA DOWNLOADED  
**Safety Protocol:** Read-Only Public Inspection Only · Zero Orders · Zero Fabricated Data

---

## 1. Executive Summary

Phase 2 has successfully audited the official **AsterDEX Futures V3 (Pro API)** endpoints, verified all eleven requested perpetual-futures instruments, empirically measured historical data coverage across all timeframes, and established a conservative local storage budget.

### Crucial Empirical Discoveries:
1. **Exchange Native Identifiers**: The requested `.P` suffix (e.g. `BTCUSDT.P`) is an external convention. The exchange-native identifiers are standard uppercase symbols: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `XRPUSDT`, `ADAUSDT`, `AVAXUSDT`, `LINKUSDT`, `DOGEUSDT`, `LTCUSDT`, and `XMRUSDT`. All 11 instruments are currently in `TRADING` status with `PERPETUAL` contract type settled in `USDT`.
2. **10 of 11 Instruments Exceed 4.5 to 5.1 Years of History**:
   `BTC`, `ETH`, `SOL`, `BNB`, `XRP`, `ADA`, `AVAX`, `LINK`, `DOGE`, and `LTC` all possess historical candles dating back to late 2021 / early 2022. For these 10 pairs, the requested **3-year research horizon is verifiably available**.
3. **`XMRUSDT` Truncation (0.78 Years)**:
   `XMRUSDT` was only listed on AsterDEX on **2026-01-13 00:00 UTC**. It possesses approximately **286 days (~0.78 years)** of history. **A 3-year historical dataset does not natively exist for XMRUSDT on AsterDEX**. Per our safety guidelines, no synthetic filler or third-party exchange data will be substituted.
4. **Endpoint Performance & Pagination**:
   The kline endpoint supports up to **1,500 bars per query** ($15.6\text{ days}$ of 15m data per call). Pagination tests confirmed contiguous, non-overlapping step intervals with 0 duplicates. Rate limit capacity is generous at **2,400 request weight units per minute**.
5. **Storage Feasibility**:
   A complete 3-year raw Parquet dataset across all 11 pairs and 3 timeframes requires only **~60 MB**. The recommended full project budget (including features, models, ledgers, and safety reserve) is **2.6 GB on HDD D:**, preserving over **62 GB** of free headroom.

---

## 2. Official Documentation References

- **API Documentation Repository**: [https://github.com/asterdex/api-docs](https://github.com/asterdex/api-docs)
- **Futures V3 General Info**: [https://asterdex.github.io/aster-api-website/futures-v3/general-info/](https://asterdex.github.io/aster-api-website/futures-v3/general-info/)
- **Verification Date**: `2026-10-27`
- **Production Base URL**: `https://fapi.asterdex.com` (Verified live and responsive)
- **Testnet Base URL**: `https://fapi.asterdex-testnet.com`

---

## 3. Verified Instrument Discovery Matrix

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

---

## 4. Empirical Historical Coverage Matrix

| Exchange Symbol | Oldest Candle Timestamp | Oldest UTC Date | Audit End Date | Historical Span | 3-Year Target | Audit Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `BTCUSDT` | `1630454400000` | `2021-09-01 00:00` | `2026-10-26 00:00` | 1,881 days (**5.15 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `ETHUSDT` | `1630972800000` | `2021-09-07 00:00` | `2026-10-26 00:00` | 1,875 days (**5.13 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `SOLUSDT` | `1631145600000` | `2021-09-09 00:00` | `2026-10-26 00:00` | 1,873 days (**5.13 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `BNBUSDT` | `1641254400000` | `2022-01-04 00:00` | `2026-10-26 00:00` | 1,756 days (**4.81 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `XRPUSDT` | `1631145600000` | `2021-09-09 00:00` | `2026-10-26 00:00` | 1,873 days (**5.13 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `ADAUSDT` | `1631145600000` | `2021-09-09 00:00` | `2026-10-26 00:00` | 1,873 days (**5.13 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `AVAXUSDT` | `1637020800000` | `2021-11-16 00:00` | `2026-10-26 00:00` | 1,805 days (**4.94 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `LINKUSDT` | `1649894400000` | `2022-04-14 00:00` | `2026-10-26 00:00` | 1,656 days (**4.53 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `DOGEUSDT` | `1631145600000` | `2021-09-09 00:00` | `2026-10-26 00:00` | 1,873 days (**5.13 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `LTCUSDT` | `1637020800000` | `2021-11-16 00:00` | `2026-10-26 00:00` | 1,805 days (**4.94 yrs**) | **MET** | **VERIFIED (>=3Y)** |
| `XMRUSDT` | `1768262400000` | `2026-01-13 00:00` | `2026-10-26 00:00` | 286 days (**0.78 yrs**) | **NOT MET** | **PARTIAL (<3Y)** |

---

## 5. Pagination, Rate Limits & Step Integrity

1. **Endpoint Parameters**:
   - `GET /fapi/v1/klines`: Parameters `symbol`, `interval`, `startTime`, `endTime`, `limit`.
   - Max Limit: Tested up to 1,500 bars per call. 2,000 bars returned 400 Bad Request.
2. **Forward & Backward Pagination**:
   - Forward continuity verified: Passing `startTime = batch1[-1].close_time + 1` produced contiguous bars with zero gaps (`batch2[0].open_time == batch1[-1].open_time + 900,000 ms`).
   - Backward query verified: Passing `endTime` retrieves historical bars ending on or before the requested millisecond.
3. **Funding Rate & Mark Price**:
   - `GET /fapi/v1/fundingRate` verified active for all 11 pairs.
   - `GET /fapi/v1/premiumIndex` verified active returning live mark price, index price, and next funding settlement timestamps.

---

## 6. Storage Budget & Hardware Allocation

- **Free Space Available**:
  - Drive C: (NVMe SSD): **20.68 GB** (Zero data storage allocated to C:)
  - Drive D: (Data HDD): **64.93 GB**
- **Projected Footprint**:
  - Raw 3-Year Parquet (11 pairs, 3 timeframes): ~60 MB
  - Processed Feature Store (30 engineered features): ~140 MB
  - Model Artifacts (LightGBM/XGBoost trees): ~50 MB
  - Ledgers & SQLite: ~30 MB
  - Emergency Safety Buffer: 1,500 MB
  - **Total Recommended Allocation**: **2.6 GB on Drive D:** (leaving > 62.3 GB free headroom).

---

## 7. Deliverables & Code Artifacts

### Documentation
- [`docs/ASTERDEX_V3_API_AUDIT.md`](file:///D:/vanta-terminal/docs/ASTERDEX_V3_API_AUDIT.md) — Comprehensive public API reference, endpoint paths, rate limits, and symbol discovery.
- [`docs/DATA_COVERAGE_AUDIT.md`](file:///D:/vanta-terminal/docs/DATA_COVERAGE_AUDIT.md) — Empirical coverage matrix, listing timestamps, step integrity, and XMR handling options.
- [`docs/STORAGE_BUDGET.md`](file:///D:/vanta-terminal/docs/STORAGE_BUDGET.md) — Hardware analysis, candle volume estimates, and safe disk budget.
- [`docs/PHASE_2_REPORT.md`](file:///D:/vanta-terminal/docs/PHASE_2_REPORT.md) — This complete delivery report.

### Code & Data Manifests
- `backend/data/asterdex_client.py` — Dedicated public AsterDEX V3 HTTP client with bounded retries and schema validation.
- `backend/data/coverage_audit.py` — Audit result processor serving verified public metadata to the API.
- `data/manifests/asterdex_v3_coverage_audit.json` — Immutable machine-readable audit report containing the verified timestamps and pagination records for all 11 pairs.
- `tests/test_api.py` — Updated with unit tests for AsterDEX V3 public client and audit endpoints.

---

## 8. Verification Testing

Executed via `python -m pytest tests/test_api.py -v`:
- `12 passed in 1.30s` (All API endpoints and adapter tests passing).
- Frontend production build (`npm run build`): All 11 pages compiled with 0 errors.

---

## 9. Recommendations for Phase 3 & Completion Checkpoint

1. **Approval to Proceed**: Phase 2 is complete. **Zero bulk data has been downloaded and zero live orders have been placed.**
2. **Strategy for XMRUSDT**: In Phase 3, we recommend adopting the **Dynamic Listing Entry** rule: the 10 qualified pairs participate across the full 3-year walk-forward evaluation, and XMRUSDT enters the eligible portfolio universe on its listing date (`2026-01-13`).
3. **Checkpoint**: Standing by for your approval of the audit findings and storage budget before commencing **PHASE 3 (Parquet Ingestion Pipeline & Deterministic Simulator)**.
