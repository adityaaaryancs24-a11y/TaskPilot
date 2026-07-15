# ARCHITECTURE.md

## Pipeline (backend/core/agents/)
```
ingestion_agent → extraction_agent → dedup_agent → priority_agent
   → planning_agent → alert_agent
```
Orchestrated by `orchestrator.py`. Triggered either by:
- `sync_engine.py`'s polling loop (slack, transcript — interval-based)
- Webhook (GitHub — real-time, see `/webhooks/github` in routes.py)
- Manual `/api/refresh` or `/api/inject` calls from the frontend

## Data sources / connectors
Each connector implements `core/connectors/base.py`'s `SourceConnector`
ABC (`connect`, `fetch_tasks`, `normalize`, `health_check`, `get_status`).
Registered in `connector_registry.py`.

| Source | Status | Auth model | Sync mode |
|---|---|---|---|
| GitHub | ✅ active (MCP) | per-user OAuth token | webhook (real-time) + MCP tool calls (on-demand) |
| Slack | ✅ active | static bot token | polling |
| Transcript | ✅ active | n/a | polling |
| Jira | ⏸️ disabled | was static API token | was polling |
| Outlook | ⏸️ disabled | was static client secret | was polling |
| ServiceNow | ⏸️ disabled | was static creds | was polling |

## GitHub MCP integration
```
Browser → GET /auth/github/login → redirect to GitHub OAuth consent
GitHub → GET /auth/github/callback?code=... → token exchanged, stored in
          oauth_connections table (sqlite, single demo user for now)
          → redirects browser to {FRONTEND_URL}/settings?tab=integrations
            (absolute URL — see "OAuth redirect" note below)

GitHub repo → webhook POST /webhooks/github (issues + pull_request events)
          → issues: InjectRequest → reprioritize_with_injection() → pipeline runs
          → pull_request: extract_linked_issue_numbers() (core/pr_linker.py)
            → link_pr_to_task() (core/state.py) for each referenced issue #

Agents (e.g. priority_agent) → core/mcp_client.py MCPClient
          → self-hosted github-mcp-server container (port 9090)
          → GitHub API, using the stored per-user OAuth token as Bearer
```
Why MCP instead of direct REST: single point of truth for GitHub API
access (official server, maintained by GitHub), per-user auth instead of
one shared token, and the same client can call write tools (create_issue,
comment, close) that the old read-only REST connector didn't expose.

Why NOT `api.githubcopilot.com/mcp` (GitHub's hosted endpoint): it
implies a Copilot license per user. We self-host the identical
open-source server instead (`ghcr.io/github/github-mcp-server`), same
code, no Copilot dependency.

### OAuth redirect — host vs. container gotcha (fixed 2026-07-16)
`github_callback()` in `routes.py` originally returned a **relative**
`RedirectResponse("/settings/integrations?...")`. Since GitHub redirects
the browser to the *backend* (`/auth/github/callback` is a FastAPI route),
a relative redirect resolves against the backend's own origin
(`localhost:8000`), not the frontend (`localhost:5173`) — and
`/settings/integrations` isn't even a real frontend route (Integrations
is a tab inside `Settings.tsx`, not a sub-route). Fixed by:
- Using an absolute URL built from `FRONTEND_URL` (env var, defaults to
  `http://localhost:5173`)
- Redirecting to `/settings?tab=integrations` instead
- `Settings.tsx` now reads `?tab=` on initial mount via a `useState`
  initializer, so the redirect lands the user on the right tab instead
  of the default "preferences" tab

### MCP DNS gotcha (fixed 2026-07-16)
`mcp_client.py` defaults `MCP_GITHUB_URL` to
`http://github-mcp-server:9090/mcp` — a Docker Compose **service name**,
only resolvable from inside the Compose network. When the backend runs
on the host (`uvicorn` directly, not containerized) while
`github-mcp-server` runs in Docker, the host can't resolve that
hostname → `[Errno 11001] getaddrinfo failed` (Windows) /
`[Errno -2] Name or service not known` (Linux). Fix: set
`MCP_GITHUB_URL=http://localhost:9090/mcp` in `backend/.env` when the
backend is host-run and the MCP server's port is published to the host
(`ports: ["9090:9090"]` in `docker-compose.yml`). **Requires a full
process restart, not just a `--reload` pickup** — `load_dotenv()` only
runs once at import time in `connector_registry.py`, so editing `.env`
while the server is running has no effect until the process is
stopped and restarted. The same host-vs-container mismatch pattern
applies to `DATABASE_URL` (seen failing against `5432` in local runs —
check if it's pointed at a Compose service name too).

## PR → Task linking (added 2026-07-16)
Auto-detects GitHub PRs that reference a task's originating issue, with
a manual override for cases the auto-detection misses.
```
PR opened/edited/synchronize webhook → routes.py github_webhook()
   → core/pr_linker.py extract_linked_issue_numbers(pr.body)
     (regex matches GitHub's own closing keywords: Fixes/Closes/Resolves #N,
      same-repo only — cross-repo refs are intentionally not matched)
   → core/state.py link_pr_to_task(task_id, pr_url, pr_number, source="auto")
     (dedupes by pr_number; a manual link is never downgraded back to auto)

Manual override:
POST /api/tasks/{task_id}/link-pr        { "pr_url": "..." }
DELETE /api/tasks/{task_id}/link-pr/{pr_number}
```
`Task.linked_prs: Optional[list[dict]]` holds
`{pr_url, pr_number, source, linked_at}` entries.

`GitHubMCPConnector` also gained `fetch_pull_requests()`,
`get_pull_request()`, `create_issue()`, `update_issue()`, and
`add_issue_comment()` (MCP tool calls, same pattern as `fetch_tasks()`).

## Two unrelated things both called "MCP" in this repo — don't confuse them
1. `mcp_server.py` (root) — OUTBOUND. Exposes TaskPilot's own data
   (tasks, plans, metrics) as MCP tools so external clients (Claude
   Desktop, etc.) can query TaskPilot. Untouched by the GitHub work.
2. `github-mcp-server` (docker-compose service) — INBOUND. TaskPilot's
   backend is the MCP *client* here, calling GitHub's tools.

## Auth model (current — intentionally minimal)
Single demo user, no session/JWT layer wired to a login screen yet.
`DEMO_USER_ID = "demo-user"` hardcoded in `github_oauth.py`. The
`oauth_connections` table has a `user_id` column already, so extending to
real multi-user auth (Google login → session → per-user rows) is additive,
not a rewrite — but it hasn't been built.

## LLM
xAI Grok, `grok-4.1-fast`, via OpenAI-compatible endpoint
`https://api.x.ai/v1`. Fallback: Gemini `gemini-2.5-flash`. Config in
`core/config.py` / `core/llm_client.py`.

⚠️ Known issue as of 2026-07-16: `core.llm_client` doesn't currently
export `get_llm_client`, causing dedup's LLM semantic-arbitration step to
fail and silently fall back to embedding-only matching (`deduplicator.py`
logs `LLM dedup arbitration failed for (...): cannot import name
'get_llm_client'`). Also seeing intermittent `400 Bad Request` from the
Grok endpoint itself, separate from the import issue. Neither is fixed
yet — dedup still runs, just without the LLM tiebreaker layer.