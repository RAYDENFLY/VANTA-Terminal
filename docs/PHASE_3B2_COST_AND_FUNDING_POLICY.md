# VANTA Terminal — Transaction Cost & Funding Accounting Policy
**Document ID:** DOC-COSTS-P3B2  
**Phase:** 3B.2 (Cost & Funding Policy)  
**Verification Date:** 2026-10-27  

---

## 1. Transaction Costs & Friction Accounting

A strategy that appears profitable before costs often generates negative returns in real trading. VANTA Terminal enforces rigorous, non-zero friction modeling across every simulated trade.

### Cost Parameters (Standard Tier Assumptions):
| Component | Default Assumption | Implementation Basis | Provenance & Classification |
| :--- | :--- | :--- | :--- |
| **Maker Fee** | `2.0 bps` (`0.02%`) | Applied to passive Take Profit limit orders | `ASSUMPTION_BASED` (AsterDEX V3 Tier 1) |
| **Taker Fee** | `5.0 bps` (`0.05%`) | Applied to all market entries, stop losses, and exits | `ASSUMPTION_BASED` (AsterDEX V3 Standard Taker) |
| **Market Slippage** | `2.0 bps` (`0.02%`) | Adverse price impact applied to executed market fills | `ASSUMPTION_BASED` (Conservative Execution) |

### PnL Decomposition:
Every trade record isolates each cost component:
$$\text{Gross PnL} = (\text{Exit Price} - \text{Entry Price}) \times \text{Quantity} \quad (\text{for Long})$$
$$\text{Total Fees} = \text{Entry Fee} + \text{Exit Fee}$$
$$\text{Net PnL} = \text{Gross PnL} - \text{Total Fees} - \text{Total Slippage} + \text{Cumulative Funding}$$

---

## 2. Historical Funding Accounting Specification

In crypto perpetual futures, funding payments are exchanged peer-to-peer every 8 hours between Longs and Shorts to anchor the perpetual market price to the spot index.

### Settlement Timestamps:
Funding occurs precisely at 8-hour calendar boundaries:
- `00:00:00 UTC`
- `08:00:00 UTC`
- `16:00:00 UTC`

### Sign Conventions:
$$\text{Payment} = -1.0 \times \text{Position Notional} \times \text{Funding Rate} \quad (\text{for Long})$$
$$\text{Payment} = +1.0 \times \text{Position Notional} \times \text{Funding Rate} \quad (\text{for Short})$$

- **When Funding Rate > 0**:
  - Longs pay Shorts. (Long incurs a cash debit; Short receives a cash credit).
- **When Funding Rate < 0**:
  - Shorts pay Longs. (Long receives a cash credit; Short incurs a cash debit).

---

## 3. Funding Data Prerequisite & Blocker Audit

### Current Status:
The OHLCV candlestick archive alone (ingested in Phase 3B.1) does not contain historical funding settlement records.

### Blocker Policy (`BLOCKED_MISSING_FUNDING_DATA`):
1. **Zero Fabrication**: In strict compliance with research ethics, VANTA Terminal **never fabricates funding payments** and **never substitutes current spot premium rates** for unvalidated historical periods.
2. **Automated Blocker Guard**: If a backtest configuration sets `use_funding = True`, but the historical funding dataset has not been ingested and validated for that symbol and date window:
   - The engine **blocks execution immediately**.
   - The run status is set to `BLOCKED_MISSING_FUNDING_DATA`.
   - The validation warning records: `"BLOCKED_MISSING_FUNDING_DATA: Complete historical funding rates for {symbol} not ingested."`
3. **Unblocking Requirements for Future Phases**:
   To unblock historical funding-aware backtests, an ingestion job must be authorized to pull historical funding settlements via AsterDEX's public endpoint `GET /fapi/v1/fundingRate` (paginated at 1,000 records per call) and produce validated Parquet datasets under `data/funding/{symbol}/funding.parquet`.
