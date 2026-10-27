# VANTA Terminal — Phase 5A Machine Learning Research Protocol

**Document ID**: `VANTA-DOCS-5A-ML-RESEARCH-PROTOCOL`  
**Protocol Version**: `1.0.0-FROZEN`  
**Execution Timestamp**: `2026-10-27T14:45:00Z`  
**Status**: `PROTOCOL_READY_FOR_APPROVAL`  
**Certified Benchmark Baseline**: `STRAT-B-01 (Donchian Breakout 1H) — UNQUALIFIED_BASELINE`  
**Global Qualification Status**: `NO_QUALIFIED_STRATEGY`  

---

## 1. Executive Summary & Research Mandate

Phase 5A establishes the formal, frozen Machine Learning research protocol for VANTA Terminal. Following the completion of the Phase 4B.5 benchmark revalidation, this protocol establishes the methodological, mathematical, and architectural boundaries for training, selecting, and evaluating supervised machine learning models.

### Core Research Mandate
> **Phase 5A is protocol design only.**  
> Zero model training, zero automated feature selection on historical out-of-sample data, zero hyperparameter grid searches, zero holdout evaluation, and zero benchmark executions are authorized in this phase.

### Primary Research Question
$$\text{Can a pre-registered, leakage-safe machine learning model produce reproducible incremental net performance}$$
$$\text{over the frozen Strategy B reference baseline after fees, slippage, shared-capital constraints, and mark-to-market risk?}$$

The objective is **not** to achieve high predictive accuracy ($R^2$ or ROC-AUC) in isolation. The objective is to determine whether supervised statistical learning can overcome the friction hurdles and risk constraints that caused all three rule-based candidates to fail institutional qualification in Phase 4B.5.

---

## 2. Certified Reference Baseline (Strategy B)

