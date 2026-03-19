"""Executor on/off API."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.schemas import SetExecutorEnabledBody
from app.services.executor_service import read_executor_enabled, set_executor_enabled

router = APIRouter(prefix="/api", tags=["executor"])


@router.get("/executor-status")
async def executor_status(_: str = Depends(get_current_username)):
    """Return executor on/off (UI toggle)."""
    enabled = read_executor_enabled()
    msg = "Executor is OFF. Turn ON so fast stake/unstake are applied." if not enabled else "Executor ON."
    return {"ok": True, "executor_enabled": enabled, "message": msg}


@router.post("/set-executor-enabled")
async def set_executor_enabled_endpoint(body: SetExecutorEnabledBody, _: str = Depends(get_current_username)):
    """Turn executor (execute() submissions) on or off."""
    try:
        set_executor_enabled(body.enabled)
        return {"ok": True, "executor_enabled": body.enabled}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
