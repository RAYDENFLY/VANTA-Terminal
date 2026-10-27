# VANTA Terminal — Phase 4B.2 Portfolio Equity & Risk Audit Report

**Workstation**: VANTA Terminal Quantitative Research Station  
**Document ID**: `VANTA-PHASE4B2-RISK-AUDIT-20261027`  
**Date**: October 27, 2026  
**Auditor**: Independent Portfolio & Risk Diagnostic Engine  
**Execution Context**: Sequential Single-Worker (`VANTA_MAX_WORKERS=1`), Offline Local Backtesting Engine  
**Dataset Quarantine**: Historical range strictly `< 2026-04-26T00:00:00Z` (`open_time < 1777161600000`)  
**Audit Scope**: Multi-Pair Portfolio Accounting, Simultaneous Positions, Equity Reset Semantics, Chronological vs Serialized Drawdown Math  
**Overall Exit Status**: **`RISK_AUDIT_PASS_WITH_LIMITATIONS`**  
**Certified Benchmark Verdict**: **`NO_CHANGE`** (`NO_QUALIFIED_STRATEGY` preserved; Strategy B remains `UNQUALIFIED_BASELINE`)  

---

## 1. Executive Summary

Phase 4B.2 was authorized to perform a rigorous diagnostic audit of the portfolio equity curves, maximum drawdown (MDD) semantics, position overlap, and multi-pair capital allocation models reported during the Phase 4B benchmark. 

### Core Audit Verdicts

1. **Exact Mathematical Reproduction (`VERIFIED_FROM_CODE_AND_ARTIFACTS`)**:
   - Strategy B's reported **`14.89%`** MDD, Strategy A's **`272.65%`** MDD, and Strategy C's **`69.55%`** MDD were **exactly reproduced to 4 decimal places** (`14.8910%`, `272.6491%`, and `69.5451%`) directly from the 30 saved Out-Of-Sample (OOS) run ledgers in `data/backtests/`.
   - All trade counts (A: 16,934; B: 2,851; C: 3,362) and net PnL figures (A: -$27,264.91; B: +$914.31; C: -$6,946.99) reconcile 100% with the master manifest.

2. **Equity Accounting Architecture Identified (`DISCREPANCY / LIMITATION`)**:
   - **Trade-Close Cashflows vs MTM**: Reported benchmark drawdowns were computed strictly from closed-trade net cashflows (`t.net_pnl`), ignoring mark-to-market unrealized excursions during open trade holding periods.
   - **Serialized Pair Concatenation vs True Chronology**: The benchmark runner appended trades pair-by-pair within each fold rather than interweaving them chronologically by exit timestamp. When recomputed in true chronological sequence by `exit_time_ms`, Strategy B's continuous cashflow MDD rises from **`14.89%`** to **`17.15%`**.
   - **Fold Reset Compounding**: The benchmark reset cash to $10,000 for each OOS fold in the engine, but calculated overall MDD by compounding cashflows continuously across all 3 folds on top of prior fold equity. When evaluated independently with a fresh $10,000 capital base, Fold 3 alone suffered an exit-time chronological drawdown of **`18.74%`**.
   - **Un-Clamped Cumulative Strategy Drag**: Strategy A's 272.65% MDD reflects cumulative unhedged loss across 10 unconstrained streams ($2.72\times$ base capital). In an isolated account with a physical bankruptcy floor ($0.00 cash), maximum possible drawdown is clamped at **`100.0%`**.

3. **Qualification Gate & Baseline Impact (`NO_CHANGE`)**:
   - In Phase 4B, Strategy B already failed GATE-2 (Expectancy: 3.26 bps vs 8.0 bps), GATE-3 (Profit Factor: 1.029 vs 1.25), GATE-7 (6/10 profitable pairs vs 7/10), and GATE-8 (Friction stress: -$1,078.63 vs >$0).
   - Under true chronological execution, Strategy B also breaches GATE-1 (17.15% > 15.0%). This further reinforces the failure of heuristic candidates.
   - The certified global outcome remains strictly **`NO_QUALIFIED_STRATEGY`**, and Strategy B remains designated as the **`UNQUALIFIED_BASELINE`**.

---

## 2. Mandatory Findings Matrix (A through G)

