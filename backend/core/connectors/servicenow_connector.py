import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from core.connectors.base import SourceConnector

logger = logging.getLogger(__name__)

PRIORITY_MAP = {
    "1": "P0",
    "2": "P1",
    "3": "P2",
    "4": "P3",
    "5": "P4",
}


class ServiceNowConnector(SourceConnector):
    name = "ServiceNow"

    def __init__(self) -> None:
        self._url = os.environ.get("SERVICENOW_URL", "").rstrip("/")
        self._user = os.environ.get("SERVICENOW_USER", "")
        self._password = os.environ.get("SERVICENOW_PASSWORD", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        if not self._url or not self._user or not self._password:
            logger.warning(
                "ServiceNow credentials not configured (SERVICENOW_URL, USER, PASSWORD)"
            )
            self.connected = False
            self.error = "Missing ServiceNow credentials"
            return False
        try:
            auth = httpx.BasicAuth(self._user, self._password)
            self._client = httpx.AsyncClient(
                base_url=self._url, auth=auth, timeout=30.0
            )
            resp = await self._client.get(
                "/api/now/table/incident", params={"sysparm_limit": 1}
            )
            resp.raise_for_status()
            self.connected = True
            self.error = None
            logger.info("Connected to ServiceNow at %s", self._url)
            return True
        except Exception as e:
            logger.error("Failed to connect to ServiceNow: %s", e)
            self.connected = False
            self.error = str(e)
            self._client = None
            return False

    async def fetch_tasks(self, since: Optional[str] = None) -> list[dict[str, Any]]:
        if not self._client or not self.connected:
            logger.info("ServiceNow not connected — using simulated defect data")
            return self._load_simulated()

        results: list[dict[str, Any]] = []
        offset = 0
        limit = 100

        try:
            while True:
                params: dict[str, Any] = {
                    "sysparm_offset": offset,
                    "sysparm_limit": limit,
                    "sysparm_fields": "sys_id,short_description,description,priority,assigned_to,state,sys_updated_on",
                }
                if since:
                    params["sysparm_query"] = (
                        f"sys_updated_on>=javascript:gs.dateGenerate('{since}','start')"
                    )

                resp = await self._client.get("/api/now/table/incident", params=params)
                resp.raise_for_status()
                data = resp.json()

                records = data.get("result", [])
                results.extend(records)

                if len(records) < limit:
                    break
                offset += limit

            self.last_sync = datetime.now(timezone.utc).isoformat()
            logger.info("Fetched %d incidents from ServiceNow", len(results))
            return results

        except httpx.HTTPStatusError as e:
            logger.error("ServiceNow API error: %s — falling back to simulated data", e)
            self.error = str(e)
            return self._load_simulated()
        except Exception as e:
            logger.error(
                "Error fetching ServiceNow incidents: %s — falling back to simulated data",
                e,
            )
            self.error = str(e)
            return self._load_simulated()

    def _load_simulated(self) -> list[dict[str, Any]]:
        import json
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent.parent / "data" / "servicenow_defects.json"
        if not path.exists():
            logger.warning("Simulated ServiceNow defect data not found at %s", path)
            return []
        try:
            with open(path) as f:
                raw = json.load(f)
            normalized = []
            for d in raw:
                status = d.get("state", "New")
                status = status.lower().replace(" ", "_")
                # Map ServiceNow state values to our internal format
                state_map = {"new": "open", "in_progress": "in_progress", "pending": "blocked", "resolved": "done", "closed": "done"}
                internal_status = state_map.get(status, "open")
                priority_map = {"P1": "P0", "P2": "P1", "P3": "P2", "P4": "P3"}
                priority = d.get("severity", "P3")
                internal_priority = priority_map.get(priority, priority)
                normalized.append(
                    {
                        "id": d.get("incidentId", d["id"]),
                        "title": d["title"],
                        "description": d.get("description", ""),
                        "source": d.get("incidentId", d["id"]),
                        "source_type": "defect",
                        "priority": internal_priority,
                        "deadline": d.get("slaDeadline"),
                        "owner": d.get("assignedTo", ""),
                        "status": internal_status,
                        "dependencies": [],
                        "blocks": [],
                        "raw_text": d.get("description", ""),
                        "category": "incident",
                        "sla_status": d.get("slaStatus", "active"),
                        "escalation_flag": d.get("escalationFlag", False),
                        "escalated_by": d.get("escalatedBy"),
                        "severity": priority,
                        "affected_system": d.get("affectedSystem", ""),
                        "affected_customers": d.get("affectedCustomers", ""),
                        "related_jira": d.get("relatedJiraId"),
                        "vp_escalation": d.get("escalationFlag", False) and d.get("escalatedBy") == "VP of Engineering",
                        "customer_facing": d.get("affectedCustomers") in ("enterprise tier", "all"),
                    }
                )
            logger.info("Loaded %d simulated ServiceNow defects", len(normalized))
            return normalized
        except Exception as e:
            logger.error("Failed to load simulated ServiceNow defects: %s", e)
            return []

    def normalize(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for record in raw:
            sys_id = record.get("sys_id", "")
            short_id = sys_id[:8] if sys_id else ""

            sn_priority = record.get("priority", "")
            priority = PRIORITY_MAP.get(str(sn_priority), "P3")

            assigned_to = None
            at = record.get("assigned_to")
            if isinstance(at, dict):
                assigned_to = at.get("display_value") or at.get("value")

            state = record.get("state", "")
            if isinstance(state, dict):
                state = state.get("display_value") or state.get("value", "")

            description = record.get("description", "") or ""

            normalized.append(
                {
                    "id": f"SN-{short_id}",
                    "title": record.get("short_description", ""),
                    "description": description,
                    "source": f"SN-{short_id}",
                    "source_type": "servicenow",
                    "priority": priority,
                    "deadline": None,
                    "owner": assigned_to,
                    "status": str(state),
                    "dependencies": [],
                    "blocks": [],
                    "raw_text": description,
                    "category": "incident",
                    "sla_status": "active",
                }
            )
        return normalized

    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            resp = await self._client.get(
                "/api/now/table/incident", params={"sysparm_limit": 1}
            )
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
