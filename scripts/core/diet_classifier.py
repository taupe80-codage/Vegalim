import re

def _compile(patterns):
    return [re.compile(p, re.IGNORECASE) for p in patterns]

def classify_ingredient(name: str, ontology: dict):
    name = (name or "").lower().strip()

    # 0) anti faux positifs
    for fp in ontology.get("anti_false_positive", []):
        if fp in name:
            return {"label": "vegetarian", "confidence": 0.9, "reason": ["anti_false_positive"]}

    # 1) safe exact
    if name in ontology.get("safe_exact", []):
        return {"label": "vegetarian", "confidence": 1.0, "reason": ["safe_exact"]}

    # 2) safe pattern
    for pat in _compile(ontology.get("safe_pattern", [])):
        if pat.search(name):
            return {"label": "vegetarian", "confidence": 0.95, "reason": ["safe_pattern"]}

    # 3) non-veg strict
    for w in ontology.get("non_veg_strict", []):
        if w in name:
            return {"label": "non_vegetarian", "confidence": 1.0, "reason": ["non_veg_strict"]}

    # 4) non-veg pattern
    for pat in _compile(ontology.get("non_veg_pattern", [])):
        if pat.search(name):
            return {"label": "non_vegetarian", "confidence": 0.9, "reason": ["non_veg_pattern"]}

    # 5) ambiguous
    for w in ontology.get("ambiguous", []):
        if w in name:
            return {"label": "uncertain", "confidence": 0.5, "reason": ["ambiguous"]}

    # 6) default
    return {"label": "vegetarian", "confidence": 0.7, "reason": ["default"]}