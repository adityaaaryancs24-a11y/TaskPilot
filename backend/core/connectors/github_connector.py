import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from core.connectors.base import SourceConnector

logger = logging.getLogger(__name__)


class GitHubConnector(SourceConnector):
    name = "GitHub"

    def __init__(self) -> None:
        self._token = os.environ.get("GITHUB_TOKEN", "")
        self._owner = os.environ.get("GITHUB_REPO_OWNER", "taskpilot-ai")
        self._repo = os.environ.get("GITHUB_REPO_NAME", "backend")
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        if not self._token:
            logger.warning("GitHub token not configured (GITHUB_TOKEN)")
            self.connected = False
            self.error = "Missing GitHub token"
            return False
        try:
            self._client = httpx.AsyncClient(
                base_url="https://api.github.com",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=30.0,
            )
            resp = await self._client.get("/user")
            resp.raise_for_status()
            self.connected = True
            self.error = None
            logger.info("Connected to GitHub as %s/%s", self._owner, self._repo)
            return True
        except Exception as e:
            logger.error("Failed to connect to GitHub: %s", e)
            self.connected = False
            self.error = str(e)
            self._client = None
            return False

    def _load_simulated(self) -> list[dict[str, Any]]:
        import json
        from pathlib import Path

        path = (
            Path(__file__).resolve().parent.parent.parent
            / "data"
            / "github_samples.json"
        )
        if not path.exists():
            logger.warning("Simulated GitHub data not found at %s", path)
            return []
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load simulated GitHub data: %s", e)
            return []

    async def fetch_tasks(self, since: Optional[str] = None) -> list[dict[str, Any]]:
        if not self._client or not self.connected:
            logger.info("GitHub not connected — using simulated data")
            return self._load_simulated()

        results: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        try:
            while True:
                params: dict[str, Any] = {
                    "state": "all",
                    "per_page": per_page,
                    "page": page,
                }
                if since:
                    params["since"] = since

                url = f"/repos/{self._owner}/{self._repo}/issues"
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                issues = resp.json()

                for issue in issues:
                    if "pull_request" in issue:
                        continue
                    results.append(issue)

                link_header = resp.headers.get("Link", "")
                if not re.search(r'rel="next"', link_header):
                    break
                page += 1

            pr_page = 1
            while True:
                params = {
                    "state": "all",
                    "per_page": per_page,
                    "page": pr_page,
                    "sort": "updated",
                    "direction": "desc",
                }
                if since:
                    params["since"] = since

                url = f"/repos/{self._owner}/{self._repo}/pulls"
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                prs = resp.json()

                for pr in prs:
                    pr["_is_pull_request"] = True
                    results.append(pr)

                link_header = resp.headers.get("Link", "")
                if not re.search(r'rel="next"', link_header):
                    break
                pr_page += 1

            self.last_sync = datetime.now(timezone.utc).isoformat()
            logger.info("Fetched %d items (issues + PRs) from GitHub", len(results))
            return results

        except httpx.HTTPStatusError as e:
            logger.error("GitHub API error: %s — falling back to simulated data", e)
            self.error = str(e)
            return self._load_simulated()
        except Exception as e:
            logger.error(
                "Error fetching GitHub items: %s — falling back to simulated data", e
            )
            self.error = str(e)
            return self._load_simulated()

    def normalize(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for issue in raw:
            number = issue.get("number", 0)
            is_pr = issue.get("_is_pull_request", False)
            issue_id = f"{'PR' if is_pr else 'GH'}-{number}"

            priority = None
            for label in issue.get("labels", []):
                name = label.get("name", "")
                if name.upper().startswith("P") and len(name) == 2:
                    priority = name.upper()
                    break

            milestone = issue.get("milestone")
            deadline = milestone.get("due_on") if milestone else None

            assignee = None
            if issue.get("assignee"):
                assignee = issue["assignee"].get("login")
            elif issue.get("assignees"):
                assignees = issue["assignees"]
                if assignees:
                    assignee = assignees[0].get("login")

            body = issue.get("body") or ""

            normalized.append(
                {
                    "id": issue_id,
                    "title": issue.get("title", ""),
                    "description": body,
                    "source": issue_id,
                    "source_type": "github",
                    "priority": priority,
                    "deadline": deadline,
                    "owner": assignee,
                    "status": issue.get("state", "open"),
                    "dependencies": [],
                    "blocks": [],
                    "raw_text": body,
                    "repo": f"{self._owner}/{self._repo}",
                    "issue_number": number,
                    "is_pull_request": is_pr,
                    "pr_state": issue.get("state", "open") if is_pr else None,
                    "mergeable": issue.get("mergeable") if is_pr else None,
                    "draft": issue.get("draft", False) if is_pr else None,
                    "review_comments": issue.get("review_comments", 0)
                    if is_pr
                    else None,
                }
            )
        return normalized

    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            resp = await self._client.get("/user")
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
