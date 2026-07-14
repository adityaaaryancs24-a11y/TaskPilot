import logging
from typing import Any, Sequence

from core.llm_client import call_llm, LLMResponse
from core.prompts import build_qa_prompt
from models.task import Task, ChatResponse

logger = logging.getLogger(__name__)

MAX_CONTEXT_TASKS = 25
MAX_HISTORY_TURNS = 6


def _build_task_context(tasks: Sequence[Task]) -> list[dict[str, Any]]:
    sorted_tasks = sorted(
        tasks,
        key=lambda t: getattr(t, "score", 0) or 0,
        reverse=True,
    )
    return [t.model_dump(mode="json") for t in sorted_tasks[:MAX_CONTEXT_TASKS]]


def _trim_history(history: list[dict]) -> list[dict]:
    return history[-(MAX_HISTORY_TURNS * 2) :]


async def answer_question(
    tasks: Sequence[Task],
    question: str,
    chat_history: Sequence[dict] | None = None,
) -> ChatResponse:
    if not isinstance(chat_history, list):
        chat_history = []

    clean_history: list[dict] = []
    for entry in chat_history:
        if not isinstance(entry, dict):
            continue
        if "user" in entry and "assistant" in entry:
            clean_history.append({"role": "user", "content": entry["user"]})
            clean_history.append({"role": "assistant", "content": entry["assistant"]})
        elif "role" in entry and "content" in entry:
            clean_history.append(entry)

    trimmed_history = _trim_history(clean_history)
    task_context = _build_task_context(tasks)
    system_prompt, user_prompt = build_qa_prompt(
        task_context, question, trimmed_history
    )

    try:
        response: LLMResponse = await call_llm(
            prompt=user_prompt,
            system=system_prompt,
            json_mode=True,
        )
    except Exception as e:
        logger.error("LLM call failed in answer_question: %s", e)
        return ChatResponse(
            answer="I'm currently unable to answer questions. The LLM service is unavailable.",
            referenced_task_ids=[],
        )

    if response.parsed_json and isinstance(response.parsed_json, dict):
        return ChatResponse(
            answer=str(response.parsed_json.get("answer", response.text)),
            referenced_task_ids=list(response.parsed_json.get("citations", [])),
        )

    if response.text.strip():
        return ChatResponse(answer=response.text.strip(), referenced_task_ids=[])

    return ChatResponse(
        answer="I couldn't find an answer based on your current task list.",
        referenced_task_ids=[],
    )
