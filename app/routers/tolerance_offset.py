"""Tolerance offset API (tolerance_offset.json / core settings)."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.core.config import load_tolerance_offset
from app.schemas import ToleranceOffsetBody
from app.services.settings_service import set_tolerance_offset

router = APIRouter(prefix="/api", tags=["tolerance-offset"])


@router.get("/tolerance-offset")
async def api_get_tolerance_offset(_: str = Depends(get_current_username)):
    """Return current tolerance offset used for min-tolerance limit orders."""
    return {"ok": True, "tolerance_offset": load_tolerance_offset()}


@router.put("/tolerance-offset")
async def api_put_tolerance_offset(body: ToleranceOffsetBody, _: str = Depends(get_current_username)):
    """Set tolerance offset (number or *multiplier string)."""
    if not set_tolerance_offset(body.tolerance_offset):
        return JSONResponse(
            {"ok": False, "error": "Failed to save tolerance offset"},
            status_code=500,
        )
    return {"ok": True, "tolerance_offset": load_tolerance_offset()}
