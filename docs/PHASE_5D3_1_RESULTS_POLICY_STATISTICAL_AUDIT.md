# VANTA Terminal — Phase 5D.3.1 Results, Cooldown & Statistical Accounting Audit

**Audit Status:** `PHASE_5D3_1_AUDIT_PASS`  
**Predecessor Status:** `PHASE_5D3_NO_QUALIFIED_MODEL`  
**Primary Strategy:** `STRAT-B-01` (Donchian Breakout 1H) — `UNQUALIFIED_BASELINE`  
**Audit Scope:** Independent read-only verification of Phase 5D.3 empirical results, policy mechanics, PnL accounting, paired bootstrap inference, and gate evaluations.

---

## 1. Executive Summary

An exhaustive, read-only audit of all Phase 5D.3 experimental artifacts was conducted across the 13 configurations (1 Benchmark-0 reference run + 12 meta-model policy candidates). The audit conclusively verifies the mathematical integrity, execution consistency, and statistical inference of the Phase 5D.3 results.

### Key Audit Findings
1. **Cooldown Policy Correctness (Audit A — Pass):** The identical performance metrics between H1 vs H2 and H3 vs H4 are not due to an implementation defect or bypassed cooldown logic. Active cooldown rejections occurred in all H2 and H4 runs. However, every signal rejected under the cooldown condition possessed a model probability $\hat{p} < \tau$. In H1 and H3, these signals were rejected under `BELOW_PROBABILITY_THRESHOLD`. Because the probability threshold is strictly more restrictive than the cooldown window, it completely subsumed the cooldown filter, resulting in identical trade ledgers.
2. **PnL & Execution Accounting Integrity (Audit B — Pass):** 100% of the 2,851 benchmark trades and all candidate trade ledgers satisfy the exact accounting identity $\text{Net PnL} = \text{Gross PnL} - \text{Total Fees} - \text{Slippage Cost} + \text{Funding Payment}$. Aggregate metrics (Gross PnL, Total Fees, Slippage, Net PnL, Profit Factor, Expectancy, and Stress PnL/PF) reconcile perfectly. A minor 1–2 cent discrepancy between the sum of pre-rounded pair net PnLs and portfolio net PnL is confirmed as normal half-cent floating-point summation variance.
3. **Bootstrap Inference & Tail Convention (Audit C — Pass):** The paired stationary block bootstrap operates strictly on synchronized 24-hour calendar-time daily PnL vectors ($T = 545$ days, $B = 2,000$ replicates, $E[L] = 5$ days). The discrepancy between the deterministic point estimate delta ($-\$147.69$ for LGBM H1) and the bootstrap mean delta ($-\$85.82$) is rigorously attributed to Monte Carlo sampling variation arising from Benchmark-0's extreme daily path volatility ($\sigma_{\text{path}} = \$3,805.53$, yielding a Monte Carlo standard error $\text{SE} = \$85.09$, placing the point estimate within $0.75$ standard errors). Percentile confidence intervals and the one-sided tail convention $P(\Delta^* \le 0)$ are mathematically sound and confirm non-significance ($p \approx 0.50$).
4. **Sparse-Trade Accounting & Gate Mechanics (Audit D — Pass):** Low mark-to-market maximum drawdown (MTM MDD) values ($0.00\%$ to $3.74\%$) are confirmed to be mechanical consequences of cash dilution under shared-capital accounting ($97.69\%$ to $100.00\%$ rejection rates). Zero-trade pairs and folds are strictly penalized under the frozen 10-pair denominator for GATE-5 and GATE-7 (scoring 0 passes). Low MDD is confirmed to be an artifact of inactive capital rather than risk management alpha.

**Final Certification:** `PHASE_5D3_1_AUDIT_PASS`. The outcome `PHASE_5D3_NO_QUALIFIED_MODEL` and baseline status `STRAT-B-01 = UNQUALIFIED_BASELINE` remain definitive.

---

## 2. Hard Constraint Verification

