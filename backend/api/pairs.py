from fastapi import APIRouter, Query, HTTPException
from backend.schemas.pairs import PairsListResponse, PairCandlesResponse, PairMetadata
from backend.fixtures.demo_data import generate_synthetic_candles, TARGET_UNIVERSE
from backend.data.coverage_audit import load_verified_coverage_audit

router = APIRouter(prefix="/pairs", tags=["Pair Universe"])

@router.get("", response_model=PairsListResponse)
def list_pairs():
    audit_data = load_verified_coverage_audit()
    results_map = {r["exchange_symbol"]: r for r in audit_data.get("results", [])}
    
    pairs_list = []
    for req_sym, base, quote in TARGET_UNIVERSE:
        ex_sym = f"{base}{quote}"
        r = results_map.get(ex_sym)
        if r:
            cat = r.get("coverage_category", "UNVERIFIED")
            status = "VERIFIED_3Y" if "VERIFIED" in cat else "PARTIAL_HISTORY"
            depth = int(r.get("total_days", 0))
            earliest = r.get("earliest_date")
            is_demo = False
        else:
            status = "PENDING"
            depth = 0
            earliest = None
            is_demo = True

        pairs_list.append(
            PairMetadata(
                symbol=f"{ex_sym} (Req: {req_sym})",
                base_asset=base,
                quote_asset=quote,
                contract_type="PERPETUAL",
                timeframes=["15m", "1H", "4H"],
                coverage_status=status,
                model_status="NOT TESTED",
                last_candle_time=earliest,
                historical_depth_days=depth,
                missing_bars=0,
                is_demo_data=is_demo
            )
        )

    return PairsListResponse(
        universe_size=len(pairs_list),
        pairs=pairs_list,
        is_demo_data=False,
        audit_required=False
    )

@router.get("/{symbol}/candles", response_model=PairCandlesResponse)
def get_pair_candles(
    symbol: str,
    timeframe: str = Query("15m", pattern="^(15m|1H|4H)$"),
    count: int = Query(120, ge=20, le=500)
):
    valid_symbols = [s[0] for s in TARGET_UNIVERSE] + [f"{s[1]}{s[2]}" for s in TARGET_UNIVERSE]
    clean_sym = symbol.split(" ")[0]
    if clean_sym not in valid_symbols and symbol not in valid_symbols:
        raise HTTPException(status_code=404, detail=f"Pair '{symbol}' not found in research universe.")
    
    candles = generate_synthetic_candles(clean_sym, timeframe, count)
    return PairCandlesResponse(
        symbol=symbol,
        timeframe=timeframe,
        is_demo_data=True,
        notice="SYNTHETIC DEMO DATA FOR INTERFACE VISUALIZATION ONLY",
        candles=candles
    )
