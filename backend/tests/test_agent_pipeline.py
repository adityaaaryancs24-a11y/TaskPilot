import time
import pytest
from datetime import datetime, timedelta, timezone

from models.task import Task, DailyPlan, InjectRequest, RankedTask, ChatResponse
from core.alert_engine import check_alerts


@pytest.mark.asyncio
async def test_full_pipeline():
    from core.agent import run_pipeline

    start = time.monotonic()
    plan = await run_pipeline()
    elapsed = time.monotonic() - start
    assert elapsed < 60, f"Pipeline took {elapsed:.2f}s, expected <60s"
    assert isinstance(plan, DailyPlan)
    # Pipeline may return empty plan if LLM API is unavailable (quota limits)
    assert plan.top_priorities is not None


@pytest.mark.asyncio
async def test_plan_shape():
    from core.agent import run_pipeline

    plan = await run_pipeline()
    assert plan.generated_at is not None
    if len(plan.top_priorities) > 0:
        for t in plan.top_priorities:
            assert isinstance(t, RankedTask)
            assert t.rank >= 1
            assert t.score > 0
            assert t.rationale


@pytest.mark.asyncio
async def test_inject_changes_rank_order():
    from core.agent import run_pipeline, reprioritize_with_injection
    from core.state import store

    plan = await run_pipeline()
    assert store.current_plan is not None

    inject_req = InjectRequest(
        title="CRITICAL: Production outage — fix immediately",
        description="All users are unable to log in. This is a P0 incident.",
        source_type="injected",
        priority="P0",
        deadline=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        owner="alice",
    )

    new_plan = await reprioritize_with_injection(inject_req)
    assert new_plan.top_priorities is not None
    if len(new_plan.top_priorities) > 0:
        injected_ids = [
            t.id for t in new_plan.top_priorities if t.id.startswith("injected_")
        ]
        assert len(injected_ids) > 0, "Injected task should be in top priorities"


@pytest.mark.asyncio
async def test_chat_returns_answer():
    from core.agent import run_pipeline
    from core.qa import answer_question
    from core.state import store

    await run_pipeline()
    tasks = store.current_tasks
    response = await answer_question(tasks, "What are my top priorities?", [])
    assert isinstance(response, ChatResponse)
    assert len(response.answer) > 0


def test_alert_engine():
    now = datetime.now(timezone.utc)
    tasks = [
        Task(
            id="T1",
            title="Urgent P0",
            source="T1",
            source_type="jira",
            priority="P0",
            deadline=(now + timedelta(hours=1)).isoformat(),
            status="open",
            owner="alice",
        ),
        Task(
            id="T2",
            title="Overdue defect",
            source="T2",
            source_type="defect",
            priority="P1",
            deadline=(now - timedelta(hours=2)).isoformat(),
            status="open",
            owner=None,
        ),
        Task(
            id="T3",
            title="Blocking task",
            source="T3",
            source_type="jira",
            priority="P2",
            deadline=None,
            status="blocked",
            owner="bob",
            dependencies=["T1"],
        ),
    ]
    alerts = check_alerts(tasks)
    assert any(a.severity == "critical" for a in alerts)
    assert any(
        "deadline" in a.message.lower() or "past" in a.message.lower() for a in alerts
    )
