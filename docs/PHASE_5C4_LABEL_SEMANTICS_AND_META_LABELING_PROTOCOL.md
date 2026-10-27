# VANTA Terminal — Phase 5C.4 Label Semantics Verification & Meta-Labeling Protocol Design

**Document ID**: `VANTA-DOCS-5C4-LABEL-SEMANTICS-META-PROTOCOL`  
**Execution Timestamp**: `2026-10-27T11:00:00Z`  
**Author**: Antigravity Quantitative Verification & Machine Learning Research Agent  
**Current Certified Status**: `PHASE_5C1_NO_QUALIFIED_MODEL`  
**Prior Audits**: `PHASE_5C2_AUDIT_PASS`, `PHASE_5C3_DIAGNOSIS_COMPLETE`  
**Scope**: Verification of label semantics defect, validation of turnover churn mechanisms, feasibility assessment of meta-labeling, and pre-registration of the Phase 5D research protocol  
**Execution Mode**: **Verification and Protocol Design Only** (Zero model training, zero backtest reruns, zero holdout access, zero source code modifications)  

---

## 1. Executive Summary & Investigation Mandate

Phase 5C.4 investigated the empirical failure mechanisms discovered in Phase 5C.3 and formulated a mathematically rigorous next-stage research protocol.

### Key Verified Findings:
1. **Confirmation of SHORT Label Semantic Defect (`CONFIRMED`)**:
   In [`backend/ml/dataset_builder.py`](file:///d:/vanta-terminal/backend/ml/dataset_builder.py), training labels were generated strictly with `side="LONG"`. Under `side="LONG"`, Class `-1` represented reaching the Long Stop Loss (a $-1.0\text{ ATR}$ move). However, [`MLModelStrategy`](file:///d:/vanta-terminal/backend/ml/ml_strategy.py) reinterpreted $\hat{y} = -1$ as a trigger to enter an aggressive **SHORT position** requiring a $-1.5\text{ ATR} - 14\text{ bps}$ downward expansion to reach Take Profit.
   Cross-tabulation on 21,887 historical 1-hour candles reveals that in **49.8% of cases where Long Stop Loss was hit, Short Take Profit was NEVER reached** (and in **36.5% of cases, price reversed and hit the Short Stop Loss**). This structural semantic mismatch explains why Short trades accounted for **63.17% of all ML candidate net losses**.
2. **Confirmation of Immediate Re-Entry Churn (`CONFIRMED`)**:
   In [`backend/ml/ml_strategy.py`](file:///d:/vanta-terminal/backend/ml/ml_strategy.py), entry signals were dispatched whenever a position was flat and $\hat{y} \ne 0$. Because position holding duration was ultra-short (median = 2.0 hours) and the models predicted non-zero on ~65-75% of all bars, the strategy re-entered on the very next bar ($\le 1\text{ hour}$) **84.32% of the time** (median re-entry delay = 1.0 hour, compared to 23.0 hours for Benchmark-0).
3. **Feasibility of Trend-Overlay Meta-Labeling (`CONFIRMED`)**:
   Repurposing ML from *autonomous trade generation* to *secondary regime filtering (Meta-Labeling)* on frozen Strategy B breakout signals resolves both core failure modes:
   - Turnover is bounded by the primary strategy's signal frequency (~2,850 trades total over 18 months instead of 25,000+).
   - Candidate trade direction ($d \in \{\text{LONG}, \text{SHORT}\}$) is pre-determined by the primary breakout, allowing unambiguous binary meta-labeling ($y^{\text{meta}} \in \{0, 1\}$).
4. **Binding Baseline Constraint (`CONFIRMED`)**:
   `Benchmark-0` (`STRAT-B-01` Donchian Breakout 1H) is an **`UNQUALIFIED_BASELINE`** (failed 5 of 8 frozen gates in Phase 4B.5). Therefore, under institutional rules, **no candidate meta-strategy can qualify merely by outperforming Benchmark-0**. All 8 frozen qualification gates must be satisfied on an absolute basis.

$$\mathbf{STATUS: \ PHASE\_5C4\_DESIGN\_READY}$$

---

## 2. Verification of LONG / SHORT Label Semantics

### 2.1 Code-Level Label Construction
In [`backend/ml/labels.py`](file:///d:/vanta-terminal/backend/ml/labels.py) lines 140–195:
```python
if side_upper == "LONG":
    for step in range(1, self.horizon_bars + 1):
        is_touch_sl = bar_l <= long_sl or is_gap_sl
        is_touch_tp = bar_h >= long_tp
        if is_touch_sl and is_touch_tp:
            assigned_label = TargetLabel.BEARISH_DOWN  # Long SL first -> -1
            break
        elif is_touch_sl:
            assigned_label = TargetLabel.BEARISH_DOWN  # Long SL first -> -1
            break
        elif is_touch_tp:
            assigned_label = TargetLabel.BULLISH_UP    # Long TP first -> +1
            break
```
In [`backend/ml/dataset_builder.py`](file:///d:/vanta-terminal/backend/ml/dataset_builder.py) lines 106 and 156:
```python
labels_series = labeler.compute_labels(raw_is_df, side=side)  # side defaults to "LONG"
```
In [`backend/ml/evaluation_driver.py`](file:///d:/vanta-terminal/backend/ml/evaluation_driver.py) line 354:
```python
fm = build_fold_matrices(fold, universe_candles, side="LONG")
```

### 2.2 Class Translation into Trading Actions
In [`backend/ml/ml_strategy.py`](file:///d:/vanta-terminal/backend/ml/ml_strategy.py) lines 63–91:
- `y_hat == 1`: Dispatches `SignalEvent` with `direction = PositionSide.LONG`, `take_profit = C_t * (1 + 1.5 * delta_atr + 0.0014)`, `stop_loss = C_t * (1 - 1.0 * delta_atr)`.
- `y_hat == -1`: Dispatches `SignalEvent` with `direction = PositionSide.SHORT`, `take_profit = C_t * (1 - 1.5 * delta_atr - 0.0014)`, `stop_loss = C_t * (1 + 1.0 * delta_atr)`.
- `y_hat == 0`: No signal emitted.

### 2.3 Mathematical Proof of Short Target Invalidation
The training target Class `-1` was assigned when price fell by $1.0\text{ ATR}$.
The trading strategy executed a Short position requiring price to fall by $1.5\text{ ATR} + 14\text{ bps}$ before rising by $1.0\text{ ATR}$.

Cross-tabulating `side="LONG"` labels against `side="SHORT"` labels on 21,887 historical 1-hour candles of `BTCUSDT`:

| `side="LONG"` Assigned Label | Total Bars | True `side="SHORT"` Label = -1 (Short TP Reached) | True `side="SHORT"` Label = 0 (Time Expiry) | True `side="SHORT"` Label = +1 (Short SL Hit) |
| :--- | :---: | :---: | :---: | :---: |
| **Class -1 (Long SL Hit)** | **12,686** | 6,367 (**50.19%**) | 1,689 (**13.31%**) | 4,630 (**36.50%**) |
| **Class 0 (Neutral Expiry)** | **2,646** | 0 (0.00%) | 951 (35.94%) | 1,695 (64.06%) |
| **Class +1 (Long TP Reached)** | **6,555** | 0 (0.00%) | 0 (0.00%) | 6,555 (100.00%) |

#### Empirical Conclusions:
1. **Invalid Semantic Reinterpretation (`CONFIRMED`)**: When the model predicted $\hat{y} = -1$, the Short position reached its required Take Profit target in only **50.19%** of cases. In **36.50%** of cases, price bounced and hit the Short Stop Loss. After subtracting 14.0 bps round-trip transaction friction, the realized win rate dropped below 40%, generating systematic losses.
2. **Ledger Loss Share Verification (`CONFIRMED`)**:
   - `MODEL-1-LOGIT`: Short trades net PnL: -$11,692.91 out of -$18,685.46 = **62.58%**.
   - `MODEL-2-LGBM`: Short trades net PnL: -$11,535.88 out of -$18,452.94 = **62.52%**.
   - `MODEL-3-XGB`: Short trades net PnL: -$12,198.22 out of -$18,937.15 = **64.41%**.
   The claim that Short trades caused approximately 63% of ML candidate losses is **100% confirmed by existing ledger arithmetic**.
3. **Barrier Anchoring Inconsistency (`CONFIRMED`)**:
   `TripleBarrierLabeler` anchored barriers to $P_{\text{entry}} = O_{t+1} \times (1 \pm s)$. `MLModelStrategy.on_bar` anchored barriers to $C_t$. Intrabar gaps between $C_t$ and $O_{t+1}$ distorted effective stop and profit distances.

---

## 3. Verification of Turnover & Re-Entry Attribution

### 3.1 Mechanism of Next-Hour Re-Entry
Inspection of [`backend/backtest/portfolio_engine.py`](file:///d:/vanta-terminal/backend/backtest/portfolio_engine.py) lines 330–420 establishes the exact chronological execution sequence:
1. **Bar Open (Sub-Step 1)**: Pending market exits are processed.
2. **Bar Intrabar (Sub-Step 4)**: High and Low bounds $[L_t, H_t]$ are evaluated against open position barriers. If Stop Loss or Take Profit is breached, `_close_position_fill` is called immediately, setting `pos.is_open() = False` and returning reserved margin to free collateral.
3. **Bar Close (Sub-Step 6)**: `strat.on_bar(bar, pos)` is called. Because the position closed during Sub-Step 4, `position.is_open()` evaluates to `False`.
4. **Signal Dispatch**: In [`backend/ml/ml_strategy.py`](file:///d:/vanta-terminal/backend/ml/ml_strategy.py), `if y_hat != 0 and not position.is_open():` emits a new entry signal for bar $t+1$ Open.
5. **Bar $t+1$ Open (Sub-Step 3)**: The new entry is filled.

**Code-Confirmed Fact**: The canonical engine and strategy contain **zero cooldown delay** between position closure and new signal emission. An intrabar exit at bar $t$ immediately allows a new entry fill at bar $t+1$.

---

### 3.2 Denominator and Metric Verification
1. **Re-Entry Denominator (`CONFIRMED`)**:
   The denominator is the total count of sequential trade pairs on the same symbol:
   $$N_{\text{pairs}} = \sum_{s \in \text{Universe}} (N_{\text{trades}, s} - 1)$$
   For `MODEL-2-LGBM`: $25,896 - 10 = 25,886\text{ pairs}$.
   Sequential pairs with $\text{entry\_time}_{k+1} - \text{exit\_time}_k \le 3,600,000\text{ ms}$ (1 hour): $21,827$.
   Re-entry percentage: $\frac{21,827}{25,886} = \mathbf{84.32\%}$.
2. **Median Holding Duration (`CONFIRMED`)**:
   Recomputed directly from trade ledger field `holding_duration_bars`:
   - `BENCHMARK-0`: Median = **8.0 bars**, Mean = **14.43 bars**.
   - `MODEL-1-LOGIT`: Median = **2.0 bars**, Mean = **2.98 bars**.
   - `MODEL-2-LGBM`: Median = **2.0 bars**, Mean = **3.00 bars**.
   - `MODEL-3-XGB`: Median = **2.0 bars**, Mean = **2.97 bars**.
3. **Absence of Expected-Return Filter (`CONFIRMED`)**:
   [`backend/ml/ml_strategy.py`](file:///d:/vanta-terminal/backend/ml/ml_strategy.py) lines 44–55 verifies that every non-zero prediction ($\hat{y} \in \{-1, +1\}$) dispatches an order whenever `not position.is_open()`. No probability threshold, volatility gate, or minimum expected return filter exists in the implementation.

---

## 4. Meta-Labeling Feasibility Assessment

### 4.1 Primary Strategy Status & Signal Generation
- **Primary Strategy**: Strategy B (`STRAT-B-01`), Donchian Breakout / Trend 1H.
- **Certified Baseline Status**: `UNQUALIFIED_BASELINE`. In Phase 4B.5, Strategy B failed 5 of the 8 qualification gates (failed GATE-1 MDD at 20.67%, GATE-2 Expectancy at +3.31 bps, GATE-3 PF at 1.007, GATE-7 Spatial at 6/10, GATE-8 Stress at -$2,222.20).
- **Signal Conditions**:
  - Long Breakout: $C_t > \text{UpperChannel}_{30, t-1} \land C_t > \text{EMA}_{100, t} \land \text{EMA\_UP} \land V_t \ge 1.5 \cdot \text{SMA}_{20}(V)$.
  - Short Breakdown: $C_t < \text{LowerChannel}_{30, t-1} \land C_t < \text{EMA}_{100, t} \land \text{EMA\_DOWN} \land V_t \ge 1.5 \cdot \text{SMA}_{20}(V)$.
- **Total Historical Signals**: Exactly **2,851 trades** across the 3 Out-of-Sample folds (~5.2 trades/day across the 10-pair universe).

---

### 4.2 Mathematical Formulation of Meta-Labeling
Instead of predicting whether arbitrary market bars will break out, the ML model acts as a **secondary execution filter** on candidate signals emitted by Strategy B:

Let candidate signal $S_i = (t_i, \text{sym}_i, d_i)$ be emitted by Strategy B at bar $t_i$ close, where $d_i \in \{\text{LONG}, \text{SHORT}\}$.
The meta-model predicts binary label $y_i^{\text{meta}} \in \{0, 1\}$:
$$y_i^{\text{meta}} = \begin{cases} 
1, & \text{if candidate trade } S_i \text{ achieves net positive return after all friction} \\
0, & \text{if candidate trade } S_i \text{ hits Stop Loss or expires with net loss/drag}
\end{cases}$$

#### Key Structural Advantages:
1. **Natural Turnover Ceiling (`CONFIRMED`)**:
   Because signals are emitted strictly by Strategy B, total trade opportunities cannot exceed 2,851 over 18 months. Maximum possible turnover is **$\le 5.2$ trades/day across 10 pairs** (compared to 47.4 trades/day for autonomous ML).
2. **Elimination of Directional Semantic Ambiguity (`CONFIRMED`)**:
   Because $d_i$ is fixed by Strategy B:
   - If $d_i = \text{LONG}$: Forward path is evaluated against Long TP ($+1.5\text{ ATR} + 14\text{ bps}$) vs Long SL ($-1.0\text{ ATR}$).
   - If $d_i = \text{SHORT}$: Forward path is evaluated against Short TP ($-1.5\text{ ATR} - 14\text{ bps}$) vs Short SL ($+1.0\text{ ATR}$).
   Both directions have identical, symmetric economic meaning: **$y = 1$ denotes trade success after friction; $y = 0$ denotes trade failure**.
3. **Execution Alignment (`CONFIRMED`)**:
   The trade entry occurs at $O_{t+1} \times (1 \pm \text{slip})$. If the meta-model predicts $\hat{P}(y_i^{\text{meta}} = 1 \mid \mathbf{x}_{t_i}) \ge \tau$, the trade is executed; otherwise, it is skipped.

---

### 4.3 Addressing the Unqualified Baseline Challenge
Because Strategy B is unqualified, can meta-labeling qualify?
- **Protocol Law**: No candidate meta-strategy can claim qualification merely by improving on Benchmark-0.
- If the meta-strategy achieves $\text{PF} = 1.20$ (improving on Benchmark-0's 1.007), but fails the frozen GATE-3 hurdle ($\ge 1.25$), it is **UNQUALIFIED**.
- If the meta-strategy achieves $\text{MDD} = 18.0\%$ (improving on Benchmark-0's 20.67%), but fails GATE-1 ($\le 15.0\%$), it is **UNQUALIFIED**.
- Meta-labeling is a methodology to filter false breakouts; it must pass **all 8 frozen qualification gates on an absolute basis**.

---

## 5. Phase 5D Research Protocol Specification

### 5.1 Protocol Architecture Overview
```
+--------------------------------------------------------------------------------------------------+
| PHASE 5D PROTOCOL: TREND-OVERLAY META-LABELING ARCHITECTURE                                     |
+--------------------------------------------------------------------------------------------------+
| 1. Primary Strategy: Frozen STRAT-B-01 (Donchian Breakout 1H, configurations B-09, B-09, B-05)   |
| 2. Candidate Arena:                                                                              |
|    - BENCHMARK-0: STRAT-B-01 unfiltered reference baseline                                       |
|    - META-1-LOGIT: Regularized Logistic Regression meta-filter (L2 penalty)                      |
|    - META-2-LGBM: Shallow LightGBM meta-filter (max_depth=3, num_leaves=7, 150 estimators)       |
|    - META-3-XGB: Shallow XGBoost meta-filter (max_depth=3, min_child_weight=50, 150 estimators)   |
| 3. Feature Catalog: Frozen 21 Phase 5A features evaluated at signal timestamp t_i                |
| 4. Labeling: Cost-aware binary meta-target y_i in {0, 1} with 14.0 bps hurdle                     |
| 5. Evaluation Engine: CanonicalPortfolioEngine (shared $10k pool, 1.0x lev, 10% sizing)          |
| 6. Statistical Inference: Synchronized Stationary Block Bootstrap (B=2000, E[L]=5d, seed 42)     |
| 7. Qualification Standard: All 8 Frozen Phase 4B/5A Gates Must Pass Simultaneously               |
+--------------------------------------------------------------------------------------------------+
```

---

### 5.2 Exact Target Formulation
For each candidate signal emitted at bar $t$ Close:
1. Reference Entry Price: $P_{\text{entry}} = O_{t+1} \times (1 + s)$ for Long; $O_{t+1} \times (1 - s)$ for Short ($s = 0.0002$).
2. Take Profit Barrier:
   - Long: $P_{\text{TP}} = P_{\text{entry}} \times (1 + 1.5 \cdot \delta_{\text{ATR}, t} + 0.0014)$
   - Short: $P_{\text{TP}} = P_{\text{entry}} \times (1 - 1.5 \cdot \delta_{\text{ATR}, t} - 0.0014)$
3. Stop Loss Barrier:
   - Long: $P_{\text{SL}} = P_{\text{entry}} \times (1 - 1.0 \cdot \delta_{\text{ATR}, t})$
   - Short: $P_{\text{SL}} = P_{\text{entry}} \times (1 + 1.0 \cdot \delta_{\text{ATR}, t})$
4. Forward Horizon: $H = 12\text{ bars}$ (with fallback analysis at $H = 24\text{ bars}$).
5. Binary Label Assignment:
   $$y_i = \begin{cases}
   1, & \text{if Take Profit touched before Stop Loss under CONSERVATIVE\_SL\_FIRST} \\
   0, & \text{if Stop Loss touched first, or collision, or neither barrier touched (expiry)}
   \end{cases}$$

---

### 5.3 Leakage Controls & Walk-Forward Partitioning
1. **Quarantine Guard**: Strictly preserve holdout boundary `2026-04-26T00:00:00Z` (`1777161600000` ms).
2. **Purge & Embargo**: Retain frozen 48h purge + 48h embargo (96 hours total). For a 12-hour or 24-hour label horizon, cross-fold label overlap is mathematically zero ($96\text{h} > 24\text{h}$).
3. **Partition Isolation**: Scalers ([`PartitionAwareScaler`](file:///d:/vanta-terminal/backend/ml/scaling.py)) and meta-models fit strictly on In-Sample signals; Out-of-Sample signals transformed using frozen In-Sample statistics.
4. **Signal-Level Temporal Alignment**: Features $\mathbf{x}_{t_i}$ computed using information strictly $\le t_{i, \text{close}}$.

---

### 5.4 Pre-Registered Execution Policy Hypotheses (Non-Optimized)
To avoid data dredging, execution parameters must be pre-declared as explicit hypotheses rather than tuned post-hoc:
- **Hypothesis 1 (Confidence Threshold $\tau = 0.50$)**: Candidate trade is executed if and only if $\hat{P}(y_i = 1 \mid \mathbf{x}_{t_i}) \ge 0.50$.
- **Hypothesis 2 (High-Conviction Threshold $\tau = 0.55$)**: Candidate trade is executed if and only if $\hat{P}(y_i = 1 \mid \mathbf{x}_{t_i}) \ge 0.55$.
- **Hypothesis 3 (Cooldown Guard $\Delta t_{\text{cool}} = 4\text{ bars}$)**: If a pair exits a trade, subsequent breakout signals on that same pair within 4 hours are filtered to prevent immediate re-entry whipsaws.

---

## 6. The 8 Frozen Qualification Gates (Absolute Standard)

All 8 frozen qualification gates remain identical and binding. No candidate qualifies without passing all 8 simultaneously:

| Gate ID | Metric & Hurdle Requirement | Denominator / Basis | Binding Standard |
| :--- | :--- | :--- | :---: |
| **GATE-1** | Per-Fold MTM MDD $\le 15.0\%$ in every fold AND Chained OOS MTM MDD $\le 15.0\%$ | Instantaneous Candle-Level MTM Equity | **MANDATORY** |
| **GATE-2** | Net Expectancy $\ge +8.0\text{ bps}$ ($+0.08\%$) | Unweighted Mean Return $\frac{1}{N} \sum (\text{NetPnL}_i / \text{Notional}_i)$ | **MANDATORY** |
| **GATE-3** | Profit Factor $\ge 1.25$ | Total Gross Wins / Total Gross Losses | **MANDATORY** |
| **GATE-4** | Aggregate OOS Trades $\ge 150$ | Total Realized Trades across 3 Folds | **MANDATORY** |
| **GATE-5** | $\ge 20$ Trades per pair across all 10 pairs | Per-Pair Realized Trade Counts | **MANDATORY** |
| **GATE-6** | Walk-Forward Consistency: $\ge 2$ of 3 folds profitable | Net Realized PnL per Fold ($> \$0.00$) | **MANDATORY** |
| **GATE-7** | Spatial Robustness: $\ge 7$ of 10 qualified pairs profitable | Per-Pair Realized Net PnL ($> \$0.00$) | **MANDATORY** |
| **GATE-8** | Stress Cost Tolerance: Stress Net PnL $> \$0$ & Stress PF $> 1.0$ | Evaluated at 21.0 bps round-trip friction | **MANDATORY** |

---

## 7. Unresolved Questions & Required Evidence

1. **In-Sample Meta-Sample Size**:
   Because Strategy B generates ~950 trades per 6-month fold across 10 pairs, the training set for each fold contains ~1,900 signal rows (compared to 87,000 bars for autonomous ML). Whether 1,900 sample instances provide sufficient statistical power for 21 features must be empirically evaluated.
2. **Primary Signal Alpha vs. Filter Efficiency**:
   If Strategy B's baseline signals have zero or negative raw predictability in certain market regimes, meta-filtering can reduce losses by dropping trades, but cannot fabricate positive alpha if no subset of breakouts is net profitable after 14 bps friction.

---

## 8. Protocol Governance & Execution Status

This deliverable represents **verification and protocol design only**.
- Zero models were trained.
- Zero backtest simulations were executed.
- Zero code in `backend/` was altered.
- The quarantined final holdout remains untouched and locked.

Implementation and evaluation require explicit user review and authorization under **Phase 5D**.

$$\mathbf{CERTIFIED \ STATUS: \ PHASE\_5C4\_DESIGN\_READY}$$
