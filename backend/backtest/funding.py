"""
VANTA Terminal — Historical Funding Rate Accounting & Settlement
=================================================================
Calculates 8-hour funding cashflows according to exchange settlement semantics.
Enforces strict blocker status when historical funding records are absent.
"""

from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from backend.backtest.schemas import PositionSide
from backend.backtest.events import FundingEvent


class FundingDataMissingException(Exception):
    """Raised when funding-dependent backtests are requested without validated funding datasets."""
    pass


class FundingAccountingModel:
    """
    Manages 8-hour perpetual funding payment debits and credits.
    Settlement occurs at 00:00, 08:00, and 16:00 UTC.
    
    Sign Convention:
    - Funding Rate > 0:
        Long pays (debit): -1.0 * notional * rate
        Short receives (credit): +1.0 * notional * rate
    - Funding Rate < 0:
        Long receives (credit): +1.0 * notional * abs(rate)
        Short pays (debit): -1.0 * notional * abs(rate)
    """

    def __init__(self, symbol: str, use_funding: bool = False):
        self.symbol = symbol
        self.use_funding = use_funding
        self.funding_records: Dict[int, float] = {}
        self.is_data_validated = False

    def load_historical_funding_data(self, funding_file: Path) -> None:
        """Loads validated historical funding records from local Parquet/JSON."""
        if not funding_file.exists():
            self.is_data_validated = False
            return

        # Funding records indexed by timestamp_ms -> funding_rate
        # In this phase, funding dataset ingestion is not yet complete.
        self.is_data_validated = False

    def verify_funding_prerequisite(self, start_time_ms: int, end_time_ms: int) -> Tuple[bool, str]:
        """
        Audits whether verified historical funding data exists for the requested run window.
        Returns (is_ready, status_label).
        """
        if not self.use_funding:
            return True, "FUNDING_DISABLED_UNVERIFIED_INPUTS"

        if not self.is_data_validated:
            return False, "BLOCKED_MISSING_FUNDING_DATA"

        return True, "FUNDING_DATA_VALIDATED"

    def process_funding_settlement(
        self,
        current_time_ms: int,
        position_side: PositionSide,
        position_notional: float
    ) -> Optional[FundingEvent]:
        """
        Calculates funding settlement if current candle timestamp aligns with 8h boundary.
        """
        if not self.use_funding or position_side == PositionSide.FLAT:
            return None

        # 8-hour settlement boundary: 00:00, 08:00, 16:00 UTC (modulo 28,800,000 ms)
        is_settlement_bar = (current_time_ms % 28800000 == 0)
        if not is_settlement_bar:
            return None

        if not self.is_data_validated:
            raise FundingDataMissingException(
                f"BLOCKED_MISSING_FUNDING_DATA: Historical funding rates for {self.symbol} "
                f"at {current_time_ms} are not validated on disk. Cannot simulate funding."
            )

        rate = self.funding_records.get(current_time_ms)
        if rate is None:
            raise FundingDataMissingException(
                f"BLOCKED_MISSING_FUNDING_DATA: Missing funding rate record at settlement {current_time_ms}."
            )

        # Calculate payment
        if position_side == PositionSide.LONG:
            # Long pays positive rate, receives negative rate
            payment = -1.0 * position_notional * rate
        else:
            # Short receives positive rate, pays negative rate
            payment = 1.0 * position_notional * rate

        return FundingEvent(
            timestamp_ms=current_time_ms,
            symbol=self.symbol,
            rate=rate,
            notional=position_notional,
            payment=round(payment, 6),
            position_side=position_side
        )
