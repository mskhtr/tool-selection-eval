from __future__ import annotations


def _prf(predicted: set[str], gold: set[str]) -> tuple[float, float, float]:
    if not predicted and not gold:
        return 1.0, 1.0, 1.0
    if not predicted or not gold:
        return 0.0, 0.0, 0.0
    true_positive = len(predicted & gold)
    precision = true_positive / len(predicted)
    recall = true_positive / len(gold)
    if precision + recall == 0:
        return precision, recall, 0.0
    f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def score_case(case: dict, prediction: dict) -> dict:
    acceptable = set(case["acceptable"])
    required = set(case["required"])
    predicted = set(prediction.get("candidate_ids") or [])
    precision, recall, f1 = _prf(predicted, acceptable)
    exact = predicted == acceptable
    required_hit = required <= predicted if required else None
    single = len(acceptable) == 1 and not case["multiple"]
    single_hit = exact if single else None
    multi_appropriate = None
    if case["multiple"]:
        multi_appropriate = required <= predicted <= acceptable and len(predicted) >= 2
    clarify_appropriate = None
    if case["clarify"]:
        clarify_appropriate = bool(prediction.get("needs_clarification")) and bool(
            prediction.get("clarification_questions")
        )
    unnecessary_question = None if case["clarify"] else bool(prediction.get("needs_clarification"))
    forced_one = None
    if case["clarify"] and case["multiple"]:
        forced_one = len(predicted) == 1 and not prediction.get("needs_clarification") and not prediction.get("abstained")
    abstain_appropriate = None
    if case["applicable"] in ("no", "unknown"):
        abstain_appropriate = not predicted and bool(prediction.get("abstained"))
    return {
        "case_id": case["id"],
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact": exact,
        "required_hit": required_hit,
        "single_hit": single_hit,
        "multi_appropriate": multi_appropriate,
        "clarify_appropriate": clarify_appropriate,
        "unnecessary_question": unnecessary_question,
        "forced_one": forced_one,
        "abstain_appropriate": abstain_appropriate,
        "error": prediction.get("error"),
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _rate(flags: list[bool | None]) -> float | None:
    usable = [flag for flag in flags if flag is not None]
    if not usable:
        return None
    return sum(1 for flag in usable if flag) / len(usable)


def summarize(case_scores: list[dict], cases: list[dict]) -> dict:
    by_id = {case["id"]: case for case in cases}

    def pack(rows: list[dict]) -> dict:
        return {
            "n": len(rows),
            "precision": _mean([row["precision"] for row in rows]),
            "recall": _mean([row["recall"] for row in rows]),
            "f1": _mean([row["f1"] for row in rows]),
            "exact_rate": _rate([row["exact"] for row in rows]),
            "required_inclusion_rate": _rate([row["required_hit"] for row in rows]),
            "single_accuracy": _rate([row["single_hit"] for row in rows]),
            "multi_appropriate_rate": _rate([row["multi_appropriate"] for row in rows]),
            "clarify_appropriate_rate": _rate([row["clarify_appropriate"] for row in rows]),
            "unnecessary_question_rate": _rate([row["unnecessary_question"] for row in rows]),
            "forced_one_rate": _rate([row["forced_one"] for row in rows]),
            "abstain_appropriate_rate": _rate([row["abstain_appropriate"] for row in rows]),
            "error_rate": _rate([bool(row["error"]) for row in rows]),
        }

    summary = pack(case_scores)
    by_category: dict[str, dict] = {}
    categories = sorted({tag for case in cases for tag in case["categories"]})
    for category in categories:
        rows = [row for row in case_scores if category in by_id[row["case_id"]]["categories"]]
        by_category[category] = pack(rows)
    summary["by_category"] = by_category
    return summary
