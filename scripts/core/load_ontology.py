import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ONTO_PATH = BASE_DIR / "backend/data/nutrition/reference/non_veg_ontology_v2.json"

def load_ontology():
    if not ONTO_PATH.exists():
        raise FileNotFoundError(f"Ontology not found: {ONTO_PATH}")
    with open(ONTO_PATH, encoding="utf-8") as f:
        return json.load(f)