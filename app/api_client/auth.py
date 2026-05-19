from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session as DbSession

from app.api_client._errors import ApiError
from app.api_client._models import AdminAuthExchangeRequest, SessionTokenResponse
from app.api_client._transport import call_service_token, raise_on_error
from app.config import settings
from app.models import User

logger = logging.getLogger(__name__)


def admin_auth_exchange(user_email: str) -> SessionTokenResponse:
    # POST /v1/admin/auth/exchange
    # Trades the admin service token + the locally-authenticated user's email
    # for a per-user backend bearer (api-conventions.md §1.10).
    body = AdminAuthExchangeRequest(user_email=user_email).model_dump()
    response = call_service_token(
        "POST",
        "/v1/admin/auth/exchange",
        json=body,
        idempotency_key=uuid.uuid4().hex,
    )
    raise_on_error(response)
    return SessionTokenResponse.model_validate(response.json())


def eager_exchange_bearer(*, db: DbSession, user: User) -> Optional[SessionTokenResponse]:
    # AB4 (admin/architecture/decisions.md Session 2026-05-18): initial exchange
    # happens after magic-link verify, before the 303 → /. Graceful posture
    # (admin/architecture/decisions.md Session 2026-05-19): if env unset or
    # exchange fails, log + return None and let `call_with_bearer` re-exchange
    # lazily on first authenticated api-client call. Keeps login working when
    # the backend isn't up (which it isn't, as of 2026-05-19).
    if not (settings.sessio_backend_base_url and settings.sessio_admin_service_token):
        logger.info("eager exchange skipped: SESSIO_BACKEND_* env vars unset")
        return None
    try:
        token = admin_auth_exchange(user.email)
    except ApiError as e:
        logger.warning(
            "eager exchange failed (%s %s); falling back to lazy. user=%s",
            e.status,
            e.code,
            user.email,
        )
        return None
    except RuntimeError as e:
        logger.warning("eager exchange config issue: %s", e)
        return None
    from app.api_client._transport import _write_cached_bearer

    _write_cached_bearer(db, user.id, token)
    logger.info("eager exchange succeeded for user=%s; bearer cached", user.email)
    return token
