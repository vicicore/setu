ONEGOV / PROJECT SETU --- SIH BUILD README

## Repository layout

```
setu/
  frontend/   Next.js + TypeScript + Tailwind (citizen + admin UI)
  backend/    FastAPI + Pydantic (API gateway, orchestration, connectors)
  infra/n8n/  n8n docker-compose + exported workflow JSON
  docs/       DECISIONS.md (implementation decisions log) + specs
```

## Local development (clean-machine quickstart)

Backend:

```bash
cd backend
py -m venv venv
./venv/Scripts/pip install -r requirements.txt
cp .env.example .env   # fill in Supabase/Appwrite/n8n values
./venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

n8n (optional locally, required for the SLA/webhook workflows):

```bash
cd infra/n8n
docker compose up -d
```

Backend tests: `cd backend && ./venv/Scripts/python -m pytest`
Backend type check: `cd backend && ./venv/Scripts/python -m mypy`

Status: Phases 1-6 (foundation through productization) plus Phase 7
(identity, persistence, security hardening) are done.

- **Orchestration** (`backend/app/services/orchestrator.py`): a real
  `JourneyOrchestrator` state machine — consent gating, multi-requirement
  dependency checks, webhook-driven cascading unlock. Untouched through
  every phase built on top of it, including this one.
- **7 product routes sharing one nav and one design language**: `/`,
  `/services` (real life-event catalog), `/journeys` + `/journeys/[id]`
  (the richest page — progress, current blocker, next action, per-step
  consent/SLA, all computed server-side), `/vault` (real
  upload→review→verify/reject lifecycle, cross-referenced against which
  journeys use each document), `/profile`, plus `/admin` and the
  judge-mode `/demo` — not dozens of disconnected screens.
- **A second real journey**: Starting a Small Business, built entirely on
  a new *generic* `/journeys` API (not a copy of the College Admission
  demo) — proving the orchestrator is a reusable platform. Exercises
  three different mock connectors (Labour, Urban Development, Finance)
  end to end.
- **One event-processing path for a service becoming verified or
  rejected, from anywhere**: a connector webhook, a demo action, or a
  vault document transition all resolve to the exact same
  `JourneyService.receive_connector_event` call. No parallel state machine.
- **`/admin` dashboard** on real, previously-built `/admin/metrics` data —
  bottleneck services ("where are citizens stuck"), department workload,
  blocked journeys. No fabricated numbers.
- **i18n foundation** (English/Marathi) covering nav, home, and common
  status/action labels — a centralized dictionary, not scattered strings.
- 39 passing backend tests, `mypy` clean across 66 source files, frontend
  build + lint clean, extensive live browser verification across every
  new page — which caught and fixed 4 real bugs this phase (a dark-mode
  CSS contrast break, a missing mock connector, and a UI/backend gating
  bug that silently blocked consent on an unlocked step). Full detail in
  `docs/DECISIONS.md`.

**Phase 7 — identity, persistence, security hardening:**

- **Real citizen authentication**: `POST /auth/session {identifier}`
  issues a server-verified bearer token — not Aadhaar, not yet Supabase
  Auth, but a real credential the backend derives a citizen_id from and
  checks on every request. Replaces the old browser-local, user-editable
  `useCitizenId()` placeholder entirely; `/login` is the only place a
  citizen types an identifier now.
- **Server-side authorization on every citizen-scoped endpoint**:
  `require_owner_or_admin` stops citizen A from reading citizen B's
  profile, documents, journeys, or consent by editing a URL — proven by
  dedicated cross-citizen isolation tests
  (`backend/app/tests/test_authorization.py`), not left to the frontend.
- **Persistent application + connector state**: every mock connector's
  request bookkeeping moved from an in-memory dict to a repository —
  proven by a test that clears every cached singleton mid-run to
  simulate a real backend restart and confirms an in-progress journey is
  still fully operable afterward.
- **Consent security**: active consent authorizes a connector exchange,
  revoked consent blocks it, expired consent blocks it independently of
  revocation — all three proven explicitly
  (`backend/app/tests/test_consent_security.py`).
- **Document lifecycle is now fully audited**, including uploads with no
  active journey behind them yet — a real gap found and fixed this
  phase, not just tested.
- **Admin-only `/admin/metrics`**, enforced server-side.
- **API hardening**: a global exception handler that never leaks
  internals on an unexpected error, basic security response headers, and
  a documented (not yet implemented — no real edge infrastructure exists
  for it) rate-limiting strategy.
- 54 passing backend tests (11 new this phase), `mypy` clean across 73
  source files, frontend build + lint clean, full live browser regression
  of every existing flow (College Admission, Small Business, rejection,
  English↔Marathi) after the auth integration. Full detail, including the
  RLS review and the demo panels' silent-login mechanism, in
  `docs/DECISIONS.md`.
- Supabase/Appwrite remain unwired — this phase's authentication and
  storage requirements were both met without them (see DECISIONS.md,
  "Not required this phase"); the repository/storage abstraction still
  exists specifically so either can be wired in later without an
  orchestrator or API rewrite.

Try it locally:

```bash
cd backend && ./venv/Scripts/python -m uvicorn app.main:app --reload
```

```bash
cd frontend && npm run dev
```

Then open `http://localhost:3000` for the full product (Home, Discover
Services, My Journeys, Documents, Profile), or go straight to
`http://localhost:3000/demo` for judge mode and click through: Reset demo
-> Grant consent -> Submit Income Certificate -> Simulate Revenue approval
— watch `education_scholarship` go from `blocked` to `ready`
automatically. A second scenario tab in `/demo` runs the same flow for
Starting a Small Business through three different mock connectors.

