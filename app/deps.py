from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Role, User


def current_user(request: Request, db: DbSession = Depends(get_db)) -> User | None:
    return get_current_user(request, db)


def require_login(request: Request, db: DbSession = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


def require_admin(user: User = Depends(require_login)) -> User:
    if user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
