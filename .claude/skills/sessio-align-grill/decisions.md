# event-dashboard — sessio-align-grill decisions log

> Append-only log of stack-coloured decisions captured during `/sessio-align-grill` runs in this repo. Companion to `sessio-docs/docs/products/admin/architecture/decisions.md` (which records the same sessions from the spec side via `/sessio-grill`).

## api-client — 2026-05-18 — Julieta

**Spec source:** sessio-docs@2b04df00 `docs/products/admin/architecture/scaffold-spec.md#api-client`
**Decision:** Hand-written client using `httpx` as transport. Each of the 15 admin operationIds becomes a hand-authored typed function; request/response models are hand-written Pydantic v2 classes (already the repo's idiom via `pydantic-settings`).
**Rationale:** v1 admin surface is small (15 operations) and stable; tooling cost of a generator outweighs drift-detection benefit at this size. Auth-bridge exchange, RFC-7807 problem+json envelope, `Idempotency-Key` injection on state-creating POSTs (`adminEventCreate`), and `X-Request-Id` correlation all need bespoke glue regardless of generator — hand-written keeps that glue in one place. Re-evaluate if the surface grows past ~30 operations or if mobile reuse becomes a goal.

**Layout:** package `app/api_client/` with these submodules:
- `_transport.py` — shared `httpx.Client`, base-URL + bearer injection, `Idempotency-Key` minting, `X-Request-Id` propagation, RFC-7807 problem+json → typed exception mapping.
- `_models.py` — Pydantic v2 schemas for every request/response body.
- `auth.py` — `adminAuthExchange` wrapper.
- `events.py` — the 7 event operationIds.
- `organisations.py` — the 5 admin org operationIds + the 2 public reads.

Sibling to `app/services/` (where `upload.py` lands per spec) — per ADR-0007 layering, services *compose* clients, so client cannot live under services. Mirrors `routers/` precedent in this repo. Future addition: `reports.py` if/when admin reports moderation comes into scope.

**Bearer storage:** new `BearerCache(user_id PK → users.id, bearer, expires_at)` SQLAlchemy model in `app/models/`. Bearer is minted by `adminAuthExchange` on magic-link verify and persisted server-side; transport reads on every authenticated call and re-exchanges on 401. Bearer never travels to the browser (the existing `SessionMiddleware` is a *signed*, not encrypted, cookie — keeping bearer in `request.session` would leak it). When `dashboard.db` retires, `BearerCache` collapses into a column on the future server-side session row; until then it's the simplest single-source for the rolling-30-day bearer lifecycle (per api-conventions §1.5).

**Error model:** hybrid. Base `ApiError(status: int, code: str, detail: str, errors: list[FieldError] | None)` raised on any non-2xx response after problem+json parsing. Named subclasses for the codes the admin handlers actually special-case:
- `ApiAuthError` — covers `UNAUTHENTICATED` (401) and `SESSION_EXPIRED` (401); transport catches internally to trigger one re-exchange before bubbling up.
- `OrgDuplicate` — `ORG_DUPLICATE` (409); rendered as inline form error in the org form.
- `OrgReferenced` — `ORG_REFERENCED` (409); rendered as the "unlink first" message on delete attempts.
- `EmailNotAllowlisted` — `EMAIL_NOT_ALLOWLISTED` (403); surfaced if the admin tool's allowlist drifts from the backend's.
- `ServiceTokenInvalid` — `SERVICE_TOKEN_INVALID` (401); ops-level, not user-facing; logged loudly.
- `ValidationFailed` — `VALIDATION_FAILED` (422); carries the `errors[]` array so form handlers can map back to field-level error rendering.

All other ProblemCodes raise base `ApiError` — routers can introspect `.code` when they need to.

---

## Session log

### 2026-05-18 — Julieta solo (impl-side run #1 of sessio-align-grill)

**Trigger:** SBL-0055 resolved 2026-05-16 (Arne solo). Phase E spec-blocker cleared. First sessio-align-grill run in event-dashboard.

**Detection summary:**
- ✅ `app-skeleton` aligned.
- ❌ `api-client` missing — first not-aligned; grilled in this session.
- 🟡 `admin-auth` partial (local magic-link works; no exchange-to-bearer yet).
- 🟡 `routing-skeleton`, `image-upload`, all event/hub views partial — mostly downstream of api-client.

**Decisions locked:** generator, layout, bearer storage, error model (see entries above).

**Patch emitted (pattern slice for api-client target):**
- `requirements.txt` +httpx 0.27.2
- `app/config.py` +`SESSIO_BACKEND_BASE_URL` / `SESSIO_ADMIN_SERVICE_TOKEN` / `sessio_backend_timeout_seconds`
- `app/models/__init__.py` +`BearerCache` table
- `app/api_client/{__init__,_errors,_models,_transport,auth,events}.py` — 6 new files, ~400 LOC
- `scripts/smoke_api_client.py` — end-to-end round-trip validation script

Only `adminAuthExchange` and `adminEventList` wrappers exist so far. Remaining 13 operationIds follow the same pattern: add request/response model to `_models.py`, add wrapper function calling `call_with_bearer` (or `call_service_token` for the exchange variant) in the matching resource module. The transport, error envelope, bearer cache, and idempotency-key plumbing are reusable across all of them.

**Open snag:** `sessio-backend` repo is bootstrap-only as of 2026-05-18 — one commit, zero application code. The api-client targets a contract that exists in api.yaml but has no running implementation. SBL-0055 resolved the **spec** blocker on Phase E; the **runtime** blocker (no backend service to call) remains.

**Next step before any more impl work:** Julieta to confirm with Arne whether (a) a backend service is already running somewhere not yet in git (staging/laptop/branch) or (b) Phase E genuinely waits on backend implementation. If (b), options are to park Phase E (per admin/prd.md §6 admin tool is launch-supporting, not launch-blocking — `event_dashboard` ships locally through 1.0 launch with Mattis-seeded events) or stub the two endpoints in sessio-backend for development. **No code committed in this session** — diff is uncommitted in working tree pending validation.

**Files in this run's worktree but not yet committed:**
- 3 modified: `requirements.txt`, `app/config.py`, `app/models/__init__.py`
- 8 untracked: `app/api_client/*` (6 files), `scripts/smoke_api_client.py`, this `decisions.md`

## routing-skeleton — 2026-05-19 — Julieta

**Spec source:** sessio-docs@2b04df00 `docs/products/admin/architecture/scaffold-spec.md#routing-skeleton`; admin/prd.md §7; `docs/inputs/scope.md` §5.
**URL shape:** `internal-now` has no prefix (default); `external-later` lives at `/external/*`. Internal staff are the only real audience at v1, so keeping the short URLs they already use as the default is the right tradeoff. `/`, `/events`, `/organisations` are unchanged. External stubs at `/external/`, `/external/events`, `/external/works`, `/external/sessions`, `/external/artists`, `/external/settings`.

**Code layout:** `app/routers/external/` package with one file per surface (`events.py`, `works.py`, `sessions.py`, `artists.py`, `settings.py`) plus an index handler in `__init__.py`. Each surface is a single stub `GET` returning the shared `templates/external/stub.html` parameterized by surface name + description. When v2/v3 lands and these become real, each file fills in with its own handlers without a structural refactor. Mirrors `routers/` package convention and the way scope.md §5 enumerates the surfaces.

**Auth:** all external stubs gate on `require_login` (same magic-link + cookie + allowlist as internal-now). External-later in production will have a separate auth realm (per-org tenancy), but the v1 stubs are reachable only by the same allowlisted internal staff so the existing gate is correct for the placeholder state.

**Nav:** unchanged. The base.html navbar still surfaces only `Events` and `Hub directory`. External stubs are URL-only (admins can navigate to `/external/` directly if curious) — they are not features and shouldn't compete for nav space against the live internal-now surface. Re-evaluate when external-later actually has real handlers.

### 2026-05-19 — Julieta solo (impl-side run #2 of sessio-align-grill)

**Trigger:** Continuation of run #1. Awaiting Arne on issue [SessioAps/sessio-backend#1](https://github.com/SessioAps/sessio-backend/issues/1) (Phase E runtime). Pivoted to next not-aligned target in topo order: `routing-skeleton`.

**Patch emitted:**
- 6 new files in `app/routers/external/` (package + 5 surface stubs)
- 2 new templates: `app/templates/external/{index,stub}.html`
- 2 lines added to `app/main.py` (import + include_router for the external package)

**Detection rule now passes:** both route groups exist (`internal-now` as the existing flat tree, `external-later` under `/external/`); each external surface renders a distinct stub page (different surface name + description text per route).

**Not in this slice:**
- Nav surfacing of external stubs (deferred until external-later has real handlers)
- Group-scoped auth dependency for external (when external-later becomes real, it needs its own per-org auth — file as a future grill when implementing that surface for real)
- Adding the `/external/` link to the dashboard home page (could surface as a low-key "previews" section; defer)

## image-upload — 2026-05-19 — Julieta

**Spec source:** sessio-docs@2b04df00 `docs/products/admin/architecture/scaffold-spec.md#image-upload`; admin/prd.md §4; storage.md §§1–4; api.yaml hero + logo upload-url/confirm pairs.

**Locked by spec (not grilled):**
- Sizes / types: 10 MB hero, 5 MB org logo, jpeg/png/webp (storage.md §4 table; backend enforces).
- Cropping / resizing: deferred at v1 per admin/prd §4 explicit non-feature ("Image cropping and text-truncation issues will surface via the artist app itself"). EXIF stripping + dimension normalisation are SBL-0047 (post-1.0).
- Three-step flow: mint → PUT direct to storage → confirm (storage.md §1). Mint-to-PUT window 5 min; mint-to-confirm window 10 min (storage.md §3).

**PUT path:** server-proxy at v1. Browser uploads multipart form-data to the admin tool; the admin server reads the bytes, calls the mint operation, PUTs the bytes to the presigned URL, calls confirm. Bytes pass through the admin server but never traverse the Sessio backend JSON API (storage.md §1 constraint is satisfied). For ~4 internal users uploading occasional 1–2 MB images, bandwidth cost is negligible vs the simplicity benefit of keeping the surface HTMX-native. Re-evaluate at: (a) user-count growth, (b) JS-heavier stack migration, (c) measurable bandwidth pressure.

**Helper API:** two named functions in `app/services/upload.py`:
- `upload_event_hero(*, db, user, event_id: UUID, file: UploadFile) -> str` (returns final hero_image_url)
- `upload_organisation_logo(*, db, user, organisation_id: UUID, file: UploadFile) -> str` (returns final logo_url)

Plus a private `_put_bytes(upload_url, data, content_type)` that does the direct storage PUT, and a private `_read_file(file)` that pulls bytes + content-type out of the FastAPI `UploadFile`. Adding a new asset class (e.g. user avatar) means adding a third named function, not a branch.

**Reusable UI helper:** `app/templates/_image_input.html` — Jinja2 partial parameterized by `name`, `label`, `current_url`, `max_mb`. Renders an `<input type="file" accept="image/jpeg,image/png,image/webp">` plus a thumbnail when replacing, plus the size-limit help text. Used by `events/form.html` (hero, 10 MB) and `organisations/form.html` (logo, 5 MB) once those forms are rewired.

**Cross-cutting concern surfaced — local-int ↔ backend-UUID id bridge.** The helpers take `event_id: UUID` and `organisation_id: UUID` because the api-client wrappers do (matching api.yaml's UUID v7 contract). The local SQLAlchemy models use integer auto-increment PKs. There is currently no mapping table between local int and backend UUID. This bridge is a CROSS-CUTTING concern for the entire api-client integration — `adminEventGet`, `adminEventUpdate`, `adminEventCancel`, and every Hub-directory write all need it too. **Routers cannot call the upload helpers (or any non-list api-client wrapper) until this is resolved.** Path forward: grill the id-bridge as a top-level decision (probably adding a `backend_id: UUID` column to local Event/Organisation rows populated on first mirror to backend) before tackling the events-create-edit-form / hub-directory-create-edit-form targets.

### 2026-05-19 — Julieta solo (impl-side run #3 of sessio-align-grill, continuation)

**Patch emitted:**
- `app/api_client/_models.py` +5 schemas (UploadUrlRequest, UploadUrlResponse, ConfirmRequest, HeroConfirmResponse, LogoConfirmResponse)
- `app/api_client/events.py` +2 wrappers (admin_event_hero_upload_url, admin_event_hero_confirm)
- `app/api_client/organisations.py` NEW — 2 wrappers (admin_organisation_logo_upload_url, admin_organisation_logo_confirm)
- `app/api_client/__init__.py` updated re-exports
- `app/services/upload.py` NEW — the two upload helpers + private PUT + file-read
- `app/templates/_image_input.html` NEW — reusable file-input partial

**Detection rule:** `image-upload` helper exists at `app/services/upload.py` with two callable upload functions (`upload_event_hero`, `upload_organisation_logo`); UI helper at `app/templates/_image_input.html` is reusable across the two consuming forms. **Aligned at the helper level.** Integration into the forms is part of the downstream targets (events-create-edit-form, hub-directory-create-edit-form) and is gated on the id-bridge grill.

**Updated target state after this run:**
- `api-client` advanced from pattern-slice (2 ops) to 6 ops wrapped (still partial against the 15-op surface; remaining 9 = adminEventGet/Create/Update/Cancel + adminOrganisationCreate/Update/Delete + organisationsList/Get).
- `image-upload` ✅ aligned at the helper level.
- Next not-aligned in topo order: events-list-view (partial, blocked on id-bridge + remaining adminEvent* wrappers).

**Open items:**
1. **Id-bridge grill** — must precede any router rewiring. Likely candidates: (a) `backend_id` column on local rows, populated on first push to backend; (b) full PK migration to UUID v7 (bigger change); (c) defer push integration entirely (read-only via api-client, writes stay local at v1).
2. **`SessioAps/sessio-backend#1`** — Arne hasn't responded yet. Smoke validation still parked.

## admin-auth AB4 — 2026-05-19 — Julieta

**Spec source:** sessio-docs@957e46b `docs/products/admin/architecture/decisions.md` Session 2026-05-18 (AB4) + Session 2026-05-19 (graceful posture). Mirrors AB1–AB6 ack chain from SBL-0068 resolution.

**Decision (graceful posture):** the eager exchange runs after `find_or_create_user` and before `303 → /`, but **does not block sign-in if it fails**. If `SESSIO_BACKEND_BASE_URL` or `SESSIO_ADMIN_SERVICE_TOKEN` are unset, eager is skipped (info-level log) and the lazy path in `call_with_bearer` handles bearer minting on first api-client call. If env is set but the exchange itself fails (network, 401 `SERVICE_TOKEN_INVALID`, 403 `EMAIL_NOT_ALLOWLISTED`, etc.), the failure is logged at warning-level and login proceeds — the user lands at `/` with no cached bearer; the next api-client call hits the lazy re-exchange path which will surface a usable `ApiError`.

**Why graceful, not strict:**
- `sessio-backend` is bootstrap-only as of 2026-05-19 (zero application code); strict eager would brick admin login until it ships.
- Per admin/prd §6, admin tool is launch-supporting, not launch-blocking — login must keep working when backend is down.
- Most v1 admin work doesn't actually traverse the backend yet (`dashboard.db` remains source of truth pending the SBL-0069 posture pick). A missing bearer at login mostly doesn't block anything until routers are rewired to call api-client wrappers, and even then the lazy path runs the same exchange.

**API shape:** new public helper `eager_exchange_bearer(*, db, user) -> Optional[SessionTokenResponse]` in `app/api_client/auth.py`. Returns the token on success, `None` on any graceful failure (env unset, ApiError, RuntimeError). Caller (currently only `verify_magic_link`) ignores the return value — it's just a best-effort warm-up.

**Patch shape:**
- `app/api_client/auth.py`: +`eager_exchange_bearer` function (~25 lines incl. imports, logger setup, and the env-check / try-except wrapping).
- `app/routers/auth.py`: 1 import line + 1 call line in `verify_magic_link`.

**Detection:** `admin-auth` target flips from 🟡 partial to ✅ aligned. AB1–AB6 are now fully executed in event-dashboard. SBL-0068 is structurally honored from the impl side; the resolution body in shared-backlog noted this as "the one execution gap" — that gap is now closed.

### 2026-05-19 — Julieta solo (impl-side run #4 of sessio-align-grill)

**Trigger:** SBL-0068 resolution acks left AB4 as the one execution gap; closing it now while not blocked on Arne.

**Patch emitted:**
- `app/api_client/auth.py` modified (+30 lines: logger, eager_exchange_bearer, deferred _write_cached_bearer import to mirror the cycle-avoidance pattern already in `_transport.py`).
- `app/routers/auth.py` modified (+2 lines: import + call site in `verify_magic_link`).

**Updated target state:**
- `admin-auth` ✅ aligned (was 🟡 partial — lazy-only).
- Everything else unchanged from the 2026-05-19 run #3 state.

### 2026-05-19 — Julieta solo (impl-side run #5 of sessio-align-grill)

**Trigger:** AB4 patch landed; api-client was the remaining target with significant solo-unblockable work (the 9 op wrappers post-pattern-slice). Pure spec-coverage pass to flip api-client from 🟡 partial (6/15) to ✅ aligned (15/15).

**Patch emitted:**
- `app/api_client/_models.py` +5 schemas (EventCreate, EventUpdate, OrgLink, Organisation, OrganisationPage, OrganisationCreate, OrganisationPatch).
- `app/api_client/events.py` +4 wrappers (admin_event_get, admin_event_create, admin_event_update, admin_event_cancel).
- `app/api_client/organisations.py` +5 wrappers (organisations_list, organisation_get, admin_organisation_create, admin_organisation_update, admin_organisation_delete).
- `app/api_client/__init__.py` re-exports updated — public surface now covers all 15 admin operationIds.

**No new decisions surfaced.** Each wrapper follows the established pattern (request model → `call_with_bearer` with optional Idempotency-Key on state-creating POSTs → response model). `admin_event_cancel` and `admin_organisation_delete` return `None` on 204; the transport raises ApiError on any 4xx/5xx so these are clean fire-and-forget.

**Updated target state:**
- `api-client` ✅ aligned (was 🟡 partial 6/15 — now 15/15 covering every admin operationId in api.yaml).

**Remaining partial targets** all depend on SBL-0069 (id-bridge / migration posture): events-list-view, events-create-edit-form, events-cancel-action, hub-directory-list-view, hub-directory-create-edit-form. Nothing else unblockable solo from the spec.
