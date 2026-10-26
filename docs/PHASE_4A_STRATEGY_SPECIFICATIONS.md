# VANTA Terminal — Strategy Candidate Specifications
**Document ID:** DOC-STRAT-P4A-001  
**Phase:** 4A (Pre-Strategy Research Protocol)  
**Verification Date:** 2026-10-27  
**Status:** FROZEN FOR WALK-FORWARD BENCHMARKING  

---

## 1. Overview & Objective

This document pre-registers the exact, causal, mathematically formalized candidate strategies to be benchmarked in Phase 4B.

To maintain strict scientific integrity, **no discretionary post-hoc parameter adjustments** are permitted during or after benchmark evaluation. All mathematical rules, indicator formulas, entry/exit logic, execution mechanics, and friction assumptions are frozen herein.

### Guiding Principles:
1. **Zero Lookahead Bias**: Every indicator and decision at candle $t$ uses information strictly available at or prior to the close of candle $t$. Orders execute at the Open of candle $t+1$ with adverse slippage.
2. **Realistic Friction Accounting**: All market orders incur a $5.0\text{ bps}$ ($0.05\%$) taker fee and $2.0\text{ bps}$ ($0.02\%$) adverse slippage on entry and exit ($14.0\text{ bps}$ minimum round-trip friction hurdle).
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
  $$L_{ref}(t) = \min_{1 \le k \le N} Low_{t-k}$$
  $$H_{ref}(t) = \max_{1 \le k \le N} High_{t-k}$$
  *(Bar $t$ is strictly excluded from the reference calculation to prevent lookahead).*
- **Average True Range ($\text{ATR}_{14}$)**:
  $$\text{TR}_i = \max\left(High_i - Low_i, |High_i - Close_{i-1}|, |Low_i - Close_{i-1}|\right)$$
  $$\text{ATR}_{14}(t) = \frac{1}{14}\sum_{k=0}^{13} \text{TR}_{t-k}$$

#### Long Entry Conditions (Bullish Sweep & Reclaim)
At candle $t$ Close, a Long signal is triggered if all three criteria hold:
1. **Liquidity Sweep**:
   $$Low_t < L_{ref}(t) \quad \text{and} \quad (L_{ref}(t) - Low_t) \ge \delta_{sweep} \times \text{ATR}_{14}(t)$$
   where $\delta_{sweep} = 0.10$ ($10\%$ of ATR).
2. **Range Reclaim**:
   $$Close_t > L_{ref}(t)$$
3. **Position State**: Current position for instrument is `FLAT`.

#### Short Entry Conditions (Bearish Sweep & Reclaim)
At candle $t$ Close, a Short signal is triggered if all three criteria hold:
1. **Liquidity Sweep**:
   $$High_t > H_{ref}(t) \quad \text{and} \quad (High_t - H_{ref}(t)) \ge \delta_{sweep} \times \text{ATR}_{14}(t)$$
2. **Range Reclaim**:
   $$Close_t < H_{ref}(t)$$
3. **Position State**: Current position for instrument is `FLAT`.

#### Execution & Exit Logic
- **Entry Execution**: Market order submitted at Close of bar $t$, executed at $Open_{t+1}$ with adverse slippage:
  $$\text{Fill Price}_{long} = Open_{t+1} \times (1 + \text{Slippage})$$
  $$\text{Fill Price}_{short} = Open_{t+1} \times (1 - \text{Slippage})$$
- **Stop Loss (SL)**:
  $$\text{SL}_{long} = Low_t - \delta_{buf} \times \text{ATR}_{14}(t), \quad \delta_{buf} = 0.10$$
  $$\text{SL}_{short} = High_t + \delta_{buf} \times \text{ATR}_{14}(t), \quad \delta_{buf} = 0.10$$
- **Take Profit (TP)**: Fixed $2.0\times$ Risk-to-Reward ratio:
  $$\text{TP}_{long} = \text{Fill Price}_{long} + 2.0 \times \left(\text{Fill Price}_{long} - \text{SL}_{long}\right)$$
  $$\text{TP}_{short} = \text{Fill Price}_{short} - 2.0 \times \left(\text{SL}_{short} - \text{Fill Price}_{short}\right)$$
- **Time-Expiry Exit**: Maximum holding duration $T_{max} = 24\text{ bars}$ (6.0 hours on 15m timeframe). If neither TP nor SL is triggered by candle $t+24$, an exit order is queued for $Open_{t+25}$.

### 2.3 Parameter Set & Bounded Tuning Grid
- Lookback Period $N \in \{15, 20, 30\}$ (Default: `20`)
- Sweep Threshold $\delta_{sweep} \in \{0.05, 0.10, 0.15\}$ (Default: `0.10`)
- Risk-Reward Ratio $R:R \in \{1.5, 2.0, 2.5\}$ (Default: `2.0`)
- Primary Timeframe: `15m`

