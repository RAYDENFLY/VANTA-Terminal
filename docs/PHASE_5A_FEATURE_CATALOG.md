# VANTA Terminal — Phase 5A Feature Catalog Specification

**Document ID**: `VANTA-DOCS-5A-FEATURE-CATALOG`  
**Protocol Version**: `1.0.0-FROZEN`  
**Target Timeframe**: 1-Hour (1H) Primary OHLCV  
**Universe**: 10 Eligible Perpetual Pairs (`BTCUSDT` to `LTCUSDT`)  
**Total Pre-Registered Features**: Exactly 21 features across 7 families  
**Leakage-Safe Availability**: Bar close timestamp $t_{\text{close}}$, accessible at $t+1$ bar Open  

---

## 1. Feature Engineering Architectural Principles

To ensure scientific validity, zero lookahead bias, and economic interpretability, all features in this catalog adhere to five non-negotiable principles:

1. **Strict Zero-Lookahead Timing**:
   A feature $X_{i, t}$ computed for symbol $i$ at discrete time index $t$ utilizes only information finalized by bar $t$'s close ($t_{\text{close}} \le t_{\text{decision}}$). It is strictly made available for model prediction and order dispatch at the Open of bar $t+1$.
2. **Point-in-Time Rolling Computation**:
   No full-sample centering, scaling, mean subtraction, or forward interpolation is permitted. All moving averages, standard deviations, and ranges use rolling windows $[t - L + 1, t]$ where $L$ is the lookback period.
3. **In-Sample Fitting Isolation**:
   Any stateful preprocessor (e.g., `RobustScaler`, quantile clipping thresholds) must be fitted strictly on the In-Sample training slice. Applying `.fit()` or `.fit_transform()` on Out-of-Sample evaluation data is an immediate protocol violation.
4. **Deterministic Missing Value Treatment**:
   Incomplete initial bars during the warmup period ($t < L_{\max}$) are marked as `NaN` and dropped from training/prediction matrices. Mid-stream missing bars (if any) are forward-filled from the previous valid close; no backward filling is permitted.
5. **Stationarity & Dimensionless Normalization**:
   Raw asset prices ($P_t$) and nominal volumes ($V_t$) cannot be fed directly into models due to non-stationarity. All features are expressed as dimensionless ratios, percentages, or z-scores normalized by contemporaneous volatility ($\text{ATR}_t$).

---

## 2. Feature Catalog Overview (21 Pre-Registered Features)

```
+--------------------------------------------------------------------------------------------------------+
| PRE-REGISTERED FEATURE FAMILIES                                                                        |
+--------+---------------------------------------+-------+-------------------+---------------------------+
| Family | Description                           | Count | Identifiers       | Primary Economic Rationale|
+--------+---------------------------------------+-------+-------------------+---------------------------+
| FAM-1  | Lagged Returns & Momentum             | 4     | RET_1, RET_4,     | Short/Medium momentum     |
|        |                                       |       | RET_12, RET_24    | and autocorrelation decay |
+--------+---------------------------------------+-------+-------------------+---------------------------+
| FAM-2  | Volatility & True Range               | 3     | NATR_14, VOLAT_24,| Normalized volatility     |
|        |                                       |       | GK_VOL_12         | expansion/compression     |
+--------+---------------------------------------+-------+-------------------+---------------------------+
| FAM-3  | Trend & Moving Average Distance       | 3     | DIST_EMA_20,      | Trend deviation and       |
|        |                                       |       | DIST_EMA_50,      | moving-average dispersion |
|        |                                       |       | SPREAD_EMA_20_50  |                           |
+--------+---------------------------------------+-------+-------------------+---------------------------+
| FAM-4  | Volume Relative to Historical Baseline| 3     | RVOL_12, RVOL_24, | Volume shock and          |
|        |                                       |       | VOL_MOM_4         | institutional commitment  |
+--------+---------------------------------------+-------+-------------------+---------------------------+
| FAM-5  | Candle Body & Wick Microstructure     | 3     | BODY_RATIO,       | Intrabar buying/selling   |
|        |                                       |       | UPPER_SHADOW,     | absorption & exhaustion   |
|        |                                       |       | LOWER_SHADOW      |                           |
+--------+---------------------------------------+-------+-------------------+---------------------------+
| FAM-6  | Rolling Range & Breakout Distance     | 3     | DONCH_POS_24,     | Channel breakout position |
|        |                                       |       | DIST_HIGH_24,     | and range expansion       |
|        |                                       |       | DIST_LOW_24       |                           |
+--------+---------------------------------------+-------+-------------------+---------------------------+
| FAM-7  | Cross-Sectional Relative Strength     | 2     | XS_REL_RET_4,     | Market leader vs laggard  |
|        |                                       |       | XS_BETA_24        | cross-sectional dispersion|
+--------+---------------------------------------+-------+-------------------+---------------------------+
```

