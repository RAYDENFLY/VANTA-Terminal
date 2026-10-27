# VANTA Terminal — Phase 5C.2 Independent Results & Accounting Audit

**Document ID**: `VANTA-DOCS-5C2-AUDIT-REPORT`  
**Execution Timestamp**: `2026-10-27T10:00:00Z`  
**Auditor**: Antigravity Quantitative Verification & System Accounting Auditor  
**Audit Scope**: Strict independent audit of Phase 5C.1 experimental outputs, metric definitions, statistical inference, and canonical portfolio accounting  
**Reference Artifacts**:
- [`docs/PHASE_5C1_CONTROLLED_ML_EVALUATION_REPORT.md`](file:///d:/vanta-terminal/docs/PHASE_5C1_CONTROLLED_ML_EVALUATION_REPORT.md)
- [`data/experiments/phase_5c/experiment_manifest.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/experiment_manifest.json)
- [`data/experiments/phase_5c/MODEL-1-LOGIT_RESULTS.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/MODEL-1-LOGIT_RESULTS.json)
- [`data/experiments/phase_5c/MODEL-2-LGBM_RESULTS.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/MODEL-2-LGBM_RESULTS.json)
- [`data/experiments/phase_5c/MODEL-3-XGB_RESULTS.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/MODEL-3-XGB_RESULTS.json)
- [`data/experiments/phase_5c/benchmark_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/benchmark_0_trades.json)
- [`data/benchmarks/phase_4b5/STRAT_B_BENCHMARK.json`](file:///d:/vanta-terminal/data/benchmarks/phase_4b5/STRAT_B_BENCHMARK.json)

**Certified Audit Finding**: `PHASE_5C2_AUDIT_PASS`  
**Confirmed System Status**: `PHASE_5C1_NO_QUALIFIED_MODEL`  
**Quarantined Final Holdout**: Impeccably Preserved ($\text{Max Timestamp} = 1777158000000 < 1777161600000$)  

---

## 1. Executive Summary & Audit Mandate

Phase 5C.2 conducted an exhaustive, independent mathematical, statistical, and portfolio-accounting audit of the Phase 5C.1 controlled machine learning results.

In strict adherence to the audit mandate:
- **Zero models were retrained.**
- **Zero strategy backtests or simulations were rerun.**
- **Zero parameters or features were modified.**
- **The quarantined Phase 6 final holdout (`2026-04-26T00:00:00Z`) was completely unaccessed and protected.**
- **Port 8000 was untouched** (PID 24956 preserved).
- **All project artifacts remain on `D:\` with > 50 GB free disk space.**

### Summary of Audit Verdicts:
1. **Metric Reconciliation (`PASS`)**: Gross PnL minus fees and slippage reconciles exactly to net PnL (within $\$0.02$ across 25,000+ trades due to independent 2-decimal fold rounding; raw float difference $< 10^{-12}$). Fold-level net PnLs sum identically to reported totals ($0.0000$ diff). Per-pair net PnLs sum identically to reported totals ($0.0000$ to $0.0100$ diff). Total trade counts reconcile with $0$ error across all folds, pairs, and ledger dumps.
2. **Expectancy Denominator Clarification (`PASS`)**: Successfully resolved the discrepancy between the Phase 4B.5 reported baseline expectancy ($+3.31\text{ bps}$) and the Phase 5C.1 comparison table value ($+0.85\text{ bps}$). The $+3.31\text{ bps}$ value is the unweighted arithmetic mean of per-trade returns, which is the binding formula in [`backend/strategy/qualification.py`](file:///d:/vanta-terminal/backend/strategy/qualification.py). The $+0.85\text{ bps}$ value represents standardized unit-notional expectancy ($\text{Total Net PnL} / (N \times \$1,000) \times 10,000$). Under both definitions, Benchmark-0 fails GATE-2 ($< +8.0\text{ bps}$), and all three ML candidates produce negative net expectancy ($-7.13\text{ bps}$ to $-11.61\text{ bps}$).
3. **Statistical Inference Correctness (`PASS`)**: Verified that paired bootstrap samples utilize identical synchronized 24-hour daily calendar blocks across all 10 pairs simultaneously. The reported one-tailed $p$-value ($1.0000$) represents the empirical probability of the null hypothesis $P(\Delta^* \le 0)$, while the upper-tail probability $P(\Delta^* > 0)$ is $0.0000$. All 2,000 resamples showed ML underperforming Benchmark-0.
4. **Portfolio Accounting & Risk Integrity (`PASS`)**: Verified that the canonical engine enforced the $1.0\times$ gross leverage cap, $10\%$ equity sizing, deterministic margin rationing, zero rehypothecation, and continuous candle-level mark-to-market drawdown tracking.
5. **Qualification Gate Re-evaluation (`PASS`)**: Re-evaluated all 8 frozen gates against realized point estimates. All three ML models decisively failed 6 of the 8 gates (G1, G2, G3, G6, G7, G8). The certified outcome remains strictly `NO_QUALIFIED_MODEL`.

$$\mathbf{AUDIT \ OUTCOME: \ PHASE\_5C2\_AUDIT\_PASS}$$

---

## 2. Audit A — Metric Reconciliation

All calculations in this section were recomputed from the saved JSON experiment artifacts without executing new simulations.

### 2.1 Cash Reconciliation: Gross PnL vs. Fees, Slippage & Net PnL
For each candidate and Benchmark-0, the ledger identity $\text{Net PnL} = \text{Gross PnL} - \text{Total Fees} - \text{Slippage Cost} + \text{Funding}$ was verified:

| Candidate ID | Reported Gross PnL (\$) | Reported Fees (\$) | Reported Slippage (\$) | Calculated Net PnL (\$) | Reported Net PnL (\$) | Discrepancy (\$) | Verification Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BENCHMARK-0** | +$4,370.79 | $2,949.30 | $1,178.06 | +$243.43 | +$243.43 | **$0.0000** | **RECONCILED** |
| **MODEL-1-LOGIT** | +$1,969.50 | $15,115.60 | $5,539.35 | -$18,685.45 | -$18,685.47 | **$0.0200** | **RECONCILED** (Fold Rounding) |
| **MODEL-2-LGBM** | +$2,230.28 | $15,134.03 | $5,549.17 | -$18,452.92 | -$18,452.94 | **$0.0200** | **RECONCILED** (Fold Rounding) |
| **MODEL-3-XGB** | +$1,650.31 | $15,064.50 | $5,522.95 | -$18,937.14 | -$18,937.14 | **$0.0000** | **RECONCILED** |

*Note on $0.02 Discrepancy*: Each candidate's total net PnL is the exact sum of its three fold-level net PnLs, each rounded to two decimal places. Recomputing directly from the raw unrounded sum of 25,000+ trade ledger records yields exact equality down to floating-point precision ($< 10^{-12}$).

---

### 2.2 Walk-Forward Fold Summation Reconciliation

Summing fold-level metrics directly from the nested `"folds"` array in each candidate's JSON artifact:

| Candidate ID | Metric | Fold 1 | Fold 2 | Fold 3 | Sum of Folds | Reported Total | Discrepancy |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **MODEL-1-LOGIT** | Net PnL (\$) | -$6,442.19 | -$6,946.13 | -$5,297.15 | -$18,685.47 | -$18,685.47 | **$0.0000** |
| | Gross PnL (\$) | +$172.25 | +$324.75 | +$1,472.50 | +$1,969.50 | +$1,969.50 | **$0.0000** |
| | Fees Paid (\$) | $4,844.31 | $5,319.50 | $4,951.79 | $15,115.60 | $15,115.60 | **$0.0000** |
| | Slippage (\$) | $1,770.12 | $1,951.37 | $1,817.86 | $5,539.35 | $5,539.35 | **$0.0000** |
| | Trades Count | 8,838 | 9,248 | 6,990 | 25,076 | 25,076 | **0** |
| **MODEL-2-LGBM** | Net PnL (\$) | -$5,285.70 | -$6,461.01 | -$6,706.23 | -$18,452.94 | -$18,452.94 | **$0.0000** |
| | Gross PnL (\$) | +$2,266.55 | +$968.80 | -$1,005.07 | +$2,230.28 | +$2,230.28 | **$0.0000** |
| | Fees Paid (\$) | $5,532.81 | $5,436.67 | $4,164.55 | $15,134.03 | $15,134.03 | **$0.0000** |
| | Slippage (\$) | $2,019.44 | $1,993.13 | $1,536.60 | $5,549.17 | $5,549.17 | **$0.0000** |
| | Trades Count | 9,080 | 9,256 | 7,560 | 25,896 | 25,896 | **0** |
| **MODEL-3-XGB** | Net PnL (\$) | -$5,738.33 | -$6,622.63 | -$6,576.18 | -$18,937.14 | -$18,937.14 | **$0.0000** |
| | Gross PnL (\$) | +$1,770.59 | +$769.77 | -$890.05 | +$1,650.31 | +$1,650.31 | **$0.0000** |
| | Fees Paid (\$) | $5,502.21 | $5,408.11 | $4,154.18 | $15,064.50 | $15,064.50 | **$0.0000** |
| | Slippage (\$) | $2,006.71 | $1,984.29 | $1,531.95 | $5,522.95 | $5,522.95 | **$0.0000** |
| | Trades Count | 8,961 | 9,146 | 7,532 | 25,639 | 25,639 | **0** |

---

### 2.3 Cross-Sectional Per-Pair Reconciliation

Summing per-pair metrics across all 10 liquid perpetual pairs in each candidate's artifact:

| Candidate ID | Sum of Per-Pair Net PnL (\$) | Reported Portfolio Total Net PnL (\$) | Delta (\$) | Sum of Per-Pair Trades | Reported Portfolio Trades | Delta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **MODEL-1-LOGIT** | -$18,685.46 | -$18,685.47 | **$0.0100** | 25,076 | 25,076 | **0** |
| **MODEL-2-LGBM** | -$18,452.94 | -$18,452.94 | **$0.0000** | 25,896 | 25,896 | **0** |
| **MODEL-3-XGB** | -$18,937.14 | -$18,937.14 | **$0.0000** | 25,639 | 25,639 | **0** |

All trade counts and net dollar PnLs cross-sectionally reconcile with absolute consistency.

---

### 2.4 Mathematical Denominators and Expectancy Reconciliation

A key mandate of this audit is reconciling the baseline expectancy previously reported as `+3.31 bps` (Phase 4B.5) with the table value `+0.85 bps` (Phase 5C.1).

Recomputing all candidate expectancies under each mathematical denominator:

| Candidate ID | Definition 1: Unweighted Mean Return $\frac{1}{N} \sum \frac{\text{NetPnL}_i}{\text{Notional}_i}$ | Definition 2: Notional-Weighted Return $\frac{\sum \text{NetPnL}_i}{\sum \text{Notional}_i}$ | Definition 3: Unit Notional Expectancy $\frac{\sum \text{NetPnL}_i}{N \times \$1,000}$ |
| :--- | :---: | :---: | :---: |
| **BENCHMARK-0** | **+3.31 bps** | **+0.83 bps** | **+0.85 bps** |
| **MODEL-1-LOGIT** | **-11.61 bps** | **-10.98 bps** | **-7.45 bps** |
| **MODEL-2-LGBM** | **-10.99 bps** | **-10.84 bps** | **-7.13 bps** |
| **MODEL-3-XGB** | **-11.53 bps** | **-11.18 bps** | **-7.39 bps** |

#### Protocol Attribution & Analysis:
1. **Source of `+3.31 bps`**:
   [`backend/strategy/qualification.py`](file:///d:/vanta-terminal/backend/strategy/qualification.py) lines 26–33 defines GATE-2 as:
   ```python
   net_returns = [pnl / notional for notional, pnl in zip(trade_notionals, net_pnls) if notional > 0]
   mean_exp, sem_exp, ci = calculate_net_expectancy_ci(net_returns)
   mean_bps = mean_exp * 10000.0
   ```
   For `BENCHMARK-0`, $\frac{1}{2,851} \sum_{i=1}^{2,851} \frac{\text{NetPnL}_i}{\text{Notional}_i} = 0.0003311 \implies \mathbf{+3.31\text{ bps}}$.
   This is the **formal, binding definition of GATE-2** under the frozen Phase 4B/5A protocol.
2. **Source of `+0.85 bps`**:
   In [`backend/ml/evaluation_driver.py`](file:///d:/vanta-terminal/backend/ml/evaluation_driver.py), expectancy was computed as:
   $$\text{Expectancy}_{\text{unit}} = \frac{\sum \text{NetPnL}}{N \times \$1,000} \times 10,000 = \frac{\$243.43}{2,851 \times \$1,000} \times 10,000 = \mathbf{+0.85\text{ bps}}$$
   This standardized unit formula divides aggregate dollar PnL by the nominal initial position size ($10\%$ of initial $\$10,000$ cash).
3. **Source of `+0.83 bps`**:
   Dividing total realized net PnL by exact cumulative entry notional: $\frac{\$243.43}{\$2,948,541.47} \times 10,000 = \mathbf{+0.83\text{ bps}}$.

#### Audit Finding on Expectancy:
- **Binding Status**: Under the codified rule in [`backend/strategy/qualification.py`](file:///d:/vanta-terminal/backend/strategy/qualification.py), **Definition 1 ($+3.31\text{ bps}$) is the binding GATE-2 value**.
- **Equivalence of Outcome**: Regardless of whether Definition 1, 2, or 3 is used:
  - Benchmark-0 fails GATE-2 ($+3.31\text{ bps}$, $+0.83\text{ bps}$, $+0.85\text{ bps}$ are all far below the $+8.0\text{ bps}$ hurdle).
  - All ML candidates fail GATE-2 catastrophically (all expectancies are strictly negative between $-7.13\text{ bps}$ and $-11.61\text{ bps}$).
  - No historical baseline results were silently altered or corrupted.

---

## 3. Audit B — Bootstrap Inference

### 3.1 Verification of Paired Synchronized Time Blocks
In [`backend/ml/inference.py`](file:///d:/vanta-terminal/backend/ml/inference.py):
- The atomic resampling unit is a **synchronous 24-hour multi-pair calendar day** ($T = \lceil (\text{end\_ms} - \text{start\_ms}) / 86,400,000 \rceil$).
- For each replicate $b \in \{1, \dots, 2,000\}$, a single index vector `resampled_indices` of length $T$ is drawn via the Stationary Block Bootstrap algorithm with geometric continuation probability $1 - p = 0.80$ ($\mathbb{E}[L] = 5\text{ days}$).
- The code computes:
  ```python
  sample_ml = mat_ml[resampled_indices]
  sample_bm = mat_bm[resampled_indices]
  ```
- **Audit Verification**: Confirmed that both models are evaluated on the exact same market days in every bootstrap replicate. Paired time synchronization is 100% verified.

---

### 3.2 Tail Convention & Hypothesis Testing Formulation
The empirical p-value in [`backend/ml/inference.py`](file:///d:/vanta-terminal/backend/ml/inference.py) line 138 is calculated as:
```python
p_value_pnl = float(np.mean(delta_pnl_reps <= 0.0))
```

#### Mathematical Interpretation:
- Let the null hypothesis be $H_0: \Delta_{\text{PnL}} \le 0$ (ML candidate does not outperform Benchmark-0).
- The alternative hypothesis is $H_1: \Delta_{\text{PnL}} > 0$ (ML candidate statistically outperforms Benchmark-0).
- In the saved bootstrap results:
  - For `MODEL-1-LOGIT`: `delta_pnl_reps <= 0.0` occurred in **2,000 of 2,000 replicates** $\implies p = 1.0000$.
  - For `MODEL-2-LGBM`: `delta_pnl_reps <= 0.0` occurred in **2,000 of 2,000 replicates** $\implies p = 1.0000$.
  - For `MODEL-3-XGB`: `delta_pnl_reps <= 0.0` occurred in **2,000 of 2,000 replicates** $\implies p = 1.0000$.
- **Tail Direction**:
  - The calculated statistic represents the **empirical support for the null hypothesis**: $P(\Delta^* \le 0) = 1.0000$.
  - If defined as the upper-tail probability against the null: $P(\Delta^* > 0) = \frac{0}{2,000} = \mathbf{0.0000}$.
  - Under either convention, the hypothesis that ML outperforms Benchmark-0 is rejected with overwhelming certainty.
- **Percentile Confidence Bounds**:
  In [`docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md`](file:///d:/vanta-terminal/docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md) Section 2.5, qualification requires the lower bound of the 95% bootstrap confidence interval to be strictly positive: $\Delta^*_{0.025} > 0$.
  The realized lower bounds are:
  - `MODEL-1-LOGIT`: **-$28,464.33**
  - `MODEL-2-LGBM`: **-$27,443.51**
  - `MODEL-3-XGB`: **-$28,069.07**
  Moreover, the *upper bounds* ($\Delta^*_{0.975}$) are also strictly negative:
  - `MODEL-1-LOGIT`: **-$9,472.31**
  - `MODEL-2-LGBM`: **-$10,712.79**
  - `MODEL-3-XGB`: **-$11,062.11**
  This proves that **all three ML models significantly underperformed Benchmark-0 at the $\alpha = 0.05$ significance level**.

---

### 3.3 Zero-Trade Replicates and Tie Handling
Inspection of [`backend/ml/inference.py`](file:///d:/vanta-terminal/backend/ml/inference.py) lines 107–126 confirms:
- **Profit Factor**: When a resampled replicate contains zero losses (`loss == 0`), if `wins > 0`, PF is clamped to $10.0$; if `wins == 0` (no trades), PF is set to $1.0$.
- **Expectancy**: When a resampled replicate contains zero trades (`n_tr == 0`), expectancy is set to $0.0\text{ bps}$.
- **Ties**: Exact ties ($\Delta = 0$) are conservatively evaluated as non-outperformance by the condition $\Delta \le 0$.

Audit B Status: **PASS**.

---

## 4. Audit C — Portfolio Risk & Bankruptcy Integrity

### 4.1 Leverage Cap & Equity Sizing
Inspection of [`backend/backtest/portfolio_engine.py`](file:///d:/vanta-terminal/backend/backtest/portfolio_engine.py):
1. **$1.0\times$ Leverage Cap**:
   `get_free_collateral` computes $\text{Borrowable} = \text{Equity} \times \text{MaxLeverage} - \text{Reserved Margin}$. With $\text{MaxLeverage} = 1.0$, total position notionals across all open positions cannot exceed instantaneous portfolio equity.
2. **$10\%$ Target Equity Sizing**:
   `calculate_order_quantity` computes $\text{Target Notional} = \text{Equity} \times 0.10$. Available capital is bounded by $\min(\text{Target Notional}, \text{Free Collateral})$.
3. **Deterministic Capital Rationing**:
   If simultaneous signals occur at the same timestamp, signals are ordered deterministically by descending bar volume (`MultiStreamEventQueue.sort_signals_deterministically`). Any signal exceeding free collateral is rejected as `INSUFFICIENT_COLLATERAL`.

---

### 4.2 Mark-to-Market Accounting & Bankruptcy Clamping
1. **Candle-Level Mark-to-Market Tracking**:
   At the close of every 1-hour bar, `get_portfolio_equity` computes $\text{Cash} + \sum \text{Unrealized PnL}$. Instantaneous drawdown from the cumulative high-watermark is evaluated and logged.
2. **Bankruptcy Floor**:
   If portfolio equity drops to $\le \$0.00$, `is_bankrupt` is set to `True`, all subsequent orders are rejected as `BANKRUPTCY_HALT`, and drawdown is clamped to $100.0\%$.
3. **Boundary Flattening Costs**:
   At the conclusion of each fold, any positions remaining open are force-closed at the final bar close price with full taker fees deducted (`ExitReason.BOUNDARY_FLAT`). Realized cash reflects all terminal closing costs.

---

### 4.3 Chained Equity Curve Transition Semantics
The chained equity curve is constructed via [`backend/ml/chained_equity.py`](file:///d:/vanta-terminal/backend/ml/chained_equity.py):
- Each fold's starting equity is normalized to the terminal equity multiplier of the preceding fold:
  $$K_f = \prod_{k=1}^{f-1} \left(1 + \frac{\text{NetPnL}_k}{\$10,000}\right)$$
- Continuous compounding is preserved across fold boundaries without artificial capital injections.
- Recomputed Chained MTM MDD matches reported values down to four decimal places:
  - `MODEL-1-LOGIT`: Recomputed **94.9210%** vs. Reported **94.9210%**
  - `MODEL-2-LGBM`: Recomputed **94.6308%** vs. Reported **94.6308%**
  - `MODEL-3-XGB`: Recomputed **95.0996%** vs. Reported **95.0996%**

Audit C Status: **PASS**.

---

## 5. Audit D — Frozen Qualification Gates & Final Status

Every candidate was re-checked against all 8 frozen qualification gates using realized point estimates:

| Gate ID | Hurdle Requirement | BENCHMARK-0 | MODEL-1-LOGIT | MODEL-2-LGBM | MODEL-3-XGB | Audit Result |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **GATE-1** | Per-Fold MTM MDD $\le 15.0\%$ & Chained MDD $\le 15.0\%$ | **FAIL** (20.67%) | **FAIL** (94.92%) | **FAIL** (94.63%) | **FAIL** (95.10%) | **VERIFIED** |
| **GATE-2** | Net Expectancy $\ge +8.0\text{ bps}$ | **FAIL** (+3.31 bps) | **FAIL** (-7.45 bps) | **FAIL** (-7.13 bps) | **FAIL** (-7.39 bps) | **VERIFIED** |
| **GATE-3** | Profit Factor $\ge 1.25$ | **FAIL** (1.007) | **FAIL** (0.830) | **FAIL** (0.840) | **FAIL** (0.834) | **VERIFIED** |
| **GATE-4** | Aggregate OOS Trades $\ge 150$ | **PASS** (2,851) | **PASS** (25,076) | **PASS** (25,896) | **PASS** (25,639) | **VERIFIED** |
| **GATE-5** | Trades per pair $\ge 20$ for all 10 pairs | **PASS** (Min 215) | **PASS** (Min 2,262) | **PASS** (Min 1,839) | **PASS** (Min 1,880) | **VERIFIED** |
| **GATE-6** | Walk-Forward Consistency: $\ge 2/3$ profitable folds | **PASS** (2/3) | **FAIL** (0/3) | **FAIL** (0/3) | **FAIL** (0/3) | **VERIFIED** |
| **GATE-7** | Spatial Robustness: $\ge 7/10$ profitable pairs | **FAIL** (6/10) | **FAIL** (0/10) | **FAIL** (0/10) | **FAIL** (0/10) | **VERIFIED** |
| **GATE-8** | Stress Cost Model: Stress Net PnL $> \$0$ & PF $> 1.0$ | **FAIL** (-$2,222) | **FAIL** (-$23,965) | **FAIL** (-$24,102) | **FAIL** (-$24,295) | **VERIFIED** |
| **VERDICT** | **Simultaneous Pass Required Across All 8 Gates** | **UNQUALIFIED** | **UNQUALIFIED** | **UNQUALIFIED** | **UNQUALIFIED** | **VERIFIED** |

Audit D Status: **PASS**.

---

## 6. Cryptographic Manifest & SHA-256 Hashes

The SHA-256 hashes of all relevant source modules, test scripts, and Phase 5C.1 result artifacts were computed directly from disk:

| File Path | SHA-256 Checksum | Purpose / Description |
| :--- | :--- | :--- |
| `backend/ml/walk_forward.py` | `b3b91a51ebe333851181b2f3ca33ad09dd1209e03b9d9628ab2d8b29f95ed3b0` | Walk-forward schedule & partition bounds |
| `backend/ml/dataset_builder.py` | `8b068bfdbf7d5df0e75db442a983ce84a0e33523f14095d6530c73e9592ebb09` | Feature matrix & label generator |
| `backend/ml/models.py` | `1941d9001593e155671d154c02e163bab853fefe8fabe68698e230b6be279023` | ML model wrappers & probability calibration |
| `backend/ml/ml_strategy.py` | `53acf3679749878cf47775a1c6840c0437cfea11dd0d0884dee3df017ed2382f` | Signal-to-trade portfolio adapter |
| `backend/ml/inference.py` | `4f6023170dc0ad63524e8b338cae408c456df0371805bd5fc2285e66e924b74a` | Synchronized stationary block bootstrap |
| `backend/ml/evaluation_driver.py` | `4ecb3dd3e5b45dffdff9d9250a9ab955f305c05c124d1f06c30de82bc588dac7` | Master Phase 5C.1 evaluation orchestrator |
| `data/experiments/phase_5c/experiment_manifest.json` | `56b622423ae1ddd51bf120fa3b0bcea93ff0fec9e26ac20a2bb8ee1f07d76daf` | Phase 5C.1 experiment manifest |
| `data/experiments/phase_5c/MODEL-1-LOGIT_RESULTS.json` | `412c6bbe9fe26966dfe6b07e438f88b5774282d74595c1d3989743413c6a0b4d` | LOGIT full results & trade ledger |
| `data/experiments/phase_5c/MODEL-2-LGBM_RESULTS.json` | `ba650546a4d901cc666f1972ab03e71edef4aa3eae88ca27fd3d4ab873036d54` | LGBM full results & trade ledger |
| `data/experiments/phase_5c/MODEL-3-XGB_RESULTS.json` | `fb68f9c3575125f7e684ccf82a1910214c816b25e0fea81e6ad46ba8508b2060` | XGB full results & trade ledger |
| `data/experiments/phase_5c/benchmark_0_trades.json` | `ba8b1c4366b59d57a941549444aa95bce135ee7d6bb82f5b4e727508ffbdf975` | Replicated Phase 4B.5 Strategy B trades |
| `docs/PHASE_5C1_CONTROLLED_ML_EVALUATION_REPORT.md` | `f627fa75d5f652f5ec4df7ba4e73c2e72daebe881ee24be528dda1bc3fdcb4f8` | Certified Phase 5C.1 evaluation report |

---

## 7. Certified Audit Conclusion

1. **Independent Verification**: All arithmetic sums, fold transitions, spatial breakdowns, and statistical intervals reported in Phase 5C.1 are verified as correct, reproducible, and mathematically coherent.
2. **Definitive Baseline Superiority**: Even though `Benchmark-0` (Strategy B Donchian Breakout 1H) remains an `UNQUALIFIED_BASELINE`, it conclusively outperformed all three supervised machine learning models after realistic friction, capital constraints, and mark-to-market risk.
3. **Institutional Integrity**: The system correctly rejects all three ML candidates. No candidate is promoted.

$$\mathbf{CERTIFIED \ AUDIT \ STATUS: \ PHASE\_5C2\_AUDIT\_PASS}$$
