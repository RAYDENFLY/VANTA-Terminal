# VANTA Terminal — Phase 4B.3 Validation Report

**Document ID**: `VANTA-PHASE4B3-VALIDATION-REPORT-20261027`  
**Execution Phase**: Phase 4B.3 Portfolio Accounting Specification & Validation  
**Date**: October 27, 2026  
**Auditor**: Quantitative Systems Architecture & Verification  
**Quarantine Integrity**: Zero candles loaded at or after `2026-04-26T00:00:00Z` (`open_time < 1777161600000`)  
**Overall Exit Status**: **`SPEC_AND_VALIDATION_PASS`**  
**Certified Outcome**: **`NO_QUALIFIED_STRATEGY`** (Unchanged; Strategy B remains `UNQUALIFIED_BASELINE`)  

---

## 1. Executive Summary

Phase 4B.3 has successfully resolved all portfolio-accounting discrepancies documented in Phase 4B.1 and Phase 4B.2. A rigorous, mathematically sound specification for multi-pair shared capital, deterministic event ordering, candle-level mark-to-market drawdown, and bankruptcy clamping has been established in [`docs/PHASE_4B3_PORTFOLIO_ACCOUNTING_SPEC.md`](file:///d:/vanta-terminal/docs/PHASE_4B3_PORTFOLIO_ACCOUNTING_SPEC.md).

All 12 canonical portfolio-accounting invariants were verified via an independent unit-test suite (`tests/test_portfolio_accounting_spec.py`), achieving a **100% pass rate (12 passed of 12 items)** with deterministic reproducibility.

---

## 2. Current vs. Proposed Portfolio Accounting Semantics

The table below contrasts the legacy Phase 4B benchmark accounting assumptions with the canonical Phase 4B.3 specification:

| Accounting Dimension | Legacy Benchmark Runner (Phase 4B) | Canonical Specification (Phase 4B.3) | Technical Rationale & Resolution |
| :--- | :--- | :--- | :--- |
| **Capital Architecture** | 10 independent single-pair sub-accounts ($10k each = $100k deployed), normalized to synthetic $10k base. | Single centralized shared capital pool ($10,000 total initial equity). | Eliminates virtual capital inflation; enforces true margin competition across pairs (`DISC-4B2-02`). |
| **Trade Event Ordering** | Trades serialized pair-by-pair within each fold (`Fold 1: ADA...XRP`). | Trades merged strictly chronologically by timestamp (`open_time_ms` / `exit_time_ms`). | Eliminates artificial cross-pair smoothing; reflects real-time calendar drawdown (`DISC-4B2-01`). |
| **Equity Evaluation** | Discrete trade-close cashflows only: `cum_equity += t.net_pnl`. | Candle-level Mark-to-Market: `Equity(t) = Cash(t) + sum(Unrealized PnL)`. | Accurately captures adverse intrabar excursions during open position holding periods. |
| **Capital Rationing** | None; all signals executed up to local sub-account leverage. | Strict free-collateral check; orders exceeding margin or 1.0x gross leverage are rejected. | Prevents over-leverage and respects portfolio margin limits. |
| **Bankruptcy & Zero Floor** | Un-clamped negative cashflow accumulation (Strategy A dropped to -$17,265; 272.65% MDD). | Physical bankruptcy floor clamped at $0.00 cash; drawdown capped at 100.0%. | Aligns with executable exchange account realities while retaining unhedged strategy drag as a metric (`DISC-4B2-03`). |
| **Fold Boundary & Reset** | Cash reset to $10k per fold, but combined MDD compounded across folds continuously. | Dual evaluation: Mandated fold-specific MTM MDD ($\le 15.0\%$) and combined MTM MDD ($\le 15.0\%$). | Prevents prior fold profit buffer from masking subsequent fold collapse (`DISC-4B2-04`). |
| **SL / TP Ambiguity** | `CONSERVATIVE_SL_FIRST` (Phase 3B.2). | `CONSERVATIVE_SL_FIRST` (Preserved). | Retains conservative execution bias when both barriers fall within candle range. |
| **Gap-Through-Stop** | Fills at candle Open with slippage, not pegged to SL. | Fills at candle Open with adverse slippage (Preserved). | Eliminates idealized barrier fills on market gap openings. |

---

## 3. Reconciliation of Maximum Drawdown Metrics

The table below reconciles the five distinct MDD figures across Strategy A, Strategy B, and Strategy C:

| Strategy | Pair-Concatenated Trade-Close MDD (Phase 4B) | Chronological Exit-Time MDD | Candle-Level MTM MDD (Fold 3, $10k Base) | Clamped Bankruptcy MDD | Fold 3 Stand-Alone Chronological MDD |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Strategy B (Donchian Breakout, 1H)** | **14.8910%** *(Reported 14.89%)* | **17.1524%** *(Breaches Gate 1)* | **20.7210%** | **14.8910%** / **17.1524%** | **18.7420%** *(Fold 3 Stand-Alone)* |
| **Strategy A (Sweep-Reclaim, 15m)** | **272.6491%** *(Reported 272.65%)* | **272.7848%** | **100.1633%** | **100.0000%** *(Bankrupt Fold 2)* | **98.3481%** *(Fold 3 Stand-Alone)* |
| **Strategy C (Mean Reversion, 15m)** | **69.5451%** *(Reported 69.55%)* | **69.7444%** | **14.1167%** | **69.5451%** / **69.7444%** | **13.9838%** *(Fold 3 Stand-Alone)* |

### Key Observations
1. **Strategy B 14.89% vs 17.15%**:
   - The reported 14.89% was an artifact of symbol-by-symbol serialization. When evaluated in true calendar time, Strategy B suffered a continuous cashflow drawdown of **17.15%**, and a candle-level MTM drawdown of **20.72%** in Fold 3.
   - This proves that Strategy B was correctly classified as an `UNQUALIFIED_BASELINE`.
2. **Strategy A 272.65% vs 100.0%**:
   - The reported 272.65% measures total cumulative unhedged loss ($2.72\times$ starting capital).
   - In a physically executable isolated margin account, bankruptcy occurs during Fold 2, clamping maximum drawdown to **100.0%**.

---

## 4. Test Suite Execution & Reproducibility Evidence

The canonical accounting specification was validated by executing `tests/test_portfolio_accounting_spec.py` via `pytest`:

```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-8.4.2
rootdir: D:\VANTA Terminal
collected 12 items

tests/test_portfolio_accounting_spec.py::test_1_shared_capital_across_multiple_pairs PASSED [  8%]
tests/test_portfolio_accounting_spec.py::test_2_two_or_more_simultaneous_open_positions PASSED [ 16%]
tests/test_portfolio_accounting_spec.py::test_3_insufficient_free_collateral_allocation_and_rejection PASSED [ 25%]
tests/test_portfolio_accounting_spec.py::test_4_open_position_unrealized_losses_mtm_drawdown PASSED [ 33%]
tests/test_portfolio_accounting_spec.py::test_5_simultaneous_exits_free_collateral_for_entries PASSED [ 41%]
tests/test_portfolio_accounting_spec.py::test_6_gap_through_stop_loss_fill_and_slippage PASSED [ 50%]
tests/test_portfolio_accounting_spec.py::test_7_same_candle_sl_tp_ambiguity_conservative_sl_first PASSED [ 58%]
tests/test_portfolio_accounting_spec.py::test_8_fee_slippage_and_cash_reconciliation PASSED [ 66%]
tests/test_portfolio_accounting_spec.py::test_9_bankruptcy_floor_clamping_at_zero PASSED [ 75%]
tests/test_portfolio_accounting_spec.py::test_10_deterministic_replay_and_identical_equity_checksum PASSED [ 83%]
tests/test_portfolio_accounting_spec.py::test_11_fold_reset_isolation_and_boundary_flattening PASSED [ 91%]
tests/test_portfolio_accounting_spec.py::test_12_funding_data_missing_exception_guard PASSED [100%]

============================= 12 passed in 0.20s ==============================
```

### Deterministic Replay Integrity (TEST-10)
Running the exact same event series produces bit-for-bit identical portfolio history and identical SHA-256 hash across repeated runs:
`hash1 == hash2` (Verified).

---

## 5. Required Source-Code Changes for Phase 5 (Roadmap)

In accordance with the instruction not to automatically rewrite the historical backtest engine, the planned codebase additions for Phase 5 are documented below:

1. **`backend/backtest/portfolio_engine.py`**:
   - New event-driven engine implementing the centralized shared-margin model (`CanonicalPortfolioManager`).
   - Manages global cash, reserved margin, free collateral, and simultaneous open positions.
2. **`backend/backtest/event_queue.py`**:
   - Chronological multi-stream dispatcher that synchronizes candle arrivals across all 10 pairs.
   - Executes exits, funding settlements, entry rationing, and barrier evaluations in deterministic order.
3. **`backend/strategy/walk_forward_v2.py`**:
   - Next-generation walk-forward runner that records candle-level MTM equity points and evaluates per-fold and combined MTM MDD against the 15.0% hurdle.

---

## 6. Discrepancy Register & Resolution Status

| Discrepancy ID | Summary | Status in Phase 4B.3 | Resolution Summary |
| :--- | :--- | :---: | :--- |
| **`DISC-4B2-01`** | Multi-Pair Cashflow Serialization | **RESOLVED** | Specified chronological event queue merging trade fills by `exit_time_ms`. Verified in `TEST-05` and `TEST-10`. |
| **`DISC-4B2-02`** | Independent Sub-Accounts vs Shared Margin | **RESOLVED** | Formulated Single-Pool Shared Capital Model ($10,000 central equity). Verified in `TEST-01`, `TEST-02`, and `TEST-03`. |
| **`DISC-4B2-03`** | Un-Clamped Equity Accumulation | **RESOLVED** | Defined dual reporting: un-clamped strategy drag (272.65%) and clamped bankruptcy floor (100.0% max). Verified in `TEST-09`. |
| **`DISC-4B2-04`** | Fold Cash Reset Inconsistency | **RESOLVED** | Mandated per-fold MTM risk budgets ($\le 15.0\%$ in every fold) alongside combined MTM MDD. Verified in `TEST-11`. |

---

## 7. Artifact Integrity & System Invariants

### 7.1. SHA-256 Cryptographic Register

| Artifact / File Path | Description | SHA-256 Checksum |
| :--- | :--- | :--- |
| `docs/PHASE_4B3_PORTFOLIO_ACCOUNTING_SPEC.md` | Canonical Portfolio Accounting Specification | `ec5d7e74c9d9165af1ec5e5ae117f77a87ea96a6058097e3a9dc63102434f092` |
| `tests/test_portfolio_accounting_spec.py` | 12-Item Validation Test Suite | `ba82bc73ba94b5379b30c1e8471c990263309a785750868f7d983c267b2d56a7` |
| `backend/strategy/validate_phase_4b3.py` | Validation Runner & Manifest Generator | `fd097d74866b0a9aa83e60dd667f3399066914588df8e59265f2ea7008cfbb5a` |
| `data/benchmarks/phase_4b3_audit/validation_summary.json` | Audit Output Manifest | `fd2b430f73ded61e68eaf176832ef8d5cf3d8feb34c359644b4ebbaef1afa618` |
| `docs/PHASE_4B3_VALIDATION_REPORT.md` | Phase 4B.3 Validation Report | *(Self-Documenting)* |

### 7.2. Physical Environment Invariants
- **Disk Free Space (HDD D:)**: **51.13 GB free** (preserves mandatory $\ge 10.0\text{ GB}$ reserve).
- **Execution Runtime**: 1.141 seconds total validation runtime.
- **Port 8000**: Untouched and unprobed.
- **Holdout Quarantine**: Zero candles $\ge 1777161600000$ loaded.

---

## 8. Final Exit Status

```
================================================================================
FINAL VALIDATION VERDICT: SPEC_AND_VALIDATION_PASS
================================================================================
1. All 12 canonical portfolio-accounting validation tests PASSED (100%).
2. Discrepancies DISC-4B2-01 through DISC-4B2-04 fully resolved in frozen specification.
3. Single-pool shared capital model ($10k central equity) formalized with capital rationing.
4. Candle-level mark-to-market MDD and bankruptcy clamping established as canonical risk metrics.
5. Historical benchmark outcome NO_QUALIFIED_STRATEGY remains 100% valid and preserved.
6. Codebase modification roadmap prepared for Phase 5 machine-learning engine.
================================================================================
```
