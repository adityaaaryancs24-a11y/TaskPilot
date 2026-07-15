# REPOSITORY_MAP.md

## Top level
```
backend/            FastAPI app, agents, connectors, tests
frontend/            React + TS + Vite app
k8s/                  Kubernetes manifests
monitoring/         Prometheus config
mcp_server.py       Outbound MCP server — exposes TaskPilot's OWN data
                      to external AI clients (Claude Desktop etc). NOT
                      related to the GitHub/Jira/Outlook MCP integration.
docker-compose.yml
SETUP_GITHUB_MCP.md  Setup steps for the GitHub OAuth App + MCP server
docs/                 This folder — persistent context, read instead of zip
```

## backend/core/  (the important stuff)
```
agents/
  orchestrator.py       coordinates the pipeline
  ingestion_agent.py     -> extraction_agent.py -> dedup_agent.py
  priority_agent.py      -> planning_agent.py -> alert_agent.py

connector_registry.py    registry of active connectors (github, slack,
                           transcript). jira/outlook/servicenow commented
                           out, not deleted — see PROJECT_CONTEXT.md.
                           NOTE: connectors are constructed eagerly at
                           import time (module-level dict), not lazily
                           despite the _get_x() helper names.
connectors/
  github_mcp_connector.py   ACTIVE — MCP-based GitHub connector. Reads
                              (fetch_tasks/list_issues) are mostly a
                              manual/backfill path now; normal ingestion
                              is webhook-driven. Also has
                              fetch_pull_requests(), get_pull_request(),
                              create_issue(), update_issue(),
                              add_issue_comment() (NEW 2026-07-16).
  github_connector.py        OLD — direct REST, unused, kept for reference
  jira_connector.py          disabled
  outlook_connector.py       disabled
  servicenow_connector.py    disabled
  slack_connector.py         active, unchanged
  transcript_connector.py    active, unchanged
  base.py                    SourceConnector ABC all connectors implement

github_oauth.py     GitHub OAuth App login/callback + token storage
mcp_client.py         generic MCP Streamable-HTTP JSON-RPC client.
                       MCP_GITHUB_URL env var — must be
                       http://localhost:9090/mcp when the backend runs on
                       the host and github-mcp-server runs in Docker
                       Compose (the Compose service hostname isn't
                       resolvable from outside the Compose network)
pr_linker.py          NEW (2026-07-16) — extract_linked_issue_numbers():
                       regex-matches GitHub's PR closing keywords
                       (Fixes/Closes/Resolves #N) to auto-link PRs to tasks
sync_engine.py         polling loop (still used for slack/transcript;
                           github now relies on webhook, not this)
state.py                 sqlite fallback store + db helpers (_get_db etc).
                           NEW: link_pr_to_task() — attaches a PR to a task,
                           dedupes by pr_number, source="auto"|"manual".
                           ⚠️ several routes.py callers still do
                           `save_state(store)` instead of
                           `save_state(store.current_tasks, store.current_plan)`
                           — signature mismatch, not yet audited/fixed.
config.py               pydantic Settings, reads backend/.env
deduplicator.py, prioritizer.py, embedding_model.py,
dependency_analyzer.py, calendar_planner.py, weekly_summary.py,
normalizer.py, rate_limiter.py, auth.py, input_sanitizer.py,
websocket_manager.py, prompts.py, llm_client.py    supporting modules.
  ⚠️ llm_client.py: deduplicator.py currently fails to import
  get_llm_client from this module (dedup falls back to embedding-only
  matching) — unfixed as of 2026-07-16, not part of the MCP work.
```

## backend/api/
```
routes.py     ALL HTTP routes.
                GitHub OAuth: /auth/github/login, /auth/github/callback
                  (redirect fixed 2026-07-16 — now absolute FRONTEND_URL,
                  targets /settings?tab=integrations, redirects to an
                  error state on failure instead of raising raw 500),
                  /auth/github/status, /auth/github/disconnect
                /webhooks/github — handles `issues` (unchanged) AND
                  `pull_request` events (NEW 2026-07-16, auto-links via
                  pr_linker.py + link_pr_to_task())
                /api/tasks/{task_id}/link-pr [POST] and
                  /api/tasks/{task_id}/link-pr/{pr_number} [DELETE]
                  (NEW 2026-07-16 — manual PR linking)
main.py       FastAPI app instantiation, includes routes.router
```

## backend/db/
```
schema.sql    sqlite schema. Added: oauth_connections table
              (user_id, provider, access_token, scope, github_login,
              connected_at)
```

## backend/models/
```
task.py       Task model. NEW field: linked_prs: Optional[list[dict]]
              (entries: {pr_url, pr_number, source, linked_at})
```

## frontend/src/app/components/
```
screens/       one file per major screen (Dashboard, Settings, Timeline,
                 Priorities, Dependencies, Notifications, HiddenTasks,
                 DedupGroups, Screen0-6)
screens/Settings.tsx   Integrations tab lives here (not a separate
                          route — /settings?tab=integrations, read via
                          a useState initializer on mount, fixed
                          2026-07-16 so the OAuth redirect lands on the
                          right tab). Owns GitHub connection state
                          (githubStatus) via GET /auth/github/status on
                          mount + a manual Connect/Disconnect button —
                          confirmed working correctly as written; no
                          spurious auto-disconnect bug (that was
                          initially suspected but ruled out — the
                          disconnect calls seen in logs were manual
                          testing, not a code bug).
shared/         reusable components (Card, TopNav, Sidebar, TaskCard, etc)
ui/               shadcn/ui primitives, not project-specific
api/taskpilot.ts   frontend's API client — check here for existing fetch
                     helper patterns before adding new ones
```

## Env vars that matter (backend/.env — never share actual values in chat)
```
LLM_API_KEY, LLM_MODEL=grok-4.1-fast, LLM_BASE_URL=https://api.x.ai/v1
GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET
PUBLIC_BASE_URL, MCP_GITHUB_URL   <- must be http://localhost:9090/mcp
                                     for host-run backend (see mcp_client.py
                                     note above); needs a FULL restart to
                                     take effect, not just --reload
FRONTEND_URL                       <- NEW (2026-07-16), used by the OAuth
                                     callback redirect, defaults to
                                     http://localhost:5173
GITHUB_REPO_OWNER, GITHUB_REPO_NAME
DATABASE_URL, REDIS_URL, SECRET_KEY   <- DATABASE_URL may have the same
                                          host-vs-Compose-hostname issue
                                          as MCP_GITHUB_URL, unconfirmed
```