# Pending grills (not yet locked)

> Open items that need a `/sessio-grill` session in `sessio-docs` to lock. Once locked, the decisions move into `decisions.md` (this skill's locked log) AND `sessio-docs/docs/products/admin/architecture/decisions.md` (the upstream-side mirror Arne co-owns).

---

## PG-01 — Phase E migration posture (local-int ↔ backend-UUID id-bridge)

**Raised:** 2026-05-19 (run #3, image-upload target).
**Surfaced because:** the image-upload helpers (`upload_event_hero`, `upload_organisation_logo`) take backend UUIDs, but the local SQLAlchemy `Event` / `Organisation` models use integer auto-increment PKs. Every non-list api-client wrapper has the same gap (`adminEventGet/Update/Cancel`, `adminOrganisationCreate/Update/Delete`, the four upload-url/confirm pairs).
**Routes the cross-boundary call to:** Arne (architecture co-owner of `docs/products/admin/architecture/`; sole owner of `docs/products/backend/architecture/`).
**Recommended pick:** Posture α (defer to post-launch cutover).

### Spec sources bearing on the decision

- `admin/prd.md` §6 *v1 internal — timing.* Lock: "Aim: live and usable by Mattis pre-launch (before 2026-05-31)." Explicit posture: admin tool is **launch-supporting, not launch-blocking**. `event_dashboard` ships locally through 1.0 launch; Mattis-seeded events at 1.0 are local-only unless Arne raw-DB-inserts to backend as a manual fallback.
- `admin/architecture/decisions.md` Q1 *Data path lock* (2026-05-11). End state: "Writes via the backend platform service. `dashboard.db` is a placeholder until the API client is built." Defines the destination, leaves the migration sequencing open.
- `admin/architecture/decisions.md` 2026-05-13 session, Phase D shape. v1 placeholder patterns flagged with `# TODO(backend)`: denormalised host-snapshot refresh on org rename, and event-cancellation push fan-out. Both wait on backend service.
- `admin/architecture/decisions.md` 2026-05-15 session — Path X chosen ("Phase E lands post-launch as a single clean refactor once the gaps close"). This pre-grill is asking: is **single clean refactor** still the right framing, or has anything changed since 05-15 that recommends a different posture?
- `shared-backlog.md` SBL-0055 *Phase E backend endpoint gaps for the admin tool [RESOLVED 2026-05-16]* — closed the 5 api.yaml gaps. Note at the bottom: "**No SBL filed for Phase E timing — it's your call when to do it.**" So timing is Julieta's owned call; Arne is consulted, not gating.
- `SessioAps/sessio-backend` repo state as of 2026-05-19 — **one commit, zero application code**. There is no running backend to point a smoke test at. (Issue [#1](https://github.com/SessioAps/sessio-backend/issues/1) raised 2026-05-18, awaiting Arne's response.)

### Three postures considered

#### Posture α — Ship local through 1.0; cut over post-launch (**recommended**)

- **v1 behaviour:** `dashboard.db` remains source of truth for events + organisations. The api-client code that landed in `ca50d3a` and `b0d6c87` exists but is NOT wired into routers; it sits ready for activation.
- **At launch:** Mattis-seeded events are local-only. Per `admin/prd.md` §6 fallback, Arne raw-DB-inserts them to backend if/when mobile artist app needs to see them.
- **Cutover trigger:** post-launch (suggested: early Phase 1.1, file as an SBL when ready). A single migration ports local rows to backend, routers swap to api-client, `dashboard.db` retires.
- **Concrete impact:**
  - **Code today:** zero further work needed before launch. The api-client + image-upload helpers + decisions log are all forward-investments.
  - **Launch readiness:** unaffected — the tool ships today, no new risk.
  - **Mobile artist app at 1.0:** does not see admin-seeded events unless Arne manually mirrors. Acceptable per admin/prd §6 since launch volume is small.
  - **Post-launch cost:** one focused refactor session (estimated 1–2 days) covering: rip out SQLAlchemy CRUD, wire routers to api-client, write a one-shot migration script, retire dashboard.db.
- **Why this is recommended:**
  - Matches admin/prd §6 framing directly.
  - Posture γ (cut over now) is technically impossible — backend doesn't exist.
  - Posture β (dual-write bridge) needs decisions about reconciliation/retry/failure semantics that depend on observing backend behaviour we can't observe yet.
  - Defers the decision until backend exists and a real migration tool can be designed informed by reality.

#### Posture β — Dual-write with a `backend_id` column

- **Schema change:** add `Event.backend_id: UUID nullable` and `Organisation.backend_id: UUID nullable`.
- **Write path:** on create, write local row, then call `adminEventCreate` / `adminOrganisationCreate`, populate `backend_id` from the response. On update/cancel/delete, mirror via `backend_id`. Reads stay local.
- **Cutover later:** flip reads to api-client; remove dual-write; delete local rows.
- **Concrete impact:**
  - **Code today:** ~30 lines added per write-path handler; 2 new SQLAlchemy columns; 1 alembic migration; **a reconciliation strategy decision** (see below).
  - **Reconciliation strategy:** what happens when local commit succeeds but backend POST fails (network error, backend down, 422)? Options: synchronous-fail (roll back local), queue+retry (background job re-tries pending pushes), nightly job (sweep `backend_id IS NULL` rows). All three need a design pass; none can be specced without observing backend behaviour.
  - **Launch readiness:** at risk — every write-path handler grows; testing covers two backends; new failure modes; new infra (queue/job) potentially.
  - **Mobile artist app at 1.0:** sees admin-seeded events as they're created (modulo reconciliation lag).
- **Why not recommended:** premature given backend doesn't exist; introduces failure modes the team has no operational experience handling; pulls scope into the pre-launch window that admin/prd §6 explicitly defers.

#### Posture γ — Cut over now: writes go directly to backend; local rows deleted

- **Schema change:** delete `Event` and `Organisation` SQLAlchemy models. Keep `User`, `MagicLinkToken`, `BearerCache` (admin auth is local).
- **All routers** call api-client exclusively. List, detail, create, edit, cancel — every operation is a backend round-trip.
- **Concrete impact:**
  - **Code today:** major refactor. Every events.py and organisations.py handler rewritten. Local Event/Organisation data wiped or migrated up-front.
  - **Launch readiness:** **launch-blocking** — event-dashboard becomes non-functional if backend is down or not yet implemented. Backend currently has zero application code.
  - **Risk vs 2026-05-31 TestFlight cut / 2026-06-01 launch:** very high. Requires Arne to deliver a runnable backend at minimum the 6 admin operationIds the tool needs before 2026-05-25 scope freeze.
- **Why not recommended:** flips admin/prd §6 from "launch-supporting" to "launch-blocking"; depends on backend implementation that doesn't exist; high risk vs short window.

### Specific questions for Arne

(In priority order; each is a single fork.)

1. **Posture pick.** α, β, or γ? Recommended α.
2. **If α:** what triggers the post-launch cutover — a calendar date (early Phase 1.1), an SBL, an explicit Mattis ask, backend-ready signal? Owner of the cutover decision = ?
3. **At 1.0 launch:** does Mattis need backend-side events for the artist app's launch demo, or are local-only events fine for the 4-person internal team's seeding workflow? (Routes follow-up SBL if Mattis is in the loop.)
4. **Post-launch migration script ownership:** Julieta writes (within her impl mandate)? Arne writes (cross-cutting)? Both pair on it?
5. **Backend runtime status** (cross-references [`#1`](https://github.com/SessioAps/sessio-backend/issues/1)) — independent of posture, when does sessio-backend become runnable? Needed for the api-client smoke test regardless of which posture lands.

### What stays unblocked while waiting

- **api-client target completion** — emitting the remaining 9 op wrappers (`adminEventGet/Create/Update/Cancel + adminOrganisationCreate/Update/Delete + organisationsList/Get`) is pure spec coverage; no router integration. Lets api-client flip from partial to fully aligned. Doesn't depend on the posture call.
- **admin-auth eager exchange** — wire `admin_auth_exchange` into `verify_magic_link` so config errors surface at login rather than first api-client use. ~15 lines. Doesn't depend on the posture call.
- **README update** — current `Phase D blocked on the backend existing` line is stale; refresh to point at the current state.

### Cross-references

- This skill's locked decisions log: `decisions.md` (api-client, routing-skeleton, image-upload entries).
- Upstream mirror (when this pre-grill turns into a locked decision): `sessio-docs/docs/products/admin/architecture/decisions.md` — Julieta + Arne co-owned; updates go via `/sessio-grill` in sessio-docs.
- The skill that authored this file: `.claude/skills/sessio-align-grill/SKILL.md`.
