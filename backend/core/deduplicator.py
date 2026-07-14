"""
Hybrid Deduplication Engine — 3-Phase Architecture
====================================================

Phase 1  — Embedding similarity (fast candidate retrieval)
           Batch-encodes all task titles+descriptions with all-MiniLM-L6-v2.
           Computes an upper-triangular cosine similarity matrix.
           Any pair with embedding_sim >= EMBED_GATE (0.60) is a candidate.

Phase 2  — Hard rule matching (zero LLM cost, runs on ALL candidates)
           - Exact Jira ID cross-reference  → confidence 0.95
           - SequenceMatcher title similarity → if >= RULE_THRESHOLD (0.75)
           - Jaccard keyword overlap          → if >= RULE_THRESHOLD (0.75)
           - VP escalation overlap            → combined signal
           If ANY hard rule fires with conf >= HARD_MATCH (0.85), skip Phase 3.

Phase 3  — LLM arbitration (only for ambiguous grey-zone pairs)
           Called only when EMBED_GATE <= combined_conf < LLM_SKIP (0.85).
           Uses build_dedup_prompt() → LLM returns {is_duplicate, confidence, reasoning}.
           LLM result is blended with embedding + rule signals.

Final confidence (blended):
  conf = EMBED_W * embed_sim + RULE_W * rule_conf + LLM_W * llm_conf
  EMBED_W=0.35, RULE_W=0.40, LLM_W=0.25

A pair is merged when final_conf >= MERGE_THRESHOLD (0.75).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from difflib import SequenceMatcher
from typing import Any

import numpy as np

from models.task import Task

logger = logging.getLogger(__name__)

# ─── Tunable thresholds ────────────────────────────────────────────────────────
EMBED_GATE      = 0.60   # Minimum embedding cosine sim to even consider a pair
RULE_THRESHOLD  = 0.75   # Minimum rule-based score to count as a signal
HARD_MATCH      = 0.85   # If rule_conf >= this, skip LLM (trusted hard match)
LLM_SKIP        = 0.85   # Same boundary: above this we trust rules; below → LLM
MERGE_THRESHOLD = 0.75   # Final blended confidence threshold to merge

# Blend weights (must sum to 1.0 for pairs that used all three phases)
EMBED_W = 0.35
RULE_W  = 0.40
LLM_W   = 0.25

JIRA_PATTERN = re.compile(r"[A-Z]+-\d+")


# ─── Text utilities ─────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _title_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _keyword_overlap(a: str, b: str) -> float:
    words_a = set(_normalize(a).split())
    words_b = set(_normalize(b).split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _extract_jira_ids(text: str) -> set[str]:
    return set(JIRA_PATTERN.findall(text.upper()))


def _task_text(t: Task) -> str:
    """Canonical text used for embedding: title + description."""
    return (t.title + " " + (t.description or "")).strip()


def _full_text(t: Task) -> str:
    """Full text including raw_text for rule-based Jira ID search."""
    return t.title + " " + (t.description or "") + " " + (t.raw_text or "")


# ─── Phase 1: Batch embeddings ──────────────────────────────────────────────────

def _compute_embedding_matrix(tasks: list[Task]) -> np.ndarray | None:
    """Returns an (N x N) cosine similarity matrix, or None if model unavailable."""
    if not tasks:
        return None
    try:
        from core.embedding_model import get_embeddings_batch, load_embedding_model

        model = load_embedding_model()
        if model is None:
            logger.warning("Embedding model not available — Phase 1 skipped")
            return None

        texts = [_task_text(t) for t in tasks]
        embeddings = get_embeddings_batch(texts)         # list[list[float]]
        mat = np.array(embeddings, dtype=np.float32)    # (N, D)

        # Normalise rows so dot product = cosine similarity
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        mat = mat / norms

        sim_matrix = mat @ mat.T                         # (N, N)
        logger.info("Embedding matrix computed: %dx%d", len(tasks), len(tasks))
        return sim_matrix

    except Exception as e:
        logger.warning("Embedding matrix computation failed: %s", e)
        return None


# ─── Phase 2: Rule-based confidence ────────────────────────────────────────────

def _rule_confidence(t1: Task, t2: Task) -> tuple[float, str]:
    """
    Returns (confidence 0..1, human-readable reason).
    Uses only deterministic string matching — no LLM, no embeddings.
    """
    reasons: list[str] = []
    best = 0.0

    # 1. Exact Jira ID cross-reference (strongest rule)
    ids1 = _extract_jira_ids(_full_text(t1))
    ids2 = _extract_jira_ids(_full_text(t2))
    common_ids = ids1 & ids2
    if common_ids:
        conf = 0.95
        reasons.append(f"Shared Jira IDs: {', '.join(sorted(common_ids))}")
        best = max(best, conf)

    # 2. One is Jira and the other (email/transcript) mentions its ID
    if not common_ids:
        if t1.source_type == "jira" and t2.source_type in ("email", "transcript", "slack"):
            mentioned = _extract_jira_ids(_full_text(t2)) & ids1
            if mentioned:
                conf = 0.90
                reasons.append(f"Email/Slack references Jira IDs: {', '.join(sorted(mentioned))}")
                best = max(best, conf)
        elif t2.source_type == "jira" and t1.source_type in ("email", "transcript", "slack"):
            mentioned = _extract_jira_ids(_full_text(t1)) & ids2
            if mentioned:
                conf = 0.90
                reasons.append(f"Email/Slack references Jira IDs: {', '.join(sorted(mentioned))}")
                best = max(best, conf)

    # 3. Title similarity (SequenceMatcher)
    ts = _title_sim(t1.title, t2.title)
    if ts >= RULE_THRESHOLD:
        reasons.append(f"Title similarity: {ts:.0%}")
        best = max(best, ts)

    # 4. Keyword overlap across title+description
    kw = _keyword_overlap(
        t1.title + " " + (t1.description or ""),
        t2.title + " " + (t2.description or ""),
    )
    if kw >= RULE_THRESHOLD:
        reasons.append(f"Keyword overlap: {kw:.0%}")
        best = max(best, kw)

    # 5. VP escalation + topic overlap
    if t1.vp_escalation and t2.vp_escalation:
        vp_kw = _keyword_overlap(
            t1.title + " " + (t1.description or ""),
            t2.title + " " + (t2.description or ""),
        )
        if vp_kw > 0.30:
            conf = round(0.85 * vp_kw, 2)
            reasons.append(f"Both VP-escalated with topic overlap ({vp_kw:.0%})")
            best = max(best, conf)

    reason_str = "; ".join(reasons) if reasons else ""
    return round(best, 3), reason_str


# ─── Phase 3: LLM arbitration (async) ──────────────────────────────────────────

async def _llm_confidence(t1: Task, t2: Task) -> tuple[float, str]:
    """
    Calls the LLM with build_dedup_prompt and returns (confidence, reasoning).
    Returns (0.0, "") on any failure so the caller falls back gracefully.
    """
    try:
        from core.llm_client import get_llm_client
        from core.prompts import build_dedup_prompt

        client = get_llm_client()
        system, user = build_dedup_prompt(t1.model_dump(), t2.model_dump())

        response = await client.generate(
            prompt=user,
            system=system,
            json_mode=True,
            temperature=0.1,          # near-deterministic for classification
            max_output_tokens=256,    # short structured answer only
        )

        parsed = response.parsed_json
        if parsed is None:
            # Try manual JSON extraction from raw text
            import json as _json
            try:
                parsed = _json.loads(response.text)
            except Exception:
                logger.warning("LLM dedup: could not parse JSON — %s", response.text[:200])
                return 0.0, ""

        is_dup = bool(parsed.get("is_duplicate", False))
        llm_conf = float(parsed.get("confidence", 0.0))
        reasoning = str(parsed.get("reasoning", ""))

        if not is_dup:
            # LLM says not a duplicate — confidence for merging = 0
            logger.debug("LLM dedup: NOT duplicate (%s vs %s) conf=%.2f", t1.id, t2.id, llm_conf)
            return 0.0, f"LLM: not a duplicate — {reasoning}"

        logger.debug("LLM dedup: IS duplicate (%s vs %s) conf=%.2f", t1.id, t2.id, llm_conf)
        return llm_conf, f"LLM: {reasoning}"

    except Exception as e:
        logger.warning("LLM dedup arbitration failed for (%s, %s): %s", t1.id, t2.id, e)
        return 0.0, ""


# ─── Pair scoring (blended) ─────────────────────────────────────────────────────

async def _score_pair(
    t1: Task,
    t2: Task,
    embed_sim: float,
) -> tuple[float, str]:
    """
    Runs Phases 2 and 3 for a candidate pair and returns
    (blended_confidence, explanation_string).

    embed_sim must already be >= EMBED_GATE to be called.
    """
    rule_conf, rule_reason = _rule_confidence(t1, t2)
    reasons: list[str] = []

    if embed_sim >= EMBED_GATE:
        reasons.append(f"Embedding similarity: {embed_sim:.0%}")

    # ── Hard match: trust rule, skip LLM ───────────────────────────────────────
    if rule_conf >= HARD_MATCH:
        blended = round(EMBED_W * embed_sim + RULE_W * rule_conf + LLM_W * rule_conf, 3)
        if rule_reason:
            reasons.append(rule_reason)
        return blended, "; ".join(reasons)

    # ── Grey zone: invoke LLM ─────────────────────────────────────────────────
    llm_conf, llm_reason = await _llm_confidence(t1, t2)

    if llm_conf == 0.0 and rule_conf < RULE_THRESHOLD:
        # Neither rule nor LLM supports merging — rely on embedding alone
        blended = round(embed_sim, 3)
    else:
        blended = round(EMBED_W * embed_sim + RULE_W * rule_conf + LLM_W * llm_conf, 3)

    if rule_reason:
        reasons.append(rule_reason)
    if llm_reason:
        reasons.append(llm_reason)

    return blended, "; ".join(reasons)


# ─── Merge helper ───────────────────────────────────────────────────────────────

def _merge_group(canonical: Task, duplicates: list[Task], confidence: float, reason: str) -> Task:
    """Annotates the canonical task with merged metadata from its duplicates."""
    merged_sources = list(dict.fromkeys(
        [t.source for t in [canonical] + duplicates]
    ))
    merged_from = [t.id for t in duplicates]

    canonical.merged_sources = merged_sources
    canonical.merged_from = merged_from
    canonical.dedup_group = f"dedup_{canonical.id}"
    canonical.dedup_confidence = round(confidence, 2)
    canonical.dedup_explanation = reason

    group_members = [
        {
            "task_id": t.id,
            "source": t.source,
            "source_type": t.source_type,
            "title": t.title,
            "confidence": round(confidence, 2),
            "reasoning": reason,
        }
        for t in duplicates
    ]

    canonical.raw_text = json.dumps({
        "dedup_group_id": canonical.dedup_group,
        "merged_count": len(duplicates) + 1,
        "match_confidence": round(confidence, 2),
        "reasoning": reason,
        "members": group_members,
    })

    return canonical


# ─── Public async API ───────────────────────────────────────────────────────────

async def deduplicate_async(tasks: list[Task]) -> list[Task]:
    """
    Async hybrid deduplication — preferred entry point.

    Returns a deduplicated list where each surviving task may have
    .merged_from, .merged_sources, .dedup_group, .dedup_confidence,
    .dedup_explanation set to document what was merged.
    """
    if not tasks:
        return []

    n = len(tasks)
    logger.info("Hybrid dedup started: %d tasks", n)

    # ── Phase 1: Compute embedding matrix ──────────────────────────────────────
    sim_matrix = _compute_embedding_matrix(tasks)

    # ── Find candidate pairs ───────────────────────────────────────────────────
    # candidate_pairs: list of (i, j, embed_sim) where i < j
    candidate_pairs: list[tuple[int, int, float]] = []
    if sim_matrix is not None:
        for i in range(n):
            for j in range(i + 1, n):
                sim = float(sim_matrix[i, j])
                if sim >= EMBED_GATE:
                    candidate_pairs.append((i, j, sim))
    else:
        # Fallback: treat every pair as a candidate (rules + LLM only)
        for i in range(n):
            for j in range(i + 1, n):
                candidate_pairs.append((i, j, 0.0))

    logger.info("Candidate pairs after embedding gate (%.0f%%): %d", EMBED_GATE * 100, len(candidate_pairs))

    # ── Phase 2 + 3: Score each candidate pair ─────────────────────────────────
    # Run phase-3 LLM calls concurrently (bounded by connector concurrency)
    scored: list[tuple[int, int, float, str]] = []

    async def _score_and_collect(i: int, j: int, embed_sim: float):
        conf, reason = await _score_pair(tasks[i], tasks[j], embed_sim)
        scored.append((i, j, conf, reason))

    await asyncio.gather(*[
        _score_and_collect(i, j, s) for i, j, s in candidate_pairs
    ])

    # Sort by confidence descending so we process highest-confidence merges first
    scored.sort(key=lambda x: x[2], reverse=True)

    # ── Greedy merge using Union-Find ──────────────────────────────────────────
    # Each task starts in its own group.  When a pair is merged, the lower-index
    # task absorbs the higher-index one.
    parent = list(range(n))
    merge_meta: dict[int, tuple[float, str]] = {}  # root → (confidence, reason)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int, conf: float, reason: str):
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        # Lower index (earlier in list, from higher-confidence source) wins
        if rx > ry:
            rx, ry = ry, rx
        parent[ry] = rx
        # Update meta for the root
        existing = merge_meta.get(rx, (0.0, ""))
        merge_meta[rx] = (max(existing[0], conf), reason if conf > existing[0] else existing[1])

    for i, j, conf, reason in scored:
        if conf >= MERGE_THRESHOLD:
            union(i, j, conf, reason)
            logger.info(
                "Merged %s + %s → conf=%.2f | %s",
                tasks[i].id, tasks[j].id, conf, reason[:80],
            )

    # ── Build output list ──────────────────────────────────────────────────────
    groups: dict[int, list[int]] = {}     # root → [member indices]
    for idx in range(n):
        root = find(idx)
        groups.setdefault(root, []).append(idx)

    result: list[Task] = []
    for root, members in groups.items():
        canonical_idx = root
        canonical = tasks[canonical_idx]
        duplicates = [tasks[m] for m in members if m != canonical_idx]

        if duplicates:
            conf, reason = merge_meta.get(root, (0.0, ""))
            canonical = _merge_group(canonical, duplicates, conf, reason)

        result.append(canonical)

    merged_count = n - len(result)
    logger.info(
        "Hybrid dedup complete: %d → %d tasks (%d merged)",
        n, len(result), merged_count,
    )
    return result


# ─── Synchronous shim (backward compatibility) ─────────────────────────────────

def deduplicate(tasks: list[Task]) -> list[Task]:
    """
    Synchronous wrapper around deduplicate_async.

    Called by DedupAgent.process() which is already an async context.
    Prefer calling deduplicate_async() directly from async code.

    Falls back to rule-only mode if no running event loop is available.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We are inside an async context — schedule as a coroutine
            # but we can't block here.  Callers should use deduplicate_async().
            # As a safety net, run rule-only dedup synchronously.
            logger.warning(
                "deduplicate() called from a running event loop. "
                "Use deduplicate_async() for full hybrid support. "
                "Falling back to rule-only mode."
            )
            return _rule_only_deduplicate(tasks)
        else:
            return loop.run_until_complete(deduplicate_async(tasks))
    except RuntimeError:
        # No event loop at all (e.g. test runner)
        return asyncio.run(deduplicate_async(tasks))


