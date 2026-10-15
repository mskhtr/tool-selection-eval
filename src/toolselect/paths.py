from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "catalog" / "tools.yaml"
CASES_PATH = ROOT / "data" / "cases.json"
METHOD_B_PATH = ROOT / "config" / "method_b.yaml"
METHOD_C_PATH = ROOT / "config" / "method_c.yaml"
ONTOLOGY_PATH = ROOT / "config" / "ontology.yaml"
MODELS_PATH = ROOT / "config" / "models.yaml"
PROMPT_A_PATH = ROOT / "config" / "prompts" / "method_a.txt"
PROMPT_C_PATH = ROOT / "config" / "prompts" / "method_c.txt"
PROMPT_D_PATH = ROOT / "config" / "prompts" / "method_d.txt"
