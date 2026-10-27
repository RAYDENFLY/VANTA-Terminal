"""
VANTA Terminal — Phase 4B Benchmark Execution Driver
====================================================
Executes the candidate strategy benchmark across all 3 candidates
(Sweep-Reclaim, Donchian Breakout, Mean Reversion) over the 10 eligible pairs
using the frozen Walk-Forward protocol with 48h purge/embargo.
"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.strategy.walk_forward_runner import WalkForwardBenchmarkRunner
from backend.data.ingestion_engine import check_disk_space_guard


def main():
    print("=" * 65)
    print("VANTA TERMINAL — PHASE 4B STRATEGY BENCHMARK RUNNER")
    print(f"Timestamp UTC: {datetime.now(timezone.utc).isoformat()}")
    print("Mode: STRICT IN-SAMPLE SELECTION · ZERO OOS RETUNING · HOLDOUT QUARANTINE")
    print("=" * 65)

    check_disk_space_guard(Path("D:/vanta-terminal/data"))

    t0 = time.time()
    runner = WalkForwardBenchmarkRunner()
    results = runner.run_all_candidates()
    elapsed = time.time() - t0

    print("\n" + "=" * 65)
    print(f"PHASE 4B BENCHMARK COMPLETE IN {elapsed:.2f}s ({elapsed/60:.2f} min)")
    print("=" * 65)

    for code, res in results.items():
        print(f"\n[Strategy {code} — {res['strategy_name']}]")
        print(f"  Benchmark Status: {res['benchmark_status']}")
        print(f"  Certified Baseline: {res['certified_baseline']}")
        print(f"  OOS Trades: {res['total_oos_trades']} | Net PnL: ${res['total_net_pnl']:.2f} | Max DD: {res['max_drawdown_pct']:.2f}%")
        print(f"  Folds Profitability: {[f['is_profitable'] for f in res['folds']]}")
        print(f"  Spatial Robustness: {sum(1 for p in res['pair_performance'].values() if p['passed'])} / 10 pairs passed")

    return results


if __name__ == "__main__":
    main()
