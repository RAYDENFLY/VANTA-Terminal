"""
VANTA Terminal — Backtest REST API Endpoints
============================================
Read-only endpoints for backtest run registry, trade ledgers,
equity curves, risk analytics, and synthetic verification.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from backend.backtest.schemas import BacktestResult, BacktestRunSummary, TradeRecord, EquityPoint
from backend.backtest.ledger import list_backtest_runs, load_backtest_run

router = APIRouter(prefix="/backtest", tags=["Backtest Engine"])


@router.get("/runs", response_model=List[BacktestRunSummary])
def get_backtest_runs():
    """Lists all historical and synthetic backtest runs."""
    return list_backtest_runs()


@router.get("/{run_id}", response_model=BacktestResult)
def get_backtest_run(run_id: str):
    """Retrieves full backtest run details, metrics, and manifest."""
    res = load_backtest_run(run_id)
    if res is None:
        raise HTTPException(status_code=404, detail=f"Backtest run '{run_id}' not found.")
    return res


@router.get("/{run_id}/ledger", response_model=List[TradeRecord])
def get_backtest_ledger(run_id: str):
    """Retrieves trade ledger for a specific run."""
    res = load_backtest_run(run_id)
    if res is None:
        raise HTTPException(status_code=404, detail=f"Backtest run '{run_id}' not found.")
    return res.trade_ledger


@router.get("/{run_id}/equity", response_model=List[EquityPoint])
def get_backtest_equity(run_id: str):
    """Retrieves equity curve and drawdown series for a specific run."""
    res = load_backtest_run(run_id)
    if res is None:
        raise HTTPException(status_code=404, detail=f"Backtest run '{run_id}' not found.")
    return res.equity_curve