All Phase 5 machine learning candidate models will be compared directly against the frozen **`UNQUALIFIED_BASELINE`** ([`STRAT-B-01`](file:///d:/vanta-terminal/data/benchmarks/phase_4b5/STRAT_B_BENCHMARK.json)), whose performance was deterministically established under the [`CanonicalPortfolioEngine`](file:///d:/vanta-terminal/backend/backtest/portfolio_engine.py) in Phase 4B.5:

```
========================================================================================
STRATEGY B REFERENCE HURDLE BENCHMARK (Phase 4B.5 Revalidation)
========================================================================================
Strategy ID:                 STRAT-B-01 (Donchian Breakout / Trend Following — 1H)
Evaluation Folds:            OOS Folds 1-3 (2024-10-28 to 2026-04-26)
Total OOS Trades:            2,851 trades
Net PnL:                     +$243.43 (on $10,000 shared margin pool, +2.43% net)
Profit Factor (PF):          1.007
Net Expectancy per Trade:    +3.31 bps (95% CI: [-10.69, +17.31] bps)
Win Rate:                    25.53% (728 wins / 2,123 losses)
Candle-Level MTM MDD:        20.67% (Fold 1: 18.19%, Fold 2: 14.89%, Fold 3: 20.67%)
Closed-Trade MDD:            21.42% (Composite continuous closed equity)
Walk-Forward Consistency:    2 of 3 Folds Profitable (F1: +$1,352.67, F2: +$150.88, F3: -$1,260.12)
Spatial Robustness:          6 of 10 Eligible Pairs Profitable
Stress Net PnL (21.0 bps):   -$2,222.20 (Stress PF: 0.934)
Gates Passed / Failed:       3 Passed (GATE-4, 5, 6) / 5 Failed (GATE-1, 2, 3, 7, 8)
Designation:                 UNQUALIFIED_BASELINE
========================================================================================
```

### Incremental Performance Requirements ($\Delta_{\text{ML}}$)
To qualify as an improvement over the reference baseline, an ML candidate strategy must achieve:
1. $\Delta \text{Net PnL} = \text{Net PnL}_{\text{ML}} - \text{Net PnL}_{\text{StratB}} > 0$.
2. $\Delta \text{Expectancy} = \text{Expectancy}_{\text{ML}} - \text{Expectancy}_{\text{StratB}} > 0$.
3. $\text{MTM MDD}_{\text{ML}} \le 15.0\%$ (satisfying GATE-1, overcoming Strategy B's 20.67% breach).
4. Full compliance with all 8 frozen qualification gates.

---

## 3. Data Integrity & Quarantine Architecture

### 3.1 Universe and Datasets
The ML research protocol uses the 10 verified perpetual cryptocurrency futures datasets on HDD `D:\`:
- **10 Eligible Pairs**: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `XRPUSDT`, `ADAUSDT`, `AVAXUSDT`, `LINKUSDT`, `DOGEUSDT`, `LTCUSDT`.
- **Primary Research Timeframe**: **1-Hour (1H)** candles (derived from verified 15m Parquet data using gap-safe aggregation).
- **Auxiliary Observer**: `XMRUSDT` (partial history; strictly excluded from spatial denominators).

### 3.2 Data Partitions & Epistemological Status
Data is strictly segregated into three distinct partitions:

```
[======================= IN-SAMPLE TRAINING =======================] [====== EMBARGO ======] [=== HISTORICAL OOS ===] [======= QUARANTINED HOLDOUT =======]
  2023-10-26 00:00:00 UTC                           2024-10-24 00:00  2024-10-26    2024-10-28 2026-04-26 00:00:00 UTC 2026-10-26 00:00:00 UTC
                                                        (Purge)            (Embargo)
  [Training & Model Fitting]                                          [PREVIOUSLY_SEEN_OOS]    [ABSOLUTE QUARANTINE - NO ACCESS]
```

1. **Partition 1: In-Sample Training & Selection**:
   - Dates: `2023-10-26T00:00:00Z` to fold purge boundary.
   - Usage: Feature engineering fitting (scalers/encoders), model training, internal cross-validation / validation slices.
2. **Partition 2: Previously Seen Historical Out-of-Sample (`PREVIOUSLY_SEEN_HISTORICAL_EVALUATION`)**:
   - Dates: `2024-10-28T00:00:00Z` to `2026-04-26T00:00:00Z` (across Folds 1, 2, and 3).
   - Epistemological Classification: **Contaminated / Previously Observed**.
   - Mandatory Disclosure: These periods were evaluated during Phase 4B and Phase 4B.5. Because the research team has observed the aggregate market regime and Strategy B's performance over these dates, **Partition 2 cannot be claimed as an untouched virgin test set**. Performance on Partition 2 will be reported with explicit acknowledgement of potential historical selection bias.
3. **Partition 3: Universal Quarantined Holdout**:
   - Range: `open_time >= 1777161600000` (`2026-04-26T00:00:00Z` to `2026-10-26T00:00:00Z`).
   - Status: **Strictly Quarantined**. Zero feature generation, zero model inference, zero inspection, zero tuning. Preserved intact for Phase 6 final certification.

---

## 4. Prediction Targets & Labeling Specification

We specify three candidate target formulations for comparative evaluation. The selection of the primary target is frozen prior to model fitting.

```
+-----------------------------------------------------------------------------------------------------+
| TARGET FORMULATION SUMMARY                                                                          |
+-------------------+----------------------------+----------------------------------------------------+
| Target Identifier | Type                       | Mathematical Formulation                           |
+-------------------+----------------------------+----------------------------------------------------+
| TARGET-A-DIR      | Binary Direction           | y_t = 1 if r_{t, t+H} > 0 else 0                  |
| TARGET-B-RET      | Forward Return Regression  | y_t = ln(P_{t+H} / P_t)                            |
| TARGET-C-BARRIER  | Cost-Aware Triple Barrier  | y_t in {+1, 0, -1} subject to friction hurdle theta|
+-------------------+----------------------------+----------------------------------------------------+
```

### 4.1 Target Formulation Trade-offs

#### Target A: Next-Period / Multi-Period Direction Classification (`TARGET-A-DIR`)
- **Formula**: $y_t = \mathbb{I}\left(P_{t+H} > P_t\right)$.
- **Advantage**: Simple, well-calibrated probabilistic outputs ($p \in [0, 1]$), standard log-loss objective.
- **Disadvantage**: Economically agnostic. A +1 bps move is treated identically to a +300 bps move. Produces many false-positive trade signals where gross gain is smaller than round-trip transaction costs (14.0 bps).

#### Target B: Forward Return Regression (`TARGET-B-RET`)
- **Formula**: $y_t = \ln\left(\frac{P_{t+H}}{P_t}\right)$.
- **Advantage**: Directly predicts return magnitude; allows dynamic position sizing or thresholding ($\hat{y}_t > \text{hurdle}$).
- **Disadvantage**: Outliers and extreme volatility spikes disproportionately dominate MSE loss; regression models often shrink predictions toward zero in noisy regimes.

#### Target C: Cost-Aware Barrier Target (`TARGET-C-BARRIER` — Recommended Primary Target)
- **Formula**: Evaluates the path of price over forward window $h \in [1, H]$ against an upper hurdle $\theta_{\text{profit}}$, a lower stop-loss $\theta_{\text{stop}}$, and a holding horizon $H$:
  $$y_t = \begin{cases} 
  +1 & \text{if } \max_{h \in [1, H]} \left(\frac{P_{t+h} - P_t}{P_t}\right) \ge \theta_{\text{profit}} \text{ before stop touched} \\
  -1 & \text{if } \min_{h \in [1, H]} \left(\frac{P_{t+h} - P_t}{P_t}\right) \le -\theta_{\text{stop}} \text{ before profit touched} \\
  0 & \text{if neither barrier touched within horizon } H \text{ (time expiry)}
  \end{cases}$$
- **Hurdle Calibration**:
  - $\theta_{\text{profit}} = 1.5 \times \text{ATR}_{14}(t) / P_t + \text{Cost Hurdle}$, where $\text{Cost Hurdle} = 0.0014$ (14.0 bps baseline round-trip friction).
  - $\theta_{\text{stop}} = 1.0 \times \text{ATR}_{14}(t) / P_t$.
  - Horizon $H = 12$ bars (12 hours on 1H timeframe).
- **Advantage**: Embeds execution friction, risk-reward asymmetry, and maximum holding time directly into the label generation. Eliminates trades that cannot overcome transaction costs.

### 4.2 Leakage-Safe Labeling Rules
1. **Timestamp Alignment**: Feature vector $\mathbf{x}_t$ is computed strictly using candles up to bar $t$ (bar close timestamp $t_{\text{close}}$).
2. **Execution Timing**: Any order triggered by prediction $\hat{y}_t$ fills at bar $t+1$ **Open** with adverse slippage (2.0 bps baseline, 3.0 bps stress).
3. **Purge Duration**: For forward horizon $H$, training labels overlap forward in time. To prevent training label leakage into evaluation folds, the purge buffer must strictly satisfy:
   $$\text{Purge Buffer} \ge H \times \Delta t_{\text{bar}} + \text{Max Holding Period} = 12\text{h} + 48\text{h} = 60\text{ hours}$$
   The frozen walk-forward purge of **48 hours** requires capping the maximum forward horizon at $H \le 12\text{ hours}$ and maximum trade holding period at **36 hours**, ensuring $\text{Total Overlap} \le 48\text{ hours}$.

---

## 5. Model Arena Architecture

To prevent data mining and p-hacking, the model arena is restricted to three pre-registered model families:

```
+-------------------------------------------------------------------------------------------------------+
| MODEL ARENA SPECIFICATION                                                                             |
+-------------------+----------------------------+-----------------------+------------------------------+
| Model Class       | Architecture               | Regularization        | Purpose                      |
+-------------------+----------------------------+-----------------------+------------------------------+
| BENCHMARK-0       | STRAT-B-01 (Donchian 1H)   | Frozen Parameters     | Non-ML Reference Hurdle      |
| MODEL-1-LOGIT     | Regularized Logistic / L2  | L2 penalty (C=0.1)    | Transparent Linear Reference |
| MODEL-2-LGBM      | Gradient Boosted Trees     | Depth 4, Leaves 15    | Nonlinear Interaction Model  |
| MODEL-3-XGB       | Extreme Gradient Boosting  | Depth 4, Min Child 50 | Tree Verification Reference  |
+-------------------+----------------------------+-----------------------+------------------------------+
```

### 5.1 Model Specifications

#### 1. Linear Reference: Regularized Logistic Regression (`MODEL-1-LOGIT`)
- **Library**: `scikit-learn` (`LogisticRegression`).
- **Penalty**: L2 (`penalty='l2'`).
- **Regularization Strength**: $C \in \{0.01, 0.1, 1.0\}$ (selected strictly on IS validation fold).
- **Solver**: `lbfgs` with `max_iter=1000`.
- **Scaling Requirement**: Features scaled using `RobustScaler` fitted exclusively on the In-Sample training slice.

#### 2. Primary Nonlinear Model: LightGBM (`MODEL-2-LGBM`)
- **Library**: `lightgbm` (`LGBMClassifier` / `LGBMRegressor`).
- **Tree Constraints**: `max_depth=4`, `num_leaves=15`, `min_child_samples=50`.
- **Subsampling & Regularization**:
  - `subsample=0.8` (row subsampling without replacement).
  - `colsample_bytree=0.8` (feature subsampling per tree).
  - `reg_alpha=0.1` (L1 leaf regularization).
  - `reg_lambda=1.0` (L2 leaf regularization).
- **Learning Dynamics**: `learning_rate=0.03`, `n_estimators=300`.
- **Early Stopping**: Early stopping patience of 25 rounds evaluated on an internal In-Sample validation split (last 20% of In-Sample slice).

#### 3. Verification Tree Model: XGBoost (`MODEL-3-XGB`)
- **Library**: `xgboost` (`XGBClassifier` / `XGBRegressor`).
- **Constraints**: `max_depth=4`, `min_child_weight=50`, `subsample=0.8`, `colsample_bytree=0.8`, `reg_alpha=0.1`, `reg_lambda=1.0`, `learning_rate=0.03`.

### 5.2 Training Objectives & Class Imbalance
- For classification models, classes may exhibit imbalance (e.g. fewer strong breakout moves than neutral periods).
- **Weighting Policy**: Balanced class weighting applied deterministically:
  $$w_c = \frac{N}{K \cdot N_c}$$
- **RNG Seeds**: Fixed seed `42` for all train-test splits, feature sampling, and tree building.
- **Hardware & Concurrency Constraints**:
  - CPU-only execution (`n_jobs=4`).
  - Max RAM budget: $\le 4.0\text{ GB}$.
  - Execution time budget: $\le 5\text{ minutes}$ per fold training run.

---

## 6. Leakage-Safe Chronological Validation Protocol

Validation follows the frozen Walk-Forward schedule established in Phase 4A/4B, augmented with strict ML-specific isolation controls:

```
========================================================================================
WALK-FORWARD ML EVALUATION SCHEDULE
========================================================================================
Fold 1:
  In-Sample Training:       2023-10-26 00:00:00 UTC to 2024-10-24 00:00:00 UTC
  Purge Window:             2024-10-24 00:00:00 UTC to 2024-10-26 00:00:00 UTC (48h)
  Embargo Warmup:           2024-10-26 00:00:00 UTC to 2024-10-28 00:00:00 UTC (48h)
  OOS Evaluation:           2024-10-28 00:00:00 UTC to 2025-04-26 00:00:00 UTC (6 months)

Fold 2:
  In-Sample Training:       2024-04-26 00:00:00 UTC to 2025-04-24 00:00:00 UTC
  Purge Window:             2025-04-24 00:00:00 UTC to 2025-04-26 00:00:00 UTC (48h)
  Embargo Warmup:           2025-04-26 00:00:00 UTC to 2025-04-28 00:00:00 UTC (48h)
  OOS Evaluation:           2025-04-28 00:00:00 UTC to 2025-10-26 00:00:00 UTC (6 months)

Fold 3:
  In-Sample Training:       2024-10-26 00:00:00 UTC to 2025-10-24 00:00:00 UTC
  Purge Window:             2025-10-24 00:00:00 UTC to 2025-10-26 00:00:00 UTC (48h)
  Embargo Warmup:           2025-10-26 00:00:00 UTC to 2025-10-28 00:00:00 UTC (48h)
  OOS Evaluation:           2025-10-28 00:00:00 UTC to 2026-04-26 00:00:00 UTC (6 months)
========================================================================================
```

### Isolation Mandates
1. **Pipeline Encapsulation**: Any transformation requiring fitting (e.g., centering, scaling, quantile clipping) must be fitted on the In-Sample slice only. Calling `.fit()` or `.fit_transform()` on OOS data is a fatal protocol breach.
2. **Cross-Sectional Synchronization**: When calculating cross-sectional features (e.g., pair relative strength relative to universe median), all 10 pairs must be synchronized on timestamp $t$. If a bar is missing for pair $j$, its value is imputed from its last observed bar $t-1$; future bars are never used.
3. **No Random Shuffling**: K-fold cross-validation with random shuffling is strictly forbidden for time series.

---

## 7. Portfolio-Level Execution & Accounting Semantics

All ML candidate models will be integrated into the [`CanonicalPortfolioEngine`](file:///d:/vanta-terminal/backend/backtest/portfolio_engine.py). Synthetic sub-account aggregation is strictly prohibited.

### Accounting Invariants
- **Initial Capital**: Clean **$10,000.00** cash reset per fold.
- **Position Sizing**: Target position size = **10.0% of current portfolio equity** ($E_t$).
- **Gross Leverage Cap**: **1.0x unleveraged futures** ($\sum \text{Notional} \le E_t$).
- **Simultaneous Positions**: Up to 10 positions across the 10 eligible pairs.
- **Capital Rationing**: When free collateral is insufficient, pending entry orders are rejected deterministically and logged as `INSUFFICIENT_COLLATERAL`.
- **Friction Models**:
  - Baseline: 5.0 bps taker fee + 2.0 bps adverse slippage per side (**14.0 bps round-trip**).
  - Stress Replacement: 7.5 bps taker fee + 3.0 bps adverse slippage per side (**21.0 bps round-trip**).
- **Execution Policy**: `ExecutionPolicy.CONSERVATIVE_SL_FIRST` with gap-through-stop fill accounting.
- **Boundary Handling**: All open positions force-flattened at fold close (`BOUNDARY_FLAT`).

---

## 8. Frozen Qualification Gates & Dual MDD Definition

All 8 qualification gates from the frozen Phase 4A/4B protocol are preserved. No threshold may be altered to accommodate ML models:

```
========================================================================================
FROZEN QUALIFICATION GATES (Phase 5 Standard)
========================================================================================
GATE-1: Maximum Drawdown (MDD)               <= 15.0%        Continuous MTM Equity Curve
GATE-2: Net Expectancy per Trade             >= +8.0 bps     Aggregate OOS Trades
GATE-3: Profit Factor (PF)                   >= 1.25         Net Realized Returns
GATE-4: Aggregate Trade Count                >= 150 trades   10 Qualified Pairs (OOS 1-3)
GATE-5: Per-Pair Minimum Activity            >= 20 trades    All 10 Qualified Pairs
GATE-6: Walk-Forward Consistency             >= 2 of 3 Folds Net Profitable Folds
GATE-7: Spatial Robustness                   >= 7 of 10 Pairs Net Profitable Pairs
GATE-8: Friction Stress Tolerance (21 bps)   Net PnL > $0    PF > 1.0 at 21.0 bps
========================================================================================
```

### Pre-Registered Dual Definition of GATE-1 (Maximum Drawdown)
To reconcile single-pool fold resets with continuous risk assessment, GATE-1 is explicitly defined as requiring **both**:
1. **Per-Fold MTM MDD**: $\text{MDD}_f \le 15.0\%$ in **every** evaluated fold ($f \in \{1, 2, 3\}$). A single fold breaching 15.0% constitutes an immediate GATE-1 failure.
2. **Combined Walk-Forward MTM MDD**: $\text{MDD}_{\text{combined}} \le 15.0\%$, calculated across the composite chained equity curve:
   $$E_{\text{composite}}(t) = E_1(t) \cdot \prod_{k=2}^f \left(1 + R_k\right)$$
Both metrics must be reported side-by-side in all Phase 5 manifests.

---

## 9. Deliverables and Pre-Registration Commitments

The Phase 5A documentation suite consists of:
1. `docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md` (this document).
2. `docs/PHASE_5A_FEATURE_CATALOG.md` (exact mathematical feature formulations, lookbacks, and proofs of zero lookahead).
3. `docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md` (block bootstrap, statistical inference, and accounting specs).
4. `data/experiments/phase_5a/protocol_manifest.json` (machine-readable configuration hashes, schemas, and frozen parameters).

### Exit Status
**`PROTOCOL_READY_FOR_APPROVAL`**

Execution of model training, feature generation, or Phase 5B benchmarking is halted pending explicit user review and authorization.
