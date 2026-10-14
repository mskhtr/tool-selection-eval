# ツール選択方式の比較レポート

採用方式は決めていない。表は実測の集計である。

## 実行条件

- 実行日時: 2026-10-14T14:34:39.520738+00:00
- テスト件数: 150
- 主カテゴリ内訳: `{"ambiguous": 23, "insufficient": 19, "clear": 28, "implicit": 18, "colloquial": 21, "multi": 15, "out_of_scope": 20, "keyword_trap": 6}`
- 正解ラベル: 実装者1名が、モデル出力を見る前に付与した。複数人の独立ラベルと不一致解消は行っていない。
- モデル: Sol `gpt-5.6-sol-medium`、Terra `gpt-5.6-terra-medium`、Luna `gpt-5.6-luna-medium`。推論設定はモデルIDの medium。温度は指定できない。
- 指示書の Astra は、実行指示が Sol / Terra / Luna だったため未実行。
- 料金とトークン数は、この実行経路では取得できない。未取得のまま空欄にする。
- 呼び出しは Cursor のサブエージェントであり、ツール無しの Chat Completions API ではない。
- グラフは LangGraph。解析ツールの実行機能は評価グラフに繋いでいない。

### 成果物ハッシュ

- catalog: `989ca1465ee8d7e12cd5d008e3d5804303a12d171dda569e304605378afcdfd7`
- cases: `2e927f2203682177122044171f1f8ecf1efe4e48ae132e9167ef385de66ff84a`
- method_b: `0c7469ca39128f3f60837bbebb2df34c4dd0b845811c065df6faf0a155352f39`
- method_c: `1ff1d6ce830d56ee123413af8cffe1075a6ef794dee6ee79db141e42ba2d8eae`
- prompt_a: `547d10e85cb7f3d2b4cfd6aa50822565c2758ff1bb518446eed6b9f66f7c543f`
- prompt_c: `5723396ec78f959038fed8d28552ada1d53a365d81d74f2b503b8ea4052f040c`
- gold_module: `a5c174f3be5f83cdbfe03f57e6c66833b5ef1392df2c74253924f607e083b84e`

## 総合比較

| 条件 | 方式 | モデル | 実行 | F1 | 完全一致 | 必須候補の包含 | 単一正解 | 複数候補の妥当 | 追加質問の妥当 | 不要な質問 | 一つに決めた | 対象外の保留 | エラー |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | A | sol | 一部実行 125/150 | 0.887 | 82.4% | 85.7% | 92.3% | 68.5% | 85.2% | 3.1% | 7.7% | 100.0% | 0.0% |
| A2 | A | terra | 実行済み | 0.795 | 75.3% | 69.8% | 88.5% | 47.3% | 65.1% | 4.7% | 12.5% | 95.3% | 0.0% |
| A3 | A | luna | 実行済み | 0.890 | 81.3% | 82.1% | 96.2% | 56.4% | 70.9% | 0.0% | 17.5% | 97.7% | 0.0% |
| B1 | B | なし | 実行済み | 0.912 | 85.3% | 84.9% | 88.5% | 70.9% | 97.7% | 10.9% | 2.5% | 100.0% | 0.0% |
| C1 | C | sol | 一部実行 100/150 | 0.768 | 76.0% | 73.3% | 97.9% | 42.5% | 100.0% | 24.6% | 0.0% | 100.0% | 0.0% |
| C2 | C | terra | 一部実行 100/150 | 0.783 | 77.0% | 74.4% | 97.9% | 45.0% | 100.0% | 26.2% | 0.0% | 100.0% | 0.0% |
| C3 | C | luna | 一部実行 75/150 | 0.704 | 69.3% | 67.6% | 97.9% | 8.3% | 100.0% | 4.3% | 0.0% | 100.0% | 0.0% |

## カテゴリ別 F1

| カテゴリ | A1 | A2 | A3 | B1 | C1 | C2 | C3 |
|---|---|---|---|---|---|---|---|
| ambiguous | 0.673 | 0.394 | 0.654 | 0.778 | 0.108 | 0.165 | 0.075 |
| clear | 0.990 | 0.964 | 1.000 | 0.940 | 1.000 | 1.000 | 1.000 |
| colloquial | 0.931 | 0.900 | 0.978 | 0.939 | 0.857 | 0.875 | 0.846 |
| implicit | 0.766 | 0.405 | 0.691 | 0.673 | 0.933 | 0.667 | 0.600 |
| insufficient | 0.871 | 0.810 | 0.848 | 0.952 | 0.812 | 0.812 | 0.800 |
| keyword_trap | 1.000 | 1.000 | 1.000 | 1.000 | 未集計 | 未集計 | 未集計 |
| multi | 1.000 | 1.000 | 1.000 | 0.964 | 1.000 | 1.000 | 1.000 |
| out_of_scope | 1.000 | 0.923 | 0.962 | 1.000 | 未集計 | 未集計 | 未集計 |

## 誤り分類（規則による自動分類。人手確認ではない）

| 誤り | A1 | A2 | A3 | B1 | C1 | C2 | C3 |
|---|---|---|---|---|---|---|---|
| 過剰な意図補完 | 3 | 5 | 8 | 1 | 0 | 0 | 0 |
| 表層キーワード誤選択 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 候補漏れ | 15 | 33 | 19 | 16 | 24 | 23 | 23 |
| 過剰選択 | 0 | 0 | 4 | 2 | 0 | 0 | 0 |
| 不適切な追加質問 | 2 | 3 | 0 | 7 | 15 | 16 | 2 |
| 質問不足 | 3 | 7 | 8 | 2 | 0 | 0 | 0 |
| カタログ照合ミス | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| その他 | 4 | 0 | 2 | 1 | 0 | 0 | 0 |

