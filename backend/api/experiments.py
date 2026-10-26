from fastapi import APIRouter, Query
from typing import Optional, List
from backend.schemas.experiments import ExperimentsListResponse, ExperimentRecord
from backend.fixtures.demo_data import get_demo_experiments
from backend.backtest.ledger import list_backtest_runs

router = APIRouter(prefix="/experiments", tags=["Experiment Registry"])

_DEMO_EXPERIMENTS = get_demo_experiments()

@router.get("", response_model=ExperimentsListResponse)
def list_experiments(status: Optional[str] = Query(None)):
    real_runs = list_backtest_runs()
    
    # Map backtest runs to ExperimentRecord
    experiment_records: List[ExperimentRecord] = []
    for r in real_runs:
        experiment_records.append(
            ExperimentRecord(
                run_id=r.run_id,
                config_hash=r.config_hash[:12] if r.config_hash else "N/A",
                dataset_version=r.dataset_id,
                strategy_family="Deterministic Synthetic Backtest" if r.is_synthetic_test else "Historical Backtest",
                model_architecture="Rule-Based Event Engine",
                status=r.status.value,
                created_at=r.created_at_utc,
                runtime_seconds=0.15,
                peak_memory_mb=12.5,
                sample_size_trades=r.total_trades,
                sharpe_ratio=r.sharpe_ratio,
                max_drawdown_pct=r.max_drawdown_pct,
                win_rate_pct=r.win_rate_pct,
                brier_score=None,
                is_demo_data=False,
                notes=f"Symbol: {r.symbol} {r.timeframe} · Return: {r.net_return_pct:.2f}% · Synthetic: {r.is_synthetic_test}"
            )
        )

    # Append demo fixtures only if no real runs exist yet
    combined = experiment_records if experiment_records else _DEMO_EXPERIMENTS

    if status:
        combined = [exp for exp in combined if exp.status.upper() == status.upper()]
    
    active_run = next((exp for exp in combined if exp.status in ["RUNNING", "QUEUED"]), None)
    
    return ExperimentsListResponse(
        total_count=len(combined),
        active_run=active_run,
        experiments=combined,
        is_demo_data=(len(experiment_records) == 0),
        storage_engine="Persistent HDD (D:/vanta-terminal/data/backtests)" if experiment_records else "In-Memory Registry (Demo)"
    )
