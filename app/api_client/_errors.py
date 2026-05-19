from __future__ import annotations

from typing import Optional

from app.api_client._models import FieldError


class ApiError(Exception):
    # Base for every non-2xx response from the backend, parsed from the
    # RFC-7807 problem+json envelope per api-conventions.md §2.

    def __init__(
        self,
        status: int,
        code: str,
        detail: str,
        errors: Optional[list[FieldError]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        self.status = status
        self.code = code
        self.detail = detail
        self.errors = errors
        self.request_id = request_id
        super().__init__(f"{status} {code}: {detail}")


# Specialised subclasses for codes the admin handlers catch by type.
# Everything else raises base ApiError; routers introspect .code if needed.

class ApiAuthError(ApiError):
    # UNAUTHENTICATED / SESSION_EXPIRED (401). Transport catches internally
    # to trigger one re-exchange before bubbling up.
    pass


class ServiceTokenInvalid(ApiError):
    # SERVICE_TOKEN_INVALID (401) on the exchange endpoint. Ops-level error
    # — the AdminServiceToken env var is bad. Not user-facing; log loudly.
    pass


class EmailNotAllowlisted(ApiError):
    # EMAIL_NOT_ALLOWLISTED (403) on exchange. Backend's allowlist disagrees
    # with the admin tool's. Surfaces if admin_emails drifts from backend.
    pass


class OrgDuplicate(ApiError):
    # ORG_DUPLICATE (409) on org create/update — (lower(name), country) clash.
    # Rendered inline on the org form.
    pass


class OrgReferenced(ApiError):
    # ORG_REFERENCED (409) on org delete — at least one event still links to
    # this org. Rendered as the "unlink first" message.
    pass


class ValidationFailed(ApiError):
    # VALIDATION_FAILED (422). `.errors` carries the FieldError array so form
    # handlers can render per-field messages.
    pass


_CODE_TO_CLASS: dict[str, type[ApiError]] = {
    "UNAUTHENTICATED": ApiAuthError,
    "SESSION_EXPIRED": ApiAuthError,
    "SERVICE_TOKEN_INVALID": ServiceTokenInvalid,
    "EMAIL_NOT_ALLOWLISTED": EmailNotAllowlisted,
    "ORG_DUPLICATE": OrgDuplicate,
    "ORG_REFERENCED": OrgReferenced,
    "VALIDATION_FAILED": ValidationFailed,
}


def error_for(
    status: int,
    code: str,
    detail: str,
    errors: Optional[list[FieldError]] = None,
    request_id: Optional[str] = None,
) -> ApiError:
    cls = _CODE_TO_CLASS.get(code, ApiError)
    return cls(status=status, code=code, detail=detail, errors=errors, request_id=request_id)
