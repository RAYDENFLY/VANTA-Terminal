import math
import time
from typing import List, Dict, Any
from backend.schemas.pairs import PairMetadata, Candle
from backend.schemas.experiments import ExperimentRecord
from backend.schemas.strategies import StrategyCandidate, CostAssumptions
from backend.schemas.models import ModelConfigResult
from backend.schemas.data import PairCoverageSummary, TimeframeCoverage

TARGET_UNIVERSE = [
    ("BTCUSDT.P", "BTC", "USDT"),
    ("ETHUSDT.P", "ETH", "USDT"),
    ("SOLUSDT.P", "SOL", "USDT"),
    ("BNBUSDT.P", "BNB", "USDT"),
    ("XRPUSDT.P", "XRP", "USDT"),
    ("ADAUSDT.P", "ADA", "USDT"),
    ("AVAXUSDT.P", "AVAX", "USDT"),
    ("LINKUSDT.P", "LINK", "USDT"),
    ("DOGEUSDT.P", "DOGE", "USDT"),
    ("LTCUSDT.P", "LTC", "USDT"),
    ("XMRUSDT.P", "XMR", "USDT"),
]

def get_demo_pairs() -> List[PairMetadata]:
    pairs = []
    for sym, base, quote in TARGET_UNIVERSE:
        pairs.append(
            PairMetadata(
                symbol=sym,
                base_asset=base,
                quote_asset=quote,
                contract_type="PERPETUAL",
                timeframes=["15m", "1H", "4H"],
                coverage_status="PENDING",
                model_status="NOT TESTED",
                last_candle_time=None,
                historical_depth_days=0,
                missing_bars=0,
                is_demo_data=True,
            )
        )
    return pairs

