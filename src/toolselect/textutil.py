from __future__ import annotations

import json
import re
import unicodedata


def normalize_text(text: str) -> str:
    """照合用に、全角半角・空白・句読点・『の』を畳む。"""
    folded = unicodedata.normalize("NFKC", text).lower()
    folded = folded.replace("の", "")
    folded = re.sub(r"[\s\u3000]+", "", folded)
    folded = re.sub(r"[、。，．,.!！?？・:：;；\"'「」『』（）()\[\]【】\-ー]", "", folded)
    return folded


def parse_json_payload(text: str) -> dict | list:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("空の応答")
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, flags=re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    start_obj = raw.find("{")
    start_arr = raw.find("[")
    starts = [index for index in (start_obj, start_arr) if index >= 0]
    if not starts:
        raise ValueError("JSONが見つからない")
    start = min(starts)
    end = max(raw.rfind("}"), raw.rfind("]"))
    if end < start:
        raise ValueError("JSONの終端が見つからない")
    return json.loads(raw[start : end + 1])
