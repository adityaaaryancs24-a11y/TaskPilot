import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from core.connectors.base import SourceConnector

logger = logging.getLogger(__name__)


class JiraConnector(SourceConnector):
    name = "Jira"

    def __init__(self) -> None:
        self._url = os.environ.get("JIRA_URL", "").rstrip("/")
        self._email = os.environ.get("JIRA_EMAIL", "")
        self._api_token = os.environ.get("JIRA_API_TOKEN", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        if not self._url or not self._email or not self._api_token:
            logger.warning(
                "Jira credentials not configured (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)"
            )
            self.connected = False
            self.error = "Missing Jira credentials"
            return False
        try:
            auth = httpx.BasicAuth(self._email, self._api_token)
            self._client = httpx.AsyncClient(
                base_url=self._url, auth=auth, timeout=30.0
            )
            resp = await self._client.get("/rest/api/3/myself")
            resp.raise_for_status()
            self.connected = True
            self.error = None
            logger.info("Connected to Jira at %s", self._url)
            return True
        except Exception as e:
            logger.error("Failed to connect to Jira: %s", e)
            self.connected = False
            self.error = str(e)
            self._client = None
            return False

    def _load_simulated(self) -> list[dict[str, Any]]:
        import json
        from pathlib import Path

        path = (
            Path(__file__).resolve().parent.parent.parent / "data" / "jira_board.json"
        )
        if not path.exists():
            logger.warning("Simulated Jira data not found at %s", path)
            return []
        try:
            with open(path) as f:
                raw = json.load(f)
            normalized = []
            for item in raw:
                normalized.append({
                    "id": item["id"],
                    "key": item.get("key", item["id"]),
                    "title": item["summary"],
                    "summary": item["summary"],
                    "description": item.get("description", ""),
                    "source": item["id"],
                    "source_type": "jira",
                    "priority": {"Critical": "P0", "High": "P1", "Medium": "P2", "Low": "P3"}.get(item.get("priority", "Medium"), "P2"),
                    "deadline": item.get("dueDate"),
                    "owner": item.get("assignee", ""),
                    "assignee": item.get("assignee"),
                    "status": {"to do": "open", "in progress": "in_progress", "in review": "in_progress", "done": "done", "blocked": "blocked", "to_do": "open", "in_progress": "in_progress", "in_review": "in_progress"}.get(item.get("status", "To Do").lower().replace(" ", "_"), "open"),
                    "dependencies": [l["id"] for l in item.get("linkedIssues", []) if l.get("type") in ("is blocked by",)],
                    "blocks": [l["id"] for l in item.get("linkedIssues", []) if l.get("type") in ("blocks",)],
                    "raw_text": item.get("description", ""),
                    "type": item.get("type", "Task"),
                    "labels": item.get("labels", []),
                    "storyPoints": item.get("storyPoints"),
                    "reporter": item.get("reporter", ""),
                    "sprint": item.get("sprint", ""),
                    "comments": item.get("comments", []),
                    "vp_escalation": any("sarah.mitchell" in c.get("author", "").lower() for c in item.get("comments", [])),
                    "customer_facing": True,
                })
            logger.info("Loaded %d items from simulated Jira board", len(normalized))
            return normalized
        except Exception as e:
            logger.error("Failed to load simulated Jira data: %s", e)
            return []

    async def fetch_tasks(self, since: Optional[str] = None) -> list[dict[str, Any]]:
        if not self._client or not self.connected:
            logger.info("Jira not connected — using simulated data")
            return self._load_simulated()

        results: list[dict[str, Any]] = []
        start_at = 0
        max_results = 50

        try:
            while True:
                jql_parts = []
                if since:
                    jql_parts.append(f"updated >= '{since}'")
                # Build a scoped JQL (unscoped queries are rejected by the /search/jql endpoint)
                if not jql_parts:
                    # Default: pull open issues from all visible projects
                    jql_parts.append("project IS NOT EMPTY")
                jql_parts.append("ORDER BY created DESC")
                jql = " ".join(jql_parts)

                params: dict[str, Any] = {
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": "id,summary,description,priority,assignee,status,duedate,issuelinks",
                }

                # Jira Cloud requires /rest/api/3/search/jql (the old /3/search was removed)
                resp = await self._client.get("/rest/api/3/search/jql", params=params)
                resp.raise_for_status()
                data = resp.json()

                issues = data.get("issues", [])
                results.extend(issues)

                # New endpoint uses "isLast" instead of "total"
                is_last = data.get("isLast", True)
                if is_last or not issues:
                    break
                start_at += max_results

            self.last_sync = datetime.now(timezone.utc).isoformat()
            logger.info("Fetched %d issues from Jira", len(results))
            return results

        except httpx.HTTPStatusError as e:
            logger.error("Jira API error: %s — falling back to simulated data", e)
            self.error = str(e)
            return self._load_simulated()
        except Exception as e:
            logger.error(
                "Error fetching Jira issues: %s — falling back to simulated data", e
            )
            self.error = str(e)
            return self._load_simulated()

    def normalize(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for issue in raw:
            fields = issue.get("fields", {})
            key = issue.get("key", "")

            priority = None
            if fields.get("priority"):
                raw_priority = fields["priority"].get("name", "")
                priority = self._map_priority(raw_priority)

            assignee = None
            if fields.get("assignee"):
                assignee = fields["assignee"].get("displayName")

            raw_status = None
            if fields.get("status"):
                raw_status = fields["status"].get("name")
            status = self._map_status(raw_status)

            dependencies = []
            blocks = []
            for link in fields.get("issuelinks", []):
                if "outwardIssue" in link:
                    dependencies.append(link["outwardIssue"].get("key", ""))
                if "inwardIssue" in link:
                    blocks.append(link["inwardIssue"].get("key", ""))

            # Convert ADF description to plain text
            description = self._adf_to_text(fields.get("description"))
            raw_text = description

            normalized.append(
                {
                    "id": key,
                    "title": fields.get("summary", ""),
                    "description": description,
                    "source": key,
                    "source_type": "jira",
                    "priority": priority,
                    "deadline": fields.get("duedate"),
                    "owner": assignee,
                    "status": status,
                    "dependencies": dependencies,
                    "blocks": blocks,
                    "raw_text": raw_text,
                }
            )
        return normalized

    @staticmethod
    def _map_status(raw: str | None) -> str:
        """Map Jira status names to Task-compatible values."""
        if not raw:
            return "open"
        mapping = {
            "to do": "open",
            "todo": "open",
            "in progress": "in_progress",
            "in review": "in_progress",
            "review": "in_progress",
            "done": "done",
            "closed": "done",
            "resolved": "done",
            "blocked": "blocked",
        }
        return mapping.get(raw.lower(), "open")

    @staticmethod
    def _map_priority(raw: str) -> str | None:
        """Map Jira priority names to Task P0-P3 values."""
        if not raw:
            return None
        mapping = {
            "highest": "P0",
            "high": "P1",
            "medium": "P2",
            "low": "P3",
            "lowest": "P3",
            "critical": "P0",
            "major": "P1",
            "minor": "P3",
            "trivial": "P3",
            "blocker": "P0",
        }
        return mapping.get(raw.lower())

    @staticmethod
    def _adf_to_text(adf: Any) -> str:
        """Convert Atlassian Document Format to plain text."""
        if adf is None:
            return ""
        if isinstance(adf, str):
            return adf
        if not isinstance(adf, dict):
            return str(adf)
        content = adf.get("content", [])
        return JiraConnector._adf_content_to_text(content)

    @staticmethod
    def _adf_content_to_text(content: list) -> str:
        parts = []
        for node in content:
            node_type = node.get("type", "")
            if node_type == "text":
                text = node.get("text", "")
                marks = node.get("marks", [])
                for mark in marks:
                    if mark.get("type") == "link" and mark.get("attrs", {}).get("href"):
                        text = f"{text} ({mark['attrs']['href']})"
                parts.append(text)
            elif node_type in ("paragraph", "heading", "listItem", "blockquote"):
                parts.append(
                    JiraConnector._adf_content_to_text(node.get("content", []))
                )
                if node_type in ("paragraph", "heading", "blockquote"):
                    parts.append("\n")
            elif node_type in ("bulletList", "orderedList"):
                parts.append(
                    JiraConnector._adf_content_to_text(node.get("content", []))
                )
            elif node_type == "hardBreak":
                parts.append("\n")
            elif node_type == "codeBlock":
                parts.append(
                    JiraConnector._adf_content_to_text(node.get("content", []))
                )
                parts.append("\n")
            elif node_type == "rule":
                parts.append("\n---\n")
            elif node_type == "mention":
                parts.append(f"@{node.get('attrs', {}).get('text', '')}")
        return "".join(parts)

    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            resp = await self._client.get("/rest/api/3/myself")
            resp.raise_for_status()
            return True
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "connected": self.connected,
            "last_sync": self.last_sync,
            "error": self.error,
        }