| Constraint | Requirement | Observed Status | Audit Verification |
|---|---|---|---|
| Holdout Boundary | No timestamps $\ge 2026-04-26\text{T}00:00:00\text{Z}$ (`1777161600000` ms) | Max Exit: `1777158000000` ms | **ZERO HOLDOUT LEAKAGE** |
| Retraining & Backtesting | Zero model fits, zero backtest replays | Zero process calls | **STRICT READ-ONLY AUDIT** |
| Bootstrap Re-sampling | Zero new pseudo-random replicates | Inspected existing JSON | **DETERMINISTIC VERIFICATION** |
| Server Isolation | Never touch port 8000 | Active PID 26148 untouched | **PORT 8000 PRESERVED** |
| Disk Storage | Free space $\ge 10\text{ GB}$ on `D:\` | 106.82 GB free on `D:\` | **STORAGE COMPLIANT** |
| Predecessor Status | Baseline remains unqualified | `UNQUALIFIED_BASELINE` | **PRESERVED** |

---

## 3. Audit A — Cooldown Policy Correctness

### 3.1 Policy Specification and Implementation
Inspection of `backend/ml/meta_strategy.py` confirms the architectural design of the cooldown filter:

```python
# Position Exit Tracking (backend/ml/meta_strategy.py:126-130)
if getattr(self, "_was_open", False) and not position.is_open():
    self.last_exit_time_ms = bar.timestamp_ms
self._was_open = position.is_open()

# Cooldown Evaluation (backend/ml/meta_strategy.py:165-172)
if self.config.cooldown_bars > 0 and self.last_exit_time_ms > 0:
    cooldown_ms = self.config.cooldown_bars * 3600 * 1000
    elapsed_since_exit = bar.timestamp_ms - self.last_exit_time_ms
    if elapsed_since_exit < cooldown_ms:
        return False, "COOLDOWN_ACTIVE"
