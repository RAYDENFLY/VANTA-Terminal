"""
VANTA Terminal — Phase 5C.1 Controlled ML Evaluation Driver
===========================================================
Executes the controlled walk-forward training, simulation, and statistical evaluation
of the pre-registered supervised ML candidate arena against Benchmark-0.

Hard Constraints Enforced:
1. Universal Holdout Quarantine: strictly blocks rows at or after 2026-04-26T00:00:00Z.
2. In-Sample Fitting Only: scalers and models fit on IS; OOS evaluated zero-lookahead.
3. Canonical Portfolio Engine: shared $10,000 pool, 1.0x leverage cap, CONSERVATIVE_SL_FIRST.
4. Single-Threaded Execution: n_jobs=4 on CPU, deterministic seed 42, memory < 4 GB.
"""

from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import json
import time
import numpy as np
import pandas as pd

from backend.strategy.qualification import QUALIFIED_PAIRS
from backend.backtest.portfolio_engine import CanonicalPortfolioEngine, PortfolioEngineConfig
from backend.backtest.schemas import ExecutionPolicy
from backend.ml.walk_forward import FOLDS_SCHEDULE, WalkForwardFold
from backend.ml.dataset_builder import load_universe_1h_candles, build_fold_matrices
from backend.ml.models import MLModelWrapper
from backend.ml.ml_strategy import MLModelStrategy
from backend.ml.chained_equity import build_chained_equity_curve
from backend.ml.inference import run_paired_stationary_bootstrap
from backend.data.loader import HOLDOUT_CUTOFF_MS

OUTPUT_DIR = Path("D:/vanta-terminal/data/experiments/phase_5c")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK_PATH = Path("D:/vanta-terminal/data/benchmarks/phase_4b5/STRAT_B_BENCHMARK.json")


