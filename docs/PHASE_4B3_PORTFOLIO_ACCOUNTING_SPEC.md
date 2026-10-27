# VANTA Terminal — Phase 4B.3 Portfolio Accounting Specification

**Document ID**: `VANTA-PHASE4B3-PORTFOLIO-SPEC-20261027`  
**Version**: `1.0.0-FROZEN`  
**Date**: October 27, 2026  
**Auditor**: Quantitative Research & Accounting Architecture  
**Execution Context**: Offline Event-Driven Multi-Pair Simulation Workstation  
**Historical Invariance**: Certified Benchmark Outcome `NO_QUALIFIED_STRATEGY` Preserved  
**Target Architecture**: Shared-Margin Multi-Pair Portfolio Engine (Prepared for Phase 5 ML Arena)  

---

## 1. Executive Context & Scope

Phase 4B.1 and Phase 4B.2 identified foundational discrepancies in how multi-pair trade flows, cash resets, and maximum drawdown were aggregated in the Phase 4B benchmark runner:
1. Trades across different pairs were serialized pair-by-pair rather than interwoven chronologically by exit time (`DISC-4B2-01`).
2. Ten independent $10,000 sub-accounts ($100,000 deployed capital) were mapped onto a synthetic $10,000 normalization convention without shared-margin rationing (`DISC-4B2-02`).
3. Drawdown was evaluated purely on closed-trade cashflows, ignoring intrabar mark-to-market excursions, and allowing negative equity accumulation without a zero bankruptcy floor (`DISC-4B2-03`).
4. Fold boundaries reset cash in the engine, but the combined runner curve compounded cashflows continuously across folds, masking Fold 3's independent risk breach (`DISC-4B2-04`).

This specification establishes the canonical, economically coherent portfolio accounting model for VANTA Terminal. It resolves every identified discrepancy, provides exact mathematical definitions, and sets the frozen foundation for benchmarking Phase 5 Machine Learning models against the `UNQUALIFIED_BASELINE`.

---

## 2. Reconciliation of Existing Maximum Drawdown (MDD) Definitions

To eliminate ambiguity across previous audit reports, five distinct MDD definitions are formalized below.

### 2.1. Formal Definition Taxonomy

```
+----------------------------------------------------------------------------------------------------+
| 1. Pair-Concatenated Trade-Close MDD (Phase 4B Runner)                                              |
|    - Concatenates closed trades by fold, then by symbol (Fold 1: ADA...XRP, Fold 2: ADA...XRP).     |
|    - Cashflow applied upon trade close: cum_equity += t.net_pnl. Intrabar excursions ignored.      |
|    - Strategy B Value: 14.8910% (Reported: 14.89%)                                                 |
|    - Classification: VERIFIED_FROM_CODE_AND_ARTIFACTS                                              |
+----------------------------------------------------------------------------------------------------+
                                           |
                                           v
+----------------------------------------------------------------------------------------------------+
| 2. Chronologically Ordered Trade-Close MDD                                                          |
|    - Merges all closed trades across the 10 pairs strictly by exit timestamp (exit_time_ms).        |
|    - Cashflow applied when trade physically closes in real time. Intrabar excursions ignored.      |
|    - Strategy B Value: 17.1524% (Breaches Gate 1 hurdle of <= 15.0%)                               |
|    - Classification: VERIFIED_FROM_CODE_AND_ARTIFACTS                                              |
+----------------------------------------------------------------------------------------------------+
                                           |
                                           v
+----------------------------------------------------------------------------------------------------+
| 3. Candle-Level Mark-to-Market (MTM) MDD (Canonical Portfolio Metric)                              |
|    - Evaluated at every candle close: Equity(t) = Cash(t) + sum_i UnrealizedPnL_i(t).              |
|    - Captures adverse open-position excursions before trade close.                                 |
|    - Strategy B Fold 3 Value (Normalized $10k base): 20.7210%                                      |
|    - Strategy B Fold 3 Value (10-account $100k base): 2.2295%                                      |
|    - Classification: VERIFIED_FROM_CODE_AND_ARTIFACTS                                              |
+----------------------------------------------------------------------------------------------------+
                                           |
                                           v
+----------------------------------------------------------------------------------------------------+
| 4. Bankruptcy-Floor / Clamped Drawdown                                                             |
|    - Enforces physical account liquidation when Equity <= $0.00. Drawdown clamped at 100.0%.       |
|    - Strategy A Un-clamped Strategy Drag: 272.65% (Loss of $2.72 per $1.00 base capital).          |
|    - Strategy A Clamped Bankruptcy MDD: 100.00% (Reached in Fold 2).                               |
|    - Classification: VERIFIED_FROM_CODE_AND_ARTIFACTS                                              |
+----------------------------------------------------------------------------------------------------+
                                           |
                                           v
+----------------------------------------------------------------------------------------------------+
| 5. Fold-Specific MDD vs Multi-Fold Aggregate                                                       |
|    - Evaluates each 6-month OOS fold independently with its dedicated $10,000 cash balance.        |
|    - Strategy B Chronological Exit MDD: Fold 1 = 12.43%, Fold 2 = 12.63%, Fold 3 = 18.74%.         |
|    - Combined 3-fold MDD (14.89%) masked Fold 3's 18.74% breach via Folds 1 & 2 profit buffer.     |
|    - Classification: VERIFIED_FROM_CODE_AND_ARTIFACTS                                              |
+----------------------------------------------------------------------------------------------------+
```