---

## 3. Strategy Candidate B: Breakout / Trend-Following (Donchian + Volume + EMA Filter)

### 3.1 Concept & Economic Rationale
Momentum and trend persistence are documented phenomena in cryptocurrency derivatives markets. Strategy B identifies structural breakouts beyond a rolling Donchian envelope, filtered by volume expansion and confirmed by the higher-level trend direction, to capture sustained regime-driven trends while discarding low-volume range chop.

### 3.2 Mathematical Formalization

#### Causal Indicators
- **Donchian Channel ($M = 20$ bars)**:
  $$D_{upper}(t) = \max_{1 \le k \le M} High_{t-k}$$
  $$D_{lower}(t) = \min_{1 \le k \le M} Low_{t-k}$$
  $$D_{mid}(t) = \frac{D_{upper}(t) + D_{lower}(t)}{2}$$
- **Volume Moving Average ($\text{SMA}_{20}(V)$)**:
  $$\overline{V}_{20}(t) = \frac{1}{20}\sum_{k=1}^{20} Volume_{t-k}$$
- **Trend Filter ($\text{EMA}_{50}$)**:
  $$\text{EMA}_{50}(t) = \alpha \cdot Close_t + (1-\alpha) \cdot \text{EMA}_{50}(t-1), \quad \alpha = \frac{2}{50+1}$$

#### Long Entry Conditions
At candle $t$ Close, enter Long if:
1. **Breakout**: $Close_t > D_{upper}(t)$.
2. **Volume Expansion**: $Volume_t \ge \gamma_{vol} \times \overline{V}_{20}(t)$, where $\gamma_{vol} = 1.20$.
3. **Trend Alignment**: $Close_t > \text{EMA}_{50}(t)$ and $\text{EMA}_{50}(t) > \text{EMA}_{50}(t-1)$.
4. **Position State**: Current position is `FLAT`.

#### Short Entry Conditions
At candle $t$ Close, enter Short if:
1. **Breakdown**: $Close_t < D_{lower}(t)$.
2. **Volume Expansion**: $Volume_t \ge \gamma_{vol} \times \overline{V}_{20}(t)$.
3. **Trend Alignment**: $Close_t < \text{EMA}_{50}(t)$ and $\text{EMA}_{50}(t) < \text{EMA}_{50}(t-1)$.
4. **Position State**: Current position is `FLAT`.

#### Execution & Exit Logic
- **Entry Execution**: Market order filled at $Open_{t+1}$ with adverse slippage.
- **Initial Stop Loss**:
  $$\text{SL}_{long} = \max\left(\text{Fill Price} - 1.50 \times \text{ATR}_{14}(t), \, D_{mid}(t)\right)$$
  $$\text{SL}_{short} = \min\left(\text{Fill Price} + 1.50 \times \text{ATR}_{14}(t), \, D_{mid}(t)\right)$$
- **Trailing Channel Exit**: If $Close_i$ crosses the dynamic Donchian midline $D_{mid}(i)$, emit exit signal at candle $i$ close to close at $Open_{i+1}$:
  $$\text{Long Exit Signal}: Close_i < D_{mid}(i)$$
  $$\text{Short Exit Signal}: Close_i > D_{mid}(i)$$
- **Time-Expiry Exit**: Maximum holding duration $T_{max} = 48\text{ bars}$ (48 hours on 1H timeframe, or 12 hours on 15m timeframe).

### 3.3 Parameter Set & Bounded Tuning Grid
- Channel Period $M \in \{15, 20, 30\}$ (Default: `20`)
- Volume Multiplier $\gamma_{vol} \in \{1.0, 1.2, 1.5\}$ (Default: `1.20`)
- Trend Filter Length $\in \{30, 50, 100\}$ (Default: `50`)
- Primary Timeframes: `1H` (Primary) and `15m` (Secondary)

---

## 4. Strategy Candidate C: Mean Reversion (Bollinger Bands + RSI Hook)

### 4.1 Concept & Economic Rationale
In high-frequency crypto trading, asset prices frequently deviate from their short-term equilibrium due to transient liquidity imbalances. Strategy C identifies statistical dispersion beyond a 2-standard-deviation Bollinger Band coupled with oscillator exhaustion (RSI), entering only upon confirmed momentum stabilization back toward the centerline.

### 4.2 Mathematical Formalization

