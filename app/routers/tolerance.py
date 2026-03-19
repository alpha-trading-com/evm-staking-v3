"""Tolerance calculation API."""
from fastapi import Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.schemas import CalcToleranceBody
from app.services.fast_stake_service import calc_min_tolerance_stake, calc_min_tolerance_unstake

router = APIRouter(prefix="/api", tags=["tolerance"])


@router.post("/calc-min-tolerance")
async def api_calc_min_tolerance(body: CalcToleranceBody, _: str = Depends(get_current_username)):
    """Calculate minimum tolerance for staking/unstaking. Returns limit_price and rate_tolerance."""
    try:
        if body.operation == "stake":
            limit_price, rate_tolerance = calc_min_tolerance_stake(body.tao_amount, body.netuid)
        else:
            limit_price, rate_tolerance = calc_min_tolerance_unstake(body.tao_amount, body.netuid)
        return {
            "ok": True,
            "limit_price": limit_price,
            "rate_tolerance": round(rate_tolerance, 6),
            "operation": body.operation,
        }
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
