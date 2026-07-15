from __future__ import annotations

from datetime import datetime
from typing import Any

from models.task import Task


_TEAM_MAP: dict[str, str] = {
    "ai-team": "ai-team",
    "backend-team": "backend-team",
    "frontend-team": "frontend-team",
    "qa-team": "qa-team",
    "alex": "frontend-team",
    "jen": "backend-team",
    "mia": "backend-team",
    "mike": "devops-team",
    "sarah": "qa-team",
    "adwika": "backend-team",
    "saatvika": "frontend-team",
}
import re

_ISSUE_REF_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)\b",
    re.IGNORECASE,
)

def extract_linked_issue_numbers(pr_body: str) -> list[int]:
    if not pr_body:
        return []
    return sorted({int(n) for n in _ISSUE_REF_RE.findall(pr_body)})

def _infer_team(owner: str | None) -> str | None:
    if owner is None:
        return None
    o = owner.strip().lower()
    return _TEAM_MAP.get(o, "default")


def _parse_date(val: Any) -> str | None:
    if val is None:
        return None
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        return dt.isoformat()
    except (ValueError, TypeError):
        return None


def normalize_all(
    jira: list[dict], defects: list[dict], emails: list[dict]
) -> list[Task]:
    tasks: list[Task] = []

    for item in jira:
        tasks.append(
            Task(
                id=item["id"],
                title=item["title"],
                description=item.get("description", ""),
                source=item.get("source", item["id"]),
                source_type=item.get("source_type", "jira"),
                priority=item.get("priority"),
                deadline=_parse_date(item.get("deadline")),
                owner=item.get("owner"),
                status=item.get("status", "open"),
                dependencies=item.get("dependencies", []),
                blocks=item.get("blocks", []),
                raw_text=item.get("raw_text", ""),
                assignee=item.get("owner"),
                team=_infer_team(item.get("owner")),
                vp_escalation=item.get("vp_escalation", False),
                customer_facing=item.get("customer_facing", False),
            )
        )

    for item in defects:
        tasks.append(
            Task(
                id=item["id"],
                title=item["title"],
                description=item.get("description", ""),
                source=item.get("source", item["id"]),
                source_type="defect",
                priority=item.get("priority"),
                deadline=_parse_date(item.get("deadline")),
                owner=item.get("owner"),
                status=item.get("status", "open"),
                dependencies=item.get("dependencies", []),
                blocks=item.get("blocks", []),
                raw_text=item.get("raw_text", ""),
                assignee=item.get("owner"),
                team=_infer_team(item.get("owner")),
                vp_escalation=item.get("vp_escalation", False),
                customer_facing=item.get("customer_facing", False),
            )
        )

    for item in emails:
        tasks.append(
            Task(
                id=item["id"],
                title=f"Email: {item.get('subject', '(no subject)')}",
                description=item.get("body", "")[:200],
                source=item.get("source", item["id"]),
                source_type="email",
                priority="P2",
                deadline=None,
                owner=None,
                status="open",
                dependencies=[],
                blocks=[],
                raw_text=item.get("body", ""),
                assignee=None,
                team=None,
                vp_escalation=item.get("vp_escalation", False),
                customer_facing=item.get("customer_facing", False),
            )
        )

    return tasks


def normalize_connector_payload(
    raw: list[dict[str, Any]], source_type: str
) -> list[dict[str, Any]]:
    normalized = []
    for item in raw:
        normalized.append(
            {
                "id": item["id"],
                "title": item["title"],
                "description": item.get("description", ""),
                "source": item.get("source", item["id"]),
                "source_type": source_type,
                "priority": item.get("priority"),
                "deadline": item.get("deadline"),
                "owner": item.get("owner"),
                "status": item.get("status", "open"),
                "dependencies": item.get("dependencies", []),
                "blocks": item.get("blocks", []),
                "raw_text": item.get("raw_text", ""),
                "vp_escalation": item.get("vp_escalation", False),
                "customer_facing": item.get("customer_facing", False),
            }
        )
    return normalized
