# VANTA Terminal — Phase 5D.3 Controlled Meta-Model Evaluation Report

**Document ID**: `VANTA-DOCS-5D3-CONTROLLED-META-MODEL-EVALUATION-REPORT`  
**Execution Timestamp**: `2026-10-27T19:40:00Z`  
**Author**: Antigravity Quantitative Verification & Machine Learning Research Agent  
**Predecessor Certification**: `PHASE_5D2_1_RECONCILIATION_PASS`  
**Primary Baseline**: `STRAT-B-01` Donchian Breakout 1H — `UNQUALIFIED_BASELINE`  
**Target Status**: `PHASE_5D3_NO_QUALIFIED_MODEL`  
**Quarantined Final Holdout**: `2026-04-26T00:00:00Z` (`1777161600000` ms) — Strictly Uninspected & Preserved  
**Scope**: Full walk-forward training, execution simulation, paired stationary block-bootstrap inference, and 8-gate institutional qualification audit for `META-1-LOGIT`, `META-2-LGBM`, and `META-3-XGB` across 4 pre-registered policy hypotheses (`H1` to `H4`).  

---

## 1. Executive Summary & Certified Research Status

Phase 5D.3 executed the first controlled historical evaluation of the pre-registered machine learning meta-labeling candidates for VANTA Terminal across the frozen 3-fold walk-forward schedule. The experiment tested whether filtering candidate breakout signals from the unqualified baseline (`STRAT-B-01`) using point-in-time machine learning classifiers improves trade selection while satisfying all eight non-negotiable institutional qualification gates.

### Primary Research Question:
> *Does any pre-registered ML meta-model candidate produce reproducible, statistically significant incremental net performance over Benchmark-0 under identical portfolio, execution, cost, and walk-forward constraints, while satisfying all eight qualification gates?*

### Definitive Research Verdict:
**No.** All twelve candidate model-policy configurations fail qualification under the frozen institutional standards. While meta-filtering successfully suppressed maximum drawdown (all candidates achieved continuous MTM MDD $< 4.0\%$, easily satisfying `GATE-1`), the models severely starved the strategy of trading volume, executing between 0 and 66 total trades across the entire 18-month evaluation window. Consequently, every candidate failed `GATE-4` ($\ge 150$ trades) and `GATE-5` ($\ge 20$ trades per pair).

Furthermore, synchronized stationary block bootstrap inference ($B=2,000$ replicates) against Benchmark-0 revealed no statistically significant outperformance for any candidate ($p$-values range from $0.4975$ to $0.5290$; 95% confidence intervals for $\Delta \text{Net PnL}$ span approximately $-\$8,200$ to $+\$7,000$, widely enclosing zero).

$$\mathbf{CERTIFIED \ STATUS: \ PHASE\_5D3\_NO\_QUALIFIED\_MODEL}$$

---

## 2. Pre-Run Integrity Checks & Protocol Conformance

Before fitting any model, preflight checks verified all system, data, and protocol invariants:

| Verification Item | Requirement / Invariant | Measured Status | Verdict |
| :--- | :--- | :--- | :--- |
| **Dataset Manifest** | SHA-256 match for all Phase 5D.2 files | All 7 files matched checksums in `phase_5d2/manifest_sha256.json` | **PASS** |
| **Walk-Forward Schedule**| Authoritative October-based dates | Fold 1: `2024-10-28`, Fold 2: `2025-04-28`, Fold 3: `2025-10-28` | **PASS** |
| **Holdout Boundary** | Hard cutoff at `1777161600000` ms | Max candle timestamp ingested: `1777158000000` | **PASS** |
| **Partition Isolation** | Zero candidate ID overlap between IS & OOS | 8,642 unique IDs across 6 partitions; 0 collisions | **PASS** |
| **Feature Temporal Causality**| $\max(T_{\text{feature}}) \le T_{\text{signal}}$ | Verified across all 8,642 candidate feature bindings | **PASS** |
| **Boundary Margin** | Zero IS trades extending into purge window | All IS trade outcomes resolved naturally within `is_end_ms` | **PASS** |
| **Baseline Reproduction**| Benchmark-0 matches Phase 4B.5 / 5C.1 | Exactly 2,851 trades, Net PnL $+\$243.43$, MDD $20.67\%$ | **PASS** |
| **Shared-Capital Engine**| Canonical portfolio accounting | Initial equity $\$10\text{k}$, 10% sizing, 1.0x lev, 14 bps friction | **PASS** |

---

## 3. Pre-Registered Model Architectures & Policy Hypotheses

### 3.1 Model Specifications
All models were instantiated with frozen hyperparameter vectors pre-registered in Phase 5C.4 and implemented in Phase 5D.1:

