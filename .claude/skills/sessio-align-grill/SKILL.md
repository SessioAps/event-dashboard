---
name: sessio-align-grill
description: Continuous-alignment loop between this impl repo (event-dashboard) and the canonical admin scaffold-spec in sessio-docs. Pulls the spec, identifies the speaker, enumerates scaffold targets, runs detection against this repo, grills on the first not-aligned target, and emits patches. Use when starting an impl session, after a sessio-docs spec change lands, or before building/touching any scaffold target (app skeleton, api client, routing, auth, image upload, etc). Also fires on "/sessio-align-grill", "check drift", "is what I'm about to build aligned with spec".
---

# sessio-align-grill

Impl-side half of [ADR-0010](https://github.com/SessioAps/sessio-docs/blob/main/docs/adr/0010-per-impl-repo-scaffold-skill.md). Treats `sessio-docs` as the canonical brain and this repo as the admin-tool impl. The admin scaffold-spec at `docs/products/admin/architecture/scaffold-spec.md` (in sessio-docs) is the contract for what should exist here and how.

This is a **loop**, not a one-shot. Every invocation re-syncs the spec and re-checks drift. There is no terminal "scaffolded" state.

## Flow (every invocation)

1. Resolve sessio-docs path + freshness (Step 1).
2. Sync sessio-docs (Step 2).
3. Identify the speaker (Step 3).
4. Load spec context (Step 4).
5. Enumerate and topo-sort targets (Step 5).
6. Run detection per target (Step 6).
7. Grill on first not-aligned target (Step 7).
8. Emit patches or open PR (Step 8).

## Step 1 — Resolve sessio-docs path and freshness

Read `.claude/skills/sessio-align-grill/config.yaml`. Shape:

```yaml
sessio_docs_path: ../sessio-docs
freshness: pull-on-run    # pull-on-run | pinned-tag | manual
pinned_tag: ~             # only used if freshness == pinned-tag
```

If `config.yaml` is missing:
- Auto-detect `../sessio-docs/` (sibling of this repo). If it exists and contains `docs/products/admin/architecture/scaffold-spec.md`, write a config with that path and `freshness: pull-on-run`.
- Otherwise ask the speaker for the path. Validate the spec file is reachable before writing config.

## Step 2 — Sync sessio-docs

If `freshness: pull-on-run`, run `git -C {sessio_docs_path} fetch && git -C {sessio_docs_path} pull --rebase` before reading any spec content.

If the rebase is unclean, surface conflicts to the speaker and **refuse to proceed**. Aligning against a half-merged spec is worse than no alignment.

If `freshness: pinned-tag`, `git -C {sessio_docs_path} checkout {pinned_tag}` (detached) and read from there. If `manual`, read whatever is in the working tree and warn the speaker that staleness is on them.

## Step 3 — Identify the speaker

Read `git config user.name` and `git config user.email`. Match against `{sessio_docs_path}/docs/profiles/*.md` by filename, frontmatter `name`, and frontmatter `github`.

If matched, load that profile. Apply the speaker's `Grilling style` and `Pet peeves` to every grill question this skill asks.

If the matched speaker is **not** a primary impl owner of the admin scaffold-spec (Julieta or Arne), enter **cross-boundary mode**: drafts are allowed, but every emission opens a PR for primary impl owner review per ADR-0002 in sessio-docs — never a direct commit.

If no profile matches, do NOT bootstrap one here. Profile authoring is sessio-docs work — refer the speaker to `/sessio-grill` in sessio-docs and stop.

## Step 4 — Load spec context

Read these from the synced sessio-docs path:

- `docs/products/admin/architecture/scaffold-spec.md` — the canonical target list.
- All paths listed under that spec's `## Imports` section (e.g. `docs/products/admin/prd.md`, `docs/products/backend/architecture/api.yaml`, `docs/products/backend/architecture/data-model.md`, design tokens, the relevant ADRs).
- `CONTEXT.md`.
- `docs/adr/0010-per-impl-repo-scaffold-skill.md` — the contract.

The admin scaffold-spec is the source of truth for which targets exist, their detection rules, dependencies, grill prompts, and primary impl owners. **Do not invent or extend targets locally.** If reality demands a target the spec doesn't list, surface it as a question that routes back to `/sessio-grill` in sessio-docs — the fix lands upstream, not here.

## Step 5 — Enumerate and topo-sort targets

Parse the scaffold-spec's `## Scaffold targets` section. For each target capture: location, spec sources consumed, what it produces, detection rule, dependencies, grill prompts.

Compute topological order on `dependencies`. Within a ready tier, preserve the spec author's listed order. Speaker can override at runtime.

## Step 6 — Run detection per target

For each target in topo order, evaluate the spec's detection rule against this repo's working tree.

Detection rules in the spec are **vendor-neutral by design** ([ADR-0007](https://github.com/SessioAps/sessio-docs/blob/main/docs/adr/0007-service-layer-and-vendor-neutrality.md), reinforced by [ADR-0010](https://github.com/SessioAps/sessio-docs/blob/main/docs/adr/0010-per-impl-repo-scaffold-skill.md) §41). Translate them to this repo's actual stack — **FastAPI + SQLAlchemy + Jinja2 + HTMX + Tailwind** — when checking. For example:

| Spec phrasing (vendor-neutral) | event-dashboard reading |
|---|---|
| `package.json exists AND a routable index page renders` | `app/main.py` imports a FastAPI instance AND a smoke route returns 2xx |
| `Typed function per operationId` | Python module exposes one importable function per `operationId` from `api.yaml`; types are Pydantic models |
| `route groups exist and render distinct stub pages` | FastAPI router groups (`internal-now`, `external-later`) mounted; each renders a Jinja2 template |
| `Sign-in route exists; allowlist check enforced; session cookie set` | `/login` route, allowlist read, cookie set on success — all present in `app/auth/` |

Translation choices are local. Append each one to `decisions.md` (Step 7) so future runs and other contributors can see what was decided and why.

Classify each target as: `aligned`, `partial`, `missing`, or `spec-blocked` (waiting on an upstream sessio-docs gap, e.g. an undefined `api.yaml` path). Surface the full classification table to the speaker before grilling.

## Step 7 — Grill on first not-aligned target

Pick the first non-`aligned` target in topo order. Surface its current state and the spec's grill prompts. **One question at a time**, applying the speaker's grilling style and pet peeves.

Capture each accepted decision in `.claude/skills/sessio-align-grill/decisions.md` as an append-only log:

```markdown
## {target-name} — {YYYY-MM-DD HH:MM} — {speaker-firstname}

**Spec source:** sessio-docs@{commit-sha} {spec-path}#{target-anchor}
**Decision:** {one-paragraph summary}
**Rationale:** {speaker's reasoning}
```

`decisions.md` is committed — it is the running log of stack-coloured decisions and a good onboarding artefact for anyone joining the impl team.

## Step 8 — Emit patches

For an accepted decision, generate the code or scaffolding into this repo's working tree. Show the diff to the speaker. Do not commit automatically.

If the speaker is in cross-boundary mode (not Julieta or Arne), open a PR instead of committing to `main`.

Commit message format:

```
align({target-name}): {one-line summary}

Spec: sessio-docs@{commit-sha} {spec-path}
Decisions: decisions.md#{anchor}
Speaker: {speaker-firstname}
```

## Step 9 — Termination

A run ends when any of:

- Every target is `aligned` or skipped this run.
- Speaker says "stop here."
- A `spec-blocked` target with no workaround is hit and every downstream target depends on it. File the blocker as a referral to sessio-docs (`/sessio-grill`) and stop.

Skipped targets are run-local; they re-surface on the next invocation.

## Hard rules

- **One-way edits.** Never write to `{sessio_docs_path}` from this skill. Spec edits go through `/sessio-grill` in sessio-docs only — that is the bidirectional gate per [ADR-0002](https://github.com/SessioAps/sessio-docs/blob/main/docs/adr/0002-authoring-model-and-bidirectional-gates.md).
- **No silent target invention.** If reality demands a target the spec doesn't list, refer to sessio-docs. Don't grow the target set locally.
- **Vendor-neutral spec, stack-coloured impl.** Don't push stack choices upstream. Capture them in `decisions.md` here.
- **Pull, don't sync-push.** This skill never pushes to sessio-docs.

## Cross-references

- `sessio-docs/docs/adr/0010-per-impl-repo-scaffold-skill.md` — the contract this skill implements.
- `sessio-docs/docs/products/admin/architecture/scaffold-spec.md` — the canonical target list.
- `sessio-docs/.claude/skills/sessio-grill/` — the upstream-side companion; spec edits go through there.
