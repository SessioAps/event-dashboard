from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.deps import require_login
from app.models import Event, Organisation, OrganisationKind, User

router = APIRouter(prefix="/organisations")
templates = Jinja2Templates(directory="app/templates")


def _parse_links(raw: str) -> list[str]:
    return [u.strip() for u in raw.splitlines() if u.strip()]


def _get_or_404(db: DbSession, org_id: int) -> Organisation:
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")
    return org


@router.get("")
def list_organisations(
    request: Request,
    kind: str | None = None,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    q = db.query(Organisation)
    if kind in {k.value for k in OrganisationKind}:
        q = q.filter(Organisation.kind == kind)
    orgs = q.order_by(Organisation.kind, func.lower(Organisation.name)).all()
    return templates.TemplateResponse(
        "organisations/list.html",
        {"request": request, "orgs": orgs, "active_kind": kind, "user": user},
    )


@router.get("/new")
def new_organisation_form(request: Request, user: User = Depends(require_login)):
    return templates.TemplateResponse(
        "organisations/form.html", {"request": request, "org": None, "user": user, "error": None}
    )


@router.post("")
def create_organisation(
    request: Request,
    kind: str = Form(...),
    name: str = Form(...),
    country: str = Form(...),
    logo_url: str = Form(""),
    description: str = Form(""),
    links: str = Form(""),
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    org = Organisation(
        kind=OrganisationKind(kind),
        name=name.strip(),
        country=country.strip().upper(),
        logo_url=logo_url.strip() or None,
        description=description.strip() or None,
        links=_parse_links(links),
        created_by_id=user.id,
    )
    db.add(org)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            "organisations/form.html",
            {
                "request": request,
                "org": None,
                "user": user,
                "error": f"An organisation named '{name}' already exists in {country.upper()}.",
            },
            status_code=409,
        )
    return RedirectResponse(url="/organisations", status_code=303)


@router.get("/{org_id}/edit")
def edit_organisation_form(
    org_id: int, request: Request, db: DbSession = Depends(get_db), user: User = Depends(require_login)
):
    org = _get_or_404(db, org_id)
    return templates.TemplateResponse(
        "organisations/form.html", {"request": request, "org": org, "user": user, "error": None}
    )


@router.post("/{org_id}/edit")
def update_organisation(
    org_id: int,
    request: Request,
    kind: str = Form(...),
    name: str = Form(...),
    country: str = Form(...),
    logo_url: str = Form(""),
    description: str = Form(""),
    links: str = Form(""),
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    org = _get_or_404(db, org_id)
    org.kind = OrganisationKind(kind)
    org.name = name.strip()
    org.country = country.strip().upper()
    org.logo_url = logo_url.strip() or None
    org.description = description.strip() or None
    org.links = _parse_links(links)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            "organisations/form.html",
            {
                "request": request,
                "org": org,
                "user": user,
                "error": f"An organisation named '{name}' already exists in {country.upper()}.",
            },
            status_code=409,
        )
    # TODO(backend): when the backend platform service exists, renaming an org
    # triggers a refresh of denormalised host_name / host_logo_url on every
    # event referencing this org (per SBL-0031 / decisions.md Q7). For v1
    # placeholder, do it locally:
    event_count = (
        db.query(Event).filter(Event.host_organisation_id == org.id).update(
            {"host_name": org.name, "host_logo_url": org.logo_url}
        )
    )
    if event_count:
        db.commit()
    return RedirectResponse(url="/organisations", status_code=303)


@router.post("/{org_id}/delete")
def delete_organisation(
    org_id: int,
    request: Request,
    db: DbSession = Depends(get_db),
    user: User = Depends(require_login),
):
    org = _get_or_404(db, org_id)
    in_use = db.query(Event).filter(Event.host_organisation_id == org.id).count()
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {in_use} event(s) reference this organisation as host. Unlink first.",
        )
    db.delete(org)
    db.commit()
    return RedirectResponse(url="/organisations", status_code=303)
