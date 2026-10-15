"""正解と、事例の横断比較を、人が読むMarkdownにする。"""

from __future__ import annotations

from pathlib import Path

from toolselect.catalog import load_catalog
from toolselect.dataset import load_cases
from toolselect.errors import classify_errors
from toolselect.paths import ROOT

DOCS = ROOT / "docs"

PRIMARY_ORDER = (
    "clear",
    "orthography",
    "colloquial",
    "multi",
    "ambiguous",
    "implicit",
    "insufficient",
    "keyword_trap",
    "out_of_scope",
)
PRIMARY_LABEL = {
    "clear": "明確（目的が書いてある）",
    "orthography": "表記ゆれ",
    "colloquial": "口語・俗称・略語",
    "multi": "複数ツールを明示",
    "ambiguous": "曖昧（対象だけで目的が未定）",
    "implicit": "暗黙の前提",
    "insufficient": "情報不足",
    "keyword_trap": "表層キーワードの引っかけ",
    "out_of_scope": "カタログ外",
}
APPLICABLE = {"yes": "カタログのツールで扱える", "no": "カタログ外", "unknown": "扱えるか不明"}
SEVERITY = {"low": "低", "medium": "中", "high": "高"}


def _names(ids: list[str], catalog_names: dict[str, str]) -> str:
    if not ids:
        return "なし"
    return "、".join(catalog_names.get(tool_id, tool_id) for tool_id in ids)


def _yes_no(flag: bool) -> str:
    return "する" if flag else "しない"


