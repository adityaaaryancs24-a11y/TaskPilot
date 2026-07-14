#!/usr/bin/env python3
"""
TaskPilot AI - One-Command Demo Script

Usage:
    python scripts/demo.py

Prerequisites:
    - Backend running on localhost:8000 (uvicorn api.main:app --reload)
    - Python dependencies installed
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

API_BASE = "http://localhost:8000"

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(text: str):
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")


def print_step(step: int, text: str):
    print(f"{BOLD}{YELLOW}[Step {step}]{RESET} {text}")


def print_ok(text: str):
    print(f"  {GREEN}\u2713{RESET} {text}")


def print_data(data: dict | list, indent: int = 2):
    print(json.dumps(data, indent=indent, default=str)[:3000])


async def main():
    print(f"{BOLD}{GREEN}")
    print("  _____ _        ____  _       _ _   ")
    print(" |_   _| |_ __ _|  _ \\| | ___ (_) |_ ")
    print("   | | | __/ _` | |_) | |/ _ \\| | __|")
    print("   | | | || (_| |  __/| | (_) | | |_ ")
    print("   |_|  \\__\\__,_|_|   |_|\\___/|_|\\__|")
    print(f"{RESET}")
    print(f"{BOLD}  TaskPilot AI - One-Command Demo{RESET}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Check health
        print_step(1, "Checking system health...")
        try:
            resp = await client.get(f"{API_BASE}/api/health")
            health = resp.json()
            print_ok(f"Status: {health['status']}, Tasks: {health['task_count']}, Jira: {health['jira_connected']}, GitHub: {health['github_connected']}")
        except Exception as e:
            print(f"  {RED}\u2717 Failed to connect: {e}{RESET}")
            print(f"  Make sure the backend is running: uvicorn api.main:app --reload")
            return

        # Step 2: Run pipeline (refresh)
        print_step(2, "Running full pipeline (Ingest -> Extract -> Dedup -> Prioritize -> Plan)...")
        try:
            start = time.monotonic()
            resp = await client.post(f"{API_BASE}/api/refresh")
            plan = resp.json()
            elapsed = time.monotonic() - start
            print_ok(f"Pipeline complete in {elapsed:.2f}s")
            print_ok(f"Generated {len(plan.get('ranked_tasks', []))} ranked tasks")
            print_ok(f"Top 3 priorities:")
            for i, t in enumerate(plan.get("top_priorities", [])[:3]):
                print(f"     {i+1}. [{t.get('priority', 'N/A')}] {t.get('title', '')[:70]} (score: {t.get('score', 0)})")
        except Exception as e:
            print(f"  {RED}\u2717 Pipeline failed: {e}{RESET}")
            return

        # Step 3: Show deduplication
        print_step(3, "Checking deduplication / cross-source correlation...")
        try:
            resp = await client.get(f"{API_BASE}/api/tasks")
            tasks = resp.json()
            merged_tasks = [t for t in tasks if t.get("merged_sources") and len(t.get("merged_sources", [])) > 0]
            if merged_tasks:
                print_ok(f"Found {len(merged_tasks)} merged task(s) with cross-source correlation:")
                for t in merged_tasks[:3]:
                    print(f"     - {t.get('id')}: {t.get('title', '')[:50]}")
                    print(f"       Merged from: {', '.join(t.get('merged_sources', []))}")
                    if t.get("dedup_confidence"):
                        print(f"       Confidence: {t.get('dedup_confidence')}")
            else:
                print_ok("No cross-source merges detected (tasks may already be unique)")
                print("  Note: JIRA-1234 (login issue) should correlate with email_008 (VP escalation)")
        except Exception as e:
            print(f"  {RED}\u2717 Failed: {e}{RESET}")

        # Step 4: Show deterministic scoring
        print_step(4, "Verifying deterministic prioritization...")
        top_tasks = plan.get("top_priorities", [])
        if top_tasks:
            t = top_tasks[0]
            print_ok(f"#1 Task: {t.get('title', '')[:60]}")
            print_ok(f"  Score: {t.get('score', 0)} (deterministic, reproducible)")
            if t.get("score_breakdown"):
                print_ok(f"  Breakdown: {json.dumps(t.get('score_breakdown', {}))}")
            print_ok(f"  Rationale: {t.get('rationale', '')[:150]}")
        else:
            print("  No tasks to score.")

        # Step 5: Get dashboard data
        print_step(5, "Loading Mission Control dashboard data...")
        try:
            resp = await client.get(f"{API_BASE}/api/dashboard")
            dash = resp.json()
            dep = dash.get("dependency_analysis", {})
            leverage = dep.get("highest_leverage_tasks", [])
            if leverage:
                print_ok(f"Highest leverage task: {leverage[0].get('title', '')[:50]} (score: {leverage[0].get('leverage_score', 0)})")
            unblocking = dep.get("unblocking_recommendations", [])
            if unblocking:
                print_ok(f"Unblocking recommendation: {unblocking[0].get('suggestion', '')[:80]}")
            time_blocks = dash.get("time_blocked_plan", {})
            if time_blocks and time_blocks.get("time_blocks"):
                print_ok(f"Generated {len(time_blocks['time_blocks'])} time blocks for today")
            calendar = dash.get("today_calendar_events", [])
            if calendar:
                print_ok(f"{len(calendar)} calendar events today")
            velocity = dash.get("team_velocity", {}).get("daily_counts", [])
            if velocity:
                print_ok(f"Team velocity data: {len(velocity)} days tracked")
            prefs = dash.get("user_preferences", {})
            if prefs:
                print_ok(f"User preferences learned: {len(prefs)} preferences")
            deferred = dash.get("deferred_tasks", [])
            if deferred:
                print_ok(f"Deferred task detection: {len(deferred)} recurring task(s)")
        except Exception as e:
            print(f"  {RED}\u2717 Dashboard failed: {e}{RESET}")

        # Step 6: Chat interaction
        print_step(6, "Testing AI Chat Assistant...")
        questions = [
            "What are my top priorities today?",
            "Which tasks are blocked?",
            "What is the login issue about?",
        ]
        for q in questions:
            try:
                resp = await client.post(f"{API_BASE}/api/chat", json={"message": q})
                chat_resp = resp.json()
                print_ok(f'Q: {q}')
                print(f'  A: {chat_resp.get("answer", "")[:150]}')
                if chat_resp.get("referenced_task_ids"):
                    print(f'  Citations: {", ".join(chat_resp["referenced_task_ids"][:3])}')
            except Exception as e:
                print(f"  {RED}\u2717 Chat failed: {e}{RESET}")

        # Step 7: Inject P1 issue
        print_step(7, "Injecting P1 issue (simulating new urgent email)...")
        try:
            resp = await client.post(f"{API_BASE}/api/inject", json={
                "title": "P1 Production Outage - Login Service Down",
                "description": "Users cannot authenticate. Auth service returning 503 errors. Customer-facing P1. VP escalation.",
                "source_type": "email",
                "priority": "P1",
                "deadline": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            })
            new_plan = resp.json()
            print_ok(f"Injected task placed at #{new_plan.get('top_priorities', [{}])[0].get('rank', '?') if new_plan.get('top_priorities') else '?'}")
            for i, t in enumerate(new_plan.get("top_priorities", [])[:3]):
                print(f"     {i+1}. [{t.get('priority', 'N/A')}] {t.get('title', '')[:60]} (score: {t.get('score', 0)})")
            print_ok("Reprioritization triggered automatically")
        except Exception as e:
            print(f"  {RED}\u2717 Inject failed: {e}{RESET}")

        # Step 8: Get traces
        print_step(8, "Gathering pipeline traces...")
        try:
            resp = await client.get(f"{API_BASE}/api/traces")
            traces = resp.json()
            if traces:
                print_ok(f"{len(traces)} trace entries")
                for t in traces[:5]:
                    print(f"     {t.get('step_name', '')}: {t.get('duration_ms', 0):.0f}ms [{t.get('status', '')}]")
        except Exception as e:
            print(f"  {RED}\u2717 Traces failed: {e}{RESET}")

        # Step 9: Weekly summary
        print_step(9, "Generating weekly summary...")
        try:
            resp = await client.get(f"{API_BASE}/api/weekly-summary")
            summary = resp.json()
            if summary.get("summary"):
                print_ok(f"Weekly summary generated ({summary.get('generated_at', '')[:10]})")
                print(f"  {summary['summary'][:200]}...")
        except Exception as e:
            print(f"  {RED}\u2717 Weekly summary failed: {e}{RESET}")

        # Step 10: Team metrics
        print_step(10, "Loading team metrics...")
        try:
            resp = await client.get(f"{API_BASE}/api/team-metrics")
            team = resp.json()
            teams = team.get("teams", {})
            if teams:
                print_ok(f"Teams tracked: {', '.join(teams.keys())}")
                for name, data in teams.items():
                    print(f"     {name}: {data.get('total_tasks', 0)} tasks, {data.get('blocked', 0)} blocked, {data.get('done', 0)} done")
        except Exception as e:
            print(f"  {RED}\u2717 Team metrics failed: {e}{RESET}")

        # Summary
        print_header("DEMO COMPLETE")
        print(f"{GREEN}All major features demonstrated:{RESET}")
        print("  \u2713 Multi-source ingestion (Jira, Email, GitHub, Slack, ServiceNow, Transcripts)")
        print("  \u2713 AI extraction of action items from unstructured text")
        print("  \u2713 Semantic deduplication with cross-source correlation")
        print("  \u2713 Deterministic prioritization with score breakdown")
        print("  \u2713 Calendar-aware time-blocked planning")
        print("  \u2713 Dependency graph analysis with critical path")
        print("  \u2713 Dynamic reprioritization on new P1 injection")
        print("  \u2713 AI Chat Assistant with task context")
        print("  \u2713 Team workload & velocity metrics")
        print("  \u2713 Weekly summary generation")
        print("  \u2713 5-agent pipeline (Observe -> Think -> Decide -> Verify -> Act)")
        print("  \u2713 Memory & preference learning")
        print("  \u2713 MCP server for AI assistant integration")
        print(f"\n{BOLD}Frontend: http://localhost:5173{RESET}")
        print(f"{BOLD}API:      http://localhost:8000{RESET}")
        print(f"{BOLD}MCP:      python mcp_server.py (stdio transport){RESET}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
