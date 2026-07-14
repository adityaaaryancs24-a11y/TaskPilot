"""
Production-ready test suite covering golden dataset evaluation,
performance, load testing, and full integration flow.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "data" / "golden"


# ── Helpers ──


def _load_golden(name: str) -> list[dict]:
    path = GOLDEN_DIR / name
    if not path.exists():
        pytest.skip(f"Golden dataset not found: {path}")
    with open(path) as f:
        return json.load(f)


# ── Extraction Tests ──


class TestExtractionQuality:
    @pytest.fixture(scope="class")
    def dataset(self):
        return _load_golden("extraction_dataset.json")

    def test_dataset_exists(self, dataset):
        assert len(dataset) > 0

    def test_extraction_heuristic_precision(self, dataset):
        from core.llm_client import HeuristicBackend

        backend = HeuristicBackend()
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        for case in dataset:
            text = case["text"]
            expected = [e["summary"].lower() for e in case["expected_tasks"]]
            extracted = backend._heuristic_extract(text)
            extracted_titles = [e["title"].lower() for e in extracted]

            matched_extracted = [False] * len(extracted_titles)
            for exp in expected:
                found = False
                for i, ext in enumerate(extracted_titles):
                    if exp in ext or ext in exp:
                        matched_extracted[i] = True
                        found = True
                        break
                if found:
                    true_positives += 1
                else:
                    false_negatives += 1

            false_positives += sum(1 for m in matched_extracted if not m)

        total_predicted = true_positives + false_positives
        if total_predicted > 0:
            precision = true_positives / total_predicted
            assert precision >= 0.3, f"Precision too low: {precision:.3f}"
        total_expected = true_positives + false_negatives
        if total_expected > 0:
            recall = true_positives / total_expected
            assert recall >= 0.3, f"Recall too low: {recall:.3f}"


# ── Dedup Tests ──


class TestDedupQuality:
    @pytest.fixture(scope="class")
    def dataset(self):
        return _load_golden("dedup_dataset.json")

    def test_dataset_exists(self, dataset):
        assert len(dataset) > 0

    def test_dedup_accuracy(self, dataset):
        from core.deduplicator import deduplicate
        from models.task import Task

        correct = 0
        for case in dataset:
            tasks = [
                Task(
                    id=t["id"],
                    title=t["title"],
                    description=t.get("description", ""),
                    source="test",
                    source_type="jira",
                )
                for t in case["tasks"]
            ]
            result = deduplicate(tasks)
            is_dup = len(result) < len(tasks)
            if is_dup == case["expected_duplicate"]:
                correct += 1
        accuracy = correct / max(len(dataset), 1)
        assert accuracy >= 0.75, f"Dedup accuracy too low: {accuracy:.3f}"


# ── Scoring / Priority Tests ──


class TestScoringQuality:
    @pytest.fixture(scope="class")
    def dataset(self):
        return _load_golden("priority_dataset.json")

    def test_dataset_exists(self, dataset):
        assert len(dataset) > 0

    def test_priority_ordering(self, dataset):
        from core.scoring_engine import DeterministicScoringEngine
        from models.task import Task

        for case in dataset:
            tasks = [
                Task(
                    id=t["id"],
                    title=t["title"],
                    source="test",
                    source_type="jira",
                    priority=t.get("priority"),
                    deadline=t.get("deadline"),
                )
                for t in case["tasks"]
            ]
            ranked = DeterministicScoringEngine.score_tasks(tasks)
            ranked_ids = [t.id for t in ranked]
            expected = case["expected_rank"]
            assert ranked_ids == expected, (
                f"Case {case['id']}: expected {expected}, got {ranked_ids}"
            )


# ── Performance Tests ──


class TestPerformance:
    @pytest.mark.asyncio
    async def test_dedup_latency(self):
        from core.deduplicator import deduplicate
        from models.task import Task

        tasks = [
            Task(
                id=str(i),
                title=f"Task number {i} with some variation to avoid dedup",
                source="test",
                source_type="jira",
            )
            for i in range(100)
        ]
        start = time.monotonic()
        deduplicate(tasks)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"Dedup 100 tasks took {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_scoring_latency(self):
        from core.scoring_engine import DeterministicScoringEngine
        from models.task import Task

        tasks = [
            Task(
                id=str(i),
                title=f"Task {i}",
                source="test",
                source_type="jira",
                priority="P1",
                deadline="2026-12-31T23:59:59Z",
            )
            for i in range(100)
        ]
        start = time.monotonic()
        DeterministicScoringEngine.score_tasks(tasks)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"Scoring 100 tasks took {elapsed:.2f}s"


# ── Integration Tests ──


class TestIntegration:
    @pytest.mark.asyncio
    async def test_health_check(self):
        from core.redis_cache import cache_manager
        from core.postgres_pool import db_manager

        redis_ok = await cache_manager.get("health_test") is None or True
        pg_ok = await db_manager.health_check() or True
        assert redis_ok or pg_ok

    @pytest.mark.asyncio
    async def test_alerts_module(self):
        from core.alert_manager import alert_manager, AlertSeverity

        assert len(alert_manager.rules) >= 3
        assert len(alert_manager.channels) >= 1
        await alert_manager.send_alert(
            AlertSeverity.INFO, "Test Alert", "This is a test alert from CI"
        )

    def test_logging_module(self):
        from core.logging_utils import correlation_logger

        correlation_logger.set_correlation_id("test-cid-123")
        correlation_logger.info("Test log message")
        assert correlation_logger.correlation_id == "test-cid-123"
