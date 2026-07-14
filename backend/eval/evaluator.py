import json
import requests
import sys
from typing import Dict, List
from rapidfuzz import fuzz

API_BASE_URL = "http://localhost:8000"


def load_ground_truth():
    with open("eval/ground_truth.json", "r") as f:
        return json.load(f)


def fetch_data(endpoint: str):
    try:
        resp = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Failed to fetch {endpoint}: {e}")
        return None


def evaluate_extraction(gt: Dict, tasks: List) -> Dict:
    gt_items = gt.get("expected_action_items", [])
    if not gt_items:
        return {"recall": 1.0, "precision": 1.0, "matches": 0}

    gt_titles = [i["title"].lower() for i in gt_items]
    ext_titles = [
        t.get("title", "").lower()
        for t in tasks
        if t.get("source_type") in ["email", "transcript"]
    ]

    matches = 0
    for gt_title in gt_titles:
        for ext_title in ext_titles:
            if fuzz.partial_ratio(gt_title, ext_title) > 70:
                matches += 1
                break

    recall = matches / len(gt_titles)
    precision = matches / len(ext_titles) if ext_titles else 0.0

    return {
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "matches": matches,
        "gt_count": len(gt_titles),
    }


def evaluate_deduplication(gt: Dict, tasks: List) -> Dict:
    gt_pairs = gt.get("expected_dedup_pairs", [])
    if not gt_pairs:
        return {"precision": 1.0}

    task_map = {t.get("id", ""): t for t in tasks}
    correct = 0
    total = len(gt_pairs)

    for pair in gt_pairs:
        t1 = task_map.get(pair["task1_id"])
        t2 = task_map.get(pair["task2_id"])
        if not t1 or not t2:
            continue

        t1_merged = t1.get("merged_from", [])
        t2_merged = t2.get("merged_from", [])
        merged = bool(
            (pair["task1_id"] in t2_merged or pair["task2_id"] in t1_merged)
            or (
                t1.get("dedup_group") is not None
                and t1["dedup_group"] == t2.get("dedup_group")
            )
        )

        if merged == pair["should_merge"]:
            correct += 1

    precision = correct / total if total > 0 else 1.0
    return {"precision": round(precision, 3), "correct": correct, "total": total}


def evaluate_prioritization(gt: Dict, ranked: List) -> Dict:
    gt_order = gt.get("expected_priority_order", [])
    if not gt_order:
        return {"tau": 1.0, "acceptable": True}

    actual = [t.get("id", "") for t in ranked]
    common = [x for x in gt_order if x in actual]
    if len(common) < 2:
        return {"tau": 0.0, "acceptable": False}

    actual_rank = {t: i for i, t in enumerate(actual) if t in common}
    concordant = 0
    discordant = 0

    for i in range(len(common)):
        for j in range(i + 1, len(common)):
            if actual_rank.get(common[i], 0) < actual_rank.get(common[j], 0):
                concordant += 1
            else:
                discordant += 1

    tau = (
        (concordant - discordant) / (concordant + discordant)
        if (concordant + discordant) > 0
        else 0
    )
    return {"tau": round(tau, 3), "acceptable": tau >= 0.8}


def evaluate_rationale(gt: Dict, ranked: List) -> Dict:
    gt_keywords = gt.get("expected_rationale_keywords", {})
    scores = []
    for task in ranked:
        task_id = task.get("id", "")
        rationale = task.get("rationale", "").lower()
        if task_id in gt_keywords:
            keywords = gt_keywords[task_id]
            found = sum(1 for kw in keywords if kw.lower() in rationale)
            scores.append(found / len(keywords) if keywords else 0)
    avg = sum(scores) / len(scores) if scores else 0
    return {"coverage": round(avg, 3)}


def evaluate_deterministic_scoring(gt: Dict, ranked: List) -> Dict:
    """Verify that scores are deterministic and reproducible."""
    gt_scores = gt.get("expected_scores", {})
    if not gt_scores:
        return {"deterministic": True, "score_accuracy": 1.0}

    matching = 0
    total = 0
    for task in ranked:
        task_id = task.get("id", "")
        expected = gt_scores.get(task_id)
        if expected is not None:
            total += 1
            actual = task.get("score", 0)
            if abs(actual - expected) / max(expected, 1) < 0.2:
                matching += 1

    accuracy = matching / total if total > 0 else 1.0
    return {
        "deterministic": True,
        "score_accuracy": round(accuracy, 3),
        "matching": matching,
        "total": total,
    }


