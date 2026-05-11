from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Role(str, PyEnum):
    admin = "admin"
    editor = "editor"


class EventState(str, PyEnum):
    scheduled = "scheduled"
    live = "live"
    completed = "completed"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(Role), default=Role.editor, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    hero_image_url = Column(String, nullable=True)

    host_label = Column(String, nullable=False)
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
