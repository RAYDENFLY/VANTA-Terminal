# VANTA Terminal — Phase 5A Evaluation & Statistical Inference Specification

**Document ID**: `VANTA-DOCS-5A-EVAL-STATS-SPEC`  
**Protocol Version**: `1.0.0-FROZEN`  
**Statistical Framework**: Stationary Block Bootstrap & Mark-to-Market Portfolio Inference  
**Primary Reference Baseline**: `STRAT-B-01 (Donchian Breakout 1H)`  

---

## 1. The Breakdown of the IID Assumption in Multi-Pair Portfolios

Standard statistical tests (such as Student's t-test for Sharpe ratios or trade expectancies) rely fundamentally on the assumption that trade returns $\{r_1, r_2, \dots, r_N\}$ are **Independent and Identically Distributed (IID)**.

In multi-pair quantitative cryptocurrency trading, the IID assumption is **fatally flawed** due to three empirical phenomena:

1. **Cross-Sectional Contemporaneous Correlation**:
   Cryptocurrency assets share a massive common market factor ($\beta_{\text{BTC}}$). When the broader market undergoes a sharp liquidation cascade, multiple open positions (e.g., Long positions across ETH, SOL, AVAX, and ADA) experience severe adverse excursions simultaneously. Treating these concurrent losses as independent draws artificially deflates the standard error of the sample mean:
   $$\text{SE}_{\text{naive}} = \frac{\sigma}{\sqrt{N}} \ll \text{SE}_{\text{true}} = \sqrt{\frac{1}{N^2} \sum_{i=1}^N \sum_{j=1}^N \text{Cov}(r_i, r_j)}$$
2. **Serial Correlation and Volatility Clustering**:
   Market regimes exhibit strong temporal persistence (Mandelbrot's volatility clustering). Periods of low volatility (where false breakouts cluster) and high-momentum trending runs persist across multiple days and weeks. Trade outcomes are auto-correlated across consecutive bars.
3. **Overlapping Position Lifecycles**:
   Under a multi-stream portfolio architecture, trades initiated at different timestamps overlap in time, sharing the same underlying market volatility and funding settlement shocks.

> **Methodological Mandate**:
> Individual trades cannot be treated as independent observations. Statistical inference and confidence interval estimation must use a **cross-sectionally synchronized Block Bootstrap** operating on calendar time units.

---

## 2. Stationary Block Bootstrap Architecture

To construct statistically rigorous, leakage-safe confidence intervals for performance metrics, we specify a **Stationary Block Bootstrap** (Politis & Romano, 1994) adapted for multi-asset portfolios.

### 2.1 The Sampling Unit: Contemporaneous Daily Vectors
- The simulation timeline is partitioned into discrete chronological blocks of time $\mathbf{B}_k$.
- The atomic unit of resampling is a **1-Day (24-Hour) Synchronous Time Block** across all 10 eligible pairs simultaneously:
  $$\mathbf{U}_d = \left\{ \mathbf{b}_{i, t} \mid i \in \{1, \dots, 10\}, \, t \in [\text{day } d \text{ start}, \, \text{day } d \text{ end}] \right\}$$
- By resampling entire 24-hour multi-asset time slices as unbroken blocks, the **cross-sectional correlation structure between pairs is preserved 100% intact**.

### 2.2 Stationary Block Length Distribution
Under the Stationary Block Bootstrap, block lengths $L_k$ are drawn from a geometric distribution with mean parameter $p$:
$$\Pr(L = k) = (1 - p)^{k-1} p, \quad k = 1, 2, \dots$$
$$\mathbb{E}[L] = \frac{1}{p} = L_{\text{expected}}$$

- **Frozen Expected Block Length**: $L_{\text{expected}} = 5\text{ days}$ ($120\text{ hours}$, $p = 0.20$).
- **Economic Justification**: 5 days reflects the typical persistence of cryptocurrency volatility and trending micro-regimes, breaking long-range non-stationarity while retaining short-range autocorrelation and intraday co-movement.

### 2.3 Resampling Algorithm

```python
def stationary_block_bootstrap_portfolio(
    daily_returns_matrix: np.ndarray, # Shape: (T_days, 10_pairs)
    expected_block_length: int = 5,
    num_replicates: int = 2000,
    random_seed: int = 42
) -> np.ndarray:
    """
    Executes cross-sectionally synchronized Stationary Block Bootstrap.
    Preserves multi-pair covariance and serial autocorrelation.
    """
    rng = np.random.default_rng(random_seed)
    T = daily_returns_matrix.shape[0]
    p = 1.0 / expected_block_length
    
    bootstrap_replicates = []
    
    for b in range(num_replicates):
        resampled_days = []
        current_idx = rng.integers(0, T)
        
        while len(resampled_days) < T:
            resampled_days.append(current_idx)
            # Decide whether to continue current block or jump
            if rng.random() < p:
                current_idx = rng.integers(0, T)
            else:
                current_idx = (current_idx + 1) % T
                
        bootstrap_sample = daily_returns_matrix[resampled_days]
        bootstrap_replicates.append(bootstrap_sample)
        
    return np.array(bootstrap_replicates)
```

### 2.4 Resampling Replicates and Metrics
- **Number of Replicates**: $B = 2,000$ independent resampled pseudo-histories.
- **Estimated Parameters**:
  1. **Net Expectancy per Trade (bps)**:
     $$\text{Exp}^* = \frac{1}{N} \sum_{i=1}^N \left(\frac{\text{NetPnL}_i}{\text{Notional}_i}\right) \times 10,000$$
     Report 95% Percentile Confidence Interval: $[\text{Exp}^*_{0.025}, \, \text{Exp}^*_{0.975}]$.
  2. **Profit Factor (PF)**:
     $$\text{PF}^* = \frac{\sum \text{Wins}^*}{\sum |\text{Losses}^*|}$$
     Report 95% Percentile Confidence Interval: $[\text{PF}^*_{0.025}, \, \text{PF}^*_{0.975}]$.
  3. **Candle-Level MTM Max Drawdown**:
     Reconstructed synthetic equity curve from resampled daily portfolio returns.
     Report 95th Percentile Worst-Case Drawdown bound: $\text{MDD}^*_{0.95}$.

---

## 3. Descriptive Uncertainty vs. Qualification Gate Hurdles

A critical distinction is enforced between **descriptive statistical uncertainty** and **formal qualification gates**:

```
+-----------------------------------------------------------------------------------------------------+
| DICHOTOMY: DESCRIPTIVE UNCERTAINTY VS. DETERMINISTIC QUALIFICATION GATES                            |
+------------------------------+------------------------------------+---------------------------------+
| Dimension                    | Descriptive Statistical Bounds     | Deterministic Qualification Gate|
+------------------------------+------------------------------------+---------------------------------+
| Core Question                | What is the estimation noise?      | Does the realized path qualify? |
| Output                       | 95% Confidence Interval            | Binary Result (PASS / FAIL)     |
| Purpose                      | Diagnosing variance & robustness   | Enforcement of institutional bar|
| Standard                     | Stationary Block Bootstrap (B=2000)| Point estimate on canonical run |
| Authority                    | Informational / Non-Disqualifying  | Binding / Disqualifying         |
+------------------------------+------------------------------------+---------------------------------+
```

### Protocol Rule on Gates
The 8 frozen qualification gates (GATE-1 through GATE-8) operate **strictly on the realized historical sample trajectory** under the [`CanonicalPortfolioEngine`](file:///d:/vanta-terminal/backend/backtest/portfolio_engine.py). 

A candidate strategy cannot claim qualification by arguing that its bootstrap upper bound passes a gate if its realized historical point estimate fails the hurdle. Conversely, passing all 8 historical point-estimate gates does not guarantee out-of-sample survival; it merely grants qualification to enter the candidate pool.

---

## 4. Pre-Registered Dual Definition of GATE-1 (Maximum Drawdown)

In Phase 4B.5, Strategy B failed GATE-1 because its candle-level mark-to-market drawdown reached **20.67%**, exceeding the 15.0% threshold.

To eliminate ambiguity between per-fold cash resets ($10,000 initial equity) and continuous multi-fold compounding, GATE-1 is formally defined as a **dual-condition hurdle**:

$$\mathbf{GATE\text{-}1} = \mathbf{Condition\_A} \land \mathbf{Condition\_B}$$

### Condition A: Per-Fold MTM MDD Ceiling ($\le 15.0\%$)
In each of the three walk-forward folds ($f \in \{1, 2, 3\}$), the continuous mark-to-market drawdown relative to the fold's high-watermark must not exceed 15.0%:
$$\text{MDD}_{\text{Fold } 1} \le 15.0\% \quad \land \quad \text{MDD}_{\text{Fold } 2} \le 15.0\% \quad \land \quad \text{MDD}_{\text{Fold } 3} \le 15.0\%$$
- **Rationale**: Demonstrates that the strategy did not suffer catastrophic liquidation within any single 6-month historical regime.

### Condition B: Combined Walk-Forward MTM MDD Ceiling ($\le 15.0\%$)
The combined walk-forward equity curve is constructed by sequentially chaining fold returns:
$$E_0 = 10,000.00$$
$$E_{\text{chained}}(t) = E_f(t) \times \prod_{k=1}^{f-1} \left(1 + \frac{\text{NetPnL}_k}{10,000}\right)$$
The maximum peak-to-trough decline of $E_{\text{chained}}(t)$ over the entire 18-month evaluation horizon must satisfy:
$$\text{MDD}_{\text{chained}} \le 15.0\%$$

**Evaluation Rule**: If either Condition A or Condition B exceeds 15.00%, GATE-1 is marked as **`FAILED`**. Both values must be explicitly recorded in the benchmark JSON manifest.

---

## 5. Incremental Performance Metrics Relative to Strategy B

Every ML candidate evaluated in Phase 5 will be benchmarked directly against Strategy B's canonical performance. We define four formal incremental metrics ($\Delta$):

### 1. Incremental Net Dollar Gain ($\Delta \text{PnL}$)
$$\Delta \text{PnL} = \text{NetPnL}_{\text{ML}} - \text{NetPnL}_{\text{StratB}} = \text{NetPnL}_{\text{ML}} - \$243.43$$
- Hurdle: $\Delta \text{PnL} > \$0.00$.

### 2. Incremental Net Expectancy ($\Delta \text{Exp}$)
$$\Delta \text{Exp} = \text{Exp}_{\text{ML}} - \text{Exp}_{\text{StratB}} = \text{Exp}_{\text{ML}} - 3.31\text{ bps}$$
- Hurdle: $\text{Exp}_{\text{ML}} \ge +8.00\text{ bps}$ (GATE-2).

### 3. Drawdown Compression Ratio ($\text{DCR}$)
$$\text{DCR} = \frac{\text{MTM MDD}_{\text{StratB}} - \text{MTM MDD}_{\text{ML}}}{\text{MTM MDD}_{\text{StratB}}} = \frac{20.67\% - \text{MTM MDD}_{\text{ML}}}{20.67\%}$$
- Hurdle: $\text{DCR} \ge 0.2743$ (which corresponds to reducing MDD from 20.67% to $\le 15.00\%$).

### 4. Incremental Profit Factor ($\Delta \text{PF}$)
$$\Delta \text{PF} = \text{PF}_{\text{ML}} - \text{PF}_{\text{StratB}} = \text{PF}_{\text{ML}} - 1.007$$
- Hurdle: $\text{PF}_{\text{ML}} \ge 1.250$ (GATE-3).

---

## 6. Execution and Reporting Standards

All Phase 5 backtest executions must generate machine-readable manifests complying with the following reporting standards:

1. **Trade Level**: Every trade record must log `entry_time_ms`, `exit_time_ms`, `entry_price`, `exit_price`, `quantity`, `notional`, `fee`, `slippage_cost`, `gross_pnl`, `net_pnl`, `exit_reason`, and `model_confidence_score`.
2. **Equity Curve Level**: Log timestamp, cash, unrealized PnL, mark-to-market equity, reserved margin, free collateral, and instantaneous drawdown on every bar.
3. **Rejection Audit**: Log all order rejections with timestamp, symbol, direction, target notional, free collateral, and rejection reason code.
4. **Stress Model Replication**: Rerun all trades through the 21.0 bps stress cost model (7.5 bps fee + 3.0 bps slippage per side) and report stress Net PnL and stress Profit Factor.
