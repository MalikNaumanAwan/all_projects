"""Admin Router"""

from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request) -> HTMLResponse:
    """Render the Admin Dashboard"""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})
