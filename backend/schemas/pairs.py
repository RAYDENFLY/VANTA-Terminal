from pydantic import BaseModel
from typing import List, Optional

class Candle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float

class PairMetadata(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    contract_type: str = "PERPETUAL"
    timeframes: List[str] = ["15m", "1H", "4H"]
    coverage_status: str = "PENDING"
    model_status: str = "NOT TESTED"
    last_candle_time: Optional[str] = None
    historical_depth_days: int = 0
    missing_bars: int = 0
    is_demo_data: bool = True

class PairsListResponse(BaseModel):
    universe_size: int
    pairs: List[PairMetadata]
    is_demo_data: bool = True
    audit_required: bool = True

class PairCandlesResponse(BaseModel):
    symbol: str
    timeframe: str
    is_demo_data: bool = True
    notice: str = "SYNTHETIC DEMO DATA FOR INTERFACE VISUALIZATION ONLY"
    candles: List[Candle]
