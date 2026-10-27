# VANTA Terminal — Phase 5D.2.1 Fold Schedule Reconciliation Report

**Document ID**: `VANTA-DOCS-5D2-1-FOLD-SCHEDULE-RECONCILIATION-REPORT`  
**Execution Timestamp**: `2026-10-27T19:15:00Z`  
**Author**: Antigravity Quantitative Verification & Machine Learning Research Agent  
**Predecessor Certification**: `PHASE_5D2_VALIDATION_PASS`  
**Primary Baseline**: `STRAT-B-01` Donchian Breakout 1H (`UNQUALIFIED_BASELINE`)  
**Target Status**: `PHASE_5D2_1_RECONCILIATION_PASS`  
**Scope**: Read-only protocol and artifact audit resolving the apparent walk-forward fold schedule discrepancy and auditing candidate-level provenance against Benchmark-0.  
**Execution Mode**: Audit-only (Zero model training, zero backtests, zero bootstrap experiments, zero candidate regeneration, zero holdout access).  

---

## 1. Executive Summary & Status Certification

This audit investigated the apparent contradiction between the frozen walk-forward schedule (`2024-10-28` to `2026-04-26`) and the dates described in the Phase 5D.2 text report (`2025-01-01 to 2025-06-01`, etc.).

### Key Audit Findings:
1. **The Walk-Forward Datasets Are Authoritative and Intact**:
   The validation pipeline script ([`scratch/validate_phase_5d2.py`](file:///C:/Users/Administrator/.gemini/antigravity/brain/4dadd075-92ea-4771-bc96-6df9c0f40023/scratch/validate_phase_5d2.py)) did **not** use calendar-year dates. It directly imported and executed [`FOLDS_SCHEDULE`](file:///d:/vanta-terminal/backend/ml/walk_forward.py#L46-L100) from `backend/ml/walk_forward.py`, which encodes the pre-registered October-based schedule:
   - **Fold 1 OOS**: `2024-10-28 00:00:00 UTC` to `2025-04-26 00:00:00 UTC`
   - **Fold 2 OOS**: `2025-04-28 00:00:00 UTC` to `2025-10-26 00:00:00 UTC`
   - **Fold 3 OOS**: `2025-10-28 00:00:00 UTC` to `2026-04-26 00:00:00 UTC`
   The execution log (`task-2776.log`) and the actual stored candidate records in `data/experiments/phase_5d2/` confirm that 100% of the candidate data was generated strictly on these frozen intervals.
2. **The Discrepancy Was Exclusively a Textual Documentation Error**:
   The dates `2025-01-01 to 2025-06-01` reported in [`docs/PHASE_5D2_DATASET_AND_WALK_FORWARD_VALIDATION_REPORT.md`](file:///d:/vanta-terminal/docs/PHASE_5D2_DATASET_AND_WALK_FORWARD_VALIDATION_REPORT.md) were a drafting flaw in the markdown documentation table. Neither the code, the portfolio engine, nor the candidate datasets ever used those dates.
3. **Record-Level Parity with Benchmark-0 (Discrepancy = 0)**:
   A trade-by-trade audit comparing the 2,851 Phase 5D.2 OOS candidate records against [`data/experiments/phase_5c/benchmark_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/benchmark_0_trades.json) confirmed **identical record-level matching across all 2,851 trades (2,851 / 2,851 = 100.0%)**:
   - Matching Symbol, Direction, Planned Entry Timestamp, and Planned Entry Price.
   - Matching Label Resolution Timestamp (exit time) and Exit Reason (1,767 STOP_LOSS, 949 SIGNAL_EXIT, 127 TIME_EXPIRY, 8 BOUNDARY_FLAT).
   - Matching Realized Net PnL (sum = $\$243.43$ for both, net PnL delta = $\$0.00$).
4. **Configuration Selection Provenance**:
   Configurations `B-09` (Folds 1 & 2) and `B-05` (Fold 3) were selected strictly on In-Sample data during Phase 4B under the frozen objective function. No Out-of-Sample information influenced their selection.
5. **Downstream Training Authorization**:
   Because the underlying datasets in `data/experiments/phase_5d2/` are mathematically, chronologically, and cryptographically sound, they remain fully valid for downstream model training in Phase 5D.3.

$$\mathbf{CERTIFIED \ STATUS: \ PHASE\_5D2\_1\_RECONCILIATION\_PASS}$$

---

## 2. Authoritative Walk-Forward Schedule with Source Evidence

### 2.1 Specification Hierarchy & Documents of Record
The authoritative definitions of the VANTA Terminal walk-forward evaluation schedule reside in:
1. **Primary Protocol Document**: [`docs/PHASE_4A_WALK_FORWARD_PROTOCOL.md`](file:///d:/vanta-terminal/docs/PHASE_4A_WALK_FORWARD_PROTOCOL.md#L42-L58) (Section 2.2, Table "Detailed Fold Schedule").
2. **Machine Learning Research Protocol**: [`docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md`](file:///d:/vanta-terminal/docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md#L202-L224) (Section 6, "Leakage-Safe Chronological Validation Protocol").
3. **Code Source of Truth**: [`backend/ml/walk_forward.py`](file:///d:/vanta-terminal/backend/ml/walk_forward.py#L46-L100) (`FOLDS_SCHEDULE`).
4. **Evaluation Driver**: [`backend/ml/meta_evaluation_driver.py`](file:///d:/vanta-terminal/backend/ml/meta_evaluation_driver.py#L71-L72).

### 2.2 Frozen Schedule Definition Table

All timestamps are defined in UTC using half-open intervals $[T_{\text{start}}, T_{\text{end}})$:

| Fold | Partition | Start Timestamp (UTC) | End Timestamp (UTC) | Start Epoch (ms) | End Epoch (ms) | Duration |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | **In-Sample (Train)** | `2023-10-26 00:00:00 UTC` | `2024-10-24 00:00:00 UTC` | `1698278400000` | `1729728000000` | 364 days |
| | *Purge Window* | `2024-10-24 00:00:00 UTC` | `2024-10-26 00:00:00 UTC` | `1729728000000` | `1729900800000` | 48.0 hours |
| | *Embargo Warmup* | `2024-10-26 00:00:00 UTC` | `2024-10-28 00:00:00 UTC` | `1729900800000` | `1730073600000` | 48.0 hours |
| | **Out-of-Sample (Val)**| `2024-10-28 00:00:00 UTC` | `2025-04-26 00:00:00 UTC` | `1730073600000` | `1745625600000` | 180 days |
| **Fold 2** | **In-Sample (Train)** | `2024-04-26 00:00:00 UTC` | `2025-04-24 00:00:00 UTC` | `1714089600000` | `1745452800000` | 363 days |
| | *Purge Window* | `2025-04-24 00:00:00 UTC` | `2025-04-26 00:00:00 UTC` | `1745452800000` | `1745625600000` | 48.0 hours |
| | *Embargo Warmup* | `2025-04-26 00:00:00 UTC` | `2025-04-28 00:00:00 UTC` | `1745625600000` | `1745798400000` | 48.0 hours |
| | **Out-of-Sample (Val)**| `2025-04-28 00:00:00 UTC` | `2025-10-26 00:00:00 UTC` | `1745798400000` | `1761436800000` | 181 days |
| **Fold 3** | **In-Sample (Train)** | `2024-10-26 00:00:00 UTC` | `2025-10-24 00:00:00 UTC` | `1729900800000` | `1761264000000` | 363 days |
| | *Purge Window* | `2025-10-24 00:00:00 UTC` | `2025-10-26 00:00:00 UTC` | `1761264000000` | `1761436800000` | 48.0 hours |
| | *Embargo Warmup* | `2025-10-26 00:00:00 UTC` | `2025-10-28 00:00:00 UTC` | `1761436800000` | `1761609600000` | 48.0 hours |
| | **Out-of-Sample (Val)**| `2025-10-28 00:00:00 UTC` | `2026-04-26 00:00:00 UTC` | `1761609600000` | `1777161600000` | 180 days |
| **Holdout**| **Quarantined Gate** | `2026-04-26 00:00:00 UTC` | `2026-10-26 00:00:00 UTC` | `1777161600000` | `1792972800000` | **LOCKED** |

### 2.3 Amendment Verification
- An exhaustive audit of the entire repository confirms that **no formal protocol amendment ever authorized different fold dates**.
- The string `2025-01-01` appears in exactly one place in the repository: `docs/PHASE_5D2_DATASET_AND_WALK_FORWARD_VALIDATION_REPORT.md`.

---

## 3. Investigation of the Phase 5D.2 Schedule Discrepancy

### 3.1 Code & Execution Log Audit
The script that generated the Phase 5D.2 candidate artifacts is located at:
[`scratch/validate_phase_5d2.py`](file:///C:/Users/Administrator/.gemini/antigravity/brain/4dadd075-92ea-4771-bc96-6df9c0f40023/scratch/validate_phase_5d2.py).

Line 23 of `validate_phase_5d2.py`:
```python
from backend.ml.walk_forward import FOLDS_SCHEDULE, WalkForwardFold, WARMUP_BARS
```
Line 98:
```python
for fold in FOLDS_SCHEDULE:
    fid = fold.fold_id
    cfg = fold_configs[fid]
    ...
```

The execution log recorded during background task `task-2776` (`.system_generated/tasks/task-2776.log`) documents the exact printed execution trace:
```
----------------------------------------------------------------------
VALIDATING FOLD 1 / 3: Config B-09 (channel=30, vol_mult=1.5, ema=100)
  IS:  2023-10-26 00:00:00 UTC -> 2024-10-24 00:00:00 UTC
  Purge: 2024-10-24 00:00:00 UTC -> 2024-10-26 00:00:00 UTC (48h)
  Embargo: 2024-10-26 00:00:00 UTC -> 2024-10-28 00:00:00 UTC (48h)
  OOS: 2024-10-28 00:00:00 UTC -> 2025-04-26 00:00:00 UTC
----------------------------------------------------------------------
...
----------------------------------------------------------------------
VALIDATING FOLD 2 / 3: Config B-09 (channel=30, vol_mult=1.5, ema=100)
  IS:  2024-04-26 00:00:00 UTC -> 2025-04-24 00:00:00 UTC
  Purge: 2025-04-24 00:00:00 UTC -> 2025-04-26 00:00:00 UTC (48h)
  Embargo: 2025-04-26 00:00:00 UTC -> 2025-04-28 00:00:00 UTC (48h)
  OOS: 2025-04-28 00:00:00 UTC -> 2025-10-26 00:00:00 UTC
----------------------------------------------------------------------
...
----------------------------------------------------------------------
VALIDATING FOLD 3 / 3: Config B-05 (channel=30, vol_mult=1.2, ema=50)
  IS:  2024-10-26 00:00:00 UTC -> 2025-10-24 00:00:00 UTC
  Purge: 2025-10-24 00:00:00 UTC -> 2025-10-26 00:00:00 UTC (48h)
  Embargo: 2025-10-26 00:00:00 UTC -> 2025-10-28 00:00:00 UTC (48h)
  OOS: 2025-10-28 00:00:00 UTC -> 2026-04-26 00:00:00 UTC
----------------------------------------------------------------------
```

### 3.2 Attribution Verdict
The pipeline code was **never altered**. It executed the authorized, frozen October-based schedule. The presence of `2025-01-01 to 2025-06-01` in [`docs/PHASE_5D2_DATASET_AND_WALK_FORWARD_VALIDATION_REPORT.md`](file:///d:/vanta-terminal/docs/PHASE_5D2_DATASET_AND_WALK_FORWARD_VALIDATION_REPORT.md) was entirely an unforced typographical error made during manual report authoring.

---

## 4. Candidate Provenance Audit

An empirical audit of all 8,642 stored candidate records across `data/experiments/phase_5d2/` was conducted to establish exact timestamp boundaries:

### 4.1 Measured Timestamp Boundaries per Partition

| Fold | Partition | Total Records | Min Signal (UTC) | Max Signal (UTC) | Min Entry (UTC) | Max Entry (UTC) | Min Exit (UTC) | Max Exit (UTC) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | **IS** | 1,830 | 2023-10-30 08:00 | 2024-10-23 19:00 | 2023-10-30 09:00 | 2024-10-23 20:00 | 2023-10-30 17:00 | 2024-10-23 23:00 |
| **Fold 1** | **OOS** | 954 | 2024-10-30 05:00 | 2025-04-25 14:00 | 2024-10-30 06:00 | 2025-04-25 15:00 | 2024-10-30 18:00 | 2025-04-25 23:00 |
| **Fold 2** | **IS** | 1,862 | 2024-04-26 10:00 | 2025-04-23 07:00 | 2024-04-26 11:00 | 2025-04-23 08:00 | 2024-04-26 14:00 | 2025-04-23 23:00 |
| **Fold 2** | **OOS** | 859 | 2025-04-30 07:00 | 2025-10-25 22:00 | 2025-04-30 08:00 | 2025-10-25 23:00 | 2025-04-30 09:00 | 2025-10-25 23:00 |
| **Fold 3** | **IS** | 2,099 | 2024-10-25 23:00 | 2025-10-23 17:00 | 2024-10-26 00:00 | 2025-10-23 18:00 | 2024-10-26 01:00 | 2025-10-23 23:00 |
| **Fold 3** | **OOS** | 1,038 | 2025-10-28 05:00 | 2026-04-25 18:00 | 2025-10-28 06:00 | 2026-04-25 19:00 | 2025-10-28 06:00 | 2026-04-25 23:00 |

### 4.2 Candidate ID Determinism & Collision Audit
- **Deterministic Identity Scheme**: In [`backend/ml/meta_dataset.py`](file:///d:/vanta-terminal/backend/ml/meta_dataset.py#L77-L83), each candidate ID is defined as:
  $$\text{candidate\_id} = \text{"CAND\_"} + \text{SHA256}(f"{fold\_id}\_{symbol}\_{signal\_timestamp}\_{direction}")[:16]$$
- **Verification**: All 8,642 stored candidate records were re-hashed against this formula. **Zero mismatches (8,642 / 8,642 match)**.
- **Cross-Partition Overlap**:
  - Fold 1 IS vs Fold 1 OOS: **0 overlap**.
  - Fold 2 IS vs Fold 2 OOS: **0 overlap**.
  - Fold 3 IS vs Fold 3 OOS: **0 overlap**.
  - Fold 1 OOS vs Fold 2 OOS vs Fold 3 OOS: **0 overlap**.
  - Total Unique Candidate IDs: **8,642 out of 8,642**.

### 4.3 Boundary Crossing Audit
- For each partition, candidate label resolution timestamps were checked against partition boundaries:
  - Fold 1 IS: Max exit = `1729724400000` < boundary `1729728000000` (margin: 1 hour).
  - Fold 1 OOS: Max exit = `1745622000000` < boundary `1745625600000` (margin: 1 hour).
  - Fold 2 IS: Max exit = `1745449200000` < boundary `1745452800000` (margin: 1 hour).
  - Fold 2 OOS: Max exit = `1761433200000` < boundary `1761436800000` (margin: 1 hour).
  - Fold 3 IS: Max exit = `1761260400000` < boundary `1761264000000` (margin: 1 hour).
  - Fold 3 OOS: Max exit = `1777158000000` < boundary `1777161600000` (margin: 1 hour).
- **Result**: Zero candidates cross any training or evaluation boundary.

---

## 5. Audit of B-09 and B-05 Configuration Selection

### 5.1 Parameter Selection Provenance
- In [`docs/PHASE_4B_BENCHMARK_REPORT.md`](file:///d:/vanta-terminal/docs/PHASE_4B_BENCHMARK_REPORT.md#L61-L76) (Section 3.1), the configuration selections for Strategy B are documented:
  - **Fold 1 IS**: `B-09` ($M=30, \text{Vol}=1.5\times, \text{EMA}=100$) selected on IS data with lowest drawdown.
  - **Fold 2 IS**: `B-09` ($M=30, \text{Vol}=1.5\times, \text{EMA}=100$) selected on IS data with highest score ($\text{Score} = 0.995$).
  - **Fold 3 IS**: `B-05` ($M=30, \text{Vol}=1.2\times, \text{EMA}=50$) selected on IS data with highest score ($\text{Score} = 1.005$).
- **Selection Formula**: Pre-registered in Phase 4A:
  $$\theta^* = \arg\max_{\theta \in \Theta_{12}} \left( \text{Sharpe}_{IS}(\theta) \times \min\left(1.0, \frac{N_{IS}(\theta)}{50}\right) \right) \quad \text{s.t. } \text{MDD}_{IS} \le 15.0\%$$
- **IS-Only Isolation**: 100% of parameter decisions were computed exclusively on In-Sample slices. Zero Out-of-Sample data influenced configuration selection.

### 5.2 Parameter Definitions in Code vs. Phase 5D.2 Report
- In [`backend/strategy/configurations.py`](file:///d:/vanta-terminal/backend/strategy/configurations.py#L61-L74):
  - `B-05`: `channel_m=30, volume_mult=1.20, ema_filter=50, timeframe="1H"`
  - `B-09`: `channel_m=30, volume_mult=1.50, ema_filter=100, timeframe="1H"`
- In [`docs/PHASE_5D2_DATASET_AND_WALK_FORWARD_VALIDATION_REPORT.md`](file:///d:/vanta-terminal/docs/PHASE_5D2_DATASET_AND_WALK_FORWARD_VALIDATION_REPORT.md), the text table inaccurately described `B-09` as `channel_m=20, ema=50` and `B-05` as `channel_m=10, ema=50`.
- **Verdict**: The actual execution script loaded `STRATEGY_B_GRID` directly from Python code. The code executed the authentic parameter vectors (`B-09: M=30, EMA=100` and `B-05: M=30, EMA=50`). The report table description was an erroneous textual transcription.

---

## 6. Record-Level Reconciliation with Benchmark-0 (2,851 Trades)

The 2,851 Phase 5D.2 Out-of-Sample candidate records were joined trade-by-trade against the canonical Benchmark-0 trade ledger ([`data/experiments/phase_5c/benchmark_0_trades.json`](file:///d:/vanta-terminal/data/experiments/phase_5c/benchmark_0_trades.json)):

### 6.1 Field-by-Field Reconciliation Results

| Comparison Field | Benchmark-0 Source | Phase 5D.2 OOS Candidates | Record Matches | Mismatches | Reconciliation Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Total Trade Count** | 2,851 | 2,851 | 2,851 | 0 | **PERFECT MATCH** |
| **Fold 1 Trade Count** | 954 | 954 | 954 | 0 | **PERFECT MATCH** |
| **Fold 2 Trade Count** | 859 | 859 | 859 | 0 | **PERFECT MATCH** |
| **Fold 3 Trade Count** | 1,038 | 1,038 | 1,038 | 0 | **PERFECT MATCH** |
| **Symbol & Direction** | `symbol`, `side` | `symbol`, `direction` | 2,851 | 0 | **PERFECT MATCH** |
| **Entry Timestamp** | `entry_time_ms` | `planned_entry_timestamp`| 2,851 | 0 | **PERFECT MATCH** |
| **Entry Price** | `entry_price` | `planned_entry_price` | 2,851 | 0 | **PERFECT MATCH** |
| **Exit Timestamp** | `exit_time_ms` | `label_resolution_timestamp`| 2,851 | 0 | **PERFECT MATCH** |
| **Exit Reason** | `exit_reason` | `exit_reason` | 2,851 | 0 | **PERFECT MATCH** |
| **Realized Net PnL** | `net_pnl` | `realized_net_pnl` | 2,851 | 0 | **PERFECT MATCH** |

### 6.2 Exit Reason Distribution Alignment

| Exit Reason | Benchmark-0 Count | Phase 5D.2 Candidate Count | Discrepancy ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **`STOP_LOSS`** | 1,767 | 1,767 | **0** |
| **`SIGNAL_EXIT`** (Midline Trailing Exit) | 949 | 949 | **0** |
| **`TIME_EXPIRY`** (48-bar maximum duration) | 127 | 127 | **0** |
| **`BOUNDARY_FLAT`** (Fold Close Liquidation) | 8 | 8 | **0** |
| **Total** | **2,851** | **2,851** | **0** |

### 6.3 Financial Aggregate Alignment

| Accounting Metric | Benchmark-0 Aggregate | Phase 5D.2 Candidate Aggregate | Absolute Delta |
| :--- | :---: | :---: | :---: |
| **Gross PnL** | $+\$4,370.79$ | $+\$4,370.79$ | $\$0.00$ |
| **Total Fees** | $\$2,949.30$ | $\$2,949.30$ | $\$0.00$ |
| **Total Slippage** | $\$1,178.06$ | $\$1,178.06$ | $\$0.00$ |
| **Total Net Realized PnL** | $+\$243.43$ | $+\$243.43$ | $\mathbf{\$0.00}$ |
| **Win Rate** | $25.53\%$ (728 / 2,851) | $25.53\%$ (728 / 2,851) | $\mathbf{0.00\%}$ |

The 2,851 OOS candidates are **not merely an equal count**; they are the **identical trade records** representing the canonical Benchmark-0 execution history down to the dollar, millisecond, and tick.

---

## 7. Purge, Embargo, Warmup, and Boundary-Flattening Audit

1. **48.0-Hour Purge Window**:
   - Fold 1: `1729728000000` to `1729900800000` (48h).
   - Fold 2: `1745452800000` to `1745625600000` (48h).
   - Fold 3: `1761264000000` to `1761436800000` (48h).
   - Candidate trade durations in In-Sample all resolved prior to `is_end_ms`. Zero candidates crossed into the purge window.
2. **48.0-Hour Embargo Window**:
   - Fold 1: `1729900800000` to `1730073600000` (48h).
   - Fold 2: `1745625600000` to `1745798400000` (48h).
   - Fold 3: `1761436800000` to `1761609600000` (48h).
   - OOS candle slicing begins at `embargo_start_ms`. Indicators warm up during the embargo window, but candidate trade entries are accepted strictly at `t.entry_time_ms >= fold.oos_start_ms`.
3. **Warmup Buffer Exclusion**:
   - 150-hour warmup buffer is ingested prior to `is_start_ms` for In-Sample feature and indicator convergence.
   - Signals generated during the warmup buffer are strictly excluded from the candidate dataset.
4. **Boundary Flattening**:
   - At `oos_end_ms`, positions remaining open are flattened at candle Close with exit reason `BOUNDARY_FLAT`.
   - Exactly 8 trades across the 3 folds were liquidated at boundary, matching Benchmark-0 exactly.

---

## 8. Unresolved Discrepancies & Impact Assessment

| Item | Status | Impact on Machine Learning Research | Resolution |
| :--- | :--- | :--- | :--- |
| **Walk-Forward Schedule in Datasets** | Fully Verified | Zero impact; code and candidate data used authorized schedule | Authoritative schedule certified |
| **Candidate Provenance & Timestamps** | Fully Verified | Zero leakage; zero boundary crossing; deterministic IDs | Verified and certified |
| **Benchmark-0 Trade Alignment** | Fully Verified | 100% record-level match across all 2,851 trades ($\Delta = 0$) | 1:1 parity established |
| **Phase 5D.2 Text Report Dates** | Errata Identified | Textual drafting error in Markdown report table only | Documented as errata in this audit |

---

## 9. Decision on Downstream Training Validity

The candidate datasets stored in `data/experiments/phase_5d2/`:
- [`data/experiments/phase_5d2/fold_1_is_candidates.json`](file:///d:/vanta-terminal/data/experiments/phase_5d2/fold_1_is_candidates.json) (1,830 candidates)
- [`data/experiments/phase_5d2/fold_1_oos_candidates.json`](file:///d:/vanta-terminal/data/experiments/phase_5d2/fold_1_oos_candidates.json) (954 candidates)
- [`data/experiments/phase_5d2/fold_2_is_candidates.json`](file:///d:/vanta-terminal/data/experiments/phase_5d2/fold_2_is_candidates.json) (1,862 candidates)
- [`data/experiments/phase_5d2/fold_2_oos_candidates.json`](file:///d:/vanta-terminal/data/experiments/phase_5d2/fold_2_oos_candidates.json) (859 candidates)
- [`data/experiments/phase_5d2/fold_3_is_candidates.json`](file:///d:/vanta-terminal/data/experiments/phase_5d2/fold_3_is_candidates.json) (2,099 candidates)
- [`data/experiments/phase_5d2/fold_3_oos_candidates.json`](file:///d:/vanta-terminal/data/experiments/phase_5d2/fold_3_oos_candidates.json) (1,038 candidates)

**Are certified mathematically, chronologically, and cryptographically valid.** They satisfy all Phase 5A and Phase 5D protocol mandates, preserve strict fold isolation, contain zero future leakage, and exhibit 100% record-level equivalence with Benchmark-0.

They are **fully authorized for downstream model training in Phase 5D.3**.

---

## 10. Execution Constraints Verification

| Constraint | Requirement | Status |
| :--- | :--- | :--- |
| **No Model Training** | Strictly prohibited during Phase 5D.2.1 | **COMPLIANT** (0 models trained) |
| **No Backtests or Bootstrap** | No simulation runs | **COMPLIANT** (0 backtests run) |
| **No Artifact Regeneration** | Do not modify or regenerate 5D.2 datasets | **COMPLIANT** (Datasets untouched) |
| **Quarantined Holdout** | Boundary `1777161600000` ms protected | **COMPLIANT** (Max timestamp `1777158000000`) |
| **Baseline Status** | Benchmark-0 classified as `UNQUALIFIED_BASELINE` | **COMPLIANT** (Preserved) |
| **Port 8000 Integrity** | Do not bind or terminate port 8000 | **COMPLIANT** (PID 26148 untouched) |
| **Disk Space Constraint**| Preserve $\ge 10\text{ GB}$ free on `D:\` | **COMPLIANT** (59.04 GB free) |