def _rule_only_deduplicate(tasks: list[Task]) -> list[Task]:
    """
    Pure synchronous rule-based fallback — no embeddings, no LLM.
    Used when deduplicate() is accidentally called from an async context.
    Functionally equivalent to the old deduplicator behaviour.
    """
    if not tasks:
        return []

    deduped: list[Task] = []
    merge_map: dict[str, tuple[Task, float, str]] = {}  # task.id → (canonical, conf, reason)

    for task in tasks:
        best_conf = 0.0
        best_reason = ""
        best_canonical: Task | None = None

        for existing in deduped:
            conf, reason = _rule_confidence(task, existing)
            if conf >= MERGE_THRESHOLD and conf > best_conf:
                best_conf = conf
                best_reason = reason
                best_canonical = existing

        if best_canonical is not None:
            merge_map[task.id] = (best_canonical, best_conf, best_reason)
        else:
            deduped.append(task)

    # Annotate canonical tasks
    groups: dict[str, list[Task]] = {}
    for dup_id, (canonical, conf, reason) in merge_map.items():
        groups.setdefault(canonical.id, []).append(
            next(t for t in tasks if t.id == dup_id)
        )

    result: list[Task] = []
    for task in deduped:
        dups = groups.get(task.id, [])
        if dups:
            conf = max(merge_map[d.id][1] for d in dups)
            reason = merge_map[dups[0].id][2]
            task = _merge_group(task, dups, conf, reason)
        result.append(task)

    return result
