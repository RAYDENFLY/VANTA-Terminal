"""
VANTA Terminal — Walk-Forward Benchmark Runner (Phase 4B)
=========================================================
Executes deterministic walk-forward benchmarking for candidate strategies
across the 10 ELIGIBLE perpetual pairs under frozen Phase 4A.1/4A.2 rules.
"""

import os
import json
import time
import math
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from backend.backtest.engine import DeterministicBacktestEngine
from backend.backtest.schemas import (
    BacktestConfig,
    BacktestResult,
    RunStatus,
    SizingType,
    ExecutionPolicy,
    ExitReason
)
from backend.strategy.configurations import (
    get_strategy_grid,
    StrategyAConfig,
    StrategyBConfig,
    StrategyCConfig
)
from backend.strategy.candidates import create_strategy_instance
from backend.strategy.qualification import (
    QUALIFIED_PAIRS,
    PARTIAL_HISTORY_PAIRS,
    evaluate_qualification_gates,
    UniverseEvaluationSummary
)
from backend.data.loader import (
    load_research_dataset,
    HOLDOUT_CUTOFF_MS,
    PURGE_DURATION_MS,
    EMBARGO_DURATION_MS,
    QuarantinedHoldoutViolationError
)
from backend.data.ingestion_engine import check_disk_space_guard


# Chronological Fold Boundaries in Unix Epoch Milliseconds
FOLDS_SCHEDULE = [
    {
        "fold_id": 1,
        "is_start_ms": 1698278400000,   # 2023-10-26T00:00:00Z
        "is_end_ms": 1729900800000,     # 2024-10-26T00:00:00Z
        "purge_cutoff_ms": 1729728000000, # 2024-10-24T00:00:00Z (48h prior)
        "embargo_start_ms": 1729900800000, # 2024-10-26T00:00:00Z
        "embargo_end_ms": 1730073600000,   # 2024-10-28T00:00:00Z (48h warmup)
        "oos_end_ms": 1745625600000,    # 2025-04-26T00:00:00Z
    },
    {
        "fold_id": 2,
        "is_start_ms": 1714089600000,   # 2024-04-26T00:00:00Z
        "is_end_ms": 1745625600000,     # 2025-04-26T00:00:00Z
        "purge_cutoff_ms": 1745452800000, # 2025-04-24T00:00:00Z (48h prior)
        "embargo_start_ms": 1745625600000, # 2025-04-26T00:00:00Z
        "embargo_end_ms": 1745798400000,   # 2025-04-28T00:00:00Z (48h warmup)
        "oos_end_ms": 1761436800000,    # 2025-10-26T00:00:00Z
    },
    {
        "fold_id": 3,
        "is_start_ms": 1729900800000,   # 2024-10-26T00:00:00Z
        "is_end_ms": 1761436800000,     # 2025-10-26T00:00:00Z
        "purge_cutoff_ms": 1761264000000, # 2025-10-24T00:00:00Z (48h prior)
        "embargo_start_ms": 1761436800000, # 2025-10-26T00:00:00Z
        "embargo_end_ms": 1761609600000,   # 2025-10-28T00:00:00Z (48h warmup)
        "oos_end_ms": 1777161600000,    # 2026-04-26T00:00:00Z (Quarantine boundary)
    }
]


