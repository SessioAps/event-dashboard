"""Public-facing event page (no login required) for sharing on social media.

This page includes Open Graph and Twitter Card meta tags so that when someone
shares the URL on any platform (WhatsApp, Slack, Twitter, LinkedIn, Discord,
iMessage, etc.) it auto-generates a rich preview with the event details.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.database import get_db
from app.models import Event

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/events/{event_id}/public")
def public_event(event_id: int, request: Request, db: DbSession = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    public_url = f"{settings.site_url.rstrip('/')}/events/{event.id}/public"
    return templates.TemplateResponse(
        "public_event.html",
        {
            "request": request,
            "event": event,
            "public_url": public_url,
            "site_name": settings.site_name,
        },
    )
