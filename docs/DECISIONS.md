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

## Open items for Phase 5+

- Supabase project must be created (cloud, free tier) and the migrations
  applied to it; Appwrite project needed for real document storage. Both
  need account creation, which requires the project owner — not
  something to be done unattended. The repository/storage abstraction
  exists specifically so this can happen later without touching
  orchestration or business logic.
- Eligibility and the citizen vault are not yet connected to each other
  or to the journey orchestrator (see above).
- No admin/operations dashboard yet (bottleneck visibility, SLA breach
  counts across all applications — today's `/demo/sla-alerts` only
  covers the single demo application).
- No i18n on the actual UI (the demo page shows Marathi + English as
  static text, not a language switcher).
- Connector state (Phase 3 limitation) still doesn't survive a backend
  restart mid-journey.