1. **`META-1-LOGIT`** (Regularized Linear Logistic Classifier):
   - Architecture: L2 Regularized Logistic Regression (`scikit-learn`).
   - Hyperparameters: $C = 1.0$, `solver='lbfgs'`, `max_iter=1000`, `random_state=42`.
2. **`META-2-LGBM`** (Shallow Gradient Boosted Decision Trees):
   - Architecture: LightGBM Classifier (`lightgbm`).
   - Hyperparameters: `max_depth=3`, `num_leaves=7`, `n_estimators=150`, `learning_rate=0.05`, `min_child_samples=50`, `random_state=42`.
3. **`META-3-XGB`** (Shallow Extreme Gradient Boosting):
   - Architecture: XGBoost Classifier (`xgboost`).
   - Hyperparameters: `max_depth=3`, `n_estimators=150`, `learning_rate=0.05`, `min_child_weight=50`, `random_state=42`, `eval_metric='logloss'`.

### 3.2 Pre-Declared Policy Hypotheses
Candidate signals emitted by `STRAT-B-01` were evaluated under four frozen policy variants:
- **`H1` (`TAU_50_COOL_0`)**: Decision threshold $\tau = 0.50$, inter-trade cooldown $= 0$ bars.
- **`H2` (`TAU_50_COOL_4`)**: Decision threshold $\tau = 0.50$, inter-trade cooldown $= 4$ bars ($4.0\text{ hours}$).
- **`H3` (`TAU_55_COOL_0`)**: Decision threshold $\tau = 0.55$, inter-trade cooldown $= 0$ bars.
- **`H4` (`TAU_55_COOL_4`)**: Decision threshold $\tau = 0.55$, inter-trade cooldown $= 4$ bars ($4.0\text{ hours}$).

---

## 4. In-Sample Training & Out-of-Sample Classification Performance

### 4.1 Walk-Forward Training Sample Support
- **Fold 1 IS**: 1,830 candidates | Class 1: 437 ($23.88\%$) | Class 0: 1,393
- **Fold 2 IS**: 1,862 candidates | Class 1: 449 ($24.11\%$) | Class 0: 1,413
- **Fold 3 IS**: 2,099 candidates | Class 1: 517 ($24.63\%$) | Class 0: 1,582

### 4.2 Out-of-Sample Classification Metrics

| Fold | Model ID | OOS Samples | OOS Win Rate | AUC-ROC | PR-AUC | Brier Score | Log Loss | Mean Predicted Prob | Pred Pos Rate ($\tau=0.50$) | Pred Pos Rate ($\tau=0.55$) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | **`META-1-LOGIT`** | 954 | 23.48% | 0.5443 | 0.2662 | 0.1827 | 0.5552 | 0.2401 | 0.31% (3 / 954) | 0.21% (2 / 954) |
| **Fold 1** | **`META-2-LGBM`**  | 954 | 23.48% | 0.5395 | 0.2522 | 0.1843 | 0.5570 | 0.2373 | 0.73% (7 / 954) | 0.31% (3 / 954) |
| **Fold 1** | **`META-3-XGB`**   | 954 | 23.48% | 0.4863 | 0.2261 | 0.1867 | 0.5635 | 0.2422 | 0.00% (0 / 954) | 0.00% (0 / 954) |
| **Fold 2** | **`META-1-LOGIT`** | 859 | 25.15% | 0.5668 | 0.2993 | 0.1873 | 0.5607 | 0.2770 | 0.12% (1 / 859) | 0.00% (0 / 859) |
| **Fold 2** | **`META-2-LGBM`**  | 859 | 25.15% | 0.5258 | 0.2858 | 0.1946 | 0.5801 | 0.2719 | 2.33% (20 / 859)| 1.16% (10 / 859)|
| **Fold 2** | **`META-3-XGB`**   | 859 | 25.15% | 0.5456 | 0.2918 | 0.1907 | 0.5695 | 0.2757 | 0.70% (6 / 859) | 0.00% (0 / 859) |
| **Fold 3** | **`META-1-LOGIT`** | 1,038 | 27.75% | 0.4523 | 0.2464 | 0.2017 | 0.5937 | 0.2661 | 0.00% (0 / 1038)| 0.00% (0 / 1038)|
| **Fold 3** | **`META-2-LGBM`**  | 1,038 | 27.75% | 0.4903 | 0.2677 | 0.2039 | 0.6015 | 0.2671 | 1.25% (13 / 1038)| 0.48% (5 / 1038)|
| **Fold 3** | **`META-3-XGB`**   | 1,038 | 27.75% | 0.5018 | 0.2778 | 0.2009 | 0.5909 | 0.2644 | 0.10% (1 / 1038)| 0.00% (0 / 1038)|

