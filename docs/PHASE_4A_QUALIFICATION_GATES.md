# VANTA Terminal — Strategy Qualification Gates
**Document ID:** DOC-GATE-P4A-001  
**Phase:** 4A (Pre-Strategy Research Protocol)  
**Verification Date:** 2026-10-27  
**Status:** FROZEN ACCEPTANCE THRESHOLDS  

---

## 1. Executive Summary & Objective

In quantitative research, post-hoc threshold relaxation ("moving the goalposts") is a leading cause of live trading failure. When strategies perform below expectation, researchers are tempted to lower drawdown limits, accept smaller sample sizes, or exclude underperforming pairs.

To prevent confirmation bias, this document establishes **frozen, non-negotiable qualification gates**. A candidate strategy must satisfy every primary gate to qualify as the certified benchmark baseline for VANTA Terminal.

If no candidate meets all criteria, the mandatory **`NO QUALIFIED STRATEGY`** fallback protocol is triggered automatically.

---

## 2. Quantitative Acceptance Thresholds

Every candidate strategy is evaluated over the combined Out-of-Sample (OOS) validation periods across all three walk-forward folds under standard exchange frictions ($5.0\text{ bps}$ taker fee, $2.0\text{ bps}$ slippage).

| Gate ID | Metric Name | Mathematical Definition | Minimum Qualification Threshold | Rationale / Failure Mode Mitigated |
| :--- | :--- | :--- | :--- | :--- |
| **GATE-1** | **Maximum Drawdown (MDD)** | $\max_{t} \left(\frac{\max_{\tau \le t} E_\tau - E_t}{\max_{\tau \le t} E_\tau}\right)$ | **$\le 15.0\%$** | Capital preservation; prevents ruinous equity drawdowns during adverse regimes. |
| **GATE-2** | **Net Expectancy per Trade** | $\mathbb{E}[R_{net}] = \frac{1}{N}\sum_{i=1}^N \frac{\text{Net PnL}_i}{\text{Position Notional}_i}$ | **$\ge +0.08\%$ ($+8.0\text{ bps}$)** | Ensures true edge after overcoming $14.0\text{ bps}$ round-trip taker friction. |
| **GATE-3** | **Profit Factor (PF)** | $\frac{\sum \max(0, \text{Net PnL}_i)}{\sum |\min(0, \text{Net PnL}_i)|}$ | **$\ge 1.25$** | Net wins must exceed net losses by at least $25\%$. |
| **GATE-4** | **Aggregate Trade Count** | $N_{total} = \sum_{k=1}^{11} N_k$ | **$\ge 150\text{ trades}$** | Statistical power; rejects fluke results from small sample sizes. |
| **GATE-5** | **Per-Pair Trade Count** | $\min_{k \in \text{QualPairs}} N_k$ | **$\ge 20\text{ trades}$** | Guarantees broad universe activity; rejects single-pair concentration. |
| **GATE-6** | **Walk-Forward Consistency** | $\sum_{m=1}^3 \mathbb{I}(\text{Net PnL}_{OOS, m} > 0)$ | **$\ge 2 \text{ of } 3 \text{ Folds}$ ($\ge 66.7\%$)** | Temporal stability across distinct market regimes (bull, bear, sideways). |
| **GATE-7** | **Cross-Pair Robustness** | $\sum_{k=1}^{11} \mathbb{I}(\text{Net PnL}_k > 0)$ | **$\ge 7 \text{ of } 11 \text{ Pairs}$ ($\ge 63.6\%$)** | Spatial generalizability; rejects curve-fitting to single market idiosyncrasies. |
| **GATE-8** | **Friction Stress Tolerance** | $\mathbb{E}[R_{stress}]$ at $7.5\text{ bps}$ fee $+ 3.0\text{ bps}$ slip | **$\text{Net PnL}_{stress} > 0$ and $\text{PF}_{stress} > 1.0$** | Fragility filter; strategy must not collapse under higher execution friction. |

---

## 3. Detailed Gate Specifications

### 3.1 Net Expectancy Hurdle (GATE-2)
Exchange fees and market impact are the primary killers of high-frequency and swing crypto strategies.
- With an exchange taker fee of $0.05\%$ ($5.0\text{ bps}$) and slippage of $0.02\%$ ($2.0\text{ bps}$) applied on both entry and exit:
  $$\text{Total Round-Trip Friction} = (5.0 + 2.0) + (5.0 + 2.0) = 14.0\text{ bps}$$
- To satisfy GATE-2 ($\text{Net Expectancy} \ge +8.0\text{ bps}$), the strategy must achieve an average **Gross Expectancy $\ge +22.0\text{ bps}$ ($0.22\%$)** per trade.

### 3.2 Friction Stress Test (GATE-8)
To assess operational fragility, the entire validation ledger is re-evaluated under elevated execution costs:
- **Taker Fee**: $7.5\text{ bps}$ ($1.5\times$ baseline)
- **Adverse Slippage**: $3.0\text{ bps}$ ($1.5\times$ baseline)
- **Total Stress Friction**: $21.0\text{ bps}$ round-trip.
- **Requirement**: If a strategy's Net PnL turns negative under this stress test, it fails GATE-8, designating it as "friction-fragile."

### 3.3 Spatial Robustness (GATE-7)
The parameter vector $\theta^*$ is held constant across all 11 instruments. Optimizing separate parameters for each coin is strictly prohibited at this stage. A viable baseline strategy must demonstrate that its economic premise holds broadly across high-beta, mid-cap, and benchmark crypto assets.

---

## 4. Fallback Protocol: `NO QUALIFIED STRATEGY` Clause

### 4.1 Trigger Condition
If **none** of the three pre-registered candidate strategies (Sweep-Reclaim, Trend-Breakout, Mean Reversion) satisfy all 8 qualification gates simultaneously, the system will **NOT** loosen the acceptance thresholds.

Instead, the benchmark runner will trigger the **`NO QUALIFIED STRATEGY`** protocol.

### 4.2 Mandatory Actions upon Trigger
1. **Formal Registry Entry**:
   The Phase 4B benchmark summary will formally record:
   ```json
   {
     "status": "NO_QUALIFIED_STRATEGY",
     "certified_baseline": null,
     "reason": "All pre-registered heuristic candidates failed one or more qualification gates under standard friction."
   }
   ```
2. **Identification of Unqualified Reference Baseline**:
   The candidate with the highest Sharpe Ratio / lowest drawdown will be selected strictly as an **Unqualified Reference Baseline** (`UNQUALIFIED_BASELINE`).
3. **UI and Ledger Watermark**:
   All dashboards, reports, and subsequent comparisons referencing this candidate will display the warning:
   > ⚠️ **UNQUALIFIED REFERENCE BASELINE**  
   > *This strategy failed Phase 4A acceptance gates. It is preserved solely as a comparative benchmark for ML models and must not be considered an approved trading signal.*
4. **Transition to Machine Learning Research (Phase 5)**:
   The failure of simple technical heuristics confirms the core hypothesis of VANTA Terminal: fixed rules cannot systematically overcome crypto-futures transaction costs, directly justifying the investigation of non-linear Machine Learning models in Phase 5.
