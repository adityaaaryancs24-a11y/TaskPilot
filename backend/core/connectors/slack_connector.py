import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from core.connectors.base import SourceConnector

logger = logging.getLogger(__name__)


class SlackConnector(SourceConnector):
    name = "Slack"

    def __init__(self) -> None:
        self._token = os.environ.get("SLACK_BOT_TOKEN", "")
        self._channels_str = os.environ.get("SLACK_CHANNELS", "#general")
        self._channels = [
            ch.strip() for ch in self._channels_str.split(",") if ch.strip()
        ]
        self._client: Optional[httpx.AsyncClient] = None
        self._conversation_map: dict[str, str] = {}

    async def connect(self) -> bool:
        if not self._token:
            logger.warning("Slack token not configured (SLACK_BOT_TOKEN)")
            self.connected = False
            self.error = "Missing Slack bot token"
            return False
        try:
            self._client = httpx.AsyncClient(
                base_url="https://slack.com/api",
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=30.0,
            )
            resp = await self._client.get("/auth.test")
            body = resp.json()
            if not body.get("ok"):
                logger.warning("Slack auth failed: %s", body.get("error", "unknown"))
                self.connected = False
                self.error = body.get("error", "Slack auth failed")
                return False
            self.connected = True
            self.error = None
            logger.info("Connected to Slack")
            return True
        except Exception as e:
            logger.error("Failed to connect to Slack: %s", e)
            self.connected = False
            self.error = str(e)
            self._client = None
            return False

    async def _build_conversation_map(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        cursor: Optional[str] = None
        try:
            while True:
                params: dict[str, Any] = {
                    "types": "public_channel,private_channel",
                    "limit": 200,
                }
                if cursor:
                    params["cursor"] = cursor
                resp = await self._client.get("/conversations.list", params=params)
                body = resp.json()
                if not body.get("ok"):
                    logger.warning("Failed to list channels: %s", body.get("error"))
                    break
                for ch in body.get("channels", []):
                    mapping[ch["name"]] = ch["id"]
                cursor = body.get("response_metadata", {}).get("next_cursor", "")
                if not cursor:
                    break
        except Exception as e:
            logger.error("Error building conversation map: %s", e)
        return mapping

    def _load_simulated(self) -> list[dict[str, Any]]:
        import json
        from pathlib import Path

        path = (
            Path(__file__).resolve().parent.parent.parent
            / "data"
            / "slack_messages.json"
        )
        if not path.exists():
            logger.warning("Simulated Slack data not found at %s", path)
            return []
        try:
            with open(path) as f:
                raw = json.load(f)
            normalized = []
            for msg in raw:
                sender_username = msg.get("sender", {}).get("username", "unknown") if isinstance(msg.get("sender"), dict) else msg.get("sender", "unknown")
                is_dm = msg.get("channel", "").startswith("DM:")
                channel_name = msg.get("channel", "#general")
                is_direct_mention = msg.get("isDirectMention", False) or "@alex.chen" in msg.get("text", "")
                normalized.append({
                    "id": msg["messageId"],
                    "title": f"Slack message in {channel_name}",
                    "description": msg.get("text", "")[:200],
                    "source": msg["messageId"],
                    "source_type": "slack",
                    "priority": "P1" if is_direct_mention and msg.get("hasActionItem") else "P2",
                    "deadline": None,
                    "owner": "alex.chen" if "@alex.chen" in msg.get("text", "") else None,
                    "status": "open",
                    "dependencies": [],
                    "blocks": [],
                    "raw_text": msg.get("text", ""),
                    "channel": channel_name,
                    "message_ts": msg.get("timestamp", ""),
                    "sender": sender_username,
                    "mentions": msg.get("mentions", []),
                    "is_direct_mention": is_direct_mention,
                    "has_action_item": msg.get("hasActionItem", False),
                    "action_item_text": msg.get("actionItemText"),
                })
            logger.info("Loaded %d simulated Slack messages", len(normalized))
            return normalized
        except Exception as e:
            logger.error("Failed to load simulated Slack data: %s", e)
            return []

    async def fetch_tasks(self, since: Optional[str] = None) -> list[dict[str, Any]]:
        if not self._client or not self.connected:
            logger.info("Slack not connected — using simulated data")
            return self._load_simulated()

        if not self._conversation_map:
            self._conversation_map = await self._build_conversation_map()
            if not self._conversation_map:
                logger.warning("No Slack channels found — using simulated data")
                return self._load_simulated()

        results: list[dict[str, Any]] = []

        for channel_name in self._channels:
            channel_id = None
            name_clean = channel_name.lstrip("#")
            for ch_name, ch_id in self._conversation_map.items():
                if ch_name == name_clean:
                    channel_id = ch_id
                    break
            if not channel_id:
                logger.warning("Channel %s not found in workspace", channel_name)
                continue

            cursor: Optional[str] = None
            try:
                while True:
                    params: dict[str, Any] = {"channel": channel_id, "limit": 100}
                    if since:
                        params["oldest"] = since
                    if cursor:
                        params["cursor"] = cursor

                    resp = await self._client.get(
                        "/conversations.history", params=params
                    )
                    body = resp.json()
                    if not body.get("ok"):
                        logger.warning(
                            "Failed to fetch history for %s: %s",
                            channel_name,
                            body.get("error"),
                        )
                        break

                    for msg in body.get("messages", []):
                        text = msg.get("text", "")
                        if re.search(r"<@\w+>", text):
                            mentioned = re.findall(r"<@(\w+)>", text)
                            ts = msg.get("ts", "")
                            results.append(
                                {
                                    "id": f"SL-{ts.replace('.', '')}",
                                    "title": f"Slack mention in {channel_name}",
                                    "description": text,
                                    "source": f"SL-{ts.replace('.', '')}",
                                    "source_type": "slack",
                                    "priority": "P2",
                                    "deadline": None,
                                    "owner": mentioned[0] if mentioned else None,
                                    "status": "open",
                                    "dependencies": [],
                                    "blocks": [],
                                    "raw_text": text,
                                    "channel": channel_name,
                                    "message_ts": ts,
                                }
                            )

                    cursor = body.get("response_metadata", {}).get("next_cursor", "")
                    if not cursor:
                        break
            except Exception as e:
                logger.error(
                    "Error fetching Slack messages from %s: %s", channel_name, e
                )
                continue

        if not results:
            logger.info(
                "No Slack messages fetched from live API — using simulated data"
            )
            return self._load_simulated()

        self.last_sync = datetime.now(timezone.utc).isoformat()
        logger.info("Fetched %d actionable messages from Slack", len(results))
        return results

    def normalize(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for item in raw:
            normalized.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "description": item.get("description", ""),
                    "source": item["id"],
                    "source_type": "slack",
                    "priority": item.get("priority", "P2"),
                    "deadline": item.get("deadline"),
                    "owner": item.get("owner"),
                    "status": item.get("status", "open"),
                    "dependencies": item.get("dependencies", []),
                    "blocks": item.get("blocks", []),
                    "raw_text": item.get("raw_text", ""),
                    "channel": item.get("channel", ""),
                    "message_ts": item.get("message_ts", ""),
                }
            )
        return normalized

    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            resp = await self._client.get("/auth.test")
            body = resp.json()
            return body.get("ok", False)
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "connected": self.connected,
            "last_sync": self.last_sync,
            "error": self.error,
        }
