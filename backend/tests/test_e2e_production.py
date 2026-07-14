"""
End-to-end production readiness tests.
These test the full pipeline with realistic data.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from core.agent import run_pipeline, reprioritize_with_injection
from core.state import store
from models.task import InjectRequest
from core.dependency_analyzer import DependencyAnalyzer


@pytest.mark.asyncio
async def test_full_pipeline_execution():
    """Test the complete pipeline end-to-end."""
    plan = await run_pipeline()
    assert plan is not None
    assert plan.generated_at is not None
    assert len(store.current_tasks) > 0


@pytest.mark.asyncio
async def test_pipeline_produces_ranked_tasks():
    """Pipeline should produce ranked tasks with scores."""
    plan = await run_pipeline()
    assert len(plan.top_priorities) > 0
    task = plan.top_priorities[0]
    assert task.score > 0
    assert task.rationale != ""
    assert len(task.score_breakdown) > 0


@pytest.mark.asyncio
async def test_pipeline_produces_alerts():
    """Pipeline should detect and generate alerts."""
    plan = await run_pipeline()
    assert hasattr(plan, "alerts")


@pytest.mark.asyncio
async def test_injection_reprioritizes():
    """Injecting a P1 should change the plan."""
    await run_pipeline()
    old_top = (
        store.current_plan.top_priorities[0]
        if store.current_plan and store.current_plan.top_priorities
        else None
    )

    new_task = InjectRequest(
        title="CRITICAL: Production database outage",
        description="Database is down, all customers affected.",
        source_type="injected",
        priority="P1",
        deadline=(datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
    )
    new_plan = await reprioritize_with_injection(new_task)

    assert new_plan is not None
    assert len(new_plan.top_priorities) > 0
    # Injected task should be in top priorities
    titles = [t.title.lower() for t in new_plan.top_priorities]
    assert any("outage" in t or "critical" in t for t in titles)


@pytest.mark.asyncio
async def test_dependency_analysis():
    """Dependency analysis should work with pipeline tasks."""
    await run_pipeline()
    tasks = store.current_tasks
    assert len(tasks) > 0

    critical_path = DependencyAnalyzer.find_critical_path(tasks)
    impact = DependencyAnalyzer.compute_blocking_impact(tasks)
    leverage = DependencyAnalyzer.find_highest_leverage_tasks(tasks)
    unblocking = DependencyAnalyzer.get_unblocking_recommendations(tasks)

    assert isinstance(critical_path, list)
    assert isinstance(impact, dict)
    assert isinstance(leverage, list)
    assert isinstance(unblocking, list)


@pytest.mark.asyncio
async def test_pipeline_multiple_runs_stable():
    """Run pipeline twice; state should be consistent."""
    plan1 = await run_pipeline()
    count1 = len(store.current_tasks)

    plan2 = await run_pipeline()
    count2 = len(store.current_tasks)

    assert count1 == count2
    assert plan1.generated_at != plan2.generated_at


@pytest.mark.asyncio
async def test_pipeline_recovers_from_failures():
    """Pipeline should not crash on bad data."""
    original_tasks = store.current_tasks[:]
    try:
        store.current_tasks = []
        plan = await run_pipeline()
        assert plan is not None
    finally:
        store.current_tasks = original_tasks


@pytest.mark.asyncio
async def test_calendar_planner_integration():
    """Calendar planner should generate time blocks."""
    from core.calendar_planner import CalendarPlanner

    await run_pipeline()
    tasks = store.current_plan.top_priorities[:6] if store.current_plan else []
    if tasks:
        blocks = CalendarPlanner.generate_time_blocked_plan(tasks)
        assert blocks is not None
