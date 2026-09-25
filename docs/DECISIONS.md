# Implementation decisions log

Records choices made where the specification did not dictate an exact detail.
Architecture itself (Next.js + FastAPI + Supabase + Appwrite + n8n) is locked
and not re-litigated here.

## Phase 1 — Foundation

- **Frontend scaffold**: `create-next-app` with TypeScript, Tailwind, ESLint,
  App Router, `src/` directory, `@/*` import alias. Reason: matches the
  architecture spec exactly and is the standard, unmodified Next.js starter
  so any engineer can onboard without extra explanation.
- **Backend package layout**: `app/api/v1`, `app/core`, `app/db`,
  `app/models`, `app/schemas`, `app/services/connectors`, `app/tests`.
  Reason: keeps versioned API routes separate from domain models/schemas and
  gives each mock government connector its own module under
  `services/connectors/`, matching the "common connector interface" required
  in Master Prompt section 12.
- **Config management**: `pydantic-settings` reading from `.env`, with a
  single cached `Settings` object (`get_settings()`), rather than reading
  `os.environ` ad hoc. Reason: strict validation is a security requirement
  (Master Prompt section 14) and this is the standard FastAPI pattern for it.
- **Python version**: 3.12 (available on this machine via the `py` launcher).
  Requirements pinned to versions compatible with 3.12.
- **n8n**: run via Docker Compose (`infra/n8n/docker-compose.yml`) rather than
  a hosted/paid instance, so the project stays runnable on a clean machine
  per the Definition of Done. Workflow JSON exports will live in
  `infra/n8n/workflows/`.
- **CORS**: locked to `http://localhost:3000` in development; will be
  extended via `.env` for any deployed frontend origin.

## Phase 2 — Data model + orchestration core

- **Dependency graph shape for the signature demo**: identity, domicile,
  caste and income certificates are modeled as *independent* documents
  (no depends_on edges between them). Only `education_scholarship`
  carries a dependency, on `income_certificate`. Reason: an earlier draft
  wired income/caste to depend on identity_verification; a failing unit
  test (`test_signature_demo_end_to_end`) exposed that this made income
  auto-promote to READY before submission, which contradicts the demo
  narrative ("Income ✕ MISSING" while Identity/Domicile show verified).
  Fixed in both the in-memory graph
  (`backend/app/services/dependency_graph.py`) and the DB seed
  (`0002_seed_catalog.sql`) — kept consistent deliberately.
- **Demo mode is in-memory, not Supabase-backed**: `app/services/demo_store.py`
  runs the real `JourneyOrchestrator` and `RevenueMockConnector` but keeps
  state in a process-local singleton rather than writing to Supabase.
  Reason: Definition of Done requires the app to run on a clean machine
  without paid third-party dependencies; the `/demo` route must work
  before any Supabase/Appwrite project exists. Production (non-demo)
  citizen data still goes through Supabase per the locked architecture —
  this is a demo-only shortcut, not a replacement for real persistence.
