from __future__ import annotations

import re
from typing import Any


def sanitize_text(text: str, max_length: int = 10000) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    # Remove control characters except newlines and tabs
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text


def sanitize_task_title(title: str) -> str:
    return sanitize_text(title, max_length=500)


def sanitize_task_description(description: str) -> str:
    return sanitize_text(description, max_length=5000)


def sanitize_chat_message(message: str) -> str:
    return sanitize_text(message, max_length=2000)


def validate_json_structure(data: Any, schema: dict) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Expected a JSON object"
    for field, field_type in schema.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], field_type):
                return False, f"Field '{field}' must be of type {field_type.__name__}"
    return True, ""


def sanitize_inject_request(data: dict) -> dict:

    sanitized = {
        "title": sanitize_task_title(data.get("title", "")),
        "description": sanitize_task_description(data.get("description", "")),
        "source_type": str(data.get("source_type", "injected")).strip(),
        "priority": str(data.get("priority", "")).strip().upper()
        if data.get("priority")
        else None,
        "deadline": str(data.get("deadline", "")).strip()
        if data.get("deadline")
        else None,
        "owner": sanitize_text(data.get("owner", ""), max_length=100) or None,
    }
    return sanitized
