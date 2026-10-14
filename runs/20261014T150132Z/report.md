# ツール選択方式の比較レポート

採用方式は決めていない。表は実測の集計である。

## 実行条件

- 実行日時: 2026-10-14T15:01:34.333332+00:00
- テスト件数: 150
- 主カテゴリ内訳: `{"ambiguous": 23, "insufficient": 19, "clear": 28, "implicit": 18, "colloquial": 21, "multi": 15, "out_of_scope": 20, "keyword_trap": 6}`
- 正解ラベル: 実装者1名が、モデル出力を見る前に付与した。複数人の独立ラベルと不一致解消は行っていない。
- モデルは Terra、Sol、Luna の順に並べ、方式ごとの番号もその順で付ける。
- モデルID: Terra `gpt-5.6-terra-medium`、Sol `gpt-5.6-sol-medium`、Luna `gpt-5.6-luna-medium`。推論設定はモデルIDの medium。温度は指定できない。
- 料金とトークン数は未取得。
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
| A1 | A | Terra | 実行済み | 0.795 | 75.3% | 69.8% | 88.5% | 47.3% | 65.1% | 4.7% | 12.5% | 95.3% | 0.0% |
| A2 | A | Sol | 実行済み | 0.905 | 84.7% | 84.9% | 92.3% | 67.3% | 67.4% | 3.1% | 7.5% | 100.0% | 0.0% |
| A3 | A | Luna | 実行済み | 0.890 | 81.3% | 82.1% | 96.2% | 56.4% | 70.9% | 0.0% | 17.5% | 97.7% | 0.0% |
| B1 | B | なし | 実行済み | 0.912 | 85.3% | 84.9% | 88.5% | 70.9% | 97.7% | 10.9% | 2.5% | 100.0% | 0.0% |
| C1 | C | Terra | 実行済み | 0.787 | 73.3% | 67.0% | 98.1% | 32.7% | 90.7% | 25.0% | 15.0% | 95.3% | 0.0% |
| C2 | C | Sol | 実行済み | 0.798 | 75.3% | 67.9% | 98.1% | 34.5% | 94.2% | 23.4% | 12.5% | 100.0% | 0.0% |
| C3 | C | Luna | 実行済み | 0.772 | 72.7% | 66.0% | 98.1% | 30.9% | 91.9% | 25.0% | 15.0% | 95.3% | 0.0% |

## カテゴリ別 F1

| カテゴリ | A1 | A2 | A3 | B1 | C1 | C2 | C3 |
|---|---|---|---|---|---|---|---|
| ambiguous | 0.394 | 0.677 | 0.654 | 0.778 | 0.288 | 0.277 | 0.233 |
| clear | 0.964 | 0.990 | 1.000 | 0.940 | 1.000 | 1.000 | 1.000 |
| colloquial | 0.900 | 0.933 | 0.978 | 0.939 | 0.883 | 0.867 | 0.867 |
| implicit | 0.405 | 0.771 | 0.691 | 0.673 | 0.516 | 0.612 | 0.516 |
| insufficient | 0.810 | 0.895 | 0.848 | 0.952 | 0.857 | 0.857 | 0.857 |
| keyword_trap | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| multi | 1.000 | 1.000 | 1.000 | 0.964 | 1.000 | 1.000 | 1.000 |
| out_of_scope | 0.923 | 1.000 | 0.962 | 1.000 | 0.923 | 1.000 | 0.923 |

## 誤り分類（規則による自動分類。人手確認ではない）

| 誤り | A1 | A2 | A3 | B1 | C1 | C2 | C3 |
|---|---|---|---|---|---|---|---|
| 過剰な意図補完 | 5 | 3 | 8 | 1 | 6 | 5 | 6 |
| 表層キーワード誤選択 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 候補漏れ | 33 | 16 | 19 | 16 | 36 | 35 | 37 |
| 過剰選択 | 0 | 0 | 4 | 2 | 0 | 0 | 0 |
| 不適切な追加質問 | 3 | 2 | 0 | 7 | 16 | 15 | 16 |
| 質問不足 | 7 | 3 | 8 | 2 | 8 | 5 | 7 |
| カタログ照合ミス | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| その他 | 0 | 4 | 2 | 1 | 0 | 0 | 2 |

## コスト

トークン数、API費用、1ケースのモデル遅延は未取得。取得できた壁時計時間があれば manifest の timing に書く。

## 安定性

複数回実行の結果は、このレポート生成時点では未実施。

## 制約

- 温度は指定できない。推論設定はモデルIDに含まれる medium のみ。
- 料金とトークン数は未取得。
- 正解ラベルは実装者1名で、複数人の独立ラベルではない。
- 誤り分類は規則による自動分類で、人手の再判定ではない。
- ユーザー確認後の選択は方式の精度に含めていない。
- 一度中断したチャンクは、不足分の再実行指示のあとで実行した。
- Luna の C方式 chunk_075 は、ツールIDをケースIDにしていた初回出力を捨て、再実行の結果を使った。
- Terra の A方式 chunk_125 はオブジェクト区切りの余分な閉じ括弧を除いて読んだ。本文の選択内容は変えていない。
- 同一入力の繰り返し実行は未実施。

## 事例

### A1

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

### A2

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

- 130「共振してそうで不安なので解析したい」 許容=['eigenvalue', 'frequency_response'] 予測=['eigenvalue'] 質問=False
- 131「この薄板、押し込むと潰れそうなので計算したい」 許容=['buckling', 'static_strength'] 予測=['buckling'] 質問=False
- 134「はんだを見れば十分でしょ、割れの話だから解析して」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=['solder_crack_propagation'] 質問=False

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 001「はんだのシミュレーションをしたい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 002「はんだ周りをシミュレーションで見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 003「ソルダの解析をお願いします」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True

### C2

#### 過剰な意図補完

- 131「この薄板、押し込むと潰れそうなので計算したい」 許容=['buckling', 'static_strength'] 予測=['buckling'] 質問=False
- 134「はんだを見れば十分でしょ、割れの話だから解析して」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=['solder_crack_propagation'] 質問=False
- 141「冷熱を繰り返すとはんだが持たない気がするので見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=['solder_life_prediction'] 質問=False

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 001「はんだのシミュレーションをしたい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 002「はんだ周りをシミュレーションで見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 003「ソルダの解析をお願いします」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True

### C3

#### 過剰な意図補完

- 126「夏場の車内ではんだがもたないので見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=['solder_life_prediction'] 質問=False
- 131「この薄板、押し込むと潰れそうなので計算したい」 許容=['buckling', 'static_strength'] 予測=['buckling'] 質問=False
- 134「はんだを見れば十分でしょ、割れの話だから解析して」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=['solder_crack_propagation'] 質問=False

#### 表層キーワード誤選択

該当なし。

#### 候補漏れ

- 001「はんだのシミュレーションをしたい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 002「はんだ周りをシミュレーションで見たい」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True
- 003「ソルダの解析をお願いします」 許容=['solder_crack_propagation', 'solder_life_prediction'] 予測=[] 質問=True

