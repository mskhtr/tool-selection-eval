from __future__ import annotations

import json

from toolselect.dataset import labeling_note, load_cases, write_cases_file
from toolselect.experiment import evaluate, manifest, new_run_dir, primary_counts, run_b, write_condition
from toolselect.report import render_report


def main() -> None:
    cases = load_cases()
    write_cases_file()
    run_dir = new_run_dir()
    outputs = run_b(cases)
    evaluation = evaluate(cases, outputs)
    write_condition(run_dir, "B1", outputs, None, evaluation)
    rows = [
        {
            "id": "A1",
            "method": "A",
            "model": "sol",
            "status": "未実行",
            "summary": None,
        },
        {
            "id": "A2",
            "method": "A",
            "model": "terra",
            "status": "未実行",
            "summary": None,
        },
        {
            "id": "A3",
            "method": "A",
            "model": "luna",
            "status": "未実行",
            "summary": None,
        },
        {
            "id": "B1",
            "method": "B",
            "model": None,
            "status": "実行済み",
            "summary": evaluation["summary"],
        },
        {
            "id": "C1",
            "method": "C",
            "model": "sol",
            "status": "未実行",
            "summary": None,
        },
        {
            "id": "C2",
            "method": "C",
            "model": "terra",
            "status": "未実行",
            "summary": None,
        },
        {
            "id": "C3",
            "method": "C",
            "model": "luna",
            "status": "未実行",
            "summary": None,
        },
    ]
    payload = manifest(
        {
            "n_cases": len(cases),
            "primary_counts": primary_counts(cases),
            "labeling": labeling_note(),
            "timing": {"B1_latency_s": None, "note": "B方式はローカル規則で、API遅延は無い。ケース単位の計測は未取得。"},
            "limitations": [
                "AとCは、Sol / Terra / Luna の応答ファイルを入れるまで未実行。",
                "正解ラベルは実装者1名。複数人の独立ラベルではない。",
                "誤り分類は規則であり、人手の再判定ではない。",
                "料金とトークン数は未取得。",
            ],
            "stability": None,
        }
    )
    (run_dir / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "comparison.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    report = render_report(run_dir)
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    print(run_dir)
    print(json.dumps(evaluation["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
