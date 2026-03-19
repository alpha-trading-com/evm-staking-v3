"""Fast stake/unstake (MevShield) APIs."""
from fastapi import Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.schemas import (
    FastStakeBody,
    FastStakeLimitBody,
    FastUnstakeBody,
    FastStakeAndUnstakeBody,
)
from app.services.fast_stake_service import (
    do_fast_stake,
    do_fast_stake_limit,
    do_fast_unstake,
    do_fast_stake_and_unstake,
)

router = APIRouter(prefix="/api", tags=["fast"])


@router.post("/fast-stake")
async def api_fast_stake(body: FastStakeBody, _: str = Depends(get_current_username)):
    """Fast stake via MevShield (Bittensor extrinsic)."""
    try:
        amount_rao = int(body.amount_tao * 10**9)
        success, message = await do_fast_stake(body.netuid, amount_rao)
        if success:
            return {"ok": True, "message": message}
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/fast-stake-limit")
async def api_fast_stake_limit(body: FastStakeLimitBody, _: str = Depends(get_current_username)):
    """Fast stake limit via MevShield. Limit price from tolerance."""
    try:
        amount_rao = int(body.amount_tao * 10**9)
        success, message, limit_price = await do_fast_stake_limit(
            body.netuid, amount_rao,
            body.rate_tolerance, body.use_min_tolerance,
        )
        if success:
            return {"ok": True, "message": message, "limit_price_used": limit_price}
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/fast-unstake")
async def api_fast_unstake(body: FastUnstakeBody, _: str = Depends(get_current_username)):
    """Fast unstake via MevShield (Bittensor extrinsic)."""
    try:
        success, message = await do_fast_unstake(body.netuid)
        if success:
            return {"ok": True, "message": message}
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/fast-stake-and-unstake")
async def api_fast_stake_and_unstake(body: FastStakeAndUnstakeBody, _: str = Depends(get_current_username)):
    """Fast stake via MevShield, then normal unstake via EVM."""
    try:
        amount_rao = int(body.amount_tao * 10**9)
        success, message = await do_fast_stake_and_unstake(
            body.netuid, amount_rao, body.limit_price
        )
        if success:
            return {"ok": True, "message": message}
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
