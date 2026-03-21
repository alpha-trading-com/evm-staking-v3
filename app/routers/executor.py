"""Executor on/off API and executor_enabled.json read/write."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.schemas import SetExecutorEnabledBody
from app.core.config import set_executor_enabled
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["executor"])


def _executor_status_dict() -> dict:
    enabled = settings.EXECUTOR_ENABLED
    msg = "Executor is OFF. Turn ON so fast stake/unstake are applied." if not enabled else "Executor ON."
    return {"ok": True, "executor_enabled": enabled, "message": msg}


@router.get("/executor-enabled")
async def api_get_executor_enabled():
    """Return whether auto-execute / executor submissions are allowed (executor_enabled.json)."""
    return _executor_status_dict()


@router.put("/executor-enabled")
async def api_put_executor_enabled(body: SetExecutorEnabledBody, _: str = Depends(get_current_username)):
    """Turn executor (execute() submissions) on or off."""
    try:
        set_executor_enabled(body.enabled)
        settings.EXECUTOR_ENABLED = body.enabled
        msg = (
            "Executor is OFF. Turn ON so fast stake/unstake are applied."
            if not body.enabled
            else "Executor ON."
        )
        return {"ok": True, "executor_enabled": body.enabled, "message": msg}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/executor-status", include_in_schema=False)
async def legacy_executor_status(_: str = Depends(get_current_username)):
    """Deprecated: use GET /api/executor-enabled."""
    return _executor_status_dict()


@router.post("/set-executor-enabled", include_in_schema=False)
async def legacy_set_executor_enabled(body: SetExecutorEnabledBody, _: str = Depends(get_current_username)):
    """Deprecated: use PUT /api/executor-enabled."""
    return await api_put_executor_enabled(body, _)
