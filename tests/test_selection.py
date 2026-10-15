from __future__ import annotations

import json

from langgraph.types import Command

from toolselect.analysis import AnalysisNotApproved, execute_analysis
from toolselect.catalog import load_catalog
from toolselect.dataset import load_cases
from toolselect.errors import classify_errors
from toolselect.gold import CASES
from toolselect.graphs import build_confirm_graph, build_method_a_graph, build_method_b_graph, build_method_c_graph
from toolselect.llm import FakeLLM, LLMResult
from toolselect.method_b import load_b_rules, select_with_rules
from toolselect.method_c import decide_from_scores, resolve_score_rows
from toolselect.method_d import load_ontology, parse_concept_response, select_with_ontology
from toolselect.metrics import score_case
from toolselect.paths import ROOT


REQUIRED_TEXTS = [
    "はんだのシミュレーションをしたい",
    "半田のシミュレーションをしたい",
    "寿命を見たい",
    "いつものをお願い",
    "鋼製アームに繰り返し曲げがかかるので、S-N曲線で疲労寿命を計算したい",
]

CATEGORIES = {
    "clear",
    "orthography",
    "ambiguous",
    "colloquial",
    "multi",
    "insufficient",
    "out_of_scope",
    "implicit",
    "keyword_trap",
}


def test_cases_cover_categories_and_spec_examples():
    assert len(CASES) == 36
    assert len({case["id"] for case in CASES}) == 36
    assert len(load_catalog().tools) == 3
    texts = {case["text"] for case in CASES}
    for text in REQUIRED_TEXTS:
        assert text in texts
    found = {tag for case in CASES for tag in case["categories"]}
    assert CATEGORIES <= found
    groups = {}
    for case in CASES:
        groups.setdefault(case["group"], []).append(case["id"])
    for group in ("solder_sim", "solder_script", "vague", "fatigue_clear"):
        assert len(groups[group]) >= 2
    catalog_ids = load_catalog().ids()
    for case in CASES:
        assert set(case["acceptable"]) <= catalog_ids
        assert set(case["required"]) <= set(case["acceptable"]) or not case["required"]
        assert set(case["required"]) <= catalog_ids


def test_llm_view_hides_rule_only_fields():
    catalog = load_catalog()
    text = catalog.llm_text()
    assert "rule_keywords" not in text
    assert "structural_failure" not in text
    diff = catalog.view_diff()
    assert "rule_keywords" in diff["rule_only_fields"]
    assert "purpose_signals" in diff["llm_fields"]


def test_method_b_on_instruction_examples():
    catalog = load_catalog()
    rules = load_b_rules()
    cases = {case["text"]: case for case in load_cases()}

    solder = select_with_rules(cases["はんだのシミュレーションをしたい"]["text"], catalog, rules)
    assert solder["scores"] is None
    assert set(solder["candidate_ids"]) == {"solder_crack_propagation", "solder_life_prediction"}
    assert solder["needs_clarification"] is True
    assert solder["abstained"] is False

    life = select_with_rules("寿命を見たい", catalog, rules)
    assert set(life["candidate_ids"]) == {"solder_life_prediction", "fatigue_life"}
    assert life["needs_clarification"] is True

    script = select_with_rules("半田のシミュレーションをしたい", catalog, rules)
    assert set(script["candidate_ids"]) == set(solder["candidate_ids"])
    assert script["needs_clarification"] is True

    katakana = select_with_rules("ハンダの亀裂進展を計算したい", catalog, rules)
    assert katakana["candidate_ids"] == ["solder_crack_propagation"]
    assert katakana["needs_clarification"] is False

    vague = select_with_rules("いつものをお願い", catalog, rules)
    assert vague["candidate_ids"] == []
    assert vague["abstained"] is True
    assert vague["needs_clarification"] is True

    clear = select_with_rules(cases[REQUIRED_TEXTS[-1]]["text"], catalog, rules)
    assert clear["candidate_ids"] == ["fatigue_life"]
    assert clear["needs_clarification"] is False

    both = select_with_rules("はんだの寿命予測と亀裂進展シミュレーションを両方やって", catalog, rules)
    assert set(both["candidate_ids"]) == {"solder_crack_propagation", "solder_life_prediction"}
    assert both["needs_clarification"] is False

    definition = select_with_rules("固有値という言葉の意味を教えて", catalog, rules)
    assert definition["candidate_ids"] == []
    assert definition["abstained"] is True

    trap = select_with_rules("ランダムに選んだ振動の話題で報告書の目次を作りたい", catalog, rules)
    assert trap["candidate_ids"] == []
    assert trap["abstained"] is True


def test_method_b_graph_runs():
    catalog = load_catalog()
    graph = build_method_b_graph(catalog, load_b_rules())
    state = graph.invoke({"case_id": "017", "condition_id": "B1", "user_text": "はんだのシミュレーションをしたい"})
    assert state["output"]["case_id"] == "017"
    assert state["output"]["scores"] is None


def test_method_c_splits_scoring_and_dictionary():
    catalog = load_catalog()
    resolved = resolve_score_rows(
        {
            "missing_information": True,
            "missing_items": ["目的"],
            "scores": [
                {"tool_id": "疲労寿命予測", "score": 80, "reason": "名称"},
                {"tool_id": "not_a_tool", "score": 90, "reason": "幻覚"},
                {"tool_id": "solder_life_prediction", "score": 70, "reason": "id"},
            ],
        },
        catalog,
    )
    assert resolved["invalid_ids"] == ["not_a_tool"]
    assert {row["tool_id"] for row in resolved["rows"]} == {"fatigue_life", "solder_life_prediction"}
    decided = decide_from_scores(resolved)
    assert decided["scores"]["fatigue_life"] == 80
    assert "not_a_tool" not in decided["candidate_ids"]
    assert decided["invalid_ids"] == ["not_a_tool"]
    assert decided["needs_clarification"] is True


