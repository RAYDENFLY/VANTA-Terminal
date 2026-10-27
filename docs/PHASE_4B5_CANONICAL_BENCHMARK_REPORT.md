# VANTA Terminal — Phase 4B.5 Canonical Benchmark Revalidation Report

**Document ID**: `VANTA-DOCS-4B5-CANONICAL-BENCHMARK-REPORT`  
**Execution Timestamp**: `2026-10-27T07:33:28Z`  
**Protocol Version**: Phase 4A.1 / 4A.2 Frozen Benchmark Protocol  
**Simulation Engine**: `CanonicalPortfolioEngine` (`backend/backtest/portfolio_engine.py`)  
**Accounting Standard**: Single-Pool Shared Margin ($10,000), 1.0x Gross Leverage Cap, MTM Candle Drawdown  
**Certified Outcome**: `REVALIDATION_PASS_NO_QUALIFIED_STRATEGY`  
**Certified Baseline**: `None`  
**Unqualified Baseline**: `STRAT-B-01 (Donchian Breakout / Trend Following — 1H)`  

---

## 1. Executive Summary

Phase 4B.5 executed a controlled, deterministic re-evaluation of the three pre-registered Phase 4B candidate strategies across the 10 eligible perpetual cryptocurrency pairs (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, `XRPUSDT`, `ADAUSDT`, `AVAXUSDT`, `LINKUSDT`, `DOGEUSDT`, `LTCUSDT`). 

The objective of this phase was to determine whether the previous Phase 4B benchmark conclusions (`NO_QUALIFIED_STRATEGY`, with Strategy B serving as the non-compliant reference baseline) remain valid under a single-pool shared collateral model, chronological multi-stream dispatch, capital rationing, and continuous candle-level mark-to-market drawdown accounting.

### Certified Revalidation Finding

The global benchmark revalidation outcome is definitively certified as:

$$\mathbf{REVALIDATION\_PASS\_NO\_QUALIFIED\_STRATEGY}$$

1. **Zero Qualified Strategies**: No strategy satisfied all 8 frozen qualification gates.
2. **Strategy B Baseline Vulnerability Confirmed**: Under the legacy Phase 4B accounting model, Strategy B was reported to have passed GATE-1 with an MDD of **14.89%** (based solely on closed-trade account balances). Under the canonical engine's continuous mark-to-market accounting, Strategy B experienced a maximum drawdown of **20.67%**, decisively failing **GATE-1 ($\le 15.0\%$)**. Furthermore, Strategy B failed **GATE-2** (Expectancy: +3.31 bps vs. +8.0 bps hurdle), **GATE-3** (Profit Factor: 1.007 vs. 1.25 hurdle), **GATE-7** (Spatial Robustness: 6/10 vs. 7/10 profitable pairs), and **GATE-8** (Friction Stress: Net PnL -$2,222.20 at 21.0 bps friction).
3. **Designation Maintained**: Strategy B is designated as the **`UNQUALIFIED_BASELINE`** for Phase 5 reference comparisons. Its parameters, code, and thresholds remain frozen and unmodified.
4. **High-Frequency Collapse Confirmed**: Strategies A (Sweep-Reclaim, 15m) and C (Mean Reversion, 15m) suffered catastrophic friction decay under shared capital, losing **-$18,221.61** (MTM MDD: 69.12%) and **-$6,229.42** (MTM MDD: 29.66%) respectively, failing 6 of 8 gates each.

---

## 2. Methodological & Architectural Transition (Phase 4B vs. Phase 4B.5)