```

### 3.2 Architectural Invariant Verification
1. **Trigger Condition:** Cooldown is activated **only upon position exit**. When `self._was_open` transitions from `True` to `False`, `self.last_exit_time_ms` is stamped with the exit bar's timestamp. Rejected signals never open a position and therefore **never trigger cooldown**.
2. **Timing Metric:** Cooldown evaluates elapsed clock time in milliseconds:  
   $$\Delta t = t_{\text{bar}} - t_{\text{exit}}$$  
   against the fixed millisecond threshold:  
   $$\text{cooldown\_ms} = \text{cooldown\_bars} \times 3,600,000\text{ ms} = 14,400,000\text{ ms (4 hours)}.$$
3. **Boundary Condition:** The boundary is **strictly exclusive** (`elapsed_since_exit < cooldown_ms`). At exactly 4 hours ($14,400,000$ ms post-exit), cooldown has expired and new signals are admitted.
4. **Cross-Pair Independence:** Cooldown state is strictly isolated per instrument. Each symbol maintains its own `MetaStrategyFilter` instance with independent `last_exit_time_ms` tracking. An exit on `BTCUSDT` has zero effect on `ETHUSDT`.
5. **Fold-Boundary Reset:** Strategy instances are instantiated afresh at each fold boundary. Furthermore, the mandatory 48-hour embargo window prior to each OOS start guarantees that any pre-OOS trades cannot influence OOS entry timing.

### 3.3 Empirical Attribution of Metric Identity (H1 vs H2 and H3 vs H4)
Across all models, H1 (cooldown = 0) and H2 (cooldown = 4) produced identical trade counts and PnL, as did H3 and H4. A replay audit was conducted using the saved signal timestamps, exit timestamps, and model probability scores $\hat{p}$:

| Model | Policy Variant | Cooldown Window | Candidate Signals in Cooldown Window | Model Probabilities of Cooldown Signals | Rejection Reason in H1/H3 | Rejection Reason in H2/H4 |
|---|---|---|---|---|---|---|
| `META-1-LOGIT` | H1 vs H2 | 4 bars (4h) | 2 signals (`SOLUSDT`) | $\hat{p} = 0.2051, 0.2696$ | `BELOW_PROBABILITY_THRESHOLD` | `COOLDOWN_ACTIVE` |
| `META-1-LOGIT` | H3 vs H4 | 4 bars (4h) | 0 signals | N/A | N/A | N/A |
| `META-2-LGBM` | H1 vs H2 | 4 bars (4h) | 4 signals (`SOLUSDT`, `ETHUSDT`) | $\hat{p} \in [0.184, 0.321]$ | `BELOW_PROBABILITY_THRESHOLD` | `COOLDOWN_ACTIVE` |
| `META-2-LGBM` | H3 vs H4 | 4 bars (4h) | 4 signals (`SOLUSDT`, `ETHUSDT`) | $\hat{p} \in [0.184, 0.321]$ | `BELOW_PROBABILITY_THRESHOLD` | `COOLDOWN_ACTIVE` |
| `META-3-XGB` | H1 vs H2 | 4 bars (4h) | 2 signals (`BTCUSDT`) | $\hat{p} = 0.1245, 0.1980$ | `BELOW_PROBABILITY_THRESHOLD` | `COOLDOWN_ACTIVE` |
| `META-3-XGB` | H3 vs H4 | 4 bars (4h) | 0 signals | N/A | N/A | N/A |

**Conclusion:** Cooldown logic was active and properly rejected signals in H2 and H4. However, every single candidate signal that arrived within a 4-hour cooldown window also had a model confidence score substantially lower than $\tau = 0.50$ (and $\tau = 0.55$). Consequently, under H1/H3, these signals were already rejected by the probability filter. The probability filter completely subsumed the cooldown filter, establishing an exact mathematical proof for the observed metric identity.

---

## 4. Audit B — PnL and Cost Reconciliation

### 4.1 Trade-Level Accounting Identity
Every individual trade record across the 13 ledgers was verified against the canonical accounting equation:
$$\text{Net PnL} = \text{Gross PnL} - \text{Total Fees} - \text{Slippage Cost} + \text{Funding Payment}$$

- **Total Trades Audited:** 3,116 trades ($2,851$ Benchmark-0 + $265$ Candidate trades).
- **Identity Adherence:** 3,116 of 3,116 trades ($100.0\%$) matched within $\$0.0001$.
- **Discrepancies:** Exactly 0.

### 4.2 Aggregate PnL and Friction Summary

| Candidate / Benchmark | Total Trades | Gross PnL ($) | Total Fees ($) | Total Slippage ($) | Net PnL ($) | Profit Factor | Net Expectancy (bps) | Stress Net PnL ($) | Stress PF |
|---|---|---|---|---|---|---|---|---|---|
| `BENCHMARK-0` | 2,851 | 4,233.15 | 2,850.51 | 1,139.21 | **243.43** | 1.007 | +3.31 | -1,820.55 | 0.950 |
| `META-1-LOGIT_H1` | 20 | -66.86 | 14.28 | 5.71 | **-86.85** | 0.801 | -41.48 | -100.97 | 0.776 |
| `META-1-LOGIT_H2` | 20 | -66.86 | 14.28 | 5.71 | **-86.85** | 0.801 | -41.48 | -100.97 | 0.776 |
| `META-1-LOGIT_H3` | 11 | -170.83 | 7.75 | 3.10 | **-181.68** | 0.413 | -163.50 | -189.39 | 0.400 |
| `META-1-LOGIT_H4` | 11 | -170.83 | 7.75 | 3.10 | **-181.68** | 0.413 | -163.50 | -189.39 | 0.400 |
| `META-2-LGBM_H1` | 66 | 162.29 | 47.53 | 19.01 | **95.74** | 1.147 | +14.13 | 49.18 | 1.072 |
| `META-2-LGBM_H2` | 66 | 162.29 | 47.53 | 19.01 | **95.74** | 1.147 | +14.13 | 49.18 | 1.072 |
| `META-2-LGBM_H3` | 31 | 1.94 | 22.37 | 8.95 | **-20.20** | 0.931 | -6.32 | -41.99 | 0.865 |
| `META-2-LGBM_H4` | 31 | 1.94 | 22.37 | 8.95 | **-20.20** | 0.931 | -6.32 | -41.99 | 0.865 |
| `META-3-XGB_H1` | 9 | 35.35 | 6.42 | 2.57 | **26.36** | 1.319 | +29.77 | 20.06 | 1.233 |
| `META-3-XGB_H2` | 9 | 35.35 | 6.42 | 2.57 | **26.36** | 1.319 | +29.77 | 20.06 | 1.233 |
| `META-3-XGB_H3` | 0 | 0.00 | 0.00 | 0.00 | **0.00** | 1.000 | 0.00 | 0.00 | 1.000 |
| `META-3-XGB_H4` | 0 | 0.00 | 0.00 | 0.00 | **0.00** | 1.000 | 0.00 | 0.00 | 1.000 |

### 4.3 Metric Formulas and Numerator/Denominator Audit
1. **Profit Factor (PF):**
   $$\text{PF} = \frac{\sum_{t \in \text{Wins}} \text{Net PnL}_t}{\sum_{t \in \text{Losses}} |\text{Net PnL}_t|}$$
   For zero-loss cases with positive wins, PF is clamped to 10.0; for zero-trade runs, it defaults to 1.000. Recomputed values matched `res['profit_factor']` within $0.001$.
2. **Net Expectancy (bps):**
   $$\text{Expectancy} = \left(\frac{1}{N} \sum_{t=1}^N \frac{\text{Net PnL}_t}{\text{Notional}_t}\right) \times 10,000\text{ bps}$$
   Recomputed values matched `res['net_expectancy_bps']` within $0.01$ bps.
3. **Friction Stress Tolerance (GATE-8):**
   Standard fees are $5.0$ bps fee $+ 2.0$ bps slip ($14.0$ bps round-trip). Stress friction applies $7.5$ bps fee $+ 3.0$ bps slip ($21.0$ bps round-trip, an incremental $7.0$ bps round-trip deduction on entry notional):
   $$\text{Stress Net PnL}_t = \text{Net PnL}_t - (\text{Notional}_t \times 0.0007)$$
   All stress totals and profit factors matched within $\$0.01$.

### 4.4 Per-Fold and Per-Pair Aggregation Audit
- **Fold Consistency:** Sum of fold trade counts and sum of fold net PnLs equaled the total trade counts and total net PnLs with zero error.
- **Pair Summation Reconciliation:** Sum of trade-level PnLs by symbol matched the portfolio net PnL exactly.
  - When summing the pre-rounded pair net PnLs reported in `res['pairs']` (each rounded to 2 decimal places), differences of $\$0.01$ or $\$0.02$ appear (e.g., Benchmark-0 sum of rounded pairs is $\$243.42$ vs total $\$243.43$; LOGIT H1 is $-\$86.83$ vs $-\$86.85$; LGBM H1 is $\$95.75$ vs $\$95.74$).
  - **Attribution:** This is standard half-cent rounding summation variance ($\sum \text{round}(x_i) \neq \text{round}(\sum x_i)$) across 10 instruments. Trade-level accounting is 100% exact.

---

## 5. Audit C — Bootstrap Pairing and Statistical Inference Audit

### 5.1 Paired Architecture & Calendar-Time Synchronization
Inspection of `backend/ml/inference.py` confirms that the stationary block bootstrap evaluates paired differences over **synchronized calendar-time daily time slices**:

```python
# Synchronous Daily Time Slices (backend/ml/inference.py:27-48)
total_days = max(1, int(np.ceil((end_ms - start_ms) / 86400000.0))) # T = 545 days
mat_ml = build_daily_pnl_matrix(ml_trades, start_ms, end_ms)
mat_bm = build_daily_pnl_matrix(benchmark_trades, start_ms, end_ms)

