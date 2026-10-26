# VANTA Terminal — Strategy Candidate Specifications
**Document ID:** DOC-STRAT-P4A-001  
**Phase:** 4A / 4A.1 (Reconciled & Frozen Specifications)  
**Verification Date:** 2026-10-27  
**Status:** RECONCILED & FROZEN FOR BENCHMARKING  

---

## 1. Overview & Objective

This document pre-registers the exact, causal, mathematically formalized candidate strategies to be benchmarked in Phase 4B.

To maintain strict scientific integrity, **no discretionary post-hoc parameter adjustments** are permitted during or after benchmark evaluation. All mathematical rules, indicator formulas, entry/exit logic, execution mechanics, friction assumptions, and parameter grids are frozen herein.

### Guiding Principles:
1. **Zero Lookahead Bias**: Every indicator and decision at candle $t$ uses information strictly available at or prior to the close of candle $t$. Orders execute at the Open of candle $t+1$ with adverse slippage.
2. **Realistic Friction Accounting**: All market orders incur a $5.0\text{ bps}$ ($0.05\%$) taker fee and $2.0\text{ bps}$ ($0.02\%$) adverse slippage on entry and exit ($14.0\text{ bps}$ round-trip total).
3. **Conservative Barrier Evaluation**: Same-candle TP/SL touches default to `CONSERVATIVE_SL_FIRST` with ambiguity logging. Gap-through stops fill at candle Open.
4. **Single-Position Discipline**: Position stacking and pyramiding are strictly disabled across all candidates ($N_{pos} \le 1$ per instrument).

---

## 2. Strategy Candidate A: Sweep-Reclaim (Liquidity Sweep & False Breakout)

### 2.1 Concept & Economic Rationale
Crypto-futures order books frequently exhibit clustered stop-loss orders beyond prominent local swing extremes. Institutional participants often drive price into these liquidity pools to fill large orders, leading to swift mean-reverting reclaims of the prior range. 

Strategy A formalizes this phenomenon by detecting when a wick breaks a multi-candle extreme by a minimum volatility-normalized threshold, but the bar closes back inside the range, indicating aggressive absorption.

### 2.2 Mathematical Formalization

#### Causal Indicators
All indicators evaluated at candle $t$ use only past completed bars ($i \in \{t-N, \dots, t-1\}$ for reference levels):
- **Rolling Reference Range ($N = 20$ bars)**:
  $$L_{ref}(t) = \min_{1 \le k \le N} Low_{t-k}, \quad H_{ref}(t) = \max_{1 \le k \le N} High_{t-k}$$
  *(Bar $t$ is strictly excluded from the reference calculation to prevent lookahead).*
- **Average True Range ($\text{ATR}_{14}$)**:
  $$\text{TR}_i = \max\left(High_i - Low_i, |High_i - Close_{i-1}|, |Low_i - Close_{i-1}|\right)$$
  $$\text{ATR}_{14}(t) = \frac{1}{14}\sum_{k=0}^{13} \text{TR}_{t-k}$$
- **Initialization & Burn-In**: Requires $N + 14 = 34\text{ bars}$. Bar index $< 34$ cannot emit signals.

#### Long Entry Conditions (Bullish Sweep & Reclaim)
At candle $t$ Close, a Long signal is triggered if all criteria hold:
1. **Liquidity Sweep**:
   $$Low_t < L_{ref}(t) \quad \text{and} \quad (L_{ref}(t) - Low_t) \ge \delta_{sweep} \times \text{ATR}_{14}(t), \quad \delta_{sweep} = 0.10$$
2. **Range Reclaim**:
   $$Close_t > L_{ref}(t)$$
3. **Simultaneous Outside-Bar Tie-Breaking**: Candle $t$ must NOT simultaneously sweep the high:
   $$High_t \le H_{ref}(t) + \delta_{sweep} \times \text{ATR}_{14}(t)$$
   *(If both high and low are swept, the signal is discarded as `SIGNAL_REJECTED_OUTSIDE_BAR_CONFLICT`).*
4. **Position State**: Current position for instrument is `FLAT`.

#### Short Entry Conditions (Bearish Sweep & Reclaim)
At candle $t$ Close, a Short signal is triggered if all criteria hold:
1. **Liquidity Sweep**:
   $$High_t > H_{ref}(t) \quad \text{and} \quad (High_t - H_{ref}(t)) \ge \delta_{sweep} \times \text{ATR}_{14}(t)$$
2. **Range Reclaim**:
   $$Close_t < H_{ref}(t)$$