#### Causal Indicators
- **Bollinger Bands ($K_{len} = 20, K_{\sigma} = 2.0$)**:
  $$\mu_t = \frac{1}{20}\sum_{k=1}^{20} Close_{t-k}$$
  $$\sigma_t = \sqrt{\frac{1}{20}\sum_{k=1}^{20} (Close_{t-k} - \mu_t)^2}$$
  $$\text{BB}_{upper}(t) = \mu_t + 2.0 \cdot \sigma_t, \quad \text{BB}_{lower}(t) = \mu_t - 2.0 \cdot \sigma_t$$
- **Relative Strength Index ($\text{RSI}_{14}$)**:
  Computed via standard Wilder 14-period smoothed gains and losses over prior closes.

#### Long Entry Conditions (Oversold Rebound)
1. **Prior Extension**: $Close_{t-1} \le \text{BB}_{lower}(t-1)$ and $\text{RSI}_{14}(t-1) < 30.0$.
2. **Confirmation Hook**: $Close_t > \text{BB}_{lower}(t)$ and $\text{RSI}_{14}(t) > \text{RSI}_{14}(t-1)$.
3. **Position State**: Current position is `FLAT`.

#### Short Entry Conditions (Overbought Rebound)
1. **Prior Extension**: $Close_{t-1} \ge \text{BB}_{upper}(t-1)$ and $\text{RSI}_{14}(t-1) > 70.0$.
2. **Confirmation Hook**: $Close_t < \text{BB}_{upper}(t)$ and $\text{RSI}_{14}(t) < \text{RSI}_{14}(t-1)$.
3. **Position State**: Current position is `FLAT`.

#### Execution & Exit Logic
- **Entry Execution**: Market order filled at $Open_{t+1}$ with adverse slippage.
- **Stop Loss**: Fixed distance from fill:
  $$\text{SL}_{long} = \text{Fill Price} - 1.50 \times \text{ATR}_{14}(t)$$
  $$\text{SL}_{short} = \text{Fill Price} + 1.50 \times \text{ATR}_{14}(t)$$
- **Take Profit (Mean Target)**: Dynamic exit triggered when Close reaches the band centerline $\mu_i$:
  $$\text{Long TP Signal}: Close_i \ge \mu_i \implies \text{Exit at } Open_{i+1}$$
  $$\text{Short TP Signal}: Close_i \le \mu_i \implies \text{Exit at } Open_{i+1}$$
- **Time-Expiry Exit**: Maximum holding duration $T_{max} = 16\text{ bars}$ (4.0 hours on 15m timeframe).

### 4.3 Parameter Set & Bounded Tuning Grid
- Band Period $K_{len} \in \{15, 20, 25\}$ (Default: `20`)
- Band Width $K_{\sigma} \in \{1.8, 2.0, 2.2\}$ (Default: `2.0`)
- RSI Thresholds $\in \{(25, 75), (30, 70), (35, 65)\}$ (Default: `30 / 70`)
- Primary Timeframe: `15m`

---

## 5. Candidate Comparison & Specification Matrix

| Specification Dimension | Candidate A: Sweep-Reclaim | Candidate B: Trend-Breakout | Candidate C: Mean Reversion |
| :--- | :--- | :--- | :--- |
| **Strategy Style** | Liquidity Sweep / Absorption | Momentum Expansion | Statistical Oscillation |
| **Primary Timeframe** | 15m | 1H (and 15m) | 15m |
| **Core Regime Target** | Range edges / Stop clusters | Strong trending impulses | Mean-reverting consolidation |
| **Lookahead Prevention** | Reference excludes Bar $t$ | Envelope excludes Bar $t$ | Mean/SD excludes Bar $t$ |
| **Signal-to-Execution** | Signal at $t$ Close $\to$ Fill $t+1$ Open | Signal at $t$ Close $\to$ Fill $t+1$ Open | Signal at $t$ Close $\to$ Fill $t+1$ Open |
| **Stop Loss Rule** | Sweep extreme $\pm 0.1\text{ ATR}$ | Midline / $1.5\text{ ATR}$ | $1.5\text{ ATR}$ from entry |
| **Take Profit Rule** | $2.0\times$ Risk-to-Reward | Trailing Donchian Midline | Bollinger Centerline $\mu$ |
| **Max Time-in-Trade** | 24 bars (6h) | 48 bars (48h) | 16 bars (4h) |
| **Position Sizing** | 10% Equity, 1.0x Leverage | 10% Equity, 1.0x Leverage | 10% Equity, 1.0x Leverage |
| **Overlapping Trades** | Blocked (`FLAT` required) | Blocked (`FLAT` required) | Blocked (`FLAT` required) |
| **Taker Fee / Slippage** | 5.0 bps / 2.0 bps | 5.0 bps / 2.0 bps | 5.0 bps / 2.0 bps |
| **Default Cost Model** | Funding-neutral baseline | Funding-neutral baseline | Funding-neutral baseline |
