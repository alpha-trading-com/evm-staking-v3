"""Stake, stake-limit, remove-stake, remove-stake-limit, transfer-stake, move-stake, withdraw APIs."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.schemas import (
    StakeBody,
    StakeLimitBody,
    RemoveStakeBody,
    RemoveStakeLimitBody,
    TransferStakeBody,
    MoveStakeBody,
    WithdrawBody,
)
from app.services.stake_service import (
    do_stake,
    do_stake_limit,
    do_stake_limit_all_sn28,
    do_remove_stake,
    do_remove_stake_limit,
    do_transfer_stake,
    do_move_stake,
    do_withdraw,
    resolve_remove_stake_amount,
    resolve_remove_stake_limit_amounts,
    resolve_move_stake_amount,
)

router = APIRouter(prefix="/api", tags=["stake"])


@router.post("/stake")
async def api_stake(body: StakeBody, _: str = Depends(get_current_username)):
    try:
        amount_rao = int(body.amount_tao * 10**9)
        return do_stake(body.hotkey, body.netuid, amount_rao)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/stake-limit")
async def api_stake_limit(body: StakeLimitBody, _: str = Depends(get_current_username)):
    try:
        amount_rao = int(body.amount_tao * 10**9)
        return do_stake_limit(
            body.hotkey, body.netuid, amount_rao,
            body.rate_tolerance, body.use_min_tolerance, body.allow_partial,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/stake-limit-all-sn28")
async def api_stake_limit_all_sn28(_: str = Depends(get_current_username)):
    """Stake-limit 100% of spendable contract balance to SN28; DEFAULT_HOTKEY; min tolerance; allow_partial always false."""
    try:
        return do_stake_limit_all_sn28()
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/remove-stake")
async def api_remove_stake(body: RemoveStakeBody, _: str = Depends(get_current_username)):
    try:
        amount_alpha_rao = resolve_remove_stake_amount(body.hotkey, body.netuid, body.amount)
        return do_remove_stake(body.hotkey, body.netuid, amount_alpha_rao)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/remove-stake-limit")
async def api_remove_stake_limit(body: RemoveStakeLimitBody, _: str = Depends(get_current_username)):
    try:
        amount_alpha_rao, amount_tao = resolve_remove_stake_limit_amounts(body.hotkey, body.netuid, body.amount)
        return do_remove_stake_limit(
            body.hotkey, body.netuid, amount_alpha_rao,
            body.rate_tolerance, body.use_min_tolerance, body.allow_partial,
            amount_tao,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/transfer-stake")
async def api_transfer_stake(body: TransferStakeBody, _: str = Depends(get_current_username)):
    try:
        amount_rao = resolve_move_stake_amount(
            body.hotkey, body.origin_netuid, body.amount_tao
        )
        if amount_rao <= 0:
            raise ValueError(
                "No stake to transfer on the origin subnet for this hotkey (or invalid amount)."
            )
        return do_transfer_stake(
            body.hotkey, body.origin_netuid, body.destination_netuid, amount_rao
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/move-stake")
async def api_move_stake(body: MoveStakeBody, _: str = Depends(get_current_username)):
    try:
        amount_rao = resolve_move_stake_amount(
            body.origin_hotkey, body.origin_netuid, body.amount_tao
        )
        return do_move_stake(
            body.origin_hotkey, body.destination_hotkey,
            body.origin_netuid, body.destination_netuid, amount_rao,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/withdraw")
async def api_withdraw(body: WithdrawBody, _: str = Depends(get_current_username)):
    try:
        return do_withdraw(body.amount_tao)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
