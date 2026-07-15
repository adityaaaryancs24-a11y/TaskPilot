"""GitHub connector — MCP edition.

Replaces github_connector.py's direct httpx calls to api.github.com.
- Auth: per-user OAuth token from core.github_oauth (not a static env token)
- Reads: primarily driven by GitHub webhooks now (see /webhooks/github in
  routes.py); fetch_tasks() below is kept for manual "sync now" / backfill
  and calls the MCP tool `list_issues` instead of REST.
- Writes: priority_agent / orchestrator can call other MCP tools
  (create_issue, add_issue_comment, update_issue) through the same client
  for actions initiated by TaskPilot.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from core.connectors.base import SourceConnector
from core.github_oauth import get_connection
from core.mcp_client import get_github_mcp_client, MCPClientError

logger = logging.getLogger(__name__)


class GitHubMCPConnector(SourceConnector):
    name = "GitHub"

    def __init__(self) -> None:
        self._owner = os.environ.get("GITHUB_REPO_OWNER", "")
        self._repo = os.environ.get("GITHUB_REPO_NAME", "")
        self._client = None

    async def connect(self) -> bool:
        conn = get_connection()
        if not conn:
            logger.warning("No GitHub OAuth connection yet — visit /auth/github/login")
            self.connected = False
            self.error = "Not connected — complete GitHub OAuth login first"
            return False
        try:
            self._client = get_github_mcp_client(conn["access_token"])
            await self._client.initialize()
            self.connected = True
            self.error = None
            logger.info("Connected to GitHub MCP server as %s", conn.get("github_login"))
            return True
        except MCPClientError as e:
            logger.error("Failed to connect to GitHub MCP server: %s", e)
            self.connected = False
            self.error = str(e)
            self._client = None
            return False

    async def fetch_tasks(self) -> list[dict[str, Any]]:
        """Manual/backfill sync — normal ingestion now happens via webhook."""
        if not self._client:
            return []
        if not (self._owner and self._repo):
            logger.warning("GITHUB_REPO_OWNER/GITHUB_REPO_NAME not set, skipping fetch_tasks")
            return []
        try:
            result = await self._client.call_tool(
                "list_issues",
                {"owner": self._owner, "repo": self._repo, "state": "open"},
            )
            return result if isinstance(result, list) else result.get("issues", [])
        except MCPClientError as e:
            logger.error("GitHub MCP list_issues failed: %s", e)
            self.error = str(e)
            return []

    def normalize(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for item in raw:
            normalized.append(
                {
                    "id": f"github-{item.get('number', item.get('id'))}",
                    "title": item.get("title", "Untitled GitHub issue"),
                    "description": item.get("body", ""),
                    "source_type": "github",
                    "source_url": item.get("html_url"),
                    "created_at": item.get("created_at"),
                    "labels": [l.get("name") if isinstance(l, dict) else l for l in item.get("labels", [])],
                    "assignee": (item.get("assignee") or {}).get("login") if item.get("assignee") else None,
                }
            )
        return normalized

    async def health_check(self) -> bool:
        return self.connected

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "connected": self.connected,
            "error": self.error,
            "last_sync": self.last_sync,
            "mode": "mcp",
        }