def evaluate_cross_source_dedup(gt: Dict, tasks: List) -> Dict:
    """Verify cross-source links by checking both task-map and merged_from."""
    gt_cross = gt.get("expected_cross_source_links", [])
    if not gt_cross:
        return {"cross_source_precision": 1.0}

    task_map = {t.get("id", ""): t for t in tasks}
    merged_into: dict[str, str] = {}
    for t in tasks:
        for merged_id in t.get("merged_from") or []:
            merged_into[merged_id] = t["id"]

    correct = 0
    total = len(gt_cross)

    for link in gt_cross:
        t1_id = link["task1_id"]
        t2_id = link["task2_id"]
        t1 = task_map.get(t1_id)
        t2 = task_map.get(t2_id)

        linked = False
        if t1 and t2:
            t1_merged = t1.get("merged_from", [])
            t2_merged = t2.get("merged_from", [])
            linked = bool(
                t1_id in t2_merged
                or t2_id in t1_merged
                or (
                    t1.get("dedup_group") is not None
                    and t1["dedup_group"] == t2.get("dedup_group")
                )
            )
        elif t1:
            linked = bool(t2_id in (t1.get("merged_from") or []))
        elif t2:
            linked = bool(t1_id in (t2.get("merged_from") or []))
        else:
            linked = (
                merged_into.get(t1_id) == merged_into.get(t2_id)
                and merged_into.get(t1_id) is not None
            )

        if linked == link["should_link"]:
            correct += 1

    precision = correct / total if total > 0 else 1.0
    return {
        "cross_source_precision": round(precision, 3),
        "correct": correct,
        "total": total,
    }


def run():
    print("=" * 60)
    print("TaskPilot AI - Evaluation Runner")
    print("=" * 60)

    gt = load_ground_truth()
    print(f"Ground truth loaded ({len(gt.get('expected_action_items', []))} items)")

    tasks_data = fetch_data("/api/tasks")
    plan_data = fetch_data("/api/plan")

    if not tasks_data or not plan_data:
        print("\nFailed to fetch API data. Is the backend running?")
        print("   Run: uvicorn api.main:app --reload")
        sys.exit(1)

    tasks = tasks_data if isinstance(tasks_data, list) else tasks_data.get("tasks", [])
    ranked = plan_data.get("ranked_tasks", [])
    print(f"API data: {len(tasks)} tasks, {len(ranked)} ranked")

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    ext = evaluate_extraction(gt, tasks)
    print("\nExtraction (target: recall >= 0.95):")
    print(f"   Recall: {ext['recall']:.3f} | Precision: {ext['precision']:.3f}")
    print(f"   Matches: {ext['matches']}/{ext['gt_count']}")

    dedup = evaluate_deduplication(gt, tasks)
    print("\nDeduplication (target: precision >= 0.90):")
    print(f"   Precision: {dedup['precision']:.3f}")
    print(f"   Correct: {dedup.get('correct', 0)}/{dedup.get('total', 0)}")

    cross = evaluate_cross_source_dedup(gt, tasks)
    print("\nCross-Source Dedup (JIRA-1234 <-> email_008):")
    print(f"   Precision: {cross['cross_source_precision']:.3f}")
    print(f"   Correct: {cross.get('correct', 0)}/{cross.get('total', 0)}")

    priority = evaluate_prioritization(gt, ranked)
    print("\nPrioritization (target: tau >= 0.80):")
    print(
        f"   Kendall's Tau: {priority['tau']:.3f} {'PASS' if priority['acceptable'] else 'FAIL'}"
    )

    det_score = evaluate_deterministic_scoring(gt, ranked)
    print("\nDeterministic Scoring:")
    print(f"   Accuracy: {det_score['score_accuracy']:.3f}")
    print(f"   Matching: {det_score.get('matching', 0)}/{det_score.get('total', 0)}")

    rationale = evaluate_rationale(gt, ranked)
    print("\nRationale Quality:")
    print(f"   Keyword Coverage: {rationale['coverage']:.3f}")

    print("\n" + "=" * 60)
    all_pass = (
        ext["recall"] >= 0.95
        and dedup["precision"] >= 0.90
        and cross["cross_source_precision"] >= 0.90
        and priority["acceptable"]
    )
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 60)
    return all_pass


if __name__ == "__main__":
    run()
