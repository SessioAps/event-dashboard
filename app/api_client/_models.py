from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# Auth bridge — POST /v1/admin/auth/exchange ---------------------------------


class AdminAuthExchangeRequest(BaseModel):
    user_email: EmailStr


class SessionTokenResponse(BaseModel):
    kind: str = Field(pattern="^session_token$")
    access_token: str
    user_id: UUID
    expires_at: datetime


# Events — GET /v1/admin/events ----------------------------------------------


class Event(BaseModel):
    # Mirrors the components/schemas/Event in api.yaml (line 3356).
    # NB the backend uses (start_at, duration_minutes); the local SQLAlchemy
    # Event model uses (start_at, end_at). Translation lives at the call
    # sites that bridge router state ↔ api-client payloads.
    id: UUID
    title: str
    description: str
    hero_image_url: str
    start_at: datetime
    duration_minutes: int
    venue_address: str
    venue_city: str
    venue_country: str = Field(min_length=2, max_length=2)
    host_organisation_id: Optional[UUID] = None
    host_name: str
    host_logo_url: Optional[str] = None
    genre_tags: list[str] = Field(default_factory=list)
    state: str
    created_at: datetime
    updated_at: datetime


class EventPage(BaseModel):
    items: list[Event]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None


# Events — write bodies -------------------------------------------------------


class EventCreate(BaseModel):
    # POST /v1/admin/events body. Hero is uploaded post-create via the
    # dedicated hero upload-url/confirm pair — hero_image_url at create time
    # is provided by the caller (typically a placeholder URL when the
    # workflow starts with the event then uploads the hero).
    title: str
    description: str
    hero_image_url: str
    start_at: datetime
    duration_minutes: int = Field(ge=1)
    venue_address: str
    venue_city: str
    venue_country: str = Field(min_length=2, max_length=2)
    host_organisation_id: Optional[UUID] = None
    host_name: str
    host_logo_url: Optional[str] = None
    genre_tags: list[str] = Field(default_factory=list)


class EventUpdate(BaseModel):
    # PATCH /v1/admin/events/{event_id} body. Every field optional. `state`
    # is patchable here, but the explicit cancel endpoint
    # (DELETE → adminEventCancel) is the right path for scheduled→cancelled
    # transitions; PATCH state is reserved for the rare correction case.
    title: Optional[str] = None
    description: Optional[str] = None
    hero_image_url: Optional[str] = None
    start_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1)
    venue_address: Optional[str] = None
    venue_city: Optional[str] = None
    venue_country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    host_organisation_id: Optional[UUID] = None
    host_name: Optional[str] = None
    host_logo_url: Optional[str] = None
    genre_tags: Optional[list[str]] = None
    state: Optional[str] = None


# Organisations — full shapes ------------------------------------------------


class OrgLink(BaseModel):
    label: str = Field(max_length=40)
    url: str


class Organisation(BaseModel):
    id: UUID
    name: str
    kind: str
    country: str = Field(min_length=2, max_length=2)
    logo_url: Optional[str] = None
    description: Optional[str] = None
    links: Optional[list[OrgLink]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class OrganisationPage(BaseModel):
    items: list[Organisation]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None


class OrganisationCreate(BaseModel):
    # POST /v1/admin/organisations body. logo_url not set here — upload via
    # the logo upload-url/confirm pair after create.
    kind: str
    name: str = Field(max_length=200)
    country: str = Field(min_length=2, max_length=2)
    description: Optional[str] = Field(default=None, max_length=2000)
    links: Optional[list[OrgLink]] = Field(default=None, max_length=10)


class OrganisationPatch(BaseModel):
    # PATCH /v1/admin/organisations/{id} body. All fields optional. logo_url
    # not patched directly — use logo upload-url/confirm flow.
    kind: Optional[str] = None
    name: Optional[str] = Field(default=None, max_length=200)
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    description: Optional[str] = Field(default=None, max_length=2000)
    links: Optional[list[OrgLink]] = Field(default=None, max_length=10)


# Uploads — presigned-URL pairs ----------------------------------------------


class UploadUrlRequest(BaseModel):
    # Shared body for adminEventHeroUploadUrl and adminOrganisationLogoUploadUrl.
    # Per-asset size cap is enforced by the backend (10 MB hero, 5 MB logo per
    # storage.md §4); the model is intentionally permissive so the client
    # surfaces the backend's 422 rather than double-validating with a stale cap.
    content_type: str = Field(pattern="^image/(jpeg|png|webp)$")
    size_bytes: int = Field(gt=0)


class UploadUrlResponse(BaseModel):
    upload_url: str
    confirm_token: str
    expires_at: datetime


class ConfirmRequest(BaseModel):
    confirm_token: str


class HeroConfirmResponse(BaseModel):
    hero_image_url: str


class LogoConfirmResponse(BaseModel):
    logo_url: str


# Problem envelope ------------------------------------------------------------


class FieldError(BaseModel):
    field: str
    code: str
    message: str
