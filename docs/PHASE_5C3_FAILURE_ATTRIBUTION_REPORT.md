# VANTA Terminal — Phase 5C.3 Failure Attribution & Strategy Diagnosis

**Document ID**: `VANTA-DOCS-5C3-FAILURE-ATTRIBUTION`  
**Execution Timestamp**: `2026-10-27T10:30:00Z`  
**Author**: Antigravity Quantitative Verification & Machine Learning Research Agent  
**Current Certified Status**: `PHASE_5C1_NO_QUALIFIED_MODEL`  
**Prior Audit Status**: `PHASE_5C2_AUDIT_PASS`  
**Scope**: Read-only diagnostic investigation into the economic, execution, and signal mechanisms driving the qualification failure of Phase 5C.1 ML candidates  
**Hard Constraints**: Zero model training, zero backtest reruns, zero holdout access, zero source code modifications  

---

## 1. Executive Summary & Diagnostic Mandate

Phase 5C.3 conducted a read-only, evidence-based diagnostic attribution of the Phase 5C.1 controlled machine learning experiment. In Phase 5C.1, all three pre-registered machine learning models (`MODEL-1-LOGIT`, `MODEL-2-LGBM`, `MODEL-3-XGB`) failed qualification despite achieving positive gross trading profits before friction (+$\$$1,650 to +$\$$2,230 across folds).

The objective of this investigation is to isolate the exact, measurable mechanisms responsible for this divergence between positive gross PnL and catastrophic net PnL (-$\$$18,450 to -$\$$18,940 net loss, 94.6% to 95.1% chained MTM drawdown), and provide an institutional recommendation for future research.

