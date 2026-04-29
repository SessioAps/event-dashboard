from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.deps import require_login
from app.models import Event, User

router = APIRouter(prefix="/events")
templates = Jinja2Templates(directory="app/templates")


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
    location: str = Form(""),
    start_at: str = Form(...),
    end_at: str = Form(...),
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    event = Event(
        title=title,
        description=description,
        location=location,
        start_at=datetime.fromisoformat(start_at),
        end_at=datetime.fromisoformat(end_at),
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
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
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
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return templates.TemplateResponse(
        "events/form.html", {"request": request, "event": event, "user": user}
    )


@router.post("/{event_id}/edit")
def update_event(
    event_id: int,
    title: str = Form(...),
    description: str = Form(""),
    location: str = Form(""),
    start_at: str = Form(...),
    end_at: str = Form(...),
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.title = title
    event.description = description
    event.location = location
    event.start_at = datetime.fromisoformat(start_at)
    event.end_at = datetime.fromisoformat(end_at)
    db.commit()
    return RedirectResponse(url=f"/events/{event.id}", status_code=303)


@router.post("/{event_id}/delete")
def delete_event(
    event_id: int,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return RedirectResponse(url="/events", status_code=303)
