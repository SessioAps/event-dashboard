from __future__ import annotations

import uuid
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session as DbSession

from app.api_client._models import (
    ConfirmRequest,
    LogoConfirmResponse,
    Organisation,
    OrganisationCreate,
    OrganisationPage,
    OrganisationPatch,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.api_client._transport import call_with_bearer
from app.models import User


def organisations_list(
    *,
    db: DbSession,
    user: User,
    limit: int = 20,
    cursor: Optional[str] = None,
    kind: Optional[str] = None,
    q: Optional[str] = None,
) -> OrganisationPage:
    # GET /v1/organisations. Public read surface (also tagged admin); same
    # path used by the host-picker on event create/edit.
    params: dict[str, Any] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    if kind is not None:
        params["kind"] = kind
    if q is not None:
        params["q"] = q
    response = call_with_bearer(
        "GET", "/v1/organisations", db=db, user=user, params=params
    )
    return OrganisationPage.model_validate(response.json())


def organisation_get(
    *, db: DbSession, user: User, organisation_id: UUID
) -> Organisation:
    # GET /v1/organisations/{organisation_id}.
    response = call_with_bearer(
        "GET", f"/v1/organisations/{organisation_id}", db=db, user=user
    )
    return Organisation.model_validate(response.json())


def admin_organisation_create(
    *, db: DbSession, user: User, body: OrganisationCreate
) -> Organisation:
    # POST /v1/admin/organisations. Idempotency-Key required (api-conventions §6).
    # 409 ORG_DUPLICATE on (lower(name), country) collision — raised as
    # OrgDuplicate via the error hierarchy.
    response = call_with_bearer(
        "POST",
        "/v1/admin/organisations",
        db=db,
        user=user,
        json=body.model_dump(mode="json"),
        idempotency_key=uuid.uuid4().hex,
    )
    return Organisation.model_validate(response.json())


def admin_organisation_update(
    *,
    db: DbSession,
    user: User,
    organisation_id: UUID,
    body: OrganisationPatch,
) -> Organisation:
    # PATCH /v1/admin/organisations/{id}. Backend refreshes denormalised
    # events.host_name / host_logo_url snapshots on name/logo_url changes.
    response = call_with_bearer(
        "PATCH",
        f"/v1/admin/organisations/{organisation_id}",
        db=db,
        user=user,
        json=body.model_dump(mode="json", exclude_none=True),
    )
    return Organisation.model_validate(response.json())


def admin_organisation_delete(
    *, db: DbSession, user: User, organisation_id: UUID
) -> None:
    # DELETE /v1/admin/organisations/{id}. Returns 204 on success. 409
    # ORG_REFERENCED if any event still links to this org — raised as
    # OrgReferenced via the error hierarchy.
    call_with_bearer(
        "DELETE",
        f"/v1/admin/organisations/{organisation_id}",
        db=db,
        user=user,
    )


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