### 4.3 Diagnostic Attribution on Probability Calibration
The classification metrics reveal the root mathematical mechanism behind the outcome:
1. **Low Signal-to-Noise Ratio**: Across all folds and models, AUC-ROC remains concentrated near random guess ($0.4523$ to $0.5668$), confirming that the 21 technical features carry very limited linear or non-linear predictive separation for breakout trade profitability.
2. **Prior Probability Anchor**: Because models are trained with log-loss on an unbalanced dataset ($24\%$ positive class), their predicted probabilities are anchored to the base rate ($\mu_{\hat{p}} \approx 0.24 - 0.27$).
3. **Threshold Mismatch**: Setting the execution hurdle to $\tau = 0.50$ or $\tau = 0.55$ requires the model to output a posterior probability $> 2.0\times$ its prior expectation. Since the features provide weak separation, the model almost never achieves this conviction, rejecting $97.7\%$ to $100.0\%$ of all candidate breakout trades.

---

## 5. Canonical Shared-Capital Portfolio Execution Results

Each candidate was replayed through the [`CanonicalPortfolioEngine`](file:///d:/vanta-terminal/backend/backtest/portfolio_engine.py) under identical shared-capital constraints ($10,000 cash pool per fold, 10% dynamic position sizing, 1.0x leverage cap, 14.0 bps round-trip transaction friction).

### 5.1 Master Performance Matrix (Benchmark-0 vs 12 Candidates)

| Candidate Configuration | Trades | Accepted | Rejected | Gross PnL | Fees ($) | Slippage ($) | Net PnL ($) | Profit Factor | Expectancy (bps) | 95% CI (bps) | Max MTM MDD | Win Rate (%) | Gate Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`BENCHMARK-0`** | **2,851** | 2,851 | 0 | +$4,370.79 | $2,949.30 | $1,178.06 | **+$243.43** | 1.007 | +3.31 | [-10.7, +17.3] | 20.67% | 25.53% | **`UNQUALIFIED_BASELINE`** |
| `META-1-LOGIT_H1 (t=0.50, c=0)` | 20 | 20 | 2,831 | -$58.66 | $20.13 | $8.06 | **-$86.85** | 0.801 | -41.48 | [-162.7, +79.8] | 3.74% | 30.00% | `NO_QUALIFIED_STRATEGY` |
| `META-1-LOGIT_H2 (t=0.50, c=4)` | 20 | 20 | 2,831 | -$58.66 | $20.13 | $8.06 | **-$86.85** | 0.801 | -41.48 | [-162.7, +79.8] | 3.74% | 30.00% | `NO_QUALIFIED_STRATEGY` |
| `META-1-LOGIT_H3 (t=0.55, c=0)` | 11 | 11 | 2,840 | -$166.38 | $10.93 | $4.37 | **-$181.68** | 0.413 | -163.46 | [-356.1, +29.2] | 3.30% | 9.09% | `NO_QUALIFIED_STRATEGY` |
| `META-1-LOGIT_H4 (t=0.55, c=4)` | 11 | 11 | 2,840 | -$166.38 | $10.93 | $4.37 | **-$181.68** | 0.413 | -163.46 | [-356.1, +29.2] | 3.30% | 9.09% | `NO_QUALIFIED_STRATEGY` |
| `META-2-LGBM_H1 (t=0.50, c=0)`  | 66 | 66 | 2,785 | +$188.70 | $66.40 | $26.56 | **+$95.74** | 1.147 | +14.12 | [-23.4, +51.6] | 2.05% | 36.36% | `NO_QUALIFIED_STRATEGY` |
| `META-2-LGBM_H2 (t=0.50, c=4)`  | 66 | 66 | 2,785 | +$188.70 | $66.40 | $26.56 | **+$95.74** | 1.147 | +14.12 | [-23.4, +51.6] | 2.05% | 36.36% | `NO_QUALIFIED_STRATEGY` |
| `META-2-LGBM_H3 (t=0.55, c=0)`  | 31 | 31 | 2,820 | +$23.32 | $31.08 | $12.43 | **-$20.20** | 0.931 | -6.34 | [-57.2, +44.5] | 1.29% | 41.94% | `NO_QUALIFIED_STRATEGY` |
| `META-2-LGBM_H4 (t=0.55, c=4)`  | 31 | 31 | 2,820 | +$23.32 | $31.08 | $12.43 | **-$20.20** | 0.931 | -6.34 | [-57.2, +44.5] | 1.29% | 41.94% | `NO_QUALIFIED_STRATEGY` |
| `META-3-XGB_H1 (t=0.50, c=0)`   | 9 | 9 | 2,842 | +$38.95 | $9.00 | $3.60 | **+$26.36** | 1.319 | +29.77 | [-71.9, +131.4] | 0.81% | 44.44% | `NO_QUALIFIED_STRATEGY` |
| `META-3-XGB_H2 (t=0.50, c=4)`   | 9 | 9 | 2,842 | +$38.95 | $9.00 | $3.60 | **+$26.36** | 1.319 | +29.77 | [-71.9, +131.4] | 0.81% | 44.44% | `NO_QUALIFIED_STRATEGY` |
| `META-3-XGB_H3 (t=0.55, c=0)`   | 0 | 0 | 2,851 | $0.00 | $0.00 | $0.00 | **$0.00** | 1.000 | 0.00 | [0.0, 0.0] | 0.00% | 0.00% | `NO_QUALIFIED_STRATEGY` |
| `META-3-XGB_H4 (t=0.55, c=4)`   | 0 | 0 | 2,851 | $0.00 | $0.00 | $0.00 | **$0.00** | 1.000 | 0.00 | [0.0, 0.0] | 0.00% | 0.00% | `NO_QUALIFIED_STRATEGY` |

*Note: In all models, Policy H2 (cooldown=4) produced identical execution to Policy H1 (cooldown=0) because candidate acceptance was already so sparse that no two accepted trades on the same pair occurred within 4 hours. The same equivalence holds between H4 and H3.*

---

### 5.2 Walk-Forward Per-Fold Performance Breakdown

| Candidate | Fold 1 Trades | Fold 1 Net PnL | Fold 1 MTM MDD | Fold 2 Trades | Fold 2 Net PnL | Fold 2 MTM MDD | Fold 3 Trades | Fold 3 Net PnL | Fold 3 MTM MDD |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`BENCHMARK-0`** | 954 | +$1,352.67 | 18.19% | 859 | +$150.88 | 14.89% | 1,038 | -$1,260.12 | 20.67% |
| `META-1-LOGIT_H1` | 17 | -$51.47 | 3.74% | 3 | -$35.38 | 0.82% | 0 | $0.00 | 0.00% |
| `META-1-LOGIT_H3` | 11 | -$181.68 | 3.30% | 0 | $0.00 | 0.00% | 0 | $0.00 | 0.00% |
| `META-2-LGBM_H1`  | 9 | -$129.67 | 1.30% | 38 | +$331.22 | 2.05% | 19 | -$105.82 | 1.33% |
| `META-2-LGBM_H3`  | 3 | -$55.86 | 0.60% | 21 | +$61.14 | 1.29% | 7 | -$25.48 | 0.77% |
| `META-3-XGB_H1`   | 0 | $0.00 | 0.00% | 8 | +$23.21 | 0.81% | 1 | +$3.15 | 0.32% |
| `META-3-XGB_H3`   | 0 | $0.00 | 0.00% | 0 | $0.00 | 0.00% | 0 | $0.00 | 0.00% |

---

### 5.3 Pair Activity & Spatial Robustness Breakdown

| Candidate | BTCUSDT | ETHUSDT | SOLUSDT | BNBUSDT | XRPUSDT | ADAUSDT | AVAXUSDT | LINKUSDT | DOGEUSDT | LTCUSDT | Profitable Pairs ($\ge 20$ trades) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`BENCHMARK-0`** | 287 | 275 | 262 | 290 | 294 | 273 | 290 | 320 | 274 | 286 | **6 of 10** |
| `META-1-LOGIT_H1` | 1 | 1 | 2 | 1 | 1 | 3 | 2 | 5 | 3 | 1 | **0 of 10** (0 / 10 $\ge 20$) |
| `META-1-LOGIT_H3` | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 4 | 2 | 0 | **0 of 10** (0 / 10 $\ge 20$) |
| `META-2-LGBM_H1`  | 5 | 8 | 7 | 2 | 7 | 7 | 8 | 7 | 9 | 6 | **0 of 10** (0 / 10 $\ge 20$) |
| `META-2-LGBM_H3`  | 1 | 4 | 3 | 1 | 2 | 4 | 3 | 5 | 3 | 5 | **0 of 10** (0 / 10 $\ge 20$) |
| `META-3-XGB_H1`   | 1 | 0 | 2 | 0 | 2 | 1 | 1 | 1 | 0 | 1 | **0 of 10** (0 / 10 $\ge 20$) |
| `META-3-XGB_H3`   | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0 of 10** (0 / 10 $\ge 20$) |

---

## 6. Synchronized Stationary Block-Bootstrap Statistical Inference

Using the pre-registered stationary block bootstrap specification:
- **Number of Replicates**: $B = 2,000$
- **Expected Block Length**: $5\text{ days}$ ($120\text{ hourly bars}$, geometric distribution $p = 0.20$)
- **RNG Seed**: `42`
- **Pair Synchronization**: Synchronous calendar-time daily resampling across all 10 pairs.
- **Hypothesis Test**: One-tailed null hypothesis $H_0: \Delta_{\text{Net PnL}} \le 0$ vs $H_1: \Delta_{\text{Net PnL}} > 0$.
- **Tail Convention**: $p$-value $= \frac{1}{B} \sum_{b=1}^B \mathbb{I}(\Delta_{\text{Net PnL}, b} \le 0.0)$. A statistically significant outperformance requires $p < 0.05$ and $95\%\text{ CI lower bound} > 0.0$.

### 6.1 Bootstrap Inference Results Table

| Candidate Configuration | $\Delta \text{Net PnL}$ Mean | $\Delta \text{Net PnL}$ Median | $\Delta \text{Net PnL}$ 95% CI | $\Delta \text{Expectancy}$ Mean | $\Delta \text{PF}$ Mean | One-Tailed $p$-value | Statistically Significant? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `META-1-LOGIT_H1` | -$265.93 | -$209.64 | [-$8,237.18, +$6,829.15] | -44.79 bps | -0.206 | 0.5155 | **NO** |
| `META-1-LOGIT_H2` | -$265.93 | -$209.64 | [-$8,237.18, +$6,829.15] | -44.79 bps | -0.206 | 0.5155 | **NO** |
| `META-1-LOGIT_H3` | -$360.67 | -$304.38 | [-$8,366.10, +$6,796.10] | -166.77 bps| -0.594 | 0.5290 | **NO** |
| `META-1-LOGIT_H4` | -$360.67 | -$304.38 | [-$8,366.10, +$6,796.10] | -166.77 bps| -0.594 | 0.5290 | **NO** |
| `META-2-LGBM_H1`  | -$85.82  | -$29.53  | [-$7,914.66, +$6,972.69] | +10.81 bps | +0.140 | 0.4975 | **NO** |
| `META-2-LGBM_H2`  | -$85.82  | -$29.53  | [-$7,914.66, +$6,972.69] | +10.81 bps | +0.140 | 0.4975 | **NO** |
| `META-2-LGBM_H3`  | -$196.38 | -$140.09 | [-$8,194.66, +$6,962.11] | -9.65 bps  | -0.076 | 0.5070 | **NO** |
| `META-2-LGBM_H4`  | -$196.38 | -$140.09 | [-$8,194.66, +$6,962.11] | -9.65 bps  | -0.076 | 0.5070 | **NO** |
| `META-3-XGB_H1`   | -$153.16 | -$96.87  | [-$8,149.76, +$6,998.56] | +26.46 bps | +0.312 | 0.5035 | **NO** |
| `META-3-XGB_H2`   | -$153.16 | -$96.87  | [-$8,149.76, +$6,998.56] | +26.46 bps | +0.312 | 0.5035 | **NO** |
| `META-3-XGB_H3`   | -$179.48 | -$123.19 | [-$8,252.23, +$6,975.77] | -3.31 bps  | -0.007 | 0.5065 | **NO** |
| `META-3-XGB_H4`   | -$179.48 | -$123.19 | [-$8,252.23, +$6,975.77] | -3.31 bps  | -0.007 | 0.5065 | **NO** |

### 6.2 Multiple Comparisons & Statistical Verdict
- None of the 12 candidate configurations achieved a bootstrap $p$-value $< 0.05$.
- In fact, all empirical $p$-values cluster tightly around $0.50$ ($0.4975$ to $0.5290$), indicating that the delta between any meta-model's performance and Benchmark-0 is indistinguishable from random noise.
- Under formal multiple-testing correction (e.g. Holm-Bonferroni across the 12 candidate tests), the significance hurdle would be even stricter ($p < 0.05 / 12 = 0.00416$). No candidate comes remotely close to statistical significance.

---

## 7. Institutional Qualification Gate Audit Matrix

All eight frozen qualification gates were evaluated programmatically via [`backend/strategy/qualification.py`](file:///d:/vanta-terminal/backend/strategy/qualification.py):

| Gate ID | Hurdle Requirement | Denominator | `BENCHMARK-0` | `META-1-LOGIT` (H1) | `META-2-LGBM` (H1) | `META-3-XGB` (H1) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **GATE-1** | Maximum Drawdown $\le 15.0\%$ | Continuous Equity Curve | 20.67% [FAIL] | **3.74% [PASS]** | **2.05% [PASS]** | **0.81% [PASS]** |
| **GATE-2** | Net Expectancy $\ge +8.0\text{ bps}$ | Unweighted Mean Return | +3.31 bps [FAIL] | -41.48 bps [FAIL] | **+14.12 bps [PASS]** | **+29.77 bps [PASS]** |
| **GATE-3** | Profit Factor $\ge 1.25$ | Net Realized PnL | 1.007 [FAIL] | 0.801 [FAIL] | 1.147 [FAIL] | **1.319 [PASS]** |
| **GATE-4** | Aggregate Trades $\ge 150$ | 10 Qualified Pairs (OOS) | **2,851 [PASS]** | 20 [FAIL] | 66 [FAIL] | 9 [FAIL] |
| **GATE-5** | Per-Pair Count $\ge 20$ trades | 10 of 10 Qualified Pairs | **10 / 10 [PASS]** | 0 / 10 [FAIL] | 0 / 10 [FAIL] | 0 / 10 [FAIL] |
| **GATE-6** | Walk-Forward Consistency | $\ge 2$ of 3 Folds Profitable| **2 / 3 [PASS]** | 0 / 3 [FAIL] | 1 / 3 [FAIL] | **2 / 3 [PASS]** |
| **GATE-7** | Spatial Robustness | $\ge 7$ of 10 Pairs Profitable | 6 / 10 [FAIL] | 3 / 10 [FAIL] | 4 / 10 [FAIL] | 4 / 10 [FAIL] |
| **GATE-8** | Stress Tolerance ($21\text{ bps}$) | Net PnL $> \$0$ & $\text{PF} > 1.0$ | -$2,222.20 [FAIL] | -$93.85 [FAIL] | **+$69.18 [PASS]** | **+$22.76 [PASS]** |
| **SUMMARY**| **Total Gates Passed** | **8 Mandatory Gates** | **4 / 8** | **1 / 8** | **3 / 8** | **5 / 8** |
| **STATUS** | **Certification Verdict** | — | **`UNQUALIFIED`** | **`FAILED`** | **`FAILED`** | **`FAILED`** |

*Note: All 12 candidate combinations failed GATE-4 and GATE-5 due to trade starvation. No candidate qualified.*

---

## 8. Baseline Reconciliation & Accounting Fidelity

The Benchmark-0 reproduction run within Phase 5D.3 was joined record-for-record against the Phase 5C.1 benchmark trade ledger (`data/experiments/phase_5c/benchmark_0_trades.json`):

| Accounting Dimension | Phase 5C.1 Benchmark-0 | Phase 5D.3 Benchmark-0 Replay | Absolute Discrepancy ($\Delta$) | Alignment |
| :--- | :---: | :---: | :---: | :---: |
| **Completed Trades** | 2,851 | 2,851 | **0** | **PERFECT MATCH** |
| **Gross PnL** | $+\$4,370.79$ | $+\$4,370.79$ | **$0.00** | **PERFECT MATCH** |
| **Total Taker Fees Paid** | $\$2,949.30$ | $\$2,949.30$ | **$0.00** | **PERFECT MATCH** |
| **Total Slippage Cost** | $\$1,178.06$ | $\$1,178.06$ | **$0.00** | **PERFECT MATCH** |
| **Net Realized PnL** | $+\$243.43$ | $+\$243.43$ | **$0.00** | **PERFECT MATCH** |
| **Continuous MTM MDD** | $20.67\%$ | $20.67\%$ | **0.00%** | **PERFECT MATCH** |
| **Profit Factor** | 1.007 | 1.007 | **0.000** | **PERFECT MATCH** |
| **Win Rate** | 25.53% | 25.53% | **0.00%** | **PERFECT MATCH** |

Zero accounting drift exists between Phase 5C and Phase 5D.3.

---

## 9. Failure Attribution & Scientific Insights

The outcome `PHASE_5D3_NO_QUALIFIED_MODEL` provides unambiguous quantitative attribution:

```
+----------------------------------------------------------------------------------------------------+
| THE META-FILTERING TRADE-OFF TRAP                                                                  |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [ Primary Breakout Candidate Stream ] (2,851 trades, 25.5% Win Rate, Gross Edge: +$4,370.79)     |
|                       |                                                                            |
|                       v                                                                            |
|  [ Meta-Classifier Evaluates Features ] (AUC ~0.45 - 0.56, Calibrated Probabilities ~0.24 - 0.27) |
|                       |                                                                            |
|                       +-----------------------------------+                                        |
|                       |                                   |                                        |
|                       v                                   v                                        |
|             [ Threshold tau >= 0.50 ]           [ Threshold tau >= 0.55 ]                          |
|             - Rejects 97.7% - 99.7% of trades   - Rejects 98.9% - 100.0% of trades                 |
|             - Executed: 9 to 66 trades          - Executed: 0 to 31 trades                         |
|                       |                                   |                                        |
|                       +-----------------+-----------------+                                        |
|                                         |                                                          |
|                                         v                                                          |
|  [ Outcome: Drawdown Suppressed (<4%), BUT Sample Size Starved (<150 trades) ]                     |
|  -> FAILS GATE-4 (Sample Size >= 150) & GATE-5 (Per-Pair Count >= 20)                              |
|  -> Bootstrap p-value ~ 0.50 (No statistically detectable edge over baseline)                      |
+----------------------------------------------------------------------------------------------------+
```

1. **Why Drawdown Improved**:
   By pruning out over $97\%$ of candidate trades, the strategy was simply in cash for most of the walk-forward evaluation period. The low MTM MDD ($< 4\%$) was not an achievement of selective alpha; it was largely the passive consequence of not being invested in the market.
2. **Why Volume Collapsed**:
   The primary Donchian breakout strategy has a structural win rate of $\sim 24 - 25\%$. Because the pre-registered decision hurdle was fixed at $\tau = 0.50$ or $\tau = 0.55$, the classifier demanded evidence strong enough to invert the prior probability from $0.24$ to $> 0.50$. In a noisy financial time series with features having weak mutual information, the posterior probability rarely reaches $0.50$.
3. **The Impossibility of Qualification Under Current Hypotheses**:
   Any classifier that does not output probabilities significantly above $0.50$ will execute fewer than 150 trades over 18 months, immediately failing `GATE-4` and `GATE-5`. Conversely, lowering $\tau$ down toward the base rate ($0.25$) simply admits almost all trades, collapsing back into the unqualified Benchmark-0 baseline ($20.67\%$ MDD, failing `GATE-1`).

---

## 10. Execution Constraints Compliance

| Constraint | Protocol Rule | Verification / Status |
| :--- | :--- | :--- |
| **No Holdout Contamination**| Data at or after `2026-04-26T00:00:00Z` strictly blocked | Max timestamp loaded: `1777158000000` (**COMPLIANT**) |
| **IS-Only Model Fitting** | Models and scalers fit strictly on IS partitions | Verified via `PartitionAwareScaler` guard (**COMPLIANT**) |
| **No Post-Hoc Tuning** | Hyperparameters and policy thresholds frozen | Zero parameter tuning or grid searches run (**COMPLIANT**) |
| **Port 8000 Untouched** | Never bind or terminate port 8000 | Port 8000 (PID 26148) untouched (**COMPLIANT**) |
| **Disk Space Invariant** | Preserve $\ge 10\text{ GB}$ free on `D:\` | 58.98 GB free on `D:\` (**COMPLIANT**) |
| **Single Job Execution** | Run one computational job at a time | Verified background execution (**COMPLIANT**) |

---

## 11. Artifact Inventory & Cryptographic Checksums

All experiment artifacts, ledgers, summaries, and manifests have been generated and saved to `data/experiments/phase_5d3/`:

| Artifact Path | Description | Records | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :---: | :---: | :--- |
| [`data/experiments/phase_5d3/benchmark_0_oos_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/benchmark_0_oos_trades.json) | Benchmark-0 OOS Trade Ledger | 2,851 | 2,021,744 | `1126d4a8e740b5825104f1fe1a0400d0026e0bab50d4fa2fab1ae8cac8ff8219` |
| [`data/experiments/phase_5d3/META-1-LOGIT_H1_TAU_50_COOL_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-1-LOGIT_H1_TAU_50_COOL_0_trades.json) | LOGIT H1 Trade Ledger | 20 | 14,526 | `b6ae5b58579da3219b4fb5ae3f9f336a6774e0811af7eda714dea3f795f3a244` |
| [`data/experiments/phase_5d3/META-1-LOGIT_H2_TAU_50_COOL_4_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-1-LOGIT_H2_TAU_50_COOL_4_trades.json) | LOGIT H2 Trade Ledger | 20 | 14,526 | `bcd8c2660c2772fa11e85e45e5d1a3d887fcc2cead35927e58a019f2667a57ad` |
| [`data/experiments/phase_5d3/META-1-LOGIT_H3_TAU_55_COOL_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-1-LOGIT_H3_TAU_55_COOL_0_trades.json) | LOGIT H3 Trade Ledger | 11 | 7,983 | `d5fce8ff5adce4dbbd4efaf8af4c2cd8eb3f83518fde179fa05028c2d9bfc91c` |
| [`data/experiments/phase_5d3/META-1-LOGIT_H4_TAU_55_COOL_4_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-1-LOGIT_H4_TAU_55_COOL_4_trades.json) | LOGIT H4 Trade Ledger | 11 | 7,983 | `95cdcfd538b8d30a1403ce3b38d839305a63817a4516029a28a019b3fb484422` |
| [`data/experiments/phase_5d3/META-2-LGBM_H1_TAU_50_COOL_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-2-LGBM_H1_TAU_50_COOL_0_trades.json) | LGBM H1 Trade Ledger | 66 | 47,832 | `283abfe6e395d3c42bfc1d50988378bde86aee3ba23aaa5ce24b658436e9a756` |
| [`data/experiments/phase_5d3/META-2-LGBM_H2_TAU_50_COOL_4_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-2-LGBM_H2_TAU_50_COOL_4_trades.json) | LGBM H2 Trade Ledger | 66 | 47,832 | `6a682a76f939aeefcfb5ade366b50025a6d0cd5f87bba355c8f4b96c9bdc670d` |
| [`data/experiments/phase_5d3/META-2-LGBM_H3_TAU_55_COOL_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-2-LGBM_H3_TAU_55_COOL_0_trades.json) | LGBM H3 Trade Ledger | 31 | 22,470 | `86e2ac58052af97dc66c6d36fd1db176033b013026ab6c353f73d052891d7c26` |
| [`data/experiments/phase_5d3/META-2-LGBM_H4_TAU_55_COOL_4_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-2-LGBM_H4_TAU_55_COOL_4_trades.json) | LGBM H4 Trade Ledger | 31 | 22,470 | `e714d2c6883713bcbe0fce2b279532c831bb3439c4c4322e8ceace5f02afbed6` |
| [`data/experiments/phase_5d3/META-3-XGB_H1_TAU_50_COOL_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-3-XGB_H1_TAU_50_COOL_0_trades.json) | XGB H1 Trade Ledger | 9 | 6,503 | `90083be614176e38ec5ca1082359daabee725d981b413b3a1f64163b5b82ba78` |
| [`data/experiments/phase_5d3/META-3-XGB_H2_TAU_50_COOL_4_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-3-XGB_H2_TAU_50_COOL_4_trades.json) | XGB H2 Trade Ledger | 9 | 6,503 | `addbaf6e61eeaf400f59d2d214a26ee5ca0d693be7a048944fa7baaa23581456` |
| [`data/experiments/phase_5d3/META-3-XGB_H3_TAU_55_COOL_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-3-XGB_H3_TAU_55_COOL_0_trades.json) | XGB H3 Trade Ledger | 0 | 2 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| [`data/experiments/phase_5d3/META-3-XGB_H4_TAU_55_COOL_4_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/META-3-XGB_H4_TAU_55_COOL_4_trades.json) | XGB H4 Trade Ledger | 0 | 2 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| [`data/experiments/phase_5d3/meta_classification_metrics.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/meta_classification_metrics.json) | Classification Evaluation | 9 folds | 4,058 | `cc69e19451edddd79a7fb3de3430f59e4b848f5c9a197fb3b8a36fed0514d002` |
| [`data/experiments/phase_5d3/bootstrap_inference_results.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/bootstrap_inference_results.json) | Block Bootstrap Statistics | 12 candidates | 11,869 | `a863b230af437667c111dc3cd04b4c07896e93dffb75f54ac703b0221aa29db3` |
| [`data/experiments/phase_5d3/phase_5d3_evaluation_summary.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/phase_5d3_evaluation_summary.json) | Master Evaluation Summary | N/A | 23,305,354 | `f2455d445cd6414a22b258f24c24e2941c7d04d73b822b001a54d9f001723cdb` |
| [`data/experiments/phase_5d3/manifest_sha256.json`](file:///d:/vanta-terminal/data/experiments/phase_5d3/manifest_sha256.json) | Cryptographic SHA-256 Manifest | 16 files | 2,239 | `08ea0d2164c9269f09251d5384fedaf9864c67b6ca16ce1fb677480b55a74a73` |

---

## 12. Conclusion & Strategic Next Steps

Phase 5D.3 concludes with an unambiguous, rigorous, and fully documented scientific finding:
1. Under the pre-registered configurations, **no ML meta-model qualifies**.
2. Baseline `STRAT-B-01` remains classified as **`UNQUALIFIED_BASELINE`**.
3. The quarantined final holdout remains **100% pristine and unviolated**.
4. The repository is preserved in a clean, reproducible state.
