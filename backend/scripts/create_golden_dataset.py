"""
Create golden datasets for evaluating extraction, dedup, and prioritization.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "golden"


def generate_extraction_dataset():
    return [
        {
            "id": "extract_001",
            "text": "Can you please fix the upload bug? It's blocking the release. Also, remember to update the documentation.",
            "expected_tasks": [
                {"summary": "Fix upload bug", "priority_hint": "high"},
                {"summary": "Update documentation", "priority_hint": "medium"},
            ],
        },
        {
            "id": "extract_002",
            "text": "The auth service is down. Could someone investigate immediately? P1 incident.",
            "expected_tasks": [
                {
                    "summary": "Investigate auth service outage",
                    "priority_hint": "critical",
                }
            ],
        },
        {
            "id": "extract_003",
            "text": "Please review the PR for the new feature and schedule a demo with the team.",
            "expected_tasks": [
                {"summary": "Review PR for new feature", "priority_hint": "medium"},
                {"summary": "Schedule demo with team", "priority_hint": "low"},
            ],
        },
        {
            "id": "extract_004",
            "text": "Just a heads up, the deployment went smoothly. No action needed.",
            "expected_tasks": [],
        },
        {
            "id": "extract_005",
            "text": "TODO: Fix memory leak in scheduler. FIXME: Add pagination to search results.",
            "expected_tasks": [
                {"summary": "Fix memory leak in scheduler", "priority_hint": "high"},
                {
                    "summary": "Add pagination to search results",
                    "priority_hint": "medium",
                },
            ],
        },
        {
            "id": "extract_006",
            "text": "Make sure to deploy the hotfix by EOD. Don't forget to update the SSL certificates.",
            "expected_tasks": [
                {"summary": "Deploy the hotfix by EOD", "priority_hint": "critical"},
                {"summary": "Update SSL certificates", "priority_hint": "high"},
            ],
        },
    ]


def generate_dedup_dataset():
    return [
        {
            "id": "dedup_001",
            "tasks": [
                {
                    "id": "JIRA-123",
                    "title": "Fix data pipeline failure",
                    "description": "The data pipeline is failing intermittently",
                },
                {
                    "id": "EMAIL-001",
                    "title": "Data pipeline broken",
                    "description": "Pipeline keeps failing, please check",
                },
            ],
            "expected_duplicate": True,
        },
        {
            "id": "dedup_002",
            "tasks": [
                {
                    "id": "JIRA-456",
                    "title": "Implement user authentication",
                    "description": "Add OAuth support",
                },
                {
                    "id": "JIRA-789",
                    "title": "Fix login page CSS",
                    "description": "Login page styling broken",
                },
            ],
            "expected_duplicate": False,
        },
        {
            "id": "dedup_003",
            "tasks": [
                {
                    "id": "JIRA-101",
                    "title": "Deploy hotfix to production",
                    "description": "Hotfix for critical bug",
                },
                {
                    "id": "EMAIL-002",
                    "title": "Deploy hotfix to production",
                    "description": "Urgent: deploy hotfix",
                },
            ],
            "expected_duplicate": True,
        },
        {
            "id": "dedup_004",
            "tasks": [
                {
                    "id": "JIRA-202",
                    "title": "Database migration script",
                    "description": "Write migration for new schema",
                },
                {
                    "id": "EMAIL-003",
                    "title": "Review PR for API changes",
                    "description": "Please review the new API endpoints",
                },
            ],
            "expected_duplicate": False,
        },
    ]


def generate_priority_dataset():
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "priority_001",
            "tasks": [
                {
                    "id": "task1",
                    "title": "Fix P1 production bug",
                    "priority": "P1",
                    "deadline": (now + timedelta(hours=2)).isoformat(),
                },
                {
                    "id": "task2",
                    "title": "Add new feature",
                    "priority": "P3",
                    "deadline": (now + timedelta(days=7)).isoformat(),
                },
            ],
            "expected_rank": ["task1", "task2"],
        },
        {
            "id": "priority_002",
            "tasks": [
                {
                    "id": "task3",
                    "title": "Documentation update",
                    "priority": "P3",
                    "deadline": None,
                },
                {
                    "id": "task4",
                    "title": "Critical security patch",
                    "priority": "P0",
                    "deadline": (now + timedelta(hours=1)).isoformat(),
                },
                {
                    "id": "task5",
                    "title": "Refactor auth module",
                    "priority": "P2",
                    "deadline": (now + timedelta(days=3)).isoformat(),
                },
            ],
            "expected_rank": ["task4", "task3", "task5"],
        },
    ]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = {
        "extraction_dataset.json": generate_extraction_dataset(),
        "dedup_dataset.json": generate_dedup_dataset(),
        "priority_dataset.json": generate_priority_dataset(),
    }

    for name, data in datasets.items():
        path = OUTPUT_DIR / name
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Created {path} ({len(data)} test cases)")

    print("Golden datasets created successfully.")


if __name__ == "__main__":
    main()
