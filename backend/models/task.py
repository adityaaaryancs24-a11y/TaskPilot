from pydantic import BaseModel
from typing import Optional, Literal


class Task(BaseModel):
    id: str
    title: str
    description: str = ""
    source: str
    source_type: Literal[
        "jira",
        "defect",
        "email",
        "transcript",
        "injected",
        "servicenow",
        "github",
        "slack",
    ]
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    deadline: Optional[str] = None
    owner: Optional[str] = None
    status: Literal["open", "in_progress", "blocked", "done", "deferred"] = "open"
    dependencies: list[str] = []
    blocks: list[str] = []
    raw_text: str = ""
    merged_from: list[str] = []
    merged_sources: list[str] = []
    grounded: Optional[bool] = None
    grounding_confidence: Optional[float] = None
    confidence: Optional[float] = None
    source_sentence: Optional[str] = None
    vp_escalation: bool = False
    customer_facing: bool = False
    dedup_group: Optional[str] = None
    assignee: Optional[str] = None
    team: Optional[str] = None
    dedup_explanation: Optional[str] = None
    dedup_confidence: Optional[float] = None
    dedup_members: Optional[list[dict]] = None
    blocking_impact_score: Optional[float] = None
    time_block: Optional[str] = None


class RankedTask(Task):
    rank: int = 0
    score: float = 0.0
    score_breakdown: dict[str, float] = {}
    rationale: str = ""


class Alert(BaseModel):
    severity: Literal["info", "warning", "critical"]
    message: str
    task_id: Optional[str] = None


class DailyPlan(BaseModel):
    generated_at: str = ""
    top_priorities: list[RankedTask] = []
    do_next: list[RankedTask] = []
    deferred: list[RankedTask] = []
    blocked: list[RankedTask] = []
    alerts: list[Alert] = []
    ranked_tasks: list[RankedTask] = []
    time_blocked_plan: Optional[dict] = None
    highest_leverage_tasks: Optional[list[dict]] = None
    deferred_tasks_detected: Optional[list[dict]] = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    referenced_task_ids: list[str] = []


class InjectRequest(BaseModel):
    title: str
    description: str = ""
    source_type: Literal[
        "jira",
        "defect",
        "email",
        "transcript",
        "injected",
        "servicenow",
        "github",
        "slack",
    ] = "injected"
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    deadline: Optional[str] = None
    owner: Optional[str] = None


class ConvertHiddenRequest(BaseModel):
    task_id: str
    title: Optional[str] = None
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    deadline: Optional[str] = None


class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    source_type: Optional[
        Literal[
            "jira",
            "defect",
            "email",
            "transcript",
            "injected",
            "servicenow",
            "github",
            "slack",
        ]
    ] = "injected"
    source: Optional[str] = "manual"
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    status: Optional[Literal["open", "in_progress", "blocked", "done", "deferred"]] = (
        "open"
    )
    deadline: Optional[str] = None
    owner: Optional[str] = None
    assignee: Optional[str] = None
    team: Optional[str] = None


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Literal["P0", "P1", "P2", "P3"]] = None
    status: Optional[Literal["open", "in_progress", "blocked", "done", "deferred"]] = (
        None
    )
    deadline: Optional[str] = None
    owner: Optional[str] = None
    assignee: Optional[str] = None
    team: Optional[str] = None


class DashboardResponse(BaseModel):
    plan: DailyPlan
    time_blocked_plan: Optional[dict] = None
    highest_leverage_tasks: Optional[list[dict]] = None
    unblocking_recommendations: Optional[list[dict]] = None
    deferred_tasks: Optional[list[dict]] = None
    team_velocity: Optional[dict] = None
    completion_patterns: Optional[dict] = None
