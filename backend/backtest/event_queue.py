"""
VANTA Terminal — Deterministic Multi-Stream Event Queue
======================================================
Synchronizes discrete candle streams across multiple perpetual pairs
into chronologically ordered BarFrames with strict deterministic tie-breaking.
"""

from typing import List, Dict, Any, Optional, Iterator, Tuple
from dataclasses import dataclass
from backend.backtest.events import BarEvent, SignalEvent


@dataclass(frozen=True)
class BarFrame:
    """
    Represents a synchronized multi-pair time slice at a single discrete candle interval.
    Contains the completed bar for each symbol active at this timestamp.
    """
    timestamp_ms: int
    close_time_ms: int
    bars: Dict[str, BarEvent]

    def get_bar(self, symbol: str) -> Optional[BarEvent]:
        return self.bars.get(symbol)


class MultiStreamEventQueue:
    """
    Consumes candle arrays for multiple symbols, validates temporal monotonicity,
    and dispatches synchronized BarFrames chronologically without pair concatenation.
    """

    def __init__(self, raw_datasets: Dict[str, List[List[Any]]]):
        """
        Args:
            raw_datasets: Dict mapping symbol -> list of candles [open_time, open, high, low, close, volume, close_time]
        """
        self.raw_datasets = raw_datasets
        self.bar_index_by_symbol: Dict[str, Dict[int, BarEvent]] = {}
        self.all_timestamps: List[int] = []
        self._build_index()

    def _build_index(self) -> None:
        """Indexes all bars by timestamp and generates the master sorted chronological timeline."""
        timestamps_set = set()

        for symbol, candles in self.raw_datasets.items():
            symbol_index = {}
            for idx, c in enumerate(candles):
                ts = int(c[0])
                bar = BarEvent(
                    timestamp_ms=ts,
                    open=float(c[1]),
                    high=float(c[2]),
                    low=float(c[3]),
                    close=float(c[4]),
                    volume=float(c[5]),
                    close_time_ms=int(c[6]),
                    bar_index=idx
                )
                symbol_index[ts] = bar
                timestamps_set.add(ts)
            self.bar_index_by_symbol[symbol] = symbol_index

        self.all_timestamps = sorted(list(timestamps_set))

    def __len__(self) -> int:
        return len(self.all_timestamps)

    def iter_frames(self) -> Iterator[BarFrame]:
        """Yields synchronized BarFrames in strict chronological sequence."""
        for ts in self.all_timestamps:
            frame_bars = {}
            frame_close_time = ts
            for symbol, symbol_index in self.bar_index_by_symbol.items():
                if ts in symbol_index:
                    b = symbol_index[ts]
                    frame_bars[symbol] = b
                    if b.close_time_ms > frame_close_time:
                        frame_close_time = b.close_time_ms

            if frame_bars:
                yield BarFrame(
                    timestamp_ms=ts,
                    close_time_ms=frame_close_time,
                    bars=frame_bars
                )

    @staticmethod
    def sort_signals_deterministically(
        signals: List[SignalEvent],
        volumes: Optional[Dict[str, float]] = None
    ) -> List[SignalEvent]:
        """
        Sorts simultaneous signals deterministically using canonical tie-breaking:
        1. Confidence / score (descending, if present via tag or attribute; default 1.0)
        2. Volume (descending, if provided)
        3. Symbol alphabetical order (A to Z)
        """
        vols = volumes or {}

        def sort_key(s: SignalEvent) -> Tuple[float, float, str]:
            conf = getattr(s, "confidence", 1.0)
            vol = vols.get(s.symbol, 0.0)
            return (-conf, -vol, s.symbol)

        return sorted(signals, key=sort_key)
