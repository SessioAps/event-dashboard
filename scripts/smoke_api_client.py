"""Pattern-slice smoke test for the api-client.

Run against a live sessio-backend instance:

    py -m scripts.smoke_api_client <admin-email>

Required env (in .env or process env):
    SESSIO_BACKEND_BASE_URL=https://backend.example  (or http://localhost:8001)
    SESSIO_ADMIN_SERVICE_TOKEN=<the long-lived token Arne provisions>
    ADMIN_EMAILS=<your email>,...

What this does:
    1. Bootstraps a User row for <admin-email> if missing (mirrors what
       magic-link verify would do).
    2. Calls adminAuthExchange via the service token, persists the per-user
       bearer in BearerCache.
    3. Calls adminEventList, prints the first page.

Validates: env wiring, service-token exchange, bearer cache write, bearer
read on subsequent call, problem+json error parsing if anything fails.
"""

from __future__ import annotations

import sys

from app.api_client import ApiError, admin_event_list
from app.api_client.auth import admin_auth_exchange
from app.api_client._transport import _write_cached_bearer
from app.auth import find_or_create_user
from app.database import Base, SessionLocal, engine


def main(email: str) -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = find_or_create_user(db, email)
        print(f"User: id={user.id} email={user.email}")

        token = admin_auth_exchange(email)
        _write_cached_bearer(db, user.id, token)
        print(f"Bearer minted: expires_at={token.expires_at.isoformat()} user_id={token.user_id}")

        page = admin_event_list(db=db, user=user, limit=5)
        print(f"Events: count={len(page.items)} next_cursor={page.next_cursor}")
        for ev in page.items:
            print(f"  - {ev.id} {ev.start_at.isoformat()} {ev.state:>9} | {ev.title}")
        return 0
    except ApiError as e:
        print(f"ApiError: status={e.status} code={e.code} detail={e.detail}", file=sys.stderr)
        if e.errors:
            for fe in e.errors:
                print(f"  field={fe.field} code={fe.code} message={fe.message}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: py -m scripts.smoke_api_client <admin-email>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
