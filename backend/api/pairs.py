from fastapi import APIRouter, Query, HTTPException
from backend.schemas.pairs import PairsListResponse, PairCandlesResponse
from backend.fixtures.demo_data import get_demo_pairs, generate_synthetic_candles, TARGET_UNIVERSE

router = APIRouter(prefix="/pairs", tags=["Pair Universe"])

@router.get("", response_model=PairsListResponse)
def list_pairs():
    pairs = get_demo_pairs()
    return PairsListResponse(
        universe_size=len(pairs),
        pairs=pairs,
        is_demo_data=True,
        audit_required=True
    )

@router.get("/{symbol}/candles", response_model=PairCandlesResponse)
def get_pair_candles(
    symbol: str,
    timeframe: str = Query("15m", pattern="^(15m|1H|4H)$"),
    count: int = Query(120, ge=20, le=500)
):
    valid_symbols = [s[0] for s in TARGET_UNIVERSE]
    if symbol not in valid_symbols:
        raise HTTPException(status_code=404, detail=f"Pair '{symbol}' not found in research universe.")
    
    candles = generate_synthetic_candles(symbol, timeframe, count)
    return PairCandlesResponse(
        symbol=symbol,
        timeframe=timeframe,
        is_demo_data=True,
        notice="SYNTHETIC DEMO DATA FOR INTERFACE VISUALIZATION ONLY",
        candles=candles
    )
