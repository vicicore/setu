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

## Open items for Phase 7+

- Supabase project must be created (cloud, free tier) and the migrations
  applied to it; Appwrite project needed for real document storage. Both
  need account creation, which requires the project owner — not
  something to be done unattended. The repository/storage abstraction
  exists specifically so this can happen later without touching
  orchestration or business logic. Nothing in Phase 6 required it.
- No real citizen authentication — `useCitizenId()` is a browser-local
  placeholder, not a security boundary.
- i18n covers key screens, not every string (see above) — a full
  translation pass is future work.
- Connector state (Phase 3 limitation) still doesn't survive a backend
  restart mid-journey.
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
