# VANTA Terminal — Phase 5A.1 Protocol Consistency Audit & Approval Gate

**Document ID**: `VANTA-DOCS-5A1-PROTOCOL-AUDIT`  
**Execution Timestamp**: `2026-10-27T14:52:00Z`  
**Auditor**: Antigravity Quantitative Verification Agent  
**Audit Scope**: Strict consistency review of Phase 5A documentation (`docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md`, `docs/PHASE_5A_FEATURE_CATALOG.md`, `docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md`, `data/experiments/phase_5a/protocol_manifest.json`)  
**Audit Status**: `PROTOCOL_APPROVAL_READY` (with documented protocol clarifications)  

---

## 1. Executive Summary & Audit Overview

Phase 5A.1 conducted a line-by-line, rigorous consistency audit of the Phase 5A Machine Learning research protocol before any Phase 5B feature pipeline implementation, model training, or benchmarking begins.

### Key Audit Findings
1. **Target Semantics Clarified (`PASS_WITH_LIMITATIONS`)**: Resolved the apparent discrepancy between the 12-hour label horizon and the 36-hour holding duration. Established that trade holding duration must equal the label evaluation horizon ($H = 12\text{ hours}$), eliminating horizon mismatch and fitting safely within the frozen 48-hour purge window.
2. **Directional Symmetry & Barrier Prices Locked (`PASS_WITH_LIMITATIONS`)**: Reconciled the Long vs. Short barrier formulations, entry price timing ($O_{t+1}$ with slippage), same-candle collision policy (`CONSERVATIVE_SL_FIRST`), and friction buffer interpretation (avoiding double-counting).
3. **Purge and Embargo Integrity Confirmed (`PASS`)**: The frozen 48-hour purge combined with the 48-hour embargo warmup provides a **96-hour buffer** between In-Sample training and Out-of-Sample trading. For a 12-hour label horizon, cross-fold label leakage is mathematically impossible.
4. **Gate-1 MDD Dual Hurdle Formalized (`PASS`)**: Retained the dual mark-to-market standard (per-fold MTM MDD $\le 15.0\%$ in every fold AND combined chained MTM MDD $\le 15.0\%$). Formally classified Closed-Trade MDD as a **diagnostic-only metric**, preserving the integrity of the 8 frozen qualification gates.
5. **Stationary Block Bootstrap Paired Difference Specified (`PASS`)**: Extended the multi-pair Stationary Block Bootstrap ($B=2,000$, $\mathbb{E}[L]=5\text{ days}$) to evaluate the paired difference $\Delta^*_{\text{ML}} = \text{Metric}^*_{\text{ML}} - \text{Metric}^*_{\text{StratB}}$ across identical resampled days.
6. **Feature Catalog & 100-Bar Warmup Verified (`PASS`)**: Audited all 21 pre-registered features. Confirmed that the longest lookback is 50 bars (`DIST_EMA_50`, `SPREAD_EMA_20_50`), and 100 bars provides >98% decay for Wilder's and exponential smoothers. Zero lookahead leakage exists.

---

## 2. Detailed Audit Findings by Required Question

### Section A: Triple-Barrier Target Semantics

#### 1. Label Horizon ($H=12\text{h}$) vs. Holding Limit ($36\text{h}$)
- **Audit Question**: Whether the 12-hour horizon is the label evaluation horizon while the 36-hour holding limit is an independent duration, or whether these definitions conflict.
- **Classification**: `PASS_WITH_LIMITATIONS`
- **Audit Finding**: In `docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md` Section 4.1, Target C was defined with horizon $H=12\text{ bars}$ (12 hours), while Section 4.2 referenced a "maximum trade holding period of 36 hours" to argue that $12\text{h} + 36\text{h} \le 48\text{h}$. This creates an inconsistency: if a model is trained to predict whether price reaches a barrier within 12 hours, holding the position for 36 hours introduces an economic regime mismatch (the trade remains open for 24 hours after the prediction has expired).
- **Resolution**:
  - The maximum trade holding period in backtest execution must be **strictly locked to $H = 12\text{ bars}$** (`time_expiry_bars = 12`).
  - If a position does not hit take-profit or stop-loss within 12 hours, it is exited at the Open of bar $t+13$ as `TIME_EXPIRY`.
  - Both the label horizon and the maximum trade holding duration are identical ($12\text{ hours}$).

