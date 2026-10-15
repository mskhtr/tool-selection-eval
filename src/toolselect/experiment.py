from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

from toolselect.catalog import load_catalog
from toolselect.dataset import artifact_hashes, load_cases
from toolselect.errors import classify_errors, count_tags
from toolselect.graphs import build_method_a_graph, build_method_b_graph, build_method_c_graph, build_method_d_graph, build_method_d_llm_graph
from toolselect.llm import ReplayLLM
from toolselect.method_b import load_b_rules
from toolselect.method_c import load_c_rules
from toolselect.method_d import load_ontology
from toolselect.metrics import score_case, summarize
from toolselect.paths import MODELS_PATH, PROMPT_A_PATH, PROMPT_C_PATH, PROMPT_D_PATH, ROOT
from toolselect.report import render_report


def load_models() -> dict:
    return yaml.safe_load(MODELS_PATH.read_text(encoding="utf-8"))


def prompt_user(catalog_text: str, user_text: str) -> str:
    return f"ツールカタログ:\n{catalog_text}\n\nユーザー入力:\n{user_text}\n"


def export_requests(out_dir: Path, chunk_size: int = 25) -> list[Path]:
    catalog = load_catalog()
    cases = load_cases()
    prompts = {
        "A": PROMPT_A_PATH.read_text(encoding="utf-8"),
        "C": PROMPT_C_PATH.read_text(encoding="utf-8"),
        "D": PROMPT_D_PATH.read_text(encoding="utf-8"),
    }
    written: list[Path] = []
    for method in ("A", "C", "D"):
        for start in range(0, len(cases), chunk_size):
            chunk = cases[start : start + chunk_size]
            payload = {
                "method": method,
                "system": prompts[method],
                "cases": [{"id": case["id"], "text": case["text"]} for case in chunk],
            }
            if method != "D":
                payload["catalog"] = catalog.llm_text()
            path = out_dir / method / f"chunk_{start:03d}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            written.append(path)
    return written


def load_replay_responses(path: Path) -> dict[str, str]:
    """case_id -> モデルが返したJSON文字列。ファイルが無ければ空。壊れたJSONは空。"""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    data = _load_response_json(text)
    if data is None:
        return {}
    responses = {}
    for row in data.get("responses") or []:
        case_id = str(row.get("case_id") or "")
        if not case_id.isdigit():
            continue
        body = row.get("body")
        if isinstance(body, str):
            responses[case_id] = body
        else:
            responses[case_id] = json.dumps(body, ensure_ascii=False)
    return responses


