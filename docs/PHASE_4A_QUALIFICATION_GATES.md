# VANTA Terminal — Strategy Qualification Gates
**Document ID:** DOC-GATE-P4A-001  
**Phase:** 4A / 4A.1 (Reconciled & Frozen Acceptance Gates)  
**Verification Date:** 2026-10-27  
**Status:** RECONCILED & FROZEN ACCEPTANCE THRESHOLDS  

---

## 1. Executive Summary & Core Mandate

In quantitative research, post-hoc threshold relaxation ("moving the goalposts") is a primary cause of live strategy failure. When strategies underperform, researchers are tempted to reduce drawdown requirements, forgive small sample sizes, or exclude underperforming pairs.

To prevent confirmation bias, this document establishes **frozen, mathematically formalized qualification gates**. A candidate strategy must satisfy every primary gate across the combined Out-of-Sample (OOS) validation periods to qualify as the certified benchmark baseline for VANTA Terminal.

If no candidate meets all criteria, the mandatory **`NO QUALIFIED STRATEGY`** fallback protocol is triggered automatically.

---

## 2. Quantitative Acceptance Thresholds Matrix

Every candidate strategy is evaluated over the combined Out-of-Sample (OOS) validation periods across all three walk-forward folds under standard exchange frictions ($5.0\text{ bps}$ taker fee, $2.0\text{ bps}$ slippage).

| Gate ID | Metric Name | Exact Mathematical Formula | Minimum Hurdle | Denominator / Basis | Failure Mode Mitigated |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GATE-1** | **Maximum Drawdown (MDD)** | $\max_{t} \left(\frac{\text{HWM}_t - E_t}{\text{HWM}_t}\right) \times 100\%$ | **$\le 15.0\%$** | Continuous equity curve | Capital preservation; prevents ruinous drawdowns. |
| **GATE-2** | **Net Expectancy per Trade** | $\mathbb{E}[r] = \frac{1}{N}\sum_{i=1}^N \frac{\text{Net PnL}_i}{\text{Fill Price}_{entry, i} \cdot Q_i}$ | **$\ge +0.08\%$ ($+8.0\text{ bps}$)** | Trade Entry Notional | Ensures edge after overcoming $14.0\text{ bps}$ friction. |
| **GATE-3** | **Profit Factor (PF)** | $\frac{\sum \max(0, \text{Net PnL}_i)}{\sum \|\min(0, \text{Net PnL}_i)\|}$ | **$\ge 1.25$** | Realized net cashflows | Wins must exceed losses by at least $25\%$. |
| **GATE-4** | **Aggregate Trade Count** | $N_{total} = \sum_{k \in \text{QualPairs}} N_k$ | **$\ge 150\text{ trades}$** | 10 Qualified Pairs (OOS) | Rejects fluke statistical artifacts. |
| **GATE-5** | **Per-Pair Trade Count** | $\min_{k \in \text{QualPairs}} N_k$ | **$\ge 20\text{ trades}$** | Each Qualified Pair | Rejects single-pair concentration. |
| **GATE-6** | **Walk-Forward Consistency** | $\sum_{m=1}^3 \mathbb{I}(\text{Net PnL}_{OOS, m} > 0)$ | **$\ge 2 \text{ of } 3 \text{ Folds}$ ($\ge 66.7\%$)** | 3 Rolling WF Folds | Temporal stability across distinct regimes. |
| **GATE-7** | **Spatial Robustness** | $\sum_{k \in \text{QualPairs}} \mathbb{I}(\text{Net PnL}_k > 0)$ | **$\ge 7 \text{ of } 10 \text{ Pairs}$ ($\ge 70.0\%$)** | **10 `ELIGIBLE` Pairs** | Generalizability across assets under same $\theta^*$. |
| **GATE-8** | **Friction Stress Tolerance** | $\mathbb{E}[r_{stress}]$ at $7.5\text{ bps}$ fee $+ 3.0\text{ bps}$ slip | **$\text{Net PnL} > 0$ and $\text{PF} > 1.0$** | $21.0\text{ bps}$ round-trip | Fragility filter; avoids razor-thin fee traps. |

---

## 3. Mathematical Definitions & Boundary Conditions

### 3.1 Net Expectancy & Uncertainty Reporting (GATE-2)
- **Primary Expectancy ($\mathbb{E}[r]$)** is calculated strictly on **Trade Entry Notional**:
  $$r_i = \frac{\text{Net Realized PnL}_i}{\text{Fill Price}_{entry, i} \times \text{Quantity}_i}$$
  $$\mathbb{E}[r] = \frac{1}{N}\sum_{i=1}^N r_i$$
- **Uncertainty Reporting**: All validation tear sheets report the sample standard deviation $s_r$, standard error of the mean $\text{SEM} = \frac{s_r}{\sqrt{N}}$, and the two-sided Student's $t$ $95\%$ confidence interval:
  $$\text{CI}_{95\%} = \mathbb{E}[r] \pm t_{0.975, N-1} \times \frac{s_r}{\sqrt{N}}$$