| Dimension | Legacy Phase 4B Model | Canonical Phase 4B.5 Engine | Practical Economic Impact |
| :--- | :--- | :--- | :--- |
| **Capital Allocation** | 10 independent $10,000 sub-accounts ($100,000 total deployed) mapped to synthetic $10k base | Single shared $10,000 cash pool per fold | Eliminates synthetic $100k capital buffering; reflects realistic fund scale |
| **Gross Leverage Cap** | Unconstrained per pair | Strict 1.0x unleveraged futures cap ($\sum \text{Notional} \le \text{Equity}$) | Multi-pair positions compete for finite collateral |
| **Event Dispatch** | Pair-by-pair batch simulation; trades interleaved post-hoc | Chronological `MultiStreamEventQueue` (`BarFrame` lockstep) | Prevents temporal out-of-order execution and retro-active fills |
| **Position Sizing** | Fixed $1,000 initial notional per pair regardless of drawdown | Dynamic 10% of instantaneous portfolio equity | Sizing scales down during equity drawdowns and scales up during expansions |
| **Drawdown Metric** | Closed-trade equity curve (balance jumps only on trade close) | Candle-by-candle Mark-to-Market equity curve ($E_t = C_t + \sum U_t$) | Captures severe intrabar adverse excursions; eliminates closed-trade blindness |
| **Intrabar Ambiguity** | Optimistic / Ambiguous | Strict `CONSERVATIVE_SL_FIRST` with gap-through-stop fill | Pessimistic, institutionally defensible stop fills |
| **Fold Resets** | PnL summed into synthetic equity curve | Independent $10,000 reset per fold; boundary position flattening | Clean temporal isolation without cross-fold capital carryover |

### Analysis of Capital Rationing and Order Rejections

In Phase 4B.5, the engine logged **0 order rejections** across all three candidate strategies. This occurred because:
1. Sizing is parameterized at **10% of portfolio equity** per trade.
2. At 1.0x gross leverage, the portfolio accommodates exactly $\lfloor 1.0 / 0.10 \rfloor = 10$ simultaneous positions.
3. The evaluation universe consists of exactly 10 pairs. Even when all 10 pairs triggered entry signals simultaneously, each pair claimed 10% margin, exhausting exactly 100% of free collateral without triggering rejections.
4. However, dynamic sizing meant that during losing streaks (such as Fold 3 in Strategy B, and all folds in Strategies A and C), trade notionals contracted from $1,000 to ~$870 (Strategy B) and ~$320 (Strategy A), naturally mitigating nominal dollar losses while accentuating percentage drawdowns relative to the high-watermark.

---

## 3. Candidate Strategy B: Donchian Breakout / Trend Following (1H)

### 3.1 Side-by-Side Comparison: Phase 4B vs. Phase 4B.5

| Metric | Phase 4B (Legacy Isolated) | Phase 4B.5 (Canonical Shared) | Delta / Shift | Evaluation / Significance |
| :--- | :--- | :--- | :--- | :--- |
| **Total OOS Trades** | 2,851 | 2,851 | 0 (Identical) | Deterministic signal parity preserved |
| **Total Net PnL ($)** | +$914.31 | +$243.43 | -$670.88 (-73.4%) | Collateral constraints & dynamic sizing reduced nominal gains |
| **Net Return on Base** | +9.14% (on synthetic $10k) | +2.43% (on $10k shared pool) | -6.71% | Real economic return on portfolio capital |
| **Profit Factor (PF)** | 1.029 | 1.007 | -0.022 | Decreased; barely above breakeven (1.000) |
| **Net Expectancy (bps)** | +3.26 bps | +3.31 bps | +0.05 bps | Remains well below +8.0 bps hurdle |
| **95% Confidence Interval** | [-10.74, +17.26] bps | [-10.69, +17.31] bps | $\pm 0.05$ bps | Indistinguishable from zero (statistically unproven) |
| **Win Rate (%)** | 25.53% | 25.53% | 0.00% | Low-win-rate, high-payoff trend profile |
| **Total Fees Paid ($)** | $2,848.17 | $2,949.30 | +$101.13 | Taker fee 5.0 bps per side accurately reconciled |
| **Total Slippage ($)** | $1,137.69 | $1,178.06 | +$40.37 | Slippage 2.0 bps per side accurately reconciled |
| **Reported MDD (%)** | **14.89% (Passed)** | **20.67% (FAILED)** | **+5.78%** | **Breaches GATE-1 threshold ($\le 15.0\%$)** |
| **Closed-Trade MDD (%)** | 14.89% | 21.42% (Composite) | +6.53% | Reflects true sequential compounding on shared pool |
| **Profitable Folds** | 2 of 3 | 2 of 3 | 0 | Fold 1 & 2 profitable; Fold 3 losing |
| **Profitable Pairs** | 6 of 10 | 6 of 10 | 0 | Spatial distribution identical |
| **Order Rejections** | N/A | 0 | 0 | Leverage cap fully accommodated 10 positions |
| **Stress Net PnL (21 bps)**| -$1,078.63 (PF: 0.97) | -$2,222.20 (PF: 0.934) | -$1,143.57 | Severe friction fragility confirmed |

