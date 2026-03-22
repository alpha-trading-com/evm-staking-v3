"""One-time staking gate password hash + password-protected enable/disable (contract)."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.schemas import InitStakingGateBody, SetStakingUnstakingEnabledBody
from app.services.staking_gate_service import (
    do_init_staking_gate_password,
    do_set_staking_unstaking_enabled,
)

router = APIRouter(prefix="/api", tags=["staking-gate"])


@router.post("/staking-gate/init")
async def api_staking_gate_init(body: InitStakingGateBody, _: str = Depends(get_current_username)):
    """One-time: set keccak256(bytes(password)) on chain. After this, use /staking-gate/enabled to toggle."""
    try:
        return do_init_staking_gate_password(body.password)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@router.post("/staking-gate/enabled")
async def api_staking_gate_enabled(body: SetStakingUnstakingEnabledBody, _: str = Depends(get_current_username)):
    """Enable or disable contract stake/unstake/execute staking paths (requires configured gate + password)."""
    try:
        return do_set_staking_unstaking_enabled(body.enabled, body.password)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
