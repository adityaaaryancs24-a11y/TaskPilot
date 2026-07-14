from __future__ import annotations

import json
from typing import Any


def build_extraction_prompt(
    source_text: str, source_type: str, source_id: str
) -> tuple[str, str]:
    system = (
        "You are an expert assistant that extracts actionable tasks hidden inside "
        "unstructured workplace text (emails, meeting transcripts). You are precise, "
        "conservative, and NEVER invent information that is not present in the source text. "
        "If the text contains no actionable items, return an empty JSON array. "
        "You always return ONLY a valid JSON array, with no commentary, no markdown fences, "
        "and no explanation outside the JSON."
    )
    few_shot = (
        "Here are examples of correct extraction:\n\n"
        "EXAMPLE 1\n"
        'Source text: "Thanks for the notes. Also, quick favor - can you loop in finance '
        "before Friday so the invoice doesn't get stuck again? Otherwise nothing else to add.\"\n"
        "Output:\n"
        "[\n"
        "  {\n"
        '    "title": "Loop in finance before Friday to avoid invoice delay",\n'
        '    "owner": null,\n'
        '    "deadline": "Friday",\n'
        '    "confidence": 0.9,\n'
        '    "source_sentence": "can you loop in finance before Friday so the invoice doesn\'t get stuck again?"\n'
        "  }\n"
        "]\n\n"
        "EXAMPLE 2 (no real action item - should return empty array)\n"
        'Source text: "Weekly infra report: cloud spend up 3%. No action required, informational only."\n'
        "Output:\n"
        "[]\n\n"
        "EXAMPLE 3 (action item assigned to someone OTHER than the inbox owner - owner field must be set)\n"
        'Source text: "Diane, can you make sure this gets done before end of sprint? Appreciate it."\n'
        "Output:\n"
        "[\n"
        "  {\n"
        '    "title": "Ensure task is completed before end of sprint",\n'
        '    "owner": "Diane",\n'
        '    "deadline": "end of sprint",\n'
        '    "confidence": 0.85,\n'
        '    "source_sentence": "Diane, can you make sure this gets done before end of sprint?"\n'
        "  }\n"
        "]\n\n"
        "EXAMPLE 4 (multiple buried items in one email - extract each separately)\n"
        'Source text: "Recap of sync: mostly routine planning. One more thing - can you also '
        "update the API docs once the rate limit change ships? And separately, can someone "
        'double check the billing webhook before Friday?"\n'
        "Output:\n"
        "[\n"
        "  {\n"
        '    "title": "Update API docs once rate limit change ships",\n'
        '    "owner": null,\n'
        '    "deadline": null,\n'
        '    "confidence": 0.82,\n'
        '    "source_sentence": "can you also update the API docs once the rate limit change ships?"\n'
        "  },\n"
        "  {\n"
        '    "title": "Double check the billing webhook",\n'
        '    "owner": null,\n'
        '    "deadline": "Friday",\n'
        '    "confidence": 0.78,\n'
        '    "source_sentence": "can someone double check the billing webhook before Friday?"\n'
        "  }\n"
        "]"
    )
    user_prompt = (
        f"{few_shot}\n"
        f"Now extract action items from this {source_type} (source_id: {source_id}).\n"
        "Remember: return ONLY the JSON array, nothing else. If there are no actionable "
        "items, return [].\n\n"
        "SOURCE TEXT:\n"
        f'"""\n{source_text}\n"""\n'
    )
    return system, user_prompt


