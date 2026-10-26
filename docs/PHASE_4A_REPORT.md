# VANTA Terminal — Phase 4A Delivery Report
## Strategy Research Protocol, Funding Data Readiness & Walk-Forward Design

**Document ID:** REP-P4A-001  
**Phase:** 4A (Pre-Strategy Research Protocol)  
**Execution Date:** 2026-10-27  
**Status:** COMPLETE · READY FOR PHASE 4B AUTHORIZATION  

---

## 1. Executive Summary

Phase 4A establishes the complete scientific, statistical, and operational protocol for candidate strategy benchmarking in VANTA Terminal. 

In strict adherence to instructions:
- **No ML model training** or unsupervised feature engineering was conducted.
- **No strategy parameter optimization or bulk benchmarking** was performed.
- **Zero Live Trading**: Order placement capabilities remain completely non-existent and physically unmapped.
- **Project Isolation**: External Port 8000 (PID 24852) remains completely unmolested and untouched.
- **Storage Policy**: All datasets and documentation live strictly on HDD `D:\` ($64.37\text{ GB}$ free, maintaining the $>10.0\text{ GB}$ reserve). SSD `C:\` usage remains strictly $0.0\text{ MB}$.

---

## 2. Pre-Strategy Engine Accounting Audit Results

Before pre-registering strategy rules, the event-driven backtesting engine implemented in Phase 3B.2 was subjected to a rigorous mathematical accounting audit.

Four hand-calculated test cases were executed and verified in [`tests/test_engine_accounting_audit.py`](file:///d:/vanta-terminal/tests/test_engine_accounting_audit.py):
1. **Long Winning Trade ($1.0\text{ unit}$, $\$100 \to \$110$)**:
   - Gross PnL: $\$9.9580$
   - Taker Fee ($5\text{ bps}$): $\$0.1050$
   - Slippage ($2\text{ bps}$): $\$0.0420$
   - Net Realized PnL: $\$9.8110$ (Engine match: 100.0000%)
2. **Short Winning Trade ($1.0\text{ unit}$, $\$100 \to \$90$)**:
   - Gross PnL: $\$9.9620$
   - Taker Fee ($5\text{ bps}$): $\$0.0950$
   - Slippage ($2\text{ bps}$): $\$0.0380$
   - Net Realized PnL: $\$9.8290$ (Engine match: 100.0000%)
3. **Gap-Through-Stop Execution**:
   - Long entered at $\$100.0200$, SL set at $\$95.0000$. Next candle opened at $\$90.0000$.
   - The engine correctly refused to fill at the unattainable $\$95.0000$ price and filled at candle Open ($Open \times (1 - \text{Slippage}) = \$89.9820$), realizing a loss of $-\$10.0380$.
4. **Intrabar Same-Candle Barrier Ambiguity**:
   - Candle spanned both $\text{Low} \le \text{SL}$ and $\text{High} \ge \text{TP}$.
   - Under `ExecutionPolicy.CONSERVATIVE_SL_FIRST`, the engine prioritized the adverse Stop Loss, logging `is_ambiguous = True`.

**Core Engine Invariants Verified**:
- Zero lookahead bias (Signal at bar $t$ close $\to$ Fill at bar $t+1$ Open).
- Invariant to future price mutation.
- Bit-for-bit deterministic reproducibility across repeated runs.
- SHA-256 Parquet dataset tamper protection.
- Guarded by `BLOCKED_MISSING_FUNDING_DATA` when funding data is absent.

*Complete audit proof available in [`docs/PHASE_4A_ENGINE_AUDIT.md`](file:///d:/vanta-terminal/docs/PHASE_4A_ENGINE_AUDIT.md).*

---

## 3. Historical Funding Data Readiness Assessment

An air-gapped audit of the official AsterDEX Futures V3 Pro API was conducted to assess historical funding rate depth and schema:

1. **Exchange Endpoint Capabilities**:
   - Endpoint: `GET /fapi/v1/fundingRate` on `https://fapi.asterdex.com`.
   - Frequency: Every $8.0\text{ hours}$ ($00:00$, $08:00$, $16:00\text{ UTC}$).
   - Limit: Up to $1,000\text{ records}$ per call.
