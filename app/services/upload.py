from __future__ import annotations

import logging
from uuid import UUID

import httpx
from fastapi import UploadFile
from sqlalchemy.orm import Session as DbSession

from app.api_client.events import admin_event_hero_confirm, admin_event_hero_upload_url
from app.api_client.organisations import (
    admin_organisation_logo_confirm,
    admin_organisation_logo_upload_url,
)
from app.config import settings
from app.models import User

logger = logging.getLogger(__name__)

# Three-step server-proxied upload flow (storage.md §1):
#   1. Read file bytes server-side.
#   2. Mint a presigned URL from the Sessio backend (content-type + size).
#   3. PUT bytes directly to the storage backend at the mint's upload_url.
#   4. Confirm with the Sessio backend; receive the final URL.
#
# Bytes pass through the admin server but never traverse the Sessio backend
# JSON API. The 5-minute mint-to-PUT window is enforced by the storage
# backend (storage.md §3) — these helpers complete in well under that.
#
# entity_id is the BACKEND UUID, not the local SQLite integer PK. The bridge
# between local-int and backend-uuid IDs is a separate concern flagged in
# decisions.md and must be resolved before routers can call these helpers.


def upload_event_hero(
    *,
    db: DbSession,
    user: User,
    event_id: UUID,
    file: UploadFile,
) -> str:
    bytes_, content_type = _read_file(file)
    mint = admin_event_hero_upload_url(
        db=db,
        user=user,
        event_id=event_id,
        content_type=content_type,
        size_bytes=len(bytes_),
    )
    _put_bytes(mint.upload_url, bytes_, content_type)
    confirm = admin_event_hero_confirm(
        db=db, user=user, event_id=event_id, confirm_token=mint.confirm_token
    )
    return confirm.hero_image_url


def upload_organisation_logo(
    *,
    db: DbSession,
    user: User,
    organisation_id: UUID,
    file: UploadFile,
) -> str:
    bytes_, content_type = _read_file(file)
    mint = admin_organisation_logo_upload_url(
        db=db,
        user=user,
        organisation_id=organisation_id,
        content_type=content_type,
        size_bytes=len(bytes_),
    )
    _put_bytes(mint.upload_url, bytes_, content_type)
    confirm = admin_organisation_logo_confirm(
        db=db, user=user, organisation_id=organisation_id, confirm_token=mint.confirm_token
    )
    return confirm.logo_url


def _read_file(file: UploadFile) -> tuple[bytes, str]:
    if not file.content_type:
        raise ValueError("Upload missing Content-Type. Use a browser file picker.")
    data = file.file.read()
    file.file.seek(0)
    return data, file.content_type


def _put_bytes(upload_url: str, data: bytes, content_type: str) -> None:
    # Direct PUT to the storage backend's presigned URL. NOT the Sessio
    # backend — this call is out-of-band per storage.md §1.
    response = httpx.put(
        upload_url,
        content=data,
        headers={"Content-Type": content_type, "Content-Length": str(len(data))},
        timeout=settings.sessio_backend_timeout_seconds * 3,  # uploads can be slower than JSON
    )
    if response.status_code >= 400:
        logger.warning(
            "presigned PUT failed status=%s body=%s", response.status_code, response.text[:300]
        )
        raise RuntimeError(
            f"Storage PUT failed ({response.status_code}). The presigned URL may have "
            f"expired (5-minute window) or the byte length / content-type drifted from "
            f"the mint."
        )
