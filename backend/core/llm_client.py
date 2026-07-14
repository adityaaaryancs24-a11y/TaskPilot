from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from dotenv import load_dotenv
import httpx
from core.tracer import trace

_RETRYABLE_STATUSES = {429, 503, 502, 500}


async def _retry_with_backoff(
    fn,
    max_retries: int = 1,
    base_delay: float = 0.5,
    backoff_factor: float = 2.0,
) -> httpx.Response:
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            resp = await fn()
            if resp.status_code in _RETRYABLE_STATUSES and attempt < max_retries:
                delay = base_delay * (backoff_factor**attempt) + random.uniform(0, 0.5)
                logger.warning(
                    "LLM %s (attempt %d/%d), retrying in %.1fs",
                    resp.status_code,
                    attempt + 1,
                    max_retries,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            last_exc = e
            if attempt >= max_retries:
                raise
            delay = base_delay * (backoff_factor**attempt) + random.uniform(0, 0.5)
            logger.warning(
                "LLM error %s (attempt %d/%d), retrying in %.1fs",
                e,
                attempt + 1,
                max_retries,
                delay,
            )
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]


load_dotenv()

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    pass


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    model: str
    parsed_json: Optional[Any] = field(default=None)
    json_parse_error: Optional[str] = field(default=None)


def _extract_json(text: str) -> tuple[Optional[Any], Optional[str]]:
    text = text.strip()
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate), None
        except json.JSONDecodeError:
            pass
    for open_char, close_char in (("[", "]"), ("{", "}")):
        start = text.find(open_char)
        end = text.rfind(close_char)
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                return json.loads(candidate), None
            except json.JSONDecodeError:
                continue
    return (
        None,
        f"Could not extract valid JSON from response (length={len(text)} chars)",
    )


class LLMBackend(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> LLMResponse: ...


# ---------------------------------------------------------------------------
# Gemini backend (PRIMARY)
# Uses Google's OpenAI-compatible endpoint.
# Set in .env:
#   GEMINI_API_KEY=AIza...
#   GEMINI_MODEL=gemini-2.5-flash   (default)
# ---------------------------------------------------------------------------


class GeminiBackend(LLMBackend):
    def __init__(self) -> None:
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"

    @property
    def name(self) -> str:
        return f"Gemini({self.model})"

    @classmethod
    async def check_connectivity(cls) -> tuple[bool, str]:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return False, "GEMINI_API_KEY not set"
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                )
                resp.raise_for_status()
                return True, f"Gemini available (model={model})"
        except Exception as e:
            return False, f"Gemini unreachable: {e}"

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMClientError("GEMINI_API_KEY is not set")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await _retry_with_backoff(
                lambda: client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )
            )
            data = response.json()
        latency_ms = (time.monotonic() - start) * 1000

        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0) or 0
        output_tokens = usage.get("completion_tokens", 0) or 0

        parsed_json = None
        json_parse_error = None
        if json_mode:
            parsed_json, json_parse_error = _extract_json(text)

        return LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model=self.model,
            parsed_json=parsed_json,
            json_parse_error=json_parse_error,
        )


# ---------------------------------------------------------------------------
# Grok backend (FALLBACK #1)
# Used when Gemini fails or GEMINI_API_KEY is not set.
# Set in .env:
#   LLM_API_KEY=xai-...
#   LLM_MODEL=grok-3-mini   (default)
#   LLM_BASE_URL=https://api.x.ai/v1
# ---------------------------------------------------------------------------


