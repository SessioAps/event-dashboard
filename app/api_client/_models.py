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
