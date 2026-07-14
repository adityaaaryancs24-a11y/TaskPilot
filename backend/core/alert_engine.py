from datetime import datetime, timedelta, timezone
from dateutil import parser
from models.task import Task, Alert


def _parse_deadline(dl: str | None) -> datetime | None:
    if not dl:
        return None
    try:
        dt = parser.parse(dl)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def check_alerts(tasks: list[Task]) -> list[Alert]:
    alerts: list[Alert] = []
    now = datetime.now(timezone.utc)
    deadline_threshold = now + timedelta(hours=24)

    open_tasks = [t for t in tasks if t.status != "done"]

    # Critical: deadline within 24 hours and not done
    for t in open_tasks:
        dl = _parse_deadline(t.deadline)
        if dl and dl <= deadline_threshold:
            if dl > now:
                remaining = dl - now
                hours = int(remaining.total_seconds() / 3600)
                alerts.append(
                    Alert(
                        severity="critical",
                        message=f"{t.priority or 'Task'} {t.id} ({t.title[:50]}) has SLA expiring in ~{hours}h and is {t.status}",
                        task_id=t.id,
                    )
                )
            else:
                alerts.append(
                    Alert(
                        severity="critical",
                        message=f"{t.priority or 'Task'} {t.id} ({t.title[:50]}) is past deadline and {t.status}",
                        task_id=t.id,
                    )
                )

    # Critical: P0 / P1 with no owner
    for t in open_tasks:
        if t.priority in ("P0", "P1") and not t.owner:
            alerts.append(
                Alert(
                    severity="critical",
                    message=f"{t.priority} {t.source_type} {t.id} ({t.title[:50]}) is unassigned",
                    task_id=t.id,
                )
            )

    # Warning: task blocking 2+ other open tasks
    blocking_map: dict[str, list[Task]] = {}
    for t in open_tasks:
        for dep_id in t.dependencies:
            blocking_map.setdefault(dep_id, []).append(t)
    for blocked_id, blockers in blocking_map.items():
        if len(blockers) >= 2:
            blocked_task = next((t for t in tasks if t.id == blocked_id), None)
            label = blocked_task.title[:50] if blocked_task else blocked_id
            alerts.append(
                Alert(
                    severity="warning",
                    message=f"{blocked_id} ({label}) is blocking {len(blockers)} tasks ({', '.join(b.id for b in blockers)})",
                    task_id=blocked_id,
                )
            )

    # Info: >15 open tasks signals overload
    if len(open_tasks) > 15:
        alerts.append(
            Alert(
                severity="info",
                message=f"You have {len(open_tasks)} open tasks — consider delegating or deferring low-priority items",
                task_id=None,
            )
        )

    return alerts
