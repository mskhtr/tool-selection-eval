from __future__ import annotations

ERROR_TAGS = (
    "過剰な意図補完",
    "表層キーワード誤選択",
    "候補漏れ",
    "過剰選択",
    "不適切な追加質問",
    "質問不足",
    "カタログ照合ミス",
    "その他",
)


def classify_errors(case: dict, prediction: dict) -> list[str]:
    """規則による誤り分類。人手確認ではない。"""
    acceptable = set(case["acceptable"])
    required = set(case["required"])
    predicted = set(prediction.get("candidate_ids") or [])
    tags: list[str] = []
    if prediction.get("invalid_ids"):
        tags.append("カタログ照合ミス")
    if prediction.get("error") and not predicted and not prediction.get("invalid_ids"):
        tags.append("その他")
        return _unique(tags)
    if required - predicted or (case["applicable"] == "yes" and acceptable and not (predicted & acceptable)):
        tags.append("候補漏れ")
    extra = predicted - acceptable
    if len(extra) >= 2 or len(predicted) >= int(case.get("excess_cap") or 5):
        tags.append("過剰選択")
    forced = (
        case["clarify"]
        and case["multiple"]
        and len(predicted) == 1
        and not prediction.get("needs_clarification")
        and not prediction.get("abstained")
    )
    if forced or prediction.get("unstated_assumptions"):
        tags.append("過剰な意図補完")
    if "keyword_trap" in case["categories"] and predicted:
        tags.append("表層キーワード誤選択")
    if case["clarify"] and not prediction.get("needs_clarification"):
        tags.append("質問不足")
    if (not case["clarify"]) and prediction.get("needs_clarification"):
        tags.append("不適切な追加質問")
    exact_behavior = predicted == acceptable and bool(prediction.get("needs_clarification")) == bool(case["clarify"])
    if not tags and not exact_behavior:
        tags.append("その他")
    return _unique(tags)


def _unique(tags: list[str]) -> list[str]:
    ordered = []
    for tag in ERROR_TAGS:
        if tag in tags and tag not in ordered:
            ordered.append(tag)
    return ordered


def count_tags(rows: list[list[str]]) -> dict[str, int]:
    counts = {tag: 0 for tag in ERROR_TAGS}
    for tags in rows:
        for tag in tags:
            counts[tag] = counts.get(tag, 0) + 1
    return counts
