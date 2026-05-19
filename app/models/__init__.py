from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class EventState(str, PyEnum):
    scheduled = "scheduled"
    live = "live"
    completed = "completed"
    cancelled = "cancelled"


class OrganisationKind(str, PyEnum):
    org = "org"
    publisher = "publisher"
    label = "label"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BearerCache(Base):
    # Server-side cache of the per-user backend bearer minted by
    # `adminAuthExchange` (api-conventions.md §1.10). One row per admin user.
    # Lifecycle:
    #   1. Magic-link verify → call exchange → upsert row.
    #   2. Every authenticated api-client call reads this row.
    #   3. On 401 from backend → invalidate + re-exchange once.
    # When dashboard.db retires, this collapses into a column on whatever
    # server-side session row replaces SessionMiddleware.
    __tablename__ = "bearer_cache"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    bearer = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(Enum(OrganisationKind), nullable=False, index=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    links = Column(JSON, default=list, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_by = relationship("User")

    __table_args__ = (
        Index("uq_org_name_country", func.lower(name), country, unique=True),
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    hero_image_url = Column(String, nullable=True)

    host_organisation_id = Column(
        Integer, ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    host_name = Column(String, nullable=False)
    host_logo_url = Column(String, nullable=True)

    venue_name = Column(String, nullable=True)
    venue_city = Column(String, nullable=False)
    venue_country = Column(String, nullable=False)
    venue_address = Column(Text, nullable=True)

    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)

    state = Column(Enum(EventState), default=EventState.scheduled, nullable=False)

    genre_tags = Column(JSON, default=list, nullable=False)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    created_by = relationship("User")
    host_organisation = relationship("Organisation")