class Phase5CDriver:
    """
    Drives Phase 5C.1 walk-forward ML training and evaluation across the arena.
    """

    def __init__(self, candidates: Optional[List[str]] = None):
        self.candidates = candidates or ["MODEL-1-LOGIT", "MODEL-2-LGBM", "MODEL-3-XGB"]
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_benchmark_0(self) -> Dict[str, Any]:
        """Loads certified Phase 4B.5 Strategy B benchmark."""
        if not BENCHMARK_PATH.exists():
            raise FileNotFoundError(f"Benchmark-0 artifact missing at {BENCHMARK_PATH}")
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_benchmark_trades(self) -> List[Dict[str, Any]]:
        """
        Retrieves or replicates the exact 2,851 OOS trades of Benchmark-0 (Strategy B)
        from Phase 4B.5 for paired stationary bootstrap inference.
        """
        trades_cache = self.output_dir / "benchmark_0_trades.json"
        if trades_cache.exists():
            with open(trades_cache, "r", encoding="utf-8") as f:
                return json.load(f)

        from backend.strategy.configurations import get_strategy_grid
        from backend.strategy.candidates import create_strategy_instance
        from backend.strategy.walk_forward_runner import FOLDS_SCHEDULE as STRAT_FOLDS
        from backend.data.loader import load_research_dataset

        grid = {c.config_id: c for c in get_strategy_grid('B')}
        cfg_map = {1: grid['B-09'], 2: grid['B-09'], 3: grid['B-05']}
        all_bm_trades = []

        for fold in STRAT_FOLDS:
            fid = fold["fold_id"]
            cfg = cfg_map[fid]
            raw_ds = {}
            for sym in QUALIFIED_PAIRS:
                p = Path("data/derived") / sym / "1h.parquet"
                if not p.exists():
                    p = Path("data/raw") / sym / "1h.parquet"
                candles, _ = load_research_dataset(p, enforce_holdout_guard=True)
                raw_ds[sym] = [c for c in candles if fold["embargo_start_ms"] <= c[0] < fold["oos_end_ms"]]

            engine = CanonicalPortfolioEngine(PortfolioEngineConfig(
                initial_equity=10000.0,
                target_position_pct=10.0,
                max_leverage=1.0,
                max_simultaneous_positions=len(QUALIFIED_PAIRS),
                taker_fee_bps=5.0,
                slippage_bps=2.0,
                use_funding=False
            ))
            res = engine.run(raw_ds, lambda s: create_strategy_instance('B', cfg), run_id=f"REVAL_B_{fid}")
            v_trades = [t.model_dump() for t in res.trade_ledger if t.entry_time_ms >= fold["embargo_end_ms"]]
            all_bm_trades.extend(v_trades)

        with open(trades_cache, "w", encoding="utf-8") as f:
            json.dump(all_bm_trades, f, indent=2)

        return all_bm_trades

    def run_candidate_on_fold(
        self,
        candidate_id: str,
        fold: WalkForwardFold,
        fold_matrices: Dict[str, Any],
        is_stress: bool = False
    ) -> Dict[str, Any]:
        """
        Trains model on IS partition and executes OOS fold on CanonicalPortfolioEngine.
        """
        # 1. Fit ML Candidate on In-Sample Matrix
        X_train = fold_matrices["X_train_scaled"]
        y_train = fold_matrices["y_train"]

        t_train_0 = time.time()
        model_wrapper = MLModelWrapper(candidate_id)
        model_wrapper.fit(X_train, y_train)
        train_duration_s = time.time() - t_train_0

        # Evaluate diagnostic metrics on IS
        is_diagnostics = model_wrapper.evaluate_diagnostics(X_train, y_train)

        # 2. Generate point-in-time predictions and prepare OOS strategy lookups
        oos_data = fold_matrices["oos_eval_data"]
        predictions_map: Dict[str, Dict[int, int]] = {}
        atr_map: Dict[str, Dict[int, float]] = {}
        oos_candles_raw: Dict[str, List[List[Any]]] = {}

        total_oos_y_true = []
        total_oos_y_pred = []
        total_oos_X = []

        for sym, sdata in oos_data.items():
            X_eval = sdata["X_scaled"]
            y_eval = sdata["y_true"].values
            open_times = sdata["open_times"]
            atrs = sdata["atr14"]
            df_eval = sdata["df"]

            preds = model_wrapper.predict(X_eval)

            predictions_map[sym] = {int(ot): int(p) for ot, p in zip(open_times, preds)}
            atr_map[sym] = {int(ot): float(a) for ot, a in zip(open_times, atrs)}

            # Convert eval_df back to raw candle format for CanonicalPortfolioEngine
            raw_candles = []
            for _, row in df_eval.iterrows():
                raw_candles.append([
                    int(row["open_time"]),
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    float(row["volume"]),
                    int(row["close_time"])
                ])
            oos_candles_raw[sym] = raw_candles

            total_oos_X.append(X_eval)
            total_oos_y_true.append(y_eval)
            total_oos_y_pred.append(preds)

        # Evaluate diagnostic metrics on OOS
        X_oos_all = np.vstack(total_oos_X)
        y_oos_true_all = np.concatenate(total_oos_y_true)
        oos_diagnostics = model_wrapper.evaluate_diagnostics(X_oos_all, y_oos_true_all)

        # 3. Configure CanonicalPortfolioEngine
        taker_fee = 7.5 if is_stress else 5.0
        slippage = 3.0 if is_stress else 2.0

        engine_config = PortfolioEngineConfig(
            initial_equity=10000.0,
            max_leverage=1.0,
            max_simultaneous_positions=len(QUALIFIED_PAIRS),
            taker_fee_bps=taker_fee,
            slippage_bps=slippage,
            maker_fee_bps=2.0 if not is_stress else 3.0,
            target_position_pct=10.0,
            use_funding=False,
            intrabar_policy=ExecutionPolicy.CONSERVATIVE_SL_FIRST
        )
        engine = CanonicalPortfolioEngine(engine_config)

        # Strategy factory for CanonicalPortfolioEngine
        def strategy_factory(sym: str) -> MLModelStrategy:
            return MLModelStrategy(
                symbol=sym,
                predictions_by_time=predictions_map[sym],
                atr_by_time=atr_map[sym],
                friction_hurdle_bps=14.0
            )

        t_sim_0 = time.time()
        sim_result = engine.run(
            raw_datasets=oos_candles_raw,
            strategy_factory=strategy_factory,
            run_id=f"{candidate_id}_FOLD_{fold.fold_id}_{'STRESS' if is_stress else 'PRIMARY'}"
        )
        sim_duration_s = time.time() - t_sim_0

        trades_list = [t.model_dump() for t in sim_result.trade_ledger]
        eq_curve = [eq.equity for eq in sim_result.equity_curve]
        ts_list = [eq.timestamp_ms for eq in sim_result.equity_curve]
        tot_trades = sim_result.total_trades
        net_profit = sim_result.net_profit
        exp_bps = (net_profit / (tot_trades * 1000.0) * 10000.0) if tot_trades > 0 else 0.0

        return {
            "candidate_id": candidate_id,
            "fold_id": fold.fold_id,
            "is_stress": is_stress,
            "train_duration_s": round(train_duration_s, 2),
            "sim_duration_s": round(sim_duration_s, 2),
            "is_diagnostics": is_diagnostics,
            "oos_diagnostics": oos_diagnostics,
            "trades": trades_list,
            "equity_curve": eq_curve,
            "timestamps": ts_list,
            "net_pnl": net_profit,
            "gross_pnl": round(sum(t.gross_pnl for t in sim_result.trade_ledger), 2),
            "fees_paid": sim_result.total_fees_paid,
            "slippage_paid": sim_result.total_slippage_cost,
            "trades_count": tot_trades,
            "win_rate_pct": sim_result.win_rate_pct,
            "profit_factor": sim_result.profit_factor,
            "expectancy_bps": round(exp_bps, 2),
            "mdd_pct": sim_result.mtm_max_drawdown_pct,
            "rejected_orders": len(sim_result.rejected_orders)
        }

    def evaluate_gates(
        self,
        fold_results: List[Dict[str, Any]],
        chained_mdd_pct: float,
        stress_net_pnl: float,
        stress_pf: float,
        all_trades: List[Dict[str, Any]],
        pair_trades_map: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Evaluates the 8 frozen qualification gates.
        """
        # G1: Per-fold MTM MDD <= 15% AND chained OOS MTM MDD <= 15%
        per_fold_mdd_pass = all(f["mdd_pct"] <= 15.0 for f in fold_results)
        chained_mdd_pass = chained_mdd_pct <= 15.0
        g1_pass = per_fold_mdd_pass and chained_mdd_pass

        # Calculate aggregate metrics across OOS
        total_trades = len(all_trades)
        total_pnl = sum(t["net_pnl"] for t in all_trades)
        total_win_pnl = sum(t["net_pnl"] for t in all_trades if t["net_pnl"] > 0)
        total_loss_pnl = sum(abs(t["net_pnl"]) for t in all_trades if t["net_pnl"] < 0)

        # G2: Net expectancy >= +8.0 bps
        # Expectancy bps = (total_pnl / (total_trades * 1000 notional)) * 10,000
        net_expectancy_bps = (total_pnl / (total_trades * 1000.0) * 10000.0) if total_trades > 0 else 0.0
        g2_pass = net_expectancy_bps >= 8.0

        # G3: Profit Factor >= 1.25
        pf = (total_win_pnl / total_loss_pnl) if total_loss_pnl > 0 else (10.0 if total_win_pnl > 0 else 1.0)
        g3_pass = pf >= 1.25

        # G4: Total trades >= 150
        g4_pass = total_trades >= 150

        # G5: Trades per pair >= 20 for all 10 pairs
        per_pair_counts = {sym: len(pair_trades_map.get(sym, [])) for sym in QUALIFIED_PAIRS}
        g5_pass = all(count >= 20 for count in per_pair_counts.values())

        # G6: At least 2 of 3 folds profitable
        profitable_folds = sum(1 for f in fold_results if f["net_pnl"] > 0)
        g6_pass = profitable_folds >= 2

        # G7: At least 7 of 10 qualified pairs profitable
        per_pair_pnl = {sym: sum(t["net_pnl"] for t in pair_trades_map.get(sym, [])) for sym in QUALIFIED_PAIRS}
        profitable_pairs = sum(1 for pnl in per_pair_pnl.values() if pnl > 0)
        g7_pass = profitable_pairs >= 7

        # G8: Stress Net PnL > $0 and Stress PF > 1.0
        g8_pass = (stress_net_pnl > 0.0) and (stress_pf > 1.0)

        all_gates_pass = all([g1_pass, g2_pass, g3_pass, g4_pass, g5_pass, g6_pass, g7_pass, g8_pass])

        return {
            "all_gates_passed": all_gates_pass,
            "qualification_status": "QUALIFIED" if all_gates_pass else "UNQUALIFIED",
            "G1_mdd": {
                "passed": g1_pass,
                "per_fold_mdds": [f["mdd_pct"] for f in fold_results],
                "chained_mdd_pct": chained_mdd_pct,
                "hurdle": "<= 15.0%"
            },
            "G2_expectancy": {
                "passed": g2_pass,
                "observed_bps": round(net_expectancy_bps, 2),
                "hurdle": ">= +8.0 bps"
            },
            "G3_profit_factor": {
                "passed": g3_pass,
                "observed_pf": round(pf, 3),
                "hurdle": ">= 1.25"
            },
            "G4_trade_count": {
                "passed": g4_pass,
                "total_trades": total_trades,
                "hurdle": ">= 150 trades"
            },
            "G5_per_pair_activity": {
                "passed": g5_pass,
                "counts": per_pair_counts,
                "hurdle": ">= 20 trades per pair"
            },
            "G6_walk_forward_consistency": {
                "passed": g6_pass,
                "profitable_folds": profitable_folds,
                "hurdle": ">= 2 of 3 folds"
            },
            "G7_spatial_robustness": {
                "passed": g7_pass,
                "profitable_pairs": profitable_pairs,
                "hurdle": ">= 7 of 10 pairs"
            },
            "G8_stress_tolerance": {
                "passed": g8_pass,
                "stress_net_pnl": round(stress_net_pnl, 2),
                "stress_pf": round(stress_pf, 3),
                "hurdle": "Stress PnL > $0 & PF > 1.0"
            }
        }

    def execute_experiment(self) -> Dict[str, Any]:
        """
        Executes the complete Phase 5C.1 evaluation across all candidates and folds.
        """
        print("=== VANTA Terminal: Phase 5C.1 Evaluation Starting ===")
        t_global_0 = time.time()

        # Step 1: Load Universe Candles (10 Qualified Pairs)
        print("1. Loading raw 1H candle datasets for 10 qualified pairs...")
        universe_candles = load_universe_1h_candles(enforce_holdout_guard=True)

        # Step 2: Load Benchmark-0
        print("2. Loading certified Benchmark-0 (Strategy B reference)...")
        benchmark_0 = self.load_benchmark_0()

        # Step 3: Pre-build Fold Matrices (features, labels, scaler)
        print("3. Pre-building Walk-Forward fold datasets (IS & OOS)...")
        fold_matrices_by_fold: Dict[int, Dict[str, Any]] = {}
        for fold in FOLDS_SCHEDULE:
            print(f"   Building Fold {fold.fold_id} (IS: {fold.is_start_utc[:10]} -> OOS: {fold.oos_start_utc[:10]})...")
            fm = build_fold_matrices(fold, universe_candles, side="LONG")
            fold_matrices_by_fold[fold.fold_id] = fm
            print(f"   Fold {fold.fold_id}: {fm['train_samples_count']} train samples, {fm['total_oos_samples_count']} OOS samples.")

        arena_results: Dict[str, Any] = {}

        # Step 4: Evaluate Each ML Candidate
        for candidate_id in self.candidates:
            print(f"\n=======================================================")
            print(f"Running Candidate: {candidate_id}")
            print(f"=======================================================")

            fold_runs = []
            stress_fold_runs = []

            for fold in FOLDS_SCHEDULE:
                print(f"--- {candidate_id} | Fold {fold.fold_id} Primary Cost Run ---")
                fm = fold_matrices_by_fold[fold.fold_id]
                res = self.run_candidate_on_fold(candidate_id, fold, fm, is_stress=False)
                fold_runs.append(res)
                print(f"    Net PnL: ${res['net_pnl']:.2f} | Trades: {res['trades_count']} | MDD: {res['mdd_pct']:.2f}% | PF: {res['profit_factor']:.3f}")

                # Stress Cost Run
                stress_res = self.run_candidate_on_fold(candidate_id, fold, fm, is_stress=True)
                stress_fold_runs.append(stress_res)

            # Build Continuous Chained Equity Curve
            fold_curves = [f["equity_curve"] for f in fold_runs]
            fold_pnls = [f["net_pnl"] for f in fold_runs]
            chained_eq, dds, chained_mdd = build_chained_equity_curve(fold_curves, fold_pnls, initial_equity=10000.0)

            # Aggregate all primary trades
            all_candidate_trades = []
            pair_candidate_trades: Dict[str, List[Dict[str, Any]]] = {s: [] for s in QUALIFIED_PAIRS}
            for fr in fold_runs:
                for tr in fr["trades"]:
                    all_candidate_trades.append(tr)
                    sym = tr["symbol"]
                    if sym in pair_candidate_trades:
                        pair_candidate_trades[sym].append(tr)

            # Aggregate stress performance
            stress_pnl = sum(sf["net_pnl"] for sf in stress_fold_runs)
            stress_win = sum(sum(t["net_pnl"] for t in sf["trades"] if t["net_pnl"] > 0) for sf in stress_fold_runs)
            stress_loss = sum(sum(abs(t["net_pnl"]) for t in sf["trades"] if t["net_pnl"] < 0) for sf in stress_fold_runs)
            stress_pf = (stress_win / stress_loss) if stress_loss > 0 else 1.0

            # Evaluate Qualification Gates
            gate_eval = self.evaluate_gates(
                fold_results=fold_runs,
                chained_mdd_pct=chained_mdd,
                stress_net_pnl=stress_pnl,
                stress_pf=stress_pf,
                all_trades=all_candidate_trades,
                pair_trades_map=pair_candidate_trades
            )

            # Step 5: Run Paired Stationary Block Bootstrap vs Benchmark-0
            print(f"    Running 2,000 paired Stationary Block Bootstrap replicates vs Benchmark-0...")
            bm_trades = self.get_benchmark_trades()

            bootstrap_stats = run_paired_stationary_bootstrap(
                ml_trades=all_candidate_trades,
                benchmark_trades=bm_trades,
                start_ms=FOLDS_SCHEDULE[0].oos_start_ms,
                end_ms=FOLDS_SCHEDULE[-1].oos_end_ms,
                num_replicates=2000,
                expected_block_days=5,
                seed=42
            )

            total_candidate_net_pnl = sum(f["net_pnl"] for f in fold_runs)
            total_candidate_gross_pnl = sum(f["gross_pnl"] for f in fold_runs)
            total_candidate_fees = sum(f["fees_paid"] for f in fold_runs)
            total_candidate_slippage = sum(f["slippage_paid"] for f in fold_runs)

            candidate_summary = {
                "candidate_id": candidate_id,
                "qualification_status": gate_eval["qualification_status"],
                "all_gates_passed": gate_eval["all_gates_passed"],
                "total_oos_trades": len(all_candidate_trades),
                "total_net_pnl": round(total_candidate_net_pnl, 2),
                "total_gross_pnl": round(total_candidate_gross_pnl, 2),
                "total_fees_paid": round(total_candidate_fees, 2),
                "total_slippage_paid": round(total_candidate_slippage, 2),
                "profit_factor": gate_eval["G3_profit_factor"]["observed_pf"],
                "net_expectancy_bps": gate_eval["G2_expectancy"]["observed_bps"],
                "chained_mtm_mdd_pct": chained_mdd,
                "per_fold_mdds": gate_eval["G1_mdd"]["per_fold_mdds"],
                "stress_net_pnl": round(stress_pnl, 2),
                "stress_profit_factor": round(stress_pf, 3),
                "gate_evaluation": gate_eval,
                "bootstrap_inference": bootstrap_stats,
                "folds": fold_runs,
                "per_pair_pnl": {sym: round(sum(t["net_pnl"] for t in pair_candidate_trades[sym]), 2) for sym in QUALIFIED_PAIRS},
                "per_pair_trades": {sym: len(pair_candidate_trades[sym]) for sym in QUALIFIED_PAIRS}
            }

            arena_results[candidate_id] = candidate_summary

            # Save per-candidate artifact
            cand_path = self.output_dir / f"{candidate_id}_RESULTS.json"
            with open(cand_path, "w", encoding="utf-8") as f:
                json.dump(candidate_summary, f, indent=2)

        # Check Global Arena Outcome
        any_qualified = any(res["all_gates_passed"] for res in arena_results.values())
        global_outcome = "PHASE_5C1_QUALIFIED_CANDIDATE_FOUND" if any_qualified else "PHASE_5C1_NO_QUALIFIED_MODEL"

        experiment_manifest = {
            "experiment_id": "EXP-PHASE-5C1-ML-WALKFORWARD",
            "execution_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_execution_duration_s": round(time.time() - t_global_0, 2),
            "global_outcome": global_outcome,
            "qualified_models_count": sum(1 for res in arena_results.values() if res["all_gates_passed"]),
            "benchmark_0_status": "STRAT-B-01 (Donchian 1H) — UNQUALIFIED_BASELINE",
            "benchmark_0_summary": {
                "net_pnl": benchmark_0.get("total_net_pnl", 243.43),
                "profit_factor": benchmark_0.get("profit_factor", 1.007),
                "mtm_mdd_pct": benchmark_0.get("mtm_max_drawdown_pct", 20.67),
                "trades": benchmark_0.get("total_oos_trades", 2851)
            },
            "candidates": {
                cid: {
                    "qualification_status": arena_results[cid]["qualification_status"],
                    "all_gates_passed": arena_results[cid]["all_gates_passed"],
                    "net_pnl": arena_results[cid]["total_net_pnl"],
                    "profit_factor": arena_results[cid]["profit_factor"],
                    "expectancy_bps": arena_results[cid]["net_expectancy_bps"],
                    "chained_mtm_mdd_pct": arena_results[cid]["chained_mtm_mdd_pct"],
                    "total_trades": arena_results[cid]["total_oos_trades"],
                    "bootstrap_delta_pnl_ci": arena_results[cid]["bootstrap_inference"].get("delta_pnl", {}),
                    "bootstrap_statistically_significant": arena_results[cid]["bootstrap_inference"].get("statistically_significant", False)
                }
                for cid in self.candidates
            }
        }

        manifest_path = self.output_dir / "experiment_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(experiment_manifest, f, indent=2)

        print(f"\n=== Experiment Finished in {time.time() - t_global_0:.2f}s ===")
        print(f"Global Outcome: {global_outcome}")
        return experiment_manifest