| Item | Dimension | Finding & Mathematical Reality | Audit Classification |
| :--- | :--- | :--- | :---: |
| **A** | **Equity Series Definition** | Reported MDD was computed from a discrete trade-close cumulative cashflow series: `cum_equity += t.net_pnl`. Intrabar excursions and candle-marked equity (`equity_curve.json`) were not used. | `VERIFIED_FROM_CODE_AND_ARTIFACTS` |
| **B** | **Chronological Processing** | Trades were serialized pair-by-pair within folds (Fold 1: ADA...XRP, Fold 2: ADA...XRP). Simultaneous positions were not interwoven in real time. Sorting chronologically increases Strategy B MDD to **17.15%**. | `DISCREPANCY` |
| **C** | **Capital Allocation Model** | The engine ran 10 independent sub-accounts of $10,000 each ($100,000 total capital deployed). Sizing was local ($1,000 notional/trade). The $10,000 portfolio curve is a synthetic normalization convention. | `VERIFIED_FROM_CODE_AND_ARTIFACTS` |
| **D** | **Fold-Level MDD vs Reset** | Folds reset to $10,000 in the engine, but combined MDD compounded across folds. Fold-specific chronological MDD for Strategy B was **12.43%** (Fold 1), **12.63%** (Fold 2), and **18.74%** (Fold 3). | `VERIFIED_FROM_CODE_AND_ARTIFACTS` |
| **E** | **Strategy B MDD Reproduction** | Strategy B's reported 14.89% MDD was reproduced exactly as **14.8910%** using the 30 saved OOS run ledgers in `data/backtests/`. | `VERIFIED_FROM_CODE_AND_ARTIFACTS` |
| **F** | **Strategy A MDD Interpretation** | Strategy A's 272.65% MDD measures cumulative strategy drag ($2.72\times$ base unit capital lost to friction). Under a standard financial bankruptcy floor ($0 equity), MDD is clamped at **100.0%**. | `VERIFIED_FROM_CODE_AND_ARTIFACTS` |
| **G** | **Qualification Gate Decision** | No gate decision is overturned. All 3 candidates fail qualification. Strategy B remains the active quantitative hurdle (`UNQUALIFIED_BASELINE`). | `VERIFIED_FROM_CODE_AND_ARTIFACTS` |

---

## 3. Detailed Empirical Analysis

### 3.1. Re-Evaluation of Strategy B (Donchian Breakout, 1H)

Strategy B was evaluated across 2,851 OOS trades over 18 months (3 folds of 6 months each).

```
Fold 1 (2024-10-28 to 2025-04-25): 954 trades  | Net PnL: +$1,691.70
Fold 2 (2025-04-28 to 2025-10-25): 859 trades  | Net PnL: +$372.55
Fold 3 (2025-10-28 to 2026-04-25): 1038 trades | Net PnL: -$1,149.95
Combined Total:                    2851 trades | Net PnL: +$914.31
```

#### Multi-Drawdown Comparative Matrix for Strategy B

| Methodology / Ordering | Fold 1 MDD | Fold 2 MDD | Fold 3 MDD | Combined 3-Fold MDD | Peak Equity / HWM | End Equity | Gate 1 Pass/Fail |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Reported Runner (Pair-Concatenated)** | 10.81% | 6.01% | 14.40% | **14.89%** | $12,721.55 | $10,914.31 | `PASS` (Hurdle $\le 15.0\%$) |
| **Chronological Exit-Time (`exit_time_ms`)** | 12.43% | 12.63% | **18.74%** | **17.15%** | $12,884.54 | $10,914.31 | `FAIL` ($17.15\% > 15.0\%$) |
| **Chronological Entry-Time (`entry_time_ms`)** | 12.46% | 12.31% | **19.36%** | **17.37%** | $12,918.55 | $10,914.31 | `FAIL` ($17.37\% > 15.0\%$) |
| **True MTM (10-Account $100k Base)** | 2.03% | 1.59% | 2.23% | **N/A (Per Fold)** | $102,063.10 | $100,914.31 | `PASS` ($\le 15.0\%$) |
| **True MTM (Normalized $10k Base)** | 15.45% | 14.39% | **20.72%** | **N/A (Per Fold)** | $12,063.10 | $10,914.31 | `FAIL` ($20.72\% > 15.0\%$) |

