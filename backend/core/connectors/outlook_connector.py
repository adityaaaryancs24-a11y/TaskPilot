import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from core.connectors.base import SourceConnector

logger = logging.getLogger(__name__)


class OutlookConnector(SourceConnector):
    name = "Outlook"

    def __init__(self) -> None:
        self._client_id = os.environ.get("AZURE_CLIENT_ID", "")
        self._client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
        self._tenant_id = os.environ.get("AZURE_TENANT_ID", "")
        self._access_token: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def _acquire_token(self) -> Optional[str]:
        url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, data=data)
                resp.raise_for_status()
                body = resp.json()
                token = body.get("access_token")
                if token:
                    logger.info("Acquired OAuth2 token for Microsoft Graph")
                    return token
                logger.warning("No access_token in token response")
                return None
        except Exception as e:
            logger.error("Failed to acquire Microsoft Graph token: %s", e)
            return None

    async def connect(self) -> bool:
        if not self._client_id or not self._client_secret or not self._tenant_id:
            logger.warning(
                "Azure credentials not configured (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)"
            )
            self.connected = False
            self.error = "Missing Azure credentials"
            return False
        token = await self._acquire_token()
        if not token:
            self.connected = False
            self.error = "Failed to acquire token"
            return False
        self._access_token = token
        self._client = httpx.AsyncClient(
            base_url="https://graph.microsoft.com/v1.0",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        self.connected = True
        self.error = None
        logger.info("Connected to Microsoft Graph")
        return True

    async def fetch_tasks(self, since: Optional[str] = None) -> list[dict[str, Any]]:
        if not self._client or not self.connected:
            logger.info("Outlook not connected — using simulated email data")
            return self._load_simulated()

        results: list[dict[str, Any]] = []
        url = "/me/messages"

        params: dict[str, Any] = {
            "$top": 100,
            "$select": "id,subject,bodyPreview,body,from,receivedDateTime,isRead",
            "$orderby": "receivedDateTime DESC",
        }
        if since:
            params["$filter"] = f"receivedDateTime ge {since}"

        try:
            while url:
                resp = await self._client.get(
                    url, params=params if "?" not in url else None
                )
                resp.raise_for_status()
                data = resp.json()

                messages = data.get("value", [])
                results.extend(messages)

                url = data.get("@odata.nextLink", "")
                params = {}

            self.last_sync = datetime.now(timezone.utc).isoformat()
            logger.info("Fetched %d emails from Outlook", len(results))
            return results

        except httpx.HTTPStatusError as e:
            logger.error("Graph API error: %s — falling back to simulated data", e)
            self.error = str(e)
            return self._load_simulated()
        except Exception as e:
            logger.error(
                "Error fetching Outlook emails: %s — falling back to simulated data", e
            )
            self.error = str(e)
            return self._load_simulated()

    def _load_simulated(self) -> list[dict[str, Any]]:
        import json
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent.parent / "data" / "outlook_emails.json"
        if not path.exists():
            logger.warning("Simulated email data not found at %s", path)
            return []
        try:
            with open(path) as f:
                raw = json.load(f)
            normalized = []
            for msg in raw:
                sender_name = msg.get("from", {}).get("name", "") if isinstance(msg.get("from"), dict) else msg.get("from", "")
                sender_email = msg.get("from", {}).get("email", "") if isinstance(msg.get("from"), dict) else msg.get("from", "")
                sender_str = f"{sender_name} <{sender_email}>" if sender_name and sender_email else (sender_name or sender_email)
                body_text = msg.get("body", "")
                priority = "P1" if msg.get("priority") == "high" else ("P2" if msg.get("priority") == "normal" else "P3")
                vp_escalation = "sarah.mitchell" in sender_email.lower() and "urgent" in msg.get("subject", "").lower()
                normalized.append(
                    {
                        "id": msg["messageId"],
                        "title": msg["subject"],
                        "description": body_text[:200] if body_text else "",
                        "source": msg["messageId"],
                        "source_type": "email",
                        "priority": priority,
                        "deadline": None,
                        "owner": sender_str,
                        "status": "open",
                        "dependencies": [],
                        "blocks": [],
                        "raw_text": body_text,
                        "from": sender_str,
                        "from_email": sender_email,
                        "timestamp": msg.get("receivedAt", ""),
                        "isRead": msg.get("isRead", False),
                        "hasActionItems": msg.get("hasActionItems", False),
                        "extractedActionItems": msg.get("extractedActionItems", []),
                        "category": msg.get("category", ""),
                        "vp_escalation": vp_escalation,
                        "customer_facing": "client" in body_text.lower() or "customer" in body_text.lower(),
                    }
                )
            logger.info("Loaded %d simulated emails", len(normalized))
            return normalized
        except Exception as e:
            logger.error("Failed to load simulated emails: %s", e)
            return []

    def normalize(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for msg in raw:
            sender = msg.get("from", {})
            email = ""
            if isinstance(sender, dict):
                email_addr = sender.get("emailAddress", {})
                if isinstance(email_addr, dict):
                    email = email_addr.get("address", "")

            body_preview = msg.get("bodyPreview", "") or ""
            body = msg.get("body", {})
            body_content = ""
            if isinstance(body, dict):
                body_content = body.get("content", "") or ""

            normalized.append(
                {
                    "id": msg.get("id", ""),
                    "title": msg.get("subject", "(no subject)"),
                    "description": body_preview,
                    "source": msg.get("id", ""),
                    "source_type": "email",
                    "priority": "P2",
                    "deadline": None,
                    "owner": None,
                    "status": "open",
                    "dependencies": [],
                    "blocks": [],
                    "raw_text": body_content,
                    "from": email,
                    "timestamp": msg.get("receivedDateTime", ""),
                }
            )
        return normalized

    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            resp = await self._client.get("/me")
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
