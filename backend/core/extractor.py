from __future__ import annotations

import asyncio
import re
import uuid
from typing import Any

from core.llm_client import call_llm
from core.prompts import build_extraction_prompt
from core.tracer import trace
from models.task import Task

CONFIDENCE_THRESHOLD = 0.65

VP_ESCALATION_SIGNALS = [
    r"\bvp\b",
    r"\bvice\s+president\b",
    r"\bceo\b",
    r"\bcto\b",
    r"\bcoo\b",
    r"\bexec(utive)?\b",
    r"\bescalat",
    r"\bdirector\b",
    r"\bfinance\s+is\s+now\s+involved\b",
    r"\barr\b",
]

CUSTOMER_FACING_SIGNALS = [
    r"\bcustomer\b",
    r"\bclient\b",
    r"\benterprise\b",
    r"\bcheckout\b",
    r"\bpayment\b",
    r"\buser(s)?\b",
    r"\bexternal\b",
    r"\bpartner\b",
]


def _detect_flags(text: str) -> tuple[bool, bool]:
    lowered = text.lower()
    vp = any(re.search(p, lowered) for p in VP_ESCALATION_SIGNALS)
    cf = any(re.search(p, lowered) for p in CUSTOMER_FACING_SIGNALS)
    return vp, cf


def _parse_extracted_items(
    raw_items: list[dict[str, Any]],
    source_id: str,
    source_type: str,
    raw_source_text: str,
) -> list[Task]:
    tasks: list[Task] = []
    for i, item in enumerate(raw_items):
        confidence = float(item.get("confidence", 0.0))
        if confidence < CONFIDENCE_THRESHOLD:
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        source_sentence = str(item.get("source_sentence", "")).strip()
        owner = item.get("owner")
        vp_flag, cf_flag = _detect_flags(f"{title} {source_sentence}")
        task_id = f"{source_id}-{i}"
        tasks.append(
            Task(
                id=task_id,
                title=title,
                source=source_id,
                source_type=source_type,
                raw_text=raw_source_text,
                owner=owner,
                status="open",
                confidence=confidence,
                source_sentence=source_sentence,
                vp_escalation=vp_flag,
                customer_facing=cf_flag,
            )
        )
    return tasks


async def _extract_single_email(email: dict[str, Any]) -> list[Task]:
    email_id = email.get("email_id") or email.get("id", f"EML-{uuid.uuid4().hex[:6]}")
    subject = email.get("subject") or email.get("title", "")
    body = email.get("body")
    if isinstance(body, dict):
        body = body.get("content", "")
    if not body:
        body = (
            email.get("body_preview")
            or email.get("bodyPreview")
            or email.get("raw_text", "")
        )
    sender = email.get("from_name") or email.get("from", "")
    if isinstance(sender, dict):
        sender = sender.get("emailAddress", {}).get("address", "") or sender.get(
            "displayName", ""
        )
    full_text = f"From: {sender}\nSubject: {subject}\n\n{body}"
    system, user_prompt = build_extraction_prompt(
        source_text=full_text,
        source_type="email",
        source_id=email_id,
    )
    response = await call_llm(
        prompt=user_prompt,
        system=system,
        json_mode=True,
        temperature=0.1,
    )
    raw_items = response.parsed_json if isinstance(response.parsed_json, list) else []
    return _parse_extracted_items(
        raw_items, source_id=email_id, source_type="email", raw_source_text=full_text
    )


@trace("extraction")
async def extract_from_emails(email_inbox: list[dict[str, Any]]) -> list[Task]:
    results = await asyncio.gather(
        *[_extract_single_email(email) for email in email_inbox],
        return_exceptions=True,
    )
    tasks: list[Task] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"[extractor] Warning: email {i} extraction failed: {result}")
        else:
            tasks.extend(result)
    return tasks


def extract_actions(text: str) -> list[dict]:
    from core.llm_client import HeuristicBackend

    backend = HeuristicBackend()
    return backend._heuristic_extract(text)


async def extract_from_transcript(
    transcript_text: str,
    meeting_id: str = "MEETING",
) -> list[Task]:
    system, user_prompt = build_extraction_prompt(
        source_text=transcript_text,
        source_type="meeting transcript",
        source_id=meeting_id,
    )
    response = await call_llm(
        prompt=user_prompt,
        system=system,
        json_mode=True,
        temperature=0.1,
    )
    raw_items = response.parsed_json if isinstance(response.parsed_json, list) else []
    return _parse_extracted_items(
        raw_items,
        source_id=meeting_id,
        source_type="transcript",
        raw_source_text=transcript_text,
    )
