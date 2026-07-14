"""
Script to test the /api/inject endpoint with various scenarios.

Usage:
    python eval/inject_scenarios.py

Requires backend running on localhost:8000
"""

import json
import sys

sys.path.insert(0, ".")

import requests

API_BASE = "http://localhost:8000"


def print_json(data):
    print(json.dumps(data, indent=2, default=str)[:2000])


def test_inject_scenario(name: str, payload: dict):
    print(f"\n{'=' * 50}")
    print(f"Scenario: {name}")
    print(f"{'=' * 50}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        resp = requests.post(f"{API_BASE}/api/inject", json=payload, timeout=30)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            top3 = data.get("top_priorities", [])
            print("Top 3 after injection:")
            for i, t in enumerate(top3[:3]):
                score_breakdown = t.get("score_breakdown", {})
                print(
                    f"  {i + 1}. [{t.get('priority', 'N/A')}] {t.get('title', '')[:60]}"
                )
                print(
                    f"      Score: {t.get('score', 0)} | Breakdown: {json.dumps(score_breakdown)}"
                )
                print(f"      Rationale: {t.get('rationale', '')[:120]}")
            print(f"Total alerts: {len(data.get('alerts', []))}")
        else:
            print(f"Error: {resp.text[:500]}")
    except Exception as e:
        print(f"Failed: {e}")


def main():
    print("Testing /api/inject endpoint...")
    print(f"API base: {API_BASE}")

    # Step 1: Check health
    resp = requests.get(f"{API_BASE}/api/health")
    print(f"\nHealth: {resp.json().get('status', 'unknown')}")

    # Step 2: Ensure pipeline has run
    try:
        resp = requests.post(f"{API_BASE}/api/refresh", timeout=60)
        print(f"Pipeline: {resp.status_code}")
    except Exception as e:
        print(f"Pipeline trigger failed: {e}")

    # Scenario 1: P1 production outage
    test_inject_scenario(
        "P1 Production Outage",
        {
            "title": "P1 Production Outage - Login Service Down",
            "description": "Users cannot authenticate. Auth service returning 503 errors. Customer-facing P1. VP escalation.",
            "source_type": "email",
            "priority": "P1",
            "deadline": "2026-06-21T18:00:00Z",
        },
    )

    # Scenario 2: Security vulnerability
    test_inject_scenario(
        "Critical Security Vulnerability",
        {
            "title": "CVE-2026-1234 - Remote code execution in auth module",
            "description": "Critical vulnerability discovered in authentication module. Patch required immediately. All users affected.",
            "source_type": "jira",
            "priority": "P0",
            "deadline": "2026-06-21T12:00:00Z",
        },
    )

    # Scenario 3: Low priority task
    test_inject_scenario(
        "Low Priority - Update README",
        {
            "title": "Update README with new API endpoints",
            "description": "The README is missing documentation for the new dashboard and dependency endpoints.",
            "source_type": "github",
            "priority": "P3",
        },
    )

    # Scenario 4: VP escalation via email
    test_inject_scenario(
        "VP Escalation - Customer Downtime",
        {
            "title": "VP ESCALATION: Major customer experiencing downtime",
            "description": "The VP of Engineering is asking about the ACME Corp downtime. This is a customer-facing P0 with executive visibility.",
            "source_type": "email",
            "priority": "P0",
            "deadline": "2026-06-21T14:00:00Z",
        },
    )


if __name__ == "__main__":
    main()
