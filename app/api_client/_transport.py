from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session as DbSession

from app.api_client._errors import ApiAuthError, ApiError, error_for
from app.api_client._models import FieldError, SessionTokenResponse
from app.config import settings
from app.models import BearerCache, User

logger = logging.getLogger(__name__)


# Single shared httpx.Client. Per-call auth is injected via the `headers`
# argument; the client carries no per-user state.
_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        if not settings.sessio_backend_base_url:
            raise RuntimeError(
                "SESSIO_BACKEND_BASE_URL is not set. Configure .env before "
                "exercising api-client calls."
            )
        _client = httpx.Client(
            base_url=settings.sessio_backend_base_url.rstrip("/"),
            timeout=settings.sessio_backend_timeout_seconds,
        )
    return _client


def _new_request_id() -> str:
    # Per api-conventions §7.5: must match ^[0-9a-zA-Z\-_]{1,64}$. uuid4 hex
    # (32 chars) satisfies this and matches the server's character set.
    return uuid.uuid4().hex


def _parse_problem(response: httpx.Response) -> ApiError:
    request_id = response.headers.get("x-request-id")
    try:
        body = response.json()
    except ValueError:
        return ApiError(
            status=response.status_code,
            code="INTERNAL_ERROR",
            detail=f"Non-JSON {response.status_code} response from backend.",
            request_id=request_id,
        )
    raw_errors = body.get("errors")
    errors: Optional[list[FieldError]] = None
    if isinstance(raw_errors, list):
        errors = [FieldError.model_validate(e) for e in raw_errors]
    return error_for(
        status=response.status_code,
        code=body.get("code") or "INTERNAL_ERROR",
        detail=body.get("detail") or body.get("title") or "Backend error.",
        errors=errors,
        request_id=request_id,
    )


def call_service_token(
    method: str,
    path: str,
    *,
    json: Optional[dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> httpx.Response:
    # Used by adminAuthExchange only — auth is the long-lived AdminServiceToken
    # rather than a per-user bearer. Every other operation uses
    # `call_with_bearer` below.
    if not settings.sessio_admin_service_token:
        raise RuntimeError(
            "SESSIO_ADMIN_SERVICE_TOKEN is not set. The admin tool cannot "
            "exchange for per-user bearers without it."
        )
    headers: dict[str, str] = {
        "Authorization": f"Bearer {settings.sessio_admin_service_token}",
        "X-Request-Id": _new_request_id(),
        "Accept": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    response = _get_client().request(method, path, json=json, headers=headers)
    return response


def _read_cached_bearer(db: DbSession, user_id: int) -> Optional[str]:
    row = db.query(BearerCache).filter(BearerCache.user_id == user_id).first()
    if not row:
        return None
    if row.expires_at <= datetime.utcnow():
        return None
    return row.bearer


def _write_cached_bearer(db: DbSession, user_id: int, token: SessionTokenResponse) -> None:
    row = db.query(BearerCache).filter(BearerCache.user_id == user_id).first()
    if row is None:
        row = BearerCache(user_id=user_id, bearer=token.access_token, expires_at=token.expires_at)
        db.add(row)
    else:
        row.bearer = token.access_token
        row.expires_at = token.expires_at
    db.commit()


def _invalidate_bearer(db: DbSession, user_id: int) -> None:
    row = db.query(BearerCache).filter(BearerCache.user_id == user_id).first()
    if row:
        db.delete(row)
        db.commit()


def call_with_bearer(
    method: str,
    path: str,
    *,
    db: DbSession,
    user: User,
    params: Optional[dict[str, Any]] = None,
    json: Optional[dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> httpx.Response:
    # Per-user authenticated call. Reads the bearer from BearerCache; on 401
    # invalidates and re-exchanges once before retrying.
    from app.api_client.auth import admin_auth_exchange  # avoid import cycle

    bearer = _read_cached_bearer(db, user.id)
    if bearer is None:
        token = admin_auth_exchange(user.email)
        _write_cached_bearer(db, user.id, token)
        bearer = token.access_token

    response = _send_with_bearer(
        method, path, bearer=bearer, params=params, json=json, idempotency_key=idempotency_key
    )

    if response.status_code == 401:
        logger.info("backend 401 for user=%s; re-exchanging bearer", user.id)
        _invalidate_bearer(db, user.id)
        token = admin_auth_exchange(user.email)
        _write_cached_bearer(db, user.id, token)
        response = _send_with_bearer(
            method,
            path,
            bearer=token.access_token,
            params=params,
            json=json,
            idempotency_key=idempotency_key,
        )

    if response.status_code >= 400:
        raise _parse_problem(response)
    return response


def _send_with_bearer(
    method: str,
    path: str,
    *,
    bearer: str,
    params: Optional[dict[str, Any]] = None,
    json: Optional[dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> httpx.Response:
    headers: dict[str, str] = {
        "Authorization": f"Bearer {bearer}",
        "X-Request-Id": _new_request_id(),
        "Accept": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return _get_client().request(method, path, params=params, json=json, headers=headers)


def raise_on_error(response: httpx.Response) -> None:
    if response.status_code >= 400:
        raise _parse_problem(response)


# Re-exported for callers that want to surface ApiAuthError specifically.
__all__ = [
    "ApiAuthError",
    "call_service_token",
    "call_with_bearer",
    "raise_on_error",
]