#### Key Technical Insights for Strategy B
1. **The Serialization Illusion**:
   - In Fold 2, pair-concatenated ordering showed an MDD of only **`6.01%`**. However, in true chronological time, drawdown was **`12.63%`**—more than double!
   - Serializing trades by symbol artificial smoothed the equity trajectory because winning clusters in one symbol (e.g. SOL) were processed after losing clusters in another symbol (e.g. AVAX), rather than colliding at the same calendar moment.
2. **Fold 3 Collapse**:
   - In Fold 3 (late 2025 to early 2026), trend persistence degraded across crypto-futures. Under true chronological ordering, Fold 3 suffered an independent **`18.74%`** drawdown on its $10,000 starting cash.
   - The reported combined MDD (14.89%) masked this severity because Fold 3 began with accumulated buffer from Folds 1 and 2 ($12,721.55 HWM), dampening the percentage drop.

---

### 3.2. Simultaneous Positions & Capital Overlap (Strategy B)

Because the backtest engine executed each pair independently, the multi-pair portfolio ran with unconstrained parallel positioning. Below is the exact distribution of simultaneous positions sampled hourly across the 10 pairs:

| Simultaneous Positions Open | Fold 1 Hours (% Time) | Fold 2 Hours (% Time) | Fold 3 Hours (% Time) | Combined Hours (% Time) | Gross Notional Exposure |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0 positions (All Flat)** | 879 hrs (20.3%) | 818 hrs (18.8%) | 1,038 hrs (24.0%) | 2,735 hrs (21.1%) | $0.00 |
| **1 position** | 905 hrs (20.9%) | 809 hrs (18.6%) | 691 hrs (16.0%) | 2,405 hrs (18.5%) | ~$1,000 |
| **2 positions** | 616 hrs (14.3%) | 790 hrs (18.2%) | 385 hrs (8.9%) | 1,791 hrs (13.8%) | ~$2,000 |
| **3 positions** | 576 hrs (13.3%) | 502 hrs (11.6%) | 263 hrs (6.1%) | 1,341 hrs (10.3%) | ~$3,000 |
| **4 positions** | 353 hrs (8.2%) | 348 hrs (8.0%) | 236 hrs (5.5%) | 937 hrs (7.2%) | ~$4,000 |
| **5 positions** | 209 hrs (4.8%) | 350 hrs (8.1%) | 282 hrs (6.5%) | 841 hrs (6.5%) | ~$5,000 |
| **6 positions** | 197 hrs (4.6%) | 290 hrs (6.7%) | 228 hrs (5.3%) | 715 hrs (5.5%) | ~$6,000 |
| **7 positions** | 177 hrs (4.1%) | 212 hrs (4.9%) | 248 hrs (5.7%) | 637 hrs (4.9%) | ~$7,000 |
| **8 positions** | 119 hrs (2.8%) | 80 hrs (1.8%) | 231 hrs (5.3%) | 430 hrs (3.3%) | ~$8,000 |
| **9 positions** | 142 hrs (3.3%) | 92 hrs (2.1%) | 298 hrs (6.9%) | 532 hrs (4.1%) | ~$9,000 |
| **10 positions (Full Basket)** | 147 hrs (3.4%) | 53 hrs (1.2%) | 420 hrs (9.7%) | 620 hrs (4.8%) | ~$10,000 |

#### Portfolio Leverage Metrics
- **Average Simultaneous Positions**:
  - Fold 1: **2.88 pairs** ($2,902.92 average notional; 0.29x leverage on $10k base).
  - Fold 2: **2.82 pairs** ($2,815.70 average notional; 0.28x leverage on $10k base).
  - Fold 3: **3.81 pairs** ($3,775.56 average notional; 0.38x leverage on $10k base).
- **Peak Notional & Leverage**:
  - Peak simultaneous positions reached **10 out of 10 pairs** in all three folds.
  - Peak aggregate notional: **$10,161.72** (Fold 1), **$10,080.98** (Fold 2), **$10,021.85** (Fold 3).
  - Peak leverage on $10,000 base: **1.02x** (effectively 100% margin utilization).
  - Peak leverage on $100,000 base: **0.10x**.

---

### 3.3. Reconciliation of Strategy A (Sweep-Reclaim, 15m)

Strategy A experienced severe structural failure under transaction costs:

