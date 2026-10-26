"""
VANTA Terminal — Backtest Schemas & Core Data Models
===================================================
Strongly-typed Pydantic v2 models and enums for deterministic backtesting,
trade ledgers, portfolio state, execution policies, and audit manifests.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator
import hashlib
import json


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class PositionSide(str, Enum):
    FLAT = "FLAT"
    LONG = "LONG"
    SHORT = "SHORT"


class ExecutionPolicy(str, Enum):
    CONSERVATIVE_SL_FIRST = "CONSERVATIVE_SL_FIRST"
    FAVORABLE_TP_FIRST = "FAVORABLE_TP_FIRST"


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TIME_EXPIRY = "TIME_EXPIRY"
    SIGNAL_EXIT = "SIGNAL_EXIT"
    MARGIN_CALL = "MARGIN_CALL"
    MANUAL_CLOSE = "MANUAL_CLOSE"


class SizingType(str, Enum):
    FIXED_NOTIONAL = "FIXED_NOTIONAL"
    PERCENT_EQUITY = "PERCENT_EQUITY"
    FIXED_UNITS = "FIXED_UNITS"


class RunStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED_MISSING_FUNDING_DATA = "BLOCKED_MISSING_FUNDING_DATA"
    CANCELLED = "CANCELLED"


class BacktestConfig(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    initial_equity: float = Field(default=10000.0, gt=0.0)
    maker_fee_bps: float = Field(default=2.0, ge=0.0)      # 2 bps = 0.02%
    taker_fee_bps: float = Field(default=5.0, ge=0.0)      # 5 bps = 0.05%
    slippage_bps: float = Field(default=2.0, ge=0.0)       # 2 bps = 0.02%
    use_funding: bool = False                              # Requires verified funding dataset
    intrabar_policy: ExecutionPolicy = ExecutionPolicy.CONSERVATIVE_SL_FIRST
    sizing_type: SizingType = SizingType.PERCENT_EQUITY
    sizing_value: float = Field(default=10.0, gt=0.0)      # e.g. 10.0% of equity or 1000 USDT
    max_leverage: float = Field(default=1.0, ge=1.0)
    max_position_notional: Optional[float] = None
    min_trade_size: float = Field(default=0.001, gt=0.0)
    qty_step_decimals: int = Field(default=3, ge=0)
    price_tick_decimals: int = Field(default=2, ge=0)
    annualization_factor: float = Field(default=365.25 * 24 * 4) # 15m default (35,064 bars/yr)

    def compute_config_hash(self) -> str:
        """Deterministic SHA-256 hash of configuration parameters."""
        cfg_dict = self.model_dump(mode="json")
        canonical_json = json.dumps(cfg_dict, sort_keys=True)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class TradeRecord(BaseModel):
    trade_id: int
    run_id: str
    symbol: str
    side: PositionSide
    entry_time_ms: int
    exit_time_ms: int
    entry_price: float
    exit_price: float
    quantity: float
    notional: float
    gross_pnl: float
    entry_fee: float
    exit_fee: float
    total_fee: float
    slippage_cost: float
    funding_payment: float
    net_pnl: float
    return_pct: float
    holding_duration_bars: int
    holding_duration_ms: int
    exit_reason: ExitReason
    is_ambiguous: bool = False
    equity_before: float
    equity_after: float


class EquityPoint(BaseModel):
    timestamp_ms: int
    bar_index: int
    equity: float
    cash: float
    unrealized_pnl: float
    drawdown_pct: float
    high_watermark: float


class CostBreakdown(BaseModel):
    total_gross_pnl: float
    total_fees_paid: float
    maker_fees_paid: float
    taker_fees_paid: float
    total_slippage_cost: float
    total_funding_paid: float
    total_funding_received: float
    net_pnl: float


class PerformanceMetrics(BaseModel):
    initial_equity: float
    final_equity: float
    net_profit: float
    net_return_pct: float
    max_drawdown_pct: float
    max_drawdown_duration_bars: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    expectancy: float
    avg_win: float
    avg_loss: float
    win_loss_ratio: float
    avg_holding_bars: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    ambiguous_trade_count: int


class BacktestResult(BaseModel):
    run_id: str
    config_hash: str
    config: BacktestConfig
    dataset_id: str
    dataset_sha256: str
    status: RunStatus
    metrics: Optional[PerformanceMetrics] = None
    cost_breakdown: Optional[CostBreakdown] = None
    trades_count: int = 0
    trade_ledger: List[TradeRecord] = Field(default_factory=list)
    equity_curve: List[EquityPoint] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    start_time_utc: Optional[str] = None
    end_time_utc: Optional[str] = None
    created_at_utc: str
    is_synthetic_test: bool = False


class BacktestRunSummary(BaseModel):
    run_id: str
    config_hash: str
    symbol: str
    timeframe: str
    status: RunStatus
    net_return_pct: float
    max_drawdown_pct: float
    win_rate_pct: float
    total_trades: int
    sharpe_ratio: float
    dataset_id: str
    is_synthetic_test: bool
    created_at_utc: str
