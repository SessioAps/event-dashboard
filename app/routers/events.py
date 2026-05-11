from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.deps import require_login
from app.models import Event, EventState, User

router = APIRouter(prefix="/events")
templates = Jinja2Templates(directory="app/templates")


def _parse_genre_tags(raw: str) -> list[str]:
    return [t.strip() for t in raw.split(",") if t.strip()]


def _get_event_or_404(db: DbSession, event_id: int) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("")
def list_events(request: Request, db: DbSession = Depends(get_db), user: User = Depends(require_login)):
    events = db.query(Event).order_by(Event.start_at.desc()).all()
    return templates.TemplateResponse(
        "events/list.html", {"request": request, "events": events, "user": user}
    )


@router.get("/new")
def new_event_form(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(
        "events/form.html", {"request": request, "event": None, "user": user}
    )


@router.post("")
def create_event(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    hero_image_url: str = Form(""),
    host_label: str = Form(...),
    host_logo_url: str = Form(""),
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
    event = Event(
        title=title,
        description=description or None,
        hero_image_url=hero_image_url or None,
        host_label=host_label,
        host_logo_url=host_logo_url or None,
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
        "events/form.html", {"request": request, "event": event, "user": user}
    )


@router.post("/{event_id}/edit")
def update_event(
    event_id: int,
    title: str = Form(...),
    description: str = Form(""),
    hero_image_url: str = Form(""),
    host_label: str = Form(...),
    host_logo_url: str = Form(""),
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
    event.title = title
    event.description = description or None
    event.hero_image_url = hero_image_url or None
    event.host_label = host_label
    event.host_logo_url = host_logo_url or None
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