3. **Simultaneous Outside-Bar Tie-Breaking**: Candle $t$ must NOT simultaneously sweep the low:
   $$Low_t \ge L_{ref}(t) - \delta_{sweep} \times \text{ATR}_{14}(t)$$
4. **Position State**: Current position for instrument is `FLAT`.

#### Execution & Exit Logic
- **Entry Execution**: Market order submitted at Close of bar $t$, executed at $Open_{t+1}$ with adverse slippage:
  $$\text{Fill Price}_{long} = Open_{t+1} \times (1 + \text{Slippage}), \quad \text{Fill Price}_{short} = Open_{t+1} \times (1 - \text{Slippage})$$
- **Stop Loss (SL)**: Fixed structural barrier:
  $$\text{SL}_{long} = Low_t - \delta_{buf} \times \text{ATR}_{14}(t), \quad \delta_{buf} = 0.10$$
  $$\text{SL}_{short} = High_t + \delta_{buf} \times \text{ATR}_{14}(t), \quad \delta_{buf} = 0.10$$
- **Take Profit (TP)**: Fixed $2.0\times$ Risk-to-Reward ratio:
  $$\text{TP}_{long} = \text{Fill Price}_{long} + 2.0 \times \left(\text{Fill Price}_{long} - \text{SL}_{long}\right)$$
  $$\text{TP}_{short} = \text{Fill Price}_{short} - 2.0 \times \left(\text{SL}_{short} - \text{Fill Price}_{short}\right)$$
- **Barrier Conflict Precedence**: Intrabar barrier conflict policy is frozen to `CONSERVATIVE_SL_FIRST`. If both SL and TP price levels are breached within the same candle, the Stop Loss is filled.
- **Time-Expiry Exit**: Maximum holding duration $T_{max} = 24\text{ bars}$ ($6.0\text{ hours}$ on 15m timeframe). If neither TP nor SL is triggered by candle $t+24$, an exit order is queued for $Open_{t+25}$.

### 2.3 Pre-Registered 12-Configuration Grid (Strategy A)
| Config ID | Lookback $N$ | Sweep $\delta_{sweep}$ | $R:R$ Target | Timeframe | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A-01** | 20 | 0.10 | 2.0 | 15m | **Default Baseline** |
| **A-02** | 20 | 0.05 | 2.0 | 15m | Shallow sweep |
| **A-03** | 20 | 0.15 | 2.0 | 15m | Deep sweep |
| **A-04** | 15 | 0.10 | 2.0 | 15m | Responsive lookback |
| **A-05** | 30 | 0.10 | 2.0 | 15m | Structural lookback |
| **A-06** | 20 | 0.10 | 1.5 | 15m | Tight target |
| **A-07** | 20 | 0.10 | 2.5 | 15m | Extended target |
| **A-08** | 15 | 0.05 | 1.5 | 15m | Fast scalping profile |
| **A-09** | 15 | 0.15 | 2.5 | 15m | Asymmetric expansion |
| **A-10** | 30 | 0.05 | 1.5 | 15m | Conservative sweep |
| **A-11** | 30 | 0.15 | 2.5 | 15m | Swing expansion |
| **A-12** | 20 | 0.08 | 2.2 | 15m | Intermediate balance |

---

## 3. Strategy Candidate B: Breakout / Trend-Following (Donchian + Volume + EMA Filter)

### 3.1 Concept & Economic Rationale
Momentum and trend persistence are documented phenomena in cryptocurrency derivatives markets. Strategy B identifies structural breakouts beyond a rolling Donchian envelope, filtered by volume expansion and confirmed by the higher-level trend direction, to capture sustained regime-driven trends while discarding low-volume range chop.

### 3.2 Mathematical Formalization

#### Causal Indicators
- **Donchian Channel ($M = 20$ bars)**:
  $$D_{upper}(t) = \max_{1 \le k \le M} High_{t-k}, \quad D_{lower}(t) = \min_{1 \le k \le M} Low_{t-k}, \quad D_{mid}(t) = \frac{D_{upper}(t) + D_{lower}(t)}{2}$$
- **Volume Moving Average ($\text{SMA}_{20}(V)$)**:
  $$\overline{V}_{20}(t) = \frac{1}{20}\sum_{k=1}^{20} Volume_{t-k}$$
- **Trend Filter ($\text{EMA}_{50}$)**:
  $$\text{EMA}_{50}(t) = \alpha \cdot Close_t + (1-\alpha) \cdot \text{EMA}_{50}(t-1), \quad \alpha = \frac{2}{50+1}$$
