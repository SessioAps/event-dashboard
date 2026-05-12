from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.deps import require_login
from app.models import Event, EventState, Organisation, OrganisationKind, User

router = APIRouter(prefix="/events")
templates = Jinja2Templates(directory="app/templates")


def _parse_genre_tags(raw: str) -> list[str]:
    return [t.strip() for t in raw.split(",") if t.strip()]


def _host_orgs(db: DbSession) -> list[Organisation]:
    return (
        db.query(Organisation)
        .filter(Organisation.kind == OrganisationKind.org)
        .order_by(func.lower(Organisation.name))
        .all()
    )


def _get_event_or_404(db: DbSession, event_id: int) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _resolve_host(db: DbSession, host_organisation_id: int) -> Organisation:
    org = (
        db.query(Organisation)
        .filter(
            Organisation.id == host_organisation_id,
            Organisation.kind == OrganisationKind.org,
        )
        .first()
    )
    if not org:
        raise HTTPException(status_code=400, detail="Invalid host organisation")
    return org


@router.get("")
def list_events(request: Request, db: DbSession = Depends(get_db), user: User = Depends(require_login)):
    events = db.query(Event).order_by(Event.start_at.desc()).all()
    return templates.TemplateResponse(
        "events/list.html", {"request": request, "events": events, "user": user}
    )


@router.get("/new")
def new_event_form(request: Request, db: DbSession = Depends(get_db), user: User = Depends(require_login)):
    return templates.TemplateResponse(
        "events/form.html",
        {"request": request, "event": None, "user": user, "host_orgs": _host_orgs(db)},
    )


@router.post("")
def create_event(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    hero_image_url: str = Form(""),
    host_organisation_id: int = Form(...),
    venue_name: str = Form(""),
    venue_city: str = Form(...),
    venue_country: str = Form(...),
    venue_address: str = Form(""),
    start_at: str = Form(...),
    end_at: str = Form(...),
    genre_tags: str = Form(""),
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    org = _resolve_host(db, host_organisation_id)
    event = Event(
        title=title,
        description=description or None,
        hero_image_url=hero_image_url or None,
        host_organisation_id=org.id,
        host_name=org.name,
        host_logo_url=org.logo_url,
        venue_name=venue_name or None,
        venue_city=venue_city,
        venue_country=venue_country,
        venue_address=venue_address or None,
        start_at=datetime.fromisoformat(start_at),
        end_at=datetime.fromisoformat(end_at),
        genre_tags=_parse_genre_tags(genre_tags),
        created_by_id=user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return RedirectResponse(url=f"/events/{event.id}", status_code=303)


@router.get("/{event_id}")
def event_detail(
    event_id: int,
    request: Request,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    event = _get_event_or_404(db, event_id)
    return templates.TemplateResponse(
        "events/detail.html", {"request": request, "event": event, "user": user}
    )


@router.get("/{event_id}/edit")
def edit_event_form(
    event_id: int,
    request: Request,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    event = _get_event_or_404(db, event_id)
    return templates.TemplateResponse(
        "events/form.html",
        {"request": request, "event": event, "user": user, "host_orgs": _host_orgs(db)},
    )


@router.post("/{event_id}/edit")
def update_event(
    event_id: int,
    title: str = Form(...),
    description: str = Form(""),
    hero_image_url: str = Form(""),
    host_organisation_id: int = Form(...),
    venue_name: str = Form(""),
    venue_city: str = Form(...),
    venue_country: str = Form(...),
    venue_address: str = Form(""),
    start_at: str = Form(...),
    end_at: str = Form(...),
    genre_tags: str = Form(""),
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    event = _get_event_or_404(db, event_id)
    org = _resolve_host(db, host_organisation_id)
    event.title = title
    event.description = description or None
    event.hero_image_url = hero_image_url or None
    event.host_organisation_id = org.id
    event.host_name = org.name
    event.host_logo_url = org.logo_url
    event.venue_name = venue_name or None
    event.venue_city = venue_city
    event.venue_country = venue_country
    event.venue_address = venue_address or None
    event.start_at = datetime.fromisoformat(start_at)
    event.end_at = datetime.fromisoformat(end_at)
    event.genre_tags = _parse_genre_tags(genre_tags)
    db.commit()
    return RedirectResponse(url=f"/events/{event.id}", status_code=303)


@router.post("/{event_id}/cancel")
def cancel_event(
    event_id: int,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    event = _get_event_or_404(db, event_id)
    if event.state == EventState.cancelled:
        return RedirectResponse(url=f"/events/{event.id}", status_code=303)
    event.state = EventState.cancelled
    db.commit()
    # TODO(backend): backend service fires cancellation push to RSVPed users
    # (app/prd.md §5.6.6). Until the API client lands, cancellation only flips
    # local state — no notification fans out.
    return RedirectResponse(url=f"/events/{event.id}", status_code=303)
