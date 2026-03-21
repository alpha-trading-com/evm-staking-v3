"""Executor on/off API and executor_enabled.json read/write."""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.config import REPO_ROOT
from app.schemas import SetExecutorEnabledBody
from bt_utils.constants import EXECUTOR_ENABLED_FILENAME

router = APIRouter(prefix="/api", tags=["executor"])


def read_executor_enabled() -> bool:
    """True if executor_enabled.json has \"enabled\": true. Default True if file missing."""
    path = REPO_ROOT / EXECUTOR_ENABLED_FILENAME
    if not path.is_file():
        return True
    try:
        with open(path) as f:
            return json.load(f).get("enabled", True)
    except Exception:
        return True


def set_executor_enabled(enabled: bool) -> None:
    """Write executor_enabled.json. Raises on IO error."""
    path = REPO_ROOT / EXECUTOR_ENABLED_FILENAME
    with open(path, "w") as f:
        json.dump({"enabled": enabled}, f)


def _executor_status_dict() -> dict:
    enabled = read_executor_enabled()
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
