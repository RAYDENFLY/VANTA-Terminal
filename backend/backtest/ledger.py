"""
VANTA Terminal — Trade Ledger & Reproducibility Serialization
=============================================================
Records trade-by-trade executions, equity snapshots, and immutable run artifacts.
Persists backtest results to versioned directories on HDD D:.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib

from backend.backtest.schemas import TradeRecord, EquityPoint, BacktestResult, BacktestRunSummary

BACKTEST_STORAGE_ROOT = Path("D:/vanta-terminal/data/backtests")


class TradeLedger:
    """
    Collects execution records, mark-to-market equity snapshots, and audit metadata.
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[EquityPoint] = []
        self.warnings: List[str] = []
        self.next_trade_id: int = 1

    def add_trade(self, trade: TradeRecord) -> None:
        self.trades.append(trade)

    def add_equity_point(self, point: EquityPoint) -> None:
        self.equity_curve.append(point)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def get_next_trade_id(self) -> int:
        tid = self.next_trade_id
        self.next_trade_id += 1
        return tid

    def save_run_artifacts(self, result: BacktestResult) -> Path:
        """
        Persists run results, trade ledger, and equity curve to a dedicated versioned directory.
        Returns the output directory path.
        """
        run_dir = BACKTEST_STORAGE_ROOT / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save main result JSON
        result_file = run_dir / "result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        # 2. Save Trade Ledger
        trades_file = run_dir / "trade_ledger.json"
        trades_data = [t.model_dump(mode="json") for t in self.trades]
        with open(trades_file, "w", encoding="utf-8") as f:
            json.dump(trades_data, f, indent=2)

        # 3. Save Equity Curve
        equity_file = run_dir / "equity_curve.json"
        equity_data = [pt.model_dump(mode="json") for pt in self.equity_curve]
        with open(equity_file, "w", encoding="utf-8") as f:
            json.dump(equity_data, f, indent=2)

        # 4. Save Run Manifest
        manifest_file = run_dir / "run_manifest.json"
        res_sha = hashlib.sha256(result_file.read_bytes()).hexdigest()
        manifest = {
            "run_id": self.run_id,
            "config_hash": result.config_hash,
            "dataset_id": result.dataset_id,
            "dataset_sha256": result.dataset_sha256,
            "status": result.status.value,
            "total_trades": len(self.trades),
            "final_equity": result.metrics.final_equity if result.metrics else 0.0,
            "net_return_pct": result.metrics.net_return_pct if result.metrics else 0.0,
            "max_drawdown_pct": result.metrics.max_drawdown_pct if result.metrics else 0.0,
            "result_file_sha256": res_sha,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "is_synthetic_test": result.is_synthetic_test
        }
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return run_dir


def load_backtest_run(run_id: str) -> Optional[BacktestResult]:
    """Loads a previously persisted backtest run by ID."""
    result_file = BACKTEST_STORAGE_ROOT / run_id / "result.json"
    if not result_file.exists():
        return None
    try:
        with open(result_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BacktestResult(**data)
    except Exception:
        return None


def list_backtest_runs() -> List[BacktestRunSummary]:
    """Lists all available persisted backtest runs in reverse chronological order."""
    if not BACKTEST_STORAGE_ROOT.exists():
        return []

    summaries = []
    for run_dir in sorted(BACKTEST_STORAGE_ROOT.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        manifest_file = run_dir / "run_manifest.json"
        result_file = run_dir / "result.json"

        if manifest_file.exists() and result_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    mf = json.load(f)
                with open(result_file, "r", encoding="utf-8") as f:
                    res = json.load(f)

                cfg = res.get("config", {})
                met = res.get("metrics", {})
                summaries.append(
                    BacktestRunSummary(
                        run_id=mf.get("run_id", run_dir.name),
                        config_hash=mf.get("config_hash", ""),
                        symbol=cfg.get("symbol", "UNKNOWN"),
                        timeframe=cfg.get("timeframe", "UNKNOWN"),
                        status=mf.get("status", "SUCCESS"),
                        net_return_pct=met.get("net_return_pct", 0.0),
                        max_drawdown_pct=met.get("max_drawdown_pct", 0.0),
                        win_rate_pct=met.get("win_rate_pct", 0.0),
                        total_trades=mf.get("total_trades", 0),
                        sharpe_ratio=met.get("sharpe_ratio", 0.0),
                        dataset_id=mf.get("dataset_id", ""),
                        is_synthetic_test=mf.get("is_synthetic_test", False),
                        created_at_utc=mf.get("created_at_utc", "")
                    )
                )
            except Exception:
                continue

    return summaries
