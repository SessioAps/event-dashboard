# Event Dashboard

Web admin tool for Sessio's internal team to seed events for the artist app's launch. v1 internal slice per [`docs/products/admin/prd.md`](../../sessio-docs/docs/products/admin/prd.md) in the sibling sessio-docs repo. Built with FastAPI, SQLAlchemy, Jinja2, HTMX, and Tailwind CSS.

> **Status (2026-05-20).** Phases A–D landed (out-of-scope cuts, Event model overhaul, magic-link auth, Hub-directory CRUD). **Phase E** — backend platform service integration — is fully scaffolded impl-side and aligned with `sessio-docs` scaffold-spec: api-client (17/17 admin operationIds wrapped, including dormant `adminReports*` wrappers for the 1.1 reports surface), image-upload helpers (server-proxy via presigned URLs), routing-skeleton (internal-now default + external-later stubs), admin-auth eager exchange. **All wrappers are dormant** — no router calls them yet. [SBL-0069](../../sessio-docs/docs/shared-backlog.md#sbl-0069) resolved 2026-05-19 (Arne addendum): **posture α locked** — `dashboard.db` stays authoritative through 1.0; Phase E cutover lands post-launch as a single Julieta-solo migration script (Arne PR-reviews) when both triggers fire: sessio-backend live + smoke green AND 1.0 launch hardening over. Per Q5 same session, `sessio-backend` is **parked through 1.0 launch** (bootstrap-only as of 2026-05-19; no backend impl pre-launch; revisit week of 2026-06-01). Per [`admin/prd.md`](../../sessio-docs/docs/products/admin/prd.md) §6 the admin tool is launch-supporting, not launch-blocking — `event-dashboard` ships locally through 1.0; Mattis-seeded events are local-only unless Arne raw-DB-inserts to backend per §6 fallback.

## Features

- Event CRUD with state machine (`scheduled` → `live` → `completed` / `cancelled`).
- Hub-directory CRUD for organisations (`org` / `publisher` / `label`) — host picker on the event form reads from this.
- Magic-link sign-in against an admin-email allowlist (no passwords).
- API client against `sessio-backend` (17 admin operationIds wrapped, hand-written `httpx` + Pydantic v2); fully dormant — no router activates the wrappers at 1.0 per the locked posture α from [SBL-0069](../../sessio-docs/docs/shared-backlog.md#sbl-0069).
- External-later stub surface at `/external/*` (events / works / sessions / artists / settings) for the v2/v3 org-admin tool.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI |
| Database | SQLite (dev) — placeholder until SBL-0069 posture pick + backend cutover |
| ORM | SQLAlchemy 2.0 |
| Templates | Jinja2 + HTMX |
| Styling | Tailwind CSS (CDN) |
| Auth (admin) | Cookie sessions + magic-link tokens |
| API client | Hand-written `httpx` + Pydantic v2 (17 admin operationIds, dormant) |

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

# Required: admin allowlist + session secret
echo 'ADMIN_EMAILS=julieta@sessio.io,mattis@sessio.io,arne@sessio.io,johannes@sessio.io' >> .env
echo 'SECRET_KEY=<a-long-random-string>' >> .env

# Optional: api-client wiring to sessio-backend (leave unset for local-only dev)
# echo 'SESSIO_BACKEND_BASE_URL=http://localhost:8001' >> .env
# echo 'SESSIO_ADMIN_SERVICE_TOKEN=<token from Arne>' >> .env

# Run the server
uvicorn app.main:app --reload
```

Open <http://localhost:8000>. Enter an allowlisted email; the magic link prints to the server console (the team grabs it from logs locally). Production deployment needs a real transactional sender swapped into `app/auth.py:send_magic_link`.

When the `SESSIO_BACKEND_*` env vars are set, the magic-link verify flow eagerly exchanges for a per-user backend bearer (per `auth.md` §8 AB4); when unset, the eager exchange logs and is skipped — login still works, the lazy path takes over on first api-client call.

## Project structure

```
event_dashboard/
├── app/
│   ├── main.py              FastAPI entry point
│   ├── config.py            Settings loaded from .env (admin allowlist + backend wiring)
│   ├── database.py          SQLAlchemy engine and session
│   ├── auth.py              Magic-link token helpers
│   ├── deps.py              Auth dependencies (require_login)
│   ├── models/              SQLAlchemy models (User, MagicLinkToken, Event, Organisation, BearerCache)
│   ├── routers/             Route handlers
│   │   ├── auth.py          /login + magic-link verify
│   │   ├── events.py        /events (internal-now)
│   │   ├── organisations.py /organisations (internal-now, Hub directory)
│   │   └── external/        /external/* stubs for v2/v3 org-admin surface
│   ├── api_client/          Typed client for sessio-backend
│   │   ├── _transport.py    httpx + bearer caching + Idempotency-Key + RFC-7807 parsing
│   │   ├── _errors.py       ApiError hierarchy
│   │   ├── _models.py       Pydantic schemas for every operation
│   │   ├── auth.py          adminAuthExchange + eager-exchange wrapper
│   │   ├── events.py        7 event operationIds
│   │   ├── organisations.py 7 organisation operationIds
│   │   └── reports.py       2 moderation-report operationIds (dormant for 1.1)
│   ├── services/
│   │   └── upload.py        Server-proxy image-upload helpers (event hero, org logo)
│   └── templates/           Jinja2 HTML templates (incl. _image_input.html partial)
├── scripts/
│   └── smoke_api_client.py  End-to-end round-trip validator against a live backend
├── .claude/skills/sessio-align-grill/
│   ├── SKILL.md             Continuous-alignment skill (impl side of ADR-0010)
│   ├── decisions.md         Locked impl-side decisions (api-client / routing-skeleton / image-upload / admin-auth)
│   └── pending-grills.md    Open cross-boundary calls (PG-01 resolved → SBL-0069 closed 2026-05-19; PG-02 admin tool visual polish, post-launch)
├── requirements.txt
└── README.md
```

## Development notes

- Tables are created on startup via `Base.metadata.create_all()`. Phase E cutover (post-launch per posture α / SBL-0069 Arne addendum 2026-05-19) will retire `dashboard.db` — a Julieta-solo migration script swaps routers to `app.api_client` and ports local rows to `sessio-backend` in a single refactor (Arne PR-reviews). Trigger fires when sessio-backend is live + smoke-test green AND 1.0 launch hardening is over (earliest ~week of 2026-06-08).
- Tailwind CSS is loaded from a CDN. Production = real Tailwind build step.
- CSRF protection isn't implemented yet. Add `fastapi-csrf-protect` before exposing this beyond localhost.
- Cross-boundary work (anything that touches `sessio-docs`) goes through `/sessio-grill` in the sessio-docs repo. Local impl-side decisions go through `/sessio-align-grill` here (continuous-alignment loop against the scaffold-spec).

## License

Private project. Not licensed for public use.
