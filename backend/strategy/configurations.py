"""
VANTA Terminal — Pre-Registered Strategy Candidate Configurations
================================================================
Defines strongly-typed configurations for Strategies A, B, and C.
Enforces the frozen 12-configuration budget per candidate.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StrategyAConfig(BaseModel):
    config_id: str
    lookback_n: int = Field(default=20, ge=10, le=50)
    sweep_delta: float = Field(default=0.10, gt=0.0)
    risk_reward: float = Field(default=2.0, gt=0.0)
    timeframe: str = "15m"
    notes: str = ""


class StrategyBConfig(BaseModel):
    config_id: str
    channel_m: int = Field(default=20, ge=10, le=50)
    volume_mult: float = Field(default=1.20, gt=0.0)
    ema_filter: int = Field(default=50, ge=10, le=200)
    timeframe: str = "1H"
    notes: str = ""


class StrategyCConfig(BaseModel):
    config_id: str
    band_len: int = Field(default=20, ge=10, le=50)
    band_std: float = Field(default=2.0, gt=0.0)
    rsi_oversold: float = Field(default=30.0, ge=10.0, le=45.0)
    rsi_overbought: float = Field(default=70.0, ge=55.0, le=90.0)
    timeframe: str = "15m"
    notes: str = ""


# Pre-Registered 12-Configuration Grid for Strategy A (Sweep-Reclaim)
# Reconciled from 27-state Cartesian space (3x3x3) to 12 frozen points:
# Default baseline + 1D sensitivity shifts (A-02..A-07) + corner/balanced shifts (A-08..A-12)
STRATEGY_A_GRID: List[StrategyAConfig] = [
    StrategyAConfig(config_id="A-01", lookback_n=20, sweep_delta=0.10, risk_reward=2.0, timeframe="15m", notes="Default Baseline"),
    StrategyAConfig(config_id="A-02", lookback_n=20, sweep_delta=0.05, risk_reward=2.0, timeframe="15m", notes="Shallow sweep"),
    StrategyAConfig(config_id="A-03", lookback_n=20, sweep_delta=0.15, risk_reward=2.0, timeframe="15m", notes="Deep sweep"),
    StrategyAConfig(config_id="A-04", lookback_n=15, sweep_delta=0.10, risk_reward=2.0, timeframe="15m", notes="Responsive lookback"),
    StrategyAConfig(config_id="A-05", lookback_n=30, sweep_delta=0.10, risk_reward=2.0, timeframe="15m", notes="Structural lookback"),
    StrategyAConfig(config_id="A-06", lookback_n=20, sweep_delta=0.10, risk_reward=1.5, timeframe="15m", notes="Tight target"),
    StrategyAConfig(config_id="A-07", lookback_n=20, sweep_delta=0.10, risk_reward=2.5, timeframe="15m", notes="Extended target"),
    StrategyAConfig(config_id="A-08", lookback_n=15, sweep_delta=0.05, risk_reward=1.5, timeframe="15m", notes="Fast scalping profile"),
    StrategyAConfig(config_id="A-09", lookback_n=15, sweep_delta=0.15, risk_reward=2.5, timeframe="15m", notes="Asymmetric expansion"),
    StrategyAConfig(config_id="A-10", lookback_n=30, sweep_delta=0.05, risk_reward=1.5, timeframe="15m", notes="Conservative sweep"),
    StrategyAConfig(config_id="A-11", lookback_n=30, sweep_delta=0.15, risk_reward=2.5, timeframe="15m", notes="Swing expansion"),
    StrategyAConfig(config_id="A-12", lookback_n=20, sweep_delta=0.08, risk_reward=2.2, timeframe="15m", notes="Intermediate balance"),
]

# Pre-Registered 12-Configuration Grid for Strategy B (Donchian Breakout)
# Reconciled from 27-state Cartesian space (3x3x3) to 12 frozen points:
# Default baseline + 1D sensitivity shifts (B-02..B-07) + corner/15m shifts (B-08..B-12)
STRATEGY_B_GRID: List[StrategyBConfig] = [
    StrategyBConfig(config_id="B-01", channel_m=20, volume_mult=1.20, ema_filter=50, timeframe="1H", notes="Default Baseline"),
    StrategyBConfig(config_id="B-02", channel_m=20, volume_mult=1.00, ema_filter=50, timeframe="1H", notes="Unfiltered volume"),
    StrategyBConfig(config_id="B-03", channel_m=20, volume_mult=1.50, ema_filter=50, timeframe="1H", notes="High volume hurdle"),
    StrategyBConfig(config_id="B-04", channel_m=15, volume_mult=1.20, ema_filter=50, timeframe="1H", notes="Fast channel"),
    StrategyBConfig(config_id="B-05", channel_m=30, volume_mult=1.20, ema_filter=50, timeframe="1H", notes="Slow channel"),
    StrategyBConfig(config_id="B-06", channel_m=20, volume_mult=1.20, ema_filter=30, timeframe="1H", notes="Sensitive trend"),
    StrategyBConfig(config_id="B-07", channel_m=20, volume_mult=1.20, ema_filter=100, timeframe="1H", notes="Macro trend"),
    StrategyBConfig(config_id="B-08", channel_m=15, volume_mult=1.00, ema_filter=30, timeframe="1H", notes="Agile momentum"),
    StrategyBConfig(config_id="B-09", channel_m=30, volume_mult=1.50, ema_filter=100, timeframe="1H", notes="Macro conviction"),
    StrategyBConfig(config_id="B-10", channel_m=20, volume_mult=1.20, ema_filter=50, timeframe="15m", notes="Intraday 15m"),
    StrategyBConfig(config_id="B-11", channel_m=30, volume_mult=1.20, ema_filter=50, timeframe="15m", notes="Structural 15m"),
    StrategyBConfig(config_id="B-12", channel_m=20, volume_mult=1.50, ema_filter=50, timeframe="15m", notes="High volume 15m"),
]

# Pre-Registered 12-Configuration Grid for Strategy C (Mean Reversion)
# Reconciled from 27-state Cartesian space (3x3x3) to 12 frozen points:
# Default baseline + 1D sensitivity shifts (C-02..C-07) + corner/calibrated shifts (C-08..C-12)
STRATEGY_C_GRID: List[StrategyCConfig] = [
    StrategyCConfig(config_id="C-01", band_len=20, band_std=2.0, rsi_oversold=30.0, rsi_overbought=70.0, timeframe="15m", notes="Default Baseline"),
    StrategyCConfig(config_id="C-02", band_len=20, band_std=1.8, rsi_oversold=30.0, rsi_overbought=70.0, timeframe="15m", notes="Narrow bands"),
    StrategyCConfig(config_id="C-03", band_len=20, band_std=2.2, rsi_oversold=30.0, rsi_overbought=70.0, timeframe="15m", notes="Wide bands"),
    StrategyCConfig(config_id="C-04", band_len=15, band_std=2.0, rsi_oversold=30.0, rsi_overbought=70.0, timeframe="15m", notes="Fast mean"),
    StrategyCConfig(config_id="C-05", band_len=25, band_std=2.0, rsi_oversold=30.0, rsi_overbought=70.0, timeframe="15m", notes="Slow mean"),
    StrategyCConfig(config_id="C-06", band_len=20, band_std=2.0, rsi_oversold=25.0, rsi_overbought=75.0, timeframe="15m", notes="Deep oversold/overbought"),
    StrategyCConfig(config_id="C-07", band_len=20, band_std=2.0, rsi_oversold=35.0, rsi_overbought=65.0, timeframe="15m", notes="Shallow oversold/overbought"),
    StrategyCConfig(config_id="C-08", band_len=15, band_std=1.8, rsi_oversold=25.0, rsi_overbought=75.0, timeframe="15m", notes="Scalping oscillator"),
    StrategyCConfig(config_id="C-09", band_len=15, band_std=2.2, rsi_oversold=35.0, rsi_overbought=65.0, timeframe="15m", notes="Responsive dispersion"),
    StrategyCConfig(config_id="C-10", band_len=25, band_std=1.8, rsi_oversold=25.0, rsi_overbought=75.0, timeframe="15m", notes="Trend reversion"),
    StrategyCConfig(config_id="C-11", band_len=25, band_std=2.2, rsi_oversold=35.0, rsi_overbought=65.0, timeframe="15m", notes="Macro dispersion"),
    StrategyCConfig(config_id="C-12", band_len=20, band_std=2.1, rsi_oversold=28.0, rsi_overbought=72.0, timeframe="15m", notes="Calibrated balance"),
]


def get_strategy_grid(strategy_id: str) -> List[Any]:
    """
    Returns the frozen 12-configuration parameter grid for the specified strategy family.
    Validates that count is exactly 12 and IDs are unique.
    """
    sid = strategy_id.upper()
    if "SWEEP" in sid or sid == "STRAT-SWEEP-01" or sid == "A":
        grid = STRATEGY_A_GRID
    elif "BREAK" in sid or sid == "STRAT-BREAK-01" or sid == "B":
        grid = STRATEGY_B_GRID
    elif "MEAN" in sid or sid == "STRAT-MEAN-01" or sid == "C":
        grid = STRATEGY_C_GRID
    else:
        raise ValueError(f"Unknown strategy family: {strategy_id}")

    if len(grid) != 12:
        raise ValueError(f"Configuration budget violation: Expected 12 configs, got {len(grid)}")

    ids = [c.config_id for c in grid]
    if len(set(ids)) != 12:
        raise ValueError(f"Duplicate configuration IDs detected in {strategy_id}: {ids}")

    return grid
