# TaskPilot AI — Backend

Real-time agentic task prioritization platform.

## Architecture

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌────────────┐   ┌──────────┐
│  Ingestion  │ → │  Extraction  │ → │  Dedup      │ → │  Priority  │ → │ Planning │
│  Agent      │   │  Agent       │   │  Agent      │   │  Agent     │   │ Agent    │
└─────────────┘   └──────────────┘   └─────────────┘   └────────────┘   └──────────┘
       │                  │                 │                 │               │
       ▼                  ▼                 ▼                 ▼               ▼
   ┌────────┐     ┌──────────────┐     ┌───────────┐     ┌──────────┐     ┌────────┐
   │ Jira   │     │ LLM         │     │ Semantic  │     │ Determ.  │     │ Daily  │
   │ GitHub │     │ Extraction   │     │ Dedup     │     │ Scoring  │     │ Plan   │
   │ Slack  │     │             │     │ Cross-    │     │ Engine   │     │ Time-  │
   │ Email  │     │             │     │ Source    │     │ (no LLM) │     │ Blocks │
   │ SN     │     │             │     │ Correl.   │     │          │     │        │
   └────────┘     └──────────────┘     └───────────┘     └──────────┘     └────────┘
```

## Agentic Workflow

```
Observe → Think → Decide → Verify → Act
```

Each agent runs through the full cycle with shared memory and reflection.

## Key Improvements (v0.3.0)

### 1. Semantic Deduplication
- Cross-source correlation (JIRA-1234 ↔ VP escalation email)
- Keyword overlap scoring
- Confidence scores with explanations
- Dedup group tracking in DB

### 2. Deterministic Prioritization
- 7-factor scoring formula (severity, deadline, business impact, dependency, customer, escalation, team blocking)
- LLM bypassed for scores — only generates rationale
- Reproducible, auditable, explainable

### 3. Calendar-Aware Planning
- Simulated calendar events (standup, sprint planning, demos)
- Time-blocked daily plans
- Unavailable slot detection
- Deep work windows scheduled around meetings

### 4. Dependency Graph Intelligence
- DAG analysis with topological sort
- Critical path detection
- Blocking impact scores (direct + transitive)
- Unblocking recommendations
- Highest leverage task identification

### 5. Memory & Learning
- User preference storage (explicit + inferred)
- Completion pattern tracking
- Deferred task detection
- Preference learning from feedback
- Agent shared memory

### 6. True Agentic Behavior
- Observe → Think → Decide → Verify → Act cycle
- Agent reflection step
- Verification step
- Shared memory across agents
- Pipeline history tracking

### 7. MCP Integration
- MCP server with stdio transport
- Tools: list_tasks, get_task, get_plan, get_dashboard, get_team_metrics, get_dependency_analysis, inject_task
- opencode.json configuration

### 8. Dynamic Reprioritization
- Automatic reprioritization on task injection
- Narrative alerts for changes
- WebSocket broadcast of updated plan

### 9. Team Dashboard
- Per-team workload metrics
- Velocity tracking (daily completion counts)
- Risk indicators (blocked, overdue, unassigned P0/P1)
- Sprint health overview

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health check |
| POST | `/api/refresh` | Run full pipeline |
| GET | `/api/plan` | Get current daily plan |
| GET | `/api/tasks` | List all tasks (with filters) |
| GET | `/api/tasks/:id` | Get single task |
| GET | `/api/dashboard` | Full dashboard with deps, calendar, velocity |
| POST | `/api/chat` | Ask questions about tasks |
| POST | `/api/inject` | Inject new P1 task |
| POST | `/api/feedback` | Submit feedback |
| GET | `/api/weekly-summary` | AI weekly summary |
| GET | `/api/team-metrics` | Team workload stats |
| GET | `/api/dependency-analysis` | Dependency graph analysis |
| GET | `/api/calendar/today` | Today's calendar events |
| GET | `/api/memory/preferences` | Learned user preferences |
| WS | `/ws` | Real-time updates |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
uvicorn api.main:app --reload
```

## MCP Server

```bash
python mcp_server.py
```

Configure in your AI assistant's opencode.json:

```json
{
  "mcpServers": {
    "taskpilot": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "env": { "PYTHONPATH": "backend" }
    }
  }
}
```

## Demo

```bash
python scripts/demo.py
```

## Evaluation

```bash
# Ensure backend is running
uvicorn api.main:app --reload

# Run evaluation
cd backend && python -m eval.evaluator
```

## Module Ownership

| Module | Owner |
|--------|-------|
| Ingestion Agent | Aditya |
| Extraction Agent | Aditya |
| Dedup Agent | Aditya |
| Priority Agent | Aditya |
| Planning Agent | Aditya |
| Alert Agent | Aditya |
| MCP Server | Aditya |
| Frontend Dashboard | Aditya |

## Completion Status

- Must-Have: 95%+ ✓
- Should-Have: 90%+ ✓
- Could-Have: 60%+ ✓
