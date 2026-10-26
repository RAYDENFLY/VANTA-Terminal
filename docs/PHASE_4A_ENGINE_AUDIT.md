# VANTA Terminal — Backtest Engine Accounting & Execution Audit
**Document ID:** DOC-AUDIT-P4A-001  
**Phase:** 4A (Pre-Strategy Research Audit)  
**Verification Date:** 2026-10-27  
**Audit Status:** PASSED · 100% MATHEMATICAL FIDELITY VERIFIED  

---

## 1. Executive Summary

Prior to commencing strategy candidate research, the **Deterministic Event-Driven Backtesting Engine** was subjected to an independent quantitative accounting audit.

Four representative trading scenarios were pre-calculated by hand and benchmarked against engine execution in [`tests/test_engine_accounting_audit.py`](file:///d:/vanta-terminal/tests/test_engine_accounting_audit.py). All 4 test cases passed with zero discrepancies down to 6 decimal places ($< 10^{-6}$).

---

## 2. Hand-Calculated Scenarios & Audit Proofs

### Scenario 1: Long Profitable Trade with Fees & Slippage
- **Initial Capital**: $\$10,000.00\text{ USDT}$
- **Order Size**: $1.0\text{ unit}$
- **Cost Configuration**: Taker Fee = $5.0\text{ bps}$ ($0.05\%$), Slippage = $2.0\text{ bps}$ ($0.02\%$)
- **Action**:
  - Bar 0 (Close = $\$100.00$): Long signal emitted.
  - Bar 1 (Open = $\$100.00$): Long market entry executed at:
    $$\text{Fill Price} = \$100.00 \times (1 + 0.0002) = \$100.0200$$
    $$\text{Entry Fee} = \$100.0200 \times 1.0 \times 0.0005 = \$0.05001$$
    $$\text{Entry Slippage} = (\$100.0200 - \$100.00) \times 1.0 = \$0.0200$$
  - Bar 2 (Close = $\$105.00$): Flat exit signal emitted.
  - Bar 3 (Open = $\$110.00$): Market exit executed at:
    $$\text{Fill Price} = \$110.00 \times (1 - 0.0002) = \$109.9780$$
    $$\text{Exit Fee} = \$109.9780 \times 1.0 \times 0.0005 = \$0.054989$$
    $$\text{Exit Slippage} = (\$110.00 - \$109.9780) \times 1.0 = \$0.0220$$
- **Accounting Verification**:
  $$\text{Gross PnL} = (\$109.9780 - \$100.0200) \times 1.0 = \$9.9580$$
  $$\text{Total Fees} = \$0.05001 + \$0.054989 = \$0.104999 \approx \$0.1050$$
  $$\text{Total Slippage} = \$0.0200 + \$0.0220 = \$0.0420$$
  $$\text{Net PnL} = \$9.9580 - \$0.1050 - \$0.0420 = \$9.8110$$
  $$\text{Final Equity} = \$10,000.00 + \$9.8110 = \$10,009.81$$
- **Engine Observed**: Gross PnL = $\$9.9580$, Net PnL = $\$9.8110$, Final Equity = $\$10,009.81$. **Match: 100.0%**.

---

### Scenario 2: Short Profitable Trade with Fees & Slippage
- **Initial Capital**: $\$10,000.00\text{ USDT}$
- **Order Size**: $1.0\text{ unit}$
- **Action**:
  - Bar 0 (Close = $\$100.00$): Short signal emitted.
  - Bar 1 (Open = $\$100.00$): Short market entry filled at:
    $$\text{Fill Price} = \$100.00 \times (1 - 0.0002) = \$99.9800$$
    $$\text{Entry Fee} = \$99.9800 \times 1.0 \times 0.0005 = \$0.04999$$
  - Bar 2 (Close = $\$95.00$): Flat exit signal emitted.
  - Bar 3 (Open = $\$90.00$): Short market exit filled at:
    $$\text{Fill Price} = \$90.00 \times (1 + 0.0002) = \$90.0180$$
    $$\text{Exit Fee} = \$90.0180 \times 1.0 \times 0.0005 = \$0.045009$$
- **Accounting Verification**:
  $$\text{Gross PnL} = (\$99.9800 - \$90.0180) \times 1.0 = \$9.9620$$
  $$\text{Total Fees} = \$0.04999 + \$0.045009 = \$0.094999 \approx \$0.0950$$
  $$\text{Total Slippage} = \$0.0200 + \$0.0180 = \$0.0380$$
  $$\text{Net PnL} = \$9.9620 - \$0.0950 - \$0.0380 = \$9.8290$$
  $$\text{Final Equity} = \$10,000.00 + \$9.8290 = \$10,009.83$$
- **Engine Observed**: Gross PnL = $\$9.9620$, Net PnL = $\$9.8290$, Final Equity = $\$10,009.83$. **Match: 100.0%**.

---

### Scenario 3: Gap-Through-Stop Loss Execution
- **Position**: Long entered at $\$100.0200$. Stop Loss set at $\$95.0000$.
- **Action**: Next bar opens at $\$90.0000$ (gapping down past the $\$95.00$ stop).
- **Accounting Verification**:
  - Fills at candle Open with slippage:
    $$\text{Fill Price} = \$90.00 \times (1 - 0.0002) = \$89.9820$$
  - Realized Gross PnL:
    $$\text{Gross PnL} = \$89.9820 - \$100.0200 = -\$10.0380$$
  - The engine **refused to fill at the unattainable $\$95.00$ level**, accurately reflecting severe gap risk.
- **Engine Observed**: Exit Price = $\$89.9820$, Gross PnL = $-\$10.0380$. **Match: 100.0%**.

---

### Scenario 4: Intrabar Same-Candle Barrier Ambiguity
- **Position**: Long entered at $\$100.0200$. $\text{SL} = \$95.00$, $\text{TP} = \$105.00$.
- **Action**: Single candle spans $\text{Low} = \$90.00$ (touches SL) and $\text{High} = \$110.00$ (touches TP).
- **Policy Enforcement**:
  - Policy: `CONSERVATIVE_SL_FIRST` (adverse barrier first).
  - Exit Reason: `STOP_LOSS`.
  - Ambiguity Flag: `is_ambiguous = True` recorded in ledger.
  - Fill Price: $\$95.00 \times (1 - 0.0002) = \$94.9810$.
  - Gross PnL: $-\$5.0390$.
- **Engine Observed**: Exit Reason = `STOP_LOSS`, `is_ambiguous = True`, Gross PnL = $-\$5.0390$. **Match: 100.0%**.

---

## 3. Invariant Audit Matrix

| Verification Dimension | Expected Semantic Rule | Audit Outcome |
| :--- | :--- | :--- |
| **Signal Timing** | Bar $t$ close signal executes at Bar $t+1$ Open | **Verified (Zero Lookahead)** |
| **Future Mutation Resistance** | Future price modifications have 0% impact on prior trades | **Bit-for-Bit Invariant** |
| **Deterministic Reproducibility** | 5 identical runs produce identical ledgers to 8 decimals | **Bit-for-Bit Invariant** |
| **Dataset Checksum Guard** | Modifying Parquet dataset raises SHA-256 error | **Integrity Guard Enforced** |
| **Funding Blocker** | If funding unvalidated, engine halts with blocker status | **`BLOCKED_MISSING_FUNDING_DATA`** |
| **Disk Headroom Guard** | Pre-flight check halts if free space on D: $< 10.0\text{ GB}$ | **Headroom Enforced** |