### 3.2 Walk-Forward Per-Fold Performance Breakdown

Each fold was initialized with an independent $10,000 cash pool and zero position carryover:

| Fold ID | Selected Config | Initial Equity | Final Equity | Net PnL ($) | Return (%) | MTM MDD (%) | Closed-Trade MDD (%) | Trades | Win Rate (%) | Profit Factor | Expectancy (bps) | Profitable? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | B-09 | $10,000.00 | $11,352.67 | +$1,352.67 | +13.53% | **18.19%** | 14.17% | 954 | 23.48% | 1.095 | +12.54 bps | **YES** |
| **Fold 2** | B-09 | $10,000.00 | $10,150.88 | +$150.88 | +1.51% | **14.89%** | 12.96% | 859 | 25.15% | 1.017 | +1.72 bps | **YES** |
| **Fold 3** | B-05 | $10,000.00 | $8,739.88 | -$1,260.12 | -12.60% | **20.67%** | 18.48% | 1,038 | 27.75% | 0.872 | -12.69 bps | **NO** |

> **Key Audit Finding on Drawdown**:
> In Fold 1, while closed-trade drawdown was only **14.17%**, the continuous candle-level mark-to-market drawdown reached **18.19%**. This proves that open positions suffered substantial unrealized drawdowns during their lifecycle before partially recovering at exit. In Fold 3, both closed-trade MDD (**18.48%**) and MTM MDD (**20.67%**) severely breached the 15.0% threshold.

### 3.3 Per-Pair Performance (10 Qualified Pairs)

| Pair | Trades Count | Net PnL ($) | Win Rate (%) | Lifecycle State | Spatial Gate Status | Primary Driver |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **AVAXUSDT** | 290 | +$763.75 | 26.90% | `ELIGIBLE` | **PASS** | Strong multi-month directional expansions |
| **DOGEUSDT** | 274 | +$555.42 | 27.74% | `ELIGIBLE` | **PASS** | Extended breakout continuation runs |
| **XRPUSDT** | 294 | +$417.14 | 27.55% | `ELIGIBLE` | **PASS** | High trend-to-noise ratio in 2024 |
| **SOLUSDT** | 262 | +$329.56 | 29.39% | `ELIGIBLE` | **PASS** | Moderate trend capture; low chop |
| **ADAUSDT** | 273 | +$311.29 | 24.18% | `ELIGIBLE` | **PASS** | High-beta trend follower |
| **ETHUSDT** | 275 | +$181.38 | 28.73% | `ELIGIBLE` | **PASS** | Modest trend gains; friction drag |
| **LINKUSDT** | 320 | -$202.17 | 22.81% | `ELIGIBLE` | **FAIL** | False breakout whipsaws |
| **BNBUSDT** | 290 | -$552.14 | 23.79% | `ELIGIBLE` | **FAIL** | Mean-reverting range chop |
| **BTCUSDT** | 287 | -$755.85 | 21.95% | `ELIGIBLE` | **FAIL** | Severe channel-boundary false breakouts |
| **LTCUSDT** | 286 | -$804.96 | 23.08% | `ELIGIBLE` | **FAIL** | Prolonged low-volatility range bound bleed |
| **Summary** | **2,851** | **+$243.43** | **25.53%** | — | **6 / 10 Pass** | **Fails GATE-7 ($\ge 7/10$)** |

### 3.4 Qualification Gates Re-Evaluation for Strategy B