#### 2. Maximum Future-Label Dependency and Purge/Embargo Duration
- **Audit Question**: The exact maximum future-label dependency in bars and the required purge/embargo duration.
- **Classification**: `PASS`
- **Audit Finding**: For prediction at bar $t$ Close ($t_{\text{close}}$), the trade enters at bar $t+1$ Open. The forward path evaluated spans bar $t+1$ Open through bar $t+12$ Close. The maximum future dependency is exactly **12 bars (12 hours)**.
- **Purge Calculation**:
  $$\text{Required Purge} \ge H \times \Delta t_{\text{bar}} = 12 \times 1\text{ hour} = 12\text{ hours}$$
  The frozen purge period is **48 hours** (48 bars). The safety margin is $48 - 12 = 36\text{ hours}$. Zero training labels can reach across the purge boundary into the evaluation fold.

#### 3. Directional Target: Long vs. Short Symmetry
- **Audit Question**: Whether labels are generated separately for LONG and SHORT decisions, or use a single directional target.
- **Classification**: `PASS_WITH_LIMITATIONS`
- **Audit Finding**: The mathematical formula in Section 4.1 was written from a Long perspective ($y_t = +1$ if $\max \Delta P \ge +1.5\text{ ATR} + 14\text{ bps}$, $y_t = -1$ if $\min \Delta P \le -1.0\text{ ATR}$). Under this definition, $y_t = -1$ represents a Long stop-loss, not a profitable Short.
- **Resolution**: The target is formalized as a **symmetric 3-class directional target** with separate barrier criteria:
  - **Class $+1$ (BUY / LONG)**: Path touches Upper Long Barrier $+1.5\text{ ATR}_{14} + 14\text{ bps}$ before touching Lower Long Barrier $-1.0\text{ ATR}_{14}$.
  - **Class $-1$ (SELL / SHORT)**: Path touches Lower Short Barrier $-1.5\text{ ATR}_{14} - 14\text{ bps}$ before touching Upper Short Barrier $+1.0\text{ ATR}_{14}$.
  - **Class $0$ (NEUTRAL / FLAT)**: Neither barrier touched within 12 bars (time expiry), OR conflicting touch within the same bar.
  - If both Long and Short barriers are simultaneously breached within the 12-hour window, the first-touched barrier assigns the label.