## コスト

トークン数、API費用、1ケースのモデル遅延は未取得。取得できた壁時計時間があれば manifest の timing に書く。

## 安定性

複数回実行の結果は、このレポート生成時点では未実施。

## 制約

- LLMの実行経路は Cursor サブエージェント（gpt-5.6-sol-medium / gpt-5.6-terra-medium / gpt-5.6-luna-medium）。素の Chat Completions ではない。
- 温度は指定できない。推論設定はモデルIDに含まれる medium のみ。
- 料金とトークン数は未取得。
- Astra は実行していない。
- 正解ラベルは実装者1名で、複数人の独立ラベルではない。
- 誤り分類は規則による自動分類で、人手の再判定ではない。
- サブエージェントはファイルを読めるため、指示で正解ファイルを開かないよう制約した。開いていないことの証明はない。
- ユーザー確認後の選択は方式の精度に含めていない。
- 中断されたチャンクは再実行していない。応答が無いケースは指標の分母に入れていない。
- Luna の C方式 chunk_075 はケースIDではなくツールIDを並べた形式だったため採用していない。
- Terra の A方式 chunk_125 はオブジェクト区切りの余分な閉じ括弧を除いて読んだ。本文の選択内容は変えていない。
- 同一入力の繰り返し実行は未実施。

## 事例

### A1

#### 過剰な意図補完

- 141「冷熱を繰り返すとはんだが持たない気がするので見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=['solder_life_prediction'] 質問=False
- 143「ランダムに揺れそうな場所で使うので解析したい」 許容=['random_vibration', 'fatigue_life'] 予測=['random_vibration'] 質問=False
- 144「衝突安全の確認をしたい」 許容=['explicit_impact', 'static_strength'] 予測=['explicit_impact'] 質問=False

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 009「この部品が壊れないか見たい」 許容=['static_strength', 'fatigue_life', 'fracture_mechanics'] 予測=[] 質問=True
- 010「壊れないか確認したい」 許容=['static_strength', 'fatigue_life', 'fracture_mechanics'] 予測=[] 質問=True
- 011「このブラケット、破損しない？」 許容=['static_strength', 'fatigue_life', 'fracture_mechanics'] 予測=[] 質問=True

### A2

#### 過剰な意図補完

- 130「共振してそうで不安なので解析したい」 許容=['eigenvalue', 'frequency_response'] 予測=['eigenvalue'] 質問=False
- 131「この薄板、押し込むと潰れそうなので計算したい」 許容=['buckling', 'static_strength'] 予測=['buckling'] 質問=False
- 141「冷熱を繰り返すとはんだが持たない気がするので見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=['solder_life_prediction'] 質問=False

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 009「この部品が壊れないか見たい」 許容=['static_strength', 'fatigue_life', 'fracture_mechanics'] 予測=[] 質問=True
- 010「壊れないか確認したい」 許容=['static_strength', 'fatigue_life', 'fracture_mechanics'] 予測=[] 質問=True
- 011「このブラケット、破損しない？」 許容=['static_strength', 'fatigue_life', 'fracture_mechanics'] 予測=[] 質問=True

### A3

#### 過剰な意図補完

- 019「繰り返し荷重の疲労寿命を予測して」 許容=['fatigue_life'] 予測=['fatigue_life'] 質問=False
- 126「夏場の車内ではんだがもたないので見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=['solder_life_prediction'] 質問=False
- 131「この薄板、押し込むと潰れそうなので計算したい」 許容=['buckling', 'static_strength'] 予測=['buckling'] 質問=False

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 043「寿命を見たい」 許容=['solder_life_prediction', 'fatigue_life'] 予測=[] 質問=True
- 044「この部品の寿命が知りたい」 許容=['solder_life_prediction', 'fatigue_life'] 予測=[] 質問=True
- 045「亀裂が心配なので見たい」 許容=['solder_crack_propagation', 'fracture_mechanics'] 予測=[] 質問=True

### B1

#### 過剰な意図補完

- 050「衝撃と振動のどちらで見るべきかも含めて、この部品を評価したい」 許容=['explicit_impact', 'eigenvalue', 'frequency_response', 'random_vibration'] 予測=['explicit_impact'] 質問=False

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 011「このブラケット、破損しない？」 許容=['static_strength', 'fatigue_life', 'fracture_mechanics'] 予測=[] 質問=True
- 012「強度的に持つか見てほしい」 許容=['static_strength', 'fatigue_life', 'fracture_mechanics'] 予測=['static_strength'] 質問=True
- 050「衝撃と振動のどちらで見るべきかも含めて、この部品を評価したい」 許容=['explicit_impact', 'eigenvalue', 'frequency_response', 'random_vibration'] 予測=['explicit_impact'] 質問=False

### C1

#### 過剰な意図補完

該当なし。

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 001「はんだのシミュレーションをしたい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 002「はんだ周りをシミュレーションで見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 003「ソルダの解析をお願いします」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True

### C2

#### 過剰な意図補完

該当なし。

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 001「はんだのシミュレーションをしたい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 002「はんだ周りをシミュレーションで見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 003「ソルダの解析をお願いします」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True

### C3

#### 過剰な意図補完

該当なし。

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 001「はんだのシミュレーションをしたい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 002「はんだ周りをシミュレーションで見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 003「ソルダの解析をお願いします」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True