```
========================================================================================
STRATEGY B QUALIFICATION GATE AUDIT MATRIX (CANONICAL ENGINE)
========================================================================================
GATE-1: Maximum Drawdown (MDD)               <= 15.0%        20.67%        [FAILED]
GATE-2: Net Expectancy per Trade             >= +8.0 bps     +3.31 bps     [FAILED]
GATE-3: Profit Factor (PF)                   >= 1.25         1.007         [FAILED]
GATE-4: Aggregate Trade Count                >= 150 trades   2,851 trades  [PASSED]
GATE-5: Per-Pair Minimum Activity            >= 20 trades    10 / 10 >= 20 [PASSED]
GATE-6: Walk-Forward Consistency             >= 2 of 3 Folds 2 of 3 Folds  [PASSED]
GATE-7: Spatial Robustness                   >= 7 of 10 Pairs 6 of 10 Pairs [FAILED]
GATE-8: Friction Stress Tolerance (21 bps)   Net PnL > $0    -$2,222.20    [FAILED]
========================================================================================
GLOBAL CERTIFICATION: NO_QUALIFIED_STRATEGY (Failed 5 of 8 Gates)
DESIGNATION: UNQUALIFIED_BASELINE (Hurdle baseline for ML models)
========================================================================================
```

---

## 4. Candidate Strategy A: Sweep-Reclaim (15m)

### 4.1 Side-by-Side Comparison: Phase 4B vs. Phase 4B.5

| Metric | Phase 4B (Legacy Isolated) | Phase 4B.5 (Canonical Shared) | Delta / Shift | Evaluation |
| :--- | :--- | :--- | :--- | :--- |
| **Total OOS Trades** | 16,934 | 16,934 | 0 | Identical trade count |
| **Total Net PnL ($)** | -$27,264.91 | -$18,221.61 | +$9,043.30 | Capital shrinkage reduced dollar losses |
| **Net Return on Base** | -272.65% (unbounded) | -182.22% (composite) | +90.43% | Compounding on shrinking equity pool |
| **Profit Factor (PF)** | 0.660 | 0.674 | +0.014 | Unchanged catastrophic loss profile |
| **Net Expectancy (bps)** | -17.15 bps | -17.07 bps | +0.08 bps | Negative expectancy after 14 bps friction |
| **Total Fees Paid ($)** | $14,809.71 | $10,125.50 | -$4,684.21 | Scaled with lower average position notional |
| **Total Slippage ($)** | $5,619.85 | $3,842.34 | -$1,777.51 | Scaled with lower average position notional |
| **Mark-to-Market MDD** | 272.65% (unbounded) | **69.12% (Fold 2)** | — | Severe capital degradation in every fold |
| **Profitable Folds** | 0 of 3 | 0 of 3 | 0 | Failed in all 3 folds |
| **Profitable Pairs** | 0 of 10 | 0 of 10 | 0 | Failed on all 10 pairs |
| **Stress Net PnL (21 bps)**| -$35,848.40 | -$22,132.74 (PF: 0.575)| +$13,715.66 | Catastrophic failure under elevated fees |

### 4.2 Walk-Forward Per-Fold Breakdown for Strategy A

| Fold ID | Selected Config | Initial Equity | Final Equity | Net PnL ($) | Return (%) | MTM MDD (%) | Closed MDD (%) | Trades | Win Rate (%) | Profit Factor | Expectancy (bps) | Profitable? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | A-11 | $10,000.00 | $4,937.60 | -$5,062.40 | -50.62% | 51.65% | 51.57% | 4,386 | 30.71% | 0.756 | -15.58 bps | **NO** |
| **Fold 2** | A-11 | $10,000.00 | $3,211.06 | -$6,788.94 | -67.89% | 69.12% | 69.12% | 5,685 | 29.27% | 0.627 | -19.04 bps | **NO** |
| **Fold 3** | A-11 | $10,000.00 | $3,629.73 | -$6,370.27 | -63.70% | 65.81% | 65.75% | 6,863 | 31.46% | 0.665 | -16.29 bps | **NO** |

**Conclusion**: Strategy A generates excessive turnover (16,934 trades). Combined round-trip transaction costs of 14.0 bps ($13,967.84 total fees + slippage) exceed the strategy's gross edge, causing irreversible equity erosion across every single fold and pair. Fails 6 of 8 gates.

---

## 5. Candidate Strategy C: Bollinger Bands + RSI Mean Reversion (15m)

### 5.1 Side-by-Side Comparison: Phase 4B vs. Phase 4B.5

