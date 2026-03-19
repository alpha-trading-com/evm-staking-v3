"""UI and root redirect."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_current_username
from app.config import REPO_ROOT

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=str(REPO_ROOT / "app" / "templates"))


@router.get("/")
async def root(_: str = Depends(get_current_username)):
    return RedirectResponse(url="/ui", status_code=302)


@router.get("/ui", response_class=HTMLResponse)
async def index(request: Request, _: str = Depends(get_current_username)):
    return templates.TemplateResponse("index.html", {"request": request})
