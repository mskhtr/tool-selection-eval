"""150件の正解と、事例の横断比較を、人が読むMarkdownにする。"""

from __future__ import annotations

from pathlib import Path

from toolselect.catalog import load_catalog
from toolselect.dataset import load_cases
from toolselect.errors import classify_errors
from toolselect.paths import ROOT

DOCS = ROOT / "docs"

PRIMARY_ORDER = (
    "clear",
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
        "比較に使った150件である。学習用との分割はしていない。原本は `src/toolselect/gold.py` で、機械可読の写しは `data/cases.json` である。",
        "",
        "ラベルは実装者1名が、モデルの出力を見る前に付けた。許容は出してよいツール、必須は必ず含めるツールである。質問は、その依頼で確認が必要かどうかである。",
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
            lines.append(f"- 許容: {_names(acceptable, catalog_names)}")
            if required == acceptable:
                lines.append("- 必須: 許容と同じ")
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


CONDITION_ORDER = ("A1", "A2", "A3", "B1", "C1", "C2", "C3")
CONDITION_LABEL = {
    "A1": "A1 直接選択 Terra",
    "A2": "A2 直接選択 Sol",
    "A3": "A3 直接選択 Luna",
    "B1": "B1 辞書・規則",
    "C1": "C1 擬似jev Terra",
    "C2": "C2 擬似jev Sol",
    "C3": "C3 擬似jev Luna",
}


def _cell(text: str) -> str:
    return text.replace("|", "｜").replace("\n", " ")


def _judgment(case: dict, prediction: dict) -> str:
    tags = classify_errors(case, prediction)
    if not tags:
        return "許容と一致"
    return "、".join(tags)


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
        "上の事例に出た依頼について、7条件が何を候補にし、質問したかを並べた。判断は、許容するツールと質問の有無を正解と比べた自動分類である。",
        "",
    ]
    for case_id in case_ids:
        case = by_id[case_id]
        lines.append(f"### {case_id}　{case['text']}")
        lines.append("")
        lines.append(f"許容: {_names(case['acceptable'], names)}。質問の正解: {_yes_no(case['clarify'])}。")
        lines.append("")
        lines.append("| 条件 | 出した候補 | 質問 | 判断 |")
        lines.append("|---|---|---|---|")
        for condition_id in CONDITION_ORDER:
            prediction = (by_condition.get(condition_id) or {}).get(case_id)
            if prediction is None:
                lines.append(f"| {CONDITION_LABEL[condition_id]} | 未実行 |  |  |")
                continue
            asked = "なし"
            questions = prediction.get("clarification_questions") or []
            if prediction.get("needs_clarification"):
                asked = "あり。" + " ".join(str(item) for item in questions) if questions else "あり"
            lines.append(
                "| {label} | {predicted} | {asked} | {judgment} |".format(
                    label=CONDITION_LABEL[condition_id],
                    predicted=_cell(_names(prediction.get("candidate_ids") or [], names)),
                    asked=_cell(asked),
                    judgment=_cell(_judgment(case, prediction)),
                )
            )
        lines.append("")
    return "\n".join(lines)


def write_testset(path: Path | None = None) -> Path:
    target = path or (DOCS / "テストセット.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_testset(), encoding="utf-8")
    return target


if __name__ == "__main__":
    print(write_testset())