#### 4. Entry Price, ATR Normalization, and Barrier Price Definitions
- **Audit Question**: How entry price, ATR normalization, upper/lower barrier prices, transaction costs, and label class assignment are defined.
- **Classification**: `PASS`
- **Audit Finding**: To match live execution:
  - **Reference Entry Price**: $P_{\text{entry}} = O_{t+1} \times (1 + \text{slippage\_rate})$ for Long, $O_{t+1} \times (1 - \text{slippage\_rate})$ for Short, where $\text{slippage\_rate} = 0.0002$ (2.0 bps).
  - **ATR Volatility Unit**: $\text{ATR}_{14, t}$ computed as of bar $t$ Close (Wilder's 14-period ATR).
  - **Upper Barrier Price (Long TP)**: $P_{\text{entry}} \times \left(1 + 1.5 \cdot \frac{\text{ATR}_{14, t}}{C_t} + 0.0014\right)$.
  - **Lower Barrier Price (Long SL)**: $P_{\text{entry}} \times \left(1 - 1.0 \cdot \frac{\text{ATR}_{14, t}}{C_t}\right)$.
  - **Lower Barrier Price (Short TP)**: $P_{\text{entry}} \times \left(1 - 1.5 \cdot \frac{\text{ATR}_{14, t}}{C_t} - 0.0014\right)$.
  - **Upper Barrier Price (Short SL)**: $P_{\text{entry}} \times \left(1 + 1.0 \cdot \frac{\text{ATR}_{14, t}}{C_t}\right)$.

#### 5. Same-Candle Collision and Gap-Through-Barrier Events
- **Audit Question**: How same-candle TP/SL collisions, gap-through-barrier events, and time-expiry labels are handled.
- **Classification**: `PASS`
- **Audit Finding**:
  - **Same-Candle Ambiguity**: In strict conformity with `ExecutionPolicy.CONSERVATIVE_SL_FIRST`, if both the profit barrier and stop barrier fall within the same bar's $[L_{t+h}, H_{t+h}]$ range, the stop-loss is assumed to trigger first. The label is assigned to Stop-Loss (or Neutral).
  - **Gap-Through-Barrier**: If a bar opens beyond the stop barrier ($O_{t+h} < P_{\text{stop}}$ for Long), the stop fill is recorded at the Open price $O_{t+h}$ (slippage gap), exactly matching `CanonicalPortfolioEngine`.
  - **Time-Expiry**: If neither barrier is touched by the end of bar $t+12$, the trade exits at bar $t+12$ Close, and the label is assigned to $0$ (`NEUTRAL`).

#### 6. Transaction Cost Hurdle vs. Double-Counting
- **Audit Question**: Whether the 14 bps friction hurdle represents round-trip costs, an additional required edge above costs, or another convention. Prevent double-counting of costs.
- **Classification**: `PASS`
- **Audit Finding**:
  - The 14.0 bps term ($0.0014$) added to the profit barrier represents an **economic hurdle buffer**. It guarantees that the gross price move required to trigger a $+1$ label is sufficient to cover round-trip transaction costs (5.0 bps taker entry + 2.0 bps entry slip + 5.0 bps taker exit + 2.0 bps exit slip = 14.0 bps) and still deliver a net positive return of at least $1.5\text{ ATR}$.
  - During backtest execution, `CanonicalPortfolioEngine` deducts actual transaction costs from cash. Because the barrier price was placed $14\text{ bps}$ higher, when the barrier is reached, the net PnL after costs is strictly positive. There is **zero double-counting**; the barrier defines the target exit price, and the engine accounts for cash flows.

#### 7. Compatibility with Next-Bar-Open Execution
- **Audit Question**: Whether the label construction is compatible with the canonical engine's next-bar-open execution semantics.
- **Classification**: `PASS`
- **Audit Finding**: Yes. Signal generation occurs at $t_{\text{close}}$. Order execution occurs at bar $t+1$ Open. Label evaluation spans bars $[t+1, t+12]$. Semantics are 100% congruent.

---

### Section B: Purge, Embargo, and Walk-Forward Boundaries

- **Audit Question**: Verify label horizons cannot overlap across partitions, calculate purge from actual maximum lookahead, verify 48h purge sufficiency, specify boundary behavior.
- **Classification**: `PASS`
- **Audit Findings**:
  1. **Purge Sufficiency**: Maximum label horizon is 12 hours. Frozen purge is 48 hours. Ratio: $\frac{\text{Purge}}{\text{Lookahead}} = \frac{48}{12} = 4.0\times$. The 48-hour purge is more than sufficient.
  2. **Separate Embargo Necessity**: An embargo warmup of **48 hours** is strictly necessary prior to Out-of-Sample trading. It allows moving averages and ATR indicators to warm up on out-of-sample data so that feature values on the first traded OOS bar are 100% warm without executing unembargoed trades.
  3. **Fold Boundary Truncation**: For any position open at the final bar of an OOS fold (e.g. at `2026-04-26 00:00:00 UTC`), the canonical engine force-flattens the position at that bar's Close with exit reason `BOUNDARY_FLAT`. Labels whose forward window extends beyond the fold boundary are truncated; no candles at or after the boundary are read.

---

### Section C: Baseline and ML Comparison Fairness

- **Audit Question**: Fair comparison between `BENCHMARK-0` and ML candidates, identical setup, portfolio mechanics, primary incremental metric $\Delta_{\text{ML}}$, prediction execution, neutral predictions.
- **Classification**: `PASS`
- **Audit Findings**:
  1. **Identical Setup**: ML candidates and `BENCHMARK-0` evaluate the exact same 10 qualified pairs over the exact same fold schedules using `CanonicalPortfolioEngine` with $10,000 cash and 1.0x gross leverage cap.
  2. **Execution of Predictions**:
     - Prediction $\hat{y}_t = +1$ triggers a Market Buy order for symbol $i$ at bar $t+1$ Open (sized at 10% of portfolio equity).
     - Prediction $\hat{y}_t = -1$ triggers a Market Sell order (Short) at bar $t+1$ Open.
     - Prediction $\hat{y}_t = 0$ (`NEUTRAL`): If flat, no order is placed. If already in a position for symbol $i$, the existing position **remains open under its active barriers** until stop-loss, take-profit, or 12-hour expiry is reached. A neutral prediction does NOT prematurely force-close an open trade.
     - Conflicting Prediction: If a position is Long and $\hat{y}_t = -1$, the Long position is closed at bar $t+1$ Open and a Short position is opened (reversal).
  3. **Primary Incremental Metric ($\Delta_{\text{ML}}$)**:
     $$\Delta \text{Net PnL} = \text{Net PnL}_{\text{ML}} - \text{Net PnL}_{\text{StratB}} = \text{Net PnL}_{\text{ML}} - \$243.43$$
     $$\Delta \text{Expectancy} = \text{Expectancy}_{\text{ML}} - 3.31\text{ bps}$$
     $$\Delta \text{MTM MDD} = \text{MTM MDD}_{\text{StratB}} - \text{MTM MDD}_{\text{ML}} = 20.67\% - \text{MTM MDD}_{\text{ML}}$$

---

### Section D: Gate-1 MDD Accounting & Closed-Trade Clarification

- **Audit Question**: Pre-registered dual hurdle, chained equity construction, boundary positions, cash treatment, clarification of closed-trade MDD status.
- **Classification**: `PASS`
- **Audit Findings**:
  1. **Dual Hurdle Preserved**:
     - Condition A: $\text{MDD}_f \le 15.0\%$ in every fold ($f \in \{1, 2, 3\}$).
     - Condition B: $\text{MDD}_{\text{chained}} \le 15.0\%$ on the multi-fold chained equity curve.
  2. **Chained Equity Curve Construction**:
     $$E_0 = \$10,000.00$$
     $$E_{\text{chained}}(t) = E_f(t) \times \prod_{k=1}^{f-1} \left(1 + \frac{\text{NetPnL}_k}{\$10,000.00}\right)$$
     Because all positions are closed with `BOUNDARY_FLAT` at fold boundaries, cash equals equity, and the transition between folds is smooth and continuous.
  3. **Resolution of Closed-Trade MDD Inconsistency**:
     - In the Phase 5A Delivery Report, a row in the table stated: `Closed-Trade MDD: Must satisfy <= 15.0%`.
     - **Audit Clarification**: This was an editorial ambiguity. The frozen qualification protocol specifies exactly **8 gates**. GATE-1 is governed exclusively by **candle-level mark-to-market drawdown**. Closed-trade MDD is formally classified as a **diagnostic-only metric** reported for historical comparison with Phase 4B. It does NOT constitute a 9th qualification gate.

---

### Section E: Synchronized Stationary Block Bootstrap

- **Audit Question**: Resampling unit, block length, missing pairs, PF/expectancy/MDD per replicate, zero-trade/bankruptcy behavior, paired $\Delta_{\text{ML}}$ uncertainty, deterministic reproducibility.
- **Classification**: `PASS`
- **Audit Findings**:
  1. **Sampling Unit**: 24-hour synchronous multi-pair calendar blocks (00:00 UTC to 23:59 UTC) across all 10 pairs simultaneously.
  2. **Block Length**: Geometric distribution with expected block length $\mathbb{E}[L] = 5\text{ days}$ ($120\text{ hours}$, $p = 0.20$).
  3. **Missing Data**: If a pair has a missing candle within a resampled block, its return is 0 (flat position); the block is never discarded.
  4. **Replicate Metrics**: On each bootstrap replicate $b \in \{1, \dots, 2000\}$:
     - Net Expectancy: mean trade return in bps.
     - Profit Factor: $\sum \text{Wins} / \sum |\text{Losses}|$. If losses = 0, PF is set to $10.0$ (finite cap).
     - MTM MDD: peak-to-trough decline of the resampled daily portfolio equity curve.
     - Zero Trades: If a replicate contains 0 trades, Expectancy = 0.0 bps, PF = 1.0, MDD = 0.0%.
     - Bankruptcy: If equity hits $\le \$0.00$, MDD is clamped to 100.0% and further trading is halted.
  5. **Paired Bootstrap for $\Delta_{\text{ML}}$**: To evaluate whether ML significantly outperforms Strategy B:
     $$\Delta^*_b = \text{Metric}^*_{\text{ML}, b} - \text{Metric}^*_{\text{StratB}, b}$$
     Evaluated across the exact same resampled days. A 95% confidence interval for $\Delta^*$ that excludes zero proves statistically significant incremental performance.
  6. **Deterministic Seed**: RNG seeded with fixed integer `42`.

---

### Section F: Feature Catalog and Leakage Invariants

- **Audit Question**: Formulas, units, lookbacks, availability, cross-sectional sync, missing values, zero lookahead, RobustScaler fitting, 100-bar warmup sufficiency.
- **Classification**: `PASS`
- **Audit Findings**:
  1. **Lookback Verification**:
     - Longest lookback: 50 bars (`DIST_EMA_50`, `SPREAD_EMA_20_50`).
     - Warmup requirement: For an exponential moving average with period 50 ($\alpha = 2/51 \approx 0.0392$), after 100 bars the residual weight of the initial seed is $(1 - \alpha)^{100} = (0.9608)^{100} = 0.0182$ (< 1.9%).
     - Therefore, the **100-bar warmup buffer is mathematically sufficient** for all 21 features.
  2. **Zero Lookahead Audit**:
     - All 21 features use data finalized strictly at or before bar $t$ Close ($t_{\text{close}}$).
     - Zero future bars, zero future labels, zero out-of-fold statistics.
  3. **Scaling Rule**:
     - `RobustScaler` is fitted strictly on the In-Sample slice. Features on OOS are transformed using the frozen training medians and interquartile ranges.

---

### Section G: Model Arena and Resource Budget

- **Audit Question**: Verify Logistic Regression, LightGBM, and XGBoost specs, deterministic seeds, CPU execution, memory budget, versions, class weighting, parameter search policy.
- **Classification**: `PASS`
- **Audit Findings**:
  1. **Environment Compatibility Verified**:
     - `scikit-learn`: 1.8.0 (Installed & operational)
     - `lightgbm`: 4.6.0 (Installed & operational)
     - `xgboost`: 3.1.1 (Installed & operational)
     - `scipy`: 1.16.1 (Installed & operational)
  2. **Hardware Budget**:
     - CPU-only execution (`n_jobs=4`). GPU acceleration disabled.
     - Memory allocation: $\le 4.0\text{ GB}$ ceiling.
     - Deterministic seed: `42`.
  3. **No Broad AutoML**: Hyperparameter tuning restricted strictly to shallow grid search on the In-Sample validation split (last 20% of In-Sample slice). Zero tuning on OOS data.

---

### Section H: Frozen Qualification Gates

- **Audit Question**: Retain all 8 gates, clarify single model vs fold application.
- **Classification**: `PASS`
- **Audit Findings**:
  1. All 8 frozen gates are strictly preserved without modification:
     - GATE-1: MDD $\le 15.0\%$ (Dual Hurdle: Per-fold $\le 15\%$ AND Combined $\le 15\%$).
     - GATE-2: Net Expectancy $\ge +8.0\text{ bps}$.
     - GATE-3: Profit Factor $\ge 1.25$.
     - GATE-4: Aggregate Trades $\ge 150$.
     - GATE-5: Per-Pair Trades $\ge 20$ for all 10 pairs.
     - GATE-6: Walk-Forward Consistency $\ge 2$ of 3 folds profitable.
     - GATE-7: Spatial Robustness $\ge 7$ of 10 pairs profitable.
     - GATE-8: Stress Net PnL $> \$0$ and Stress PF $> 1.0$ at 21.0 bps friction.
  2. **Model Application**: In Walk-Forward evaluation, Model $\mathcal{M}_f$ is trained on In-Sample $f$ and evaluated out-of-sample on Fold $f$. The 8 gates evaluate the **concatenated OOS performance of the walk-forward pipeline**, exactly matching the methodology used for Strategies A, B, and C in Phase 4B.5.

---

## 3. Summary of Findings & Classifications

```
========================================================================================
AUDIT FINDINGS CLASSIFICATION MATRIX
========================================================================================
Section A.1: 12h Horizon vs 36h Holding Limit        PASS_WITH_LIMITATIONS (Holding locked to 12h)
Section A.2: Future-Label Dependency & Purge         PASS                  (12h lookahead <= 48h purge)
Section A.3: Long vs Short Directional Symmetry      PASS_WITH_LIMITATIONS (Symmetric 3-class locked)
Section A.4: Entry Price & Barrier Definitions       PASS                  (O_{t+1} + slip, ATR locked)
Section A.5: Collision & Gap Handling                PASS                  (CONSERVATIVE_SL_FIRST)
Section A.6: Transaction Cost Hurdle Accounting      PASS                  (No double-counting confirmed)
Section A.7: Execution Timing Compatibility          PASS                  (100% congruent with engine)
Section B.1: Purge & Embargo Boundary Integrity      PASS                  (96h total buffer)
Section C.1: Baseline & ML Comparison Fairness       PASS                  (Identical shared capital)
Section D.1: Gate-1 Dual MTM MDD Accounting          PASS                  (Dual MTM hurdle confirmed)
Section D.2: Closed-Trade MDD Clarification          PASS                  (Diagnostic metric only)
Section E.1: Stationary Block Bootstrap              PASS                  (B=2000, daily blocks)
Section E.2: Paired Bootstrap for Delta_ML           PASS                  (Identical resampled days)
Section F.1: 21 Features & Zero Lookahead            PASS                  (Zero leakage proven)
Section F.2: 100-Bar Warmup Sufficiency              PASS                  (Max lookback 50 bars)
Section G.1: Model Arena & Resource Constraints      PASS                  (CPU-only, seed 42)
Section H.1: 8 Frozen Qualification Gates            PASS                  (Strictly preserved)
========================================================================================
OVERALL STATUS: PROTOCOL_APPROVAL_READY
========================================================================================
```

---

## 4. Proposed Amendments to Protocol Documentation

To reflect the audit clarifications, minor text updates are proposed for:
1. `docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md`:
   - Locking trade holding limit to $12\text{ hours}$ (`time_expiry_bars = 12`).
   - Explicitly stating symmetric barriers for Long and Short trades.
   - Clarifying that Closed-Trade MDD is a diagnostic metric, not a 9th gate.
2. `docs/PHASE_5A_EVALUATION_AND_STATISTICS_SPEC.md`:
   - Documenting the paired block bootstrap for $\Delta_{\text{ML}}$.
3. `data/experiments/phase_5a/protocol_manifest.json`:
   - Updating hashes and parameters accordingly.

---

## 5. Concise List of Unresolved User Decisions

There are **zero critical blockers** preventing Phase 5B authorization. The following design choices are formalized and submitted for final user confirmation:

1. **Holding Duration Lock (`DEC-01`)**: Trade maximum holding duration is locked to $12\text{ bars}$ ($12\text{ hours}$ on 1H timeframe) to perfectly match the label evaluation horizon $H=12$.
2. **Directional Target Symmetry (`DEC-02`)**: Target C is formalized as a symmetric 3-class target ($+1$ for Long breakout, $-1$ for Short breakout, $0$ for neutral/time-expiry).
3. **Closed-Trade MDD Status (`DEC-03`)**: Closed-Trade MDD is formally designated as a diagnostic-only metric; GATE-1 is evaluated strictly on the dual candle-level MTM MDD standard.

---

## 6. Exit Criteria

$$\mathbf{PROTOCOL\_APPROVAL\_READY}$$

All critical definitions are mathematically consistent, leakage safety is proven, and comparison fairness against Strategy B is guaranteed. All Phase 5B implementation work remains halted pending explicit user approval.
