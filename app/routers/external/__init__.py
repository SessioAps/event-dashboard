from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.deps import require_login
from app.models import User
from app.routers.external import artists, events, sessions, settings, works

router = APIRouter(prefix="/external")
templates = Jinja2Templates(directory="app/templates")

# Five surfaces stubbed for the v2/v3 org-admin tool (per scope.md §5).
# Internal-now (the rest of this repo) ships at v1; external-later is
# placeholder-only until the external org-admin tool is built out.
SURFACES = [
    {"slug": "events", "name": "Events", "description": "Org admins managing the events they host."},
    {"slug": "works", "name": "Works", "description": "Publishers managing the works they hold rights to."},
    {"slug": "sessions", "name": "Sessions", "description": "Orgs managing sessions created on behalf of signed artists."},
    {"slug": "artists", "name": "Signed artists", "description": "Org rosters and signed-artist relationship management."},
    {"slug": "settings", "name": "Settings", "description": "Org profile, billing, team members."},
]


@router.get("")
def external_index(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(
        "external/index.html",
        {"request": request, "user": user, "surfaces": SURFACES},
    )


router.include_router(events.router)
router.include_router(works.router)
router.include_router(sessions.router)
router.include_router(artists.router)
router.include_router(settings.router)
