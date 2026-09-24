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

## Open items for Phase 3+

- Supabase project must be created (cloud, free tier) and the migrations
  above applied to it; Appwrite project needed for real document
  storage. Both need account creation, which requires the project owner
  — not something to be done unattended.
- Connector interface (`app/services/connectors/base.py`) currently
  supports Revenue/Education/Social Justice/Labour mocks with only
  `submit`/`get_status`/`simulate_approval`/`simulate_rejection`/
  `emit_webhook_event`. The actual `/webhooks/n8n/{event}` HTTP endpoint
  and n8n workflow JSON exports are not yet built.
- Eligibility engine (`GET/POST /eligibility/evaluate`) and citizen
  profile/vault/consent REST endpoints backed by Supabase are not yet
  built — only the in-memory demo path is wired end to end so far.