1. What we are building

Problem: SIH260129 --- system integration and interoperability among
government digital platforms causing fragmented service delivery.

Benchmark: Aaple Sarkar, Government of Maharashtra.

Aaple Sarkar is already a large public-service platform. Its official
dashboard currently reports 1,212 notified services, 1,083 services
available on the portal and 38 departments. It also supports service
discovery, citizen profiles, application tracking, certificate
verification, appeals, Sewa Kendra information and public/official
dashboards.

Our project must therefore not compete with Aaple Sarkar on number of
services or visual redesign.

Our layer is the orchestration layer.

A citizen states a goal. OneGov discovers the required government
services, checks prerequisites, reuses verified information with
consent, coordinates departments, and shows one end-to-end journey.

2. The core problem we demonstrate

A citizen may need several government services for one real-life goal.

Example:

College admission + scholarship → Domicile → Income Certificate →
Caste/eligibility information → Scholarship application

In a fragmented model, the citizen is responsible for understanding
departments, repeatedly providing information, and following multiple
application statuses.

OneGov turns this into a single journey.

3. The six core innovations

Unified Citizen Profile

Government API / Integration Hub

Life-Event Service Discovery

Smart Eligibility Engine

Document Vault + Consent

Cross-Department Journey Tracker + SLA Monitor

These are directly aligned with the team's existing solution documents.

4. Signature demo

Citizen statement

Marathi:

मला इंजिनिअरिंग कॉलेज प्रवेशासाठी शिष्यवृत्ती अर्ज करायचा आहे.

English:

I want to apply for an engineering college admission scholarship.

Expected system behavior

Recognize "College Admission + Scholarship".

Build the service dependency graph.

Check the synthetic citizen profile.

Find Domicile already verified.

Find Income Certificate missing/expired.

Identify Scholarship as blocked by Income Certificate.

Ask for explicit consent to share eligible verified data.

Create a mock Revenue application.

Show Revenue status in the same journey.

Simulate Revenue approval.

Automatically update Income Certificate to verified.

Automatically unlock Scholarship.

Show one completed cross-department timeline.

Judge takeaway

The citizen did not: - search for the correct department - re-upload a
verified document - manually create a second application after the
prerequisite - track multiple portals

The orchestration layer handled the dependency.

5. Aaple Sarkar coverage

The official online catalog includes services across many domains,
including:

Revenue

Rural Development & Panchayat Raj

Labour

Water Resources

Industries

Skill, Employment, Entrepreneurship & Innovation

Forest

Registration & Stamps

Cooperation/Marketing/Textiles

Law & Judiciary

Home

Transport

Agriculture

Finance

Public Health

Water Supply & Sanitation

Maharashtra Pollution Control Board

Urban Development

Tourism & Cultural Affairs

Social Justice & Special Assistance

Medical Education/AYUSH

Maharashtra Maritime Board

Maharashtra Industrial Development Corporation

municipal bodies and other listed departments/sub-departments

tax/GST-related services

The official service page contains the detailed catalog. The prototype
should use a curated, metadata-rich subset for the demo instead of
pretending to implement the entire catalog.

6. What makes OneGov different

Existing portal model               OneGov model

Find a service                      State a goal

Department-centric                  Journey-centric