def test_method_c_graph_with_fake_llm():
    catalog = load_catalog()
    body = {
        "missing_information": False,
        "missing_items": [],
        "scores": [
            {"tool_id": tool_id, "score": 90 if tool_id == "fatigue_life" else 10, "reason": "test"}
            for tool_id in catalog.ids()
        ],
    }

    def handler(**_kwargs):
        return LLMResult(text=json.dumps(body, ensure_ascii=False), model_id="fake")

    graph = build_method_c_graph(catalog, FakeLLM("fake", handler), "system", {"min_include_score": 50, "high_confidence": 75, "near_tie_window": 15, "max_candidates": 5})
    state = graph.invoke({"case_id": "021", "condition_id": "C1", "user_text": "固有値"})
    assert state["output"]["candidate_ids"] == ["fatigue_life"]
    assert state["output"]["needs_clarification"] is False
    assert state["raw_response"]


def test_method_a_graph_normalizes_output():
    def handler(**_kwargs):
        return LLMResult(
            text='```json\n{"candidate_ids":["fatigue_life"],"needs_clarification":false,"clarification_questions":[],"abstained":false,"reasons":["明示"],"unstated_assumptions":[]}\n```',
            model_id="fake",
            prompt_tokens=None,
            completion_tokens=None,
            cost_usd=None,
        )

    graph = build_method_a_graph(load_catalog(), FakeLLM("fake", handler), "system")
    state = graph.invoke({"case_id": "005", "condition_id": "A1", "user_text": "疲労寿命"})
    output = state["output"]
    assert output["candidate_ids"] == ["fatigue_life"]
    assert output["ranks"] == {"fatigue_life": 1}
    assert output["scores"] is None
    assert output["cost_usd"] is None


def test_metrics_and_error_tags_do_not_use_confirmation():
    case = {
        "id": "009",
        "acceptable": ["solder_crack_propagation", "solder_life_prediction", "fatigue_life"],
        "required": ["solder_crack_propagation", "solder_life_prediction", "fatigue_life"],
        "multiple": True,
        "clarify": True,
        "applicable": "yes",
        "categories": ["ambiguous"],
    }
    prediction = {
        "candidate_ids": ["fatigue_life"],
        "needs_clarification": False,
        "clarification_questions": [],
        "abstained": False,
        "invalid_ids": [],
        "unstated_assumptions": ["静荷重と仮定した"],
    }
    score = score_case(case, prediction)
    assert score["forced_one"] is True
    assert score["exact"] is False
    tags = classify_errors(case, prediction)
    assert "過剰な意図補完" in tags
    assert "候補漏れ" in tags
    assert "質問不足" in tags


def test_confirmation_does_not_execute_analysis():
    graph = build_confirm_graph()
    config = {"configurable": {"thread_id": "case-001"}}
    paused = graph.invoke(
        {"case_id": "001", "proposed_ids": ["solder_crack_propagation", "solder_life_prediction"], "questions": ["どちらですか"]},
        config,
    )
    assert paused["pre_confirm_ids"] == ["solder_crack_propagation", "solder_life_prediction"]
    assert paused["analysis_executed"] is False
    assert "__interrupt__" in paused
    resumed = graph.invoke(Command(resume={"selected_ids": ["solder_life_prediction"], "approved": True}), config)
    assert resumed["pre_confirm_ids"] == ["solder_crack_propagation", "solder_life_prediction"]
    assert resumed["final_ids"] == ["solder_life_prediction"]
    assert resumed["analysis_executed"] is False
    try:
        execute_analysis(["solder_life_prediction"], approved=False)
        raise AssertionError("承認前に実行口が通った")
    except AnalysisNotApproved:
        pass
    planned = execute_analysis(["solder_life_prediction"], approved=True)
    assert planned["executed"] is False
    source = (ROOT / "src" / "toolselect" / "graphs.py").read_text(encoding="utf-8")
    assert "execute_analysis" not in source


def test_ontology_uses_relations_and_does_not_commit_suggestions():
    catalog = load_catalog()
    ontology = load_ontology()
    crack = select_with_ontology("半田のき裂がどこまで進むかシミュレーションしたい", catalog, ontology)
    assert crack["candidate_ids"] == ["solder_crack_propagation"]
    assert crack["needs_clarification"] is False
    life = select_with_ontology("はんだ接合の熱疲労寿命を計算したい", catalog, ontology)
    assert life["candidate_ids"] == ["solder_life_prediction"]
    assert life["needs_clarification"] is False
    vague = select_with_ontology("はんだのシミュレーションをしたい", catalog, ontology)
    assert set(vague["candidate_ids"]) == {"solder_crack_propagation", "solder_life_prediction"}
    assert vague["needs_clarification"] is True
    hint = select_with_ontology("はんだが割れそうなので見たい", catalog, ontology)
    assert set(hint["candidate_ids"]) == {"solder_crack_propagation", "solder_life_prediction"}
    assert hint["needs_clarification"] is True
    both = parse_concept_response(
        '{"concepts":["solder","life"],"suggestions":[]}',
        "はんだの寿命を計算して",
        catalog,
        ontology,
    )
    assert both["candidate_ids"] == ["solder_life_prediction"]
    assert "llm_concepts" in both["rule_trace"]
