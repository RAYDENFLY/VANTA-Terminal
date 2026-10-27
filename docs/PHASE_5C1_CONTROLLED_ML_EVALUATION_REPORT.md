# VANTA Terminal — Phase 5C.1 Controlled ML Evaluation Report

**Document ID**: `VANTA-DOCS-5C1-EVALUATION-REPORT`  
**Execution Timestamp**: `2026-10-27T09:12:00Z`  
**Author**: Antigravity Quantitative Verification & Machine Learning Research Agent  
**Certified Outcome**: `PHASE_5C1_NO_QUALIFIED_MODEL`  
**Reference Baseline**: `STRAT-B-01 (Donchian Breakout 1H) — UNQUALIFIED_BASELINE`  
**Holdout Quarantine**: Strictly Preserved (Zero data loaded or evaluated $\ge \text{2026-04-26T00:00:00Z}$)  

---

## 1. Executive Summary & Certified Findings

Phase 5C.1 executed the first controlled walk-forward Machine Learning experiment in VANTA Terminal, following the pre-registered protocol specified in [`docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md`](file:///d:/vanta-terminal/docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md), the feature definitions in [`docs/PHASE_5A_FEATURE_CATALOG.md`](file:///d:/vanta-terminal/docs/PHASE_5A_FEATURE_CATALOG.md), the statistical framework in [`docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md`](file:///d:/vanta-terminal/docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md), and the conformance corrections established in [`docs/PHASE_5B1_PROTOCOL_CONFORMANCE_AUDIT.md`](file:///d:/vanta-terminal/docs/PHASE_5B1_PROTOCOL_CONFORMANCE_AUDIT.md) and [`docs/PHASE_5B2_LABEL_SEMANTICS_GATE.md`](file:///d:/vanta-terminal/docs/PHASE_5B2_LABEL_SEMANTICS_GATE.md).

The central research question evaluated was:
> *Does any pre-registered supervised Machine Learning candidate produce reproducible incremental net performance over Benchmark-0 under identical portfolio, execution, cost, and walk-forward constraints?*

### Certified Outcome:
$$\mathbf{STATUS: \ PHASE\_5C1\_NO\_QUALIFIED\_MODEL}$$

**All three pre-registered ML candidates (`MODEL-1-LOGIT`, `MODEL-2-LGBM`, `MODEL-3-XGB`) failed 6 of the 8 frozen qualification gates**, generating severe continuous mark-to-market drawdowns (~94.6% to 95.1%) and substantial net dollar losses (~-$18,450 to -$18,940). None of the candidates produced positive net PnL, positive expectancy, or statistically significant incremental performance over `Benchmark-0`.

### Key Research Findings:
1. **Marginal Gross Predictability Crushed by High-Frequency Friction**:
   All three models achieved weakly positive gross dollar PnL in In-Sample and across portions of Out-of-Sample (Gross PnL: +$1,969.50 for LOGIT, +$2,230.28 for LGBM, +$1,650.31 for XGB). However, each model generated over **25,000 Out-of-Sample trades** across the 18 months of OOS testing (~46 trades per day across 10 pairs). At 14.0 bps round-trip baseline friction, total execution fees ($15,100+) and slippage ($5,500+) totaled **$20,600+**, completely overwhelming the marginal gross edge and producing net expectancies of **-7.13 to -7.45 bps per trade**.
2. **Benchmark-0 Remains the Superior Reference (Despite Being Unqualified)**:
   `Benchmark-0` (Strategy B Donchian Breakout 1H) produced **+$243.43 net PnL** on 2,851 trades with a 20.67% MTM MDD. In the paired stationary block bootstrap ($B=2,000$ replicates, $\mathbb{E}[L]=5\text{ days}$), the 95% confidence interval for incremental ML net PnL ($\Delta_{\text{PnL}} = \text{PnL}_{\text{ML}} - \text{PnL}_{\text{BM0}}$) was **[-$28,464, -$9,472]** for LOGIT, **[-$27,444, -$10,713]** for LGBM, and **[-$28,069, -$11,062]** for XGB. In **zero out of 2,000 resamples** did any ML candidate match or exceed Benchmark-0 ($p = 1.000$).
3. **Pervasive Cross-Sectional and Walk-Forward Fragility**:
   Across all three walk-forward folds and across all 10 liquid perpetual pairs, **zero folds and zero pairs were net profitable** for any ML model (0/3 profitable folds, 0/10 profitable pairs).
4. **Holdout Quarantine Impeccably Preserved**:
   All training, scaling, feature computation, and backtesting operations strictly respected the `2026-04-26T00:00:00Z` quarantine boundary (`1777161600000` ms). The final candle loaded was `1777158000000` ms (`2026-04-25 23:00:00 UTC`). Zero holdout rows were inspected or accessed.

---

## 2. Experimental Setup & Arena Architecture

### 2.1 The Candidates Evaluated
1. **`BENCHMARK-0`**: Frozen Phase 4B.5 Strategy B Reference (Donchian Breakout / Trend 1H, configurations `B-09`, `B-09`, `B-05`). Certified baseline status: `UNQUALIFIED_BASELINE`.
2. **`MODEL-1-LOGIT`**: Regularized Multinomial Logistic Regression, L2 penalty ($C=0.10$), `solver='lbfgs'`, multi-class balanced sample weighting.
3. **`MODEL-2-LGBM`**: LightGBM Classifier, 300 estimators, `max_depth=4`, `num_leaves=15`, `min_child_samples=50`, `subsample=0.8`, `colsample_bytree=0.8`, `learning_rate=0.03`, `random_state=42`, `n_jobs=4`.
4. **`MODEL-3-XGB`**: XGBoost Classifier, 300 estimators, `max_depth=4`, `min_child_weight=50`, `subsample=0.8`, `colsample_bytree=0.8`, `learning_rate=0.03`, `random_state=42`, `n_jobs=4`.

### 2.2 Walk-Forward Schedule & Sample Partitions
The three pre-registered walk-forward folds were executed with 150-bar warmup buffers, 48-hour purges, and 48-hour embargos:

| Fold | In-Sample Train Range (UTC) | IS Samples | Purge / Embargo Buffer | Out-of-Sample Eval Range (UTC) | OOS Samples |
| :--- | :--- | :---: | :---: | :--- | :---: |
| **Fold 1** | 2023-10-26 00:00 $\rightarrow$ 2024-10-24 00:00 | 86,750 | 96 Hours (48h purge + 48h embargo) | 2024-10-28 00:00 $\rightarrow$ 2025-04-26 00:00 | 43,200 |
| **Fold 2** | 2024-04-26 00:00 $\rightarrow$ 2025-04-24 00:00 | 87,000 | 96 Hours (48h purge + 48h embargo) | 2025-04-28 00:00 $\rightarrow$ 2025-10-26 00:00 | 43,440 |
| **Fold 3** | 2024-10-26 00:00 $\rightarrow$ 2025-10-24 00:00 | 87,000 | 96 Hours (48h purge + 48h embargo) | 2025-10-28 00:00 $\rightarrow$ 2026-04-26 00:00 | 43,200 |

### 2.3 Feature Matrix & Label Semantics
- **Features**: 21 pre-registered features across 7 families (Lagged returns, Volatility/True Range, Moving Average distances, Relative Volume, Microstructure wick ratios, Rolling range, Cross-sectional beta/relative return). Scaled strictly with [`PartitionAwareScaler`](file:///d:/vanta-terminal/backend/ml/scaling.py) fit on In-Sample only.
- **Labels**: Triple-Barrier Target (`TARGET-C-BARRIER`, $H=12\text{ bars}$) with entry at $O_{t+1} \times (1 \pm 2\text{ bps slip})$, Take Profit at $1.5\text{ ATR}_{14} + 14.0\text{ bps hurdle}$, Stop Loss at $1.0\text{ ATR}_{14}$, and `CONSERVATIVE_SL_FIRST` collision resolution.
- **Portfolio Accounting**: [`CanonicalPortfolioEngine`](file:///d:/vanta-terminal/backend/backtest/portfolio_engine.py) with shared $10,000 equity pool, 1.0x gross leverage cap, 10% target sizing per position, 14.0 bps round-trip friction (primary) and 21.0 bps (stress).

---

## 3. Master Arena Performance Comparison

The table below presents the Out-of-Sample economic performance across all four candidates:

| Candidate ID | Total Trades | Win Rate | Gross PnL | Fees Paid | Slippage Cost | Net PnL | Profit Factor | Net Expectancy | Chained MTM MDD | Stress Net PnL | Stress PF |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BENCHMARK-0** | 2,851 | 33.15% | +$2,228.00 | $1,421.36 | $563.21 | **+$243.43** | **1.007** | **+0.85 bps** | **20.67%** | -$2,222.20 | 0.934 |
| **MODEL-1-LOGIT** | 25,076 | 39.53% | +$1,969.50 | $15,115.60 | $5,539.35 | **-$18,685.47** | **0.830** | **-7.45 bps** | **94.92%** | -$23,965.14 | 0.741 |
| **MODEL-2-LGBM** | 25,896 | 39.41% | +$2,230.28 | $15,134.03 | $5,549.17 | **-$18,452.94** | **0.840** | **-7.13 bps** | **94.63%** | -$24,102.29 | 0.749 |
| **MODEL-3-XGB** | 25,639 | 39.25% | +$1,650.31 | $15,064.50 | $5,522.95 | **-$18,937.14** | **0.834** | **-7.39 bps** | **95.10%** | -$24,294.84 | 0.745 |

---

## 4. Frozen Qualification Gate Evaluation Matrix

All eight gates established in Phase 4B and reaffirmed in Phase 5A are binding:

| Gate ID | Metric & Hurdle | BENCHMARK-0 | MODEL-1-LOGIT | MODEL-2-LGBM | MODEL-3-XGB |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **GATE-1** | Per-Fold MTM MDD $\le 15.0\%$ & Chained MDD $\le 15.0\%$ | **FAIL** (20.67%) | **FAIL** (94.92%) | **FAIL** (94.63%) | **FAIL** (95.10%) |
| **GATE-2** | Net Expectancy $\ge +8.0\text{ bps}$ | **FAIL** (+0.85 bps) | **FAIL** (-7.45 bps) | **FAIL** (-7.13 bps) | **FAIL** (-7.39 bps) |
| **GATE-3** | Profit Factor $\ge 1.25$ | **FAIL** (1.007) | **FAIL** (0.830) | **FAIL** (0.840) | **FAIL** (0.834) |
| **GATE-4** | Aggregate OOS Trades $\ge 150$ | **PASS** (2,851) | **PASS** (25,076) | **PASS** (25,896) | **PASS** (25,639) |
| **GATE-5** | $\ge 20$ Trades per pair for all 10 pairs | **PASS** (Min 215) | **PASS** (Min 2,262) | **PASS** (Min 1,839) | **PASS** (Min 1,880) |
| **GATE-6** | Walk-Forward Consistency: $\ge 2/3$ profitable folds | **PASS** (2/3) | **FAIL** (0/3) | **FAIL** (0/3) | **FAIL** (0/3) |
| **GATE-7** | Spatial Robustness: $\ge 7/10$ profitable pairs | **FAIL** (6/10) | **FAIL** (0/10) | **FAIL** (0/10) | **FAIL** (0/10) |
| **GATE-8** | Stress Cost Tolerance: Stress PnL $> \$0$ & PF $> 1.0$ | **FAIL** (-$2,222) | **FAIL** (-$23,965) | **FAIL** (-$24,102) | **FAIL** (-$24,295) |
| **SUMMARY** | **All 8 Gates Simultaneously Passed** | **UNQUALIFIED** | **UNQUALIFIED** | **UNQUALIFIED** | **UNQUALIFIED** |

---

## 5. Walk-Forward Fold-by-Fold Breakdown

### Fold 1 (OOS: 2024-10-28 to 2025-04-26)
- Initial Capital: $10,000.00
- **BENCHMARK-0**: Trades: 954 | Net PnL: -$1,100.82 | MTM MDD: 15.34% | PF: 0.880
- **MODEL-1-LOGIT**: Trades: 8,838 | Net PnL: -$6,442.19 | MTM MDD: 64.56% | PF: 0.841 | Gross: +$172.25 | Fees: $4,844.31
- **MODEL-2-LGBM**: Trades: 9,080 | Net PnL: -$5,285.70 | MTM MDD: 55.16% | PF: 0.891 | Gross: +$2,266.55 | Fees: $5,532.81
- **MODEL-3-XGB**: Trades: 8,961 | Net PnL: -$5,738.33 | MTM MDD: 57.60% | PF: 0.881 | Gross: +$1,770.59 | Fees: $5,502.21

### Fold 2 (OOS: 2025-04-28 to 2025-10-26)
- Initial Capital: $10,000.00
- **BENCHMARK-0**: Trades: 859 | Net PnL: +$1,273.74 | MTM MDD: 12.87% | PF: 1.150
- **MODEL-1-LOGIT**: Trades: 9,248 | Net PnL: -$6,946.13 | MTM MDD: 69.48% | PF: 0.805 | Gross: +$324.75 | Fees: $5,319.50
- **MODEL-2-LGBM**: Trades: 9,256 | Net PnL: -$6,461.01 | MTM MDD: 64.70% | PF: 0.819 | Gross: +$968.80 | Fees: $5,436.67
- **MODEL-3-XGB**: Trades: 9,146 | Net PnL: -$6,622.63 | MTM MDD: 66.37% | PF: 0.812 | Gross: +$769.77 | Fees: $5,408.11

### Fold 3 (OOS: 2025-10-28 to 2026-04-26)
- Initial Capital: $10,000.00
- **BENCHMARK-0**: Trades: 1,038 | Net PnL: +$70.51 | MTM MDD: 20.67% | PF: 1.010
- **MODEL-1-LOGIT**: Trades: 6,990 | Net PnL: -$5,297.15 | MTM MDD: 58.26% | PF: 0.843 | Gross: +$1,472.50 | Fees: $4,951.79
- **MODEL-2-LGBM**: Trades: 7,560 | Net PnL: -$6,706.23 | MTM MDD: 67.40% | PF: 0.781 | Gross: -$1,005.07 | Fees: $4,164.55
- **MODEL-3-XGB**: Trades: 7,532 | Net PnL: -$6,576.18 | MTM MDD: 66.33% | PF: 0.783 | Gross: -$890.05 | Fees: $4,154.18

---

## 6. Spatial Cross-Sectional Robustness (Per-Pair Results)

The table below summarizes the net dollar PnL and trade activity per pair across all three Out-of-Sample folds:

| Symbol | Benchmark-0 PnL | MODEL-1-LOGIT PnL | Trades | MODEL-2-LGBM PnL | Trades | MODEL-3-XGB PnL | Trades |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BTCUSDT** | +$412.30 | -$1,897.75 | 2,451 | -$1,951.56 | 1,839 | -$1,872.51 | 1,880 |
| **ETHUSDT** | +$185.10 | -$2,213.84 | 2,262 | -$1,869.03 | 2,436 | -$1,587.79 | 2,389 |
| **SOLUSDT** | -$312.40 | -$1,656.23 | 2,301 | -$1,813.38 | 2,480 | -$1,887.67 | 2,462 |
| **BNBUSDT** | +$95.20 | -$2,616.03 | 2,658 | -$2,794.04 | 2,797 | -$2,948.72 | 2,783 |
| **XRPUSDT** | +$140.50 | -$1,774.13 | 2,320 | -$1,817.10 | 2,554 | -$2,353.56 | 2,529 |
| **ADAUSDT** | -$480.10 | -$1,491.06 | 2,367 | -$725.79 | 2,619 | -$420.02 | 2,559 |
| **AVAXUSDT** | +$210.80 | -$1,097.57 | 3,012 | -$1,570.51 | 3,156 | -$1,404.17 | 3,119 |
| **LINKUSDT** | -$115.60 | -$2,776.72 | 2,695 | -$2,289.89 | 2,812 | -$2,972.20 | 2,746 |
| **DOGEUSDT** | +$320.10 | -$843.30 | 2,434 | -$1,037.82 | 2,541 | -$914.39 | 2,525 |
| **LTCUSDT** | -$212.47 | -$2,318.83 | 2,576 | -$2,583.82 | 2,662 | -$2,576.11 | 2,647 |
| **Profitable Pairs** | **6 / 10** | **0 / 10** | — | **0 / 10** | — | **0 / 10** | — |

---

## 7. Secondary Classification Diagnostics (ML Performance Only)

Classification diagnostics were tracked as secondary sanity checks. As established in Phase 5A, raw classification accuracy is not an economic objective:

| Metric | Fold | MODEL-1-LOGIT (IS / OOS) | MODEL-2-LGBM (IS / OOS) | MODEL-3-XGB (IS / OOS) |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy** | Fold 1 | 35.28% / 32.97% | 42.92% / 35.13% | 42.02% / 34.78% |
| | Fold 2 | 36.34% / 42.68% | 43.35% / 43.59% | 42.75% / 43.31% |
| | Fold 3 | 35.68% / 34.46% | 42.84% / 36.21% | 41.93% / 36.27% |
| **Balanced Accuracy** | Fold 1 | 39.77% / 39.40% | 49.83% / 40.79% | 48.99% / 41.22% |
| | Fold 2 | 40.15% / 38.22% | 50.03% / 38.26% | 49.08% / 38.29% |
| | Fold 3 | 39.89% / 38.58% | 50.29% / 39.25% | 49.19% / 39.40% |
| **Brier Multi-Class Score** | Fold 1 | 0.6614 / 0.6695 | 0.6271 / 0.6563 | 0.6326 / 0.6566 |
| | Fold 2 | 0.6601 / 0.6411 | 0.6245 / 0.6269 | 0.6300 / 0.6286 |
| | Fold 3 | 0.6610 / 0.6697 | 0.6259 / 0.6592 | 0.6316 / 0.6595 |

### Out-of-Sample Confusion Matrix (Fold 1 Aggregate):
For `MODEL-2-LGBM` (Rows: True Labels `[-1, 0, 1]`, Columns: Predicted Labels `[-1, 0, 1]`):
```
True \ Pred       -1 (Short)    0 (Neutral)     +1 (Long)
-1 (Bearish SL/TP)   8,088        8,475           8,421
 0 (Neutral Expiry)    679        1,591             677
+1 (Bullish TP/SL)   4,500        5,193           5,456
```
The confusion matrix confirms that while the tree models fit the In-Sample partitions moderately well (Balanced Accuracy ~50.3%), the models over-predicted directional breakouts in OOS, suffering severe false discovery rates where neutral or choppy moves were predicted as trend breakouts.

---

## 8. Synchronized Stationary Block Bootstrap Inference

Following [`docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md`](file:///d:/vanta-terminal/docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md), statistical inference was conducted using a cross-sectionally synchronized Stationary Block Bootstrap with $B = 2,000$ resamples, a geometric block length parameter $p = 0.20$ ($\mathbb{E}[L] = 5\text{ days}$), and random seed 42.

Paired resampling evaluated the incremental performance $\Delta_{\text{ML}} = \text{Metric}_{\text{ML}} - \text{Metric}_{\text{BM0}}$ across identical daily slices:

| Candidate ID | Metric | Point Estimate ($\Delta$) | Bootstrap Mean ($\Delta^*$) | Bootstrap Std | 95% Bootstrap CI $[\Delta^*_{0.025}, \Delta^*_{0.975}]$ | One-Tailed $p$-value ($H_1: \Delta > 0$) | Statistically Significant |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **MODEL-1-LOGIT** | Net PnL (\$) | -$18,928.90 | -$18,783.12 | \$4,740.14 | **[-$28,464.33, -$9,472.31]** | **1.000** | **NO** |
| | Expectancy (bps) | -8.30 | -8.11 | 13.62 | [-36.48, +16.87] | 0.722 | **NO** |
| | Profit Factor | -0.177 | -0.180 | 0.121 | [-0.430, +0.040] | 0.941 | **NO** |
| **MODEL-2-LGBM** | Net PnL (\$) | -$18,696.37 | -$18,705.99 | \$4,216.58 | **[-$27,443.51, -$10,712.79]** | **1.000** | **NO** |
| | Expectancy (bps) | -7.98 | -7.85 | 13.43 | [-35.66, +16.91] | 0.716 | **NO** |
| | Profit Factor | -0.167 | -0.170 | 0.115 | [-0.410, +0.040] | 0.938 | **NO** |
| **MODEL-3-XGB** | Net PnL (\$) | -$19,180.57 | -$19,173.66 | \$4,182.48 | **[-$28,069.07, -$11,062.11]** | **1.000** | **NO** |
| | Expectancy (bps) | -8.24 | -8.10 | 13.51 | [-36.22, +16.57] | 0.724 | **NO** |
| | Profit Factor | -0.173 | -0.170 | 0.115 | [-0.420, +0.030] | 0.945 | **NO** |

### Statistical Inference Verdict:
- The null hypothesis $H_0: \Delta_{\text{PnL}} \le 0$ **CANNOT be rejected**.
- The one-tailed $p$-value across 2,000 paired replicates is identically $1.0000$ for all three models. In **zero bootstrap replicates** did any ML candidate deliver greater net PnL than Benchmark-0.
- Conversely, the upper bound of the 95% confidence interval for incremental dollar return is strictly negative for all candidates (highest upper bound is -$9,472.31 for LOGIT). This establishes that **all three ML models significantly underperformed the unqualified Benchmark-0 reference**.

---

## 9. Economic Post-Mortem & Attribution of Failure

Why did supervised Machine Learning fail to qualify in Phase 5C.1?

1. **The Turnover-Friction Trap**:
   In financial machine learning, predicting high-volatility triple-barrier exits on 1-hour candles creates an excessively active trading policy. The ML models triggered an average of **1.4 trades per hour across the 10-pair universe** (~25,500 trades over 18 months). At 14.0 bps round-trip friction, each trade forfeits $0.14 per $1,000 notional. Total fees paid exceeded $20,600 on an initial $10,000 cash pool.
2. **Gross Edge Exists But Is Sub-Friction**:
   The ML models actually identified positive directional drift: gross PnL before fees was +$1,970 (LOGIT) and +$2,230 (LGBM). However, this represents an average gross edge of only **+7.8 bps to +8.6 bps per trade**. When subtracted by 14.0 bps of mandatory taker and slippage friction, the net edge becomes negative (-5.4 to -6.2 bps plus boundary close-out decay).
3. **Contrast with Benchmark-0 (Donchian Trend)**:
   Benchmark-0 utilized a strict multi-condition regime filter (`channel_m=30`, `volume_mult=1.5`, `ema_filter=100`). It entered only 2,851 trades over the same 18-month span (an 89% lower trade frequency). Even with a lower win rate (33.15% vs 39.4%), its selectivity allowed it to preserve capital and survive with positive net profit (+$243.43).
4. **Failure of Probability Calibration to Discriminate Chop**:
   In low-volatility regimes (such as Fold 1 and Fold 3), crypto perpetuals exhibit frequent mean-reverting chop. The feature catalog (momentum, EMA distances, normalized range) triggered false breakout signals during range-bound consolidations, hitting the $1.0\text{ ATR}$ stop barrier before achieving the $1.5\text{ ATR} + 14\text{ bps}$ profit barrier.

---

## 10. Audit Trail & Verification Manifests

- **Experiment Manifest**: [`data/experiments/phase_5c/experiment_manifest.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/experiment_manifest.json)
- **Candidate 1 Results**: [`data/experiments/phase_5c/MODEL-1-LOGIT_RESULTS.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/MODEL-1-LOGIT_RESULTS.json)
- **Candidate 2 Results**: [`data/experiments/phase_5c/MODEL-2-LGBM_RESULTS.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/MODEL-2-LGBM_RESULTS.json)
- **Candidate 3 Results**: [`data/experiments/phase_5c/MODEL-3-XGB_RESULTS.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/MODEL-3-XGB_RESULTS.json)
- **Benchmark Trades Cache**: [`data/experiments/phase_5c/benchmark_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/benchmark_0_trades.json)
- **Holdout Boundary Verification**: Max open timestamp loaded: `1777158000000` (`2026-04-25 23:00:00 UTC`), strictly `< 1777161600000` (`2026-04-26 00:00:00 UTC`).

---

## 11. Final Certified Exit Status

Following the mandatory qualification rules of Phase 5C.1:

$$\mathbf{CERTIFIED \ OUTCOME: \ PHASE\_5C1\_NO\_QUALIFIED\_MODEL}$$

- No candidate strategy is promoted to `QUALIFIED_STRATEGY`.
- `Benchmark-0` (`STRAT-B-01` Donchian Breakout 1H) retains its status as `UNQUALIFIED_BASELINE`.
- The quarantined Phase 6 final holdout remains untouched and locked.
- The experiment concludes cleanly with reproducible artifacts and cryptographic manifests.
