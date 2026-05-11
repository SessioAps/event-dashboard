# Event Dashboard

Web admin tool for Sessio's internal team to seed events for the artist app's launch. v1 internal slice per [`docs/products/admin/prd.md`](../../sessio-docs/docs/products/admin/prd.md) in the sibling sessio-docs repo. Built with FastAPI, SQLAlchemy, Jinja2, HTMX, and Tailwind CSS.

> **Status:** Phases A-C of the 2026-05-11 decisions in [`decisions.md`](../../sessio-docs/docs/products/admin/architecture/decisions.md) are landed. Phase D (Q1 + F1 — backend platform service API client + presigned-URL image upload) is blocked on the backend existing.

## Features

- Event CRUD with state machine (`scheduled` → `live` → `completed` / `cancelled`).
- Magic-link sign-in against an admin-email allowlist (no passwords).

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI |
| Database | SQLite (dev) — placeholder until backend platform service exists |
| ORM | SQLAlchemy 2.0 |
| Templates | Jinja2 + HTMX |
| Styling | Tailwind CSS (CDN) |
| Auth | Cookie sessions + magic-link tokens |

## Quick start

```bash
# Windows (PowerShell)
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set the admin allowlist + a session secret
echo 'ADMIN_EMAILS=julieta@sessio.io,mattis@sessio.io,arne@sessio.io,johannes@sessio.io' >> .env
echo 'SECRET_KEY=<a-long-random-string>' >> .env

# Run the server
uvicorn app.main:app --reload
```

Open <http://localhost:8000>. Enter an allowlisted email; the magic link prints to the server console (the team grabs it from logs locally). Production deployment needs a real transactional sender swapped into `app/auth.py:send_magic_link`.

## Project structure

```
event_dashboard/
├── app/
│   ├── main.py              FastAPI entry point
│   ├── config.py            Settings loaded from .env
│   ├── database.py          SQLAlchemy engine and session
│   ├── auth.py              Magic-link token helpers
│   ├── deps.py              Auth dependencies (require_login)
│   ├── models/              SQLAlchemy models (User, MagicLinkToken, Event)
│   ├── routers/             Route handlers (auth, events)
│   └── templates/           Jinja2 HTML templates
├── requirements.txt
└── README.md
```

## Development notes

- Tables are created on startup via `Base.metadata.create_all()`. Once the backend platform service exists, this dashboard reads/writes via that service and the local SQLite goes away (decisions.md Q1).
- Tailwind CSS is loaded from a CDN. Production = real Tailwind build step.
- CSRF protection isn't implemented yet. Add `fastapi-csrf-protect` before exposing this beyond localhost.

## License

Private project. Not licensed for public use.
