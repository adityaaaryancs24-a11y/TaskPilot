import requests
import json
from rapidfuzz import fuzz

API_BASE = "http://localhost:8000"


def fetch_tasks():
    resp = requests.get(f"{API_BASE}/api/tasks")
    resp.raise_for_status()
    return resp.json()


def fetch_plan():
    resp = requests.get(f"{API_BASE}/api/plan")
    resp.raise_for_status()
    return resp.json()


def generate_ground_truth():
    tasks = fetch_tasks()
    plan = fetch_plan()

    extracted = [t for t in tasks if t.get("source_type") in ["email", "transcript"]]
    expected_action_items = []
    for t in extracted:
        expected_action_items.append(
            {
                "id": t.get("id"),
                "title": t.get("title"),
                "source_sentence": t.get("description", "")[:150] or t.get("title", ""),
                "source_type": t.get("source_type"),
            }
        )

    dedup_pairs = []
    checked = set()
    for i, t1 in enumerate(tasks):
        for j, t2 in enumerate(tasks):
            if i >= j or t1.get("id") in checked or t2.get("id") in checked:
                continue
            title1 = t1.get("title", "")
            title2 = t2.get("title", "")
            if fuzz.partial_ratio(title1, title2) > 80:
                dedup_pairs.append(
                    {
                        "task1_id": t1.get("id"),
                        "task2_id": t2.get("id"),
                        "should_merge": True,
                        "reason": f"Similar titles: '{title1[:40]}' and '{title2[:40]}'",
                    }
                )
                checked.add(t1.get("id"))
                checked.add(t2.get("id"))
                break

    ranked = plan.get("ranked_tasks", [])
    priority_order = [t.get("id") for t in ranked[:5]]

    rationale_keywords = {}
    for t in ranked[:3]:
        rationale_keywords[t.get("id")] = ["high priority", "urgent"]

    ground_truth = {
        "expected_action_items": expected_action_items,
        "expected_dedup_pairs": dedup_pairs,
        "expected_priority_order": priority_order,
        "expected_rationale_keywords": rationale_keywords,
    }

    with open("eval/ground_truth.json", "w") as f:
        json.dump(ground_truth, f, indent=2)

    print("Generated ground_truth.json from live data")
    print(f"   - {len(expected_action_items)} action items")
    print(f"   - {len(dedup_pairs)} dedup pairs")
    print(f"   - {len(priority_order)} priority order items")


if __name__ == "__main__":
    generate_ground_truth()
