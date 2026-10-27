"""
VANTA Terminal — Canonical Walk-Forward Evaluation Framework V2 (Phase 4B.4)
=============================================================================
Integrates the CanonicalPortfolioEngine with the frozen 3-fold Walk-Forward protocol:
1. Multi-pair shared capital pool ($10,000 reset per fold).
2. Synchronized multi-stream event queue.
3. 48-hour purge/embargo isolation.
4. Candle-level mark-to-market drawdown per fold and combined.
5. Strict quarantine guard (< 2026-04-26T00:00:00Z).
"""

from typing import List, Dict, Any, Optional, Tuple, Callable
from pathlib import Path
from pydantic import BaseModel, Field
import json
import hashlib

from backend.backtest.portfolio_engine import (
    CanonicalPortfolioEngine,
    PortfolioEngineConfig,
    PortfolioRunResult
)
from backend.strategy.qualification import QUALIFIED_PAIRS
from backend.data.loader import load_research_dataset, HOLDOUT_CUTOFF_MS
from backend.strategy.walk_forward_runner import FOLDS_SCHEDULE


class FoldValidationResult(BaseModel):
    fold_id: int
    initial_equity: float
    final_equity: float
    net_profit: float
    net_return_pct: float
    mtm_max_drawdown_pct: float
    closed_trade_max_drawdown_pct: float
    trades_count: int
    winning_trades: int
    losing_trades: int
    profit_factor: float
    expectancy: float
    is_profitable: bool
    rejected_orders_count: int
    trades_by_symbol: Dict[str, int]
    net_pnl_by_symbol: Dict[str, float]


class WalkForwardV2Summary(BaseModel):
    strategy_id: str
    strategy_name: str
    timeframe: str
    evaluation_timestamp_utc: str
    folds: List[FoldValidationResult]
    combined_metrics: Dict[str, Any]
    fold_isolation_statement: str
    quarantine_verified: bool


class WalkForwardV2Runner:
    """
    Executes walk-forward evaluation using the multi-pair shared-margin portfolio engine.
    """

    def __init__(
        self,
        data_root: Path = Path("D:/vanta-terminal/data"),
        target_position_pct: float = 10.0,
        max_leverage: float = 1.0
    ):
        self.data_root = data_root
        self.target_position_pct = target_position_pct
        self.max_leverage = max_leverage

    def get_dataset_path(self, symbol: str, timeframe: str) -> Path:
        tf = timeframe.lower()
        if tf == "15m":
            p = self.data_root / "raw" / symbol / "15m.parquet"
        elif tf in ["1h", "4h"]:
            p = self.data_root / "derived" / symbol / f"{tf}.parquet"
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        if not p.exists():
            raise FileNotFoundError(f"Parquet dataset not found at {p}")
        return p

    def load_slice(
        self,
        symbol: str,
        timeframe: str,
        start_ms: int,
        end_ms: int
    ) -> List[List[Any]]:
        path = self.get_dataset_path(symbol, timeframe)
        candles, meta = load_research_dataset(path, enforce_holdout_guard=True)
        # Slices strictly within [start_ms, end_ms)
        return [c for c in candles if start_ms <= c[0] < end_ms]

    def run_fold_oos(
        self,
        fold_id: int,
        timeframe: str,
        strategy_factory: Callable[[str], Any],
        symbols: Optional[List[str]] = None
    ) -> PortfolioRunResult:
        """
        Runs a single Out-of-Sample fold with a fresh isolated $10,000 cash reset.
        """
        eval_symbols = symbols or QUALIFIED_PAIRS
        fold = next(f for f in FOLDS_SCHEDULE if f["fold_id"] == fold_id)

        # Slice data for the embargo warmup and OOS period:
        # Candles fed from embargo_start_ms to oos_end_ms
        raw_datasets = {}
        for sym in eval_symbols:
            raw_datasets[sym] = self.load_slice(
                symbol=sym,
                timeframe=timeframe,
                start_ms=fold["embargo_start_ms"],
                end_ms=fold["oos_end_ms"]
            )

        cfg = PortfolioEngineConfig(
            initial_equity=10000.0,  # Fresh $10,000 cash reset
            target_position_pct=self.target_position_pct,
            max_leverage=self.max_leverage,
            max_simultaneous_positions=len(eval_symbols),
            taker_fee_bps=5.0,
            slippage_bps=2.0,
            use_funding=False
        )

        engine = CanonicalPortfolioEngine(cfg)
        result = engine.run(
            raw_datasets=raw_datasets,
            strategy_factory=strategy_factory,
            run_id=f"WF2_FOLD_{fold_id}_{timeframe}"
        )
        return result
