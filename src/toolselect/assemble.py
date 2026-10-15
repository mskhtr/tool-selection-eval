from __future__ import annotations

import json
from pathlib import Path

from toolselect.catalog import load_catalog
from toolselect.dataset import labeling_note, load_cases, write_cases_file
from toolselect.experiment import (
    evaluate,
    load_models,
    load_replay_responses,
    manifest,
    new_run_dir,
    primary_counts,
    run_b,
    run_d,
    run_replay,
    stability,
    write_condition,
)
from toolselect.paths import ROOT
from toolselect.readable import render_case_comparison
from toolselect.report import condition_label, render_report


RESPONSE_ROOT = ROOT / "runs" / "llm_responses"
CHUNKS = ("chunk_000.json", "chunk_025.json", "chunk_050.json", "chunk_075.json", "chunk_100.json", "chunk_125.json")


def merge_model_method(model: str, method: str) -> dict[str, str]:
    merged: dict[str, str] = {}
    for name in CHUNKS:
        path = RESPONSE_ROOT / model / method / name
        merged.update(load_replay_responses(path))
    return merged


def write_merged(model: str, method: str, responses: dict[str, str]) -> Path:
    path = RESPONSE_ROOT / model / method / "merged.json"
    payload = {
        "responses": [
            {"case_id": case_id, "body": json.loads(body)}
            for case_id, body in sorted(responses.items())
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _tool_names(ids: list[str] | None, names: dict[str, str]) -> str:
    if not ids:
        return "なし"
    return "、".join(names.get(tool_id, tool_id) for tool_id in ids)


def _examples(cases: list[dict], details: list[dict], tag: str, limit: int = 3) -> list[dict]:
    by_id = {case["id"]: case for case in cases}
    found = []
    for row in details:
        if tag not in row["tags"]:
            continue
        case = by_id[row["case_id"]]
        prediction = row["prediction"]
        found.append(
            {
                "case_id": case["id"],
                "text": case["text"],
                "acceptable": case["acceptable"],
                "predicted": prediction.get("candidate_ids"),
                "clarification": prediction.get("needs_clarification"),
                "assumptions": prediction.get("unstated_assumptions"),
                "reasons": prediction.get("reasons"),
            }
        )
        if len(found) >= limit:
            break
    return found


def assemble(stability_runs: dict | None = None) -> Path:
    write_cases_file()
    cases = load_cases()
    models = load_models()
    run_dir = new_run_dir()
    rows = []
    example_block: dict[str, dict] = {}
    b_outputs = run_b(cases)
    predictions = {"B1": {row["case_id"]: row for row in b_outputs}}
    b_eval = evaluate(cases, b_outputs)
    write_condition(run_dir, "B1", b_outputs, None, b_eval)
    saved = {"B1": b_eval}
    for condition in models["conditions"]:
        if condition["method"] == "B":
            rows.append(
                {
                    "id": "B1",
                    "method": "B",
                    "model": None,
                    "status": "実行済み",
                    "summary": b_eval["summary"],
                    "n_responses": len(cases),
                }
            )
            example_block["B1"] = {
                "過剰な意図補完": _examples(cases, b_eval["details"], "過剰な意図補完"),
                "表層キーワード誤選択": _examples(cases, b_eval["details"], "表層キーワード誤選択"),
                "候補漏れ": _examples(cases, b_eval["details"], "候補漏れ"),
            }
            continue
        if condition["method"] == "D" and not condition.get("model"):
            outputs = run_d(cases)
            predictions["D1"] = {row["case_id"]: row for row in outputs}
            evaluation = evaluate(cases, outputs)
            write_condition(run_dir, "D1", outputs, None, evaluation)
            rows.append(
                {
                    "id": "D1",
                    "method": "D",
                    "model": None,
                    "status": "実行済み",
                    "summary": evaluation["summary"],
                    "n_responses": len(cases),
                }
            )
            example_block["D1"] = {
                "過剰な意図補完": _examples(cases, evaluation["details"], "過剰な意図補完"),
                "表層キーワード誤選択": _examples(cases, evaluation["details"], "表層キーワード誤選択"),
                "候補漏れ": _examples(cases, evaluation["details"], "候補漏れ"),
            }
            saved["D1"] = evaluation
            continue
        responses = merge_model_method(condition["model"], condition["method"])
        present = [case for case in cases if case["id"] in responses]
        merged_path = write_merged(condition["model"], condition["method"], responses)
        outputs, raw_rows = run_replay(condition, merged_path, present)
        predictions[condition["id"]] = {row["case_id"]: row for row in outputs}
        evaluation = evaluate(present, outputs) if present else {"summary": None, "details": []}
        write_condition(run_dir, condition["id"], outputs, raw_rows, evaluation)
        missing = len(cases) - len(present)
        if missing == 0:
            status = "実行済み"
        elif present:
            status = f"一部実行 {len(present)}/{len(cases)}"
        else:
            status = "未実行"
        rows.append(
            {
                "id": condition["id"],
                "method": condition["method"],
                "model": condition["model"],
                "status": status,
                "summary": evaluation["summary"],
                "n_responses": len(present),
                "n_missing": missing,
            }
        )
        if present:
            example_block[condition["id"]] = {
                "過剰な意図補完": _examples(cases, evaluation["details"], "過剰な意図補完"),
                "表層キーワード誤選択": _examples(cases, evaluation["details"], "表層キーワード誤選択"),
                "候補漏れ": _examples(cases, evaluation["details"], "候補漏れ"),
            }
        saved[condition["id"]] = evaluation
    payload = manifest(
        {
            "n_cases": len(cases),
            "primary_counts": primary_counts(cases),
            "labeling": labeling_note(),
            "timing": {
                "per_case_latency_s": None,
                "token_usage": None,
                "api_cost": None,
                "note": "トークン数・料金・モデル単体の遅延は未取得。",
            },
            "limitations": [
                "温度は指定できない。推論設定はモデルIDに含まれる medium のみ。",
                "料金とトークン数は未取得。",
                "正解ラベルは実装者1名で、複数人の独立ラベルではない。",
                "オントロジーの関係は、正解ラベルを書いた実装者1名が、辞書の外れ方を見てから書いた。モデル出力を見て関係を直してはいない。",
                "誤り分類は規則による自動分類で、人手の再判定ではない。",
                "ユーザー確認後の選択は方式の精度に含めていない。",
                "同一入力の繰り返し実行は未実施。",
            ],
            "stability": stability_runs,
            "examples": example_block,
        }
    )
    (run_dir / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "comparison.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    names = {tool.id: tool.name for tool in load_catalog().tools}
    report = render_report(run_dir)
    report += "\n## 事例\n\n"
    report += "見出しは条件番号、方式、モデルである。選ぶべきツールは、その依頼で出すのが正解のツールである。予測はその条件が出した候補である。\n\n"
    labels = {row["id"]: condition_label(row) for row in rows}
    for condition_id, groups in example_block.items():
        report += f"### {labels.get(condition_id, condition_id)}\n\n"
        for tag, items in groups.items():
            report += f"#### {tag}\n\n"
            if not items:
                report += "該当なし。\n\n"
                continue
            for item in items:
                asked = "質問あり" if item["clarification"] else "質問なし"
                report += (
                    f"- {item['case_id']}「{item['text']}」 "
                    f"選ぶべきツール: {_tool_names(item['acceptable'], names)}。"
                    f"予測: {_tool_names(item['predicted'], names)}。"
                    f"{asked}\n"
                )
            report += "\n"
    example_ids = sorted(
        {
            item["case_id"]
            for groups in example_block.values()
            for items in groups.values()
            for item in items
        }
    )
    if example_ids:
        report += "\n" + render_case_comparison(cases, predictions, names, example_ids)
    report_path = run_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")
    latest = ROOT / "reports"
    latest.mkdir(exist_ok=True)
    (latest / "latest.md").write_text(report, encoding="utf-8")
    print(run_dir)
    return run_dir


if __name__ == "__main__":
    assemble()
