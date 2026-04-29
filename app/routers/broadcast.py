"""Endpoints for broadcasting an event: email all users and post to socials."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.database import get_db
from app.deps import require_admin
from app.models import Event, User
from app.services.email import EmailError, send_bulk
from app.services.social import get_configured_posters, post_to_all
from app.services.social.base import EventPost

router = APIRouter(prefix="/events/{event_id}")
templates = Jinja2Templates(directory="app/templates")


def _get_event(db: DbSession, event_id: int) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _build_event_post(event: Event) -> EventPost:
    return EventPost(
        title=event.title,
        description=event.description or "",
        location=event.location,
        start_at_iso=event.start_at.strftime("%A, %B %d, %Y at %H:%M"),
        public_url=f"{settings.site_url.rstrip('/')}/events/{event.id}/public",
    )


def _render_email_html(event: Event) -> str:
    """Tiny inline-styled HTML email template."""
    location_block = (
        f'<p style="margin:0 0 8px"><strong>Location:</strong> {event.location}</p>'
        if event.location else ""
    )
    description_block = (
        f'<div style="margin-top:16px;color:#475569;line-height:1.5">{event.description}</div>'
        if event.description else ""
    )
    public_url = f"{settings.site_url.rstrip('/')}/events/{event.id}/public"
    return f"""\
<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#f8fafc;margin:0;padding:24px">
  <div style="max-width:560px;margin:0 auto;background:white;padding:32px;border-radius:8px;border:1px solid #e2e8f0">
    <h1 style="margin:0 0 16px;color:#0f172a">{event.title}</h1>
    <p style="margin:0 0 8px"><strong>When:</strong> {event.start_at.strftime("%A, %B %d, %Y · %H:%M")}</p>
    {location_block}
    {description_block}
    <a href="{public_url}" style="display:inline-block;margin-top:24px;background:#2563eb;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">View event details</a>
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:32px 0 16px">
    <p style="color:#64748b;font-size:12px;margin:0">Sent from {settings.site_name}</p>
  </div>
</body></html>"""


@router.post("/broadcast-email")
async def broadcast_email(
    event_id: int,
    request: Request,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    event = _get_event(db, event_id)
    recipients = [u.email for u in db.query(User).all()]

    try:
        result = await send_bulk(
            recipients,
            subject=f"Upcoming: {event.title}",
            html=_render_email_html(event),
        )
        message = f"Email sent to {result['sent']} of {len(recipients)} users."
        if result["failed"]:
            message += f" {result['failed']} failed."
        kind = "success" if result["failed"] == 0 else "warning"
    except EmailError as e:
        message = f"Email send failed: {e}"
        kind = "error"

    if request.headers.get("HX-Request"):
        return _toast_html(message, kind)
    return HTMLResponse(message)


@router.post("/post-social")
async def post_social(
    event_id: int,
    request: Request,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    event = _get_event(db, event_id)
    configured = get_configured_posters()

    if not configured:
        message = "No social platforms are configured. Add API keys to your .env file."
        kind = "warning"
    else:
        results = await post_to_all(_build_event_post(event))
        successes = [r.platform for r in results if r.success]
        failures = [f"{r.platform}: {r.message}" for r in results if not r.success]
        if successes and not failures:
            message = f"Posted to: {', '.join(successes)}"
            kind = "success"
        elif successes:
            message = f"Posted to {', '.join(successes)}. Failures — {'; '.join(failures)}"
            kind = "warning"
        else:
            message = f"All posts failed: {'; '.join(failures)}"
            kind = "error"

    if request.headers.get("HX-Request"):
        return _toast_html(message, kind)
    return HTMLResponse(message)


def _toast_html(message: str, kind: str = "success") -> HTMLResponse:
    """Tiny HTMX-swappable status banner."""
    colors = {
        "success": "bg-green-50 border-green-200 text-green-800",
        "warning": "bg-yellow-50 border-yellow-200 text-yellow-800",
        "error": "bg-red-50 border-red-200 text-red-800",
    }
    classes = colors.get(kind, colors["success"])
    return HTMLResponse(
        f'<div class="px-4 py-3 border rounded {classes}">{message}</div>'
    )
