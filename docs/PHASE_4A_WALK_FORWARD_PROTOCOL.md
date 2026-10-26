# VANTA Terminal — Walk-Forward Benchmark Protocol
**Document ID:** DOC-WFP-P4A-001  
**Phase:** 4A / 4A.1 (Protocol Reconciled & Frozen)  
**Verification Date:** 2026-10-27  
**Status:** RECONCILED & FROZEN FOR BENCHMARKING  

---

## 1. Executive Summary & Core Mandate

The primary vulnerability in quantitative crypto strategy research is **selection bias and data leakage** caused by:
1. In-sample overfitting through unrestricted parameter searches.
2. Contamination of out-of-sample test data via overlapping lookback windows or forward information flow.
3. Premature exposure or informal inspection of the test set during iterative strategy development.

To guarantee institutional-grade statistical rigor, this document pre-registers the **Walk-Forward Validation Protocol with Purging, Embargo, and Absolute Holdout Quarantine** for VANTA Terminal across the perpetual universe.

---

## 2. Chronological Universe Partitioning & Absolute Holdout Quarantine

### 2.1 The Untouched Test Set (Holdout Quarantine)
A foundational principle of VANTA Terminal is that **the final 6 months of historical data are strictly quarantined across the entire universe**:
- **Quarantine Period**: `2026-04-26 00:00:00 UTC` to `2026-10-26 00:00:00 UTC` ($183\text{ days}$).
- **Absolute Quarantine Mandate**: Under **NO circumstances** is any pair—including `XMRUSDT`—evaluated, backtested, inspected, ranked, or tuned against this window during Phase 4 (Candidate Strategy Benchmarking) or Phase 5 (ML Model Arena).
- **Physical Isolation**: Data loading pipelines for Phase 4 and Phase 5 hard-cap historical candle timestamps at `< 1777161600000` (`2026-04-26 00:00:00 UTC`).
- **Release Condition**: The quarantined holdout is unsealed exclusively during the authorized one-shot Out-Of-Sample Final Audit in Phase 6.

### 2.2 Rolling Walk-Forward Folds (10 Qualified Pairs)
For the 10 qualified pairs with complete 3-year history (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `XRPUSDT`, `ADAUSDT`, `AVAXUSDT`, `LINKUSDT`, `DOGEUSDT`, `LTCUSDT`), the pre-quarantine history spans `2023-10-26 00:00:00 UTC` to `2026-04-26 00:00:00 UTC` ($913\text{ days}$).

We partition this period into three **Rolling (Fixed-Length 12-Month In-Sample, 6-Month Out-Of-Sample)** folds:

```
[--- 2023-10-26 ----------------------------- 2026-04-26 --------- 2026-10-26 ---]
Fold 1:  |==== IS 1 (12m) ====|--- OOS 1 (6m) ---|
Fold 2:         |==== IS 2 (12m) ====|--- OOS 2 (6m) ---|
Fold 3:                |==== IS 3 (12m) ====|--- OOS 3 (6m) ---|
Holdout (Phase 6):                                      |*** QUARANTINE (6m) ***|
```

#### Detailed Fold Schedule:
| Fold Name | Split Phase | Start Timestamp (UTC) | End Timestamp (UTC) | Duration | Candle Count (15m) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fold 1** | In-Sample (Train) | `2023-10-26 00:00:00` | `2024-10-26 00:00:00` | 366 days | 35,136 bars |
| | *Purge Window* | `2024-10-24 00:00:00` | `2024-10-26 00:00:00` | 48.0 hours | 192 bars (15m) / 48 bars (1H) |
| | *Embargo Window*| `2024-10-26 00:00:00` | `2024-10-28 00:00:00` | 48.0 hours | Burn-in indicator warmup |
| | Out-of-Sample (Val) | `2024-10-28 00:00:00` | `2025-04-26 00:00:00` | 180 days | 17,280 bars |
| **Fold 2** | In-Sample (Train) | `2024-04-26 00:00:00` | `2025-04-26 00:00:00` | 365 days | 35,040 bars |
| | *Purge Window* | `2025-04-24 00:00:00` | `2025-04-26 00:00:00` | 48.0 hours | 192 bars (15m) / 48 bars (1H) |
| | *Embargo Window*| `2025-04-26 00:00:00` | `2025-04-28 00:00:00` | 48.0 hours | Burn-in indicator warmup |
| | Out-of-Sample (Val) | `2025-04-28 00:00:00` | `2025-10-26 00:00:00` | 181 days | 17,376 bars |
| **Fold 3** | In-Sample (Train) | `2024-10-26 00:00:00` | `2025-10-26 00:00:00` | 365 days | 35,040 bars |
| | *Purge Window* | `2025-10-24 00:00:00` | `2025-10-26 00:00:00` | 48.0 hours | 192 bars (15m) / 48 bars (1H) |
| | *Embargo Window*| `2025-10-26 00:00:00` | `2025-10-28 00:00:00` | 48.0 hours | Burn-in indicator warmup |
| | Out-of-Sample (Val) | `2025-10-28 00:00:00` | `2026-04-26 00:00:00` | 180 days | 17,280 bars |
| **Holdout** | **Quarantined Test**| `2026-04-26 00:00:00` | `2026-10-26 00:00:00` | 183 days | **LOCKED UNTIL PHASE 6** |

