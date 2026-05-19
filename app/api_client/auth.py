from __future__ import annotations

import uuid

from app.api_client._models import AdminAuthExchangeRequest, SessionTokenResponse
from app.api_client._transport import call_service_token, raise_on_error


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
