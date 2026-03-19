"""Stake info (coldkey stakes list) API."""
from fastapi import Depends
from fastapi.responses import JSONResponse

from app.auth import get_current_username
from app.services.stake_info_service import get_stake_info_response

router = APIRouter(prefix="/api", tags=["stake_info"])


@router.get("/stake-info")
async def api_stake_info(_: str = Depends(get_current_username)):
    """Get stake info for the configured coldkey."""
    try:
        return get_stake_info_response()
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)
