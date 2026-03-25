"""Fast stake/unstake (MevShield) APIs."""
from fastapi import APIRouter, Depends
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
    do_fast_stake_limit_all_sn28,
    do_fast_unstake,
    do_fast_stake_and_unstake,
)
from app.services.stake_service import SN28_NETUID

router = APIRouter(prefix="/api", tags=["fast"])


@router.post("/fast-stake")
def api_fast_stake(body: FastStakeBody, _: str = Depends(get_current_username)):
    """Fast stake via MevShield (Bittensor extrinsic)."""
    try:
        amount_rao = int(body.amount_tao * 10**9)
        success, message = do_fast_stake(body.netuid, amount_rao)
        if success:
            return {"ok": True, "message": message}
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/fast-stake-limit")
def api_fast_stake_limit(body: FastStakeLimitBody, _: str = Depends(get_current_username)):
    """Fast stake limit via MevShield. Limit price from tolerance."""
    try:
        amount_rao = int(body.amount_tao * 10**9)
        success, message, limit_price = do_fast_stake_limit(
            body.netuid, amount_rao,
            body.rate_tolerance, body.use_min_tolerance,
        )
        if success:
            return {"ok": True, "message": message, "limit_price_used": limit_price}
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/fast-stake-limit-all-sn28")
def api_fast_stake_limit_all_sn28(_: str = Depends(get_current_username)):
    """Fast stake-limit full spendable amount (same basis as EVM stake-all-SN28) to netuid 28, min tolerance."""
    try:
        success, message, limit_price, amount_rao, amount_tao = do_fast_stake_limit_all_sn28()
        if success:
            return {
                "ok": True,
                "message": message,
                "limit_price_used": limit_price,
                "amount_rao": amount_rao,
                "amount_tao": amount_tao,
                "netuid": SN28_NETUID,
            }
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/fast-unstake")
def api_fast_unstake(body: FastUnstakeBody, _: str = Depends(get_current_username)):
    """Fast unstake via MevShield (Bittensor extrinsic)."""
    try:
        success, message = do_fast_unstake(body.netuid)
        if success:
            return {"ok": True, "message": message}
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/fast-stake-and-unstake")
def api_fast_stake_and_unstake(body: FastStakeAndUnstakeBody, _: str = Depends(get_current_username)):
    """Fast stake via MevShield, then normal unstake via EVM."""
    try:
        amount_rao = int(body.amount_tao * 10**9)
        success, message = do_fast_stake_and_unstake(
            body.netuid, amount_rao, body.limit_price
        )
        if success:
            return {"ok": True, "message": message}
        return JSONResponse({"ok": False, "error": message}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