- **Migration verification method**: ran `0001_init.sql` and
  `0002_seed_catalog.sql` against a disposable `postgres:16` Docker
  container (with a minimal stub `auth.users`/`auth.uid()` standing in
  for Supabase's own auth schema) rather than trusting the SQL by
  inspection. Confirmed: all 16 tables + 5 enums + RLS policies created
  with zero errors, RLS actually enabled (`relrowsecurity = t`) on
  citizen-owned tables, and the dependency graph read back from the
  database matches the in-memory graph exactly. Container was torn down
  after verification — this was a one-off check, not a running service.

## Phase 3 — Repository abstraction, service layer, real /demo frontend

- **Layering**: `app/api/v1/demo.py` (HTTP) -> `app/services/journey_service.py`
  (orchestration + persistence coordination) -> `app/repositories/interfaces.py`
  (ports) -> `app/repositories/local/*.py` (JSON-file adapter). The
  `JourneyOrchestrator` itself (business logic — consent gating,
  dependency resolution, cascading unlock) was **not** touched or
  simplified; it still knows nothing about repositories or JSON files.
  Swapping in Supabase later means writing `SupabaseApplicationRepository`
  and `SupabaseAuditLogRepository` against the same
  `app/repositories/interfaces.py` contracts and changing two branches in
  `app/core/container.py` — no orchestrator or API code changes.
- **Domain object vs. persisted record are different types on purpose**:
  `Journey`/`JourneyStep`/`Consent` (dataclasses, carry a live
  `DependencyGraph`) vs. `ApplicationRecord`/`StepRecord`/`ConsentRecord`
  (Pydantic, JSON-serializable, store only `life_event_code`).
  `app/services/journey_mapper.py` converts between them, resolving the
  graph via a small registry (`app/services/dependency_graph.GRAPH_REGISTRY`)
  keyed by the same life-event codes seeded in the database. A round-trip
  test (`test_journey_mapper.py`) proves this loses no state.
- **Connector instances stay process-wide singletons, not persisted**:
  `RevenueMockConnector` holds its own request registry in memory
  (`app/core/container.get_revenue_connector`). In production a connector
  calls a real external department API per request and has no local
  state to persist; the mock's in-memory registry is a demo-scope
  stand-in for that, not a gap in the persistence layer. Restarting the
  backend mid-journey (after submit, before approve) loses the
  connector's ability to look up that specific request — acceptable for
  a live demo (one continuous process) and called out here rather than
  silently accepted.
- **Audit trail is append-only across resets, deliberately**: `/demo/reset`
  creates a fresh `journey.reset` audit entry but never clears prior
  entries for that application id. An audit trail that a "reset" button
  could erase would defeat its purpose; verified this by resetting mid-way
  through a run in the browser and confirming the full history stayed.
- **Static type checking**: added `mypy` (strict-ish config in
  `pyproject.toml`: `disallow_untyped_defs`, `check_untyped_defs`,
  `warn_return_any`). Runs clean across all 42 backend source files.
- **A real bug caught by actually using the feature in a browser, not
  just running pytest**: `JourneyOrchestrator.start_journey` appended
  "Journey started for citizen X" to the timeline *after* calling
  `_recompute_dependents`, so the rendered timeline showed
  "education_scholarship -> blocked" before "Journey started" —
  contradicting its own narrative. Existing tests didn't catch this
  because none asserted timeline *order*, only membership. Fixed by
  moving the append before the recompute call, and added a regression
  assertion (`test_signature_demo_end_to_end`, item 1b) plus verified the
  fix live via the browser tool against the running frontend + backend.
- **Test isolation for file-backed repositories**: added an autouse
  pytest fixture (`app/tests/conftest.py`) that points `LOCAL_DATA_DIR`
  at a fresh `tmp_path` and clears every `container.py` `lru_cache` per
  test — without it, tests would read/write the same JSON files and
  leak state into each other.

## Phase 4 — Generic webhook boundary, n8n workflows, eligibility, profile/vault

- **One event-processing path, not two**: `POST /api/v1/webhooks/n8n/{event}`
  (`app/api/v1/webhooks.py`) resolves a bare `external_reference` back to
  its `(application_id, service_code)` via a new repository method
  (`ApplicationRepository.find_by_step_external_reference`), then calls
  the exact same `JourneyService.receive_connector_event` the `/demo`
  approve action calls. The only new parameter is `source`, used purely
  for audit-trail labeling (`"demo_action"` vs.
  `"n8n_webhook:<event>"`) — no orchestration behavior branches on it.
  Proved by `test_webhooks.py::test_webhook_approval_unlocks_scholarship_same_as_demo_action`.
- **Webhook auth**: a shared-secret header (`x-setu-webhook-secret`),
  checked only when `N8N_WEBHOOK_SECRET` is configured — local dev with
  no secret set stays open, matching the existing `.env.example` default.
  This is a shared-secret, not a signed payload; upgrading to HMAC
  signature verification is a reasonable later hardening step once a
  real department/n8n integration exists, not needed for the mock
  connectors driving the demo.
- **Non-terminal statuses are acknowledged, not applied**: only
  `"approved"`/`"rejected"` drive a state transition; anything else
  (e.g. `"submitted"`) returns `accepted_status: "ignored"` and touches
  no state. Prevents an intermediate department-system status update
  from being misread as a final outcome.
- **n8n workflows verified against a real, disposable n8n instance**, not
  just written by hand: `docker compose up`, `n8n import:workflow` on
  both JSON files (each needed a top-level `id` field the CLI importer
  requires — added), `n8n list:workflow` confirmed both registered, and
  `n8n export:workflow` round-tripped one back out with every node
  intact. Container + volume torn down after. Only 2 workflows, not one
  per bullet in the spec's requirement list — dependency re-evaluation is
  intentionally *not* a separate n8n step (see below), and a fourth
  "notification" workflow would have been a no-op node with nothing to
  connect it to, so its logic is folded into the two real workflows
  instead of padding the count.
- **Dependency re-evaluation stays inside the backend webhook call,
  not a separate n8n node**: splitting it into its own async n8n step
  would let a client read a state where the connector step is "approved"
  but dependents haven't yet been recomputed — a real inconsistent-read
  window. Keeping it atomic with the state write costs nothing (it's a
  fast in-process call) and removes an entire class of race condition.
- **Eligibility engine is a pure function, not a Journey method**:
  `app/services/eligibility.py:evaluate(life_event_code, graph,
  verified_service_codes)` mirrors the same dependency-blocking logic
  `JourneyOrchestrator._recompute_dependents` uses, but deliberately
  doesn't call into the orchestrator — eligibility is checked *before*
  any Application/Consent exists, so there's no Journey object for it to
  operate on yet. `EligibilityEvaluateRequest` takes an explicit
  `verified_service_codes: list[str]` rather than a citizen_id looked up
  against a live profile store, because that store doesn't exist yet
  (see below) — wiring eligibility to the vault is later work.
- **Citizen profile + document vault use opaque string citizen_ids**,
  not UUIDs, consistent with every other identifier in the app so far
  (`demo-citizen-priya-deshmukh` etc.) — there's no Supabase Auth issuing
  real UUIDs yet. `CitizenProfileView`/`DocumentView` will need a pass
  when real auth arrives, but the repository/service shape underneath
  won't change.
- **Vault upload enforces the security spec's MIME allow-list and 5MB
  limit today**, via `LocalDiskDocumentStorage` (already built in Phase
  3) — not deferred until Appwrite exists. Tested with an oversized file
  and a disallowed MIME type, both rejected with 422.
- **Profile and vault are not yet wired to eligibility or the journey
  orchestrator** — `verified_service_codes` for eligibility is still
  caller-supplied. Connecting "does this citizen's vault contain a
  verified income certificate" to the eligibility engine and to
  `start_or_reset_journey`'s `already_verified_service_codes` is the
  natural next step once there's a reason to (e.g. a non-demo journey).

## Phase 5 — System integration: profile/vault/eligibility/orchestrator as one system

- **Requirement graph generalized from single-dependency to
  multi-requirement**: `DependencyEdge(depends_on_service_code: str |
  None)` became `ServiceRequirement(requires: list[str])`. The SQL
  schema (`service_dependencies`) was already a many-to-many junction
  table — this just makes the in-memory graph match what the database
  could already express. `education_scholarship` now genuinely requires
  `[identity_verification, domicile_certificate, income_certificate]`,
  matching the example given for this phase, instead of a single
  artificial edge to `income_certificate`. `JourneyOrchestrator`'s
  `_recompute_dependents` and `eligibility.evaluate` both walk the same
  `requirements_of()` — one definition of "what does X require", read by
  both, per the explicit instruction not to build a parallel state
  machine.
- **Document lifecycle is real**: `DocumentStatus` became
  `UPLOADED -> UNDER_REVIEW -> VERIFIED / REJECTED (/ EXPIRED)`, replacing
  the old `PENDING/ACTION_NEEDED` vocabulary. `DocumentVaultService`
  gained `submit_for_review`/`verify`/`reject`, each a real, persisted
  transition (`InvalidDocumentTransitionError` if called out of order —
  tested: verifying a document still in `UPLOADED` is rejected).
- **No caller-supplied `verified_service_codes` for the normal flow**:
  `GET /citizens/{id}/eligibility/{life_event_code}` computes the
  verified set itself, from `app/services/vault_eligibility.py`. The old
  `POST /eligibility/evaluate` was renamed to `/eligibility/evaluate-raw`
  and is documented as test-only — never wired into `/demo` or any
  citizen-facing call.
- **Two verified-set functions, not one, and that's deliberate**:
  `verified_service_codes_from_vault` (vault documents only) seeds a
  *new* journey's starting state — a fresh journey should only inherit
  pre-verified documents, not whatever a previous run happened to verify
  through a connector. `verified_service_codes_for_citizen` (vault +
  every application's already-VERIFIED steps) backs the citizen-facing
  eligibility view, so it doesn't go stale the moment a connector
  approval lands mid-journey. A live browser session with income
  verified via the Revenue connector, but eligibility still reading
  "Income Certificate — not started", is exactly the bug that using the
  vault-only function everywhere would have caused — caught by actually
  clicking through the demo (see below), not by pytest, and now covered
  by `test_citizen_eligibility_reflects_connector_verified_state_not_only_vault`.
- **Vault verification cascades through the orchestrator's existing
  event path, not a new one**: `JourneyService.sync_verified_document`
  finds any of the citizen's applications with that service_code sitting
  in `NOT_STARTED`/`BLOCKED` and calls the exact same
  `receive_connector_event` a webhook uses (`source="vault_verification"`).
  `app/services/vault_integration.py` is the thin coordinator that calls
  `DocumentVaultService.verify()` then this — kept separate so neither
  service depends on the other directly.
- **The signature demo's `caste_certificate` is deliberately left
  UPLOADED-but-unreviewed on every reset**, not pre-verified like
  identity/domicile — it's the one thing `/demo` walks through
  "Submit for Review" -> "Verify" live, showing the vault -> eligibility
  -> journey cascade on a real, non-required step without touching the
  income/scholarship path priority 7 required to keep passing unchanged.
  Because `education_scholarship` doesn't require caste, this is
  additive and risk-free to the existing signature flow.
- **`GET /admin/metrics` is real, computed groundwork, not a dashboard**:
  every number (`bottleneck_service_codes`, department pending/rejected
  counts, SLA at-risk/breached counts, blocked-journey details) is
  derived by walking actual `ApplicationRecord`s through the same
  `DependencyGraph`/SLA logic used everywhere else — no separately
  tracked counters that could drift from reality. No admin UI yet, per
  instruction not to build a decorative dashboard before the data behind
  it is real.
- **Citizen-facing surface scoped to 2 real pages, not "dozens"**: a new
  `/` home page (replacing the untouched Next.js boilerplate that was
  still live through Phase 4 — a real gap, fixed here) plus the
  significantly expanded `/demo` page, which now itself covers profile,
  vault, eligibility, consent, dependency graph, connector/webhook
  status, unified timeline, SLA and audit trail as sections of one
  coherent citizen journey experience — deliberately not split into
  separate `/profile`, `/vault`, `/consent`, `/timeline` routes yet,
  per the explicit instruction against dozens of disconnected pages.
- **A second real bug found only by clicking through the browser, not by
  pytest**: `refreshAll()` originally fetched `getJourney()` (which
  lazily seeds the vault on first load) in the same `Promise.all` as the
  vault/eligibility calls. The vault-dependent requests could race ahead
  of the seeding transaction and read an empty vault, showing
  "Identity Verification — Not started" in the Eligibility panel while
  the Dependency Graph panel correctly showed "Verified" one section
  below — a visible, confusing inconsistency a judge would have seen.
  Fixed by sequencing: `await getJourney()` first, *then*
  `Promise.all([documents, eligibility, auditLog])`.

## Phase 6 — Productization: real product shell + judge experience

Backend additions were kept deliberately minimal — this phase is framed
as frontend/product work, and the instruction was explicit: don't expand
backend architecture unless a real product feature needs it. Everything
below is additive; the orchestrator, repository/storage abstraction and
event-processing path built in Phases 3-5 are untouched.

- **New generic (non-demo) backend surface**, needed because every
  product page (`/services`, `/journeys`, `/journeys/[id]`, `/vault`,
  `/profile`) needs data for *any* citizen and *any* life event, not just
  the fixed demo citizen the `/demo/*` endpoints are scoped to:
  - `GET/POST /citizens/{id}/journeys`, `GET /journeys/{id}`,
    `POST /journeys/{id}/consent/{service}[/revoke]`,
    `POST /journeys/{id}/submit/{service}`,
    `POST /journeys/{id}/approve/{service}` (`app/api/v1/journeys.py`) —
    a generic version of the demo's college-specific actions, resolving
    connectors by department instead of hardcoding Revenue.
  - `GET /life-events`, `GET /life-events/{code}` — citizen-facing
    life-event metadata (title/description/goal statement, EN+MR),
    backed by a new small static registry
    (`app/services/life_event_catalog.py`) keyed by the same codes as
    `GRAPH_REGISTRY`.
  - `app/services/journey_narrative.py` — `current_blocker`/`next_action`
    computed server-side from real step/consent state, so "what's
    blocking me, what do I do next" (Priority 3) is backend truth
    transformed into plain language, never invented as frontend copy.
- **Two new mock connectors** (Urban Development, Finance) plus a
  **generic connector-by-department resolver**
  (`container.get_connector_for_department`) — needed for the second
  real life event (Priority 7). The existing `/demo` college flow still
  uses its own hardcoded `get_revenue_connector()` untouched.
- **A third new connector (Home/identity) was needed to fix a real bug**:
  a citizen without the `/demo` seeding's pre-verified identity got "No
  connector registered for department 'Home'" the instant they tried to
  submit `identity_verification` through the generic API — a path the
  college demo's citizen never exercised because their identity always
  started pre-verified. Found live in the browser, not by code review;
  `app/services/connectors/home_affairs.py` added, with a regression test.
- **Consent revoke** (`JourneyService.revoke_consent`, wrapping the
  orchestrator's existing `revoke_consent` which was built but never
  exposed) — needed for Priority 5's "Grant / Reject / Revoke" consent UX.
- **Document rejection now cascades symmetrically with verification**:
  `JourneyService.sync_rejected_document` mirrors `sync_verified_document`
  — a rejected vault document pushes any waiting journey step to
  REJECTED through the same shared event path, so "the requirement
  remains unsatisfied and the citizen gets an actionable next step"
  (a Phase 6 testing requirement) is real backend state, not just a
  vault-level status with no journey-level consequence.
- **`DocumentView.used_by`**: cross-references a document's `doc_type`
  against every one of the citizen's applications' step keys, so the
  vault can show "Income Certificate — used by: Scholarship Application"
  (Priority 4's reusable-data demonstration) without a second, separate
  relationship being modeled — it's derived, not stored.

### Frontend: the product shell

- **7 routes** (`/`, `/services`, `/journeys`, `/journeys/[id]`,
  `/vault`, `/profile`, `/demo`) plus `/admin`, sharing one `NavBar` and
  one design language — not "dozens of disconnected pages." `/demo`
  keeps its own distinct judge-mode framing (orange badge) so it reads
  as a separate mode, not a hidden extra page in the main IA.
- **No real citizen auth yet** (Supabase Auth isn't wired — see below),
  so `useCitizenId()` is a browser-local, editable-on-`/profile`
  stand-in identifier. It is explicitly documented as not a security
  boundary; the backend doesn't verify who's asking. This is the
  correct scope for "local adapters only, no Supabase yet."
- **i18n foundation**: a small React context (`LanguageProvider`) + a
  centralized string dictionary (`translations.ts`), covering nav, the
  home hero/architecture explainer, status labels, and common
  action/consent labels — not an exhaustive translation of every string
  on every page (e.g. the "How SETU works" step list and admin dashboard
  stayed English-only). This matches the instruction to translate "the
  most important citizen-facing screens," not the whole product, given
  the scope of this phase. Backend identifiers/API fields are never
  translated — only display strings.
- **Judge Mode (`/demo`) restructured with a scenario selector**: the
  original College Admission implementation was extracted verbatim into
  `CollegeAdmissionPanel.tsx` with zero logic changes (Priority 7 of the
  acceptance criteria: "College Admission remains fully deterministic")
  — re-verified live in the browser end to end after every change in
  this phase. `SmallBusinessPanel.tsx` is new, built entirely on the
  generic `/journeys` API — proving the orchestrator is reusable, not
  proving a second bespoke demo implementation.
- **Home page rebuilt** with the architecture explainer (Priority 10):
  Citizen → OneGov UI → Profile + Consent → Service Orchestrator →
  Connector/Adapter Layer → Government Departments, and the central
  message "SETU does not replace existing government portals. It
  connects them around the citizen's goal." No separate explainer page
  — folded into Home to avoid page-count creep.
- **Admin dashboard (`/admin`)** consumes `GET /admin/metrics` (already
  real since Phase 5) with zero new backend work — total/active/complete/
  blocked journey counts, bottleneck service codes ("where are citizens
  getting stuck"), department pending/rejected counts, blocked-journey
  detail list. No fabricated numbers; an empty section says so plainly
  ("No blocked journeys right now") rather than showing a fake zero-state
  chart.

### Bugs found via live browser use this phase (not by code review)

- **Dark-mode CSS silently broke every page's contrast**: `globals.css`
  had a `prefers-color-scheme: dark` media query flipping `--background`
  to near-black, combined with a plain (unlayered) `body { background }`
  rule that beat every Tailwind utility class regardless of specificity
  (CSS cascade layers: unlayered always wins over `@layer utilities`,
  which is where Tailwind's generated classes live). No page in this
  product implements a `dark:` variant, so on any browser/OS defaulting
  to dark scheme, every page rendered with dark text on a near-black
  background — nearly unreadable. Confirmed via
  `getComputedStyle(document.body)` before fixing. Removed the dark
  override; the product is light-only until dark mode is deliberately
  designed for.
- **`canGrant` excluded `READY`, only allowing `NOT_STARTED`** in both
  `SmallBusinessPanel.tsx` and `/journeys/[id]/page.tsx` — so the moment
  a step's dependency was satisfied (e.g. `local_noc` once
  `business_registration` verified), its "Grant consent" button stayed
  permanently disabled even though the backend had no such restriction
  (`grant_consent` never checked step status). A judge clicking through
  the Small Business scenario would hit two dead buttons. Fixed by
  including `ready` alongside `not_started` in both places.
- **The backend's `next_action` text had the identical gap**: it only
  suggested granting consent/submitting for `NOT_STARTED` steps, so a
  `READY` step (with no active journey-level short-circuit) would fall
  through to a stale "submit your final application" message that never
  mentioned consent. Fixed by merging `NOT_STARTED` and `READY` into one
  actionable branch in `journey_narrative.next_action`. Note: this
  particular fix is not exercised by the Small Business graph's own
  topology (both `local_noc` and `gst_registration` share the single
  `business_registration` dependency, so they become READY
  simultaneously, at which point `Journey.is_complete()` — true once
  every step is VERIFIED-or-READY, established since Phase 2 — already
  short-circuits `next_action` to "nothing further needed" first). It's
  still correct and kept for any life event whose steps unlock at
  different times.
- **`is_complete()` semantics were re-examined, not changed**: a journey
  where every step is at least READY counts as complete, exactly as it
  has since Phase 2 (this is why `education_scholarship` reaching READY
  was always the college demo's finish line without a further
  submission). Applying that same rule to Small Business means the
  citizen can stop once `local_noc`/`gst_registration` are READY, or
  optionally submit them for final department sign-off — both are valid
  under the existing definition; the frontend now permits both instead
  of blocking the optional path.

## Phase 7 — Identity, persistence, security hardening

This phase turns the local/demo prototype into an authenticated,
persistent, authorization-enforcing platform, without touching the
orchestrator's business logic, without introducing Supabase/Appwrite
(neither was actually required — see below), and without breaking the
judge demo. **DEMO MODE vs PRODUCTION MODE boundary**: every identifier,
credential and integration in this codebase today is demo-safe synthetic
data over local adapters. Nothing here talks to Aadhaar, DigiLocker, a
real Maharashtra department system, Supabase, or Appwrite — the
repository/storage abstraction exists so those can be wired in later
without an orchestrator or API rewrite, but claiming any of them are
integrated today would be false. See "Not required this phase" below for
why Supabase/Appwrite specifically weren't introduced.

### Identity + authentication (Priority 2)

- **Opaque bearer tokens, not Aadhaar, not Supabase Auth yet.**
  `POST /auth/session {identifier}` (`app/api/v1/auth.py`) registers on
  first use and returns a `secrets.token_urlsafe(32)` session token
  (`app/services/auth_service.py`). `identifier` is deliberately generic
  (a phone number in a real deployment; any string in local dev/demo) —
  there is no OTP, no Aadhaar e-KYC, matching the explicit instruction
  not to integrate real Aadhaar without authorization.
- **`derive_citizen_id(identifier) = f"citizen-{sha256(identifier)[:16]}"`**
  (`app/services/identity.py`) is the single source of truth for turning
  an identifier into a citizen_id — used by both real login and demo
  seeding (`demo_scenario.DEMO_CITIZEN_ID` is now *derived* from
  `DEMO_LOGIN_IDENTIFIER`, not a separate hardcoded string). This means
  logging in as the demo identifier produces exactly the demo citizen,
  proven by `test_citizen_eligibility_reflects_connector_verified_state_not_only_vault`.
- **Why this shape, not a JWT library**: the seam that matters is
  `get_current_session(authorization) -> SessionRecord` in
  `app/core/security.py`. Swapping in real Supabase Auth later means
  replacing this one function's body (verify a Supabase JWT, look up
  `auth.users`) — no route handler changes, since every handler already
  depends on `SessionRecord`, never on a raw citizen_id string.
- **Session storage is a repository, not a dict**: `AuthRepository`
  (`app/repositories/interfaces.py`) + `LocalJsonAuthRepository`
  (`accounts.json`, `sessions.json`) — same pattern as every other piece
  of state, so it survives a backend restart (see Persistence below) and
  has a clear Supabase-adapter seam (`SupabaseAuthRepository` later,
  though real Supabase Auth would likely replace most of this repository
  rather than sit behind it — noted honestly, not hidden).

### Authorization (Priority 3)

- **`require_owner_or_admin(citizen_id, session)`** (`app/core/security.py`)
  is called explicitly at the top of every handler that takes a
  citizen_id path parameter — not via a `Depends` chain, because the
  check needs the specific path parameter's value, not just "is there a
  session." Raises 403 unless `session.citizen_id == citizen_id` or
  `session.role == "admin"`.
- **A citizen_id or document_id in a URL is never trusted alone.**
  `vault.py::_get_owned_document` is the sharpest example: it checks
  *both* that the document's actual owner matches the URL's citizen_id
  *and* that the authenticated session is that citizen (or admin) —
  a document_id is not proof of ownership, and a citizen_id in the URL
  is not proof of identity. This closed a real gap found while
  retrofitting: `submit-for-review`/`verify`/`reject` previously had
  **zero** ownership check at all (only `get_document` checked).
- **Dedicated cross-citizen isolation tests**: `app/tests/test_authorization.py`
  — two independently-logged-in citizens, proving citizen A gets 403 (or
  404, where ownership is checked past a not-found document) attempting
  to read/write citizen B's profile, documents (list/get/upload/submit-
  for-review/verify/reject), journeys (list/start/get/consent/revoke/
  submit/approve), and eligibility. Also proves the admin branch of
  `require_owner_or_admin` is real, not just the owner branch.
  `test_admin_metrics.py::test_metrics_requires_admin_role` covers the
  admin-only surface (Priority 10).

### RLS review (Priority 4)

`backend/app/db/migrations/0001_init.sql` (written in Phase 2, verified
against a disposable Postgres container then) already encodes the target
RLS model for when Supabase is wired — reviewed here against the current
local-adapter authorization model rather than weakened or rewritten:

| Data category | Table(s) | Who can read | Who can write |
|---|---|---|---|
| Citizen identity/profile | `citizens`, `profiles` | Owner (`auth.uid() = id`); officials scoped to their district or all (super_admin) | Owner only |
| Documents + verifications | `documents`, `document_verifications` | Owner; officials (read) | Owner (documents); verification rows are official-authored |
| Journeys/applications | `applications`, `application_steps` | Owner; officials | Owner writes applications; steps follow the parent application |
| Consent | `consents` | Owner only (not official-readable — consent is between citizen and the recipient department, not a staff dashboard concern) | Owner only |
| Connector requests/events | `connector_requests`, `connector_events` | Owner (via their application/step); officials | service_role only (backend), no citizen-facing write policy |
| SLA records | `sla_records` | Owner; officials | service_role only |
| Notifications | `notifications` | Owner only | Owner only |
| Audit logs | `audit_logs` | Officials only (`is_official()`) — a citizen cannot read their own audit trail via RLS directly; the app exposes a scoped view over the same data through `GET /demo/audit-log` instead | service_role only (backend) |
| Service/life-event catalog, district analytics | `services`, `life_events`, `service_dependencies`, `district_analytics` | Public read (no PII) for the catalog; `district_analytics` official-only | service_role only |

`citizens.id references auth.users(id)` — matching exactly how
`derive_citizen_id` + real Supabase Auth would line up once wired: the
citizen_id this backend already uses everywhere becomes the Supabase
`auth.users.id`, not a second parallel identifier. No RLS policy was
loosened to make the current local-adapter demo work, because the
current demo doesn't run against this schema at all yet (see below).

### Persistent state (Priority 5)

- **`ConnectorRequestRepository`** (`app/repositories/interfaces.py` +
  `app/repositories/local/connector_request_repository.py`) replaces the
  in-memory `dict` every mock connector (`GovernmentConnector` base
  class, `app/services/connectors/base.py`) used to hold its request
  bookkeeping in. Every connector now takes the repository in its
  constructor; `container._connector_registry` injects the same shared
  repository into all of them.
- **Proof, not assertion**: `test_restart_persistence.py` clears every
  `container.py` `lru_cache` mid-test (`_restart_backend()`) — the only
  way a state-carrying singleton could survive that is if it was
  actually written to disk. Confirms an in-progress application, its
  connector external_reference, and the session token itself all survive
  and remain fully operable (`approve` still works, dependency
  resolution still cascades) after the simulated restart.
- This directly resolves the Phase 3-noted limitation that connector
  state didn't survive a backend restart mid-journey.

### Consent security (Priority 6)

`Consent.is_active` (`app/services/orchestrator.py`) was already
correct — checks `revoked_at is None and expires_at > now` — but had no
dedicated expiry test. `app/tests/test_consent_security.py` proves all
three states explicitly: active consent authorizes the connector
exchange; revoked consent blocks it (`ConsentRequiredError`); expired
consent (via `validity_days=-1`, since the public API doesn't expose a
citizen-chosen validity period) also blocks it, independently of
revocation. Grant/revoke are additionally exercised end-to-end over HTTP
in `test_journeys_api.py`.

### Document security (Priority 7)

Reviewed against the checklist, not rewritten — this was already mostly
correct from Phase 4/5:

- **MIME allow-list + 5MB limit** (`LocalDiskDocumentStorage`,
  `Settings.max_upload_mb = 5`, never 15MB) — enforced server-side,
  tested with an oversized file and a disallowed MIME type.
- **No path traversal, no arbitrary file execution possible**: storage
  keys are always server-generated (`uuid.uuid4().hex` + a MIME-derived
  extension) — the client-supplied filename is stored only as
  `original_filename` metadata and never touches a filesystem path.
- **Ownership + verification lifecycle**: see Authorization above —
  every vault endpoint now checks ownership, including the three that
  previously didn't.
- **Rejection reasons**: `DocumentRejectRequest.reason` is required and
  surfaced on the record (`rejection_reason`), tested end to end
  (`test_document_rejection_cascades_and_leaves_requirement_unsatisfied`).
- **No sensitive bytes in logs**: confirmed by inspection — the only
  `logger` call in the codebase (`app/main.py`'s unhandled-exception
  handler, added this phase) logs only the HTTP method and path, never
  headers, bodies, or file contents.
- **Known limitation, not a Phase 7 regression**: `DocumentView.url`
  (`/media/documents/{storage_key}`) is a URL *shape* returned by the
  API — there is no route actually mounted to serve it yet (true since
  Phase 4). Practically this means there is currently no way to
  download a stored file's bytes at all, which is safe by omission but
  worth fixing deliberately (with its own authorization check) before
  a document *preview* feature is built — not done here as it wasn't
  part of this phase's scope.

### API security (Priority 8)

- **Global exception handler** (`app/main.py`): every *expected* failure
  already raised a specific `HTTPException` with a safe message in its
  own handler (verified by grepping every `except ... raise
  HTTPException(..., str(exc))` in `app/api/v1/` — all catch narrow,
  known exception types, never a bare `Exception`, so `str(exc)` is
  always a controlled domain message, not a stack trace). The new
  `@app.exception_handler(Exception)` is the backstop for a genuine bug:
  it logs the real exception server-side and returns a fixed
  `{"detail": "Internal server error"}` — internals never reach a client
  even if a future handler forgets to catch something.
- **Security headers middleware** (`app/main.py`): `X-Content-Type-Options:
  nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` on
  every response.
- **CORS**: unchanged from Phase 1 — locked to `http://localhost:3000`,
  extended only via `.env` for a real deployed frontend origin. Not
  loosened this phase.
- **Input validation**: every request body is a Pydantic schema
  (`app/schemas/`); path parameters that must resolve to a real
  entity (life event code, service code, application id, document id)
  already 404 through existing `ValueError`/`KeyError` handling.
- **Rate limiting — strategy documented, not implemented this phase**:
  the highest-value target is `POST /auth/session` (unlimited identifier
  guesses/account creation). The correct mechanism for a real deployment
  is an edge/gateway-level limiter (Supabase's own or a reverse proxy),
  keyed by IP for the unauthenticated login endpoint and by citizen_id
  for authenticated endpoints — not an in-process Python limiter, which
  wouldn't survive the multi-instance deployment a real gateway already
  implies. Not implemented here because there is no real edge
  infrastructure yet for it to live in (single local process, no
  gateway), and adding an in-process limiter would be security theater
  for a judge demo rather than a real control — noted honestly as a gap
  rather than faked.
- **Secrets**: no secret is exposed to the frontend (`SUPABASE_SERVICE_ROLE_KEY`
  etc. are backend-only env vars, unused this phase since Supabase isn't
  wired yet); session tokens are opaque and carry no embedded claims to
  leak if logged (and they aren't logged — see Document security above).

### Audit trail (Priority 9)

- Journey-level events (`journey.reset`, `consent.granted`,
  `consent.revoked`, `connector.submitted`, `connector.event_received`)
  were already audited by `JourneyService` since Phase 3/4 —
  `application_id`-scoped, via `AuditLogRepository`.
- **Gap found and fixed this phase**: that scoping meant a document with
  no active journey requiring its doc_type (e.g. a `supplementary_document`
  upload, or any document uploaded before a journey exists) left
  **upload/submit-for-review/verify/reject completely unaudited** —
  `JourneyService.sync_verified_document`/`sync_rejected_document` only
  write an audit entry when they find a matching journey step. Fixed by
  moving document-lifecycle auditing into `DocumentVaultService` itself
  (`document.uploaded`/`document.submitted_for_review`/`document.verified`/
  `document.rejected`, `resource_type="document"`, `application_id=None`)
  — independent of whether a journey ever cascades from it. Regression
  test: `test_document_lifecycle_is_audited_even_without_an_active_journey`.
- **Not added this phase**: SLA breach events are computed on read
  (`compute_sla_status`) rather than written as discrete audit entries
  when a deadline passes — there is no background job in this
  architecture that would notice the transition at the moment it
  happens (see Phase 4's n8n `sla-monitoring` workflow, which polls
  rather than pushes). Documented as a gap rather than fabricating an
  event that nothing actually triggers.

### Admin authorization (Priority 10)

`require_admin(session)` (403 unless `session.role == "admin"`) gates
`GET /admin/metrics`. Role is assigned at account-creation time only, if
the login identifier is in `Settings.admin_identifiers` (default:
`["admin"]`) — a local bootstrap mechanism explicitly documented as not
how role assignment would work against real Supabase Auth (that would be
a `role` claim or a separate `officials` table row, matching
`0001_init.sql`'s `officials`/`official_role` model). Frontend gate:
`/admin` checks `role === "admin"` from `useAuth()` and shows an access
message instead of the dashboard for anyone else — enforced by the
backend regardless of what the frontend does or doesn't render.

### Preserving the existing demo (Priorities 11-12)

- **Every citizen-facing endpoint now requires authentication**, which
  would have broken both Judge Mode panels outright (they never logged
  in). Fixed by giving each panel a fixed, silent login: `CollegeAdmissionPanel`
  logs in as `demo_scenario.DEMO_LOGIN_IDENTIFIER` (returned by
  `GET /demo/catalog` as `login_identifier`, so the frontend never
  hardcodes it independently of the backend's derivation) and threads
  the resulting token through its `citizenApi`/`journeyApi` calls;
  `SmallBusinessPanel` does the same with a new fixed identifier,
  `demo-small-business-registration`. Neither panel's *business logic*
  changed — same deterministic seeded state, same real backend
  processing, same event-processing path.
  The `/demo/*` endpoints themselves (`app/api/v1/demo.py`) were
  deliberately left unauthenticated — they always operate on the one
  fixed demo citizen/application regardless of caller, so adding session
  auth to them would add a login requirement without adding a real
  authorization boundary (there's only ever one demo citizen for them to
  authorize against). The generic `/citizens/*` and `/journeys/*`
  endpoints they call *into* (for documents/eligibility/journeys) are
  fully authenticated — those are shared with the real citizen surface,
  which is where authorization actually needed to be enforced.
- Full regression re-verified live in the browser after the auth
  integration: College Admission (Reset → Vault → Eligibility → Consent
  → Submit Income → Approve → Scholarship Ready → Timeline), Small
  Business (Start → Registration → Urban Development → Finance →
  Complete), the rejection flow, and English↔Marathi toggle.

### Frontend: real login replacing the citizen-ID placeholder

- **`useAuth()`** (`frontend/src/lib/useAuth.ts`) replaces
  `useCitizenId()` (deleted) — stores a real server-issued token,
  citizen_id and role in `localStorage`, not a free-text, user-editable
  citizen_id. `/login` (new) is the only place a citizen types an
  identifier; every other page reads `useAuth()` and shows a "Log in"
  prompt instead of a request if there's no session.
  `frontend/src/lib/api.ts`'s `request()`/`uploadRequest()` attach
  `Authorization: Bearer <token>` automatically from `localStorage`,
  with an optional per-call `token` override — the mechanism the demo
  panels use to authenticate as their fixed identity without touching
  (or requiring) whatever citizen is actually logged in in the browser.
- **`NavBar`** shows Log in/Log out based on `useAuth().isLoggedIn`, and
  only shows the Admin link when `role === "admin"`.

### Bugs found via live browser use this phase (not by code review)

- **A real concurrency bug in the JSON persistence layer, hit only by
  the auth integration**: `JsonFileStore.__init__` always writes its
  `default` value if the target file doesn't exist yet — safe under a
  single writer, but `container.py`'s `@lru_cache`d factories have no
  "single-flight" behavior, so two concurrent requests that are each
  the very first to touch a brand-new data directory (exactly what
  happens when both Judge Mode panels silently log in at once against a
  freshly reset `app/data/`) can each construct their own
  `JsonFileStore` for `accounts.json` before either result is cached.
  Both then tried to write the same fixed `accounts.json.tmp` path
  simultaneously; on Windows, one process's `os.replace` failed with
  `WinError 32` (target file in use by the other), surfacing to the
  browser as a CORS error (the crashed response never reached
  `CORSMiddleware` cleanly) — genuinely confusing until the backend's
  own traceback (visible because this was live `uvicorn --reload`, not
  the new production-safe exception handler) showed the real
  `PermissionError`. Fixed by giving every write its own unique temp
  filename (`app/repositories/local/json_file_store.py`) — whichever of
  two equivalent concurrent initial writes wins the rename no longer
  matters, since both are writing the same `default` content.
- **`useAuth()` didn't stay in sync across components**: `NavBar` and
  whichever page is open each call `useAuth()` independently, and each
  call originally created its own isolated `useState`. Logging in from
  `/login` updated that page's own state and `localStorage`, but
  `NavBar`'s separate hook instance had no way to know — it kept
  showing "Log in" after a successful client-side-routed login until a
  full page reload. Fixed with a small same-tab event
  (`window.dispatchEvent`/`addEventListener` on a `"setu-auth-changed"`
  event) that every `useAuth()` instance emits on login/logout and
  listens for to resync from `localStorage` — confirmed fixed by
  logging in via a real link click (not a raw navigation) and watching
  `NavBar` flip to "Log out" immediately.
- Both found during this phase's full live-browser regression (login,
  College Admission, Small Business, Marathi toggle, admin gate) run
  against the actual `uvicorn`/`next dev` servers, not just by reading
  the diff.

### Not required this phase: Supabase, Appwrite

Both remain unwired, deliberately: **Supabase** — this phase authenticates
via an opaque token issued and verified entirely by this backend, which
is what Priority 2 actually asked for ("real citizen authentication...
NOT Aadhaar"); a Supabase project doesn't have to exist for that
requirement to be met, and everything in `get_current_session`/
`AuthRepository` is already shaped as a drop-in seam for real Supabase
JWT verification the moment a project exists and is explicitly
requested. **Appwrite** — no new document-storage requirement was
introduced this phase (the vault's MIME/size/ownership rules were
already real, local-adapter-backed); introducing Appwrite now would be
adding infrastructure the phase's actual priorities didn't need, against
the explicit instruction not to introduce it "just because it exists in
the original architecture documentation." Both remain the natural next
step per the repository/storage abstraction, whenever real storage or
real identity verification is explicitly requested.

## Open items for Phase 8+

- Supabase project must be created (cloud, free tier) and the migrations
  applied to it; Appwrite project needed for real document storage. Both
  need account creation, which requires the project owner — not
  something to be done unattended. The repository/storage abstraction
  exists specifically so this can happen later without touching
  orchestration or business logic.
- No route currently serves `DocumentView.url` — see Document security
  above.
- No real rate limiting — see API security above.
- SLA breaches are computed on read, not pushed as discrete audit
  events — see Audit trail above.
- Admin role assignment (`admin_identifiers`) is a local bootstrap
  mechanism, not how it would work against real Supabase Auth/officials.
- i18n covers key screens, not every string (unchanged since Phase 6) —
  the new `/login` page and admin access-denied messages are English-only.
- Admin dashboard has no "average processing time" metric — the spec
  said not to fabricate one, and there isn't yet enough real completed-
  journey history to compute it meaningfully.
- Small Business's "Reset" in Judge Mode starts a genuinely new journey
  (fresh UUID) rather than mutating a fixed one in place like College
  Admission's deterministic reset — the generic `/citizens/{id}/journeys`
  POST always creates fresh. Multiple demo runs accumulate journeys for
  the demo business citizen in local storage; harmless (JSON file, not
  shown to judges directly) but noted as a minor rough edge, not silently
  hidden.