### 2.2. Reconciliation of Key Benchmark Figures

1. **Why Strategy B reported 14.89% MDD**:
   - In `walk_forward_runner.py`, trades were appended in symbol order (`ADAUSDT` through `XRPUSDT`).
   - In Fold 2, symbol serialization created an artificial drawdown of only **6.01%** because winning trades in one instrument offset losing trades in another after the fact.
   - Compounding this into Fold 3 across all 2,851 trades produced a combined peak-to-trough decline of $(\$12,721.55 - \$10,827.24) / \$12,721.55 = \mathbf{14.8910\%}$.
2. **Why Strategy B chronological MDD is 17.15%**:
   - When trades are merged strictly by calendar exit time (`exit_time_ms`), cross-pair drawdowns coincide simultaneously.
   - Fold 2 drawdown increases from 6.01% to **12.63%**, and Fold 3 drawdown increases from 14.40% to **18.74%**.
   - The combined continuous decline from peak $(\$12,884.54)$ to trough $(\$10,674.34)$ equals $\mathbf{17.1524\%}$, crossing the 15.0% threshold.
3. **Why Fold 3 Mark-to-Market MDD reached 20.72%**:
   - During Fold 3, open positions suffered substantial unrealized intrabar losses before closing or hitting trailing stops.
   - On the normalized $10,000 portfolio base, total mark-to-market equity dropped from its local peak of $\$12,063.10$ to $\$9,563.45$, yielding an MTM peak-to-trough drop of $\mathbf{20.7210\%}$.

---

## 3. The Canonical Portfolio Capital Model

For all future strategy research and Phase 5 ML model benchmarking, the simulation must adhere strictly to the **Single-Pool Shared Capital Model**.

### 3.1. Core Capital & Margin Equations

1. **Initial Portfolio Capital**:
   - $E_0 = \$10,000.00$ cash allocated to a single central portfolio ledger.
   - Independent sub-accounts are prohibited. All pairs share one common collateral pool.
2. **Total Mark-to-Market Portfolio Equity**:
   $$\text{Equity}(t) = \text{Cash}(t) + \sum_{i=1}^{K} \text{UnrealizedPnL}_i(t)$$
   where $K$ is the number of active open positions ($0 \le K \le 10$).
3. **Reserved Margin**:
   - For unleveraged futures simulation ($\text{MaxLeverage} = 1.0\times$):
     $$\text{MarginReserved}(t) = \sum_{i=1}^{K} \text{Notional}_i(t) = \sum_{i=1}^{K} (Q_i \times P_i(t))$$
4. **Free Collateral Available for New Entries**:
   $$\text{FreeCollateral}(t) = \max\left(0.0, \; \text{Equity}(t) - \text{MarginReserved}(t)\right)$$
5. **Cash Ledger Reconciliation**:
   $$\text{Cash}(t) = E_0 + \sum \text{RealizedGrossPnL} - \sum \text{FeesPaid} - \sum \text{SlippagePaid} + \sum \text{FundingCashflow}$$

### 3.2. Capital Allocation & Sizing Policy