---

## 3. Detailed Mathematical Feature Specifications

### Family 1: Lagged Returns & Multi-Horizon Momentum

#### 1. `RET_1` — 1-Hour Log Return
- **Formula**:
  $$\text{RET\_1}_t = \ln\left(\frac{C_t}{C_{t-1}}\right)$$
- **Inputs**: `close`
- **Lookback**: 1 bar (1 hour). Warmup: 2 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: High-frequency momentum / short-term mean-reversion impulse.
- **Leakage Proof**: Uses strictly $C_t$ and $C_{t-1}$. Both are finalized at $t_{\text{close}}$.

#### 2. `RET_4` — 4-Hour Log Return
- **Formula**:
  $$\text{RET\_4}_t = \ln\left(\frac{C_t}{C_{t-4}}\right)$$
- **Inputs**: `close`
- **Lookback**: 4 bars (4 hours). Warmup: 5 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Intraday momentum matching standard 4H session horizons.
- **Leakage Proof**: Uses $C_t$ and $C_{t-4}$; strictly historical.

#### 3. `RET_12` — 12-Hour Cumulative Log Return
- **Formula**:
  $$\text{RET\_12}_t = \ln\left(\frac{C_t}{C_{t-12}}\right)$$
- **Inputs**: `close`
- **Lookback**: 12 bars (12 hours). Warmup: 13 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Half-day momentum capturing funding settlement cycles (8h-12h).
- **Leakage Proof**: Uses $C_t$ and $C_{t-12}$; strictly historical.

#### 4. `RET_24` — 24-Hour (1-Day) Cumulative Log Return
- **Formula**:
  $$\text{RET\_24}_t = \ln\left(\frac{C_t}{C_{t-24}}\right)$$
- **Inputs**: `close`
- **Lookback**: 24 bars (24 hours). Warmup: 25 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Full-day directional momentum.
- **Leakage Proof**: Uses $C_t$ and $C_{t-24}$; strictly historical.

---

### Family 2: Volatility & True Range Measures