2. **Coverage Depth Across Universe**:
   - **10 Qualified Pairs**: Continuously available back to `2023-10-26 00:00:00 UTC` ($\ge 3\text{ years}$ depth).
   - **`XMRUSDT`**: Available from listing at `2026-01-13 17:00:00 UTC` ($286\text{ days}$).
3. **Storage State & Pre-Registration Decision**:
   - In Phase 3B.1, only OHLCV bars were authorized and saved to disk. Historical funding rates have **not yet been serialized into local Parquet on disk**.
   - Per Phase 4A rules, no bulk downloads were initiated.
   - All strategy comparison benchmarks in Phase 4B will be evaluated on a **funding-neutral baseline** (`use_funding = False`), accounting rigorously for Taker Fee ($5\text{ bps}$) and Slippage ($2\text{ bps}$).
   - If funding ingestion is approved in a future phase, the full 3-year universe requires only **44 HTTP calls**, yielding $33,738\text{ rows}$ and consuming $< 250\text{ KB}$ of Parquet storage on HDD `D:\`.

*Complete assessment available in [`docs/PHASE_4A_FUNDING_READINESS.md`](file:///d:/vanta-terminal/docs/PHASE_4A_FUNDING_READINESS.md).*

---

## 4. Pre-Registered Strategy Candidate Specifications

Three distinct, causal, non-curve-fitted heuristic strategy candidates have been pre-registered:

1. **Strategy Candidate A: Sweep-Reclaim (Liquidity Sweep & False Breakout)**:
   - Primary Timeframe: `15m`
   - Entry: Wick sweeps $20$-bar Low/High by $\ge 0.10\times\text{ATR}_{14}$ followed by a bar Close back inside the range. Entry at next bar Open.
   - Stop Loss: Sweep extreme $\pm 0.10\times\text{ATR}_{14}$.
   - Take Profit: Fixed $2.0\times$ Risk-to-Reward ratio.
   - Max Holding Time: $24\text{ bars}$ ($6.0\text{ hours}$).
2. **Strategy Candidate B: Breakout / Trend-Following (Donchian + Volume + EMA Filter)**:
   - Primary Timeframe: `1H` (Secondary: `15m`)
   - Entry: Close breaks $20$-bar Donchian channel with volume $\ge 1.20\times\text{SMA}_{20}(V)$ aligned with $50\text{ EMA}$ slope. Entry at next bar Open.
   - Stop Loss: Donchian Midline or $1.50\times\text{ATR}_{14}$.
   - Take Profit: Dynamic trailing exit on Donchian Midline cross.
   - Max Holding Time: $48\text{ bars}$ ($48\text{ hours}$ on 1H).
3. **Strategy Candidate C: Mean Reversion (Bollinger Bands + RSI Hook)**:
   - Primary Timeframe: `15m`
   - Entry: Candle $t-1$ pierces $2.0\text{ SD}$ Bollinger Band with $\text{RSI}_{14} < 30 / > 70$, followed by candle $t$ closing back inside the band with an RSI reversal hook.
   - Stop Loss: $1.50\times\text{ATR}_{14}$ from entry.
   - Take Profit: Return to Bollinger centerline $\mu$.
   - Max Holding Time: $16\text{ bars}$ ($4.0\text{ hours}$).

*Complete mathematical formulations available in [`docs/PHASE_4A_STRATEGY_SPECIFICATIONS.md`](file:///d:/vanta-terminal/docs/PHASE_4A_STRATEGY_SPECIFICATIONS.md).*

---

## 5. Walk-Forward Benchmark Protocol & Holdout Quarantine

To prevent selection bias and lookahead leakage, the following validation framework is frozen:

1. **Quarantined Test Set (Holdout)**:
   - Range: `2026-04-26 00:00:00 UTC` to `2026-10-26 00:00:00 UTC` ($183\text{ days}$).
   - **Status**: Strictly locked. Zero evaluation, zero tuning, and zero inspection permitted until the Phase 6 Final Audit.
2. **3-Fold Walk-Forward Schedule (10 Qualified Pairs)**:
   - **Fold 1**: IS: `2023-10-26` to `2024-10-26` ($12\text{m}$) $\to$ Purge ($24\text{ bars}$) $\to$ OOS Val: `2024-10-26` to `2025-04-26` ($6\text{m}$).
   - **Fold 2**: IS: `2024-04-26` to `2025-04-26` ($12\text{m}$) $\to$ Purge ($24\text{ bars}$) $\to$ OOS Val: `2025-04-26` to `2025-10-26` ($6\text{m}$).
   - **Fold 3**: IS: `2024-10-26` to `2025-10-26` ($12\text{m}$) $\to$ Purge ($24\text{ bars}$) $\to$ OOS Val: `2025-10-26` to `2026-04-26` ($6\text{m}$).
3. **`XMRUSDT` Asymmetric Handling**:
   - Excluded from Fold 1 and Fold 2.
   - Enters Fold 3 on `2026-01-13 17:00:00 UTC` ($103\text{ days}$ IS).
   - Evaluated fully in the Quarantined Holdout.
   - Absolutely zero synthetic back-padding or data fabrication.
4. **Tuning Budget Limit**:
   - Maximum of $12\text{ parameter configurations}$ per candidate evaluated strictly on In-Sample data.
   - Single-pass evaluation on OOS validation. Zero iterative re-tuning.

*Complete protocol available in [`docs/PHASE_4A_WALK_FORWARD_PROTOCOL.md`](file:///d:/vanta-terminal/docs/PHASE_4A_WALK_FORWARD_PROTOCOL.md).*

---

## 6. Frozen Strategy Qualification Gates & Fallback Protocol

A candidate strategy must satisfy all 8 qualification gates over out-of-sample validation to become the certified baseline for ML comparison:

| Gate | Criterion | Minimum Hurdle |
| :--- | :--- | :--- |
| **GATE-1** | Maximum Drawdown (MDD) | $\le 15.0\%$ |
| **GATE-2** | Net Expectancy per Trade | $\ge +0.08\%$ ($+8.0\text{ bps}$) after $14\text{ bps}$ friction |
| **GATE-3** | Profit Factor (PF) | $\ge 1.25$ |
| **GATE-4** | Universe Trade Count | $\ge 150\text{ trades}$ |
| **GATE-5** | Per-Pair Trade Count | $\ge 20\text{ trades}$ per qualified pair |
| **GATE-6** | Walk-Forward Consistency | $\ge 2\text{ of } 3\text{ Folds}$ net profitable |
| **GATE-7** | Cross-Pair Robustness | $\ge 7\text{ of } 11\text{ Pairs}$ net profitable under same $\theta^*$ |
| **GATE-8** | Friction Stress Tolerance | Net positive PnL at $7.5\text{ bps}$ fee $+ 3.0\text{ bps}$ slip |

### Mandatory Fallback: `NO QUALIFIED STRATEGY` Clause
If no candidate meets all gates, the system will **NOT** lower thresholds. Instead:
1. Formally record a `NO_QUALIFIED_STRATEGY` status in the benchmark registry.
2. Label the top-performing candidate strictly as an `UNQUALIFIED_BASELINE`.
3. Proceed directly to Phase 5 ML feature research to determine if non-linear models can achieve alpha where fixed heuristics fail.

*Complete qualification criteria available in [`docs/PHASE_4A_QUALIFICATION_GATES.md`](file:///d:/vanta-terminal/docs/PHASE_4A_QUALIFICATION_GATES.md).*

---

## 7. Safety, Resource, and Test Verification Matrix

| Verification Dimension | Mandatory Specification | Verified Observed Status | Audit Result |
| :--- | :--- | :--- | :--- |
| **Forbidden Port 8000** | Must never be probed, bound, or killed | PID 24852 listening untouched | **PASS** |
| **Local App Binding** | Loopback only (`127.0.0.1`) | Backend 8101, Frontend 3000 | **PASS** |
| **Live Order Execution** | Permanently disabled | Zero keys, zero order signing | **PASS** |
| **Storage Reserve (HDD D:)** | Minimum $\ge 10.0\text{ GB}$ reserve | $64.37\text{ GB}$ free ($>6.4\times$ reserve) | **PASS** |
| **SSD C: Footprint** | Must remain $0.0\text{ MB}$ | $0.0\text{ MB}$ written to C: | **PASS** |
| **Pytest Test Suite** | 100% pass across all modules | 43 of 43 passed (100%) | **PASS** |
| **Next.js Production Build** | Zero compile errors across routes | 11 of 11 static routes compiled | **PASS** |
