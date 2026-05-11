from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession

from app.auth import (
    consume_magic_link,
    email_in_allowlist,
    find_or_create_user,
    issue_magic_link,
    send_magic_link,
)
from app.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(
        "login.html", {"request": request, "sent_to": None, "error": None}
    )


@router.post("/login")
def login_request(
    request: Request,
    email: str = Form(...),
    db: DbSession = Depends(get_db),
):
    email = email.strip().lower()

    if email_in_allowlist(email):
        token = issue_magic_link(db, email)
        link = str(request.url_for("verify_magic_link", token=token.token))
        send_magic_link(email, link)

    # Render the same "check your inbox" page regardless of allowlist hit/miss
    # so the form does not reveal which addresses are allowed.
    return templates.TemplateResponse(
        "login.html", {"request": request, "sent_to": email, "error": None}
    )


@router.get("/login/verify/{token}", name="verify_magic_link")
def verify_magic_link(token: str, request: Request, db: DbSession = Depends(get_db)):
    consumed = consume_magic_link(db, token)
    if not consumed:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "sent_to": None, "error": "That link is invalid or expired. Request a new one below."},
            status_code=400,
        )

    user = find_or_create_user(db, consumed.email)
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
