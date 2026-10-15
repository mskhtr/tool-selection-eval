"""正解ラベル。モデルを実行する前に確定する。複数人の独立ラベルではない。"""

from __future__ import annotations

SOLDER = ["solder_crack_propagation", "solder_life_prediction"]
LIFE = ["solder_life_prediction", "fatigue_life"]
CRACK = ["solder_crack_propagation"]
SOLDER_LIFE = ["solder_life_prediction"]
FATIGUE = ["fatigue_life"]


def _case(
    case_id: str,
    primary: str,
    categories: list[str],
    group: str,
    text: str,
    acceptable: list[str],
    required: list[str],
    multiple: bool,
    clarify: bool,
    applicable: str,
    needed: list[str],
    severity: str,
    reason: str,
    stability: bool = False,
) -> dict:
    return {
        "id": case_id,
        "primary": primary,
        "categories": categories,
        "group": group,
        "text": text,
        "acceptable": acceptable,
        "required": required,
        "multiple": multiple,
        "clarify": clarify,
        "applicable": applicable,
        "needed": needed,
        "severity": severity,
        "reason": reason,
        "stability": stability,
    }


def _one(tool: str) -> list[str]:
    return [tool]


CASES: list[dict] = [
    _case("001", "clear", ["clear"], "crack_clear", "はんだ接合の亀裂が温度サイクルでどこまで進むかシミュレーションしたい", CRACK, CRACK, False, False, "yes", [], "medium", "はんだの亀裂がどこまで進むかが進展シミュレーションの目的である。", True),
    _case("002", "clear", ["clear"], "crack_clear", "はんだクラックの進展量をサイクルごとに計算したい", CRACK, CRACK, False, False, "yes", [], "medium", "はんだクラックの進展量を求めている。"),
    _case("003", "clear", ["clear"], "solder_life_clear", "はんだ接合の熱疲労寿命を計算したい", SOLDER_LIFE, SOLDER_LIFE, False, False, "yes", [], "medium", "はんだ接合の熱疲労寿命は寿命予測を指す。", True),
    _case("004", "clear", ["clear"], "solder_life_clear", "BGAはんだが温度サイクル何回で寿命に達するか予測したい", SOLDER_LIFE, SOLDER_LIFE, False, False, "yes", [], "medium", "はんだが何回で寿命に達するかが明示されている。"),
    _case("005", "clear", ["clear"], "fatigue_clear", "鋼製アームに繰り返し曲げがかかるので、S-N曲線で疲労寿命を計算したい", FATIGUE, FATIGUE, False, False, "yes", [], "high", "金属のS-N疲労寿命であり、はんだ寿命ではない。", True),
    _case("006", "clear", ["clear"], "fatigue_clear", "金属部品の高サイクル疲労寿命をS-Nで出したい", FATIGUE, FATIGUE, False, False, "yes", [], "high", "高サイクル疲労とS-Nが疲労寿命予測を指す。"),
    _case("007", "orthography", ["orthography", "ambiguous"], "solder_script", "半田のシミュレーションをしたい", SOLDER, SOLDER, True, True, "yes", ["亀裂進展か寿命予測か"], "medium", "半田ははんだの表記ゆれで、目的はまだ決まらない。"),
    _case("008", "orthography", ["orthography", "ambiguous"], "solder_script", "ハンダのシミュレーションをしたい", SOLDER, SOLDER, True, True, "yes", ["亀裂進展か寿命予測か"], "medium", "ハンダははんだの表記ゆれで、目的はまだ決まらない。", True),
    _case("009", "orthography", ["orthography", "clear"], "solder_life_script", "半田接合の熱疲労寿命を計算したい", SOLDER_LIFE, SOLDER_LIFE, False, False, "yes", [], "medium", "半田ははんだの表記ゆれで、熱疲労寿命は寿命予測を指す。"),
    _case("010", "orthography", ["orthography", "clear"], "solder_life_script", "ハンダの寿命を計算して", SOLDER_LIFE, SOLDER_LIFE, False, False, "yes", [], "medium", "ハンダの寿命ははんだ寿命予測を指す。"),
    _case("011", "orthography", ["orthography", "clear"], "crack_script", "半田のき裂がどこまで進むかシミュレーションしたい", CRACK, CRACK, False, False, "yes", [], "medium", "半田とき裂は、はんだと亀裂の表記ゆれである。進み方が目的である。"),
    _case("012", "orthography", ["orthography", "clear"], "crack_script", "ハンダの亀裂進展を計算したい", CRACK, CRACK, False, False, "yes", [], "medium", "ハンダははんだの表記ゆれで、亀裂進展が目的である。"),
    _case("013", "colloquial", ["colloquial", "ambiguous"], "solder_sim", "ソルダの解析をお願いします", SOLDER, SOLDER, True, True, "yes", ["亀裂進展か寿命予測か"], "medium", "ソルダははんだの俗称で、目的は決まらない。"),
    _case("014", "colloquial", ["colloquial", "clear"], "crack_colloquial", "はんだのクラックが進むやつ回して", CRACK, CRACK, False, False, "yes", [], "medium", "クラックが進むは進展シミュレーションの口語である。"),
    _case("015", "colloquial", ["colloquial", "clear"], "crack_colloquial", "ソルダのクラックグロース見たい", CRACK, CRACK, False, False, "yes", [], "medium", "ソルダのクラックグロースははんだ亀裂進展の俗称である。"),
    _case("016", "colloquial", ["colloquial", "clear"], "fatigue_colloquial", "疲労回して。S-Nで", FATIGUE, FATIGUE, False, False, "yes", [], "high", "疲労をS-Nで回すは金属の疲労寿命予測である。"),
    _case("017", "ambiguous", ["ambiguous"], "solder_sim", "はんだのシミュレーションをしたい", SOLDER, SOLDER, True, True, "yes", ["亀裂進展か寿命予測か"], "medium", "はんだという対象だけでは目的が決まらない。", True),
    _case("018", "ambiguous", ["ambiguous"], "solder_sim", "はんだ周りをシミュレーションで見たい", SOLDER, SOLDER, True, True, "yes", ["亀裂進展か寿命予測か"], "medium", "シミュレーションとだけあり、進み方と寿命回数のどちらでもない。"),
    _case("019", "ambiguous", ["ambiguous"], "life_word", "寿命を見たい", LIFE, LIFE, True, True, "yes", ["はんだの寿命か、金属の疲労寿命か"], "medium", "寿命だけではんだ寿命と金属疲労の両方があり得る。"),
    _case("020", "ambiguous", ["ambiguous"], "life_word", "この部品の寿命が知りたい", LIFE, LIFE, True, True, "yes", ["はんだの寿命か、金属の疲労寿命か"], "medium", "部品の寿命とだけあり、材料が書かれていない。"),
    _case("021", "multi", ["multi", "clear"], "pair_solder", "はんだの寿命予測と亀裂進展シミュレーションを両方やって", SOLDER, SOLDER, True, False, "yes", [], "medium", "寿命予測と亀裂進展の両方を指定している。"),
    _case("022", "multi", ["multi", "clear"], "pair_solder", "温度サイクルの寿命と、亀裂がどう伸びるかの両方をはんだで見たい", SOLDER, SOLDER, True, False, "yes", [], "medium", "はんだについて寿命と亀裂の伸びの両方を見たいと書かれている。"),
    _case("023", "multi", ["multi", "clear"], "pair_lives", "金属の疲労寿命と、はんだの熱疲労寿命をそれぞれ計算したい", LIFE, LIFE, True, False, "yes", [], "medium", "二つの寿命予測をそれぞれ計算すると書かれている。"),
    _case("024", "implicit", ["implicit", "ambiguous"], "solder_worry", "はんだが割れそうなので見たい", SOLDER, SOLDER, True, True, "yes", ["進展経路か、寿命回数か"], "medium", "割れそうからはんだの不具合は読み取れるが、進展と寿命のどちらを出すかは書かれていない。"),
    _case("025", "implicit", ["implicit", "ambiguous"], "solder_worry", "冷熱を繰り返すとはんだが持たない気がするので見たい", SOLDER, SOLDER, True, True, "yes", ["寿命回数か、亀裂進展か"], "medium", "持たないから寿命と決めやすいが、亀裂の進み方も候補に残る。"),
    _case("026", "implicit", ["implicit", "clear"], "fatigue_worry", "鋼が繰り返しで折れそうなので寿命を見たい", FATIGUE, FATIGUE, False, False, "yes", [], "medium", "鋼の繰り返しと寿命が見えており、金属の疲労寿命を指す。"),
    _case("027", "insufficient", ["insufficient"], "vague", "いつものをお願い", [], [], False, True, "unknown", ["どの解析か"], "medium", "いつもの対象が書かれていない。"),
    _case("028", "insufficient", ["insufficient"], "vague", "例のやつやっといて", [], [], False, True, "unknown", ["どの解析か"], "medium", "例のやつが指示の中に無い。"),
    _case("029", "insufficient", ["insufficient"], "too_little", "いい感じに見て", [], [], False, True, "unknown", ["見たい現象"], "low", "いい感じには評価目的が無い。"),
    _case("030", "keyword_trap", ["keyword_trap", "out_of_scope"], "chemistry", "はんだの成分を化学分析したい", [], [], False, True, "no", [], "low", "化学分析であり、はんだの力学シミュレーションではない。"),
    _case("031", "keyword_trap", ["keyword_trap", "out_of_scope"], "files", "はんだ亀裂の写真をフォルダに整理したい", [], [], False, True, "no", [], "low", "写真整理であり、亀裂進展シミュレーションではない。"),
    _case("032", "keyword_trap", ["keyword_trap", "out_of_scope"], "schedule", "寿命の短い開発日程を引き直したい", [], [], False, True, "no", [], "low", "開発日程の話で、寿命解析ではない。"),
    _case("033", "out_of_scope", ["out_of_scope"], "missing_tool", "ブラケットの固有振動数を計算したい", [], [], False, True, "no", [], "medium", "固有値解析はこのカタログに無い。"),
    _case("034", "out_of_scope", ["out_of_scope"], "missing_tool", "配管の圧力損失を流体で計算したい", [], [], False, True, "no", [], "medium", "流体解析はこのカタログに無い。"),
    _case("035", "out_of_scope", ["out_of_scope", "keyword_trap"], "procedure", "はんだ付けの作業手順書を作って", [], [], False, True, "no", [], "low", "作業手順書の作成であり、はんだのシミュレーションではない。"),
    _case("036", "orthography", ["orthography", "clear"], "fatigue_script", "金属の疲労寿命をＳ－Ｎで計算したい", FATIGUE, FATIGUE, False, False, "yes", [], "medium", "全角のＳ－ＮはS-Nの表記ゆれで、金属の疲労寿命を指す。"),
]


LABELING = {
    "labeler_count": 1,
    "independent_adjudication": False,
    "note": "実装者1名が、モデル出力を見る前に付与した。複数人の独立ラベルと不一致解消は行っていない。",
    "frozen_before_model_runs": True,
}