def build_prioritization_prompt(
    deduplicated_tasks: list[dict[str, Any]],
) -> tuple[str, str]:
    system = (
        "You are a prioritization engine for a software engineer's task list. "
        "You score every task using EXACTLY the formula provided, and you never "
        "deviate from it or apply intuition instead. Your rationale must show the "
        "actual component values you used, in two sentences: one stating the "
        "score breakdown, one stating the single biggest driver of the score. "
        "Return ONLY a valid JSON array sorted by score descending, no commentary."
    )
    formula_block = (
        "SCORING FORMULA (apply exactly):\n"
        "score = (deadline_urgency * 0.35) + (severity * 0.30) + (business_impact * 0.20) + (dependency_blocking * 0.15)\n\n"
        "Component rules:\n"
        "- deadline_urgency: 100 if due/SLA within 24h; linearly scale down to 0 at 14+ days out; 30 if no deadline given.\n"
        "- severity: P0=100, P1=75, P2=50, P3=25.\n"
        "- business_impact: 100 if flagged as VP/exec escalation OR explicit customer-facing financial impact; 70 if customer-facing but no exec escalation; 40 otherwise.\n"
        "- dependency_blocking: 100 if this task blocks 2+ other tasks; 60 if it blocks exactly 1 other task; 0 if it blocks nothing.\n\n"
        "Output schema per task:\n"
        "{\n"
        '  "id": "<task id>",\n'
        '  "score": <number, 0-100, one decimal place>,\n'
        '  "score_breakdown": {"deadline_urgency": <0-100>, "severity": <0-100>, "business_impact": <0-100>, "dependency_blocking": <0-100>},\n'
        '  "rationale": "<two sentences: score breakdown by component, then the single biggest driver>"\n'
        "}\n"
    )
    tasks_json = json.dumps(deduplicated_tasks, indent=2)
    user_prompt = (
        f"{formula_block}\n"
        "Score and rank ALL of the following tasks using the formula above. Return a "
        "JSON array sorted by score descending. Include every task -- do not omit any.\n\n"
        f"TASKS:\n{tasks_json}\n"
    )
    return system, user_prompt