def render_testset() -> str:
    catalog_names = {tool.id: tool.name for tool in load_catalog().tools}
    cases = load_cases()
    lines = [
        "# テストセット",
        "",
        f"比較に使う{len(cases)}件である。学習用との分割はしていない。原本は `src/toolselect/gold.py` で、機械可読の写しは `data/cases.json` である。",
        "",
        "ラベルは実装者1名が、モデルの出力を見る前に付けた。選ぶべきツールは、その依頼で出すのが正解のツールである。必須は、その中で必ず含めるツールである。質問は、その依頼で確認が必要かどうかである。",
        "",
    ]
    by_primary: dict[str, list[dict]] = {}
    for case in cases:
        by_primary.setdefault(case["primary"], []).append(case)
    for primary in PRIMARY_ORDER:
        group = by_primary.get(primary) or []
        if not group:
            continue
        lines.append(f"## {PRIMARY_LABEL.get(primary, primary)}（{len(group)}件）")
        lines.append("")
        for case in group:
            acceptable = case["acceptable"]
            required = case["required"]
            lines.append(f"### {case['id']}　{case['text']}")
            lines.append("")
            lines.append(f"- 選ぶべきツール: {_names(acceptable, catalog_names)}")
            if required == acceptable:
                lines.append("- 必須: 選ぶべきツールと同じ")
            else:
                lines.append(f"- 必須: {_names(required, catalog_names)}")
            lines.append(f"- 複数候補: {_yes_no(case['multiple'])}")
            lines.append(f"- 質問: {_yes_no(case['clarify'])}")
            lines.append(f"- 適用: {APPLICABLE.get(case['applicable'], case['applicable'])}")
            needed = "、".join(case["needed"]) if case["needed"] else "なし"
            lines.append(f"- 確認したいこと: {needed}")
            lines.append(f"- 重要度: {SEVERITY.get(case['severity'], case['severity'])}")
            extras = [PRIMARY_LABEL.get(tag, tag) for tag in case["categories"] if tag != primary]
            if extras:
                lines.append(f"- 重なる種類: {'、'.join(extras)}")
            lines.append(f"- 理由: {case['reason']}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


CONDITION_ORDER = ("A1", "A2", "A3", "B1", "C1", "C2", "C3", "D1", "D2", "D3", "D4")
CONDITION_LABEL = {
    "A1": "A1（LLM選択・Sol）",
    "A2": "A2（LLM選択・Terra）",
    "A3": "A3（LLM選択・Luna）",
    "B1": "B1（辞書・規則）",
    "C1": "C1（LLM採点＋しきい値（擬似jev）・Sol）",
    "C2": "C2（LLM採点＋しきい値（擬似jev）・Terra）",
    "C3": "C3（LLM採点＋しきい値（擬似jev）・Luna）",
    "D1": "D1（オントロジー）",
    "D2": "D2（オントロジー＋LLM・Sol）",
    "D3": "D3（オントロジー＋LLM・Terra）",
    "D4": "D4（オントロジー＋LLM・Luna）",
}


def _cell(text: str) -> str:
    return text.replace("|", "｜").replace("\n", " ")


def _format_score(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:g}"


def _score_cell(prediction: dict, names: dict[str, str]) -> str:
    """LLM採点＋しきい値（擬似jev）が付けた適合度。20未満は最高点だけ残し、0は省く。"""
    scores = prediction.get("scores")
    if not isinstance(scores, dict) or not scores:
        return "—"
    ranked = sorted(
        ((float(score), tool_id) for tool_id, score in scores.items()),
        key=lambda item: (-item[0], item[1]),
    )
    top = ranked[0][0]
    if top <= 0:
        return "すべて 0"
    shown = [(score, tool_id) for score, tool_id in ranked if score >= 20]
    if not shown:
        leaders = [(score, tool_id) for score, tool_id in ranked if score == top]
        if len(leaders) > 3:
            return f"最高 {_format_score(top)}"
        shown = leaders
    return "、".join(f"{names.get(tool_id, tool_id)} {_format_score(score)}" for score, tool_id in shown)


def _judgment(case: dict, prediction: dict) -> str:
    tags = classify_errors(case, prediction)
    if not tags:
        return "選ぶべきツールと一致"
    return "、".join(tags)


def _comparison_block(case: dict, by_condition: dict[str, dict[str, dict]], names: dict[str, str]) -> list[str]:
    lines = [
        f"### {case['id']}　{case['text']}",
        "",
        f"選ぶべきツール: {_names(case['acceptable'], names)}。質問の正解: {_yes_no(case['clarify'])}。",
        "",
        "| 条件 | 出した候補 | 適合度 | 質問 | 判断 |",
        "|---|---|---|---|---|",
    ]
    for condition_id in CONDITION_ORDER:
        prediction = (by_condition.get(condition_id) or {}).get(case["id"])
        if prediction is None:
            lines.append(f"| {CONDITION_LABEL[condition_id]} | 未実行 |  |  |  |")
            continue
        asked = "なし"
        questions = prediction.get("clarification_questions") or []
        if prediction.get("needs_clarification"):
            asked = "あり。" + " ".join(str(item) for item in questions) if questions else "あり"
        lines.append(
            "| {label} | {predicted} | {scores} | {asked} | {judgment} |".format(
                label=CONDITION_LABEL[condition_id],
                predicted=_cell(_names(prediction.get("candidate_ids") or [], names)),
                scores=_cell(_score_cell(prediction, names)),
                asked=_cell(asked),
                judgment=_cell(_judgment(case, prediction)),
            )
        )
    lines.append("")
    return lines


def render_case_comparison(
    cases: list[dict],
    by_condition: dict[str, dict[str, dict]],
    names: dict[str, str],
    case_ids: list[str],
) -> str:
    by_id = {case["id"]: case for case in cases}
    lines = [
        "## 同じ依頼での比較",
        "",
        f"上の事例に出た依頼について、{len(CONDITION_ORDER)}条件が何を候補にし、質問したかを並べた。判断は、選ぶべきツールと質問の有無を正解と比べた自動分類である。",
        "",
        "適合度はLLM採点＋しきい値（擬似jev）が各ツールに付けた得点である。LLM選択と辞書・規則は得点を付けない。20以上を高い順に書き、どれも20未満のときは最高点だけを書いた。同点が4件以上なら最高点の数値だけにした。0は省いた。候補に入れる下限は50、一位との差が15以内を接近とみなす。情報不足でも、一位が75以上ならその理由だけでは質問しない。",
        "",
    ]
    for case_id in case_ids:
        lines.extend(_comparison_block(by_id[case_id], by_condition, names))
    return "\n".join(lines)


def load_run_predictions(run_dir: Path) -> dict[str, dict[str, dict]]:
    import json

    by_condition: dict[str, dict[str, dict]] = {}
    for condition_id in CONDITION_ORDER:
        path = run_dir / condition_id / "predictions.jsonl"
        rows: dict[str, dict] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                rows[str(row["case_id"])] = row
        by_condition[condition_id] = rows
    return by_condition


def render_results(run_dir: Path) -> str:
    names = {tool.id: tool.name for tool in load_catalog().tools}
    cases = load_cases()
    by_condition = load_run_predictions(run_dir)
    lines = [
        "# テスト結果",
        "",
        f"{len(cases)}件それぞれについて、{len(CONDITION_ORDER)}条件が出した候補と質問を並べた。元データは `{run_dir.relative_to(ROOT).as_posix()}` の `predictions.jsonl` である。",
        "",
        "判断は、選ぶべきツールと質問の有無を正解と比べた自動分類である。人が読み直した分類ではない。",
        "",
        "適合度はLLM採点＋しきい値（擬似jev、C1〜C3）が各ツールに付けた得点である。LLM選択と辞書・規則は得点を付けない。20以上を高い順に書き、どれも20未満のときは最高点だけを書いた。同点が4件以上なら最高点の数値だけにした。0は省いた。候補に入れる下限は50、一位との差が15以内を接近とみなす。情報不足でも、一位が75以上ならその理由だけでは質問しない。",
        "",
    ]
    by_primary: dict[str, list[dict]] = {}
    for case in cases:
        by_primary.setdefault(case["primary"], []).append(case)
    for primary in PRIMARY_ORDER:
        group = by_primary.get(primary) or []
        if not group:
            continue
        lines.append(f"## {PRIMARY_LABEL.get(primary, primary)}（{len(group)}件）")
        lines.append("")
        for case in group:
            lines.extend(_comparison_block(case, by_condition, names))
    return "\n".join(lines).rstrip() + "\n"


def write_results(run_dir: Path | None = None, path: Path | None = None) -> Path:
    runs = ROOT / "runs"
    if run_dir is None:
        candidates = [
            item
            for item in runs.iterdir()
            if item.is_dir() and (item / "A1" / "predictions.jsonl").exists() and (item / "C3" / "predictions.jsonl").exists()
        ]
        if not candidates:
            raise FileNotFoundError("A1 と C3 のそろった実行結果が runs に無い")
        run_dir = max(candidates, key=lambda item: item.name)
    target = path or (DOCS / "テスト結果.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_results(run_dir), encoding="utf-8")
    return target


def write_testset(path: Path | None = None) -> Path:
    target = path or (DOCS / "テストセット.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_testset(), encoding="utf-8")
    return target


if __name__ == "__main__":
    print(write_testset())
