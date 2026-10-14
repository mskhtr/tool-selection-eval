# ツール選択方式の比較

自然言語の依頼から解析ツールを選ぶ三方式を、同じカタログと同じ正解ラベルで比べる。採用方式は決めていない。

## 方式

- A: LangGraph でカタログと入力を LLM に渡し、ツールを直接選ばせる
- B: LLM を使わない。カタログの名称、目的の手がかり、系統、事務・説明表現の除外で候補を出す
- C: LangGraph で LLM が適合度を採点し、別モジュールがツール ID を辞書引きし、その後に順位と差で候補か追加質問かを決める

解析そのものは実行しない。確認グラフは、承認前の候補と承認後の選択を分けて持つ。

## モデル

実行に使うのは次の三つ。並びは Terra、Sol、Luna。

| 呼び名 | モデルID | 推論設定 |
|---|---|---|
| Terra | gpt-5.6-terra-medium | medium |
| Sol | gpt-5.6-sol-medium | medium |
| Luna | gpt-5.6-luna-medium | medium |

温度は指定できない。料金とトークン数はこの実行経路では取れないので、空のまま記録する。API キーは使っていない。

## 実行

```powershell
cd C:\Users\masaki\Documents\python-projects\20261014_tool-selection-eval
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m toolselect
```

`python -m toolselect` は B 方式だけを 150 件実行する。A と C は `runs/llm_responses/<sol|terra|luna>/<A|C>/chunk_*.json` にモデル応答を置いてから、次で集計する。

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m toolselect.assemble
```

応答が無い条件は、実行済みにしない。

## データ

- ツール定義: `catalog/tools.yaml`
- 正解ラベル: `src/toolselect/gold.py` と、そこから書き出す `data/cases.json`
- 人が読むレポートとテストセット: `docs/レポート.md`、`docs/テストセット.md`
- ラベルは 1 名がモデル実行前に付けた。複数人の独立ラベルではない
- B 方式の規則: `config/method_b.yaml`
- C 方式のしきい値: `config/method_c.yaml`
- プロンプト: `config/prompts/`

LLM に渡すカタログからは、`rule_keywords` と系統のトリガーを外している。