def generate_synthetic_candles(symbol: str, timeframe: str = "15m", count: int = 120) -> List[Candle]:
    """
    Generates deterministic synthetic demo candles for UI chart visualization.
    Clearly marked as synthetic demo data.
    """
    base_price_map = {
        "BTCUSDT.P": 67450.0,
        "ETHUSDT.P": 3480.0,
        "SOLUSDT.P": 178.5,
        "BNBUSDT.P": 595.0,
        "XRPUSDT.P": 0.542,
        "ADAUSDT.P": 0.358,
        "AVAXUSDT.P": 28.4,
        "LINKUSDT.P": 12.1,
        "DOGEUSDT.P": 0.142,
        "LTCUSDT.P": 72.8,
        "XMRUSDT.P": 158.0,
    }
    base_price = base_price_map.get(symbol, 100.0)
    
    # 15m = 900s, 1H = 3600s, 4H = 14400s
    tf_seconds = 900 if timeframe == "15m" else (3600 if timeframe == "1H" else 14400)
    end_time = int(time.time() // tf_seconds * tf_seconds)
    start_time = end_time - (count * tf_seconds)
    
    candles = []
    current_close = base_price
    
    # Deterministic pseudo-random seed based on symbol characters
    seed_offset = sum(ord(c) for c in symbol)
    
    for i in range(count):
        bar_time = start_time + (i * tf_seconds)
        # Periodic oscillating price wave + deterministic noise
        wave = math.sin((i + seed_offset) * 0.15) * (base_price * 0.012)
        noise = math.cos((i * 1.3) + seed_offset) * (base_price * 0.006)
        
        o = current_close
        c = round(base_price + wave + noise, 4 if base_price < 10 else 2)
        spread = abs(c - o)
        h = round(max(o, c) + (spread * 0.4) + (base_price * 0.003), 4 if base_price < 10 else 2)
        l = round(min(o, c) - (spread * 0.4) - (base_price * 0.003), 4 if base_price < 10 else 2)
        vol = round(1500.0 + abs(math.sin(i * 0.5)) * 4500.0, 2)
        
        candles.append(
            Candle(
                time=bar_time,
                open=o,
                high=h,
                low=l,
                close=c,
                volume=vol
            )
        )
        current_close = c
        
    return candles

def get_demo_experiments() -> List[ExperimentRecord]:
    return [
        ExperimentRecord(
            run_id="EXP-20261027-001",
            config_hash="7f8b91a2",
            dataset_version="DEMO_FIXTURE_V0",
            strategy_family="Sweep-Reclaim",
            model_architecture="Rule-Based (Pre-ML)",
            status="COMPLETED",
            created_at="2026-10-27 04:15:00 UTC",
            runtime_seconds=12.4,
            peak_memory_mb=184.2,
            sample_size_trades=142,
            sharpe_ratio=1.42,
            max_drawdown_pct=11.6,
            win_rate_pct=54.2,
            brier_score=None,
            is_demo_data=True,
            notes="Baseline validation run using demo fixture data"
        ),
        ExperimentRecord(
            run_id="EXP-20261027-002",
            config_hash="4c3a10d8",
            dataset_version="DEMO_FIXTURE_V0",
            strategy_family="Breakout/Trend",
            model_architecture="Rule-Based (Pre-ML)",
            status="COMPLETED",
            created_at="2026-10-27 04:30:00 UTC",
            runtime_seconds=10.8,
            peak_memory_mb=176.5,
            sample_size_trades=98,
            sharpe_ratio=0.88,
            max_drawdown_pct=18.4,
            win_rate_pct=42.9,
            brier_score=None,
            is_demo_data=True,
            notes="Breakout test across demo series"
        ),
        ExperimentRecord(
            run_id="EXP-20261027-003",
            config_hash="9e21df65",
            dataset_version="DEMO_FIXTURE_V0",
            strategy_family="Mean Reversion",
            model_architecture="Rule-Based (Pre-ML)",
            status="COMPLETED",
            created_at="2026-10-27 04:45:00 UTC",
            runtime_seconds=9.3,
            peak_memory_mb=171.0,
            sample_size_trades=184,
            sharpe_ratio=1.12,
            max_drawdown_pct=14.1,
            win_rate_pct=58.7,
            brier_score=None,
            is_demo_data=True,
            notes="Mean reversion test across demo series"
        ),
        ExperimentRecord(
            run_id="EXP-20261027-004",
            config_hash="pending_h",
            dataset_version="DEMO_FIXTURE_V0",
            strategy_family="Sweep-Reclaim",
            model_architecture="Global LightGBM (Config A)",
            status="QUEUED",
            created_at="2026-10-27 05:00:00 UTC",
            runtime_seconds=None,
            peak_memory_mb=None,
            sample_size_trades=None,
            sharpe_ratio=None,
            max_drawdown_pct=None,
            win_rate_pct=None,
            brier_score=None,
            is_demo_data=True,
            notes="Queued pending Phase 4/5 implementation"
        ),
    ]

def get_demo_strategies() -> List[StrategyCandidate]:
    return [
        StrategyCandidate(
            id="STRAT-SWEEP-01",
            name="Sweep-Reclaim Baseline",
            family="Sweep-Reclaim",
            description="Identifies liquidity sweep outside 30-bar swing extremes and reclaims range with ATR stop",
            status="CANDIDATE",
            entry_logic="Close inside previous swing high/low following liquidity puncture",
            stop_loss_logic="1.0x ATR beyond extreme sweep wick",
            take_profit_logic="Opposing swing boundary or 2.0x Risk",
            trades_count=142,
            win_rate_pct=54.2,
            profit_factor=1.62,
            sharpe_ratio=1.42,
            max_drawdown_pct=11.6,
            expectancy_r=0.48,
            avg_holding_bars=8.4,
            is_demo_data=True
        ),
        StrategyCandidate(
            id="STRAT-BREAK-01",
            name="Volatility Contraction Breakout",
            family="Breakout/Trend",
            description="Enters on momentum channel breakout following volatility squeeze with RVOL >= 1.5",
            status="CANDIDATE",
            entry_logic="Close > Upper Donchian Channel(20) with Volume > 1.5x MA(20)",
            stop_loss_logic="Trailing EMA(21) or 1.5x ATR",
            take_profit_logic="Triple-barrier expiry or trend reversal",
            trades_count=98,
            win_rate_pct=42.9,
            profit_factor=1.28,
            sharpe_ratio=0.88,
            max_drawdown_pct=18.4,
            expectancy_r=0.22,
            avg_holding_bars=19.2,
            is_demo_data=True
        ),
        StrategyCandidate(
            id="STRAT-MEAN-01",
            name="Statistical Mean Reversion",
            family="Mean Reversion",
            description="Fades price deviations >= 2.5 standard deviations from 50-period rolling mean",
            status="CANDIDATE",
            entry_logic="|Z-Score| >= 2.5 on candle close + RSI extreme",
            stop_loss_logic="1.2x ATR from entry",
            take_profit_logic="Return to rolling VWAP / mean",
            trades_count=184,
            win_rate_pct=58.7,
            profit_factor=1.45,
            sharpe_ratio=1.12,
            max_drawdown_pct=14.1,
            expectancy_r=0.31,
            avg_holding_bars=5.6,
            is_demo_data=True
        ),
    ]

def get_demo_models() -> List[ModelConfigResult]:
    return [
        ModelConfigResult(
            config_id="CONFIG-A-GLOBAL",
            name="Global Pooled LightGBM",
            architecture="LightGBM GBDT (Categorical Pair Encoding)",
            description="Single pooled model trained over all 11 pairs with pair feature tokens",
            training_scope="All 11 eligible pairs pooled",
            features_count=24,
            val_brier_score=0.184,
            val_roc_auc=0.648,
            val_sharpe=1.65,
            val_max_drawdown_pct=9.8,
            val_win_rate_pct=57.4,
            sample_size_trades=1150,
            bootstrap_sharpe_ci95=[1.31, 1.98],
            status="CANDIDATE",
            is_demo_data=True
        ),
        ModelConfigResult(
            config_id="CONFIG-B-SPECIALISTS",
            name="Pair Specialist Models",
            architecture="11 Independent Pair-Specific LightGBM Models",
            description="One specialist model per cryptocurrency with zero cross-pair training data",
            training_scope="Single native instrument per model",
            features_count=24,
            val_brier_score=0.201,
            val_roc_auc=0.612,
            val_sharpe=1.38,
            val_max_drawdown_pct=13.4,
            val_win_rate_pct=53.1,
            sample_size_trades=1150,
            bootstrap_sharpe_ci95=[0.98, 1.72],
            status="CANDIDATE",
            is_demo_data=True
        ),
        ModelConfigResult(
            config_id="CONFIG-C-CALIBRATED",
            name="Global Model + Pair Calibration",
            architecture="Shared Global LightGBM + Pair-Specific Isotonic Calibration",
            description="Global representation base with validation-fitted per-pair probability thresholds",
            training_scope="Global features with localized validation calibration",
            features_count=24,
            val_brier_score=0.171,
            val_roc_auc=0.655,
            val_sharpe=1.78,
            val_max_drawdown_pct=8.4,
            val_win_rate_pct=59.2,
            sample_size_trades=1150,
            bootstrap_sharpe_ci95=[1.45, 2.12],
            status="CANDIDATE",
            is_demo_data=True
        ),
    ]

def get_demo_coverage() -> List[PairCoverageSummary]:
    summaries = []
    for sym, base, quote in TARGET_UNIVERSE:
        summaries.append(
            PairCoverageSummary(
                symbol=sym,
                target_history_years=3.0,
                verified_history_years=0.0,
                audit_status="PENDING_PHASE_2",
                timeframes={
                    "15m": TimeframeCoverage(
                        timeframe="15m",
                        available_bars=0,
                        earliest_candle=None,
                        latest_candle=None,
                        gap_count=0,
                        coverage_pct=0.0,
                        status="PENDING_AUDIT"
                    ),
                    "1H": TimeframeCoverage(
                        timeframe="1H",
                        available_bars=0,
                        earliest_candle=None,
                        latest_candle=None,
                        gap_count=0,
                        coverage_pct=0.0,
                        status="PENDING_AUDIT"
                    ),
                    "4H": TimeframeCoverage(
                        timeframe="4H",
                        available_bars=0,
                        earliest_candle=None,
                        latest_candle=None,
                        gap_count=0,
                        coverage_pct=0.0,
                        status="PENDING_AUDIT"
                    )
                },
                raw_storage_mb=0.0,
                manifest_checksum=None,
                is_demo_data=True
            )
        )
    return summaries
