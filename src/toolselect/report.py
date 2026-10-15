from __future__ import annotations

import json
from pathlib import Path


def _pct(value: float | None) -> str:
    if value is None:
        return "未集計"
    return f"{value * 100:.1f}%"


def _num(value: float | None) -> str:
    if value is None:
        return "未集計"
    return f"{value:.3f}"


# 並びと附番の順。1 が先頭。
INTELLIGENCE_RANK = {"sol": 0, "terra": 1, "luna": 2}
DISPLAY_NAME = {"sol": "Sol", "terra": "Terra", "luna": "Luna"}
METHOD_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
METHOD_LABEL = {"A": "LLM選択", "B": "辞書・規則", "C": "LLM採点＋しきい値（擬似jev）", "D": "オントロジー"}
CATEGORY_LABEL = {
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
ERROR_LABEL = {
    "過剰な意図補完": "書いていない目的を補って、候補を一つに絞った。",
    "表層キーワード誤選択": "引っかけ用の語に釣られて、カタログ外なのに候補を出した。",
    "候補漏れ": "出すべきツールが候補に入っていない。質問だけして候補が空の場合も含む。",
    "過剰選択": "選ぶべきでないツールを多く足した。",
    "不適切な追加質問": "質問しなくてよい依頼なのに質問した。",
    "質問不足": "質問すべき依頼なのに質問しなかった。",
    "カタログ照合ミス": "カタログに無い ID を返した。",
    "その他": "上の規則に当てはまらない不一致。",
}


def order_conditions(conditions: list[dict]) -> list[dict]:
    ordered = sorted(
        conditions,
        key=lambda row: (
            METHOD_ORDER.get(row["method"], 9),
            INTELLIGENCE_RANK.get(row.get("model") or "", -1),
        ),
    )
    counts: dict[str, int] = {}
    numbered = []
    for row in ordered:
        method = row["method"]
        counts[method] = counts.get(method, 0) + 1
        copied = dict(row)
        copied["id"] = f"{method}{counts[method]}"
        numbered.append(copied)
    return numbered


def _model_name(model: str | None) -> str:
    if not model:
        return "なし"
    return DISPLAY_NAME.get(model, model)


def method_label(row: dict) -> str:
    if row["method"] == "D" and row.get("model"):
        return "オントロジー＋LLM"
    return METHOD_LABEL.get(row["method"], row["method"])


def condition_label(row: dict) -> str:
    method = method_label(row)
    model = _model_name(row.get("model"))
    if row["method"] == "D" and model != "なし":
        return f"{row['id']}（オントロジー＋LLM・{model}）"
    if row["method"] == "B" or model == "なし":
        return f"{row['id']}（{method}）"
    return f"{row['id']}（{method}・{model}）"


def _condition_body(row: dict) -> str:
    model = _model_name(row.get("model"))
    if row["method"] == "A":
        return f"{model} が共有カタログを読み、候補・追加質問・保留を直接返す。複数候補を返してよい。"
    if row["method"] == "B":
        return "モデルは使わない。名称、目的の手がかり、キーワードに紐づくツールの組、事務・説明表現の除外で候補を決める。得点は付けない。"
    if row["method"] == "C":
        return f"{model} が全ツールに適合度を付ける。別処理が ID をカタログで引き、得点の高さと差で候補を出すか質問するかを決める。適合度は確率ではない。"
    if row["method"] == "D" and model == "なし":
        return "モデルは使わない。語を概念にまとめ、関係でツールへ結ぶ。割れや持たないは示唆で、目的を一つに決めない。"
    if row["method"] == "D":
        return f"{model} が依頼文を概念へ当てはめる。ツールの決定はオントロジーの関係が行う。"
    return ""


def _category_counts(counts: dict) -> str:
    parts = [f"{_category_name(key)} {counts[key]}件" for key in _ordered_categories(list(counts))]
    return "、".join(parts) if parts else "なし"


def _category_name(key: str) -> str:
    return CATEGORY_LABEL.get(key, key)


def _date_only(value: object) -> str:
    text = str(value or "")
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return text


def _grade(value: float | None) -> str:
    if value is None:
        return "未集計"
    if value >= 0.85:
        return "良い"
    if value >= 0.80:
        return "中間"
    return "弱い"


def _category_cell(summary: dict | None, key: str) -> str:
    if not summary:
        return "未集計"
    value = ((summary.get("by_category") or {}).get(key) or {}).get("f1")
    return f"{_num(value)}（{_grade(value)}）"


def _ordered_categories(keys: list[str]) -> list[str]:
    known = [key for key in CATEGORY_LABEL if key in keys]
    rest = [key for key in keys if key not in CATEGORY_LABEL]
    return known + rest


def _by_id(conditions: list[dict]) -> dict[str, dict]:
    return {row["id"]: row for row in conditions}


def _f1(row: dict | None) -> float | None:
    if not row:
        return None
    return (row.get("summary") or {}).get("f1")


def _cat_f1(row: dict | None, key: str) -> float | None:
    if not row:
        return None
    return ((row.get("summary") or {}).get("by_category") or {}).get(key, {}).get("f1")


_REASON = {
    "A2": "候補は36件すべて選ぶべきツールと一致した。カタログ外とキーワードの依頼では保留したが、質問文が空だった。",
    "A1": "「冷熱を繰り返すとはんだが持たない」で、はんだ寿命予測だけを質問なしで出した。",
    "B1": "目的の文字列からずれると、亀裂進展と寿命予測を両方出して必ず質問する。",
    "C3": "50点未満は候補から外す。暗黙の前提では両はんだツールを残せた。",
    "A3": "半田、ハンダ、ソルダだけ、寿命だけ、のように目的が未定だと候補を空にする。",
    "C1": "半田やハンダのシミュレーションは両ツールが50点未満。025は寿命予測だけを質問なしで出した。",
    "C2": "半田やハンダのシミュレーションは両ツールが50点未満。025は寿命予測だけを出して質問した。",
    "D1": "36件すべてで候補が選ぶべきツールと一致した。関係は、正解を書いた人が辞書の外れ方を見てから書いている。",
    "D2": "Sol の概念への当てはめは、オントロジーの関係が選ぶ候補と一致した。",
    "D3": "Terra の概念への当てはめは、オントロジーの関係が選ぶ候補と一致した。",
    "D4": "「鋼が繰り返しで折れそうなので寿命を見たい」で、寿命を概念にせず示唆に入れた。候補は空になった。",
}


def _tradeoffs() -> list[str]:
    return [
        "",
        "## 各条件の利点と欠点",
        "",
        "利点と欠点は、この36件で出た候補と質問から書いている。",
        "",
        "| 条件 | 利点 | 欠点 |",
        "|---|---|---|",
        "| A1（LLM選択・Sol） | 目的が書いてある依頼では候補が揃う。不要な質問は無かった。 | 「冷熱を繰り返すとはんだが持たない」で、寿命予測だけを質問なしで出した。カタログ外では質問文が空だった。 |",
        "| A2（LLM選択・Terra） | 36件すべてで候補が選ぶべきツールと一致した。不要な質問も、一つに決めた割合も無い。 | カタログ外とキーワードの引っかけでは保留したが、質問文が空で、追加質問の妥当は 66.7% だった。 |",
        "| A3（LLM選択・Luna） | 目的が書いてある依頼では候補が揃う。不要な質問は無かった。 | 半田、ハンダ、ソルダだけ、寿命だけ、のように目的が未定だと候補を空にする。025では寿命予測だけを質問なしで出した。 |",
        "| B1（辞書・規則） | モデルを使わない。当たった規則が残る。質問すべき依頼では質問文がある。 | 目的の文字列がずれると、はんだの二つを出して必ず質問する。不要な質問は 38.9%。熱疲労寿命は疲労寿命の語にも当たる。 |",
        "| C1（LLM採点＋しきい値（擬似jev）・Sol） | 点数と、候補にするかの決まりが分かれている。目的が書いてある依頼では候補が揃いやすい。 | 50点未満は候補から外れる。半田のシミュレーションは両ツールが50点未満で空になった。025は寿命予測だけを質問なしで出した。 |",
        "| C2（LLM採点＋しきい値（擬似jev）・Terra） | 025では寿命予測だけでも質問した。一つに決めた割合は無い。 | 候補集合の F1 は C1 と同じ 0.769。目的が未定だと点数が低く、候補が空になる。不要な質問は 16.7%。 |",
        "| C3（LLM採点＋しきい値（擬似jev）・Luna） | 暗黙の前提では両はんだツールを50点で残せた。一つに決めた割合は無く、追加質問の妥当は 100% だった。 | 表記ゆれ、口語、曖昧は弱い。目的が複数だと点数が近く、質問が残る。候補集合の F1 は 0.806。 |",
        "| D1（オントロジー） | この36件では候補と質問が選ぶべき結果と一致した。長い語を先に取り、割れや持たないだけでは一つに決めない。 | 関係は、正解を書いた人が辞書の外れ方を見てから書いている。ラベルに無い語は概念にならない。 |",
        "| D2（オントロジー＋LLM・Sol） | Sol の概念への当てはめは、この36件では関係の決定と一致した。 | モデルが概念を落とすと、関係はツールを選べない。この36件では Sol の落としは無かった。 |",
        "| D3（オントロジー＋LLM・Terra） | Terra の概念への当てはめは、この36件では関係の決定と一致した。 | モデルが概念を落とすと、関係はツールを選べない。この36件では Terra の落としは無かった。 |",
        "| D4（オントロジー＋LLM・Luna） | 多くの依頼では概念の当てはめが関係と一致した。追加質問の妥当は 100% だった。 | 「鋼が繰り返しで折れそうなので寿命を見たい」で、寿命を概念にせず示唆に入れ、候補が空になった。 |",
        "",
        "## 未知は言い、決まっていれば質問しない",
        "",
        "分からない依頼では一つに決めず、分からないと質問する。目的が決まっている依頼では質問しない。この見方で、この36件の一番は **D1（オントロジー）**、**D2（オントロジー＋LLM・Sol）**、**D3（オントロジー＋LLM・Terra）** である。三つは同じで、決まっている依頼に質問は無く、候補も選ぶべきツールと一致した。目的が未定の依頼では質問文があり、一つには決めなかった。カタログ外でもツールを出さず、質問文があった。",
        "",
        "件数は、その条件がこの見方から外れた依頼の数である。0 がよい。",
        "",
        "| 条件 | 決まっているのに質問 | 決まっているのに候補が違う | 未定なのに質問せず一つに決めた | 未定なのに候補が空 | カタログ外で質問文が無い |",
        "|---|---|---|---|---|---|",
        "| D1（オントロジー） | 0 | 0 | 0 | 0 | 0 |",
        "| D2（オントロジー＋LLM・Sol） | 0 | 0 | 0 | 0 | 0 |",
        "| D3（オントロジー＋LLM・Terra） | 0 | 0 | 0 | 0 | 0 |",
        "| A2（LLM選択・Terra） | 0 | 0 | 0 | 0 | 6 |",
        "| A1（LLM選択・Sol） | 0 | 0 | 1 | 0 | 6 |",
        "| D4（オントロジー＋LLM・Luna） | 1 | 1 | 0 | 0 | 0 |",
        "| B1（辞書・規則） | 7 | 6 | 0 | 0 | 0 |",
        "| C2（LLM採点＋しきい値（擬似jev）・Terra） | 3 | 0 | 0 | 8 | 0 |",
        "| C3（LLM採点＋しきい値（擬似jev）・Luna） | 3 | 0 | 0 | 7 | 0 |",
        "| A3（LLM選択・Luna） | 0 | 0 | 1 | 7 | 6 |",
        "| C1（LLM採点＋しきい値（擬似jev）・Sol） | 3 | 0 | 1 | 8 | 0 |",
        "",
        "A2（LLM選択・Terra）は、決まっている依頼では質問せず、候補も一致した。カタログ外の6件は保留したが、質問文が空で、分からないとは書いていない。B1（辞書・規則）は未定でも質問文があるが、決まっている依頼への質問が7件ある。",
        "",
        "## この36件では精度が出ても外れる言い方",
        "",
        "このセットの口語は、ソルダ、クラック、クラックグロース、S-N、回して、である。現場の一部でしか使わない言い回しや、強いスラングは入れていない。次は方式の仕組みから言える外れ方で、この実行の点数ではない。",
        "",
        "| 言い方 | 辞書・規則 | オントロジー | LLM選択とLLM採点 | オントロジー＋LLM |",
        "|---|---|---|---|---|",
        "| ラベルに無い言い回し。例は、亀裂を「ヒビが走る」、寿命を「接合が死ぬ」と言う。 | キーワードも目的の手がかりも無い。はんだなどの登録語が残れば組を出して質問し、無ければ保留する。 | 概念が立たない。はんだだけ残れば亀裂進展と寿命予測を出して質問し、登録語も無ければ保留する。 | 学習で知っている言い回しなら当たることがある。チーム内だけの呼び方は、カタログにもプロンプトにも無いので、空になるか近い語へ寄る。 | モデルはプロンプトの概念IDへしか当てはめない。ラベルから遠い語は概念に入らず、オントロジーと同じく届かない。 |",
        "| 登録語を別の意味で使う。例は、寿命を納期の意味で使う。 | 化学分析、写真、日程は事務の語として保留した。一覧に無い意味の重なりは、解析ツールを出す。 | 辞書と同じ事務の語で保留する。一覧に無い意味の重なりは、立った概念の関係でツールを出す。 | 字面の近いツールへ寄ることがある。この36件の引っかけは保留できた。別の意味のスラングは未計測。 | 字面を概念へ入れると、そのあとの関係がツールを出す。入れなければ保留になる。 |",
        "| その場では一つの目的だと決まっている示唆。例は、持たないを寿命だけと読む現場。 | 目的の文字列が無ければ、はんだの二つを出して必ず質問する。 | 持たないは示唆のままなので、はんだの二つを出して質問する。寿命だけには決めない。 | モデルによっては寿命だけに決め、質問しない。A1 はこの36件でそうなった。 | モデルが寿命を概念に入れると寿命予測だけになる。示唆のままなら二つを出して質問する。 |",
        "",
        "カタログはツール3個である。ツールや目的を足すと、同じ語が複数の組に当たり、辞書は質問が増える。オントロジーは組み合わせの書き漏れで候補が空になる。同じ文の繰り返しは未実施で、LLMありの条件は概念の入れ方が変わることがある。",
    ]


def _metric(row: dict, key: str) -> float | None:
    value = (row.get("summary") or {}).get(key)
    if value is None:
        return None
    return float(value)


def _higher(row: dict, key: str) -> float:
    value = _metric(row, key)
    return 1.0 if value is None else -value


def _lower(row: dict, key: str) -> float:
    value = _metric(row, key)
    return 1.0 if value is None else value


def _rank_key(row: dict) -> tuple:
    return (
        _higher(row, "f1"),
        _lower(row, "unnecessary_question_rate"),
        _lower(row, "forced_one_rate"),
        _higher(row, "clarify_appropriate_rate"),
        _higher(row, "exact_rate"),
        _higher(row, "multi_appropriate_rate"),
        _higher(row, "required_inclusion_rate"),
        _higher(row, "single_accuracy"),
        _higher(row, "abstain_appropriate_rate"),
        _lower(row, "error_rate"),
    )


def _ranked(conditions: list[dict]) -> list[dict]:
    return sorted(conditions, key=_rank_key)


def _place_labels(ranked: list[dict]) -> list[str]:
    keys = [_rank_key(row) for row in ranked]
    labels = []
    for key in keys:
        place = sum(1 for other in keys if other < key) + 1
        tied = sum(1 for other in keys if other == key) > 1
        text = f"{place}位"
        labels.append(f"同率{text}" if tied else text)
    return labels


def _conclusion(conditions: list[dict]) -> list[str]:
    ranked = _ranked(conditions)
    places = _place_labels(ranked)
    top = ranked[0]
    top_key = _rank_key(top)
    tied = [row for row in ranked if _rank_key(row) == top_key]
    if len(tied) == 1:
        opening = f"最もよかったのは **{condition_label(top)}** である。候補集合の F1 は {_num(_f1(top))}。"
    else:
        names = "、".join(f"**{condition_label(row)}**" for row in tied)
        opening = f"最もよかったのは同率1位の {names} である。候補集合の F1 は {_num(_f1(top))} で、不要な質問、一つに決めた割合、追加質問の妥当も同じである。"
    lines = [
        "## 結論",
        "",
        opening,
        "",
        "順位は候補集合の F1 だけでは決めない。F1 が同じときは、不要な質問が少ない方、一つに決めた割合が低い方、追加質問が妥当な方、の順で分ける。ここまで同じときだけ同率とする。候補集合の F1 が 0.85 以上を「良い」、0.80 以上 0.85 未満を「中間」、0.80 未満を「弱い」とした。この区切りは見やすさのためである。",
        "",
        "| 順 | 条件 | 候補集合のF1 | 判定 | 不要な質問 | 一つに決めた | 追加質問の妥当 |",
        "|---|---|---|---|---|---|---|",
    ]
    for place, row in zip(places, ranked):
        summary = row.get("summary") or {}
        lines.append(
            "| {index} | {label} | {f1} | {grade} | {unneeded} | {forced} | {clarify} |".format(
                index=place,
                label=condition_label(row),
                f1=_num(summary.get("f1")),
                grade=_grade(summary.get("f1")),
                unneeded=_pct(summary.get("unnecessary_question_rate")),
                forced=_pct(summary.get("forced_one_rate")),
                clarify=_pct(summary.get("clarify_appropriate_rate")),
            )
        )
    lines.extend(
        [
            "",
            "依頼の種類ごとの判定である。",
            "",
            "| 条件 | 明確 | 表記ゆれ | 口語 | 曖昧 | 暗黙の前提 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in ranked:
        lines.append(
            "| {label} | {clear} | {orthography} | {colloquial} | {ambiguous} | {implicit} |".format(
                label=condition_label(row),
                clear=_grade(_cat_f1(row, "clear")),
                orthography=_grade(_cat_f1(row, "orthography")),
                colloquial=_grade(_cat_f1(row, "colloquial")),
                ambiguous=_grade(_cat_f1(row, "ambiguous")),
                implicit=_grade(_cat_f1(row, "implicit")),
            )
        )
    lines.extend(["", "| 条件 | 理由 |", "|---|---|"])
    for row in ranked:
        lines.append(f"| {condition_label(row)} | {_REASON.get(row['id'], '')} |")
    lines.extend(_tradeoffs())
    lines.append("")
    return lines


def render_report(run_dir: Path) -> str:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    conditions = order_conditions(json.loads((run_dir / "comparison.json").read_text(encoding="utf-8")))
    lines = [
        "# ツール選択方式の比較レポート",
        "",
        *_conclusion(conditions),
        "## 実行条件",
        "",
        f"- 実行日時: {_date_only(manifest.get('created_at'))}",
        f"- テスト件数: {manifest.get('n_cases')}",
        f"- 主カテゴリ内訳: {_category_counts(manifest.get('primary_counts') or {})}",
        f"- 正解ラベル: {manifest.get('labeling', {}).get('note')}",
        "- 条件番号は方式ごとの連番で、モデルは Sol、Terra、Luna の順に付ける。",
        "- モデルID: Sol `gpt-5.6-sol-medium`、Terra `gpt-5.6-terra-medium`、Luna `gpt-5.6-luna-medium`。推論設定はモデルIDの medium。温度は指定できない。",
        "- グラフは LangGraph。解析ツールの実行機能は評価グラフに繋いでいない。",
        "",
        "## 比較条件",
            "",
            "番号は方式ごとの連番である。同じ番号でも方式が違えば別条件である。A1（LLM選択・Sol）と C1（LLM採点＋しきい値（擬似jev）・Sol）は、どちらも Sol だが別の実験である。",
            "",
            "- LLM選択: LLM がカタログと依頼文を読み、候補、追加質問、保留を一度に返す。書いていない目的は補わない。",
            "- 辞書・規則: LLM を使わない。カタログの名称、目的の手がかり、キーワードに紐づくツールの組、事務・説明表現の除外で候補を決める。どの規則が当たったかを残す。得点は付けない。",
            "- LLM採点＋しきい値（擬似jev）: LLM がカタログの全ツールに適合度を付ける。別処理がツール ID をカタログから引き、得点の高さと差で、候補を出すか追加質問するかを決める。適合度は校正済みの確率ではない。",
            "- オントロジー: 語を概念にまとめ、関係でツールへ結ぶ。D1 は LLM を使わない。D2、D3、D4 は LLM が概念へ当てはめ、候補は同じ関係が決める。割れ、持たない、折れは示唆で、目的を一つに決めない。",
            "",
            "### LLM選択",
            "",
            "A1、A2、A3 はこの流れである。モデルだけが違う。",
            "",
            "```mermaid",
            "flowchart TD",
            "    input[\"依頼文とカタログ\"] --> llm[\"LLMが一度に判断する\"]",
            "    llm --> result[\"候補、追加質問、保留を返す\"]",
            "    rule[\"書いていない目的は補わない\"] -.-> llm",
            "```",
            "",
            "### 辞書・規則",
            "",
            "B1 はこの流れである。LLM は使わない。当たった規則は記録する。得点は付けない。",
            "",
            "```mermaid",
            "flowchart TD",
            "    input[\"依頼文を正規化する\"] --> meta{\"事務や説明の語があるか\"}",
            "    meta -->|ある| veto[\"候補なしで保留する\"]",
            "    meta -->|ない| verb{\"解析を頼む語があるか\"}",
            "    verb -->|ない| noverb[\"候補なしで保留する\"]",
            "    verb -->|ある| strong{\"名称か目的の手がかりがあるか\"}",
            "    strong -->|ある| multi{\"候補が複数で、両方とは書いていないか\"}",
            "    multi -->|はい| ask[\"その候補を出して質問する\"]",
            "    multi -->|いいえ| keep[\"その候補を出す。質問しない\"]",
            "    strong -->|ない| family{\"はんだ、半田、ハンダ、ソルダ、bga のどれかがあるか\"}",
            "    family -->|ある| fam[\"はんだ亀裂進展と寿命予測を両方出して必ず質問する\"]",
            "    family -->|分からない| weak{\"弱い語だけ当たるか\"}",
            "    weak -->|当たる| weakask[\"当たったツールを出して質問する\"]",
            "    weak -->|当たらない| none[\"候補なしで保留する\"]",
            "```",
            "",
            "はんだ、半田、ハンダ、ソルダ、bga は、はんだ用ツールの組を指すキーワードである。目的の手がかりが無いときにこのどれかがあると、はんだ亀裂進展シミュレーションとはんだ寿命予測シミュレーションを両方出し、必ず質問する。目的は一つに決めない。「両方」と書いてあっても、この分岐では質問をやめない。名称か目的の手がかりがあるときは、このキーワードには広げない。短い目的の語が、別ツールの長い語の一部なら、短い方は捨てる。",
            "",
            "### LLM採点＋しきい値（擬似jev）",
            "",
            "C1、C2、C3 はこの流れである。点数を付けるモデルだけが違う。点数は確率ではない。",
            "",
            "```mermaid",
            "flowchart TD",
            "    input[\"依頼文とカタログ\"] --> score[\"LLMが全ツールに点数を付ける\"]",
            "    score --> resolve[\"名前をカタログのIDへ引き当てる。点数は変えない\"]",
            "    resolve --> enough{\"50点以上があるか\"}",
            "    enough -->|ない| empty[\"候補は空。質問だけ残す\"]",
            "    enough -->|ある| band[\"50点以上で、一位との差が15点以内を残す\"]",
            "    band --> tie{\"複数か、情報不足で一位が75点未満か\"}",
            "    tie -->|はい| ask[\"候補を出して質問する\"]",
            "    tie -->|いいえ| one[\"その候補を出す\"]",
            "```",
            "",
            "### オントロジー",
            "",
            "D1 は LLM を使わない。D2、D3、D4 は LLM が依頼文を概念へ当てはめ、そのあとで同じ関係が候補を決める。",
            "",
            "```mermaid",
            "flowchart TD",
            "    input[\"依頼文\"] --> gate{\"事務の語、または依頼の語が無いか\"}",
            "    gate -->|ある| veto[\"候補なしで保留する\"]",
            "    gate -->|ない| read[\"語を概念にする。長い語を優先する\"]",
            "    read --> relate{\"概念の関係がツールに届くか\"}",
            "    relate -->|届く| multi{\"候補が複数で、両方とは書いていないか\"}",
            "    multi -->|はい| ask[\"その候補を出して質問する\"]",
            "    multi -->|いいえ| keep[\"その候補を出す。質問しない\"]",
            "    relate -->|届かない| subject{\"対象だけ分かるか\"}",
            "    subject -->|はんだだけ、または寿命だけ| both[\"関係するツールを全部出して質問する\"]",
            "    subject -->|分からない| none[\"候補なしで保留する\"]",
            "```",
            "",
            "割れ、持たない、折れは示唆である。概念には足さず、目的を一つに決めない。LLMありのときは、上の読み取りだけを LLM が行う。そのあとの関係は D1 と同じである。",
            "",
            "D1 の読み取りで、依頼がどう分かれるかの例である。",
            "",
            "| 依頼 | 立った概念 | 示唆 | 判断 | 候補 |",
            "|---|---|---|---|---|",
            "| 半田のき裂がどこまで進むかシミュレーションしたい | はんだ、亀裂、進展 | なし | はんだと亀裂がそろった | はんだ亀裂進展シミュレーション。質問しない |",
            "| 半田接合の熱疲労寿命を計算したい | はんだ、熱疲労、寿命 | なし | 熱疲労は疲労より長いので、疲労は立たない。はんだと寿命がそろった | はんだ寿命予測シミュレーション。質問しない |",
            "| 半田のシミュレーションをしたい | はんだ | なし | 対象だけで、目的の概念が無い | はんだ亀裂進展シミュレーションとはんだ寿命予測シミュレーションを出して質問する |",
            "| はんだが割れそうなので見たい | はんだ | 亀裂（割れ） | 割れは亀裂の確定にしない | はんだ亀裂進展シミュレーションとはんだ寿命予測シミュレーションを出して質問する |",
            "| 冷熱を繰り返すとはんだが持たない気がするので見たい | はんだ | 寿命（持たない） | 持たないは寿命の確定にしない | はんだ亀裂進展シミュレーションとはんだ寿命予測シミュレーションを出して質問する |",
            "| 温度サイクルの寿命と、亀裂がどう伸びるかの両方をはんだで見たい | はんだ、寿命、亀裂 | なし | 二つの関係に届き、両方と書いてある | はんだ亀裂進展シミュレーションとはんだ寿命予測シミュレーションを出す。質問しない |",
            "| 鋼が繰り返しで折れそうなので寿命を見たい | 金属、寿命 | なし | 寿命の語があるので、折れは示唆に残さない。金属と寿命がそろった | 疲労寿命予測。質問しない |",
            "| はんだの成分を化学分析したい | はんだ | なし | 化学分析は解析の実行ではない | 候補なしで保留する |",
            "| ブラケットの固有振動数を計算したい | なし | なし | 計算とはあるが、概念がツールまで届かない | 候補なしで保留する |",
            "",
            "D4（オントロジー＋LLM・Luna）は、「鋼が繰り返しで折れそうなので寿命を見たい」で寿命を概念にせず示唆へ入れた。金属だけでは疲労寿命予測に届かず、候補は空になった。",
            "",
            "| 条件 | 方式 | モデル | この条件でやること |",
            "|---|---|---|---|",
    ]
    for row in conditions:
        lines.append(
            f"| {condition_label(row)} | {method_label(row)} | {_model_name(row.get('model'))} | {_condition_body(row)} |"
        )
    lines.extend(
        [
            "",
            "## 評価指標",
            "",
            "候補の正解は一つのツールに限らない。選ぶべきツールに入っていればそのツールは正解で、必須は必ず含めなければならない。質問すべきか、保留すべきかもラベルに含まれ、ユーザーが後から選んだ結果は精度に入れていない。",
            "",
            "### 候補集合のF1",
            "",
            "出したツールの集合が、選ぶべきツールにどれだけ近いかを、依頼1件ごとに 0 から 1 で表した値である。表の数字は、その値を対象の依頼で平均したものである。全件の平均が総合の F1、種類ごとの平均がカテゴリ別の F1 である。",
            "",
            "1件の計算は、次の二つを組み合わせる。",
            "",
            "- 適合率は、出したツールのうち選ぶべきツールに入っていた割合である。余分なツールを足すと下がる。",
            "- 再現率は、選ぶべきツールのうち出せていた割合である。出すべきツールを落とすと下がる。",
            "- F1 は 2 × 適合率 × 再現率 ÷（適合率 + 再現率）である。どちらかが低いと、もう一方が高くても F1 は伸びない。",
            "",
            "例は次のとおりである。",
            "",
            "- 選ぶべきツールが疲労寿命予測だけで、それだけ出した。F1 は 1。",
            "- 選ぶべきツールがはんだ亀裂進展とはんだ寿命予測の2件で、1件だけ出した。適合率は 1、再現率は 0.5、F1 は 0.667。",
            "- 選ぶべきツールが1件で、その1件に加えて別のツールも出した。適合率は 0.5、再現率は 1、F1 は 0.667。",
            "- 選ぶべきツールがあるのに候補が空、または選ぶべきツールが無いのに候補を出した。F1 は 0。",
            "- 選ぶべきツールも候補も無い。出さないのが正解で出していないので、F1 は 1。",
            "",
            "F1 が見ているのはツールの集合だけである。質問の有無は、下の表の「追加質問の妥当」と「不要な質問」で集計する。",
            "",
            "| 指標 | 意味 | 読み方 |",
            "|---|---|---|",
            "| 候補集合のF1 | 上の計算を依頼ごとに行い、平均する。1 に近いほど、出してよいツールに近い。 | 1 なら過不足なく一致。0.667 は、2件中1件だけ出すか、正解1件に余分を1件足した程度。 |",
            "| 完全一致 | 出した候補が選ぶべきツールとまったく同じだった割合。 | 高いほど、過不足なく一致している。 |",
            "| 必須の包含 | 必須ツールがすべて予測に入っていた割合。必須が空のケースは分母に入らない。 | 高いほど、落としてはいけないツールを残せている。 |",
            "| 単一正解 | 正解が1ツールのケースで、その1件だけを選べた割合。 | 高いほど、目的が一つの依頼を選べている。 |",
            "| 複数候補の妥当 | 複数候補が期待されるケースで、必須を含み、選ぶべきツールの範囲に収まり、2件以上出している割合。 | 高いほど、迷う依頼で候補を狭めすぎていない。 |",
            "| 追加質問の妥当 | 質問すべきケースで、質問すると判断し、質問文もある割合。 | 高いほど、確認が必要な依頼で質問できている。 |",
            "| 不要な質問 | 質問しなくてよいケースで、それでも質問した割合。 | 低いほど、明確な依頼を止めずに進める。 |",
            "| 一つに決めた | 複数候補を残して質問すべきケースで、質問せず1件に決めた割合。 | 低いほど、書いていない目的で絞り込みすぎていない。 |",
            "| 対象外の保留 | カタログ外、または適用が不明なケースで、候補を出さず保留した割合。 | 高いほど、カタログに無い依頼をツールに寄せていない。 |",
            "| 処理エラー | 応答を候補に変換できなかった割合。選択の良し悪しではない。 | 0 なら、集計に乗らなかった応答はない。 |",
            "",
            "カテゴリ別の値も同じ候補集合の F1 である。1件の依頼が複数カテゴリに入ることがある。誤り分類は規則による自動付与で、1件に複数の誤りが付く。人手で読み直した分類ではない。",
            "",
            "## 結果の一覧",
            "",
            "候補集合の F1 が 0.85 以上を「良い」、0.80 以上 0.85 未満を「中間」、0.80 未満を「弱い」とした。この区切りは一覧を見やすくするためのものである。",
            "",
            "| 順 | 条件 | 方式 | モデル | 候補集合のF1 | 判定 | 曖昧 | 暗黙の前提 | 明確 |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    ranked = _ranked(conditions)
    for place, row in zip(_place_labels(ranked), ranked):
        summary = row.get("summary") or {}
        lines.append(
            "| {index} | {id} | {method} | {model} | {f1} | {grade} | {ambiguous} | {implicit} | {clear} |".format(
                index=place,
                id=condition_label(row),
                method=method_label(row),
                model=_model_name(row.get("model")),
                f1=_num(summary.get("f1")),
                grade=_grade(summary.get("f1")),
                ambiguous=_category_cell(summary, "ambiguous"),
                implicit=_category_cell(summary, "implicit"),
                clear=_category_cell(summary, "clear"),
            )
        )
    lines.extend(
        [
            "",
            "不要な質問と、一つに決めた割合は、低い方が望ましい。",
            "",
            "| 条件 | 方式 | モデル | 不要な質問 | 一つに決めた | 候補漏れ |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in ranked:
        summary = row.get("summary") or {}
        misses = (summary.get("error_tags") or {}).get("候補漏れ")
        lines.append(
            "| {id} | {method} | {model} | {unneeded} | {forced} | {misses} |".format(
                id=condition_label(row),
                method=method_label(row),
                model=_model_name(row.get("model")),
                unneeded=_pct(summary.get("unnecessary_question_rate")),
                forced=_pct(summary.get("forced_one_rate")),
                misses="未集計" if misses is None else str(misses),
            )
        )
    lines.extend(["", "## 総合比較", ""])
    lines.append("| 条件 | 方式 | モデル | 実行 | 候補集合のF1 | 完全一致 | 必須の包含 | 単一正解 | 複数候補の妥当 | 追加質問の妥当 | 不要な質問 | 一つに決めた | 対象外の保留 | 処理エラー |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in conditions:
        summary = row.get("summary") or {}
        lines.append(
            "| {id} | {method} | {model} | {status} | {f1} | {exact} | {req} | {single} | {multi} | {clarify} | {unneeded} | {forced} | {abstain} | {err} |".format(
                id=condition_label(row),
                method=method_label(row),
                model=_model_name(row.get("model")),
                status=row["status"],
                f1=_num(summary.get("f1")),
                exact=_pct(summary.get("exact_rate")),
                req=_pct(summary.get("required_inclusion_rate")),
                single=_pct(summary.get("single_accuracy")),
                multi=_pct(summary.get("multi_appropriate_rate")),
                clarify=_pct(summary.get("clarify_appropriate_rate")),
                unneeded=_pct(summary.get("unnecessary_question_rate")),
                forced=_pct(summary.get("forced_one_rate")),
                abstain=_pct(summary.get("abstain_appropriate_rate")),
                err=_pct(summary.get("error_rate")),
            )
        )
    lines.extend(["", "## カテゴリ別の候補集合F1", ""])
    lines.append("列名は条件番号、方式、モデルである。")
    lines.append("")
    categories = []
    for row in conditions:
        if row.get("summary"):
            categories = list((row["summary"].get("by_category") or {}).keys())
            break
    categories = _ordered_categories(categories)
    header = "| 依頼の種類 | " + " | ".join(condition_label(row) for row in conditions) + " |"
    lines.append(header)
    lines.append("|---|" + "|".join(["---"] * len(conditions)) + "|")
    for category in categories:
        cells = []
        for row in conditions:
            block = ((row.get("summary") or {}).get("by_category") or {}).get(category) or {}
            cells.append(_num(block.get("f1")) if row.get("summary") else "未実行")
        lines.append("| " + _category_name(category) + " | " + " | ".join(cells) + " |")
    lines.extend(["", "## 誤り分類", ""])
    lines.append("件数は自動規則で数えた。1件に複数の誤りが付くことがある。")
    lines.append("")
    lines.append("| 誤り | 意味 |")
    lines.append("|---|---|")
    for tag, meaning in ERROR_LABEL.items():
        lines.append(f"| {tag} | {meaning} |")
    lines.append("")
    tag_names = []
    for row in conditions:
        tags = (row.get("summary") or {}).get("error_tags") or {}
        for name in tags:
            if name not in tag_names:
                tag_names.append(name)
    if tag_names:
        lines.append("| 誤り | " + " | ".join(condition_label(row) for row in conditions) + " |")
        lines.append("|---|" + "|".join(["---"] * len(conditions)) + "|")
        for tag in tag_names:
            cells = []
            for row in conditions:
                tags = (row.get("summary") or {}).get("error_tags") or {}
                cells.append(str(tags.get(tag, "未実行" if not row.get("summary") else 0)))
            lines.append("| " + tag + " | " + " | ".join(cells) + " |")
    lines.extend(["", "## 安定性", ""])
    stability = manifest.get("stability")
    if not stability:
        lines.append("複数回実行の結果は、このレポート生成時点では未実施。")
    else:
        lines.append(f"- 対象ケース数: {stability.get('n_cases')}")
        lines.append(f"- 繰り返し回数: {stability.get('n_runs')}")
        lines.append(f"- 候補集合の平均ジャッカード: {_num(stability.get('mean_jaccard'))}")
        lines.append(f"- 追加質問の有無が一致した割合: {_pct(stability.get('clarification_agreement_rate'))}")
    lines.extend(["", "## 制約", ""])
    for item in manifest.get("limitations") or []:
        if "料金" in item or "トークン" in item:
            continue
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)
