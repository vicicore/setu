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

Status: Phase 1 (Foundation), Phase 2 (orchestration core + Supabase
schema) and Phase 3 (repository/storage abstraction + a real `/demo`
frontend) are done.

- **Orchestration** (`backend/app/services/orchestrator.py`): a real
  `JourneyOrchestrator` state machine — consent gating, dependency checks,
  webhook-driven cascading unlock. Untouched by the persistence work below.
- **Persistence is behind interfaces, not scattered**: API -> `JourneyService`
  -> `ApplicationRepository`/`AuditLogRepository` (ports) ->
  `LocalJson*Repository` (today's adapter). Same shape for documents:
  `DocumentStoragePort` -> `LocalDiskDocumentStorage`. Supabase/Appwrite
  become new adapter classes later without touching orchestration or API code
  — see `docs/DECISIONS.md`.
  4 mock department connectors (Revenue/Education/Social Justice/Labour)
  behind one common interface, and the full Supabase schema + RLS
  (`backend/app/db/migrations/`, verified against a real Postgres container).
- **A real, working `/demo` page** (`frontend/src/app/demo/page.tsx`) — not
  a mockup: it calls the FastAPI backend live, renders the dependency graph,
  lets you grant consent / submit / simulate approval, and shows the
  scholarship auto-unlock, the unified timeline, and the audit trail.
  Verified by actually clicking through it in a browser end to end.
- 11 passing backend tests, `mypy` clean across 42 source files, frontend
  build + lint clean.
- Supabase/Appwrite/n8n are still only wired for configuration, not
  connected to live projects — deliberately deferred; the abstraction
  above exists so that's a later, isolated step.

Try it locally:

```bash
cd backend && ./venv/Scripts/python -m uvicorn app.main:app --reload
```

```bash
cd frontend && npm run dev
```

Then open `http://localhost:3000/demo` and click through: Reset demo ->
Grant consent -> Submit Income Certificate -> Simulate Revenue approval —
watch `education_scholarship` go from `blocked` to `ready` automatically.

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
