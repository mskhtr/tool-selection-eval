from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from toolselect.paths import CATALOG_PATH
from toolselect.textutil import normalize_text

LLM_FIELDS = (
    "id",
    "name",
    "domain",
    "target",
    "purpose",
    "method",
    "aliases",
    "inputs",
    "input_conditions",
    "constraints",
    "outputs",
    "differences",
    "purpose_signals",
)
RULE_ONLY_FIELDS = ("rule_keywords",)


@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    domain: str
    target: str
    purpose: str
    method: str
    aliases: tuple[str, ...]
    inputs: tuple[str, ...]
    input_conditions: tuple[str, ...]
    constraints: tuple[str, ...]
    outputs: tuple[str, ...]
    differences: str
    purpose_signals: tuple[str, ...]
    rule_keywords: tuple[str, ...]

    def name_forms(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


@dataclass(frozen=True)
class Catalog:
    version: str
    tools: tuple[Tool, ...]

    def ids(self) -> set[str]:
        return {tool.id for tool in self.tools}

    def by_id(self) -> dict[str, Tool]:
        return {tool.id: tool for tool in self.tools}

    def llm_text(self) -> str:
        blocks: list[str] = []
        for tool in self.tools:
            aliases = "、".join(tool.aliases) if tool.aliases else "なし"
            signals = "、".join(tool.purpose_signals) if tool.purpose_signals else "なし"
            blocks.append(
                "\n".join(
                    [
                        f"ID: {tool.id}",
                        f"正式名称: {tool.name}",
                        f"分野: {tool.domain}",
                        f"解析対象: {tool.target}",
                        f"解析目的: {tool.purpose}",
                        f"解析手法: {tool.method}",
                        f"別名: {aliases}",
                        f"入力データ: {'、'.join(tool.inputs)}",
                        f"必要な入力条件: {'、'.join(tool.input_conditions)}",
                        f"制約: {'、'.join(tool.constraints)}",
                        f"出力: {'、'.join(tool.outputs)}",
                        f"他ツールとの違い: {tool.differences}",
                        f"目的の手がかり: {signals}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    def view_diff(self) -> dict[str, list[str]]:
        return {
            "llm_fields": list(LLM_FIELDS),
            "rule_only_fields": list(RULE_ONLY_FIELDS),
            "rule_only_config": [
                "config/method_b.yaml の family triggers, request_substrings, hard_meta_substrings, combination_substrings"
            ],
        }

    def resolve_mention(self, mention: str) -> str | None:
        key = normalize_text(mention)
        if not key:
            return None
        if key in self.ids() or mention in self.ids():
            return mention if mention in self.ids() else key
        for tool in self.tools:
            if key == tool.id:
                return tool.id
            for form in tool.name_forms():
                if key == normalize_text(form):
                    return tool.id
        return None


def _as_tuple(value) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(str(item) for item in value)


@cache
def load_catalog(path: str | None = None) -> Catalog:
    catalog_path = CATALOG_PATH if path is None else Path(path)
    data = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    tools = []
    for row in data["tools"]:
        tools.append(
            Tool(
                id=row["id"],
                name=row["name"],
                domain=row["domain"],
                target=row["target"],
                purpose=row["purpose"],
                method=row["method"],
                aliases=_as_tuple(row.get("aliases")),
                inputs=_as_tuple(row.get("inputs")),
                input_conditions=_as_tuple(row.get("input_conditions")),
                constraints=_as_tuple(row.get("constraints")),
                outputs=_as_tuple(row.get("outputs")),
                differences=row.get("differences") or "",
                purpose_signals=_as_tuple(row.get("purpose_signals")),
                rule_keywords=_as_tuple(row.get("rule_keywords")),
            )
        )
    return Catalog(version=str(data.get("version")), tools=tuple(tools))