### 2.3 Statistical Non-Independence Clarification
- The walk-forward scheme is strictly **rolling**, with In-Sample windows shifting by $6\text{ months}$ while spanning $12\text{ months}$. Consequently, adjacent In-Sample windows have an exact **$50\%$ chronological overlap**.
- Although the Out-of-Sample validation windows are non-overlapping in time ($18\text{ months}$ of contiguous evaluation from October 2024 to April 2026), the parameter vectors $\theta^*_1, \theta^*_2, \theta^*_3$ are fitted on overlapping historical data.
- **Protocol Warning**: Performance observations across the three folds are **autocorrelated and must NOT be treated as independent, identically distributed (i.i.d.) random samples**. All summary metrics report cross-fold dispersion, and hypothesis tests account for degrees-of-freedom adjustments.

---

## 3. Pair Universe Lifecycle & Denominator Accounting

### 3.1 Three Mutually Exclusive Pair States
Each instrument in the research universe is assigned one of three formal lifecycle states:

1. **`ELIGIBLE` (10 Qualified Pairs)**:
   - `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `XRPUSDT`, `ADAUSDT`, `AVAXUSDT`, `LINKUSDT`, `DOGEUSDT`, `LTCUSDT`.
   - Continuous verified history $\ge 3\text{ years}$ ($105,216\text{ bars}$ on 15m).
   - Fully active across all 3 Walk-Forward Folds.
   - Forms the **sole denominator ($N_{qual} = 10$)** for the primary Spatial Robustness Gate.
2. **`PARTIAL_HISTORY` (`XMRUSDT`)**:
   - Continuous verified history starts on `2026-01-13 16:45:00 UTC` ($286\text{ days}$ total).
   - Pre-quarantine history: Exactly **$103\text{ days}$** (`2026-01-13 17:00:00` to `2026-04-26 00:00:00 UTC`).
   - In-Sample history in Folds 1, 2, and 3: **$0\text{ days}$**.
   - Status: Non-voting exploratory observer. Evaluated only during its $103\text{ days}$ active window in Fold 3 OOS; strictly excluded from the spatial robustness denominator.
3. **`INSUFFICIENT_SAMPLE`**:
   - Any qualified pair that generates $< 20\text{ completed trades}$ over the 3 OOS validation folds is designated as `INSUFFICIENT_SAMPLE`.
   - Treatment: Counted strictly as **$\text{Net PnL} \le 0$ (FAIL)** for spatial robustness. It cannot be omitted or dropped to artificially boost pass rates.

### 3.2 Non-Fabrication Rule
Zero synthetic back-padding, price simulation, or cross-pair proxy substitution is permitted for `XMRUSDT` prior to `2026-01-13`.

---

## 4. Purging, Embargo & Boundary Liquidation Mechanics

To prevent cross-boundary information contamination and trade leakage:

### 4.1 Purge Window ($48.0\text{ Hours}$)
The purge duration is standardized to **$48.0\text{ hours}$ (192 bars on 15m, 48 bars on 1H)**, matching the maximum holding duration across all candidate strategies ($T_{max} = 48\text{ bars}$ for 1H Breakout):
- **Cutoff Timestamp**: $T_{cutoff} = T_{split} - 48\text{h}$.
- **Rule**: At $T_{cutoff}$, signal generation for In-Sample evaluation ceases.
- **Forced Liquidation**: Any position remaining open at $T_{split}$ is forcefully closed on the final bar of the In-Sample period at Market Close and recorded in the In-Sample ledger with exit reason `BOUNDARY_FLAT`.

### 4.2 Split Boundary Clean Slate
- **Zero Carry-Over**: No open position, pending order, trailing stop, or unrealized PnL carries across $T_{split}$ into Out-of-Sample.
- **Clean Slate**: The Out-of-Sample portfolio initializes strictly at $100\%$ cash ($\$10,000.00\text{ USDT}$) with `FLAT` positions across all pairs.

### 4.3 Embargo Window ($48.0\text{ Hours}$)
- To prevent cold-start indicator distortion (e.g., 50 EMA, 20 Donchian, 14 ATR), an initial $48.0\text{-hour}$ warm-up buffer is enforced at the start of Out-of-Sample.
- Indicators update causally during this buffer, but no entry signals are acted upon until $T_{split} + 48\text{h}$.

---

## 5. Parameter Tuning Budget & Optimization Discipline

To prevent data mining and *p-hacking*:

1. **Strict 12-Configuration Budget**: For each strategy candidate, exactly **12 pre-registered parameter configurations** may be evaluated on In-Sample data.
2. **Objective Function for Parameter Selection**:
   The optimal parameter vector $\theta^*$ is selected within the In-Sample partition using a single pre-registered objective:
   $$\theta^* = \arg\max_{\theta \in \Theta_{12}} \left( \text{Sharpe Ratio}_{IS}(\theta) \times \min\left(1.0, \frac{N_{trades, IS}(\theta)}{50}\right) \right)$$
   subject to the hard constraint:
   $$\text{Max Drawdown}_{IS}(\theta) \le 15.0\%$$
3. **One-Shot Out-of-Sample Evaluation**: Once $\theta^*$ is selected from In-Sample, it is evaluated on the Out-of-Sample validation fold **exactly once**.
4. **Re-Tuning Ban**: Re-tuning or adjusting parameters after observing OOS performance is strictly prohibited. If $\theta^*$ fails an OOS gate, the candidate fails that fold.
