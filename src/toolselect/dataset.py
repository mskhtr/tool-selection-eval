from __future__ import annotations

import hashlib
import json
from pathlib import Path

from toolselect.gold import CASES, LABELING
from toolselect.paths import CASES_PATH, CATALOG_PATH, METHOD_B_PATH, METHOD_C_PATH, PROMPT_A_PATH, PROMPT_C_PATH


def load_cases() -> list[dict]:
    return [dict(case) for case in CASES]


def labeling_note() -> dict:
    return dict(LABELING)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_cases_file(path: Path | None = None) -> Path:
    target = path or CASES_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"labeling": labeling_note(), "cases": load_cases()}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def artifact_hashes() -> dict[str, str]:
    write_cases_file()
    return {
        "catalog": sha256_file(CATALOG_PATH),
        "cases": sha256_file(CASES_PATH),
        "method_b": sha256_file(METHOD_B_PATH),
        "method_c": sha256_file(METHOD_C_PATH),
        "prompt_a": sha256_file(PROMPT_A_PATH),
        "prompt_c": sha256_file(PROMPT_C_PATH),
        "gold_module": sha256_text(Path(__file__).with_name("gold.py").read_text(encoding="utf-8")),
    }
