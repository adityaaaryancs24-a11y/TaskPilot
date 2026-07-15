"""Minimal MCP client speaking the Streamable HTTP transport (JSON-RPC 2.0
over a single POST endpoint). Used to talk to the self-hosted
github-mcp-server container instead of calling the GitHub REST API directly.

Server ref: github/github-mcp-server, run with --transport streamable-http,
exposed at MCP_GITHUB_URL (default http://github-mcp-server:9090/mcp).
"""

from __future__ import annotations

import itertools
import logging
import os
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_id_counter = itertools.count(1)


class MCPClientError(Exception):
    pass


class MCPClient:
    """One client per (server, user access token) — GitHub OAuth tokens are
    per-user, so don't share a client across users."""

    def __init__(self, base_url: str, bearer_token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self._token = bearer_token
        self._session_id: Optional[str] = None

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    async def _rpc(self, method: str, params: Optional[dict] = None) -> dict:
        payload = {"jsonrpc": "2.0", "id": next(_id_counter), "method": method}
        if params is not None:
            payload["params"] = params

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.base_url, json=payload, headers=self._headers())
            if resp.status_code >= 400:
                raise MCPClientError(f"MCP server error {resp.status_code}: {resp.text[:300]}")
            session_id = resp.headers.get("Mcp-Session-Id")
            if session_id:
                self._session_id = session_id
            data = resp.json()

        if "error" in data:
            raise MCPClientError(f"MCP tool error: {data['error']}")
        return data.get("result", {})

    async def initialize(self) -> dict:
        return await self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "taskpilot-backend", "version": "1.0"},
            },
        )

    async def list_tools(self) -> list[dict]:
        result = await self._rpc("tools/list")
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: Optional[dict] = None) -> Any:
        result = await self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        return result.get("content", result)


def get_github_mcp_client(access_token: str) -> MCPClient:
    base_url = os.environ.get("MCP_GITHUB_URL", "http://github-mcp-server:9090/mcp")
    return MCPClient(base_url, bearer_token=access_token)