def build_daily_plan_prompt(
    ranked_tasks: list[dict[str, Any]],
    active_alerts: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    system = (
        "You are a planning assistant that converts an already-ranked task list "
        "into a clear, structured daily plan for a software engineer. You do NOT "
        "re-rank or re-score tasks -- you organize the given ranking into sections. "
        "Be concise: one line of rationale per task, no filler language. "
        "Output valid markdown only, using exactly these four headers in this order: "
        "'## Top 3 for Today', '## Do Next', '## Blocked - Needs Action From Others', "
        "'## Defer to Tomorrow'."
    )
    alerts_block = ""
    if active_alerts:
        alerts_block = (
            "\nACTIVE ALERTS (mention briefly at the top if relevant):\n"
            f"{json.dumps(active_alerts, indent=2)}\n"
        )
    tasks_json = json.dumps(ranked_tasks, indent=2)
    user_prompt = (
        "Given this already-ranked task list (highest score = highest priority), "
        "organize it into a daily plan.\n"
        f"{alerts_block}\n"
        f"RANKED TASKS:\n{tasks_json}\n\n"
        "Rules:\n"
        '- "Top 3 for Today" = the 3 highest-scored tasks, each with a one-sentence rationale.\n'
        '- "Do Next" = next 2-4 tasks worth queuing up after the top 3.\n'
        '- "Blocked - Needs Action From Others" = any task whose dependencies aren\'t resolved yet, or that explicitly needs someone else to act first.\n'
        '- "Defer to Tomorrow" = remaining lower-priority tasks.\n'
        "- Every task must appear in exactly one section.\n"
    )
    return system, user_prompt


def build_reprioritize_prompt(
    current_ranked_tasks: list[dict[str, Any]],
    new_task: dict[str, Any],
) -> tuple[str, str]:
    system = (
        "You are a prioritization engine handling a live re-ranking event: a new "
        "task has just arrived and must be scored and merged into an existing "
        "ranked list using the same formula as before. You must clearly explain "
        "what changed in the ranking and why. "
        "Return ONLY valid JSON, no commentary outside the JSON."
    )
    formula_block = (
        "SCORING FORMULA (apply exactly, same as standard prioritization):\n"
        "score = (deadline_urgency * 0.35) + (severity * 0.30) + (business_impact * 0.20) + (dependency_blocking * 0.15)\n"
        "- deadline_urgency: 100 if due/SLA within 24h; linearly scale down to 0 at 14+ days; 30 if none given.\n"
        "- severity: P0=100, P1=75, P2=50, P3=25.\n"
        "- business_impact: 100 if VP/exec escalation or explicit customer financial impact; 70 if customer-facing only; 40 otherwise.\n"
        "- dependency_blocking: 100 if blocks 2+ tasks; 60 if blocks 1; 0 if blocks none.\n\n"
        "Output schema:\n"
        "{\n"
        '  "new_rank": [ {"id": "...", "score": <number>, "rationale": "<two sentences>"}, ... ],\n'
        '  "change_summary": "<one or two sentences naming exactly which task moved>"\n'
        "}\n"
    )
    user_prompt = (
        f"{formula_block}\n"
        "CURRENT RANKED TASKS (before the new task arrived):\n"
        f"{json.dumps(current_ranked_tasks, indent=2)}\n\n"
        "NEW TASK JUST INJECTED:\n"
        f"{json.dumps(new_task, indent=2)}\n\n"
        "Score the new task using the formula, merge it into the ranking, and return the "
        "full updated ranking (all tasks, including the new one) sorted by score "
        "descending, plus a change_summary explaining the rank movement.\n"
    )
    return system, user_prompt


def build_dedup_prompt(
    task_a: dict,
    task_b: dict,
) -> tuple[str, str]:
    """Phase-3 LLM dedup prompt: called ONLY for ambiguous pairs where
    embedding similarity is in the grey zone (0.60–0.84) and no hard rule
    (exact ID / exact title) already fired.

    Returns (system_prompt, user_prompt).
    The LLM must respond with ONLY a JSON object matching:
    {
      "is_duplicate": true | false,
      "confidence": 0.0-1.0,
      "reasoning": "<one sentence explaining the decision>"
    }
    """
    system = (
        "You are a deduplication assistant for a task-management system. "
        "Your ONLY job is to decide whether two work tasks refer to the same "
        "underlying issue or action item. You must weigh semantic meaning, not "
        "just surface wording — the same task can be described very differently "
        "across Jira, email, Slack, and meeting transcripts. "
        "Rules:\n"
        "- Return true if both tasks would require the SAME real-world action to complete.\n"
        "- Return false if they are related but genuinely distinct actions.\n"
        "- Be conservative: when genuinely uncertain, return false.\n"
        "- NEVER invent information. Use only what is given.\n"
        "Return ONLY a valid JSON object, no commentary, no markdown fences:\n"
        '{"is_duplicate": <true|false>, "confidence": <0.0-1.0>, '
        '"reasoning": "<one concise sentence>"}'
    )
    user_prompt = (
        "Decide if these two tasks are duplicates of each other.\n\n"
        "TASK A:\n"
        f"  ID: {task_a.get('id', 'N/A')}\n"
        f"  Source: {task_a.get('source_type', 'unknown')} / {task_a.get('source', '')}\n"
        f"  Title: {task_a.get('title', '')}\n"
        f"  Description: {(task_a.get('description') or '')[:400]}\n"
        f"  Priority: {task_a.get('priority', 'unknown')}\n"
        f"  Deadline: {task_a.get('deadline', 'none')}\n"
        f"  Owner: {task_a.get('owner', 'unknown')}\n\n"
        "TASK B:\n"
        f"  ID: {task_b.get('id', 'N/A')}\n"
        f"  Source: {task_b.get('source_type', 'unknown')} / {task_b.get('source', '')}\n"
        f"  Title: {task_b.get('title', '')}\n"
        f"  Description: {(task_b.get('description') or '')[:400]}\n"
        f"  Priority: {task_b.get('priority', 'unknown')}\n"
        f"  Deadline: {task_b.get('deadline', 'none')}\n"
        f"  Owner: {task_b.get('owner', 'unknown')}\n\n"
        "Return ONLY the JSON verdict. No extra text."
    )
    return system, user_prompt


def build_qa_prompt(
    full_task_context: list[dict[str, Any]],
    user_question: str,
    chat_history: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    system = (
        "You are a conversational assistant answering questions about a software "
        "engineer's task list. You answer ONLY using the task context provided -- "
        "you NEVER invent task details, deadlines, owners, or email content that "
        "is not present in the context. If the answer isn't in the context, say so "
        "explicitly rather than guessing. Every factual claim must be backed by a "
        "citation to a specific task id or source id from the context. "
        'Return ONLY valid JSON: {"answer": "<your answer>", "citations": ["<id>", ...]}'
    )
    history_block = ""
    if chat_history:
        history_lines = "\n".join(
            f"{turn['role']}: {turn['content']}" for turn in chat_history[-6:]
        )
        history_block = f"\nRECENT CONVERSATION:\n{history_lines}\n"
    context_json = json.dumps(full_task_context, indent=2)
    user_prompt = (
        "TASK CONTEXT (the only source of truth -- do not use outside knowledge):\n"
        f"{context_json}\n"
        f"{history_block}\n"
        f'USER QUESTION: "{user_question}"\n\n'
        "Answer the question using only the context above. Cite specific task/source IDs "
        "that support your answer.\n"
    )
    return system, user_prompt
