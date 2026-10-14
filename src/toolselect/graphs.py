from __future__ import annotations

from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from toolselect.catalog import Catalog
from toolselect.llm import LLMClient
from toolselect.method_b import select_with_rules
from toolselect.method_c import parse_score_response
from toolselect.schema import empty_output, with_ranks
from toolselect.textutil import parse_json_payload


class SelectState(TypedDict, total=False):
    case_id: str
    condition_id: str
    user_text: str
    system_prompt: str
    user_prompt: str
    raw_response: str
    llm_error: str
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: float | None
    latency_s: float | None
    output: dict[str, Any]


def _user_prompt(catalog_text: str, user_text: str) -> str:
    return f"ツールカタログ:\n{catalog_text}\n\nユーザー入力:\n{user_text}\n"


def build_method_a_graph(catalog: Catalog, llm: LLMClient, system_prompt: str):
    catalog_text = catalog.llm_text()

    def prepare(state: SelectState) -> dict:
        return {
            "system_prompt": system_prompt,
            "user_prompt": _user_prompt(catalog_text, state["user_text"]),
        }

    def call_llm(state: SelectState) -> dict:
        result = llm.complete(
            system=state["system_prompt"],
            user=state["user_prompt"],
            case_id=state["case_id"],
        )
        return {
            "raw_response": result.text,
            "llm_error": result.error,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "cost_usd": result.cost_usd,
            "latency_s": result.latency_s,
        }

    def parse(state: SelectState) -> dict:
        output = empty_output(
            case_id=state["case_id"],
            condition_id=state["condition_id"],
            method="A",
            model_id=llm.model_id,
        )
        output["latency_s"] = state.get("latency_s")
        output["prompt_tokens"] = state.get("prompt_tokens")
        output["completion_tokens"] = state.get("completion_tokens")
        output["cost_usd"] = state.get("cost_usd")
        if state.get("llm_error"):
            output["error"] = state["llm_error"]
            output["abstained"] = True
            output["needs_clarification"] = True
            return {"output": output}
        try:
            payload = parse_json_payload(state.get("raw_response") or "")
        except (ValueError, TypeError) as error:
            output["error"] = f"parse_error: {error}"
            output["abstained"] = True
            output["needs_clarification"] = True
            return {"output": output}
        if not isinstance(payload, dict):
            output["error"] = "parse_error: object expected"
            output["abstained"] = True
            return {"output": output}
        known = catalog.ids()
        invalid = []
        candidates = []
        for item in payload.get("candidate_ids") or []:
            mention = str(item).strip()
            if mention in known:
                if mention not in candidates:
                    candidates.append(mention)
                continue
            resolved = catalog.resolve_mention(mention)
            if resolved and resolved not in candidates:
                candidates.append(resolved)
                output["rule_trace"].append(f"resolved_alias:{mention}->{resolved}")
            else:
                invalid.append(mention)
        output.update(
            {
                "candidate_ids": candidates,
                "ranks": with_ranks(candidates),
                "scores": None,
                "needs_clarification": bool(payload.get("needs_clarification")),
                "clarification_questions": [str(q) for q in payload.get("clarification_questions") or []],
                "abstained": bool(payload.get("abstained")) or not candidates,
                "reasons": [str(item) for item in payload.get("reasons") or []],
                "unstated_assumptions": [str(item) for item in payload.get("unstated_assumptions") or []],
                "invalid_ids": invalid,
            }
        )
        if invalid:
            output["rule_trace"].append("catalog_mismatch")
        if output["abstained"] and not output["needs_clarification"]:
            output["needs_clarification"] = True
        return {"output": output}

    graph = StateGraph(SelectState)
    graph.add_node("prepare", prepare)
    graph.add_node("call_llm", call_llm)
    graph.add_node("parse", parse)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "call_llm")
    graph.add_edge("call_llm", "parse")
    graph.add_edge("parse", END)
    return graph.compile()