class GrokBackend(LLMBackend):
    def __init__(self) -> None:
        self.api_key = os.environ.get("LLM_API_KEY") or os.environ.get(
            "XAI_API_KEY", ""
        )
        self.base_url = os.environ.get("LLM_BASE_URL", "https://api.x.ai/v1").rstrip(
            "/"
        )
        self.model = self._sanitize_model(os.environ.get("LLM_MODEL", "grok-3-mini"))

    @staticmethod
    def _sanitize_model(model: str) -> str:
        m = model.strip().lower()
        m = re.sub(r"\s+", "-", m)
        m = re.sub(r"\.0$", "", m)
        return m

    @property
    def name(self) -> str:
        return f"Grok({self.model})"

    @classmethod
    async def check_connectivity(cls) -> tuple[bool, str, list[str]]:
        api_key = os.environ.get("LLM_API_KEY") or os.environ.get("XAI_API_KEY", "")
        if not api_key:
            return False, "LLM_API_KEY not set", []
        base_url = os.environ.get("LLM_BASE_URL", "https://api.x.ai/v1").rstrip("/")
        model = GrokBackend._sanitize_model(os.environ.get("LLM_MODEL", "grok-3-mini"))
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                )
                resp.raise_for_status()
                return True, f"Grok available (model={model})", [model]
        except Exception as e:
            return False, f"Grok unreachable: {e}", []

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMClientError("LLM_API_KEY (Grok) is not set")

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await _retry_with_backoff(
                lambda: client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )
            )
            data = response.json()
        latency_ms = (time.monotonic() - start) * 1000

        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0) or 0
        output_tokens = usage.get("completion_tokens", 0) or 0

        parsed_json = None
        json_parse_error = None
        if json_mode:
            parsed_json, json_parse_error = _extract_json(text)

        return LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model=self.model,
            parsed_json=parsed_json,
            json_parse_error=json_parse_error,
        )


# ---------------------------------------------------------------------------
# OpenAICompatibleBackend — kept for backwards compatibility with main.py
# check_connectivity(). Points to Grok by default.
# ---------------------------------------------------------------------------


class OpenAICompatibleBackend(GrokBackend):
    """Alias of GrokBackend. Kept so main.py startup check still works."""

    @classmethod
    async def check_connectivity(cls) -> tuple[bool, str, list[str]]:
        # Try Gemini first, then Grok
        gem_ok, gem_msg = await GeminiBackend.check_connectivity()
        if gem_ok:
            return True, f"Gemini (primary): {gem_msg}", []
        grok_ok, grok_msg, models = await GrokBackend.check_connectivity()
        if grok_ok:
            return True, f"Grok (fallback): {grok_msg}", models
        return False, f"Both LLMs unavailable. Gemini: {gem_msg} | Grok: {grok_msg}", []


# ---------------------------------------------------------------------------
# Heuristic fallback (FALLBACK #2 — no API key needed)
# ---------------------------------------------------------------------------


