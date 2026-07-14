import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from core.connectors.base import SourceConnector

logger = logging.getLogger(__name__)

FIREFLIES_GRAPHQL_URL = "https://api.fireflies.ai/graphql"


class TranscriptConnector(SourceConnector):
    name = "Meeting Transcripts"

    def __init__(self) -> None:
        self._fireflies_key = os.environ.get("FIREFLIES_API_KEY", "")
        self._otter_key = os.environ.get("OTTER_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None
        self._provider: Optional[str] = None

    async def connect(self) -> bool:
        if self._fireflies_key:
            self._client = httpx.AsyncClient(
                base_url=FIREFLIES_GRAPHQL_URL,
                headers={"Authorization": f"Bearer {self._fireflies_key}"},
                timeout=30.0,
            )
            self._provider = "fireflies"
            try:
                query = "{ me { name } }"
                resp = await self._client.post("", json={"query": query})
                resp.raise_for_status()
                data = resp.json()
                if data.get("data", {}).get("me"):
                    self.connected = True
                    self.error = None
                    logger.info("Connected to Fireflies AI")
                    return True
                logger.warning("Fireflies API returned unexpected response")
                self.connected = False
                self.error = "Fireflies auth failed"
                self._client = None
                return False
            except Exception as e:
                logger.error("Failed to connect to Fireflies: %s", e)
                self._client = None
                self._provider = None
                self.connected = False
                self.error = str(e)
                return False

        if self._otter_key:
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self._otter_key}"},
                timeout=30.0,
            )
            self._provider = "otter"
            try:
                resp = await self._client.get("https://otter.ai/api/v1/me")
                resp.raise_for_status()
                self.connected = True
                self.error = None
                logger.info("Connected to Otter AI")
                return True
            except Exception as e:
                logger.error("Failed to connect to Otter AI: %s", e)
                self._client = None
                self._provider = None
                self.connected = False
                self.error = str(e)
                return False

        logger.warning(
            "No transcript API key configured (FIREFLIES_API_KEY or OTTER_API_KEY)"
        )
        self.connected = False
        self.error = "Missing transcript API key"
        return False

    async def fetch_tasks(self, since: Optional[str] = None) -> list[dict[str, Any]]:
        if not self._client or not self.connected:
            logger.info(
                "Transcript connector not connected — using simulated transcript data"
            )
            return self._load_simulated()

        if self._provider == "fireflies":
            return await self._fetch_fireflies(since)
        elif self._provider == "otter":
            return await self._fetch_otter(since)
        return self._load_simulated()

    async def _fetch_fireflies(
        self, since: Optional[str] = None
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor: Optional[str] = None

        date_filter = ""
        if since:
            date_filter = f', date: {{ gte: "{since}" }}'

        try:
            while True:
                query = (
                    """
                query($cursor: String) {
                    transcripts(cursor: $cursor %s, limit: 50) {
                        title
                        id
                        date
                        participants
                        sentences {
                            text
                        }
                    }
                }
                """
                    % date_filter
                )

                variables: dict[str, Any] = {}
                if cursor:
                    variables["cursor"] = cursor

                resp = await self._client.post(
                    "",
                    json={"query": query, "variables": variables},
                )
                resp.raise_for_status()
                data = resp.json()

                transcripts_data = data.get("data", {}).get("transcripts", {})
                if isinstance(transcripts_data, dict):
                    items = transcripts_data.get("transcripts", [])
                    cursor = transcripts_data.get("cursor", "")
                elif isinstance(transcripts_data, list):
                    items = transcripts_data
                    cursor = None
                else:
                    items = []
                    cursor = None

                for t in items:
                    full_text = " ".join(
                        s.get("text", "") for s in t.get("sentences", [])
                    )
                    meeting_id = t.get("id", "")
                    results.append(
                        {
                            "id": meeting_id,
                            "title": t.get("title", "Meeting Transcript"),
                            "description": full_text[:300],
                            "source": meeting_id,
                            "source_type": "transcript",
                            "priority": None,
                            "deadline": None,
                            "owner": None,
                            "status": "open",
                            "dependencies": [],
                            "blocks": [],
                            "raw_text": full_text,
                            "meeting_date": t.get("date", ""),
                            "participants": t.get("participants", []),
                        }
                    )

                if not cursor:
                    break

            self.last_sync = datetime.now(timezone.utc).isoformat()
            logger.info("Fetched %d transcripts from Fireflies", len(results))
            return results

        except Exception as e:
            logger.error("Error fetching Fireflies transcripts: %s", e)
            self.error = str(e)
            return []

    async def _fetch_otter(self, since: Optional[str] = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 1

        try:
            while True:
                params: dict[str, Any] = {"page": page, "limit": 50}
                if since:
                    params["start_date"] = since

                resp = await self._client.get(
                    "https://otter.ai/api/v1/transcripts", params=params
                )
                resp.raise_for_status()
                data = resp.json()

                items = data.get("data", []) if isinstance(data, dict) else data
                if not items:
                    break

                for t in items:
                    meeting_id = t.get("id", "")
                    full_text = t.get("text", "") or t.get("transcript", "") or ""
                    results.append(
                        {
                            "id": meeting_id,
                            "title": t.get("title", "Meeting Transcript"),
                            "description": full_text[:300],
                            "source": meeting_id,
                            "source_type": "transcript",
                            "priority": None,
                            "deadline": None,
                            "owner": None,
                            "status": "open",
                            "dependencies": [],
                            "blocks": [],
                            "raw_text": full_text,
                            "meeting_date": t.get("date", "")
                            or t.get("created_at", ""),
                            "participants": t.get("participants", []),
                        }
                    )

                page += 1
                if len(items) < 50:
                    break

            self.last_sync = datetime.now(timezone.utc).isoformat()
            logger.info("Fetched %d transcripts from Otter AI", len(results))
            return results

        except Exception as e:
            logger.error("Error fetching Otter transcripts: %s", e)
            self.error = str(e)
            return []

    def _load_simulated(self) -> list[dict[str, Any]]:
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent.parent / "data" / "meeting_transcript.txt"
        if not path.exists():
            logger.warning("Simulated transcript data not found at %s", path)
            return []
        try:
            with open(path) as f:
                text = f.read()
            items = [
                {
                    "id": "transcript_001",
                    "title": "Sprint 46 Retro + Sprint 47 Kick-off — Jan 12, 2024",
                    "description": text[:300],
                    "source": "transcript_001",
                    "source_type": "transcript",
                    "priority": None,
                    "deadline": None,
                    "owner": None,
                    "status": "open",
                    "dependencies": [],
                    "blocks": [],
                    "raw_text": text,
                    "meeting_date": "2024-01-12T14:00:00Z",
                    "participants": [
                        "David Park",
                        "Alex Chen",
                        "Jordan Lee",
                        "Priya Sharma",
                        "Marcus Webb",
                        "Sarah Mitchell",
                    ],
                }
            ]
            logger.info("Loaded simulated meeting transcript (%d chars)", len(text))
            return items
        except Exception as e:
            logger.error("Failed to load simulated transcript: %s", e)
            return []

    def normalize(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for item in raw:
            normalized.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "description": item.get("description", ""),
                    "source": item["id"],
                    "source_type": "transcript",
                    "priority": item.get("priority"),
                    "deadline": item.get("deadline"),
                    "owner": item.get("owner"),
                    "status": item.get("status", "open"),
                    "dependencies": item.get("dependencies", []),
                    "blocks": item.get("blocks", []),
                    "raw_text": item.get("raw_text", ""),
                    "meeting_date": item.get("meeting_date", ""),
                    "participants": item.get("participants", []),
                }
            )
        return normalized

    async def health_check(self) -> bool:
        if not self._client or not self._provider:
            return False
        try:
            if self._provider == "fireflies":
                query = "{ me { name } }"
                resp = await self._client.post("", json={"query": query})
                resp.raise_for_status()
                data = resp.json()
                return bool(data.get("data", {}).get("me"))
            elif self._provider == "otter":
                resp = await self._client.get("https://otter.ai/api/v1/me")
                resp.raise_for_status()
                return True
            return False
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "connected": self.connected,
            "last_sync": self.last_sync,
            "error": self.error,
            "provider": self._provider,
        }