def build_method_b_graph(catalog: Catalog, rules: dict):
    def match(state: SelectState) -> dict:
        output = select_with_rules(state["user_text"], catalog, rules)
        output["case_id"] = state["case_id"]
        output["condition_id"] = state["condition_id"]
        return {"output": output}

    graph = StateGraph(SelectState)
    graph.add_node("match", match)
    graph.add_edge(START, "match")
    graph.add_edge("match", END)
    return graph.compile()


def build_method_c_graph(catalog: Catalog, llm: LLMClient, system_prompt: str, rules: dict):
    catalog_text = catalog.llm_text()

    def prepare(state: SelectState) -> dict:
        return {
            "system_prompt": system_prompt,
            "user_prompt": _user_prompt(catalog_text, state["user_text"]),
        }

    def call_llm(state: SelectState) -> dict:
        result = llm.complete(
            system=state["system_prompt"],
            user=state["user_prompt"],
            case_id=state["case_id"],
        )
        return {
            "raw_response": result.text,
            "llm_error": result.error,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "cost_usd": result.cost_usd,
            "latency_s": result.latency_s,
        }

    def resolve_and_decide(state: SelectState) -> dict:
        output = empty_output(
            case_id=state["case_id"],
            condition_id=state["condition_id"],
            method="C",
            model_id=llm.model_id,
        )
        output["latency_s"] = state.get("latency_s")
        output["prompt_tokens"] = state.get("prompt_tokens")
        output["completion_tokens"] = state.get("completion_tokens")
        output["cost_usd"] = state.get("cost_usd")
        if state.get("llm_error"):
            output["error"] = state["llm_error"]
            output["abstained"] = True
            output["needs_clarification"] = True
            output["rule_trace"] = ["llm_error"]
            return {"output": output}
        decided = parse_score_response(state.get("raw_response") or "", catalog, rules)
        decided["case_id"] = state["case_id"]
        decided["condition_id"] = state["condition_id"]
        decided["model_id"] = llm.model_id
        decided["latency_s"] = state.get("latency_s")
        decided["prompt_tokens"] = state.get("prompt_tokens")
        decided["completion_tokens"] = state.get("completion_tokens")
        decided["cost_usd"] = state.get("cost_usd")
        return {"output": decided}

    graph = StateGraph(SelectState)
    graph.add_node("prepare", prepare)
    graph.add_node("call_llm", call_llm)
    graph.add_node("resolve_and_decide", resolve_and_decide)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "call_llm")
    graph.add_edge("call_llm", "resolve_and_decide")
    graph.add_edge("resolve_and_decide", END)
    return graph.compile()


class ConfirmState(TypedDict, total=False):
    case_id: str
    proposed_ids: list[str]
    questions: list[str]
    pre_confirm_ids: list[str]
    user_selected_ids: list[str]
    approved: bool
    final_ids: list[str]
    analysis_executed: bool


def build_confirm_graph():
    """候補を見せ、ユーザーが承認するまで解析を実行しない。"""

    def propose(state: ConfirmState) -> dict:
        return {
            "pre_confirm_ids": list(state.get("proposed_ids") or []),
            "analysis_executed": False,
        }

    def wait_for_user(state: ConfirmState) -> dict:
        answer = interrupt(
            {
                "case_id": state.get("case_id"),
                "candidates": state.get("pre_confirm_ids") or [],
                "questions": state.get("questions") or [],
                "message": "候補を確認してください。承認するまで解析ツールは実行しません。",
            }
        )
        selected = [str(item) for item in (answer or {}).get("selected_ids") or []]
        approved = bool((answer or {}).get("approved"))
        return {
            "user_selected_ids": selected,
            "approved": approved,
            "final_ids": selected if approved else [],
            "analysis_executed": False,
        }

    graph = StateGraph(ConfirmState)
    graph.add_node("propose", propose)
    graph.add_node("wait_for_user", wait_for_user)
    graph.add_edge(START, "propose")
    graph.add_edge("propose", "wait_for_user")
    graph.add_edge("wait_for_user", END)
    return graph.compile(checkpointer=MemorySaver())
