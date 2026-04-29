from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.deps import require_login
from app.models import Event, Session, User

router = APIRouter(prefix="/events/{event_id}/sessions")
templates = Jinja2Templates(directory="app/templates")


def _get_event_or_404(db: DbSession, event_id: int) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("")
def create_session(
    event_id: int,
    request: Request,
    title: str = Form(...),
    speaker: str = Form(""),
    description: str = Form(""),
    start_at: str = Form(...),
    end_at: str = Form(...),
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    event = _get_event_or_404(db, event_id)
    session = Session(
        event_id=event.id,
        title=title,
        speaker=speaker,
        description=description,
        start_at=datetime.fromisoformat(start_at),
        end_at=datetime.fromisoformat(end_at),
    )
    db.add(session)
    db.commit()
    db.refresh(event)

    # If the request came from HTMX, return just the updated session list fragment
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "events/_sessions_list.html", {"request": request, "event": event}
        )
    return RedirectResponse(url=f"/events/{event_id}", status_code=303)


@router.post("/{session_id}/delete")
def delete_session(
    event_id: int,
    session_id: int,
    request: Request,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    session = (
        db.query(Session)
        .filter(Session.id == session_id, Session.event_id == event_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()

    if request.headers.get("HX-Request"):
        return HTMLResponse("")  # HTMX swaps the row out
    return RedirectResponse(url=f"/events/{event_id}", status_code=303)
