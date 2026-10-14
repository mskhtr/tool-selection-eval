from __future__ import annotations

from functools import cache

import yaml

from toolselect.catalog import Catalog, Tool
from toolselect.paths import METHOD_B_PATH
from toolselect.schema import empty_output, with_ranks
from toolselect.textutil import normalize_text


@cache
def load_b_rules(path: str | None = None) -> dict:
    rule_path = METHOD_B_PATH if path is None else path
    if path is None:
        text = METHOD_B_PATH.read_text(encoding="utf-8")
    else:
        from pathlib import Path

        text = Path(path).read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _contains_any(text: str, phrases: list[str]) -> list[str]:
    hits = []
    for phrase in phrases:
        if normalize_text(phrase) and normalize_text(phrase) in text:
            hits.append(phrase)
    return hits


def _tool_hits(tool: Tool, text: str) -> dict[str, list[str]]:
    names = _contains_any(text, list(tool.name_forms()))
    purposes = _contains_any(text, list(tool.purpose_signals))
    weaks = _contains_any(text, list(tool.rule_keywords))
    return {"name": names, "purpose": purposes, "weak": weaks}


def _suppress_shorter_purpose(purpose_hits: dict[str, list[str]]) -> set[str]:
    """短い手がかりが、他ツールの長い手がかりに含まれるときだけ落とす。"""
    drop: set[str] = set()
    for tool_id, signals in purpose_hits.items():
        if not signals:
            continue

        def covered(signal: str) -> bool:
            for other_id, other_signals in purpose_hits.items():
                if other_id == tool_id:
                    continue
                for other in other_signals:
                    if signal != other and signal in other:
                        return True
            return False

        if all(covered(signal) for signal in signals):
            drop.add(tool_id)
    return drop


def select_with_rules(user_text: str, catalog: Catalog, rules: dict | None = None) -> dict:
    rules = rules or load_b_rules()
    text = normalize_text(user_text)
    trace: list[str] = ["normalize_nfkc"]
    meta_hits = _contains_any(text, rules["hard_meta_substrings"])
    if meta_hits:
        trace.append("meta_veto:" + ",".join(meta_hits))
        return _finish(
            candidate_ids=[],
            abstained=True,
            needs_clarification=True,
            questions=["これは解析ツールの実行依頼ですか。実行するなら、対象と知りたいことを指定してください。"],
            reasons=["説明・事務・検索の表現が含まれるため、ツールを選ばず保留した。"],
            trace=trace,
        )

    request_hits = _contains_any(text, rules["request_substrings"])
    if not request_hits:
        trace.append("no_request_verb")
        return _finish(
            candidate_ids=[],
            abstained=True,
            needs_clarification=True,
            questions=["解析として何を計算したいかを教えてください。"],
            reasons=["解析の実行を頼む表現が無いため保留した。"],
            trace=trace,
        )

    per_tool = {tool.id: _tool_hits(tool, text) for tool in catalog.tools}
    purpose_hits = {tool_id: hits["purpose"] for tool_id, hits in per_tool.items() if hits["purpose"]}
    suppressed = _suppress_shorter_purpose(purpose_hits)
    if suppressed:
        trace.append("suppress_shorter_purpose:" + ",".join(sorted(suppressed)))
        for tool_id in suppressed:
            per_tool[tool_id]["purpose"] = []

    for tool_id, hits in per_tool.items():
        if hits["name"]:
            trace.append(f"alias:{tool_id}")
        if hits["purpose"]:
            trace.append(f"purpose:{tool_id}")
        if hits["weak"]:
            trace.append(f"weak:{tool_id}")

    strong = [
        tool_id
        for tool_id, hits in per_tool.items()
        if hits["name"] or hits["purpose"]
    ]
    named = [tool_id for tool_id, hits in per_tool.items() if hits["name"]]
    family_tools = _matched_family_tools(text, rules)
    if family_tools:
        trace.append("family:" + ",".join(family_tools))

    if strong:
        ordered = _order(strong, per_tool, catalog)
        combination = _contains_any(text, rules["combination_substrings"])
        all_named = all(tool_id in named for tool_id in ordered)
        needs_clarification = len(ordered) > 1 and not all_named and not combination
        if combination and len(ordered) > 1:
            trace.append("explicit_combination")
        reasons = ["名称・別名または目的の手がかりが一致したツールを候補にした。"]
        if needs_clarification:
            reasons.append("候補が複数あり、入力だけでは一つに決められない。")
        return _finish(
            candidate_ids=ordered,
            abstained=False,
            needs_clarification=needs_clarification,
            questions=_question(ordered, catalog) if needs_clarification else [],
            reasons=reasons,
            trace=trace,
        )

    if family_tools:
        ordered = [tool_id for tool_id in _catalog_order(catalog) if tool_id in family_tools]
        return _finish(
            candidate_ids=ordered,
            abstained=False,
            needs_clarification=True,
            questions=_question(ordered, catalog),
            reasons=["対象の系統だけが分かり、解析目的の手がかりが無いので候補を並べて確認する。"],
            trace=trace,
        )

    weak = [tool_id for tool_id, hits in per_tool.items() if hits["weak"]]
    if weak:
        ordered = _order(weak, per_tool, catalog)
        trace.append("weak_only")
        return _finish(
            candidate_ids=ordered,
            abstained=False,
            needs_clarification=True,
            questions=_question(ordered, catalog),
            reasons=["弱いキーワードだけが一致したため、一つには決めず確認する。"],
            trace=trace,
        )

    trace.append("no_match")
    return _finish(
        candidate_ids=[],
        abstained=True,
        needs_clarification=True,
        questions=["どの解析を実行したいか、対象と知りたいことを教えてください。"],
        reasons=["カタログの名称、目的の手がかり、系統のいずれにも一致しなかった。"],
        trace=trace,
    )


def _matched_family_tools(text: str, rules: dict) -> list[str]:
    found: list[str] = []
    for family in rules["families"].values():
        if _contains_any(text, family["triggers"]):
            for tool_id in family["tools"]:
                if tool_id not in found:
                    found.append(tool_id)
    return found


def _catalog_order(catalog: Catalog) -> list[str]:
    return [tool.id for tool in catalog.tools]


def _order(tool_ids: list[str], per_tool: dict, catalog: Catalog) -> list[str]:
    catalog_index = {tool_id: index for index, tool_id in enumerate(_catalog_order(catalog))}

    def sort_key(tool_id: str) -> tuple:
        hits = per_tool[tool_id]
        return (
            0 if hits["name"] else 1,
            0 if hits["purpose"] else 1,
            catalog_index[tool_id],
        )

    return sorted(tool_ids, key=sort_key)


def _question(tool_ids: list[str], catalog: Catalog) -> list[str]:
    names = "、".join(catalog.by_id()[tool_id].name for tool_id in tool_ids)
    return [f"次のどれが目的に近いですか。{names}"]


def _finish(
    *,
    candidate_ids: list[str],
    abstained: bool,
    needs_clarification: bool,
    questions: list[str],
    reasons: list[str],
    trace: list[str],
) -> dict:
    output = empty_output(case_id="", condition_id="B1", method="B", model_id=None)
    output.update(
        {
            "candidate_ids": candidate_ids,
            "ranks": with_ranks(candidate_ids),
            "scores": None,
            "needs_clarification": needs_clarification,
            "clarification_questions": questions,
            "abstained": abstained,
            "reasons": reasons,
            "rule_trace": trace,
        }
    )
    return output
