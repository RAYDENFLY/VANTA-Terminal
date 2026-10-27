"""
VANTA Terminal — Meta-Labeling Walk-Forward Evaluation Driver (Phase 5D.1)
==========================================================================
Orchestration interface for the 3-fold Walk-Forward evaluation of pre-registered
meta-models against the frozen STRAT-B-01 baseline on CanonicalPortfolioEngine.

Key Invariants:
1. Universal Holdout Quarantine: Date ranges or candidate timestamps >= 2026-04-26T00:00:00Z
   (1777161600000) trigger immediate QuarantinedHoldoutViolationError.
2. In-Sample Isolation: Preprocessing (scaling) and models fit strictly on In-Sample
   training partitions.
3. Candidate Stream Equivalence: Baseline and meta-models evaluate the exact same
   candidate trade opportunities; no selective dropping of pairs or bars.
4. Leakage-Proof Purge & Embargo: 48h purge + 48h embargo (96h total) strictly enforced;
   training candidates with outcome resolution after is_end_ms are purged.
5. Absolute Qualification Standards: All 8 frozen qualification gates remain mandatory;
   no candidate qualifies solely by outperforming an unqualified baseline.
6. Synchronized Stationary Block Bootstrap: Resamples calendar-time hourly blocks across
   all 10 pairs (B=2,000, E[L]=5 days, seed=42).
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from backend.data.loader import HOLDOUT_CUTOFF_MS, QuarantinedHoldoutViolationError
from backend.ml.walk_forward import FOLDS_SCHEDULE, WalkForwardFold
from backend.ml.features import REGISTERED_FEATURE_NAMES
from backend.ml.scaling import PartitionAwareScaler
from backend.ml.meta_models import BaseMetaModel, create_meta_model
from backend.ml.meta_strategy import MetaPolicyConfig, MetaPolicyVariant, FROZEN_META_POLICIES
from backend.ml.meta_dataset import CandidateTradeRecord
from backend.strategy.qualification import QUALIFIED_PAIRS, evaluate_qualification_gates


@dataclass(frozen=True)
class StationaryBlockBootstrapConfig:
    replicates: int = 2000
    expected_block_length_bars: int = 120  # 5 days (120 1H bars)
    seed: int = 42


@dataclass
class PairedTradeComparison:
    candidate_id: str
    symbol: str
    signal_timestamp: int
    direction: str
    baseline_executed: bool
    baseline_net_pnl: float
    baseline_notional: float
    meta_executed: bool
    meta_net_pnl: float
    meta_notional: float
    incremental_net_pnl: float
    incremental_return: float


class MetaEvaluationDriver:
    """
    Orchestrates the controlled walk-forward evaluation and paired statistical
    inference between Benchmark-0 and meta-model candidates.
    """

    def __init__(
        self,
        bootstrap_config: Optional[StationaryBlockBootstrapConfig] = None
    ):
        self.bootstrap_config = bootstrap_config or StationaryBlockBootstrapConfig()
        self.folds: List[WalkForwardFold] = FOLDS_SCHEDULE

    def validate_date_range(self, start_ms: int, end_ms: int) -> None:
        """Fails closed if requested interval intersects the quarantined holdout."""
        if start_ms >= HOLDOUT_CUTOFF_MS or end_ms > HOLDOUT_CUTOFF_MS:
            raise QuarantinedHoldoutViolationError(
                f"Evaluation range [{start_ms}, {end_ms}) intersects the quarantined "
                f"final holdout cutoff {HOLDOUT_CUTOFF_MS} (2026-04-26T00:00:00Z)."
            )
        if start_ms >= end_ms:
            raise ValueError(f"Invalid interval: start_ms {start_ms} >= end_ms {end_ms}.")

    def validate_candidate_stream_equivalence(
        self,
        baseline_candidates: List[CandidateTradeRecord],
        meta_candidates: List[CandidateTradeRecord]
    ) -> None:
        """
        Verifies that baseline and meta-models evaluate an identical candidate stream.
        """
        if len(baseline_candidates) != len(meta_candidates):
            raise ValueError(
                f"Candidate stream count mismatch: baseline has {len(baseline_candidates)}, "
                f"meta has {len(meta_candidates)}."
            )

        for b_cand, m_cand in zip(baseline_candidates, meta_candidates):
            if b_cand.candidate_id != m_cand.candidate_id:
                raise ValueError(
                    f"Candidate ID mismatch in sequence: {b_cand.candidate_id} vs {m_cand.candidate_id}"
                )
            if b_cand.symbol != m_cand.symbol or b_cand.signal_timestamp != m_cand.signal_timestamp:
                raise ValueError(
                    f"Candidate attribute mismatch for {b_cand.candidate_id}."
                )

    def validate_partition_isolation(
        self,
        fold: WalkForwardFold,
        training_candidates: List[CandidateTradeRecord],
        evaluation_candidates: List[CandidateTradeRecord]
    ) -> None:
        """
        Validates temporal partition isolation and purge/embargo compliance.
        """
        self.validate_date_range(fold.is_start_ms, fold.oos_end_ms)

        train_ids = set()
        for c in training_candidates:
            if not (fold.is_start_ms <= c.signal_timestamp < fold.is_end_ms):
                raise ValueError(
                    f"Training candidate {c.candidate_id} timestamp {c.signal_timestamp} outside IS range."
                )
            if c.label_resolution_timestamp is not None and c.label_resolution_timestamp > fold.is_end_ms:
                raise ValueError(
                    f"Leakage violation: Training candidate {c.candidate_id} label resolution "
                    f"{c.label_resolution_timestamp} extends into purge period (> {fold.is_end_ms})."
                )
            train_ids.add(c.candidate_id)

        for c in evaluation_candidates:
            if not (fold.oos_start_ms <= c.signal_timestamp < fold.oos_end_ms):
                raise ValueError(
                    f"Evaluation candidate {c.candidate_id} timestamp {c.signal_timestamp} outside OOS range."
                )
            if c.candidate_id in train_ids:
                raise ValueError(
                    f"Partition overlap violation: Candidate {c.candidate_id} appears in both IS and OOS."
                )

    def compute_paired_comparison(
        self,
        candidate_records: List[CandidateTradeRecord],
        baseline_trade_map: Dict[str, Any],
        meta_trade_map: Dict[str, Any]
    ) -> List[PairedTradeComparison]:
        """
        Constructs paired trade records between baseline execution and meta-model execution.
        """
        comparisons: List[PairedTradeComparison] = []

        for c in candidate_records:
            cid = c.candidate_id
            b_trade = baseline_trade_map.get(cid)
            m_trade = meta_trade_map.get(cid)

            b_exec = b_trade is not None
            b_pnl = float(b_trade["net_pnl"]) if b_exec else 0.0
            b_notional = float(b_trade["notional"]) if b_exec else 0.0
            b_ret = (b_pnl / b_notional) if (b_exec and b_notional > 0) else 0.0

            m_exec = m_trade is not None
            m_pnl = float(m_trade["net_pnl"]) if m_exec else 0.0
            m_notional = float(m_trade["notional"]) if m_exec else 0.0
            m_ret = (m_pnl / m_notional) if (m_exec and m_notional > 0) else 0.0

            inc_pnl = m_pnl - b_pnl
            inc_ret = m_ret - b_ret

            comparisons.append(PairedTradeComparison(
                candidate_id=cid,
                symbol=c.symbol,
                signal_timestamp=c.signal_timestamp,
                direction=c.direction,
                baseline_executed=b_exec,
                baseline_net_pnl=round(b_pnl, 4),
                baseline_notional=round(b_notional, 2),
                meta_executed=m_exec,
                meta_net_pnl=round(m_pnl, 4),
                meta_notional=round(m_notional, 2),
                incremental_net_pnl=round(inc_pnl, 4),
                incremental_return=round(inc_ret, 6)
            ))

        return comparisons

    def get_evaluation_specification(self) -> Dict[str, Any]:
        """Returns reproducible metadata for the evaluation environment."""
        return {
            "driver_name": "MetaEvaluationDriver",
            "folds_count": len(self.folds),
            "holdout_cutoff_ms": HOLDOUT_CUTOFF_MS,
            "holdout_cutoff_utc": "2026-04-26T00:00:00Z",
            "qualified_universe": QUALIFIED_PAIRS,
            "predeclared_policies": [p.value for p in MetaPolicyVariant],
            "bootstrap_config": {
                "replicates": self.bootstrap_config.replicates,
                "expected_block_length_bars": self.bootstrap_config.expected_block_length_bars,
                "seed": self.bootstrap_config.seed
            },
            "qualification_gates_count": 8,
            "revalidation_engine": "CanonicalPortfolioEngine"
        }
