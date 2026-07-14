from __future__ import annotations

from datetime import datetime, timezone, timedelta

from core.scoring_engine import DeterministicScoringEngine
from models.task import Task


def make_task(overrides: dict | None = None) -> Task:
    base = {
        "id": "test-1",
        "title": "Test task",
        "source": "test",
        "source_type": "jira",
        "description": "",
        "raw_text": "",
    }
    if overrides:
        base.update(overrides)
    return Task(**base)


class TestScoringEngine:
    def test_compute_score_default(self):
        task = make_task()
        score, breakdown = DeterministicScoringEngine.compute_score(task)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_p1_high_severity(self):
        task = make_task({"priority": "P1"})
        _, breakdown = DeterministicScoringEngine.compute_score(task)
        assert breakdown["severity"] >= 70

    def test_p0_max_severity(self):
        task = make_task({"priority": "P0"})
        _, breakdown = DeterministicScoringEngine.compute_score(task)
        assert breakdown["severity"] >= 95

    def test_imminent_deadline(self):
        soon = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        task = make_task({"deadline": soon})
        _, breakdown = DeterministicScoringEngine.compute_score(task)
        assert breakdown["deadline_urgency"] > 80

    def test_vp_escalation(self):
        task = make_task({"vp_escalation": True})
        _, breakdown = DeterministicScoringEngine.compute_score(task)
        assert breakdown["business_impact"] >= 90

    def test_customer_facing(self):
        task = make_task({"customer_facing": True})
        _, breakdown = DeterministicScoringEngine.compute_score(task)
        assert breakdown["business_impact"] >= 60

    def test_no_deadline_gives_mid_urgency(self):
        task = make_task({"deadline": None})
        _, breakdown = DeterministicScoringEngine.compute_score(task)
        assert 20 <= breakdown["deadline_urgency"] <= 40

    def test_multi_blocking(self):
        task = make_task({"blocks": ["task-2", "task-3"]})
        _, breakdown = DeterministicScoringEngine.compute_score(task, [task])
        assert breakdown["dependency_impact"] >= 80

    def test_single_blocking(self):
        task = make_task({"blocks": ["task-2"]})
        _, breakdown = DeterministicScoringEngine.compute_score(task, [task])
        assert 50 <= breakdown["dependency_impact"] <= 70

    def test_no_blocking(self):
        task = make_task({"blocks": []})
        _, breakdown = DeterministicScoringEngine.compute_score(task, [task])
        assert breakdown["dependency_impact"] == 0

    def test_score_breakdown_keys(self):
        task = make_task(
            {
                "priority": "P1",
                "deadline": (
                    datetime.now(timezone.utc) + timedelta(days=1)
                ).isoformat(),
            }
        )
        _, breakdown = DeterministicScoringEngine.compute_score(task)
        assert "deadline_urgency" in breakdown
        assert "severity" in breakdown
        assert "business_impact" in breakdown
        assert "dependency_impact" in breakdown

    def test_edge_case_long_deadline(self):
        far = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        task = make_task({"deadline": far})
        _, breakdown = DeterministicScoringEngine.compute_score(task)
        assert breakdown["deadline_urgency"] <= 10