# Paired Resampling (backend/ml/inference.py:96-104)
sample_ml = mat_ml[resampled_indices]
sample_bm = mat_bm[resampled_indices]
delta_pnl_reps[b] = pnl_ml - pnl_bm
```

1. **Time Unit:** Calendar time (24-hour UTC days, $86,400,000$ ms per day).
2. **Synchronization:** In each replicate $b \in \{1, \dots, 2000\}$, the exact same vector of resampled daily indices `resampled_indices` is extracted from both `mat_ml` and `mat_bm`.
3. **Paired Difference:** On every resampled day $t$, the incremental performance $\Delta_t = \text{ML}_t - \text{BM}_t$ is evaluated concurrently.

### 5.2 Attribution of Point Delta vs Bootstrap Mean Delta
A central question investigated is why `META-2-LGBM_H1` exhibited a deterministic point delta of $-\$147.69$ but a bootstrap mean delta of $-\$85.82$:

$$\text{Point Delta} = \text{Net PnL}_{\text{LGBM H1}} - \text{Net PnL}_{\text{BM}} = \$95.74 - \$243.43 = -\$147.69$$
$$\text{Bootstrap Mean Delta} = \overline{\Delta}_{\text{LGBM H1}} = \overline{\text{PnL}}_{\text{ML}} - \overline{\text{PnL}}_{\text{BM}} = \$93.66 - \$179.48 = -\$85.82$$

#### Point Estimate vs Bootstrap Mean Comparison Table

| Candidate | Det. Net ($) | Det. BM ($) | Point $\Delta$ ($) | Boot ML Mean ($) | Boot BM Mean ($) | Boot $\Delta$ Mean ($) | Point - Boot Diff ($) | Boot 95% CI for $\Delta$ ($) | One-Tailed $p$-Value |
|---|---|---|---|---|---|---|---|---|---|
| `META-1-LOGIT_H1` | -86.85 | 243.43 | -330.28 | -86.45 | 179.48 | -265.93 | **-64.35** | [-8,237.18, 6,829.15] | 0.5155 |
| `META-1-LOGIT_H2` | -86.85 | 243.43 | -330.28 | -86.45 | 179.48 | -265.93 | **-64.35** | [-8,237.18, 6,829.15] | 0.5155 |
| `META-1-LOGIT_H3` | -181.68 | 243.43 | -425.11 | -181.19 | 179.48 | -360.67 | **-64.44** | [-8,366.10, 6,796.10] | 0.5290 |
| `META-1-LOGIT_H4` | -181.68 | 243.43 | -425.11 | -181.19 | 179.48 | -360.67 | **-64.44** | [-8,366.10, 6,796.10] | 0.5290 |
| `META-2-LGBM_H1` | 95.74 | 243.43 | -147.69 | 93.66 | 179.48 | -85.82 | **-61.87** | [-7,914.66, 6,972.69] | 0.4975 |
| `META-2-LGBM_H2` | 95.74 | 243.43 | -147.69 | 93.66 | 179.48 | -85.82 | **-61.87** | [-7,914.66, 6,972.69] | 0.4975 |
| `META-2-LGBM_H3` | -20.20 | 243.43 | -263.63 | -16.90 | 179.48 | -196.38 | **-67.25** | [-8,194.66, 6,962.11] | 0.5070 |
| `META-2-LGBM_H4` | -20.20 | 243.43 | -263.63 | -16.90 | 179.48 | -196.38 | **-67.25** | [-8,194.66, 6,962.11] | 0.5070 |
| `META-3-XGB_H1` | 26.36 | 243.43 | -217.07 | 26.32 | 179.48 | -153.16 | **-63.91** | [-8,149.76, 6,998.56] | 0.5035 |
| `META-3-XGB_H2` | 26.36 | 243.43 | -217.07 | 26.32 | 179.48 | -153.16 | **-63.91** | [-8,149.76, 6,998.56] | 0.5035 |
| `META-3-XGB_H3` | 0.00 | 243.43 | -243.43 | 0.00 | 179.48 | -179.48 | **-63.95** | [-8,252.23, 6,975.77] | 0.5065 |
| `META-3-XGB_H4` | 0.00 | 243.43 | -243.43 | 0.00 | 179.48 | -179.48 | **-63.95** | [-8,252.23, 6,975.77] | 0.5065 |

#### Mathematical Cause of the Discrepancy
Notice that the discrepancy `Point - Boot Diff` is virtually constant across all candidates, clustering precisely at $-\$63.95$. This demonstrates that the difference does not originate in the ML models, but rather in the **Benchmark-0 bootstrap resampling distribution**:
1. For ML candidates, the bootstrap replicate mean matches the deterministic sample mean closely:
   - For `META-3-XGB_H3`: Deterministic $=\$0.00$, Bootstrap Mean $=\$0.00$ ($\Delta = \$0.00$).
   - For `META-3-XGB_H1`: Deterministic $=\$26.36$, Bootstrap Mean $=\$26.32$ ($\Delta = \$0.04$).
   - For `META-1-LOGIT_H1`: Deterministic $=-\$86.85$, Bootstrap Mean $=-\$86.45$ ($\Delta = -\$0.40$).
   - For `META-2-LGBM_H1`: Deterministic $=\$95.74$, Bootstrap Mean $=\$93.66$ ($\Delta = \$2.08$).
2. For `BENCHMARK-0`:
   - Deterministic PnL $= \$243.43$.
   - Bootstrap Replicate Mean $= \$179.48$.
   - Difference $= \$243.43 - \$179.48 = \$63.95$.
3. **Statistical Dispersion of Benchmark-0:**
   - Benchmark-0 executed 2,851 trades across 10 volatile crypto instruments.
   - The standard deviation of Benchmark-0's 545-day path PnL across the 2,000 bootstrap replicates is:
     $$\sigma_{\text{BM reps}} = \$3,805.53$$
   - The Monte Carlo standard error of the mean across $B = 2,000$ replicates is:
     $$\text{SE}(\overline{\text{BM}}) = \frac{\sigma}{\sqrt{B}} = \frac{3,805.53}{\sqrt{2,000}} = \frac{3,805.53}{44.72} = \$85.09$$
   - The observed deviation of $\$63.95$ represents:
     $$z = \frac{243.43 - 179.48}{85.09} = 0.751 \text{ standard errors}$$
4. **Conclusion:** An error of $0.75$ standard errors is entirely standard within a $B = 2,000$ Monte Carlo simulation (the expected 95% sampling interval is $\pm 1.96 \times \$85.09 = \pm \$166.78$). Because LGBM H1 filtered out $97.69\%$ of trades, its path variance is small ($\sigma = \$304.01$, $\text{SE} = \$6.79$), whereas Benchmark-0's enormous path variance drives the sample delta mean deviation.

### 5.3 Confidence Interval and One-Sided Tail Convention
1. **Confidence Interval Construction:**
   The 95% CI is computed via Efron's empirical percentile method:
   $$\text{CI}_{95} = [\hat{q}_{0.025}, \hat{q}_{0.975}]$$
   For `META-2-LGBM_H1`, the interval is $[-\$7,914.66, +\$6,972.69]$. Because this interval spans zero by thousands of dollars, any hypothesis of positive incremental alpha is rejected.
2. **One-Sided Tail Convention:**
   In `backend/ml/inference.py`:
   $$p = \frac{1}{B} \sum_{b=1}^B \mathbb{I}(\Delta_b \le 0.0)$$
   - This measures the empirical fraction of bootstrap replicates where the ML model fails to outperform Benchmark-0.
   - For `META-2-LGBM_H1`, $p = 0.4975$. This indicates that in $49.75\%$ of resampled market histories, LGBM H1 performed worse than or equal to Benchmark-0, while in $50.25\%$ it performed better.
   - A $p$-value of $\approx 0.50$ confirms that the model's incremental performance is statistically indistinguishable from zero (pure noise).
   - Absolute statistical significance requires $\hat{q}_{0.025} > 0.0$ ($p < 0.025$). Since $\hat{q}_{0.025} = -\$7,914.66$, `statistically_significant` is unambiguously `False`.

---

## 6. Audit D — Sparse-Trade Interpretation and Gate Compliance

### 6.1 Mark-to-Market MDD Under Shared Capital
All meta-models reported low mark-to-market maximum drawdown figures ($0.00\%$ to $3.74\%$), compared to Benchmark-0's $20.67\%$:

```python
# Shared Capital Dynamics (backend/backtest/portfolio_engine.py)
# Initial Capital = $10,000 per fold
# Position Size = $1,000 notional (10% allocation)
# Cash Allocation = 90% when 1 position active, 100% when 0 positions active
```

1. **Mechanics of Low MDD:**
   In `CanonicalPortfolioEngine`, portfolio equity equals cash plus open position mark-to-market value. Because the meta-models rejected between $97.69\%$ and $100.00\%$ of all candidate trades, the portfolio remained $100\%$ in cash for $>97\%$ of the 13,080 hourly candles.
2. **Loss Damping:**
   When an active trade was entered, it represented at most $\$1,000$ notional ($10\%$ of portfolio equity). Even an extreme $10\%$ adverse price swing on an individual position produces an unrealized loss of $\$100$, which registers as only a $1.0\%$ drawdown on the $\$10,000$ shared-capital account.
3. **Artifact of Inactivity:**
   For `META-3-XGB_H3` and `H4`, $0$ trades were executed across all 3 folds. The portfolio remained entirely in cash ($10,000.00$), yielding an exact MDD of $0.00\%$. While $0.00\%$ passes GATE-1 ($\le 15.0\%$), it reflects complete capital inactivity, not risk management alpha.

### 6.2 Candidate Rejection and Sparsity Breakdown Table

| Candidate | Total Signals | Trades Taken | Rejections | Rejection Rate (%) | MTM MDD (%) | Zero Folds (of 3) | Zero Pairs (of 10) |
|---|---|---|---|---|---|---|---|
| `BENCHMARK-0` | 2,851 | 2,851 | 0 | 0.00% | 20.67% | 0 | 0 |
| `META-1-LOGIT_H1` | 2,851 | 20 | 2,831 | 99.30% | 3.74% | 1 (Fold 2) | 0 |
| `META-1-LOGIT_H2` | 2,851 | 20 | 2,831 | 99.30% | 3.74% | 1 (Fold 2) | 0 |
| `META-1-LOGIT_H3` | 2,851 | 11 | 2,840 | 99.61% | 3.30% | 2 (Folds 1, 2) | 3 (`ETH`, `BNB`, `LTC`) |
| `META-1-LOGIT_H4` | 2,851 | 11 | 2,840 | 99.61% | 3.30% | 2 (Folds 1, 2) | 3 (`ETH`, `BNB`, `LTC`) |
| `META-2-LGBM_H1` | 2,851 | 66 | 2,785 | 97.69% | 2.05% | 0 | 0 |
| `META-2-LGBM_H2` | 2,851 | 66 | 2,785 | 97.69% | 2.05% | 0 | 0 |
| `META-2-LGBM_H3` | 2,851 | 31 | 2,820 | 98.91% | 1.29% | 0 | 0 |
| `META-2-LGBM_H4` | 2,851 | 31 | 2,820 | 98.91% | 1.29% | 0 | 0 |
| `META-3-XGB_H1` | 2,851 | 9 | 2,842 | 99.68% | 0.81% | 1 (Fold 1) | 3 (`BNB`, `SOL`, `LTC`) |
| `META-3-XGB_H2` | 2,851 | 9 | 2,842 | 99.68% | 0.81% | 1 (Fold 1) | 3 (`BNB`, `SOL`, `LTC`) |
| `META-3-XGB_H3` | 2,851 | 0 | 2,851 | 100.00% | 0.00% | 3 (Folds 1, 2, 3) | 10 (All 10 pairs) |
| `META-3-XGB_H4` | 2,851 | 0 | 2,851 | 100.00% | 0.00% | 3 (Folds 1, 2, 3) | 10 (All 10 pairs) |

### 6.3 Spatial and Activity Gate Evaluation on Zero-Trade Pairs
Inspection of `backend/strategy/qualification.py` (lines 154–218) confirms how zero-trade pairs are evaluated:
1. **Frozen Denominator:** GATE-5 and GATE-7 strictly evaluate against the frozen denominator of **10 Qualified Pairs**.
2. **Activity Hurdle (GATE-5):** Requires $\ge 20$ trades per pair. Any pair with $< 20$ trades (including zero trades) is marked `INSUFFICIENT_SAMPLE` and fails.
3. **Spatial Robustness (GATE-7):**
   ```python
   # Pair must have >= 20 trades AND positive net PnL to count as pass
   if len(pnls) >= 20 and p_net > 0:
       positive_pairs += 1
   ```
   If a pair has zero trades, `len(pnls) == 0 < 20`, so it is strictly evaluated as `FAIL`.
4. **Scoring:** For `META-2-LGBM_H1` (the most active candidate with 66 trades), the trades were distributed across pairs as follows: `BTC` (9), `ETH` (4), `SOL` (11), `BNB` (6), `XRP` (7), `ADA` (5), `AVAX` (8), `LINK` (8), `DOGE` (5), `LTC` (3). Not a single pair reached the 20-trade threshold. Consequently:
   - GATE-5 score: **0 of 10 pairs satisfied minimum activity** (FAIL).
   - GATE-7 score: **0 of 10 pairs profitable with adequate sample** (FAIL).
5. **Statistical Safeguard:** The institutional gates operated exactly as intended: they prevented low-activity models from qualifying on spurious win-rate or low-drawdown anomalies by strictly requiring sample size and spatial generalizability.

---

## 7. Qualification Gate Scorecard Audit

The following table summarizes the evaluation of all 8 frozen qualification gates across the 13 configurations:

| Candidate | GATE-1 (MDD $\le 15\%$) | GATE-2 (Exp $\ge 8$ bps) | GATE-3 (PF $\ge 1.25$) | GATE-4 ($N \ge 150$) | GATE-5 ($N_p \ge 20$) | GATE-6 (WF $\ge 2/3$) | GATE-7 (Spatial $\ge 7/10$) | GATE-8 (Stress PnL $>0$) | Final Certified Status |
|---|---|---|---|---|---|---|---|---|---|
| `BENCHMARK-0` | FAIL (20.67%) | FAIL (3.3 bps) | FAIL (1.007) | **PASS** (2,851) | **PASS** (10/10) | **PASS** (2/3) | FAIL (6/10) | FAIL (-$1,820.55) | `NO_QUALIFIED_STRATEGY` |
| `META-1-LOGIT_H1` | **PASS** (3.74%) | FAIL (-41.5 bps) | FAIL (0.801) | FAIL (20) | FAIL (0/10) | FAIL (1/3) | FAIL (0/10) | FAIL (-$100.97) | `NO_QUALIFIED_STRATEGY` |
| `META-1-LOGIT_H2` | **PASS** (3.74%) | FAIL (-41.5 bps) | FAIL (0.801) | FAIL (20) | FAIL (0/10) | FAIL (1/3) | FAIL (0/10) | FAIL (-$100.97) | `NO_QUALIFIED_STRATEGY` |
| `META-1-LOGIT_H3` | **PASS** (3.30%) | FAIL (-163.5 bps)| FAIL (0.413) | FAIL (11) | FAIL (0/10) | FAIL (1/3) | FAIL (0/10) | FAIL (-$189.39) | `NO_QUALIFIED_STRATEGY` |
| `META-1-LOGIT_H4` | **PASS** (3.30%) | FAIL (-163.5 bps)| FAIL (0.413) | FAIL (11) | FAIL (0/10) | FAIL (1/3) | FAIL (0/10) | FAIL (-$189.39) | `NO_QUALIFIED_STRATEGY` |
| `META-2-LGBM_H1` | **PASS** (2.05%) | **PASS** (+14.1 bps) | FAIL (1.147) | FAIL (66) | FAIL (0/10) | FAIL (1/3) | FAIL (0/10) | **PASS** (+$49.18) | `NO_QUALIFIED_STRATEGY` |
| `META-2-LGBM_H2` | **PASS** (2.05%) | **PASS** (+14.1 bps) | FAIL (1.147) | FAIL (66) | FAIL (0/10) | FAIL (1/3) | FAIL (0/10) | **PASS** (+$49.18) | `NO_QUALIFIED_STRATEGY` |
| `META-2-LGBM_H3` | **PASS** (1.29%) | FAIL (-6.3 bps) | FAIL (0.931) | FAIL (31) | FAIL (0/10) | FAIL (1/3) | FAIL (0/10) | FAIL (-$41.99) | `NO_QUALIFIED_STRATEGY` |
| `META-2-LGBM_H4` | **PASS** (1.29%) | FAIL (-6.3 bps) | FAIL (0.931) | FAIL (31) | FAIL (0/10) | FAIL (1/3) | FAIL (0/10) | FAIL (-$41.99) | `NO_QUALIFIED_STRATEGY` |
| `META-3-XGB_H1` | **PASS** (0.81%) | **PASS** (+29.8 bps) | **PASS** (1.319) | FAIL (9) | FAIL (0/10) | **PASS** (2/3) | FAIL (0/10) | **PASS** (+$20.06) | `NO_QUALIFIED_STRATEGY` |
| `META-3-XGB_H2` | **PASS** (0.81%) | **PASS** (+29.8 bps) | **PASS** (1.319) | FAIL (9) | FAIL (0/10) | **PASS** (2/3) | FAIL (0/10) | **PASS** (+$20.06) | `NO_QUALIFIED_STRATEGY` |
| `META-3-XGB_H3` | **PASS** (0.00%) | FAIL (0.0 bps) | FAIL (1.000) | FAIL (0) | FAIL (0/10) | FAIL (0/3) | FAIL (0/10) | FAIL ($0.00) | `NO_QUALIFIED_STRATEGY` |
| `META-3-XGB_H4` | **PASS** (0.00%) | FAIL (0.0 bps) | FAIL (1.000) | FAIL (0) | FAIL (0/10) | FAIL (0/3) | FAIL (0/10) | FAIL ($0.00) | `NO_QUALIFIED_STRATEGY` |

---

## 8. Audit Certification and Recommendations

### 8.1 Audit Certification
- **Status:** `PHASE_5D3_1_AUDIT_PASS`
- **Integrity Findings:**
  1. All 13 trade ledgers and execution summaries are internally and mathematically consistent.
  2. Cooldown policy mechanics operate strictly as specified; metric invariance between H1/H2 and H3/H4 is proven to be caused by probability threshold dominance.
  3. Paired stationary bootstrap inference is calendar-synchronized; sample mean delta deviations are proven to be standard Monte Carlo sampling variance ($\le 0.75\text{ SE}$).
  4. Spatial robustness and sample size gates properly penalize trade sparsity; low MDD is verified as cash drag.
  5. Universal holdout quarantine ($2026-04-26\text{T}00:00:00\text{Z}$) and server isolation (port 8000) were 100% preserved.

### 8.2 Research Recommendations for Next Phase
1. **Address Extreme Threshold Restrictiveness:** Meta-labeling with default classification thresholds ($\tau = 0.50, 0.55$) resulted in severe over-filtering ($97.7\%$ to $100\%$ rejection rate). Future work should examine dynamic calibration, quantile-based top-$K$ selection, or rank-ordered trade selection to ensure sufficient sample sizes ($N \ge 150$).
2. **Base Strategy Viability:** The underlying signal generator `STRAT-B-01` remains `UNQUALIFIED_BASELINE`. A meta-model can filter poor breakouts, but if the primary generator generates negative gross alpha after friction across most market regimes, meta-filtering cannot synthesize a qualified institutional strategy out of thin air.
3. **Preserve Frozen Protocol:** Do not alter the 8 frozen qualification gates. They successfully protected the project from qualifying low-sample, cash-diluted strategies.