class WalkForwardBenchmarkRunner:
    """
    Executes sequential single-worker walk-forward benchmarking
    across the 10 eligible pairs and 3 strategy candidates.
    """

    def __init__(self, data_root: Path = Path("D:/vanta-terminal/data")):
        self.data_root = data_root
        self.benchmark_dir = data_root / "benchmarks" / "phase_4b"
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)
        # Pre-flight check
        check_disk_space_guard(self.data_root)

    def get_dataset_path(self, symbol: str, timeframe: str) -> Path:
        """Resolves local Parquet path on HDD D:."""
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

    def load_universe_candles(self, timeframe: str) -> Dict[str, List[List[Any]]]:
        """
        Loads candles for the 10 eligible pairs with the holdout guard enforced.
        """
        universe_candles = {}
        for sym in QUALIFIED_PAIRS:
            path = self.get_dataset_path(sym, timeframe)
            candles, meta = load_research_dataset(path, enforce_holdout_guard=True)
            universe_candles[sym] = candles
        return universe_candles

    def run_strategy_benchmark(self, strategy_family: str) -> Dict[str, Any]:
        """
        Runs the full 3-fold Walk-Forward benchmark for a candidate strategy.
        1. Selects parameter set theta* on In-Sample across the 12 frozen configs.
        2. Evaluates theta* once on Out-Of-Sample.
        3. Aggregates OOS trades, runs stress cost model, and evaluates qualification gates.
        """
        # Determine timeframe and strategy type
        sid = strategy_family.upper()
        if "SWEEP" in sid or sid == "A":
            strat_code = "A"
            timeframe = "15m"
            strat_name = "Sweep-Reclaim"
        elif "BREAK" in sid or sid == "B":
            strat_code = "B"
            timeframe = "1H"
            strat_name = "Donchian Breakout / Trend"
        elif "MEAN" in sid or sid == "C":
            strat_code = "C"
            timeframe = "15m"
            strat_name = "Bollinger Bands + RSI Mean Reversion"
        else:
            raise ValueError(f"Unknown strategy family: {strategy_family}")

        print(f"\n=======================================================")
        print(f"BENCHMARKING CANDIDATE: Strategy {strat_code} ({strat_name})")
        print(f"Timeframe: {timeframe} | Pairs: 10 Qualified Pairs")
        print(f"=======================================================")

        # Step 1: Load candle data for the 10 eligible pairs
        print(f"Loading {len(QUALIFIED_PAIRS)} qualified datasets ({timeframe})...")
        universe_data = self.load_universe_candles(timeframe)
        grid = get_strategy_grid(strat_code)

        folds_results = []
        all_oos_trades = []
        pair_oos_trades: Dict[str, List[float]] = {s: [] for s in QUALIFIED_PAIRS}
        pair_oos_notionals: Dict[str, List[float]] = {s: [] for s in QUALIFIED_PAIRS}
        fold_net_pnls = []
        selection_audit_trail = []

        # Step 2: Iterate across the 3 Rolling Folds
        for fold in FOLDS_SCHEDULE:
            fid = fold["fold_id"]
            print(f"\n--- FOLD {fid} / 3 ---")
            print(f"In-Sample: {datetime.fromtimestamp(fold['is_start_ms']/1000, timezone.utc).date()} to {datetime.fromtimestamp(fold['is_end_ms']/1000, timezone.utc).date()}")
            print(f"Purge cutoff: {datetime.fromtimestamp(fold['purge_cutoff_ms']/1000, timezone.utc).isoformat()}")

            # A: In-Sample Grid Search over the 12 pre-registered configurations
            best_config = None
            best_score = -999.0
            config_evaluations = []

            for cfg in grid:
                is_trades = []
                is_pnls = []
                # Run across the 10 pairs on In-Sample
                for sym, candles in universe_data.items():
                    # Slice In-Sample candles (up to purge cutoff)
                    is_slice = [c for c in candles if fold["is_start_ms"] <= c[0] < fold["purge_cutoff_ms"]]
                    if not is_slice:
                        continue

                    bt_cfg = BacktestConfig(
                        symbol=sym,
                        timeframe=timeframe,
                        initial_equity=10000.0,
                        taker_fee_bps=5.0,
                        slippage_bps=2.0,
                        use_funding=False,
                        sizing_type=SizingType.PERCENT_EQUITY,
                        sizing_value=10.0,
                        max_leverage=1.0
                    )
                    engine = DeterministicBacktestEngine(bt_cfg)
                    strat_inst = create_strategy_instance(strat_code, cfg)
                    res = engine.run(is_slice, strat_inst, is_synthetic=False)
                    is_trades.extend(res.trade_ledger)
                    is_pnls.extend([t.net_pnl for t in res.trade_ledger])

                # Calculate IS performance metrics
                n_trades = len(is_trades)
                net_profit = sum(is_pnls)
                gross_wins = sum(p for p in is_pnls if p > 0)
                gross_losses = sum(abs(p) for p in is_pnls if p < 0)
                pf = (gross_wins / gross_losses) if gross_losses > 0 else (1.0 if gross_wins > 0 else 0.0)

                # Approximate annual Sharpe for ranking
                if n_trades >= 5:
                    mean_p = sum(is_pnls) / n_trades
                    var_p = sum((p - mean_p) ** 2 for p in is_pnls) / (n_trades - 1)
                    std_p = math.sqrt(var_p) if var_p > 0 else 1.0
                    sharpe = (mean_p / std_p) * math.sqrt(n_trades) if std_p > 0 else 0.0
                else:
                    sharpe = 0.0

                # MDD proxy
                cum = 0.0
                hwm = 0.0
                max_dd = 0.0
                for p in is_pnls:
                    cum += p
                    hwm = max(hwm, cum)
                    dd = (hwm - cum) / 10000.0 * 100.0
                    max_dd = max(max_dd, dd)

                # Objective Function: Sharpe * min(1.0, N / 50) subject to MDD <= 15%
                if max_dd <= 15.0:
                    score = sharpe * min(1.0, n_trades / 50.0)
                else:
                    score = -999.0

                eval_record = {
                    "config_id": cfg.config_id,
                    "trades": n_trades,
                    "net_profit": round(net_profit, 2),
                    "profit_factor": round(pf, 2),
                    "sharpe": round(sharpe, 2),
                    "max_drawdown_pct": round(max_dd, 2),
                    "score": round(score, 3)
                }
                config_evaluations.append(eval_record)

                if score > best_score:
                    best_score = score
                    best_config = cfg

            # Fallback if all configs breached 15% DD: select lowest drawdown
            if best_config is None:
                best_config = min(grid, key=lambda c: next(e["max_drawdown_pct"] for e in config_evaluations if e["config_id"] == c.config_id))

            print(f"Optimal IS Configuration Selected: {best_config.config_id} (Score: {best_score:.3f})")
            selection_audit_trail.append({
                "fold_id": fid,
                "selected_config": best_config.config_id,
                "selected_score": best_score,
                "grid_evaluations": config_evaluations
            })

            # B: Out-of-Sample Validation Run with the selected best_config
            # Embargo warmup: feed candles from fold["embargo_start_ms"] to fold["oos_end_ms"]
            # But trades are only executed after embargo_end_ms
            fold_oos_trades = []
            fold_pnl = 0.0

            for sym, candles in universe_data.items():
                oos_slice = [c for c in candles if fold["embargo_start_ms"] <= c[0] < fold["oos_end_ms"]]
                if not oos_slice:
                    continue

                bt_cfg = BacktestConfig(
                    symbol=sym,
                    timeframe=timeframe,
                    initial_equity=10000.0, # Fresh $10,000 cash reset
                    taker_fee_bps=5.0,
                    slippage_bps=2.0,
                    use_funding=False,
                    sizing_type=SizingType.PERCENT_EQUITY,
                    sizing_value=10.0,
                    max_leverage=1.0
                )
                engine = DeterministicBacktestEngine(bt_cfg)
                strat_inst = create_strategy_instance(strat_code, best_config)
                res = engine.run(oos_slice, strat_inst, is_synthetic=False)

                # Filter trades executed strictly after embargo_end_ms
                valid_trades = [t for t in res.trade_ledger if t.entry_time_ms >= fold["embargo_end_ms"]]
                fold_oos_trades.extend(valid_trades)
                for t in valid_trades:
                    pair_oos_trades[sym].append(t.net_pnl)
                    pair_oos_notionals[sym].append(t.notional)

            fold_pnl = sum(t.net_pnl for t in fold_oos_trades)
            fold_net_pnls.append(fold_pnl)
            all_oos_trades.extend(fold_oos_trades)

            print(f"OOS Fold {fid} Completed: {len(fold_oos_trades)} trades | Net PnL: ${fold_pnl:.2f}")
            folds_results.append({
                "fold_id": fid,
                "selected_config": best_config.config_id,
                "oos_trades_count": len(fold_oos_trades),
                "oos_net_pnl": round(fold_pnl, 2),
                "is_profitable": fold_pnl > 0
            })

        # Step 3: Combined Out-Of-Sample Evaluation
        total_trades = len(all_oos_trades)
        total_net_pnl = sum(t.net_pnl for t in all_oos_trades)
        total_fees = sum(t.total_fee for t in all_oos_trades)
        total_slippage = sum(t.slippage_cost for t in all_oos_trades)
        trade_notionals = [t.notional for t in all_oos_trades]
        trade_pnls = [t.net_pnl for t in all_oos_trades]

        # Calculate Overall OOS Drawdown
        cum_equity = 10000.0
        hwm = 10000.0
        max_dd_pct = 0.0
        for pnl in trade_pnls:
            cum_equity += pnl
            hwm = max(hwm, cum_equity)
            dd = (hwm - cum_equity) / hwm * 100.0
            max_dd_pct = max(max_dd_pct, dd)

        # Step 4: Friction Stress Test (7.5 bps taker fee + 3.0 bps slippage, REPLACING baseline)
        # Recost every trade under stress parameters
        stress_net_pnls = []
        for t in all_oos_trades:
            # Baseline entry notional ~ t.notional
            # Baseline fees were 5 bps entry + 5 bps exit = 10 bps total
            # Baseline slip was 2 bps entry + 2 bps exit = 4 bps total
            # Stress fee is 7.5 bps entry + 7.5 bps exit = 15 bps (1.5x fee)
            # Stress slip is 3.0 bps entry + 3.0 bps exit = 6 bps (1.5x slip)
            extra_fee = t.total_fee * 0.50
            extra_slip = t.slippage_cost * 0.50
            s_pnl = t.net_pnl - extra_fee - extra_slip
            stress_net_pnls.append(s_pnl)

        stress_net_pnl = sum(stress_net_pnls)
        s_wins = sum(p for p in stress_net_pnls if p > 0)
        s_losses = sum(abs(p) for p in stress_net_pnls if p < 0)
        stress_pf = (s_wins / s_losses) if s_losses > 0 else (1.0 if s_wins > 0 else 0.0)

        # Step 5: Evaluate Qualification Gates
        summary = evaluate_qualification_gates(
            strategy_id=f"STRAT-{strat_code}-01",
            max_drawdown_pct=max_dd_pct,
            trade_notionals=trade_notionals,
            net_pnls=trade_pnls,
            pair_trades=pair_oos_trades,
            fold_net_pnls=fold_net_pnls,
            stress_net_pnl=stress_net_pnl,
            stress_profit_factor=stress_pf
        )

        # Save Benchmark Output Artifact
        out_payload = {
            "strategy_id": f"STRAT-{strat_code}-01",
            "strategy_name": strat_name,
            "timeframe": timeframe,
            "cost_model": "TAKER_5BPS_SLIPPAGE_2BPS (FUNDING_EXCLUDED_BASELINE)",
            "benchmark_status": summary.status,
            "certified_baseline": summary.certified_baseline,
            "total_oos_trades": total_trades,
            "total_net_pnl": round(total_net_pnl, 2),
            "total_fees_paid": round(total_fees, 2),
            "total_slippage_paid": round(total_slippage, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "folds": folds_results,
            "selection_audit_trail": selection_audit_trail,
            "pair_performance": {
                sym: {
                    "trades": len(pair_oos_trades[sym]),
                    "net_pnl": round(sum(pair_oos_trades[sym]), 2),
                    "status": summary.pair_states[sym].value,
                    "passed": len(pair_oos_trades[sym]) >= 20 and sum(pair_oos_trades[sym]) > 0
                } for sym in QUALIFIED_PAIRS
            },
            "qualification_gates": [g.model_dump() for g in summary.gates],
            "fallback_notice": summary.fallback_notice
        }

        out_file = self.benchmark_dir / f"STRAT_{strat_code}_BENCHMARK.json"
        with open(out_file, "w") as f:
            json.dump(out_payload, f, indent=2)

        print(f"\nBenchmark Complete for Strategy {strat_code}:")
        print(f"Status: {summary.status} | Trades: {total_trades} | Net PnL: ${total_net_pnl:.2f} | Max DD: {max_dd_pct:.2f}%")
        print(f"Artifact written to {out_file}")

        return out_payload

    def run_all_candidates(self) -> Dict[str, Any]:
        """Runs benchmarks for all 3 candidates sequentially."""
        res_a = self.run_strategy_benchmark("A")
        res_b = self.run_strategy_benchmark("B")
        res_c = self.run_strategy_benchmark("C")

        # Compile master comparison
        all_results = {"A": res_a, "B": res_b, "C": res_c}
        master_file = self.benchmark_dir / "PHASE_4B_MASTER_SUMMARY.json"
        with open(master_file, "w") as f:
            json.dump(all_results, f, indent=2)

        return all_results
