from datetime import datetime

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine, get_db
from app.deps import current_user
from app.models import Event, Session as EventSession, User
from app.routers import auth, broadcast, calendar, events, public, sessions

# Create tables on startup (use Alembic for production migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Event Dashboard")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, max_age=settings.session_max_age)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(sessions.router)
app.include_router(broadcast.router)
app.include_router(calendar.router)
app.include_router(public.router)


@app.get("/")
def home(request: Request, db: DbSession = Depends(get_db), user: User | None = Depends(current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    now = datetime.utcnow()
    stats = {
        "event_count": db.query(Event).count(),
        "upcoming_count": db.query(Event).filter(Event.start_at >= now).count(),
        "session_count": db.query(EventSession).count(),
    }
    recent_events = db.query(Event).order_by(Event.created_at.desc()).limit(5).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "stats": stats, "recent_events": recent_events},
    )
