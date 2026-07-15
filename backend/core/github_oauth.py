"""GitHub OAuth App login flow + encrypted-at-rest token storage.

Replaces the old static GITHUB_TOKEN env var approach. Flow:
  1. Frontend/browser hits GET /auth/github/login -> redirected to GitHub's
     consent screen (the "Sign in to GitHub / Authorize" page).
  2. GitHub redirects back to GET /auth/github/callback?code=...
  3. We exchange the code for an access token and store it.

Requires a GitHub OAuth App (https://github.com/settings/developers) with:
  Authorization callback URL = {PUBLIC_BASE_URL}/auth/github/callback

Env vars needed:
  GITHUB_OAUTH_CLIENT_ID
  GITHUB_OAUTH_CLIENT_SECRET
  PUBLIC_BASE_URL          (e.g. http://localhost:8000)
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

import httpx

from core.state import _get_db, _ensure_db

logger = logging.getLogger(__name__)

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_SCOPES = "repo read:user"

# Single-user demo scope for now — every connection is stored against this id.
# Swap this for the authenticated session's user id once Google login lands.
DEMO_USER_ID = "demo-user"

# In-memory CSRF state store (fine for single-instance demo; move to Redis for prod)
_pending_states: set[str] = set()


def _client_id() -> str:
    return os.environ.get("GITHUB_OAUTH_CLIENT_ID", "")


def _client_secret() -> str:
    return os.environ.get("GITHUB_OAUTH_CLIENT_SECRET", "")


def _base_url() -> str:
    return os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")


def build_authorize_url() -> str:
    if not _client_id():
        raise RuntimeError(
            "GITHUB_OAUTH_CLIENT_ID not set — create a GitHub OAuth App first."
        )
    state = secrets.token_urlsafe(24)
    _pending_states.add(state)
    redirect_uri = f"{_base_url()}/auth/github/callback"
    return (
        f"{GITHUB_AUTHORIZE_URL}?client_id={_client_id()}"
        f"&redirect_uri={redirect_uri}&scope={GITHUB_SCOPES.replace(' ', '%20')}"
        f"&state={state}"
    )


async def exchange_code_for_token(code: str, state: str) -> dict:
    if state not in _pending_states:
        raise RuntimeError("Invalid or expired OAuth state (possible CSRF)")
    _pending_states.discard(state)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": _client_id(),
                "client_secret": _client_secret(),
                "code": code,
                "redirect_uri": f"{_base_url()}/auth/github/callback",
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    if "error" in payload:
        raise RuntimeError(f"GitHub OAuth error: {payload.get('error_description', payload['error'])}")

    access_token = payload["access_token"]
    scope = payload.get("scope", "")

    # fetch the login so the UI can show "Connected as @username"
    async with httpx.AsyncClient(timeout=15.0) as client:
        me = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        me.raise_for_status()
        github_login = me.json().get("login", "")

    save_connection(access_token, scope, github_login)
    return {"github_login": github_login, "scope": scope}


def save_connection(access_token: str, scope: str, github_login: str, user_id: str = DEMO_USER_ID) -> None:
    _ensure_db()
    conn = _get_db()
    conn.execute(
        """
        INSERT INTO oauth_connections (user_id, provider, access_token, scope, github_login, connected_at)
        VALUES (?, 'github', ?, ?, ?, ?)
        ON CONFLICT(user_id, provider) DO UPDATE SET
            access_token = excluded.access_token,
            scope = excluded.scope,
            github_login = excluded.github_login,
            connected_at = excluded.connected_at
        """,
        (user_id, access_token, scope, github_login, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    logger.info("GitHub OAuth connection saved for %s (login=%s)", user_id, github_login)


def get_connection(user_id: str = DEMO_USER_ID) -> Optional[dict]:
    _ensure_db()
    conn = _get_db()
    row = conn.execute(
        "SELECT access_token, scope, github_login, connected_at FROM oauth_connections WHERE user_id = ? AND provider = 'github'",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def disconnect(user_id: str = DEMO_USER_ID) -> None:
    _ensure_db()
    conn = _get_db()
    conn.execute("DELETE FROM oauth_connections WHERE user_id = ? AND provider = 'github'", (user_id,))
    conn.commit()
    conn.close()