class HeuristicBackend(LLMBackend):
    @property
    def name(self) -> str:
        return "Heuristic"

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> LLMResponse:
        start = time.monotonic()
        system_lower = (system or "").lower()

        if json_mode:
            if "prioritization" in system_lower or "prioritisation" in system_lower:
                scored = self._heuristic_prioritize(prompt)
                text = json.dumps(scored)
                parsed_json = scored
            elif "extract" in system_lower:
                text = json.dumps(self._heuristic_extract(prompt))
                parsed_json = json.loads(text)
            elif "question" in system_lower or "assistant" in system_lower:
                parsed_json = self._heuristic_qa(prompt)
                text = json.dumps(parsed_json)
            else:
                text = json.dumps(
                    {
                        "answer": "Heuristic mode: Unable to answer questions. Please check your task list manually.",
                        "citations": [],
                    }
                )
                parsed_json = json.loads(text)
        else:
            if "planning" in system_lower:
                text = self._heuristic_daily_plan(prompt)
            elif "weekly summary" in system_lower or "standup" in system_lower:
                text = (
                    "## Accomplished This Week\n\n"
                    "LLM summary unavailable in heuristic mode.\n\n"
                    "## In Progress / Carried Over\n\n"
                    "Review your active task list for current priorities.\n\n"
                    "## Blockers & Deferred\n\n"
                    "Alerts panel shows any active blockers."
                )
            else:
                text = "Heuristic mode: Unable to answer questions. Please check your task list manually."

        latency_ms = (time.monotonic() - start) * 1000
        return LLMResponse(
            text=text,
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
            model="heuristic",
            parsed_json=parsed_json if json_mode else None,
            json_parse_error=None,
        )

    def _heuristic_prioritize(self, prompt: str) -> list[dict[str, Any]]:
        tasks, _ = _extract_json(prompt)
        if not isinstance(tasks, list):
            return []
        scored = []
        for task in tasks:
            score = self._compute_score(task)
            rationale = self._build_rationale(task, score)
            du = self._deadline_urgency(task.get("deadline"))
            sv = self._severity_score(task.get("priority"))
            bi = self._business_impact(
                task.get("vp_escalation", False), task.get("customer_facing", False)
            )
            db = self._dependency_blocking(task.get("blocks", []))
            scored.append(
                {
                    "id": task.get("id", ""),
                    "score": round(score, 1),
                    "score_breakdown": {
                        "deadline_urgency": round(du, 1),
                        "severity": round(sv, 1),
                        "business_impact": round(bi, 1),
                        "dependency_blocking": round(db, 1),
                    },
                    "rationale": rationale,
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _compute_score(self, task: dict[str, Any]) -> float:
        du = self._deadline_urgency(task.get("deadline"))
        sv = self._severity_score(task.get("priority"))
        bi = self._business_impact(
            task.get("vp_escalation", False), task.get("customer_facing", False)
        )
        db = self._dependency_blocking(task.get("blocks", []))
        return du * 0.35 + sv * 0.30 + bi * 0.20 + db * 0.15

    def _deadline_urgency(self, deadline: Optional[str]) -> float:
        if not deadline:
            return 30.0
        try:
            dt = datetime.fromisoformat(deadline)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            diff_hours = (dt - now).total_seconds() / 3600
            if diff_hours <= 24:
                return 100.0
            diff_days = diff_hours / 24
            if diff_days >= 14:
                return 0.0
            return 100.0 * (1 - diff_days / 14)
        except (ValueError, TypeError):
            return 30.0

    def _severity_score(self, priority: Optional[str]) -> float:
        return {"P0": 100, "P1": 75, "P2": 50, "P3": 25}.get(priority or "", 25)

    def _business_impact(self, vp_escalation: bool, customer_facing: bool) -> float:
        if vp_escalation:
            return 100.0
        if customer_facing:
            return 70.0
        return 40.0

    def _dependency_blocking(self, blocks: Any) -> float:
        count = len(blocks) if isinstance(blocks, list) else 0
        if count >= 2:
            return 100.0
        if count == 1:
            return 60.0
        return 0.0

    def _build_rationale(self, task: dict[str, Any], score: float) -> str:
        du = self._deadline_urgency(task.get("deadline"))
        sv = self._severity_score(task.get("priority"))
        bi = self._business_impact(
            task.get("vp_escalation", False), task.get("customer_facing", False)
        )
        db = self._dependency_blocking(task.get("blocks", []))
        components = {
            "deadline urgency": du,
            "severity": sv,
            "business impact": bi,
            "dependency blocking": db,
        }
        biggest = max(components, key=components.get)
        return (
            f"Score breakdown: deadline_urgency={du:.0f}×0.35, severity={sv:.0f}×0.30, "
            f"business_impact={bi:.0f}×0.20, dependency_blocking={db:.0f}×0.15 = {score:.1f}. "
            f"Biggest driver: {biggest}."
        )

    def _heuristic_daily_plan(self, prompt: str) -> str:
        tasks, _ = _extract_json(prompt)
        if not isinstance(tasks, list) or not tasks:
            return "## Top 3 for Today\n\nNo tasks found.\n"
        scored = [(task, self._compute_score(task)) for task in tasks]
        scored.sort(key=lambda x: x[1], reverse=True)
        top3 = scored[:3]
        do_next = scored[3:7]
        deferred = [t for t, _ in scored[7:]]
        lines = ["## Top 3 for Today\n"]
        for task, score in top3:
            lines.append(f"- **{task.get('title', 'Untitled')}** (score: {score:.1f})")
        lines.append("\n## Do Next\n")
        for task, score in do_next:
            lines.append(f"- {task.get('title', 'Untitled')} (score: {score:.1f})")
        lines.append("\n## Defer to Tomorrow\n")
        for task, _ in deferred:
            lines.append(f"- {task.get('title', 'Untitled')}")
        return "\n".join(lines)

    def _heuristic_extract(self, prompt: str) -> list[dict[str, Any]]:
        tasks = []
        seen_titles: set[str] = set()
        action_patterns = [
            re.compile(
                r"(?:can you|please|could you|make sure to|don't forget to|remember to)\s+(.+?)(?:\.|$)",
                re.IGNORECASE,
            ),
            re.compile(r"(?:TODO|FIXME|ACTION)[:\s]+(.+)$", re.MULTILINE),
        ]
        for pattern in action_patterns:
            for match in pattern.finditer(prompt):
                title = match.group(1).strip().rstrip(".")
                if not title or len(title) < 5:
                    continue
                key = title.lower()
                if key not in seen_titles:
                    seen_titles.add(key)
                    tasks.append(
                        {
                            "title": title,
                            "owner": None,
                            "deadline": None,
                            "confidence": 0.7,
                            "source_sentence": match.group(0).strip(),
                        }
                    )
        return tasks

    def _heuristic_qa(self, prompt: str) -> dict[str, Any]:
        tasks, _ = _extract_json(prompt)
        if not isinstance(tasks, list) or not tasks:
            return {
                "answer": "No task data available to answer your question.",
                "citations": [],
            }

        question_match = re.search(r'USER QUESTION:\s*"([^"]+)"', prompt)
        question = question_match.group(1).lower() if question_match else prompt.lower()
        citations = []

        if any(w in question for w in ["top", "priority", "most important", "#1"]):
            candidates = sorted(
                tasks,
                key=lambda t: (
                    {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(t.get("priority", ""), 4),
                    -(t.get("score") or 0),
                ),
            )
            if candidates:
                t = candidates[0]
                tid = t.get("id") or t.get("task_id") or ""
                title = t.get("title", "Untitled")
                priority = t.get("priority", "unset")
                score = t.get("score")
                score_str = f" (score: {score:.0f})" if score else ""
                citations.append(tid)
                return {
                    "answer": f'Your top priority is "{title}" [priority: {priority}{score_str}].',
                    "citations": citations,
                }
        elif any(w in question for w in ["how many", "count", "total tasks"]):
            return {
                "answer": f"You have {len(tasks)} tasks in your list.",
                "citations": [
                    t.get("id") or t.get("task_id", "")
                    for t in tasks[:3]
                    if t.get("id") or t.get("task_id")
                ],
            }
        elif any(w in question for w in ["blocked", "blocking", "stuck", "waiting"]):
            blocked = [t for t in tasks if t.get("status") == "blocked"]
            if blocked:
                names = "\n".join(
                    f"- {t.get('title', 'Untitled')} ({t.get('id', '')})"
                    for t in blocked[:5]
                )
                citations = [
                    t.get("id") or t.get("task_id", "")
                    for t in blocked[:5]
                    if t.get("id") or t.get("task_id")
                ]
                return {
                    "answer": f"Blocked tasks ({len(blocked)}):\n{names}",
                    "citations": citations,
                }
            return {"answer": "No tasks are currently blocked.", "citations": []}
        elif any(w in question for w in ["p0", "p1", "critical", "urgent"]):
            urgent = [t for t in tasks if t.get("priority") in ("P0", "P1")]
            if urgent:
                names = "\n".join(
                    f"- {t.get('title', 'Untitled')} ({t.get('priority', '')})"
                    for t in urgent[:5]
                )
                citations = [
                    t.get("id") or t.get("task_id", "")
                    for t in urgent[:5]
                    if t.get("id") or t.get("task_id")
                ]
                return {
                    "answer": f"Urgent tasks ({len(urgent)}):\n{names}",
                    "citations": citations,
                }
            return {"answer": "No P0 or P1 tasks in your list.", "citations": []}
        elif any(w in question for w in ["deadline", "due", "sla", "overdue"]):
            overdue = [
                t for t in tasks if t.get("status") == "overdue" or t.get("deadline")
            ]
            if overdue:
                names = "\n".join(
                    f"- {t.get('title', 'Untitled')} (due: {t.get('deadline', 'unknown')})"
                    for t in overdue[:5]
                )
                citations = [
                    t.get("id") or t.get("task_id", "")
                    for t in overdue[:5]
                    if t.get("id") or t.get("task_id")
                ]
                return {
                    "answer": f"Tasks with deadlines ({len(overdue)}):\n{names}",
                    "citations": citations,
                }
            return {
                "answer": "No tasks with upcoming deadlines found.",
                "citations": [],
            }
        else:
            return {
                "answer": "I can answer questions about your top priorities, task count, blocked tasks, urgent items, and deadlines. Try asking something specific!",
                "citations": [],
            }


# ---------------------------------------------------------------------------
# Rules engine (FALLBACK #3 — absolute last resort)
# ---------------------------------------------------------------------------


class RulesEngineBackend(LLMBackend):
    HIGH_KEYWORDS = {
        "critical",
        "urgent",
        "production",
        "hotfix",
        "p0",
        "severe",
        "outage",
    }
    MEDIUM_KEYWORDS = {"review", "meeting", "docs", "documentation", "refactor", "test"}

    @property
    def name(self) -> str:
        return "RulesEngine"

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> LLMResponse:
        start = time.monotonic()
        system_lower = (system or "").lower()

        if json_mode and (
            "prioritization" in system_lower or "prioritisation" in system_lower
        ):
            scored = self._rules_prioritize(prompt)
            text = json.dumps(scored)
            parsed_json = scored
        elif json_mode and "extract" in system_lower:
            heur = HeuristicBackend()
            extracted = heur._heuristic_extract(prompt)
            text = json.dumps(extracted)
            parsed_json = extracted
        elif json_mode:
            result = {
                "answer": "Rules engine: Unable to answer. Please check your task list manually.",
                "citations": [],
            }
            text = json.dumps(result)
            parsed_json = result
        else:
            text = "Rules engine mode: Unable to generate narrative responses."
            parsed_json = None

        latency_ms = (time.monotonic() - start) * 1000
        return LLMResponse(
            text=text,
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
            model="rules-engine",
            parsed_json=parsed_json,
            json_parse_error=None,
        )

    def _rules_prioritize(self, prompt: str) -> list[dict[str, Any]]:
        tasks, _ = _extract_json(prompt)
        if not isinstance(tasks, list):
            return []
        scored = []
        for task in tasks:
            title = (task.get("title", "") or "").lower()
            if any(kw in title for kw in self.HIGH_KEYWORDS):
                score = 90.0
            elif any(kw in title for kw in self.MEDIUM_KEYWORDS):
                score = 60.0
            else:
                score = 25.0
            scored.append(
                {
                    "id": task.get("id", ""),
                    "score": round(score, 1),
                    "score_breakdown": {
                        "deadline_urgency": 0,
                        "severity": score,
                        "business_impact": 0,
                        "dependency_blocking": 0,
                    },
                    "rationale": f"Rules engine: keyword-based score of {score:.0f}.",
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored


# ---------------------------------------------------------------------------
# Resilient client — tries Gemini first, then Grok, then heuristic, then rules
# ---------------------------------------------------------------------------


class ResilientLLMClient:
    def __init__(self) -> None:
        self.backends: list[LLMBackend] = [
            GeminiBackend(),  # PRIMARY
            GrokBackend(),  # FALLBACK #1
            HeuristicBackend(),  # FALLBACK #2
            RulesEngineBackend(),  # FALLBACK #3
        ]

    async def call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> LLMResponse:
        last_error: Optional[Exception] = None
        for backend in self.backends:
            try:
                logger.debug("Trying backend: %s", backend.name)
                response = await backend.generate(
                    prompt=prompt,
                    system=system,
                    json_mode=json_mode,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
                if backend.name not in ("Heuristic", "RulesEngine"):
                    logger.info("LLM call succeeded via %s", backend.name)
                return response
            except Exception as e:
                logger.warning("Backend %s failed: %s — trying next", backend.name, e)
                last_error = e
                continue
        raise LLMClientError(f"All backends failed. Last error: {last_error}")


_client = ResilientLLMClient()


@trace("llm_call")
async def call_llm(
    prompt: str,
    system: Optional[str] = None,
    json_mode: bool = False,
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
) -> LLMResponse:
    return await _client.call_llm(
        prompt=prompt,
        system=system,
        json_mode=json_mode,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )
