"""Heartbeat settings API (heartbeat_enabled.json)."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.schemas import HeartbeatSettingsBody
from app.services.settings_service import (
    get_heartbeat_enabled,
    set_heartbeat_enabled_safe,
)

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/heartbeat-enabled")
async def api_get_heartbeat_enabled(_: str = Depends(get_current_username)):
    """Return heartbeat on/off flag."""
    return {"ok": True, "heartbeat_enabled": get_heartbeat_enabled()}


@router.put("/heartbeat-enabled")
async def api_put_heartbeat_enabled(body: HeartbeatSettingsBody, _: str = Depends(get_current_username)):
    """Set heartbeat on/off."""
    try:
        set_heartbeat_enabled_safe(body.enabled)
        return {"ok": True, "heartbeat_enabled": body.enabled}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
