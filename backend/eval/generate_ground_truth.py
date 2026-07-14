import requests
import json

API_BASE = "http://localhost:8000"


def regenerate():
    tasks = requests.get(f"{API_BASE}/api/tasks").json()
    plan = requests.get(f"{API_BASE}/api/plan").json()

    # Extract email/transcript tasks
    extracted = [t for t in tasks if t.get("source_type") in ["email", "transcript"]]
    action_items = []
    for t in extracted:
        action_items.append(
            {
                "id": t["id"],
                "title": t["title"],
                "source_sentence": t.get("source_sentence", "")
                or t.get("description", "")[:100],
                "source_type": t.get("source_type"),
            }
        )

    # Priority order from ranked tasks
    priority_order = [t["id"] for t in plan.get("ranked_tasks", [])[:5]]

    # Dedup pairs (you can manually add if needed)
    dedup_pairs = []

    ground_truth = {
        "expected_action_items": action_items,
        "expected_dedup_pairs": dedup_pairs,
        "expected_priority_order": priority_order,
        "expected_rationale_keywords": {},
    }

    with open("eval/ground_truth.json", "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"✅ Ground truth updated with {len(action_items)} action items")


if __name__ == "__main__":
    regenerate()