def _load_response_json(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        repaired = text.replace('}}},{"case_id"', '}},{"case_id"')
        try:
            data = json.loads(repaired)
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


def _invoke(graph, case: dict, condition_id: str) -> tuple[dict, str | None]:
    state = graph.invoke(
        {
            "case_id": case["id"],
            "condition_id": condition_id,
            "user_text": case["text"],
        }
    )
    return state.get("output") or {}, state.get("raw_response")


def run_d(cases: list[dict] | None = None) -> list[dict]:
    catalog = load_catalog()
    graph = build_method_d_graph(catalog, load_ontology())
    rows = []
    for case in cases or load_cases():
        output, _raw = _invoke(graph, case, "D1")
        rows.append(output)
    return rows


def run_b(cases: list[dict] | None = None) -> list[dict]:
    catalog = load_catalog()
    graph = build_method_b_graph(catalog, load_b_rules())
    rows = []
    for case in cases or load_cases():
        output, _raw = _invoke(graph, case, "B1")
        rows.append(output)
    return rows


def run_replay(condition: dict, response_path: Path, cases: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    catalog = load_catalog()
    cases = cases or load_cases()
    model_key = condition.get("model")
    models = load_models()["models"]
    model_id = models[model_key]["api_model_id"] if model_key else None
    responses = load_replay_responses(response_path)
    llm = ReplayLLM(model_id or "missing", responses)
    if condition["method"] == "A":
        graph = build_method_a_graph(catalog, llm, PROMPT_A_PATH.read_text(encoding="utf-8"))
    elif condition["method"] == "C":
        graph = build_method_c_graph(catalog, llm, PROMPT_C_PATH.read_text(encoding="utf-8"), load_c_rules())
    elif condition["method"] == "D":
        graph = build_method_d_llm_graph(catalog, llm, PROMPT_D_PATH.read_text(encoding="utf-8"), load_ontology())
    else:
        raise ValueError(condition["method"])
    outputs = []
    raw_rows = []
    for case in cases:
        output, raw = _invoke(graph, case, condition["id"])
        outputs.append(output)
        raw_rows.append({"case_id": case["id"], "raw_response": raw, "error": output.get("error")})
    return outputs, raw_rows


def evaluate(cases: list[dict], outputs: list[dict]) -> dict:
    by_id = {row["case_id"]: row for row in outputs}
    scores = []
    error_rows = []
    details = []
    for case in cases:
        prediction = by_id[case["id"]]
        score = score_case(case, prediction)
        tags = classify_errors(case, prediction)
        scores.append(score)
        error_rows.append(tags)
        details.append({"case_id": case["id"], "tags": tags, "score": score, "prediction": prediction})
    summary = summarize(scores, cases)
    summary["error_tags"] = count_tags(error_rows)
    summary["classifier"] = "rules_v1_automatic"
    return {"summary": summary, "details": details}


def stability(runs: list[list[dict]]) -> dict:
    """同一ケースの複数回について、候補集合のジャッカードと質問有無の一致を見る。"""
    by_run = []
    for rows in runs:
        by_run.append({row["case_id"]: row for row in rows})
    case_ids = sorted(set.intersection(*(set(mapping) for mapping in by_run))) if by_run else []
    per_case = []
    for case_id in case_ids:
        sets = [set(mapping[case_id].get("candidate_ids") or []) for mapping in by_run]
        flags = [bool(mapping[case_id].get("needs_clarification")) for mapping in by_run]
        pair_scores = []
        for left in range(len(sets)):
            for right in range(left + 1, len(sets)):
                union = sets[left] | sets[right]
                pair_scores.append(1.0 if not union else len(sets[left] & sets[right]) / len(union))
        per_case.append(
            {
                "case_id": case_id,
                "mean_jaccard": sum(pair_scores) / len(pair_scores) if pair_scores else None,
                "clarification_agreement": len(set(flags)) == 1,
                "candidate_sets": [sorted(items) for items in sets],
            }
        )
    jaccards = [row["mean_jaccard"] for row in per_case if row["mean_jaccard"] is not None]
    agreements = [row["clarification_agreement"] for row in per_case]
    return {
        "n_cases": len(per_case),
        "n_runs": len(runs),
        "mean_jaccard": sum(jaccards) / len(jaccards) if jaccards else None,
        "clarification_agreement_rate": sum(1 for flag in agreements if flag) / len(agreements) if agreements else None,
        "cases": per_case,
    }


def write_condition(run_dir: Path, condition_id: str, outputs: list[dict], raw_rows: list[dict] | None, evaluation: dict) -> None:
    folder = run_dir / condition_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "predictions.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in outputs) + "\n",
        encoding="utf-8",
    )
    if raw_rows is not None:
        (folder / "raw.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in raw_rows) + "\n",
            encoding="utf-8",
        )
    (folder / "evaluation.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")


def new_run_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = ROOT / "runs" / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def manifest(extra: dict | None = None) -> dict:
    models = load_models()
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hashes": artifact_hashes(),
        "models": models,
        "catalog_views": load_catalog().view_diff(),
        "note": "B方式はLLMを使わない。AとCの実測は、応答ファイルがある条件だけ実行済みとする。",
    }
    if extra:
        payload.update(extra)
    return payload


def primary_counts(cases: list[dict]) -> dict[str, int]:
    return dict(Counter(case["primary"] for case in cases))


def render_saved_report(run_dir: Path) -> str:
    return render_report(run_dir)
