# GitHub OAuth + MCP setup

## 1. Create a GitHub OAuth App
GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
- Homepage URL: `http://localhost:8000` (or your deployed URL)
- Authorization callback URL: `http://localhost:8000/auth/github/callback`
- Copy the Client ID and generate a Client Secret

## 2. backend/.env
```
GITHUB_OAUTH_CLIENT_ID=xxx
GITHUB_OAUTH_CLIENT_SECRET=xxx
PUBLIC_BASE_URL=http://localhost:8000
GITHUB_REPO_OWNER=your-org-or-username
GITHUB_REPO_NAME=your-repo
MCP_GITHUB_URL=http://github-mcp-server:9090/mcp
```

## 3. Start everything
```
docker compose up -d
```
This now also starts `github-mcp-server` (the official self-hosted image,
`ghcr.io/github/github-mcp-server`) on port 9090.

## 4. Connect GitHub
Visit `http://localhost:8000/auth/github/login` in a browser — you'll see
the standard GitHub "Sign in to GitHub / Authorize" screen (same as the
screenshot), approve it, and you're redirected back with the token stored
in `oauth_connections` (sqlite table, single demo user for now).

Check connection: `GET /auth/github/status`

## 5. Webhook (real-time sync)
On your GitHub repo: Settings → Webhooks → Add webhook
- Payload URL: `http://<your-public-host>/webhooks/github`
- Content type: `application/json`
- Events: Issues (at minimum; add Pull requests / Issue comments later)

Locally you'll need a tunnel (ngrok/cloudflared) since GitHub needs to
reach this URL from the internet.

## What changed
- `github_connector.py` (direct REST + static PAT) → replaced by
  `github_mcp_connector.py` (MCP tool calls + per-user OAuth token)
- `jira_connector.py`, `outlook_connector.py`, `servicenow_connector.py` →
  disabled in `connector_registry.py` (commented out, not deleted)
- New: `core/github_oauth.py`, `core/mcp_client.py`,
  `/auth/github/*` routes, `/webhooks/github` route
- New table: `oauth_connections` in `backend/db/schema.sql`
