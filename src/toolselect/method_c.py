from __future__ import annotations

from functools import cache

import yaml

from toolselect.catalog import Catalog
from toolselect.paths import METHOD_C_PATH
from toolselect.schema import empty_output, with_ranks
from toolselect.textutil import parse_json_payload


@cache
def load_c_rules(path: str | None = None) -> dict:
    if path is None:
        text = METHOD_C_PATH.read_text(encoding="utf-8")
    else:
        from pathlib import Path

        text = Path(path).read_text(encoding="utf-8")
    return yaml.safe_load(text)


def resolve_score_rows(payload: dict, catalog: Catalog) -> dict:
    """LLMの言及をカタログIDへ引き当てる。スコアの意味は変えない。"""
    known = catalog.ids()
    resolved: list[dict] = []
    invalid_ids: list[str] = []
    unresolved: list[str] = []
    seen: set[str] = set()
    for row in payload.get("scores") or []:
        if not isinstance(row, dict):
            unresolved.append(str(row))
            continue
        mention = str(row.get("tool_id") or row.get("name") or row.get("id") or "").strip()
        tool_id = mention if mention in known else catalog.resolve_mention(mention)
        if tool_id is None:
            bucket = invalid_ids if mention else unresolved
            bucket.append(mention or str(row))
            continue
        if tool_id in seen:
            continue
        seen.add(tool_id)
        try:
            score = float(row.get("score"))
        except (TypeError, ValueError):
            unresolved.append(mention)
            continue
        resolved.append(
            {
                "tool_id": tool_id,
                "score": score,
                "reason": str(row.get("reason") or ""),
                "mention": mention,
            }
        )
    return {
        "rows": resolved,
        "invalid_ids": invalid_ids,
        "unresolved_mentions": unresolved,
        "missing_information": bool(payload.get("missing_information")),
        "missing_items": [str(item) for item in payload.get("missing_items") or []],
    }


def decide_from_scores(resolved: dict, rules: dict | None = None) -> dict:
    """スコアの差と情報不足から、候補提示か追加質問かを決める。"""
    rules = rules or load_c_rules()
    rows = sorted(resolved["rows"], key=lambda row: (-row["score"], row["tool_id"]))
    output = empty_output(case_id="", condition_id="", method="C", model_id=None)
    output["invalid_ids"] = list(resolved["invalid_ids"])
    output["unresolved_mentions"] = list(resolved["unresolved_mentions"])
    output["scores"] = {row["tool_id"]: row["score"] for row in rows}
    trace = ["score_sort", "dictionary_resolve"]
    if resolved["invalid_ids"] or resolved["unresolved_mentions"]:
        trace.append("resolve_mismatch")

    if not rows:
        output.update(
            {
                "abstained": True,
                "needs_clarification": True,
                "clarification_questions": ["カタログのツールに結び付く採点が無かったため保留した。目的を教えてください。"],
                "reasons": ["有効なツールIDのスコアが無かった。"],
                "rule_trace": trace + ["no_resolved_score"],
            }
        )
        return output

    top = rows[0]["score"]
    window = float(rules["near_tie_window"])
    minimum = float(rules["min_include_score"])
    high = float(rules["high_confidence"])
    band = [row for row in rows if row["score"] >= minimum and row["score"] >= top - window]
    if not band:
        output.update(
            {
                "abstained": True,
                "needs_clarification": True,
                "clarification_questions": ["適合度がどれも低いです。解析の対象と、何を知りたいかを教えてください。"],
                "reasons": ["どのツールも採用しきい値に届かなかった。スコアは確率として解釈していない。"],
                "rule_trace": trace + ["below_minimum"],
            }
        )
        return output

    capped = band[: int(rules["max_candidates"])]
    if len(band) > int(rules["max_candidates"]):
        trace.append("capped")
    candidate_ids = [row["tool_id"] for row in capped]
    missing = resolved["missing_information"]
    close = len(band) > 1
    needs_clarification = close or (missing and top < high)
    questions: list[str] = []
    if needs_clarification:
        if resolved["missing_items"]:
            questions.append("次を教えてください。" + "、".join(resolved["missing_items"]))
        else:
            names = "、".join(candidate_ids)
            questions.append(f"上位候補が接近しています。目的に近いものを指定してください。候補: {names}")
    reasons = [
        "適合度スコアの順位と候補間の差で候補を決めた。スコアは校正済み確率ではない。",
    ]
    if missing:
        reasons.append("採点側が情報不足を示した。")
    output.update(
        {
            "candidate_ids": candidate_ids,
            "ranks": with_ranks(candidate_ids),
            "needs_clarification": needs_clarification,
            "clarification_questions": questions,
            "abstained": False,
            "reasons": reasons,
            "rule_trace": trace,
        }
    )
    return output


def parse_score_response(raw: str, catalog: Catalog, rules: dict | None = None) -> dict:
    try:
        payload = parse_json_payload(raw)
    except (ValueError, TypeError) as error:
        output = empty_output(case_id="", condition_id="", method="C", model_id=None)
        output["error"] = f"parse_error: {error}"
        output["abstained"] = True
        output["needs_clarification"] = True
        output["rule_trace"] = ["parse_error"]
        return output
    if isinstance(payload, list):
        payload = {"scores": payload, "missing_information": False, "missing_items": []}
    if not isinstance(payload, dict):
        output = empty_output(case_id="", condition_id="", method="C", model_id=None)
        output["error"] = "parse_error: object expected"
        output["abstained"] = True
        return output
    resolved = resolve_score_rows(payload, catalog)
    decided = decide_from_scores(resolved, rules)
    scored_ids = {row["tool_id"] for row in resolved["rows"]}
    missing_tools = catalog.ids() - scored_ids
    if len(scored_ids) * 2 < len(catalog.ids()):
        decided["error"] = "incomplete_scores"
        decided["rule_trace"] = list(decided["rule_trace"]) + ["incomplete_scores"]
    elif missing_tools:
        decided["rule_trace"] = list(decided["rule_trace"]) + ["partial_scores"]
    return decided
