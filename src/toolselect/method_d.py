from __future__ import annotations

from functools import cache

import yaml

from toolselect.catalog import Catalog
from toolselect.method_b import load_b_rules
from toolselect.paths import ONTOLOGY_PATH
from toolselect.schema import empty_output, with_ranks
from toolselect.textutil import normalize_text, parse_json_payload


@cache
def load_ontology(path: str | None = None) -> dict:
    if path is None:
        text = ONTOLOGY_PATH.read_text(encoding="utf-8")
    else:
        from pathlib import Path

        text = Path(path).read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _occurrences(text: str, labels: list[str]) -> list[tuple[int, int]]:
    found = []
    for label in labels:
        folded = normalize_text(label)
        if not folded:
            continue
        start = 0
        while True:
            index = text.find(folded, start)
            if index < 0:
                break
            found.append((index, index + len(folded)))
            start = index + 1
    return found


def match_concepts(user_text: str, ontology: dict | None = None) -> dict[str, list[str]]:
    """長いラベルを優先して概念を立てる。短い語が長い語の一部なら立てない。"""
    ontology = ontology or load_ontology()
    text = normalize_text(user_text)
    hits: list[tuple[int, int, str, str]] = []
    for concept, spec in (ontology.get("concepts") or {}).items():
        for start, end in _occurrences(text, spec.get("labels") or []):
            hits.append((start, end, concept, "concept"))
    hits.sort(key=lambda item: (-(item[1] - item[0]), item[0], item[2]))
    occupied: list[tuple[int, int]] = []
    concepts: list[str] = []
    for start, end, concept, _kind in hits:
        if any(not (end <= left or start >= right) for left, right in occupied):
            continue
        occupied.append((start, end))
        if concept not in concepts:
            concepts.append(concept)
    suggestions: list[str] = []
    for concept, labels in (ontology.get("suggestions") or {}).items():
        for start, end in _occurrences(text, labels):
            if any(not (end <= left or start >= right) for left, right in occupied):
                continue
            if concept not in suggestions:
                suggestions.append(concept)
    return {"concepts": concepts, "suggestions": suggestions}


def _tools_for(concepts: set[str], ontology: dict) -> list[str]:
    matched = []
    for tool_id, groups in (ontology.get("tool_requirements") or {}).items():
        if any(set(group) <= concepts for group in groups):
            matched.append(tool_id)
    return matched


def _contains_any(text: str, needles: list[str]) -> list[str]:
    return [needle for needle in needles if needle and normalize_text(needle) in text]


def decide_from_concepts(
    user_text: str,
    concepts: list[str],
    suggestions: list[str],
    catalog: Catalog,
    ontology: dict | None = None,
    *,
    trace_prefix: list[str] | None = None,
) -> dict:
    """概念の関係で候補を決める。示唆だけでは目的を一つにしない。"""
    ontology = ontology or load_ontology()
    rules = load_b_rules()
    text = normalize_text(user_text)
    known = set(ontology.get("concepts") or {})
    trace = list(trace_prefix or [])
    invalid = [item for item in concepts if item not in known]
    concepts_set = [item for item in concepts if item in known]
    suggestions_set = [item for item in suggestions if item in known and item not in concepts_set]
    trace.append("concepts:" + ",".join(concepts_set or ["none"]))
    if suggestions_set:
        trace.append("suggestions:" + ",".join(suggestions_set))
    output = empty_output(case_id="", condition_id="", method="D", model_id=None)
    output["invalid_ids"] = invalid
    output["rule_trace"] = trace

    meta_hits = _contains_any(text, rules["hard_meta_substrings"])
    if meta_hits:
        trace.append("meta_veto:" + ",".join(meta_hits))
        return _finish(output, [], True, True, ["これは解析ツールの実行依頼ですか。実行するなら、対象と知りたいことを指定してください。"], ["説明・事務・検索の表現が含まれるため、ツールを選ばず保留した。"])

    if not _contains_any(text, rules["request_substrings"]):
        trace.append("no_request_verb")
        return _finish(output, [], True, True, ["解析として何を計算したいかを教えてください。"], ["解析の実行を頼む表現が無いため保留した。"])

    active = set(concepts_set)
    matched = _tools_for(active, ontology)
    if not matched:
        subject_only = ontology.get("subject_only") or {}
        for subject, tools in subject_only.items():
            others = active - {subject}
            if subject in active and not others:
                matched = list(tools)
                trace.append(f"subject_only:{subject}")
                break
    if not matched:
        trace.append("no_match")
        return _finish(
            output,
            [],
            True,
            True,
            ["どの解析を実行したいか、対象と知りたいことを教えてください。"],
            ["オントロジーの概念がツールの関係まで届かなかった。"],
        )

    order = [tool.id for tool in catalog.tools if tool.id in matched]
    combination = _contains_any(text, rules["combination_substrings"])
    needs_question = len(order) > 1 and not combination
    if combination and len(order) > 1:
        trace.append("explicit_combination")
    trace.append("tools:" + ",".join(order))
    reasons = ["概念の関係に合うツールを候補にした。"]
    if needs_question:
        reasons.append("候補が複数あり、入力だけでは一つに決められない。")
    names = "、".join(catalog.by_id()[tool_id].name for tool_id in order)
    questions = [f"次のどれが目的に近いですか。{names}"] if needs_question else []
    return _finish(output, order, False, needs_question, questions, reasons)


def select_with_ontology(user_text: str, catalog: Catalog, ontology: dict | None = None) -> dict:
    ontology = ontology or load_ontology()
    matched = match_concepts(user_text, ontology)
    return decide_from_concepts(
        user_text,
        matched["concepts"],
        matched["suggestions"],
        catalog,
        ontology,
        trace_prefix=["normalize_nfkc", "label_match"],
    )


def parse_concept_response(raw: str, user_text: str, catalog: Catalog, ontology: dict | None = None) -> dict:
    ontology = ontology or load_ontology()
    try:
        payload = parse_json_payload(raw)
    except (ValueError, TypeError) as error:
        output = empty_output(case_id="", condition_id="", method="D", model_id=None)
        output["error"] = f"parse_error: {error}"
        output["abstained"] = True
        output["needs_clarification"] = True
        output["rule_trace"] = ["parse_error"]
        return output
    if not isinstance(payload, dict):
        output = empty_output(case_id="", condition_id="", method="D", model_id=None)
        output["error"] = "parse_error: object expected"
        output["abstained"] = True
        output["needs_clarification"] = True
        output["rule_trace"] = ["parse_error"]
        return output
    concepts = [str(item) for item in payload.get("concepts") or []]
    suggestions = [str(item) for item in payload.get("suggestions") or []]
    return decide_from_concepts(
        user_text,
        concepts,
        suggestions,
        catalog,
        ontology,
        trace_prefix=["llm_concepts"],
    )


def _finish(output: dict, candidate_ids: list[str], abstained: bool, needs_clarification: bool, questions: list[str], reasons: list[str]) -> dict:
    output.update(
        {
            "candidate_ids": candidate_ids,
            "ranks": with_ranks(candidate_ids),
            "scores": None,
            "needs_clarification": needs_clarification,
            "clarification_questions": questions,
            "abstained": abstained,
            "reasons": reasons,
        }
    )
    return output
