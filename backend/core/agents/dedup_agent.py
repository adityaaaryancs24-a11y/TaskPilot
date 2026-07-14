"""
DedupAgent — Orchestrator agent wrapper for the hybrid deduplication engine.

Calls deduplicate_async() (not the synchronous shim) so that the LLM
arbitration phase runs concurrently inside the pipeline event loop.
"""

import json
import logging
import re
import time
from typing import Any

from core.agents.base import BaseAgent
from core.deduplicator import deduplicate_async

logger = logging.getLogger(__name__)


class DedupAgent(BaseAgent):
    name = "deduplication"

    async def process(self, context: dict[str, Any]) -> dict[str, Any]:
        normalized_tasks = context.get("normalized_tasks", [])
        extracted_tasks = context.get("extracted_tasks", [])

        merged = normalized_tasks + extracted_tasks
        logger.info(
            "DedupAgent: merging %d normalized + %d extracted = %d total",
            len(normalized_tasks),
            len(extracted_tasks),
            len(merged),
        )

        if not merged:
            return {"deduped_tasks": []}

        t0 = time.monotonic()
        try:
            # ── Full hybrid async dedup (embedding + rules + LLM) ─────────────
            deduped = await deduplicate_async(merged)
            elapsed_ms = (time.monotonic() - t0) * 1000

            merged_count = len(merged) - len(deduped)
            logger.info(
                "DedupAgent: %d → %d tasks (%d merged) in %.0fms",
                len(merged), len(deduped), merged_count, elapsed_ms,
            )
            self.remember("last_merged_count", str(merged_count))
            self.remember("last_elapsed_ms", f"{elapsed_ms:.0f}")

        except Exception as e:
            logger.error("DedupAgent: deduplication failed: %s — using merged list", e)
            deduped = merged

        # ── Decode dedup_group JSON blob into task fields ─────────────────────
        deduped_with_explanation = []
        for t in deduped:
            if t.raw_text and t.dedup_group:
                try:
                    dedup_info = (
                        json.loads(t.raw_text)
                        if isinstance(t.raw_text, str)
                        else {}
                    )
                    if isinstance(dedup_info, dict) and "dedup_group_id" in dedup_info:
                        # Promote fields from the JSON blob to first-class attrs
                        if not t.dedup_explanation:
                            t.dedup_explanation = dedup_info.get("reasoning", "")
                        if not t.dedup_confidence:
                            t.dedup_confidence = dedup_info.get("match_confidence", 0.0)
                        if "members" in dedup_info:
                            t.dedup_members = dedup_info["members"]
                        t.raw_text = ""        # clear the blob — info is now on the task
                except (json.JSONDecodeError, TypeError):
                    pass
            deduped_with_explanation.append(t)

        return {"deduped_tasks": deduped_with_explanation}

    async def reflect(self, context: dict[str, Any]) -> dict[str, Any]:
        reflection = await super().reflect(context)
        normalized = context.get("normalized_tasks", [])
        extracted = context.get("extracted_tasks", [])
        total = len(normalized) + len(extracted)

        reflection["observations"] = [
            f"Received {total} tasks ({len(normalized)} normalized, {len(extracted)} extracted)",
            "Hybrid dedup engine active: embedding (Phase 1) + rules (Phase 2) + LLM (Phase 3)",
        ]

        # Cross-source Jira ↔ email correlation hints
        jira_tasks = [t for t in (normalized + extracted) if t.source_type == "jira"]
        email_tasks = [t for t in (normalized + extracted) if t.source_type in ("email", "transcript", "slack")]

        if jira_tasks and email_tasks:
            reflection["decisions"] = [
                "Cross-source correlation active between Jira and email/transcript/Slack tasks"
            ]
            jira_ids_found = []
            for t in email_tasks:
                ids = re.findall(
                    r"[A-Z]+-\d+",
                    t.title + " " + (t.description or "") + " " + (t.raw_text or ""),
                )
                if ids:
                    jira_ids_found.append({"email": t.id, "jira_ids": ids})
            if jira_ids_found:
                reflection["observations"].append(
                    f"Email/Slack-to-Jira references detected: {jira_ids_found}"
                )

        last_merged = self.recall("last_merged_count")
        if last_merged:
            reflection["observations"].append(
                f"Previous pipeline merged {last_merged} duplicates"
            )

        return reflection

    async def verify(self, result: dict[str, Any]) -> dict[str, Any]:
        tasks = result.get("deduped_tasks", [])
        issues = []

        # Sanity: no two surviving tasks should share the same id
        ids = [t.id for t in tasks]
        if len(ids) != len(set(ids)):
            issues.append("Duplicate IDs found in deduped output — possible merge bug")

        # Sanity: merged tasks should have dedup_group set
        for t in tasks:
            if t.merged_from and not t.dedup_group:
                issues.append(f"Task {t.id} has merged_from but no dedup_group")

        return {
            "verified": len(issues) == 0,
            "agent": self.name,
            "issues": issues,
            "task_count": len(tasks),
        }