- **Initialization & Burn-In**: Requires $\max(M, 50) + 14 = 64\text{ bars}$. Bar index $< 64$ cannot emit signals.

#### Long Entry Conditions
At candle $t$ Close, enter Long if:
1. **Breakout**: $Close_t > D_{upper}(t)$.
2. **Volume Expansion**: $Volume_t \ge \gamma_{vol} \times \overline{V}_{20}(t)$, where $\gamma_{vol} = 1.20$.
3. **Trend Alignment**: $Close_t > \text{EMA}_{50}(t)$ and $\text{EMA}_{50}(t) > \text{EMA}_{50}(t-1)$.
4. **Dual Channel Anomaly Check**: Candle $t$ must NOT have $Close_t < D_{lower}(t)$ (corrupted data reject).
5. **Position State**: Current position is `FLAT`.

#### Short Entry Conditions
At candle $t$ Close, enter Short if:
1. **Breakdown**: $Close_t < D_{lower}(t)$.
2. **Volume Expansion**: $Volume_t \ge \gamma_{vol} \times \overline{V}_{20}(t)$.
3. **Trend Alignment**: $Close_t < \text{EMA}_{50}(t)$ and $\text{EMA}_{50}(t) < \text{EMA}_{50}(t-1)$.
4. **Dual Channel Anomaly Check**: Candle $t$ must NOT have $Close_t > D_{upper}(t)$.
5. **Position State**: Current position is `FLAT`.

#### Execution & Exit Logic (Deterministically Reconciled)
- **Entry Execution**: Market order filled at $Open_{t+1}$ with adverse slippage.
- **Frozen Stop Loss Definition**: To remove all post-hoc ambiguity, the catastrophic stop loss is deterministically frozen to an ATR volatility distance:
  $$\text{SL}_{long} = \text{Fill Price}_{long} - 1.50 \times \text{ATR}_{14}(t)$$
  $$\text{SL}_{short} = \text{Fill Price}_{short} + 1.50 \times \text{ATR}_{14}(t)$$
- **Trailing Midline Trend Exit**: The dynamic Donchian midline $D_{mid}$ serves strictly as the **regime invalidation exit**. When completed candle Close crosses $D_{mid}$, an exit order is queued for the next bar Open:
  $$\text{Long Midline Exit}: Close_i < D_{mid}(i) \implies \text{Queue Exit at } Open_{i+1}$$
  $$\text{Short Midline Exit}: Close_i > D_{mid}(i) \implies \text{Queue Exit at } Open_{i+1}$$
- **Time-Expiry Exit**: Maximum holding duration $T_{max} = 48\text{ bars}$ ($48.0\text{ hours}$ on 1H timeframe). If neither SL nor Midline exit is triggered by candle $t+48$, an exit order is queued for $Open_{t+49}$.

### 3.3 Pre-Registered 12-Configuration Grid (Strategy B)
| Config ID | Channel $M$ | Volume Multiplier $\gamma_{vol}$ | EMA Filter | Timeframe | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **B-01** | 20 | 1.20 | 50 | 1H | **Default Baseline** |
| **B-02** | 20 | 1.00 | 50 | 1H | Unfiltered volume |
| **B-03** | 20 | 1.50 | 50 | 1H | High volume hurdle |
| **B-04** | 15 | 1.20 | 50 | 1H | Fast channel |
| **B-05** | 30 | 1.20 | 50 | 1H | Slow channel |
| **B-06** | 20 | 1.20 | 30 | 1H | Sensitive trend |
| **B-07** | 20 | 1.20 | 100 | 1H | Macro trend |
| **B-08** | 15 | 1.00 | 30 | 1H | Agile momentum |
| **B-09** | 30 | 1.50 | 100 | 1H | Macro conviction |
| **B-10** | 20 | 1.20 | 50 | 15m | Intraday 15m |
| **B-11** | 30 | 1.20 | 50 | 15m | Structural 15m |
| **B-12** | 20 | 1.50 | 50 | 15m | High volume 15m |

---

## 4. Strategy Candidate C: Mean Reversion (Bollinger Bands + RSI Hook)

### 4.1 Concept & Economic Rationale
In high-frequency crypto trading, asset prices frequently deviate from their short-term equilibrium due to transient liquidity imbalances. Strategy C identifies statistical dispersion beyond a 2-standard-deviation Bollinger Band coupled with oscillator exhaustion (RSI), entering only upon confirmed momentum stabilization back toward the centerline.

