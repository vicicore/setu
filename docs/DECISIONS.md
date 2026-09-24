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

## Open items for Phase 2+

- Supabase project must be created (cloud, free tier) and its migrations
  written under `backend/app/db/migrations/` — not yet started.
- Appwrite: decide between Appwrite Cloud vs. self-hosted for the demo
  environment; default to Appwrite Cloud free tier unless told otherwise.
