# PROJECT_CONTEXT.md — read this first, every new chat

Paste this file (or the whole `docs/` folder) instead of the zip. Say:
"Read docs/PROJECT_CONTEXT.md and docs/REPOSITORY_MAP.md before doing anything."

## What TaskPilot is
Multi-agent task management system. Ingests tasks from external sources
(GitHub, Slack, formerly Jira/Outlook/ServiceNow), extracts/dedupes/
prioritizes them via an LLM agent pipeline, and shows a daily plan in a
React dashboard.

## Stack
- Backend: FastAPI (Python), Celery + Redis for async jobs, Postgres (or
  sqlite fallback), Alembic migrations
- Frontend: React + TypeScript + Vite, shadcn/ui
- Infra: Docker Compose (local), Kubernetes manifests (`k8s/`), Prometheus
- LLM: xAI Grok via `https://api.x.ai/v1`, model `grok-4.1-fast`
  (fallback: Gemini `gemini-2.5-flash`)

## Current architecture decision (as of this doc)
Migrating connectors from direct REST/static-PAT calls to MCP
(Model Context Protocol):
- ✅ GitHub — DONE. Self-hosted `github-mcp-server` (official image),
  per-user OAuth (`core/github_oauth.py`), webhook-driven real-time sync
  (`/webhooks/github`), MCP tool calls for on-demand actions
  (`core/mcp_client.py`, `core/connectors/github_mcp_connector.py`)
- ⏸️ Jira, Outlook, ServiceNow — DISABLED (commented out in
  `connector_registry.py`, not deleted). Same MCP pattern planned when
  it's their turn.
- ❌ Google login / full multi-tenant auth — NOT built. Current scope is
  single demo user (`DEMO_USER_ID = "demo-user"` in `github_oauth.py`).
  Revisit if going multi-user.

## Recently completed (2026-07-16 session)
- **PR → task linking**, auto-detect + manual override, routed through
  MCP: `core/pr_linker.py` (new — regex extraction of closing keywords
  from PR body), `link_pr_to_task()` in `core/state.py` (new), `pull_request`
  webhook handling in `routes.py`, `linked_prs` field on `Task`,
  `POST/DELETE /api/tasks/{id}/link-pr` endpoints, and
  `fetch_pull_requests()`/`get_pull_request()`/`create_issue()`/
  `update_issue()`/`add_issue_comment()` added to `GitHubMCPConnector`.
- **Fixed OAuth callback redirect bug**: was a relative
  `/settings/integrations` redirect (resolved against the backend's own
  port, and pointed at a route that doesn't exist on the frontend).
  Now an absolute `{FRONTEND_URL}/settings?tab=integrations` redirect;
  `Settings.tsx` reads `?tab=` on mount to land on the right tab.
- **Fixed MCP DNS resolution bug**: `MCP_GITHUB_URL` was defaulting to
  the Docker Compose service hostname (`github-mcp-server`), unresolvable
  from the host-run backend. Set to `http://localhost:9090/mcp` in
  `backend/.env` (port 9090 is published to the host in
  `docker-compose.yml`). Needs a full process restart to take effect —
  `--reload` doesn't re-run `load_dotenv()`.
- (Earlier in the week) GitHub OAuth login button in Settings →
  Integrations tab (`frontend/.../screens/Settings.tsx`)
- (Earlier in the week) LLM provider fixed to xAI Grok (`grok-4.1-fast`),
  was previously a typo'd non-existent model name

## Known gaps / next up
- No Google auth / multi-user support yet
- Jira/Outlook/ServiceNow re-enablement (MCP-based) not started
- **`core.llm_client` missing `get_llm_client` export** — dedup's LLM
  semantic-arbitration step fails on every call and silently falls back
  to embedding-only matching. Not yet fixed. Also seeing intermittent
  `400 Bad Request` from the Grok endpoint itself.
- Postgres connection failing locally (`Connect call failed ... 5432`) —
  falling back to sqlite; likely the same host-vs-Compose-hostname
  mismatch as the MCP issue, unconfirmed — check `DATABASE_URL` in
  `.env` if this needs to be a real Postgres run.
- `create_issue`/`update_issue` MCP methods exist on the connector now
  but aren't yet called from `priority_agent` — write-back still not
  wired into the pipeline itself, only available as standalone connector
  methods.
- Frontend `VITE_API_BASE_URL` — confirmed working (Settings.tsx uses it
  correctly with a `localhost:8000` fallback)

## Session log (append one line per session so history isn't lost)
- 2026-07-16: Scoped + built GitHub MCP integration (OAuth, webhook, MCP
  client/connector), fixed LLM env vars, added Settings UI button.
- 2026-07-16 (later same day): Built PR→task auto-linking + manual
  override through MCP; fixed OAuth redirect bug (relative URL landing
  on backend port + nonexistent frontend route); fixed MCP DNS
  resolution bug (Compose service hostname unresolvable from host-run
  backend); noted new `get_llm_client` import bug in dedup as unfixed.