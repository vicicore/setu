# n8n workflows

Two workflows, matching Phase 4 scope (Master Prompt section 13):

- **connector-status-webhook.json** — receives a department/application
  status event, forwards it to SETU's `/api/v1/webhooks/n8n/{event}`
  boundary, and branches on whether it actually changed journey state.
  Dependency re-evaluation and downstream unlock happen inside that one
  backend call (atomic with the state write) — deliberately not a
  separate n8n step; see `docs/DECISIONS.md`.
- **sla-monitoring.json** — polls `GET /demo/sla-alerts` on a schedule and
  branches to a notify/all-clear no-op. The notify node is a stand-in for
  a real channel (email/Slack) — wiring one in doesn't require any
  backend change.

Both were verified by importing them into a real, disposable n8n
instance (`docker compose up`, then `n8n import:workflow`) and exporting
them back out to confirm n8n's own validation accepted every node type
and connection — not just that the JSON parses.

## Importing

```bash
cd infra/n8n
docker compose up -d
docker exec n8n-n8n-1 n8n import:workflow --input=/home/node/workflows/connector-status-webhook.json
docker exec n8n-n8n-1 n8n import:workflow --input=/home/node/workflows/sla-monitoring.json
```

Then open `http://localhost:5678`, complete the one-time local owner
setup (n8n requires this on first run), and activate both workflows.

## Environment variables the workflows read

Set in `infra/n8n/docker-compose.yml`:

- `SETU_API_BASE_URL` — the running FastAPI backend's `/api/v1` base URL
  (defaults to `http://host.docker.internal:8000/api/v1` so the n8n
  container can reach a backend running on the host machine)
- `SETU_WEBHOOK_SECRET` — must match the backend's `N8N_WEBHOOK_SECRET`
  (`backend/.env`); leave both blank for local dev without signature
  checks
