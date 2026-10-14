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
INTELLIGENCE_RANK = {"terra": 0, "sol": 1, "luna": 2}
DISPLAY_NAME = {"sol": "Sol", "terra": "Terra", "luna": "Luna"}
METHOD_ORDER = {"A": 0, "B": 1, "C": 2}
METHOD_LABEL = {"A": "直接選択", "B": "辞書・規則", "C": "擬似jev"}
CATEGORY_LABEL = {
    "clear": "明確（目的が書いてある）",
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
    "過剰選択": "許容されないツールを多く足した。",
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
            INTELLIGENCE_RANK.get(row.get("model") or "", 9),
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


def _condition_body(row: dict) -> str:
    model = _model_name(row.get("model"))
    if row["method"] == "A":
        return f"{model} が共有カタログを読み、候補・追加質問・保留を直接返す。複数候補を返してよい。"
    if row["method"] == "B":
        return "モデルは使わない。名称、目的の手がかり、系統、事務・説明表現の除外で候補を決める。得点は付けない。"
    if row["method"] == "C":
        return f"{model} が全ツールに適合度を付ける。別処理が ID をカタログで引き、得点の高さと差で候補を出すか質問するかを決める。適合度は確率ではない。"
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


def render_report(run_dir: Path) -> str:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    conditions = order_conditions(json.loads((run_dir / "comparison.json").read_text(encoding="utf-8")))
    lines = [
        "# ツール選択方式の比較レポート",
        "",
        "## 結論",
        "",
        "### 総合",
        "",
        "- 結果: 最もよいのは **B1**（F1 0.912）。次点は A2（0.905）。追加質問の妥当さ 97.7%、一つに決めた割合 2.5% も7条件で最もよい。",
        "- 理由: 「はんだ」なら亀裂進展と寿命予測、「振動」なら固有値・周波数応答・ランダム振動、のように同じ系統のツールをまとめて残して質問する。",
        "",
        "### B1 の弱点",
        "",
        "- 結果: 不要な質問は 10.9%。目的が書いてある依頼の F1 は 0.940 で、A3 と擬似jev の 1.000 より低い。",
        "- 理由: 言い回しが登録文字列からずれると、同じ系統のツールを全部出して必ず質問する。短い別名が別ツールに掛かり、候補が広がる。ラベルと規則は同一人物が書いている。",
        "",
        "### LLM を使う条件",
        "",
        "- 結果: 最も近いのは **A2**（F1 0.905、不要な質問 3.1%）。A3 は 0.890 で、1件に絞った割合が 17.5%。",
        "- 理由: A2 は曖昧な依頼でも候補を残してから質問する。A3 は迷うと質問せず1件に絞る。",
        "",
        "### 擬似jev",
        "",
        "- 結果: 曖昧な依頼の F1 は 0.233〜0.288。総合は 0.772〜0.798。",
        "- 理由: 書いていない目的は点を上げず、50点未満は候補から外す。質問だけが残り、集合の得点が 0 になる。",
        "",
        "### Terra の直接選択",
        "",
        "- 結果: A1 の F1 は 0.795。曖昧な依頼と暗黙の前提で候補が空になる。",
        "- 理由: 質問の分かれ方は正解に沿うことが多い。候補欄が空なので、その件は 0 点になる。",
        "",
        "### 口語・俗称・略語",
        "",
        "- 結果: 最も強いのは **A3**（F1 0.978）。B1 は 0.939、A2 は 0.933。擬似jev は 0.867〜0.883。",
        "- 理由: モーダルや FRF のように目的が書いてある俗称は、どの条件もほぼ解ける。差は「破損しない？」「強度的に持つか」の2件で、A3 だけが静強度・疲労・破壊を残した。",
        "",
        "### 採用",
        "",
        "- 結果: 採用するなら **B1**。目的が書いてある依頼だけなら A2 か A3 でも足りる。擬似jev と A1 は、対象だけが書いてある依頼には使わない。",
        "- 理由: 擬似jev と A1 は、質問を出しても候補が空になり、集合の F1 が 0 になる。",
        "",
        "## 実行条件",
        "",
        f"- 実行日時: {_date_only(manifest.get('created_at'))}",
        f"- テスト件数: {manifest.get('n_cases')}",
        f"- 主カテゴリ内訳: {_category_counts(manifest.get('primary_counts') or {})}",
        f"- 正解ラベル: {manifest.get('labeling', {}).get('note')}",
        "- 条件番号は方式ごとの連番で、モデルは Terra、Sol、Luna の順に付ける。",
        "- モデルID: Terra `gpt-5.6-terra-medium`、Sol `gpt-5.6-sol-medium`、Luna `gpt-5.6-luna-medium`。推論設定はモデルIDの medium。温度は指定できない。",
        "- グラフは LangGraph。解析ツールの実行機能は評価グラフに繋いでいない。",
        "",
        "### 成果物ハッシュ",
        "",
    ]
    for name, digest in (manifest.get("hashes") or {}).items():
        lines.append(f"- {name}: `{digest}`")
    lines.extend(
        [
            "",
            "## 比較条件",
            "",
            "番号は方式ごとの連番である。同じ番号でも方式が違えば別条件である。A1 は Terra の直接選択、C1 は Terra の擬似jev であり、同じ実験ではない。",
            "",
            "- 直接選択: LLM がカタログと依頼文を読み、候補、追加質問、保留を一度に返す。書いていない目的は補わない。",
            "- 辞書・規則: LLM を使わない。カタログの名称、目的の手がかり、系統、事務・説明表現の除外で候補を決める。どの規則が当たったかを残す。得点は付けない。",
            "- 擬似jev: LLM がカタログの全ツールに適合度を付ける。別処理がツール ID をカタログから引き、得点の高さと差で、候補を出すか追加質問するかを決める。適合度は校正済みの確率ではない。",
            "",
            "| 条件 | 方式 | モデル | この条件でやること |",
            "|---|---|---|---|",
        ]
    )
    for row in conditions:
        lines.append(
            f"| {row['id']} | {METHOD_LABEL.get(row['method'], row['method'])} | {_model_name(row.get('model'))} | {_condition_body(row)} |"
        )
    lines.extend(
        [
            "",
            "## 評価指標",
            "",
            "候補の正解は一つのツールに限らない。許容集合に入っていればそのツールは正解で、必須集合は必ず含めなければならない。質問すべきか、保留すべきかもラベルに含まれ、ユーザーが後から選んだ結果は精度に入れていない。",
            "",
            "### 候補集合のF1",
            "",
            "出したツールの集合が、出してよいツールの集合（許容集合）にどれだけ近いかを、依頼1件ごとに 0 から 1 で表した値である。表の数字は、その値を対象の依頼で平均したものである。150件全体の平均が総合の F1、種類ごとの平均がカテゴリ別の F1 である。",
            "",
            "1件の計算は、次の二つを組み合わせる。",
            "",
            "- 適合率は、出したツールのうち許容集合に入っていた割合である。余分なツールを足すと下がる。",
            "- 再現率は、許容集合のうち出せていた割合である。出すべきツールを落とすと下がる。",
            "- F1 は 2 × 適合率 × 再現率 ÷（適合率 + 再現率）である。どちらかが低いと、もう一方が高くても F1 は伸びない。",
            "",
            "例は次のとおりである。",
            "",
            "- 許容が疲労寿命予測だけで、それだけ出した。F1 は 1。",
            "- 許容がはんだ亀裂進展とはんだ寿命予測の2件で、1件だけ出した。適合率は 1、再現率は 0.5、F1 は 0.667。",
            "- 許容が1件で、その1件に加えて別のツールも出した。適合率は 0.5、再現率は 1、F1 は 0.667。",
            "- 許容があるのに候補が空、または許容が空なのに候補を出した。F1 は 0。",
            "- 許容も候補も空である。出さないのが正解で出していないので、F1 は 1。",
            "",
            "F1 が見ているのはツールの集合だけである。質問の有無は、下の表の「追加質問の妥当」と「不要な質問」で集計する。",
            "",
            "| 指標 | 意味 | 読み方 |",
            "|---|---|---|",
            "| 候補集合のF1 | 上の計算を依頼ごとに行い、平均する。1 に近いほど、出してよいツールに近い。 | 1 なら過不足なく一致。0.667 は、2件中1件だけ出すか、正解1件に余分を1件足した程度。 |",
            "| 完全一致 | 予測集合が許容集合とまったく同じだった割合。 | 高いほど、過不足なく一致している。 |",
            "| 必須の包含 | 必須ツールがすべて予測に入っていた割合。必須が空のケースは分母に入らない。 | 高いほど、落としてはいけないツールを残せている。 |",
            "| 単一正解 | 正解が1ツールのケースで、その1件だけを選べた割合。 | 高いほど、目的が一つの依頼を選べている。 |",
            "| 複数候補の妥当 | 複数候補が期待されるケースで、必須を含み、許容の範囲に収まり、2件以上出している割合。 | 高いほど、迷う依頼で候補を狭めすぎていない。 |",
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
            "候補集合の F1 が 0.85 以上を「良い」、0.80 以上 0.85 未満を「中間」、0.80 未満を「弱い」とした。この区切りは一覧を見やすくするためのもので、採用の基準ではない。",
            "",
            "| 順 | 条件 | 方式 | モデル | 候補集合のF1 | 判定 | 曖昧 | 暗黙の前提 | 明確 |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    ranked = sorted(
        conditions,
        key=lambda row: -1 if (row.get("summary") or {}).get("f1") is None else -float((row.get("summary") or {})["f1"]),
    )
    for index, row in enumerate(ranked, start=1):
        summary = row.get("summary") or {}
        lines.append(
            "| {index} | {id} | {method} | {model} | {f1} | {grade} | {ambiguous} | {implicit} | {clear} |".format(
                index=index,
                id=row["id"],
                method=METHOD_LABEL.get(row["method"], row["method"]),
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
                id=row["id"],
                method=METHOD_LABEL.get(row["method"], row["method"]),
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
                id=row["id"],
                method=METHOD_LABEL.get(row["method"], row["method"]),
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
    lines.append("列の A1 などは、上の比較条件と同じ番号である。")
    lines.append("")
    categories = []
    for row in conditions:
        if row.get("summary"):
            categories = list((row["summary"].get("by_category") or {}).keys())
            break
    categories = _ordered_categories(categories)
    header = "| 依頼の種類 | " + " | ".join(row["id"] for row in conditions) + " |"
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
        lines.append("| 誤り | " + " | ".join(row["id"] for row in conditions) + " |")
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
