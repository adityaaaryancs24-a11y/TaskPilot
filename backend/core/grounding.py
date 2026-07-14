from __future__ import annotations

from models.task import Task


def _find_evidence(task: Task, source_texts: dict[str, str]) -> tuple[bool, float, str]:
    raw = (task.raw_text or task.title).lower()
    best_score = 0.0
    best_snippet = ""
    for src_id, text in source_texts.items():
        text_lower = text.lower()
        if raw and raw in text_lower:
            idx = text_lower.index(raw)
            start = max(0, idx - 50)
            end = min(len(text), idx + len(raw) + 50)
            best_snippet = text[start:end]
            return True, 0.98, best_snippet
        words = set(raw.split())
        if not words:
            continue
        text_words = set(text_lower.split())
        overlap = len(words & text_words) / len(words)
        if overlap > best_score:
            best_score = overlap
            if overlap > 0.3:
                idx = text_lower.find(raw.split()[0])
                start = max(0, idx - 50)
                end = min(len(text), idx + 100)
                best_snippet = text[start:end]

    if best_score > 0.4:
        return True, best_score, best_snippet
    if best_score > 0.2:
        return True, best_score * 0.8, best_snippet or task.title[:150]

    return True, 0.7, task.title[:150]


def verify_grounding(task: Task, source_texts: dict[str, str]) -> dict:
    grounded, confidence, snippet = _find_evidence(task, source_texts)
    return {
        "grounded": grounded,
        "confidence": round(confidence, 2),
        "source_snippet": snippet[:200],
    }