```
Total Trades: 16,934 | Net PnL: -$27,264.91
Gross PnL: -$6,835.35 | Fees: $14,809.71 | Slippage: $5,619.85
```

#### Drawdown Metrics for Strategy A

| Metric | Fold 1 | Fold 2 | Fold 3 | Combined 3-Fold | Interpretation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Runner Order (Un-clamped)** | 66.61% | 108.40% | 97.67% | **272.65%** | Cumulative strategy drag relative to initial unit base |
| **Runner Order (Clamped at 0)** | 66.61% | 100.00% | 97.67% | **100.00%** | Standard physical bankruptcy / total liquidation floor |
| **Chronological Exit (Un-clamped)** | 67.09% | 108.57% | 98.35% | **272.78%** | True calendar cashflow drag |
| **Chronological Exit (Clamped)** | 67.09% | 100.00% | 98.35% | **100.00%** | Bankruptcy reached during Fold 2 |
| **True MTM ($100k Capital Base)** | 6.78% | 10.97% | 10.02% | **N/A** | Drawdown if $100k actual cash backed the 10 streams |
| **True MTM (Normalized $10k Base)** | 67.82% | 109.73% | 100.16% | **N/A** | Mark-to-market drawdown on $10k unit capital |

#### Explanation of Strategy A's 272.65% MDD
1. **Un-Clamped Continuous Summation**:
   - The runner formula `cum_equity += pnl` did not clamp at zero.
   - When cumulative losses reached -$10,000 (Fold 2), real capital would be zero.
   - Because the algorithm continued adding negative cashflows until equity reached `-$17,264.91`, the drawdown formula `(10000 - (-17264.91)) / 10000 = 272.65%` produced a figure greater than 100%.
2. **Appropriate Interpretation**:
   - 272.65% is an **un-clamped cumulative loss ratio**, indicating that trading costs and losses consumed **$2.72 for every $1.00 of base capital**.
   - For executable trading systems, the standard risk statistic is **100.0%** (ruin/bankruptcy).

---

### 3.4. Reconciliation of Strategy C (Mean Reversion, 15m)

Strategy C also suffered consistent losses across all folds:

```
Total Trades: 3,362 | Net PnL: -$6,946.99
Gross PnL: -$2,552.37 | Fees: $3,166.15 | Slippage: $1,228.47
```

#### Drawdown Metrics for Strategy C

| Metric | Fold 1 | Fold 2 | Fold 3 | Combined 3-Fold |
| :--- | :---: | :---: | :---: | :---: |
| **Runner Order (Un-clamped)** | 33.89% | 22.65% | 13.52% | **69.55%** |
| **Chronological Exit-Time** | 33.80% | 24.40% | 13.98% | **69.74%** |
| **True MTM ($100k Base)** | 3.40% | 2.49% | 1.41% | **N/A** |
| **True MTM (Normalized $10k Base)** | 34.00% | 24.84% | 14.12% | **N/A** |

Strategy C maintained low position overlap (average 0.35 to 0.44 simultaneous positions), but friction steadily degraded capital, yielding a cumulative drawdown of **69.55%** (runner) and **69.74%** (chronological).

---

## 4. Master Fold Reconciliation Table

Below is the complete per-fold equity reconciliation table across all three strategies:

