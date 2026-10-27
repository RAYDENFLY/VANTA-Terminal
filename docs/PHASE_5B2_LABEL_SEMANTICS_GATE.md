# VANTA Terminal — Phase 5B.2 Final Label Semantics Gate

**Document Identifier**: `docs/PHASE_5B2_LABEL_SEMANTICS_GATE.md`  
**Execution Timestamp**: `2026-10-27T15:40:00+07:00`  
**Auditor**: Antigravity Quantitative Verification & Conformance Agent  
**Reference Deliverables**:
- [`docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md`](file:///d:/VANTA%20Terminal/docs/PHASE_5A_ML_RESEARCH_PROTOCOL.md)
- [`docs/PHASE_5A2_FINAL_PROTOCOL_INTEGRITY_CHECK.md`](file:///d:/VANTA%20Terminal/docs/PHASE_5A2_FINAL_PROTOCOL_INTEGRITY_CHECK.md)
- [`docs/PHASE_5B_FEATURE_PIPELINE_REPORT.md`](file:///d:/VANTA%20Terminal/docs/PHASE_5B_FEATURE_PIPELINE_REPORT.md)
- [`docs/PHASE_5B1_PROTOCOL_CONFORMANCE_AUDIT.md`](file:///d:/VANTA%20Terminal/docs/PHASE_5B1_PROTOCOL_CONFORMANCE_AUDIT.md)
- [`backend/ml/labels.py`](file:///d:/VANTA%20Terminal/backend/ml/labels.py)
- [`tests/test_triple_barrier_labels.py`](file:///d:/VANTA%20Terminal/tests/test_triple_barrier_labels.py)

**Gate Status**: `LABEL_SEMANTICS_PASS`

---

## 1. Executive Summary

Phase 5B.2 executes the final, critical audit and gate verification of the Triple-Barrier target labeling engine (`backend/ml/labels.py`). The investigation focused specifically on resolving the semantic conflict identified in Phase 5B.1 regarding same-candle collisions under `CONSERVATIVE_SL_FIRST` and verifying complete fidelity to the frozen protocol mapping:
- **Long TP first**: `+1`
- **Long SL first**: `-1`
- **Short TP first**: `-1`
- **Short SL first**: `+1`
- **Neither barrier touched by the 12-bar expiry**: `0`

### Defect Diagnosis
The audit determined that the previous assignment of Class `0` to same-candle collisions was **both a code defect and a test defect**:
1. In `backend/ml/labels.py`, the resolution logic checked whether either side was a "TP winner" (`long_outcome == "TP"` or `short_outcome == "TP"`). When an intra-candle collision occurred, both sides hit Stop Loss under `CONSERVATIVE_SL_FIRST`, which fell through to `else: assigned_label = TargetLabel.NEUTRAL_EXPIRY (0)`.
2. This conflated violent high-volatility stopouts with quiet, range-bound 12-bar expiries, directly violating the invariant that **Class `0` is strictly and exclusively reserved for time expiry where neither barrier is touched**.
3. Under the frozen protocol, a Long stopout is `-1` (downward loss), and a Short stopout is `+1` (upward loss). Neither collision outcome can ever be `0`.

The code and tests have been corrected to strictly follow the frozen mapping for both LONG and SHORT perspectives.

---

## 2. Analysis of Label Convention: Outcome Direction vs Trade Action

### 2.1 The Two Perspectives
A key source of ambiguity in machine learning trade targets is whether the integer label represents **Outcome Direction** (the physical price direction of the first barrier touch) or **Trade Action** (an action directive for a long-only model):

| Event | Market Movement | Long Trade Perspective | Short Trade Perspective | Unified Directional Class |
| :--- | :---: | :---: | :---: | :---: |
| **Upper Barrier Reached First** | Upside / Bullish | Take Profit (Win) $\implies \mathbf{+1}$ | Stop Loss (Loss) $\implies \mathbf{+1}$ | $\mathbf{+1}$ (`BULLISH_UP`) |
| **Lower Barrier Reached First** | Downside / Bearish | Stop Loss (Loss) $\implies \mathbf{-1}$ | Take Profit (Win) $\implies \mathbf{-1}$ | $\mathbf{-1}$ (`BEARISH_DOWN`) |
| **Neither Barrier Reached by Bar 12** | Range-Bound | Time Expiry $\implies \mathbf{0}$ | Time Expiry $\implies \mathbf{0}$ | $\mathbf{0}$ (`NEUTRAL_EXPIRY`) |

### 2.2 Reconciled Convention
1. In standard trend-following and momentum regimes, **Outcome Direction** and **Trade Action** are harmoniously aligned:
   - When price breaks out to the upside, Long wins (`+1`) and Short loses (`+1`). Both agree on label `+1`.
   - When price breaks out to the downside, Long loses (`-1`) and Short wins (`-1`). Both agree on label `-1`.
   - When price stays within the band for all 12 bars, both expire neutral (`0`).
2. **The Same-Candle Collision Divergence**:
   When a single bar expands violently across both Upper and Lower barriers:
   - For a **LONG** trade: The risk is to the downside (Long SL is the lower barrier). Under `CONSERVATIVE_SL_FIRST`, the stop loss triggers first $\implies$ **Label is `-1`** (`BEARISH_DOWN` / Long Stopout).
   - For a **SHORT** trade: The risk is to the upside (Short SL is the upper barrier). Under `CONSERVATIVE_SL_FIRST`, the stop loss triggers first $\implies$ **Label is `+1`** (`BULLISH_UP` / Short Stopout).
   - In neither case can the label ever be `0`. Class `0` remains strictly preserved for time expiry with neither barrier touched.

---

## 3. Fee, Slippage & Hurdle Mathematics Audit

### 3.1 Frozen Barrier Definitions
As audited in Phase 5A.2:
- Reference Long Entry: $P_{\text{entry, Long}} = O_{t+1} \times (1 + 0.0002)$
- Reference Short Entry: $P_{\text{entry, Short}} = O_{t+1} \times (1 - 0.0002)$
- Normalized Volatility: $\delta_{\text{ATR}, t} = \frac{\text{ATR}_{14, t}}{C_t}$
- Long TP Barrier: $P_{\text{TP, Long}} = P_{\text{entry, Long}} \times (1 + 1.5 \cdot \delta_{\text{ATR}, t} + 0.0014)$
- Long SL Barrier: $P_{\text{SL, Long}} = P_{\text{entry, Long}} \times (1 - 1.0 \cdot \delta_{\text{ATR}, t})$
- Short TP Barrier: $P_{\text{TP, Short}} = P_{\text{entry, Short}} \times (1 - 1.5 \cdot \delta_{\text{ATR}, t} - 0.0014)$
- Short SL Barrier: $P_{\text{SL, Short}} = P_{\text{entry, Short}} \times (1 + 1.0 \cdot \delta_{\text{ATR}, t})$

### 3.2 Rigorous Economic Assessment of Hurdle Buffer
Earlier reports claimed that deducting $0.0014$ in the TP barrier produces an **exact zero-difference net return**:
$$R_{\text{gross}} - \text{Friction} = (1.5 \cdot \delta_{\text{ATR}} + 0.0014) - 0.0014 = 1.5 \cdot \delta_{\text{ATR}}$$

A rigorous derivation against [`backend/backtest/portfolio_engine.py`](file:///d:/VANTA%20Terminal/backend/backtest/portfolio_engine.py) reveals why this is a **conservative heuristic buffer** rather than an exact mathematical equality:
1. **Exit Notional Scaling**: Exchange fees are calculated on traded notional ($P \times Q$). The exit fee is paid on exit notional $P_{\text{TP}} \times Q$, whereas entry fee is paid on $P_{\text{entry}} \times Q$. Because $P_{\text{TP}} > P_{\text{entry}}$, the actual exit fee rate relative to entry capital is $f_{\text{exit}} \times \frac{P_{\text{TP}}}{P_{\text{entry}}} = f_{\text{exit}} \cdot (1 + 1.5 \cdot \delta_{\text{ATR}} + 0.0014) > f_{\text{exit}}$.
2. **Maker vs Taker Asymmetry**: In `CanonicalPortfolioEngine`, TP exits are limit orders filled at $P_{\text{TP}}$ as **maker orders**, which pay `maker_fee_bps = 2.0 bps` ($0.0002$) with **zero slippage**, whereas the 14.0 bps hurdle conservatively assumes full round-trip **taker friction** ($2 \times (5.0\text{ fee} + 2.0\text{ slippage}) = 14.0\text{ bps}$).
3. **Conclusion**: The 14 bps hurdle is a conservative, risk-averse gross profit requirement that guarantees any breakout reaching Take Profit yields a solid positive realized edge ($> 1.5 \cdot \delta_{\text{ATR}}$) under actual exchange fee structures.

---

## 4. Code & Test Implementation Details

### 4.1 Implementation in `backend/ml/labels.py`
[`backend/ml/labels.py`](file:///d:/VANTA%20Terminal/backend/ml/labels.py) was updated with:
```python
class TargetLabel(IntEnum):
    BEARISH_DOWN = -1
    NEUTRAL_EXPIRY = 0
    BULLISH_UP = 1

    # Directional aliases matching frozen protocol
    SHORT_BREAKOUT = -1
    LONG_BREAKOUT = 1
```

The method [`compute_labels(df_ohlcv, side="LONG")`](file:///d:/VANTA%20Terminal/backend/ml/labels.py#L83-L188) evaluates the forward path deterministically:
- When `side="LONG"`:
  - If Long SL hit first (or collision under `CONSERVATIVE_SL_FIRST`): `assigned_label = TargetLabel.BEARISH_DOWN` (`-1`).
  - If Long TP hit first: `assigned_label = TargetLabel.BULLISH_UP` (`+1`).
  - If neither hit within 12 bars: `assigned_label = TargetLabel.NEUTRAL_EXPIRY` (`0`).
- When `side="SHORT"`:
  - If Short SL hit first (or collision under `CONSERVATIVE_SL_FIRST`): `assigned_label = TargetLabel.BULLISH_UP` (`+1`).
  - If Short TP hit first: `assigned_label = TargetLabel.BEARISH_DOWN` (`-1`).
  - If neither hit within 12 bars: `assigned_label = TargetLabel.NEUTRAL_EXPIRY` (`0`).

Dedicated helpers [`compute_long_labels(df)`](file:///d:/VANTA%20Terminal/backend/ml/labels.py#L190-L193) and [`compute_short_labels(df)`](file:///d:/VANTA%20Terminal/backend/ml/labels.py#L194-L197) are exported for downstream pipelines.

### 4.2 Test Updates in `tests/test_triple_barrier_labels.py`
Replaced the flawed test with two distinct, deterministic unit tests:
1. `test_triple_barrier_long_same_candle_collision_conservative_sl_first`:
   - Simulates a bar with High 110.0 and Low 90.0 spanning both Long TP (103.16) and Long SL (98.02).
   - Under `CONSERVATIVE_SL_FIRST`, Long SL triggers first $\implies$ asserts `TargetLabel.BEARISH_DOWN` (`-1`).
2. `test_triple_barrier_short_same_candle_collision_conservative_sl_first`:
   - Simulates the same volatile bar.
   - Under `CONSERVATIVE_SL_FIRST`, Short SL triggers first $\implies$ asserts `TargetLabel.BULLISH_UP` (`+1`).
3. `test_triple_barrier_time_expiry_neither_barrier_touched`:
   - Price remains in tight band $\implies$ asserts `TargetLabel.NEUTRAL_EXPIRY` (`0`).

---

## 5. Verification Test Suite Matrix

All 10 tests in [`tests/test_triple_barrier_labels.py`](file:///d:/VANTA%20Terminal/tests/test_triple_barrier_labels.py) passed in 1.27s:

| Test Identifier | Perspective | Verification Target | Status |
| :--- | :--- | :--- | :---: |
| `test_exact_barrier_formulas_and_slippage` | Math | Exact frozen barrier formulas down to $10^{-12}$ | **PASS** |
| `test_triple_barrier_tp_first` | Long | Long TP reached first $\implies \mathbf{+1}$ | **PASS** |
| `test_triple_barrier_sl_first` | Long / Short | Downside movement reaches SL/TP $\implies \mathbf{-1}$ | **PASS** |
| `test_triple_barrier_long_same_candle_collision_conservative_sl_first` | Long | Long collision under `CONSERVATIVE_SL_FIRST` $\implies \mathbf{-1}$ | **PASS** |
| `test_triple_barrier_short_same_candle_collision_conservative_sl_first` | Short | Short collision under `CONSERVATIVE_SL_FIRST` $\implies \mathbf{+1}$ | **PASS** |
| `test_triple_barrier_time_expiry_neither_barrier_touched` | Expiry | Neither barrier touched $\implies \mathbf{0}$ | **PASS** |
| `test_price_movement_at_expiry_exceeding_14bps_without_barrier_touch` | Expiry | +50 bps drift without barrier touch $\implies \mathbf{0}$ | **PASS** |
| `test_triple_barrier_directional_symmetry` | Symmetry | Symmetric Long (+1) and Short (-1) mirror paths | **PASS** |
| `test_triple_barrier_gap_through_stop` | Execution | Gap-through stop fills at gap Open price | **PASS** |
| `test_triple_barrier_partition_boundary_isolation` | Quarantine | Last 12 bars of partition are strictly NaN | **PASS** |

### Complete Regression Suite
- **ML Component Test Suite**: 26 of 26 tests passed in 3.26s.
- **Portfolio Engine Test Suite**: 12 of 12 tests passed in 0.50s (`test_portfolio_engine_v2.py`).
- **Total Combined Tests**: 38 of 38 tests passed.

---

## 6. Cryptographic Signatures (SHA-256)

```
8142e44e0d276ab04ab1e05027396f3db34fad1ed69d80d6511fb174cc02d372  backend/ml/chained_equity.py
c17dc3e941f020a4bb719f00fcef90f4f04175a04c0b02bbc5cf7894bdf2254b  backend/ml/features.py
e94d42438c3079d859d70e3a1a89b79b1e4b37c69a2da0c4fe7ce4d3691522b8  backend/ml/labels.py
88075851d281fe3d0a094954b637756e65a7d4281f64a8cc45d4006ce73ec3d5  backend/ml/scaling.py
de4f2f2d874fe2784137d24d18adeda7b74da7ab58db2df80c4aad485f88d18c  backend/ml/__init__.py
baebb03ef39c1d00faf428d2ebae9afc686c3b894a44eed94d2d34037355b988  tests/test_triple_barrier_labels.py
```

---

## 7. Exit Certification

The Triple-Barrier target labeling engine has been verified and aligned with the frozen Phase 5A / 5A.1 / 5A.2 specifications. All label semantics are closed-form, deterministic, and free of contradictions.

**Phase 5B.2 Final Label Semantics Gate Status**:
```
LABEL_SEMANTICS_PASS
```
