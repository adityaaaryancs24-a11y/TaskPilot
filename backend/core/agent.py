import asyncio
import logging
import time

from models.task import Task, RankedTask, DailyPlan, InjectRequest
from core.state import store, save_state, save_trace
from core.agents.orchestrator import AgentOrchestrator
from core.alert_engine import check_alerts

from core.prioritizer import reprioritize, build_daily_plan_from_tasks
from core.normalizer import _infer_team
from core.tracer import trace
from core.grounding import verify_grounding
from core.qa import answer_question as qa_answer_question
from core.notification_service import notification_service
from core.dependency_analyzer import DependencyAnalyzer
from core.calendar_planner import CalendarPlanner

logger = logging.getLogger(__name__)

HAS_WEEKLY_SUMMARY = True

_orchestrator = AgentOrchestrator()


@trace("pipeline")
async def run_pipeline() -> DailyPlan:
    start_time = time.monotonic()
    logger.info("=== Pipeline run started ===")

    try:
        context = await _orchestrator.run_pipeline()
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        raise

    ranked_tasks = context.get("ranked_tasks", [])
    plan = context.get("plan")

    if not plan:
        alerts = context.get("alerts", [])
        plan = build_daily_plan_from_tasks(ranked_tasks, alerts)

    time_blocked = context.get("time_blocked_plan")
    if time_blocked:
        plan.time_blocked_plan = time_blocked

    leverage = context.get("highest_leverage_tasks")
    if leverage:
        plan.highest_leverage_tasks = leverage

    deferred = context.get("deferred_tasks_detected")
    if deferred:
        plan.deferred_tasks_detected = deferred

    store.update(ranked_tasks, plan)
    await save_state(ranked_tasks, plan)
    await save_trace("pipeline_total", (time.monotonic() - start_time) * 1000)

    notification_service.schedule(plan=plan, tasks=ranked_tasks, alerts=plan.alerts)

    elapsed = time.monotonic() - start_time
    logger.info("=== Pipeline finished in %.2fs ===", elapsed)
    if elapsed > 60:
        logger.warning("Pipeline exceeded 60s target (%.2fs)", elapsed)

    return plan


async def reprioritize_with_injection(new_task_data: InjectRequest) -> DailyPlan:
    start_time = time.monotonic()
    logger.info("=== Reprioritize with injection started ===")

    if store.current_plan is None:
        raise RuntimeError("No existing plan to reprioritize — run refresh first")

    try:
        new_task = Task(
            id=f"injected_{int(time.time())}",
            title=new_task_data.title,
            description=new_task_data.description or "",
            source="injected",
            source_type=new_task_data.source_type or "injected",
            priority=new_task_data.priority,
            deadline=new_task_data.deadline,
            owner=new_task_data.owner,
            assignee=new_task_data.owner,
            team=_infer_team(new_task_data.owner),
            status="open",
            dependencies=[],
            raw_text=new_task_data.title + " " + (new_task_data.description or ""),
            grounded=True,
            grounding_confidence=1.0,
        )
        logger.info("Injected task: %s (%s)", new_task.id, new_task.title)

        result = await asyncio.to_thread(verify_grounding, new_task, {})
        new_task.grounded = result.get("grounded", True)
        new_task.grounding_confidence = result.get("confidence", 0.95)

        updated_ranked, change_summary = await reprioritize(
            store.current_tasks, new_task
        )

        alerts_list = check_alerts(updated_ranked)
        new_plan = build_daily_plan_from_tasks(updated_ranked, alerts_list)

        time_blocked = CalendarPlanner.generate_time_blocked_plan(
            updated_ranked[: min(6, len(updated_ranked))]
        )
        if time_blocked:
            new_plan.time_blocked_plan = time_blocked

        leverage = DependencyAnalyzer.find_highest_leverage_tasks(updated_ranked)
        if leverage:
            new_plan.highest_leverage_tasks = leverage

        store.update(updated_ranked, new_plan)

        top = updated_ranked[0] if updated_ranked else None
        if top and top.merged_sources and top.vp_escalation:
            store.narrative_alert = (
                f"I noticed {', '.join(top.merged_sources)} and {top.id} are about the same issue "
                f"— I merged them and placed {top.id} at #1. SLA: {top.deadline}. "
                f"Dedup confidence: {top.dedup_confidence or 'N/A'}. "
                f"Reason: {top.rationale}"
            )
        elif top and top.priority in ("P0", "P1"):
            store.narrative_alert = (
                f"\u26a0 {top.id} is a {top.priority} with deadline {top.deadline}. "
                f"Placed at #1 automatically. {top.rationale}"
            )

        if change_summary:
            store.narrative_alert = f"{store.narrative_alert or ''} | {change_summary}"

        await save_state(updated_ranked, new_plan)
        notification_service.schedule(
            plan=new_plan, tasks=updated_ranked, alerts=new_plan.alerts
        )

        narrative = getattr(store, "narrative_alert", None)
        if narrative:
            notification_service.schedule(narrative=narrative)
            store.narrative_alert = None

        elapsed = time.monotonic() - start_time
        logger.info("=== Reprioritize finished in %.2fs ===", elapsed)
        if elapsed > 15:
            logger.warning("Reprioritize exceeded 15s target (%.2fs)", elapsed)

        return new_plan
    except Exception as e:
        logger.error("Reprioritize failed: %s", e)
        raise


async def answer_question(question: str, tasks: list[RankedTask], context: dict) -> str:
    result = await qa_answer_question(tasks, question, context.get("chat_history"))
    return result.answer