| Strategy | Fold | Trades | Net PnL ($) | Max Sim. Pos. | Avg Sim. Pos. | Peak Notional ($) | Runner MDD (%) | Chrono Exit MDD (%) | Clamped MDD (%) | MTM MDD ($10k Base) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Strat A** | 1 | 4,386 | -$6,661.30 | 10 / 10 | 1.70 | $9,910.37 | 66.61% | 67.09% | 66.61% | 67.82% |
| **Strat A** | 2 | 5,685 | -$10,836.56 | 10 / 10 | 2.03 | $8,943.38 | 108.40% | 108.57% | 100.00% | 109.73% |
| **Strat A** | 3 | 6,863 | -$9,767.04 | 10 / 10 | 2.52 | $9,813.99 | 97.67% | 98.35% | 97.67% | 100.16% |
| **Strat A** | **All** | **16,934** | **-$27,264.91** | **10 / 10** | **2.08** | **$9,910.37** | **272.65%** | **272.78%** | **100.00%** | **N/A** |
| **Strat B** | 1 | 954 | +$1,691.70 | 10 / 10 | 2.88 | $10,161.72 | 10.81% | 12.43% | 10.81% | 15.45% |
| **Strat B** | 2 | 859 | +$372.55 | 10 / 10 | 2.82 | $10,080.98 | 6.01% | 12.63% | 6.01% | 14.39% |
| **Strat B** | 3 | 1,038 | -$1,149.95 | 10 / 10 | 3.81 | $10,021.85 | 14.40% | 18.74% | 14.40% | 20.72% |
| **Strat B** | **All** | **2,851** | **+$914.31** | **10 / 10** | **3.17** | **$10,161.72** | **14.89%** | **17.15%** | **14.89%** | **N/A** |
| **Strat C** | 1 | 1,402 | -$3,379.64 | 9 / 10 | 0.42 | $8,973.12 | 33.89% | 33.80% | 33.89% | 34.00% |
| **Strat C** | 2 | 1,155 | -$2,218.73 | 10 / 10 | 0.44 | $9,860.20 | 22.65% | 24.40% | 22.65% | 24.84% |
| **Strat C** | 3 | 805 | -$1,348.61 | 9 / 10 | 0.35 | $8,973.49 | 13.52% | 13.98% | 13.52% | 14.12% |
| **Strat C** | **All** | **3,362** | **-$6,946.99** | **10 / 10** | **0.40** | **$9,860.20** | **69.55%** | **69.74%** | **69.55%** | **N/A** |

---

## 5. Phase 4B.2 Discrepancy Register

| Issue ID | Category | Severity | Evidence & Analysis | Practical Impact | Recommended Action |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **`DISC-4B2-01`** | **Cashflow Serialization** | **HIGH** | In `walk_forward_runner.py`, trades were concatenated pair-by-pair rather than sorted chronologically. In Strategy B, chronological exit-time MDD is **`17.15%`**, whereas pair-concatenated MDD was reported as **`14.89%`**. | GATE-1 is breached under true chronology ($17.15\% > 15.0\%$). However, Strategy B already failed GATE-2, 3, 7, and 8. Global outcome `NO_QUALIFIED_STRATEGY` is unaffected. | Build a synchronized multi-pair event queue in Phase 5 that merges fills chronologically by `exit_time_ms`. |
| **`DISC-4B2-02`** | **Capital Model Representation** | **HIGH** | The simulator ran 10 isolated sub-accounts of $10,000 each ($100,000 total capital). Peak positions reached 10 pairs ($10,161 notional). Sizing reflected local sub-account cash with no shared margin contention. | The reported $10k portfolio curve is a synthetic normalization convention. If gross leverage had exceeded 1.0x or if cash had gone negative in one pair, other pairs were unaffected. | Explicitly label the current model as "10 Isolated Sub-Accounts Normalized to $10k". Implement centralized portfolio margin in Phase 5. |
| **`DISC-4B2-03`** | **Un-Clamped Drawdown** | **MEDIUM** | Strategy A reported **`272.65%`** MDD because cumulative losses (-$27,265) accumulated without a zero-floor on synthetic $10k equity. Physical margin liquidation occurs at $0.00 (100% loss). | Accurately conveys strategy drag ($2.72\times$ capital loss), but violates conventional financial risk reporting where drawdown $\le 100\%$. | Provide dual reporting in future phases: un-clamped strategy drag (272.65%) and clamped bankruptcy drawdown (100.0%). |
| **`DISC-4B2-04`** | **Fold Reset Inconsistency** | **MEDIUM** | OOS engines reset cash to $10,000 at each fold boundary, but combined MDD was computed by compounding trades continuously across all 3 folds. Fold 3 suffered an independent **`18.74%`** chronological drawdown. | Evaluating folds independently reveals that Fold 3 exceeded the 15% risk budget. The combined curve dampened this drop using Folds 1 and 2 profits. | Mandate per-fold risk budgeting in Phase 5 walk-forward gates in addition to aggregate multi-fold MDD. |

---

## 6. Qualification Gate Decisions & Baseline Status

Does Phase 4B.2 change the historical Phase 4B outcome?

**Conclusion: NO.**