- **Target Position Sizing**:
  - Each individual pair position targets a fixed fraction $w$ of current total portfolio equity:
    $$\text{TargetNotional}_i(t) = w \times \text{Equity}(t), \quad w = 10.0\% \; (0.10)$$
- **Capital Rationing & Competition**:
  - When a new signal arrives, allocable notional is constrained by free collateral:
    $$\text{AllocableNotional}_i(t) = \min\left(\text{TargetNotional}_i(t), \; \text{FreeCollateral}(t)\right)$$
  - If $\text{AllocableNotional}_i(t) < \$10.00$ (minimum order threshold), the order is **REJECTED** due to `INSUFFICIENT_COLLATERAL`.
- **Maximum Simultaneous Positions**:
  - Bound by available margin: at $w = 10\%$ and $1.0\times$ max leverage, a maximum of 10 positions can be open concurrently.
  - If 10 positions are open, gross leverage is 100%, free collateral is $\$0.00$, and any subsequent entry signal is rejected until an existing position exits.

---

## 4. Deterministic Event Processing & Execution Timeline

To eliminate all lookahead bias and ensure 100% deterministic reproducibility across multiple pairs, event processing within every discrete candle interval follows a strict 8-step chronological order:

```
Discrete Bar Timeline (t -> t+1)
========================================================================================
[Bar t Closes] -----> [Bar t+1 Opens] ------------------------> [Bar t+1 Closes]
- Strategy generates  Step 1: Mark Open Positions (MTM Open)     Step 6: Mark to Market (MTM Close)
  signals for t+1     Step 2: Execute Market Exits (Free Margin) Step 7: Strategy Signal Generation
                      Step 3: Funding Settlement (00, 08, 16 UTC)Step 8: Fold Boundary Flattening
                      Step 4: Execute Market Entries (Rationing)
                      Step 5: Intrabar Barriers (SL/TP Evaluation)
========================================================================================
```

### 4.1. Detailed Step-by-Step Execution Sequence

1. **Step 1: Mark Open Positions (MTM Open)**:
   - Mark all existing positions to bar $t+1$ `open` price: $P_{\text{open}}$.
2. **Step 2: Execute Market Exits (Signal-based & Expired Orders)**:
   - Exits generated at bar $t$ execute at bar $t+1$ `open` with adverse slippage:
     - Long exit fill: $P_{\text{fill}} = P_{\text{open}} \times (1 - \text{slip})$.
     - Short exit fill: $P_{\text{fill}} = P_{\text{open}} \times (1 + \text{slip})$.
   - Deduct exit fee, calculate realized PnL, update `Cash`, and **immediately release reserved margin into `FreeCollateral`**.
3. **Step 3: Scheduled Funding Settlement**:
   - If timestamp equals 00:00, 08:00, or 16:00 UTC, apply funding payments for open positions directly to `Cash`.
4. **Step 4: Execute Pending Market Entries (Multi-Signal Tie-Breaking)**:
   - Exits in Step 2 freed collateral. Entries now compete for remaining `FreeCollateral`.
   - **Deterministic Tie-Breaking Rule**: When multiple pairs generate entry signals simultaneously:
     1. Highest strategy signal confidence/score (descending).
     2. Highest 24-hour volume / liquidity (descending).
     3. Symbol alphabetical order (`ADAUSDT` before `BTCUSDT`).
   - Sizing: $Q_i = \text{AllocableNotional}_i / P_{\text{fill}}$.
   - Deduct entry taker fee immediately from `Cash`. Reserve margin.
5. **Step 5: Intrabar Barrier Evaluation (SL, TP, Time Expiry)**:
   - Evaluated for all open positions using bar $t+1$ `High` and `Low`.
   - **Conflict Resolution (`CONSERVATIVE_SL_FIRST`)**: If both SL and TP price levels fall within $[\text{Low}, \text{High}]$, Stop-Loss executes first.
   - **Gap-Through-Stop**: If bar opens beyond SL, fill price is bar Open with adverse slippage, absorbing the full gap.
6. **Step 6: Bar-End Mark-to-Market & Equity Point Recording**:
   - Mark remaining positions to bar $t+1$ `close` price: $P_{\text{close}}$.
   - Record canonical portfolio equity point:
     $$\text{EquityPoint}(t) = \left(\text{timestamp\_ms}, \; \text{cash}, \; \text{unrealized\_pnl}, \; \text{equity}, \; \text{drawdown\_pct}, \; \text{free\_collateral}\right)$$