### 4.2 Mathematical Formalization

#### Causal Indicators
- **Bollinger Bands ($K_{len} = 20, K_{\sigma} = 2.0$)**:
  $$\mu_t = \frac{1}{20}\sum_{k=1}^{20} Close_{t-k}, \quad \sigma_t = \sqrt{\frac{1}{20}\sum_{k=1}^{20} (Close_{t-k} - \mu_t)^2}$$
  $$\text{BB}_{upper}(t) = \mu_t + 2.0 \cdot \sigma_t, \quad \text{BB}_{lower}(t) = \mu_t - 2.0 \cdot \sigma_t$$
- **Relative Strength Index ($\text{RSI}_{14}$)**:
  Computed via standard Wilder 14-period smoothed gains and losses over prior closes.
- **Initialization & Burn-In**: Requires $\max(K_{len}, 14) + 14 = 34\text{ bars}$. Bar index $< 34$ cannot emit signals.

#### Long Entry Conditions (Oversold Rebound)
1. **Prior Extension**: $Close_{t-1} \le \text{BB}_{lower}(t-1)$ and $\text{RSI}_{14}(t-1) < 30.0$.
2. **Confirmation Hook**: $Close_t > \text{BB}_{lower}(t)$ and $\text{RSI}_{14}(t) > \text{RSI}_{14}(t-1)$.
3. **Dual Band Piercing Check**: Candle $t-1$ must NOT simultaneously breach $\text{BB}_{upper}(t-1)$.
4. **Position State**: Current position is `FLAT`.

#### Short Entry Conditions (Overbought Rebound)
1. **Prior Extension**: $Close_{t-1} \ge \text{BB}_{upper}(t-1)$ and $\text{RSI}_{14}(t-1) > 70.0$.
2. **Confirmation Hook**: $Close_t < \text{BB}_{upper}(t)$ and $\text{RSI}_{14}(t) < \text{RSI}_{14}(t-1)$.
3. **Dual Band Piercing Check**: Candle $t-1$ must NOT simultaneously breach $\text{BB}_{lower}(t-1)$.
4. **Position State**: Current position is `FLAT`.

#### Execution & Exit Logic
- **Entry Execution**: Market order filled at $Open_{t+1}$ with adverse slippage.
- **Stop Loss**: Fixed distance from fill:
  $$\text{SL}_{long} = \text{Fill Price}_{long} - 1.50 \times \text{ATR}_{14}(t)$$
  $$\text{SL}_{short} = \text{Fill Price}_{short} + 1.50 \times \text{ATR}_{14}(t)$$
- **Take Profit (Mean Target)**: Dynamic exit triggered when Close reaches the band centerline $\mu_i$:
  $$\text{Long TP Signal}: Close_i \ge \mu_i \implies \text{Exit at } Open_{i+1}$$
  $$\text{Short TP Signal}: Close_i \le \mu_i \implies \text{Exit at } Open_{i+1}$$
- **Barrier Conflict Precedence**: `CONSERVATIVE_SL_FIRST`.
- **Time-Expiry Exit**: Maximum holding duration $T_{max} = 16\text{ bars}$ ($4.0\text{ hours}$ on 15m timeframe).

### 4.3 Pre-Registered 12-Configuration Grid (Strategy C)
| Config ID | Band Length $K_{len}$ | Band Std $K_\sigma$ | RSI Thresholds | Timeframe | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **C-01** | 20 | 2.0 | 30 / 70 | 15m | **Default Baseline** |
| **C-02** | 20 | 1.8 | 30 / 70 | 15m | Narrow bands |
| **C-03** | 20 | 2.2 | 30 / 70 | 15m | Wide bands |
| **C-04** | 15 | 2.0 | 30 / 70 | 15m | Fast mean |
| **C-05** | 25 | 2.0 | 30 / 70 | 15m | Slow mean |
| **C-06** | 20 | 2.0 | 25 / 75 | 15m | Deep oversold/overbought |
| **C-07** | 20 | 2.0 | 35 / 65 | 15m | Shallow oversold/overbought |
| **C-08** | 15 | 1.8 | 25 / 75 | 15m | Scalping oscillator |
| **C-09** | 15 | 2.2 | 35 / 65 | 15m | Responsive dispersion |
| **C-10** | 25 | 1.8 | 25 / 75 | 15m | Trend reversion |
| **C-11** | 25 | 2.2 | 35 / 65 | 15m | Macro dispersion |
| **C-12** | 20 | 2.1 | 28 / 72 | 15m | Calibrated balance |