| Metric | Phase 4B (Legacy Isolated) | Phase 4B.5 (Canonical Shared) | Delta / Shift | Evaluation |
| :--- | :--- | :--- | :--- | :--- |
| **Total OOS Trades** | 3,362 | 3,362 | 0 | Identical trade count |
| **Total Net PnL ($)** | -$9,144.30 | -$6,229.42 | +$2,914.88 | Sizing shrinkage on drawdown |
| **Net Return on Base** | -91.44% | -62.29% | +29.15% | Cumulative decline across folds |
| **Profit Factor (PF)** | 0.530 | 0.618 | +0.088 | Deeply unprofitable |
| **Net Expectancy (bps)** | -21.43 bps | -21.00 bps | +0.43 bps | Severe negative edge per trade |
| **Total Fees Paid ($)** | $4,127.34 | $2,894.18 | -$1,233.16 | Friction accounting |
| **Total Slippage ($)** | $1,602.81 | $1,122.91 | -$479.90 | Friction accounting |
| **Mark-to-Market MDD** | 91.44% | **29.66% (Fold 1)** | — | Exceeds 15% threshold in Folds 1 & 2 |
| **Profitable Folds** | 0 of 3 | 0 of 3 | 0 | Failed across all 3 folds |
| **Profitable Pairs** | 0 of 10 | 0 of 10 | 0 | Failed on all 10 pairs |
| **Stress Net PnL (21 bps)**| -$11,988.50 | -$8,299.99 (PF: 0.516) | +$3,688.51 | Fragile to friction |

### 5.2 Walk-Forward Per-Fold Breakdown for Strategy C

| Fold ID | Selected Config | Initial Equity | Final Equity | Net PnL ($) | Return (%) | MTM MDD (%) | Closed MDD (%) | Trades | Win Rate (%) | Profit Factor | Expectancy (bps) | Profitable? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | C-10 | $10,000.00 | $7,069.20 | -$2,930.80 | -29.31% | 29.66% | 29.62% | 1,402 | 31.60% | 0.597 | -23.71 bps | **NO** |
| **Fold 2** | C-10 | $10,000.00 | $7,979.83 | -$2,020.17 | -20.20% | 22.43% | 22.10% | 1,155 | 36.10% | 0.638 | -19.46 bps | **NO** |
| **Fold 3** | C-10 | $10,000.00 | $8,721.55 | -$1,278.45 | -12.78% | 13.38% | 13.29% | 805 | 43.73% | 0.627 | -18.49 bps | **NO** |

**Conclusion**: Mean-reversion signals systematically entered counter-trend positions during persistent cryptocurrency momentum surges, resulting in repeated stop-outs and trailing barrier failures. Fails 6 of 8 gates.

---

## 6. Comprehensive 8-Gate Evaluation Matrix

| Gate ID | Hurdle Requirement | Denominator | Strategy B (Donchian 1H) | Strategy A (Sweep 15m) | Strategy C (MeanRev 15m) |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **GATE-1** | Maximum Drawdown $\le 15.0\%$ | Continuous MTM Equity Curve | **20.67% [FAIL]** | **69.12% [FAIL]** | **29.66% [FAIL]** |
| **GATE-2** | Net Expectancy $\ge +8.0\text{ bps}$ | Aggregate OOS Trades | **+3.31 bps [FAIL]** | **-17.07 bps [FAIL]** | **-21.00 bps [FAIL]** |
| **GATE-3** | Profit Factor $\ge 1.25$ | Realized Net Returns | **1.007 [FAIL]** | **0.674 [FAIL]** | **0.618 [FAIL]** |
| **GATE-4** | Aggregate Trades $\ge 150$ | 10 Qualified Pairs (OOS 1-3)| **2,851 [PASS]** | **16,934 [PASS]** | **3,362 [PASS]** |
| **GATE-5** | Per-Pair Activity $\ge 20$ Trades | 10 Qualified Pairs | **10 / 10 [PASS]** | **10 / 10 [PASS]** | **10 / 10 [PASS]** |
| **GATE-6** | Temporal Consistency $\ge 2/3$ Folds| 3 Rolling WF Folds | **2 / 3 [PASS]** | **0 / 3 [FAIL]** | **0 / 3 [FAIL]** |
| **GATE-7** | Spatial Robustness $\ge 7/10$ Pairs | 10 Qualified Pairs (Frozen) | **6 / 10 [FAIL]** | **0 / 10 [FAIL]** | **0 / 10 [FAIL]** |
| **GATE-8** | Stress Tolerance Net PnL $> \$0$ | 21.0 bps Friction Model | **-$2,222.20 [FAIL]** | **-$22,132.74 [FAIL]**| **-$8,299.99 [FAIL]** |
| **STATUS** | **Certified Outcome** | **All 8 Gates Required** | **NO_QUALIFIED** | **NO_QUALIFIED** | **NO_QUALIFIED** |
| **ROLE** | **Designation** | — | **UNQUALIFIED_BASELINE** | **REJECTED** | **REJECTED** |

