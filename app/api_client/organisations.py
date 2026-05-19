from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy.orm import Session as DbSession

from app.api_client._models import (
    ConfirmRequest,
    LogoConfirmResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.api_client._transport import call_with_bearer
from app.models import User


def admin_organisation_logo_upload_url(
    *,
    db: DbSession,
    user: User,
    organisation_id: UUID,
    content_type: str,
    size_bytes: int,
) -> UploadUrlResponse:
    # POST /v1/admin/organisations/{organisation_id}/logo/upload-url
    # Mint step. Logo cap is 5 MB (vs hero's 10 MB) per storage.md §4 — the
    # backend enforces.
    body = UploadUrlRequest(content_type=content_type, size_bytes=size_bytes).model_dump()
    response = call_with_bearer(
        "POST",
        f"/v1/admin/organisations/{organisation_id}/logo/upload-url",
        db=db,
        user=user,
        json=body,
        idempotency_key=uuid.uuid4().hex,
    )
    return UploadUrlResponse.model_validate(response.json())


def admin_organisation_logo_confirm(
    *,
    db: DbSession,
    user: User,
    organisation_id: UUID,
    confirm_token: str,
) -> LogoConfirmResponse:
    # POST /v1/admin/organisations/{organisation_id}/logo/confirm
    # Confirm step. On success the backend persists logo_url AND refreshes the
    # denormalised events.host_logo_url snapshot on linked events
    # (storage.md §1 confirm step semantics for org logos).
    body = ConfirmRequest(confirm_token=confirm_token).model_dump()
    response = call_with_bearer(
        "POST",
        f"/v1/admin/organisations/{organisation_id}/logo/confirm",
        db=db,
        user=user,
        json=body,
        idempotency_key=uuid.uuid4().hex,
    )
    return LogoConfirmResponse.model_validate(response.json())