Citizen manages prerequisites       Orchestrator manages dependencies

Repeat information where necessary  Reuse verified information with
consent

Separate statuses                   One timeline

Static service information          Actionable next step

Portal-level tracking               Cross-service journey tracking

Department silo                     Connector/adaptor architecture

7. Architecture

Citizen
  |
  v
Next.js OneGov UI
  |
  v
FastAPI API Gateway
  |
  +---- Citizen/Profile
  |
  +---- Life-Event Engine
  |
  +---- Eligibility Rules
  |
  +---- Consent Manager
  |
  +---- Document Vault Metadata
  |
  +---- Journey Orchestrator
  |
  +---- Connector Hub
  |
  +---- SLA/Audit
  |
  +---- n8n Webhooks
          |
          +---- Revenue Mock API
          +---- Education Mock API
          +---- Social Justice Mock API
          +---- Labour Mock API

Supabase PostgreSQL
  - citizen data
  - service catalog
  - journey state
  - consent logs
  - audit logs
  - analytics

Appwrite
  - document binaries

n8n
  - asynchronous workflow simulation
  - SLA triggers
  - webhook events

8. Important architecture decision

One supplied context document mentions Node.js/NestJS or Go as possible
gateway technologies.

The backend specification, security specification, rules and task queue
specify FastAPI.

Therefore the implementation standard is:

Next.js + FastAPI + Supabase + Appwrite + n8n.

Do not create two competing backend architectures.

9. Security baseline

The project must enforce:

no hardcoded secrets

.env.example

Pydantic request validation

Supabase JWT verification

PostgreSQL RLS

least privilege

signed/time-bound consent

audit logs

file MIME validation

5 MB maximum upload

PDF/JPEG/PNG demo files only

no real Aadhaar or other personal identifiers

no access tokens in logs

HTTPS/TLS in deployment

The security document is stricter than an older backend draft on file
size. Use 5 MB.

10. Minimum routes

Citizen

/

/services

/journeys

/journeys/[id]

/vault

/profile

Governance

/dashboard

/admin

SIH presentation

/demo

/demo is mandatory.

11. Demo-mode requirements

The judge should not need to understand infrastructure.

Provide:

Reset Demo

Start College Admission

Grant Consent

Simulate Income Certificate Submitted

Simulate Income Certificate Approved

Simulate SLA Breach

Demo controls must be clearly marked as simulation tools and must not
appear in normal citizen workflows.

12. Required tests

Backend

auth middleware

Pydantic validation

citizen isolation

RLS

consent lifecycle

document validation

eligibility rules

DAG transitions

connector responses

webhook processing

SLA transitions

Frontend

build

type check

lint

mobile responsiveness

accessibility basics

error/loading/empty states

journey state rendering

End-to-end

Test:

start journey → inspect vault → consent → create prerequisite → connector update → approval → downstream unlock → unified timeline

13. Critical anti-patterns

Do not accept:

fake buttons that do nothing

static journey screenshots masquerading as orchestration

fake "AI eligibility" without rules

hardcoded government credentials

real Aadhaar numbers in seed data

direct claims of real government API integration

dozens of unrelated screens

copied Aaple Sarkar UI

charts without underlying data

a chatbot that only answers questions and does not trigger workflows

14. Definition of done

The implementation is ready for SIH demo only when:

the signature journey works from start to finish

dependency state changes are real

consent is recorded

mock department APIs are called

webhook/status updates change the journey

downstream service automatically unlocks

the citizen sees one timeline

admin sees bottlenecks/SLA

security tests pass

no secrets or real identifiers are present

/demo can reproduce the entire story

15. Evidence expected from freelancer

At every milestone provide:

routes

screenshots

API list

database migration changes

test output

security checks

known limitations

next milestone

Never accept "completed" without evidence.

16. SIH evaluation story

The prototype should be evaluated on:

A. Reduction in citizen effort

How much repeated entry/document handling disappears?

B. Interoperability

Can two or more department connectors participate in one journey?

C. Orchestration

Can a prerequisite automatically block/unblock a downstream service?

D. Consent and privacy

Can a citizen see and control what is shared?

E. Accessibility

Can the journey be completed in Marathi/Hindi/English and with
accessible interaction?

F. Administrative visibility

Can officials identify stalled services and SLA problems?

G. Demonstrability

Can a judge understand the difference from Aaple Sarkar in three
minutes?

17. Final product statement

OneGov is not another government portal. It is the interoperability
layer that connects government portals around the citizen's goal.