---

## 7. Protocol Compliance, Holdout Quarantine & Safety Audit

1. **Universal Holdout Quarantine**:
   - The universal holdout boundary ($t \ge 1777161600000$, `2026-04-26T00:00:00Z`) was strictly quarantined.
   - All loaders and backtest runs enforced `open_time < 1777161600000`.
   - **Zero holdout candles were accessed, inspected, or processed**.
2. **Purge and Embargo Integrity**:
   - 48-hour purge prior to In-Sample boundary strictly prevented trade leakage across fold transitions.
   - 48-hour embargo warmup prior to OOS allowed technical indicators to stabilize without generating unembargoed orders.
3. **Execution Safety and Project Isolation**:
   - Storage location: Entire simulation executed on HDD `D:\vanta-terminal`.
   - Available disk space on `D:`: **54.71 GB free** (mandatory safety reserve of $\ge 10.0\text{ GB}$ strictly preserved).
   - Port 8000: Untouched and unprobed (external PID 24852 preserved).
   - Order execution: Zero live exchange credentials, zero order routing, zero wallet signatures.
   - Concurrency: Strictly sequential single-worker execution (`VANTA_MAX_WORKERS=1`).

---

## 8. Cryptographic Manifest Checksums

The benchmark execution produced deterministic, cryptographically signed manifests saved in `data/benchmarks/phase_4b5/`:

| File Name | Size (Bytes) | SHA-256 Cryptographic Checksum |
| :--- | :---: | :--- |
| `STRAT_B_BENCHMARK.json` | 16,402 | `168e39ce823126bace6d3db1873154ef9721e453d29dd27e773b7f3fb924bdd5` |
| `STRAT_A_BENCHMARK.json` | 16,641 | `f6d2785f4ffa109bf331cf1eae63298045f062bb5b5e582e063de405451cfc3e` |
| `STRAT_C_BENCHMARK.json` | 16,559 | `b55e5e85b3c4a7bf401ce69b93bdbcf6ff07e98b1401b11426d38031faf35e58` |
| `PHASE_4B5_MASTER_SUMMARY.json` | 58,992 | `9f6e1dd61705a42986b705d633c9d723279ba98d3c520c433a027c1e6b2a382d` |
| `manifest_sha256.json` | 398 | `0f2dbffafaa76ca6c67d1656ca010f36f3322199b794101e4df45e45a50787e2` |

---

## 9. Conclusion & Formal Authorization Gate

The Phase 4B.5 benchmark revalidation confirms that:
1. Under an economically realistic, single-pool shared collateral model with mark-to-market drawdown accounting, **none of the three rule-based candidate strategies pass institutional qualification**.
2. Strategy B's previously reported compliance with GATE-1 (14.89% MDD) was an artifact of closed-trade balance jumping; under true candle-level MTM accounting, its drawdown reaches **20.67%**, failing GATE-1 alongside GATE-2, GATE-3, GATE-7, and GATE-8.
3. Designating Strategy B as the **`UNQUALIFIED_BASELINE`** provides a rigorous, reproducible, non-overfit benchmark against which Phase 5 Machine Learning models must compete. To qualify in Phase 5, ML strategies must overcome this hurdle and satisfy all 8 qualification gates without threshold relaxation.

**Certified Exit Status**: `REVALIDATION_PASS_NO_QUALIFIED_STRATEGY`  
**Ready for Phase 5 Authorization Gate**.