1. **Gate Re-Evaluation**:
   - Even if GATE-1 for Strategy B is re-evaluated using true chronological exit time (17.15%), Strategy B's gate scorecard moves from **4 passed / 4 failed** to **3 passed / 5 failed**:
     - `GATE-1 (MDD <= 15.0%)`: **FAIL** (17.15%)
     - `GATE-2 (Expectancy >= 8.0 bps)`: **FAIL** (+3.26 bps)
     - `GATE-3 (Profit Factor >= 1.25)`: **FAIL** (1.029)
     - `GATE-4 (Trade Count >= 150)`: **PASS** (2,851 trades)
     - `GATE-5 (Per-Pair Trades >= 20)`: **PASS** (10 of 10 pairs)
     - `GATE-6 (Walk-Forward Consistency)`: **PASS** (2 of 3 folds profitable)
     - `GATE-7 (Spatial Robustness >= 7/10)`: **FAIL** (6 of 10 pairs profitable)
     - `GATE-8 (Friction Stress Tolerance)`: **FAIL** (-$1,078.63 net PnL)
2. **Outcome Invariance**:
   - Because Strategy B already failed GATE-2, GATE-3, GATE-7, and GATE-8 in Phase 4B, the global decision remains strictly **`NO_QUALIFIED_STRATEGY`**.
   - Strategy B remains the **`UNQUALIFIED_BASELINE`** (the quantitative benchmark hurdle that Phase 5 machine-learning models must outperform).
   - Strategies A and C failed all 8 gates under every definition.
   - Therefore, the frozen qualification gate outcome is completely robust against portfolio accounting adjustments.

---

## 7. Artifact Integrity Register

All manifests, datasets, and audit outputs have been cryptographically verified using SHA-256:

| Artifact / File Path | Description | SHA-256 Checksum |
| :--- | :--- | :--- |
| `data/benchmarks/phase_4b/PHASE_4B_MASTER_SUMMARY.json` | Input Master Benchmark Manifest | `10bbdd09a4e52e60360c4d0917d59aac67471477dbcd5ed2249fa9cec0c4ebeb` |
| `data/benchmarks/phase_4b/STRAT_A_BENCHMARK.json` | Input Strategy A Manifest | `0a3360f59e2198f04a5c08f739d89c46600e3b0077eb38a8253b10d0f3a2b0fa` |
| `data/benchmarks/phase_4b/STRAT_B_BENCHMARK.json` | Input Strategy B Manifest | `027b834abf9dcfee8b93d27ca70294bcb2436e63516c7d437b5333de88726bdf` |
| `data/benchmarks/phase_4b/STRAT_C_BENCHMARK.json` | Input Strategy C Manifest | `c93e46a048d0ecd4c5f82bd60c2b7d57155a6e84cb0d27929ff60ce2708edc52` |
| `data/benchmarks/phase_4b_audit/audit_summary.json` | Input Phase 4B.1 Audit Manifest | `a2d4ac5941b0dd53b04f3cbe89421903ecdfedfc32d093770dbfcf3dd468d46d` |
| `backend/strategy/risk_audit_4b2.py` | Phase 4B.2 Risk Audit Engine | `111516e87f2e18b871c530ea873db8151b723f5e5df67fa6eef2d0ca2bcae0eb` |
| `data/benchmarks/phase_4b2_audit/risk_audit_summary.json` | Phase 4B.2 Risk Audit Output Manifest | `6f36ef39898610eb92fe0bd8397fe54e6b0568db0e1478c469206e18f91f6dec` |
| `docs/PHASE_4B2_PORTFOLIO_RISK_AUDIT.md` | Phase 4B.2 Comprehensive Audit Report | *(Self-Documenting)* |

---

## 8. Final Audit Exit Status

```
================================================================================
FINAL AUDIT VERDICT: RISK_AUDIT_PASS_WITH_LIMITATIONS
================================================================================
1. Exact numerical reproduction of reported Phase 4B metrics verified from code and saved run artifacts.
2. Serialization discrepancy documented (reported pair-concat MDD: 14.89% vs chronological MDD: 17.15%).
3. Multi-pair capital allocation verified as 10 isolated sub-accounts normalized to $10k base.
4. Strategy A un-clamped MDD (272.65%) confirmed as unhedged strategy drag (100.0% clamped bankruptcy floor).
5. Historical benchmark outcome NO_QUALIFIED_STRATEGY remains 100% valid and unaltered.
6. Strategy B remains the certified UNQUALIFIED_BASELINE hurdle for Phase 5.
================================================================================
```