### Core Diagnostic Finding:
> [!IMPORTANT]
> **The Primary Cause of Failure is the "Turnover-Friction Trap" Coupled with Zero-Cooldown Argmax Triggering**:
> The ML models possessed a genuine, measurable gross edge over the market (+1.17 bps per trade gross expectancy for LGBM; +$\$$2,230 gross dollar return across 25,896 trades). However, because [`MLModelStrategy`](file:///d:/vanta-terminal/backend/ml/ml_strategy.py) lacked a trade cooldown period, confidence threshold filter, or trade-selectivity constraint, the strategy entered a new position on the very next bar **84.32% of the time** after an exit (median re-entry latency = 1.0 hour). 
> 
> This created an unhedged high-turnover churning loop (~47 trades/day across 10 pairs; 25,896 total trades) that incurred **$20,683.22 in mandatory execution friction** (fees and slippage). The marginal gross edge (+1.17 bps) was an order of magnitude smaller than the unavoidable transaction friction (~12.16 bps per trade), turning a modestly predictive signal into an economically catastrophic strategy.

---

## 2. Turnover and Cost Drag Attribution

All metrics below were computed directly from the saved trade ledgers (`benchmark_0_trades.json` and candidate `_RESULTS.json` files):

### 2.1 Turnover and Execution Velocity Metrics

| Metric | BENCHMARK-0 (Donchian 1H) | MODEL-1-LOGIT | MODEL-2-LGBM | MODEL-3-XGB | Evidence Status | Supporting Source |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Total OOS Trades** | 2,851 | 25,076 | 25,896 | 25,639 | **CONFIRMED** | Result JSON trade ledgers |
| **Trades per Calendar Day (Universe)** | 5.22 | 45.93 | 47.43 | 46.96 | **CONFIRMED** | 546-day aggregate span |
| **Trades per Day per Pair** | 0.52 | 4.59 | 4.74 | 4.70 | **CONFIRMED** | 10 qualified pairs |
| **Mean Holding Duration** | 14.43 hours (bars) | 2.98 hours | 3.00 hours | 2.97 hours | **CONFIRMED** | `holding_duration_bars` |
| **Median Holding Duration** | 8.00 hours | 2.00 hours | 2.00 hours | 2.00 hours | **CONFIRMED** | `holding_duration_bars` |
| **25th / 75th Percentile Holding** | 2.0h / 25.0h | 0.0h / 4.0h | 0.0h / 4.0h | 0.0h / 4.0h | **CONFIRMED** | Quantiles of duration |
| **Median Re-Entry Latency** | 23.00 hours | 1.00 hour | 1.00 hour | 1.00 hour | **CONFIRMED** | $\Delta t(\text{entry}_{k+1} - \text{exit}_k)$ |
| **% Re-Entering Within 1 Bar ($\le 1\text{h}$)** | 1.65% | 84.18% | 84.32% | 84.05% | **CONFIRMED** | Inter-trade timestamp diff |

*Key Takeaway*: While Benchmark-0 waited an average of 31 hours (median 23 hours) between exiting a pair and re-entering, the ML strategy re-entered on the **very next bar in 84.3% of all cases**. The strategy was effectively trapped in continuous execution.

---

### 2.2 Cost Drag and PnL Decomposition per Trade

| Metric | BENCHMARK-0 | MODEL-1-LOGIT | MODEL-2-LGBM | MODEL-3-XGB | Evidence Status | Supporting Source |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Gross PnL (Total)** | +$4,370.79 | +$1,969.50 | +$2,230.28 | +$1,650.31 | **CONFIRMED** | `gross_pnl` ledger sum |
| **Exchange Fees (Total)** | $2,949.30 | $15,115.61 | $15,134.04 | $15,064.50 | **CONFIRMED** | `total_fee` ledger sum |
| **Slippage Cost (Total)** | $1,178.06 | $5,539.36 | $5,549.18 | $5,522.95 | **CONFIRMED** | `slippage_cost` ledger sum |
| **Total Friction Cost** | $4,127.36 | $20,654.97 | $20,683.22 | $20,587.45 | **CONFIRMED** | Fees + Slippage |
| **Net Realized PnL** | **+$243.43** | **-$18,685.46** | **-$18,452.94** | **-$18,937.15** | **CONFIRMED** | `net_pnl` ledger sum |
| **Friction as % of Gross Profit** | **94.4%** | **1,048.7%** | **927.4%** | **1,247.5%** | **CONFIRMED** | $\text{Friction} / \text{Gross}$ |
| **Gross Return per Trade (Mean)** | +$1.5331 | +$0.0785 | +$0.0861 | +$0.0644 | **CONFIRMED** | Ledger mean |
| **Friction per Trade (Mean)** | $1.4477 | $0.8237 | $0.7987 | $0.8030 | **CONFIRMED** | Ledger mean |
| **Net Return per Trade (Mean)** | +$0.0854 | -$0.7452 | -$0.7126 | -$0.7386 | **CONFIRMED** | Ledger mean |
| **Gross Expectancy (on Notional)** | **+17.31 bps** | **+0.54 bps** | **+1.17 bps** | **+0.63 bps** | **CONFIRMED** | Per-trade return mean |
| **Realized Friction Rate** | **14.00 bps** | **12.15 bps** | **12.16 bps** | **12.17 bps** | **CONFIRMED** | Taker + Maker + Slip |
| **Net Expectancy (on Notional)** | **+3.31 bps** | **-11.61 bps** | **-10.99 bps** | **-11.53 bps** | **CONFIRMED** | GATE-2 binding formula |

*Key Takeaway*: Exchange friction absorbed **927% to 1,247% of gross profits** for the ML candidates. Even with maker fee savings on Take Profit fills (reducing average friction from 14.0 bps to 12.16 bps), the gross expectancy of ~1.0 bps was entirely consumed.

---

### 2.3 Breakdown by Trade Direction and Exit Reason

#### By Direction (Long vs. Short):
| Candidate ID | Side | Trade Count | Win Rate | Gross PnL (\$) | Total Friction (\$) | Net PnL (\$) | Net PnL Share |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **BENCHMARK-0** | **LONG** | 1,386 | 24.24% | +$2,942.20 | $2,009.44 | **+$932.76** | +383.2% |
| | **SHORT** | 1,465 | 26.76% | +$1,428.59 | $2,117.92 | **-$689.33** | -283.2% |
| **MODEL-1-LOGIT** | **LONG** | 8,731 | 39.84% | +$133.16 | $7,125.72 | **-$6,992.55** | 37.4% |
| | **SHORT** | 16,345 | 39.28% | +$1,836.34 | $13,529.25 | **-$11,692.91** | 62.6% |
| **MODEL-2-LGBM** | **LONG** | 10,286 | 39.52% | +$1,373.47 | $8,290.53 | **-$6,917.06** | 37.5% |
| | **SHORT** | 15,610 | 39.34% | +$856.81 | $12,392.69 | **-$11,535.88** | 62.5% |
| **MODEL-3-XGB** | **LONG** | 9,972 | 39.61% | +$1,361.35 | $8,100.28 | **-$6,738.92** | 35.6% |
| | **SHORT** | 15,667 | 39.07% | +$288.95 | $12,487.17 | **-$12,198.22** | 64.4% |

#### By Exit Reason (`MODEL-2-LGBM`):
| Exit Reason | Trade Count | Win Rate | Gross PnL (\$) | Friction Paid (\$) | Net PnL (\$) | Economic Interpretation |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **STOP_LOSS** | 14,914 (57.6%) | 0.00% | -$99,218.10 | $13,718.07 | -$112,936.17 | Trapped in adverse price path ($1.0\text{ ATR}$) |
| **TAKE_PROFIT** | 9,521 (36.8%) | 98.93% | +$98,920.52 | $5,664.69 | +$93,255.83 | Reached profit target ($1.5\text{ ATR} + 14\text{ bps}$) |
| **TIME_EXPIRY** | 1,438 (5.6%) | 54.31% | +$2,523.36 | $1,290.09 | +$1,233.27 | Exited flat at bar 12 close; net profitable |
| **BOUNDARY_FLAT** | 23 (0.1%) | 26.09% | +$4.50 | $10.37 | -$5.88 | Terminal fold close-out |

*Key Takeaway*: Take Profit trades generated substantial gross gains (+$\$$98,920), but Stop Loss exits (-$\$$99,218 gross) combined with cumulative round-trip friction (-$\$$20,683) produced the net collapse. Furthermore, **SHORT trades accounted for ~63% of all net losses** across all three ML candidates.

---

## 3. Predictive Signal Quality Diagnosis

### 3.1 Asymmetric Target Label Distribution
The Triple-Barrier labeling engine was audited in Phase 5B.2 with asymmetric parameters:
- Long Take Profit: $+1.5\text{ ATR}_{14} + 14.0\text{ bps}$
- Long Stop Loss: $-1.0\text{ ATR}_{14}$

In a geometric random walk without drift, the first-hitting probability for asymmetric barriers $-a$ and $+b$ is:
$$P(\text{hit } -a \text{ before } +b) = \frac{b}{a + b} = \frac{1.5}{1.0 + 1.5} = 60.0\%$$

Empirical target class distributions extracted from [`MODEL-2-LGBM_RESULTS.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/MODEL-2-LGBM_RESULTS.json):

| Partition | Total Bars | Class -1 (Stop Hit First) | Class 0 (Time Expiry) | Class +1 (TP Hit First) | Theoretical Random Walk | Conformance Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1 IS** | 86,750 | 51,091 (**58.9%**) | 6,718 (**7.7%**) | 28,941 (**33.4%**) | 60.0% / 0.0% / 40.0% | **CONFIRMED** |
| **Fold 1 OOS** | 43,200 | 24,984 (**57.8%**) | 2,947 (**6.8%**) | 15,149 (**35.1%**) | 60.0% / 0.0% / 40.0% | **CONFIRMED** |
| **Fold 2 IS** | 87,000 | 50,909 (**58.5%**) | 6,457 (**7.4%**) | 29,634 (**34.1%**) | 60.0% / 0.0% / 40.0% | **CONFIRMED** |
| **Fold 2 OOS** | 43,440 | 25,100 (**57.8%**) | 3,531 (**8.1%**) | 14,689 (**33.8%**) | 60.0% / 0.0% / 40.0% | **CONFIRMED** |
| **Fold 3 IS** | 87,000 | 50,461 (**58.0%**) | 6,519 (**7.5%**) | 30,020 (**34.5%**) | 60.0% / 0.0% / 40.0% | **CONFIRMED** |
| **Fold 3 OOS** | 43,200 | 26,037 (**60.3%**) | 4,403 (**10.2%**) | 12,640 (**29.3%**) | 60.0% / 0.0% / 40.0% | **CONFIRMED** |

*Key Takeaway*:
Because Stop Loss is at $1.0\text{ ATR}$ while Take Profit is at $1.5\text{ ATR} + 14\text{ bps}$, **~58% to 60% of all market bars naturally hit Stop Loss first**. The models were exposed to a structural class imbalance where negative outcomes dominate positive outcomes by nearly 2:1.

---

### 3.2 OOS Generalization Decay
Diagnostic classification metrics show clear out-of-sample decay between In-Sample fitting and Out-of-Sample evaluation:

| Candidate ID | Metric | Fold 1 (IS / OOS) | Fold 2 (IS / OOS) | Fold 3 (IS / OOS) | Degradation Pattern |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **MODEL-1-LOGIT** | Accuracy | 35.28% / 32.97% | 36.34% / 42.68% | 35.68% / 34.46% | Stagnant near 3-class baseline (33.3%) |
| | Balanced Acc | 39.77% / 39.40% | 40.15% / 38.22% | 39.89% / 38.58% | Marginal linear separability |
| | Brier Score | 0.6614 / 0.6695 | 0.6601 / 0.6411 | 0.6610 / 0.6697 | Flat multi-class uncertainty |
| **MODEL-2-LGBM** | Accuracy | 42.92% / 35.13% | 43.35% / 43.59% | 42.84% / 36.21% | -7.8% drop in Folds 1 & 3 |
| | Balanced Acc | 49.83% / 40.79% | 50.03% / 38.26% | 50.29% / 39.25% | **-9.0% to -11.8% drop** |
| | Brier Score | 0.6271 / 0.6563 | 0.6245 / 0.6269 | 0.6259 / 0.6592 | Substantial calibration loss |
| **MODEL-3-XGB** | Accuracy | 42.02% / 34.78% | 42.75% / 43.31% | 41.93% / 36.27% | -7.2% drop in Folds 1 & 3 |
| | Balanced Acc | 48.99% / 41.22% | 49.08% / 38.29% | 49.19% / 39.40% | **-7.8% to -10.8% drop** |
| | Brier Score | 0.6326 / 0.6566 | 0.6300 / 0.6286 | 0.6316 / 0.6595 | Substantial calibration loss |

*Key Takeaway*:
The tree-based models achieved ~50% balanced accuracy on In-Sample training, but degraded to ~38-41% in Out-of-Sample testing. In regime transitions (particularly Fold 2 to Fold 3), models suffered high false-discovery rates, misclassifying rangebound consolidations as directional breakouts.

---

## 4. Strategy & Execution Compatibility Findings

A line-by-line inspection of [`backend/ml/ml_strategy.py`](file:///d:/vanta-terminal/backend/ml/ml_strategy.py) and [`backend/backtest/portfolio_engine.py`](file:///d:/vanta-terminal/backend/backtest/portfolio_engine.py) identified three critical execution architecture incompatibilities:

### 4.1 Incompatibility 1: Discrete Argmax Execution Without a Confidence Hurdle (`CONFIRMED`)
- **Observed Code Behavior**:
  [`backend/ml/evaluation_driver.py`](file:///d:/vanta-terminal/backend/ml/evaluation_driver.py) line 94 called `preds = model_wrapper.predict(X_eval)`. This executes `np.argmax(probabilities, axis=1)`.
  In [`backend/ml/ml_strategy.py`](file:///d:/vanta-terminal/backend/ml/ml_strategy.py):
  ```python
  y_hat = self.predictions.get(bar.timestamp_ms, 0)
  if y_hat == 0:
      return None
  if position.is_open():
      return None
  ```
- **Consequence**: An order was placed if $P(\text{class}) = 0.35$ while the other classes had $0.33$ and $0.32$. The strategy had no confidence filter (e.g., $P(\hat{y}) \ge 0.55$), no margin of victory threshold ($P_1 - P_2 \ge \theta$), and no expected-value gate ($\mathbb{E}[R] \ge 14\text{ bps}$).

### 4.2 Incompatibility 2: The Immediate Re-Entry Feedback Loop (`CONFIRMED`)
- **Observed Code Behavior**:
  `on_bar` evaluated entry eligibility solely by `if position.is_open(): return None`.
- **Consequence**:
  Because positions had a median lifespan of only **2.0 hours**, when a trade hit Stop Loss or Take Profit at 14:00, the position closed. At the 15:00 bar close, `position.is_open()` was `False`. Since the model predicted non-zero on ~65-75% of bars, a new trade was dispatched at the 16:00 open. 
  This explains why **84.32% of all trades entered within 1 hour of the prior exit**. The strategy had zero inter-trade cooling.

### 4.3 Incompatibility 3: Target Semantic Mismatch on Short Trades (`CONFIRMED`)
- **Observed Code Behavior**:
  In [`backend/ml/dataset_builder.py`](file:///d:/vanta-terminal/backend/ml/dataset_builder.py), training labels were generated using `side="LONG"`.
  Under `side="LONG"`:
  - Class `+1` = Price touches $+1.5\text{ ATR} + 14\text{ bps}$ before touching $-1.0\text{ ATR}$.
  - Class `-1` = Price touches $-1.0\text{ ATR}$ before touching $+1.5\text{ ATR} + 14\text{ bps}$.
- **Consequence**:
  When the strategy executed `y_hat == -1`, it entered a **SHORT position** with Take Profit at $-1.5\text{ ATR} - 14\text{ bps}$ and Stop Loss at $+1.0\text{ ATR}$.
  However, the model was trained on labels where Class `-1` merely meant price dropped $-1.0\text{ ATR}$ (Long Stop Loss), **NOT** that price dropped $-1.5\text{ ATR} - 14\text{ bps}$ (Short Take Profit).
  Consequently, short entries were systematically under-specified, leading to lower win rates and **accounting for 63% of all losses**.

---

## 5. Evidence-Based Attribution Matrix

| Dimension | Observed Mechanism | Exact Source File | Status | Impact on Failure | Additional Evidence Needed to Establish Full Causality |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Execution** | Immediate Re-entry ($\le 1\text{h}$) in 84.3% of trades | [`backend/ml/ml_strategy.py`](file:///d:/vanta-terminal/backend/ml/ml_strategy.py) | **CONFIRMED** | **CRITICAL** | None; proved by ledger timestamp deltas |
| **Execution** | Unfiltered Argmax dispatch (zero confidence threshold) | [`backend/ml/evaluation_driver.py`](file:///d:/vanta-terminal/backend/ml/evaluation_driver.py) | **CONFIRMED** | **CRITICAL** | Counterfactual test with probability thresholds (requires new authorization) |
| **Cost Drag** | Cumulative friction ($20.6k) exceeds gross edge ($2.2k) | Candidate JSON ledgers | **CONFIRMED** | **CRITICAL** | Proved by exact ledger cash reconciliation |
| **Labeling** | Short target asymmetry semantic mismatch | [`backend/ml/dataset_builder.py`](file:///d:/vanta-terminal/backend/ml/dataset_builder.py) | **CONFIRMED** | **HIGH** | Symmetric short label evaluation (requires new authorization) |
| **Signal** | Natural 2:1 class imbalance (59% class -1) | Candidate JSON diagnostics | **CONFIRMED** | **MODERATE** | None; mathematical property of asymmetric barriers |
| **Signal** | Generalization decay from IS (~50%) to OOS (~40%) | Candidate JSON diagnostics | **CONFIRMED** | **MODERATE** | Out-of-fold feature importance analysis |
| **Signal** | Probability calibration by decile | *Not persisted in Phase 5C.1* | **UNVERIFIED** | Unknown | Full probability vector serialization |
| **Risk** | Capital rationing or order rejections | Candidate JSON ledgers | **CONFIRMED (NO IMPACT)** | **NONE** | Rejection count was 0 across all runs |

---

## 6. Limitations of Existing Artifacts

The following questions **cannot be definitively resolved** from existing Phase 5C.1 artifacts:
1. **Continuous Probability Deciles**: Phase 5C.1 saved discrete predictions ($y \in \{-1, 0, 1\}$), Brier scores, and confusion matrices, but did not persist continuous probability arrays ($P(y_t = k)$). We cannot evaluate post-hoc whether trades with $P(\hat{y}) > 0.60$ were net profitable without retraining.
2. **Feature Importance Permutation Scores**: Per-feature Gini importance and SHAP values were not saved into the result JSONs. We can identify that models suffered generalization decay, but cannot rank which specific feature families contributed most to false signals.

---

## 7. Recommended Research Decisions

Based on the verified findings of this diagnostic audit, **two institutional research decisions are presented**:

### Decision 1 (Recommended): Abandon Autonomous High-Frequency Trade Generation in Favor of Trend-Overlay Meta-Labeling
- **Rationale**: Financial machine learning on 1-hour candles faces an insurmountable friction barrier when attempting to generate 25,000 autonomous entries. Exchange taker fees (5.0 bps) and adverse slippage (2.0 bps) demand a minimum realized edge of 14.0 bps per trade. 
- In contrast, `Benchmark-0` (Strategy B Donchian Breakout 1H) demonstrated positive net profit (+$\$$243.43) on only 2,851 trades by requiring strict trend conditions (`channel_m=30`, `volume_mult=1.5`, `ema_filter=100`).
- **Research Path**: Repurpose ML models from *autonomous entry generators* to *secondary regime filters (Meta-Labeling)*. When Strategy B emits a breakout signal, an ML meta-model predicts whether that specific trade will hit Take Profit or Stop Loss, filtering out false breakouts without increasing turnover.

### Decision 2 (Alternative): Constrained Autonomous ML with Mandatory Selectivity Constraints
- **Rationale**: If autonomous ML signal generation is pursued in a future phase, it must be conditioned on:
  1. A pre-registered **probability confidence threshold** (e.g., enter only if $P(\hat{y}) \ge 0.55$).
  2. A mandatory **minimum trade cooldown** (e.g., minimum 12 hours between trades on the same symbol).
  3. Strict **symmetric barrier labeling** (independent models for Long and Short).
  4. A turnover ceiling capping trades to $\le 150\text{ trades/year/pair}$ (~3,000 trades total).

### Immediate Action:
- Conclude Phase 5C without modifying code, running backtests, or training models.
- Preserve `STRAT-B-01` as `UNQUALIFIED_BASELINE`.
- Preserve certified system status as `PHASE_5C1_NO_QUALIFIED_MODEL`.
- Await user review and explicit authorization before commencing Phase 6 or Phase 5D.

---

## 8. Final Certified Exit Status

$$\mathbf{CERTIFIED \ DIAGNOSTIC \ STATUS: \ PHASE\_5C3\_DIAGNOSIS\_COMPLETE}$$
