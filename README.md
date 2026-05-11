# Event Dashboard

Web admin tool for Sessio's internal team to seed events for the artist app's launch. v1 internal slice per [`docs/products/admin/prd.md`](../sessio-docs/docs/products/admin/prd.md). Built with FastAPI, SQLAlchemy, Jinja2, HTMX, and Tailwind CSS.

> **Status:** undergoing refactor against the 2026-05-11 decisions in [`docs/products/admin/architecture/decisions.md`](../sessio-docs/docs/products/admin/architecture/decisions.md). Email broadcasts, social auto-posting, public OG event pages, calendar view, and conference-track "sessions" are being removed. Phase B (Event model + state machine), Phase C (magic-link auth), and Phase D (host identity) follow.

## Features (post-Phase-A)

- Event CRUD (create, read, update — cancel/state-machine landing in Phase B)
- Email + password login (replaced with magic-link + allowlist in Phase C)

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
└── .env.example
```

## Development notes

- Tables are created on startup via `Base.metadata.create_all()`. For
  production, set up Alembic migrations and remove that call from `main.py`.
- The Tailwind CSS is loaded from a CDN for simplicity. For production, run
  a real Tailwind build step.
- CSRF protection is not yet implemented. Add `fastapi-csrf-protect` before
  exposing this to untrusted users.

## License

Private project. Not licensed for public use.