- **Secondary $R$-Expectancy ($\mathbb{E}[R]$)**: Reported for risk-normalized comparability:
  $$\mathbb{E}[R] = \frac{1}{N}\sum_{i=1}^N \frac{\text{Net Realized PnL}_i}{\text{Initial Dollar Risk}_i}, \quad \text{where } \text{Initial Risk}_i = |\text{Fill Price}_{entry, i} - \text{SL}_i| \times Q_i$$

### 3.2 Profit Factor Boundary Handling (GATE-3)
$$\text{PF} = \frac{\sum_{i=1}^N \max(0, \text{Net PnL}_i)}{\sum_{i=1}^N |\min(0, \text{Net PnL}_i)|}$$
- **Zero Loss Case**: If $\sum |\text{Losses}| = 0$ and $\sum \text{Wins} > 0$, $\text{PF}$ is recorded as $\infty$ (satisfies GATE-3).
- **Zero Win Case**: If $\sum \text{Wins} = 0$, $\text{PF} = 0.0$ (fails GATE-3).

### 3.3 Spatial Robustness Denominator & Zero-Trade Rules (GATE-5 & GATE-7)
- **Exact Denominator**: GATE-7 is evaluated strictly over the **10 `ELIGIBLE` Qualified Pairs** (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `XRPUSDT`, `ADAUSDT`, `AVAXUSDT`, `LINKUSDT`, `DOGEUSDT`, `LTCUSDT`).
- **`XMRUSDT` Status**: As a `PARTIAL_HISTORY` pair lacking 3-year coverage and in-sample training, `XMRUSDT` is excluded from the denominator ($N_{qual} = 10$).
- **Zero-Trade / Inadequate Sample Treatment**:
  - If a qualified pair generates $< 20\text{ completed trades}$ across the 3 OOS folds, it is flagged as `INSUFFICIENT_SAMPLE`.
  - It automatically fails GATE-5.
  - In GATE-7, any pair with `INSUFFICIENT_SAMPLE` or $0$ trades is treated strictly as **$\text{Net PnL} \le 0$ (FAIL)**.
  - Under no circumstances may an inactive or loss-making pair be dropped to inflate spatial win rates.

### 3.4 Friction Stress Test Mechanics (GATE-8)
- The stress test **REPLACES** baseline friction; it does NOT add on top of it.
- **Baseline Friction**: $5.0\text{ bps}$ taker fee $+ 2.0\text{ bps}$ adverse slippage on both entry and exit ($14.0\text{ bps}$ round-trip).
- **Stress Friction**: $7.5\text{ bps}$ taker fee ($1.5\times$) $+ 3.0\text{ bps}$ adverse slippage ($1.5\times$) on both entry and exit ($21.0\text{ bps}$ round-trip).
- **Evaluation**: The exact trade sequence, fill timestamps, and quantities generated during OOS are re-costed under the elevated friction. The candidate must achieve positive aggregate Net PnL ($\sum \text{Net PnL}_{stress} > 0$) and $\text{PF}_{stress} > 1.0$.

---

## 4. Mandatory Fallback Protocol: `NO QUALIFIED STRATEGY` Clause

### 4.1 Trigger Condition
If **none** of the three pre-registered candidate strategies (Sweep-Reclaim, Trend-Breakout, Mean Reversion) satisfy all 8 qualification gates simultaneously, the system will **NOT** loosen acceptance thresholds.

The benchmark runner will trigger the **`NO QUALIFIED STRATEGY`** protocol automatically.

### 4.2 Mandatory Protocol Execution
1. **Registry Declaration**:
   The Phase 4B benchmark summary will formally record:
   ```json
   {
     "status": "NO_QUALIFIED_STRATEGY",
     "certified_baseline": null,
     "reason": "All pre-registered heuristic candidates failed one or more qualification gates under standard friction."
   }
   ```
2. **Identification of Unqualified Reference Baseline**:
   The candidate with the highest Sharpe Ratio / lowest drawdown will be designated as an **Unqualified Reference Baseline** (`UNQUALIFIED_BASELINE`).
3. **Mandatory UI and Ledger Watermark**:
   All dashboards, reports, and subsequent comparisons referencing this candidate will display:
   > ⚠️ **UNQUALIFIED REFERENCE BASELINE**  
   > *This strategy failed Phase 4A acceptance gates. It is preserved solely as a comparative benchmark for ML models and must not be considered an approved trading signal.*
4. **Transition to Machine Learning Research (Phase 5)**:
   The failure of simple technical heuristics confirms the core hypothesis of VANTA Terminal: fixed rules cannot systematically overcome crypto-futures transaction costs, directly justifying the investigation of non-linear Machine Learning models in Phase 5.