7. **Step 7: Strategy Signal Generation (Zero Lookahead)**:
   - Strategies inspect completed bar $t+1$ features and queue pending orders for execution at bar $t+2$ Open.
8. **Step 8: Fold Boundary Flattening**:
   - On the final bar of an OOS fold, all remaining open positions are force-closed at bar Close price (`BOUNDARY_FLAT`) to deliver a clean cash-only ledger.

---

## 5. Drawdown and Liquidation Semantics

### 5.1. Canonical Maximum Drawdown Formula

The official risk metric for VANTA Terminal qualification gates is **Candle-Level Mark-to-Market Maximum Drawdown**:

1. **High-Water Mark (HWM)**:
   $$\text{HWM}(t) = \max\left(E_0, \; \max_{0 \le s \le t} \text{Equity}(s)\right), \quad \text{HWM}(0) = \$10,000.00$$
2. **Current Drawdown Percentage**:
   $$\text{DD}(t) = \frac{\text{HWM}(t) - \text{Equity}(t)}{\text{HWM}(t)} \times 100\%$$
3. **Fold Maximum Drawdown**:
   $$\text{MDD}_{\text{fold}} = \max_{t \in \text{Fold}} \text{DD}(t)$$

### 5.2. Bankruptcy Floor & Maintenance Margin

1. **Maintenance Margin Requirement (MMR)**:
   - Baseline futures MMR is set to $\text{MMR} = 5.0\%$ of active notional exposure.
2. **Liquidation Threshold**:
   - If $\text{Equity}(t) \le \sum_{i=1}^{K} \text{Notional}_i(t) \times \text{MMR}$:
     - A liquidation event is triggered.
     - All active positions are immediately liquidated at market open/close with taker fee and adverse slippage.
     - Trading is halted permanently for that fold.
3. **Bankruptcy Floor Clamping**:
   - If total equity drops to $\$0.00$ or below, equity is clamped strictly to $\mathbf{\$0.00}$.
   - Drawdown is clamped at exactly $\mathbf{100.0\%}$. Negative equity values (e.g. Strategy A's 272.65%) are classified as **unhedged strategy drag ratios**, not executable drawdown percentages.

### 5.3. Future Qualification Gate Requirements

To replace the heuristic single-stream gate with a robust multi-pair standard in Phase 5:
- **GATE-1 (Multi-Pair Risk Budget)**:
  - Must satisfy $\text{MDD}_{\text{fold}} \le 15.0\%$ in **EVERY individual fold** (Fold 1, Fold 2, and Fold 3).
  - Must satisfy $\text{MDD}_{\text{combined}} \le 15.0\%$ across the entire walk-forward test.
  - Evaluation uses **Candle-Level Mark-to-Market Equity**, including open positions.

---

## 6. Implementation Architecture & Source Code Roadmap

To integrate this specification into VANTA Terminal without touching historical Phase 4B artifacts, the following new components are planned for Phase 5:

1. **`backend/backtest/portfolio_engine.py`**:
   - A multi-pair event-driven engine that consumes simultaneous candle streams from the 10 eligible pairs.
   - Implements the centralized `CanonicalPortfolioManager` validated in `tests/test_portfolio_accounting_spec.py`.
2. **`backend/backtest/event_queue.py`**:
   - Merges bar events across all 10 pairs by timestamp, executing exits, funding, entries, and barrier checks in strict deterministic order.
3. **`backend/strategy/walk_forward_v2.py`**:
   - Walk-forward runner utilizing the shared-margin portfolio engine.
   - Evaluates per-fold MTM MDD alongside combined MTM MDD.

---

## 7. Cryptographic Invariants & Preservation

- All Phase 4B benchmark results (`PHASE_4B_MASTER_SUMMARY.json`), Phase 4B.1 audit manifests (`phase_4b_audit/audit_summary.json`), and Phase 4B.2 risk audit manifests (`phase_4b2_audit/risk_audit_summary.json`) remain strictly untouched and read-only.
- The certified benchmark decision remains unchanged: **`NO_QUALIFIED_STRATEGY`**.
- Strategy B remains the frozen **`UNQUALIFIED_BASELINE`**.
