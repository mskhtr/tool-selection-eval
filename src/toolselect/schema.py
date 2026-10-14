from __future__ import annotations

from typing import Any


def empty_output(
    *,
    case_id: str,
    condition_id: str,
    method: str,
    model_id: str | None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "condition_id": condition_id,
        "method": method,
        "model_id": model_id,
        "candidate_ids": [],
        "ranks": {},
        "scores": None,
        "needs_clarification": False,
        "clarification_questions": [],
        "abstained": False,
        "reasons": [],
        "unstated_assumptions": [],
        "invalid_ids": [],
        "unresolved_mentions": [],
        "latency_s": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "cost_usd": None,
        "error": None,
        "rule_trace": [],
    }


def with_ranks(candidate_ids: list[str]) -> dict[str, int]:
    return {tool_id: index + 1 for index, tool_id in enumerate(candidate_ids)}
