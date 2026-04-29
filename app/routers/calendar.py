import calendar
from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.deps import require_login
from app.models import Event, User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/calendar")
def calendar_view(
    request: Request,
    year: int | None = None,
    month: int | None = None,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    today = date.today()
    year = year or today.year
    month = month or today.month

    # Build the month grid
    cal = calendar.Calendar(firstweekday=0)  # Monday
    month_days = list(cal.itermonthdates(year, month))

    # Fetch events overlapping this month
    month_start = datetime(year, month, 1)
    next_month = datetime(year + (month // 12), (month % 12) + 1, 1)
    events = (
        db.query(Event)
        .filter(and_(Event.start_at < next_month, Event.end_at >= month_start))
        .order_by(Event.start_at)
        .all()
    )

    # Group events by day
    events_by_day: dict[date, list[Event]] = {}
    for ev in events:
        d = ev.start_at.date()
        events_by_day.setdefault(d, []).append(ev)

    # Previous and next month for navigation
    prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
    next_year, next_month_num = (year, month + 1) if month < 12 else (year + 1, 1)

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": user,
            "year": year,
            "month": month,
            "month_name": calendar.month_name[month],
            "month_days": month_days,
            "events_by_day": events_by_day,
            "today": today,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month_num,
        },
    )
