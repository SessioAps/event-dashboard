from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.deps import require_login
from app.models import User

router = APIRouter(prefix="/settings")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def settings_stub(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(
        "external/stub.html",
        {
            "request": request,
            "user": user,
            "surface_name": "Settings",
            "surface_description": "Org profile, billing, team members. v2/v3 — external org-admin surface.",
        },
    )
