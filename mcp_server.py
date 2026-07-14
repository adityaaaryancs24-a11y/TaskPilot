#!/usr/bin/env python3
"""MCP (Model Context Protocol) server for TaskPilot AI.

Provides tools for AI assistants to:
- List and retrieve tasks
- Get current daily plan
- Get dependency analysis
- Get team metrics

Run: python mcp_server.py
"""

import json
import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("mcp-server")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from core.state import store, load_state, get_team_velocity
from models.task import DailyPlan

store.current_tasks, store.current_plan = load_state()


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id", 0)

    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {
                        "tools": {
                            "list_tasks": "List all current tasks with optional filters",
                            "get_task": "Get a specific task by ID",
                            "get_plan": "Get the current daily plan",
                            "get_dashboard": "Get full dashboard data including dependency analysis",
                            "get_team_metrics": "Get team workload and velocity metrics",
                            "get_dependency_analysis": "Get dependency graph analysis",
                            "inject_task": "Inject a new high-priority task",
                        }
                    },
                    "serverInfo": {
                        "name": "taskpilot-mcp",
                        "version": "0.1.0",
                    },
                },
            }

        elif method == "tools/list":
            tools = [
                {
                    "name": "list_tasks",
                    "description": "List all current tasks with optional filters (source_type, priority, status)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "source_type": {"type": "string", "description": "Filter by source type (jira, email, github, slack, etc.)"},
                            "priority": {"type": "string", "description": "Filter by priority (P0, P1, P2, P3)"},
                            "status": {"type": "string", "description": "Filter by status (open, in_progress, blocked, done)"},
                        },
                    },
                },
                {
                    "name": "get_task",
                    "description": "Get a specific task by ID",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "The task ID"},
                        },
                        "required": ["task_id"],
                    },
                },
                {
                    "name": "get_plan",
                    "description": "Get the current daily plan with top priorities",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "get_dashboard",
                    "description": "Get full dashboard data including dependency analysis, time-blocked plan, and team velocity",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "get_team_metrics",
                    "description": "Get team workload, velocity, and distribution metrics",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "get_dependency_analysis",
                    "description": "Get dependency graph analysis including critical path and blocking impacts",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "inject_task",
                    "description": "Inject a new high-priority task and trigger reprioritization",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "description": {"type": "string", "description": "Task description"},
                            "priority": {"type": "string", "description": "Priority (P0, P1, P2, P3)"},
                            "deadline": {"type": "string", "description": "Deadline ISO datetime"},
                        },
                        "required": ["title"],
                    },
                },
            ]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})

            if tool_name == "list_tasks":
                tasks = store.current_tasks
                if tool_args.get("source_type"):
                    tasks = [t for t in tasks if t.source_type == tool_args["source_type"]]
                if tool_args.get("priority"):
                    tasks = [t for t in tasks if t.priority == tool_args["priority"]]
                if tool_args.get("status"):
                    tasks = [t for t in tasks if t.status == tool_args["status"]]
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(
                            [t.model_dump(mode="json") for t in tasks], indent=2, default=str
                        )}]
                    },
                }

            elif tool_name == "get_task":
                task_id = tool_args.get("task_id", "")
                for t in store.current_tasks:
                    if t.id == task_id:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": [{"type": "text", "text": json.dumps(t.model_dump(mode="json"), indent=2, default=str)}]
                            },
                        }
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": f"Task {task_id} not found"},
                }

            elif tool_name == "get_plan":
                if store.current_plan:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(store.current_plan.model_dump(mode="json"), indent=2, default=str)}]
                        },
                    }
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"content": [{"type": "text", "text": "No plan available. Run the pipeline first."}]},
                }

            elif tool_name == "get_dashboard":
                from core.dependency_analyzer import DependencyAnalyzer
                from core.calendar_planner import CalendarPlanner
                from core.memory import memory_system
                tasks = store.current_tasks
                ranked = store.current_plan.ranked_tasks if store.current_plan else []
                dependencies = DependencyAnalyzer.compute_blocking_impact(tasks)
                leverage = DependencyAnalyzer.find_highest_leverage_tasks(tasks)
                unblocking = DependencyAnalyzer.get_unblocking_recommendations(tasks)
                time_blocks = CalendarPlanner.generate_time_blocked_plan(ranked[:6]) if ranked else None
                preferences = memory_system.get_all_preferences()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({
                            "task_count": len(tasks),
                            "top_priorities": [t.model_dump(mode="json") for t in ranked[:3]] if ranked else [],
                            "highest_leverage_tasks": leverage,
                            "unblocking_recommendations": unblocking[:3] if unblocking else [],
                            "time_blocked_plan": time_blocks,
                            "user_preferences": preferences,
                        }, indent=2, default=str)}]
                    },
                }

            elif tool_name == "get_team_metrics":
                tasks = store.current_tasks
                team_stats = {}
                for t in tasks:
                    team = t.team or "unassigned"
                    if team not in team_stats:
                        team_stats[team] = {"total": 0, "blocked": 0, "done": 0, "in_progress": 0}
                    team_stats[team]["total"] += 1
                    if t.status == "blocked": team_stats[team]["blocked"] += 1
                    if t.status == "done": team_stats[team]["done"] += 1
                    if t.status == "in_progress": team_stats[team]["in_progress"] += 1
                velocity = get_team_velocity()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({
                            "team_stats": team_stats,
                            "velocity": velocity,
                        }, indent=2, default=str)}]
                    },
                }

            elif tool_name == "get_dependency_analysis":
                from core.dependency_analyzer import DependencyAnalyzer
                tasks = store.current_tasks
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({
                            "critical_path": DependencyAnalyzer.find_critical_path(tasks),
                            "blocking_impacts": DependencyAnalyzer.compute_blocking_impact(tasks),
                            "highest_leverage_tasks": DependencyAnalyzer.find_highest_leverage_tasks(tasks),
                            "unblocking_recommendations": DependencyAnalyzer.get_unblocking_recommendations(tasks),
                        }, indent=2, default=str)}]
                    },
                }

            elif tool_name == "inject_task":
                import asyncio
                from core.agent import reprioritize_with_injection
                from models.task import InjectRequest
                req = InjectRequest(
                    title=tool_args.get("title", "New task"),
                    description=tool_args.get("description", ""),
                    priority=tool_args.get("priority", "P1"),
                    deadline=tool_args.get("deadline"),
                )
                plan = asyncio.run(reprioritize_with_injection(req))
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(plan.model_dump(mode="json"), indent=2, default=str)}]
                    },
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

    except Exception as e:
        logger.error("Error handling request: %s", e)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(e)},
        }


def main():
    import sys

    logger.info("TaskPilot MCP server starting (stdio transport)...")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.error("Unhandled error: %s", e)


if __name__ == "__main__":
    main()
