import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.models import MagicLinkToken, User

logger = logging.getLogger(__name__)


def email_in_allowlist(email: str) -> bool:
    return email.strip().lower() in settings.admin_emails


def issue_magic_link(db: DbSession, email: str) -> MagicLinkToken:
    token = MagicLinkToken(
        token=secrets.token_urlsafe(32),
        email=email.strip().lower(),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.magic_link_ttl_minutes),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def send_magic_link(email: str, link: str) -> None:
    # TODO(deploy): swap console-print for a real transactional sender
    # (Resend / SMTP) once event_dashboard is deployed for the 4-person team.
    # Locally on a dev machine, the team grabs the link from server logs.
    logger.warning("MAGIC LINK for %s -> %s", email, link)
    print(f"\n  ✉  Magic link for {email}\n     {link}\n")


def consume_magic_link(db: DbSession, token_str: str) -> Optional[MagicLinkToken]:
    token = db.query(MagicLinkToken).filter(MagicLinkToken.token == token_str).first()
    if not token:
        return None
    if token.used_at is not None:
        return None
    if token.expires_at < datetime.utcnow():
        return None
    token.used_at = datetime.utcnow()
    db.commit()
    return token


def find_or_create_user(db: DbSession, email: str) -> User:
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(request: Request, db: DbSession) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()
