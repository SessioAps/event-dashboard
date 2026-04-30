from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DbSession

from app.auth import authenticate_user, hash_password
from app.database import get_db
from app.models import Role, User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: DbSession = Depends(get_db),
):
    user = authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password"},
            status_code=401,
        )
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(
        "register.html", {"request": request, "error": None, "values": {}}
    )


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(""),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: DbSession = Depends(get_db),
):
    email = email.strip().lower()
    full_name = full_name.strip()
    values = {"email": email, "full_name": full_name}

    def render_error(msg: str, status: int = 400):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": msg, "values": values},
            status_code=status,
        )

    # Basic validation
    if not email or "@" not in email:
        return render_error("Please enter a valid email address.")
    if len(password) < 8:
        return render_error("Password must be at least 8 characters.")
    if password != confirm_password:
        return render_error("Passwords do not match.")

    # Check for existing user
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return render_error("An account with that email already exists.", status=409)

    # Create user. First user becomes admin; everyone else is editor.
    is_first_user = db.query(User).count() == 0
    user = User(
        email=email,
        full_name=full_name or None,
        hashed_password=hash_password(password),
        role=Role.admin if is_first_user else Role.editor,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto-login the new user
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=303)