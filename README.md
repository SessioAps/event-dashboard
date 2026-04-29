# Event Dashboard

A web-based admin dashboard for creating, managing, and promoting events and their sessions. Built with FastAPI, SQLAlchemy, Jinja2, HTMX, and Tailwind CSS.

## Features

- 🔐 Email/password login with admin and editor roles
- 📅 Event CRUD (create, read, update, delete)
- 🎤 Inline session management on each event (no page reload, via HTMX)
- 🗓 Monthly calendar view of all events
- 🔗 Public, shareable event pages with Open Graph previews
- 📧 One-click email broadcasts to all users (via Resend)
- 📣 One-click social posting (LinkedIn working; Twitter/Facebook/Instagram stubbed)
- 🌐 Native share buttons (Twitter, LinkedIn, Facebook, WhatsApp, email) — no API setup required

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI | Modern, fast, auto-documented |
| Database | SQLite (dev) / PostgreSQL (prod) | Zero-setup locally, scalable later |
| ORM | SQLAlchemy 2.0 | Database-agnostic |
| Templates | Jinja2 + HTMX | Server-rendered with snappy interactivity, no SPA complexity |
| Styling | Tailwind CSS | Utility-first, no custom CSS files |
| Auth | Cookie sessions + bcrypt | Simple and secure for an internal tool |
| Email | Resend | Easiest modern email API |

## Quick start

### Prerequisites

- Python 3.12 or newer
- Git

### Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd event_dashboard

# Create a virtual environment and install dependencies
# Windows (PowerShell):
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt

# macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set SECRET_KEY at minimum

# Create the first admin user
python -m scripts.create_admin   # or `py -m scripts.create_admin` on Windows

# Run the server
uvicorn app.main:app --reload    # or `py -m uvicorn app.main:app --reload`
```

Open http://localhost:8000 and sign in.

## Project structure

```
event_dashboard/
├── app/
│   ├── main.py              FastAPI entry point
│   ├── config.py            Settings loaded from .env
│   ├── database.py          SQLAlchemy engine and session
│   ├── auth.py              Password hashing and login helpers
│   ├── deps.py              Auth dependencies (require_login, require_admin)
│   ├── models/              SQLAlchemy models (User, Event, Session)
│   ├── routers/             Route handlers grouped by feature
│   ├── services/            External integrations (email, social)
│   └── templates/           Jinja2 HTML templates
├── scripts/
│   └── create_admin.py      Bootstrap the first admin user
├── requirements.txt
├── README.md
├── SETUP_BROADCASTS.md      Configuring email and social
└── .env.example
```

## Optional features

### Email broadcasts (Resend)

1. Sign up at [resend.com](https://resend.com) and create an API key.
2. Add to `.env`: `RESEND_API_KEY=re_...`
3. Restart the server. The "📧 Email all users" button now sends real emails.

See [`SETUP_BROADCASTS.md`](SETUP_BROADCASTS.md) for full details, including verifying your sending domain.

### LinkedIn auto-posting

Requires creating a LinkedIn developer app and generating an access token.
Full step-by-step in [`SETUP_BROADCASTS.md`](SETUP_BROADCASTS.md).

### Other social platforms

Twitter/X, Facebook, and Instagram are stubbed in `app/services/social/stubs.py`
with comments explaining each platform's requirements. Implement the same
interface as `LinkedInPoster` to add a working integration.

## Roles

- **admin**: full access including broadcast features
- **editor**: can create and edit events, but cannot send emails or post to social

Set a user's role in the database directly, or extend `scripts/create_admin.py`
to create editor accounts.

## Development notes

- Tables are created on startup via `Base.metadata.create_all()`. For
  production, set up Alembic migrations and remove that call from `main.py`.
- The Tailwind CSS is loaded from a CDN for simplicity. For production, run
  a real Tailwind build step.
- CSRF protection is not yet implemented. Add `fastapi-csrf-protect` before
  exposing this to untrusted users.

## License

Private project. Not licensed for public use.
