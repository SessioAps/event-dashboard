from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session as DbSession

from app.api_client._models import Report, ReportPage, ReportUpdate
from app.api_client._transport import call_with_bearer
from app.models import User


def admin_reports_list(
    *,
    db: DbSession,
    user: User,
    limit: int = 20,
    cursor: Optional[str] = None,
    state: Optional[str] = None,
    target_entity_type: Optional[str] = None,
) -> ReportPage:
    # GET /v1/admin/reports
    # Default state filter on the backend is `submitted`. Cursor pagination
    # per api-conventions.md §3. Dormant at 1.0 per admin/prd §3.3 —
    # founder triages via api.yaml direct; this wrapper exists for the 1.1
    # admin reports UI.
    params: dict[str, object] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    if state is not None:
        params["state"] = state
    if target_entity_type is not None:
        params["target_entity_type"] = target_entity_type

    response = call_with_bearer(
        "GET", "/v1/admin/reports", db=db, user=user, params=params
    )
    return ReportPage.model_validate(response.json())


def admin_report_update(
    *, db: DbSession, user: User, report_id: UUID, body: ReportUpdate
) -> Report:
    # PATCH /v1/admin/reports/{report_id}. Naturally idempotent (PATCH); no
    # Idempotency-Key required. Transitions per data-model.md §reports
    # state machine. Backend bounces illegal transitions as 422.
    response = call_with_bearer(
        "PATCH",
        f"/v1/admin/reports/{report_id}",
        db=db,
        user=user,
        json=body.model_dump(mode="json", exclude_none=True),
    )
    return Report.model_validate(response.json())