#### 5. `NATR_14` — Normalized Average True Range (14-period)
- **Formula**:
  $$\text{TR}_t = \max\left(H_t - L_t, \, |H_t - C_{t-1}|, \, |L_t - C_{t-1}|\right)$$
  $$\text{ATR}_{14, t} = \frac{13 \cdot \text{ATR}_{14, t-1} + \text{TR}_t}{14} \quad (\text{Wilder's Smoothing})$$
  $$\text{NATR\_14}_t = \frac{\text{ATR}_{14, t}}{C_t} \times 100$$
- **Inputs**: `high`, `low`, `close`
- **Lookback**: 14 bars. Warmup: 28 bars (for Wilder exponential decay).
- **Scope**: Per-pair.
- **Economic Rationale**: Dimensionless percentage volatility; critical for adapting to regime shifts.
- **Leakage Proof**: Uses strictly high, low, close up to bar $t$.

#### 6. `VOLAT_24` — Realized Log-Return Volatility (24-period)
- **Formula**:
  $$\text{VOLAT\_24}_t = \sqrt{\frac{1}{23} \sum_{k=0}^{23} \left(\text{RET\_1}_{t-k} - \overline{\text{RET\_1}}_{t}\right)^2}$$
- **Inputs**: `close`
- **Lookback**: 24 bars. Warmup: 25 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Sample standard deviation of 1-hour returns over the past 24 hours.
- **Leakage Proof**: Uses only historical returns over window $[t-23, t]$.

#### 7. `GK_VOL_12` — Garman-Klass Microstructure Volatility (12-period)
- **Formula**:
  $$\text{GK}_t = 0.5 \left(\ln\left(\frac{H_t}{L_t}\right)\right)^2 - (2\ln 2 - 1) \left(\ln\left(\frac{C_t}{O_t}\right)\right)^2$$
  $$\text{GK\_VOL\_12}_t = \sqrt{\frac{1}{12} \sum_{k=0}^{11} \text{GK}_{t-k}}$$
- **Inputs**: `open`, `high`, `low`, `close`
- **Lookback**: 12 bars. Warmup: 13 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Extreme-value volatility estimator; 7x more efficient than close-to-close volatility.
- **Leakage Proof**: Intrabar OHLC values computed within bar $t-k \le t$.

---

### Family 3: Trend & Moving Average Distance

#### 8. `DIST_EMA_20` — Distance to 20-period Exponential Moving Average
- **Formula**:
  $$\text{EMA}_{20, t} = \alpha C_t + (1 - \alpha) \text{EMA}_{20, t-1}, \quad \alpha = \frac{2}{20 + 1}$$
  $$\text{DIST\_EMA\_20}_t = \frac{C_t - \text{EMA}_{20, t}}{\text{ATR}_{14, t}}$$
- **Inputs**: `close`, `ATR_14`
- **Lookback**: 20 bars. Warmup: 50 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Short-term trend deviation normalized by ATR units (z-score equivalent).
- **Leakage Proof**: Standard recursive EMA strictly using prices $\le t$.

#### 9. `DIST_EMA_50` — Distance to 50-period Exponential Moving Average
- **Formula**:
  $$\text{EMA}_{50, t} = \alpha C_t + (1 - \alpha) \text{EMA}_{50, t-1}, \quad \alpha = \frac{2}{50 + 1}$$
  $$\text{DIST\_EMA\_50}_t = \frac{C_t - \text{EMA}_{50, t}}{\text{ATR}_{14, t}}$$
- **Inputs**: `close`, `ATR_14`
- **Lookback**: 50 bars. Warmup: 100 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Medium-term trend deviation in ATR units.
- **Leakage Proof**: Recursive EMA strictly using prices $\le t$.

#### 10. `SPREAD_EMA_20_50` — Moving Average Spread Ratio
- **Formula**:
  $$\text{SPREAD\_EMA\_20\_50}_t = \frac{\text{EMA}_{20, t} - \text{EMA}_{50, t}}{\text{ATR}_{14, t}}$$
- **Inputs**: `close`, `ATR_14`
- **Lookback**: 50 bars. Warmup: 100 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Measures trend alignment and MACD-style momentum slope.
- **Leakage Proof**: Built strictly from past EMAs and ATR.

---

### Family 4: Volume Relative to Historical Baseline

#### 11. `RVOL_12` — Relative Volume (12-period)
- **Formula**:
  $$\text{SMA\_VOL}_{12, t} = \frac{1}{12} \sum_{k=0}^{11} V_{t-k}$$
  $$\text{RVOL\_12}_t = \frac{V_t}{\text{SMA\_VOL}_{12, t} + \epsilon}, \quad \epsilon = 10^{-8}$$
- **Inputs**: `volume`
- **Lookback**: 12 bars. Warmup: 13 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Detects sudden liquidity bursts and volume breakout confirmations.
- **Leakage Proof**: Rolling average over $[t-11, t]$.

#### 12. `RVOL_24` — Relative Volume (24-period)
- **Formula**:
  $$\text{SMA\_VOL}_{24, t} = \frac{1}{24} \sum_{k=0}^{23} V_{t-k}$$
  $$\text{RVOL\_24}_t = \frac{V_t}{\text{SMA\_VOL}_{24, t} + \epsilon}$$
- **Inputs**: `volume`
- **Lookback**: 24 bars. Warmup: 25 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Daily volume comparison baseline.
- **Leakage Proof**: Rolling average over $[t-23, t]$.

#### 13. `VOL_MOM_4` — Volume Momentum
- **Formula**:
  $$\text{VOL\_MOM\_4}_t = \frac{\sum_{k=0}^3 V_{t-k}}{\sum_{k=4}^7 V_{t-k} + \epsilon}$$
- **Inputs**: `volume`
- **Lookback**: 8 bars. Warmup: 9 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Ratio of recent 4-hour volume to prior 4-hour volume.
- **Leakage Proof**: Uses disjoint past slices $[t-3, t]$ and $[t-7, t-4]$.

---

### Family 5: Candle Body & Wick Microstructure

#### 14. `BODY_RATIO` — Candle Body Proportion
- **Formula**:
  $$\text{BODY\_RATIO}_t = \frac{|C_t - O_t|}{H_t - L_t + \epsilon}$$
- **Inputs**: `open`, `high`, `low`, `close`
- **Lookback**: 1 bar. Warmup: 1 bar.
- **Scope**: Per-pair.
- **Economic Rationale**: Values near 1.0 indicate strong directional conviction (Marubozu); values near 0.0 indicate indecision (Doji).
- **Leakage Proof**: Single-candle intrabar calculation at bar $t$.

#### 15. `UPPER_SHADOW` — Upper Wick Proportion
- **Formula**:
  $$\text{UPPER\_SHADOW}_t = \frac{H_t - \max(O_t, C_t)}{H_t - L_t + \epsilon}$$
- **Inputs**: `open`, `high`, `low`, `close`
- **Lookback**: 1 bar. Warmup: 1 bar.
- **Scope**: Per-pair.
- **Economic Rationale**: Measures overhead selling pressure / buyer rejection.
- **Leakage Proof**: Single-candle intrabar calculation at bar $t$.

#### 16. `LOWER_SHADOW` — Lower Wick Proportion
- **Formula**:
  $$\text{LOWER\_SHADOW}_t = \frac{\min(O_t, C_t) - L_t}{H_t - L_t + \epsilon}$$
- **Inputs**: `open`, `high`, `low`, `close`
- **Lookback**: 1 bar. Warmup: 1 bar.
- **Scope**: Per-pair.
- **Economic Rationale**: Measures bottom-fishing buying support / seller rejection.
- **Leakage Proof**: Single-candle intrabar calculation at bar $t$.

---

### Family 6: Rolling Range & Breakout Distance

#### 17. `DONCH_POS_24` — Position within 24-period Donchian Channel
- **Formula**:
  $$\text{HIGH\_24}_t = \max_{k \in [0, 23]} H_{t-k}, \quad \text{LOW\_24}_t = \min_{k \in [0, 23]} L_{t-k}$$
  $$\text{DONCH\_POS\_24}_t = \frac{C_t - \text{LOW\_24}_t}{\text{HIGH\_24}_t - \text{LOW\_24}_t + \epsilon} \in [0.0, 1.0]$$
- **Inputs**: `high`, `low`, `close`
- **Lookback**: 24 bars. Warmup: 25 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Continuous stochastic oscillator over the 24-hour channel.
- **Leakage Proof**: Extremum over $[t-23, t]$.

#### 18. `DIST_HIGH_24` — Normalized Distance to 24-period High
- **Formula**:
  $$\text{DIST\_HIGH\_24}_t = \frac{\text{HIGH\_24}_t - C_t}{\text{ATR}_{14, t}}$$
- **Inputs**: `high`, `close`, `ATR_14`
- **Lookback**: 24 bars. Warmup: 28 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Proximity to upper breakout boundary in ATR units.
- **Leakage Proof**: Strictly historical channel boundary.

#### 19. `DIST_LOW_24` — Normalized Distance to 24-period Low
- **Formula**:
  $$\text{DIST\_LOW\_24}_t = \frac{C_t - \text{LOW\_24}_t}{\text{ATR}_{14, t}}$$
- **Inputs**: `low`, `close`, `ATR_14`
- **Lookback**: 24 bars. Warmup: 28 bars.
- **Scope**: Per-pair.
- **Economic Rationale**: Proximity to lower breakdown boundary in ATR units.
- **Leakage Proof**: Strictly historical channel boundary.

---

### Family 7: Cross-Sectional Relative Strength (10 Eligible Pairs)

#### 20. `XS_REL_RET_4` — Cross-Sectional Relative Return (4-period)
- **Formula**:
  Let $\mathcal{U} = \{1, 2, \dots, 10\}$ be the set of 10 qualified pairs.
  $$\overline{\text{RET\_4}}_{\mathcal{U}, t} = \frac{1}{10} \sum_{j \in \mathcal{U}} \text{RET\_4}_{j, t}$$
  $$\text{XS\_REL\_RET\_4}_{i, t} = \text{RET\_4}_{i, t} - \overline{\text{RET\_4}}_{\mathcal{U}, t}$$
- **Inputs**: `close` across all 10 eligible pairs.
- **Lookback**: 4 bars. Warmup: 5 bars.
- **Scope**: Cross-sectional (universe-wide).
- **Economic Rationale**: Identifies market leaders and laggards relative to broad market beta.
- **Leakage Proof**: Computed contemporaneously at bar close $t$ across all pairs. No future cross-sectional data is accessible.
- **Missing Data Handling**: If pair $j$ has a missing bar at $t$, its previous valid return is held, or the cross-sectional mean is computed over the remaining $N-1$ available pairs.

#### 21. `XS_BETA_24` — Rolling Market Beta (24-period)
- **Formula**:
  Using `BTCUSDT` as the market benchmark $M$:
  $$\text{XS\_BETA\_24}_{i, t} = \frac{\sum_{k=0}^{23} \left(\text{RET\_1}_{i, t-k} - \overline{\text{RET\_1}}_{i, t}\right) \left(\text{RET\_1}_{M, t-k} - \overline{\text{RET\_1}}_{M, t}\right)}{\sum_{k=0}^{23} \left(\text{RET\_1}_{M, t-k} - \overline{\text{RET\_1}}_{M, t}\right)^2 + \epsilon}$$
  (For `BTCUSDT`, $\text{XS\_BETA\_24} \equiv 1.0$).
- **Inputs**: `close` for pair $i$ and `BTCUSDT`.
- **Lookback**: 24 bars. Warmup: 25 bars.
- **Scope**: Cross-sectional pair-to-market.
- **Economic Rationale**: Dynamically estimates asset sensitivity to macro crypto market moves.
- **Leakage Proof**: Uses past 24-hour synchronous return pairs.

---

## 4. Pipeline Standardization & Scaling Protocol

To maintain zero information leakage between In-Sample training and Out-of-Sample evaluation:

1. **Scaler Choice**: `RobustScaler` from `scikit-learn` (subtracts median, divides by interquartile range $[Q_{25}, Q_{75}]$). Robust against crypto outlier spikes.
2. **Fitting Constraint**:
   ```python
   # STRICT PROTOCOL RULE:
   scaler = RobustScaler()
   scaler.fit(X_train)                  # Fitted ONLY on In-Sample slice
   X_train_scaled = scaler.transform(X_train)
   X_oos_scaled = scaler.transform(X_oos)  # Transformed using training statistics
   ```
3. **Quantile Clipping**: After scaling, all continuous features are clipped to $[-5.0, +5.0]$ to prevent numerical instability in gradient boosting or logistic regression solvers.

---

## 5. Verification Matrix & Summary

| # | Feature Name | Lookback | Warmup | Scope | Scaling Method | Lookahead Risk |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `RET_1` | 1 | 2 | Per-Pair | RobustScaler | Zero |
| 2 | `RET_4` | 4 | 5 | Per-Pair | RobustScaler | Zero |
| 3 | `RET_12` | 12 | 13 | Per-Pair | RobustScaler | Zero |
| 4 | `RET_24` | 24 | 25 | Per-Pair | RobustScaler | Zero |
| 5 | `NATR_14` | 14 | 28 | Per-Pair | RobustScaler | Zero |
| 6 | `VOLAT_24` | 24 | 25 | Per-Pair | RobustScaler | Zero |
| 7 | `GK_VOL_12` | 12 | 13 | Per-Pair | RobustScaler | Zero |
| 8 | `DIST_EMA_20` | 20 | 50 | Per-Pair | RobustScaler | Zero |
| 9 | `DIST_EMA_50` | 50 | 100 | Per-Pair | RobustScaler | Zero |
| 10 | `SPREAD_EMA_20_50` | 50 | 100 | Per-Pair | RobustScaler | Zero |
| 11 | `RVOL_12` | 12 | 13 | Per-Pair | RobustScaler | Zero |
| 12 | `RVOL_24` | 24 | 25 | Per-Pair | RobustScaler | Zero |
| 13 | `VOL_MOM_4` | 8 | 9 | Per-Pair | RobustScaler | Zero |
| 14 | `BODY_RATIO` | 1 | 1 | Per-Pair | Bounded $[0, 1]$ | Zero |
| 15 | `UPPER_SHADOW` | 1 | 1 | Per-Pair | Bounded $[0, 1]$ | Zero |
| 16 | `LOWER_SHADOW` | 1 | 1 | Per-Pair | Bounded $[0, 1]$ | Zero |
| 17 | `DONCH_POS_24` | 24 | 25 | Per-Pair | Bounded $[0, 1]$ | Zero |
| 18 | `DIST_HIGH_24` | 24 | 28 | Per-Pair | RobustScaler | Zero |
| 19 | `DIST_LOW_24` | 24 | 28 | Per-Pair | RobustScaler | Zero |
| 20 | `XS_REL_RET_4` | 4 | 5 | Universe | RobustScaler | Zero |
| 21 | `XS_BETA_24` | 24 | 25 | Universe | RobustScaler | Zero |

**Warmup Buffer Specification**: A nominal minimum of **100 bars** achieves 98.18% convergence for the 50-period EMA. To achieve >99.75% exponential decay convergence across all smoothers, the dataset loader will pre-pend a **150-bar warmup buffer** (150 hours $\approx$ 6.25 days) prior to the In-Sample start timestamp. All historical Parquet files contain continuous data to accommodate this buffer without holdout violation. Zero feature rows during the pre-pended buffer are included in training or evaluation matrices.
