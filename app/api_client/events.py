from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session as DbSession

from app.api_client._models import (
    ConfirmRequest,
    EventPage,
    HeroConfirmResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.api_client._transport import call_with_bearer
from app.models import User


def admin_event_list(
    *,
    db: DbSession,
    user: User,
    limit: int = 20,
    cursor: Optional[str] = None,
    state: Optional[str] = None,
    host_organisation_id: Optional[UUID] = None,
    q: Optional[str] = None,
) -> EventPage:
    # GET /v1/admin/events
    # Sort: (start_at DESC, id DESC). Returns events in every state including
    # `cancelled`. Cursor pagination per api-conventions.md §3.
    params: dict[str, object] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    if state is not None:
        params["state"] = state
    if host_organisation_id is not None:
        params["host_organisation_id"] = str(host_organisation_id)
    if q is not None:
        params["q"] = q

    response = call_with_bearer("GET", "/v1/admin/events", db=db, user=user, params=params)
    return EventPage.model_validate(response.json())


def admin_event_hero_upload_url(
    *,
    db: DbSession,
    user: User,
    event_id: UUID,
    content_type: str,
    size_bytes: int,
) -> UploadUrlResponse:
    # POST /v1/admin/events/{event_id}/hero/upload-url
    # Mint step of the two-call upload (storage.md §1). Body declares
    # content_type + size_bytes for signature pinning. Idempotency-Key
    # required (api-conventions §6).
    body = UploadUrlRequest(content_type=content_type, size_bytes=size_bytes).model_dump()
    response = call_with_bearer(
        "POST",
        f"/v1/admin/events/{event_id}/hero/upload-url",
        db=db,
        user=user,
        json=body,
        idempotency_key=uuid.uuid4().hex,
    )
    return UploadUrlResponse.model_validate(response.json())


def admin_event_hero_confirm(
    *,
    db: DbSession,
    user: User,
    event_id: UUID,
    confirm_token: str,
) -> HeroConfirmResponse:
    # POST /v1/admin/events/{event_id}/hero/confirm
    # Confirm step. Backend validates the upload landed (size + content-type
    # match the signature) and persists hero_image_url on the event.
    body = ConfirmRequest(confirm_token=confirm_token).model_dump()
    response = call_with_bearer(
        "POST",
        f"/v1/admin/events/{event_id}/hero/confirm",
        db=db,
        user=user,
        json=body,
        idempotency_key=uuid.uuid4().hex,
    )
    return HeroConfirmResponse.model_validate(response.json())
