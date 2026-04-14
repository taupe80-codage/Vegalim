"""explainer.py — Raisons lisibles du score. Fusionne : score_explainer"""
from __future__ import annotations

_DIM_RULES = [
    {"dim": "nutrition",     "hi": 7.5, "pos": "riche_en_nutriments",       "lo": 4.0, "neg": "valeur_nutritive_limitée"},
    {"dim": "authenticity",  "hi": 7.0, "pos": "recette_authentique",       "lo": None,"neg": None},
    {"dim": "accessibility", "hi": 7.5, "pos": "ingrédients_accessibles",   "lo": 4.0, "neg": "ingrédients_difficiles_à_trouver"},
    {"dim": "cost",          "hi": 7.5, "pos": "budget_économique",         "lo": 4.0, "neg": "recette_coûteuse"},
    {"dim": "ease",          "hi": 7.5, "pos": "recette_simple",            "lo": 4.0, "neg": "recette_technique"},
    {"dim": "carbon",        "hi": 7.5, "pos": "faible_empreinte_carbone",  "lo": 4.0, "neg": None},
    {"dim": "flavor",        "hi": 7.0, "pos": "profil_gustatif_équilibré", "lo": None,"neg": None},
]

def explain(score_result: dict) -> list[str]:
    """Retourne les labels lisibles depuis un dict score_recipe()."""
    labels = []
    dims   = score_result.get("dims", score_result.get("details", score_result))
    for rule in _DIM_RULES:
        val = float(dims.get(rule["dim"], 0) or 0)
        if val >= rule["hi"] and rule["pos"]:
            labels.append(rule["pos"])
        elif rule["lo"] and val < rule["lo"] and rule["neg"]:
            labels.append(rule["neg"])
    for b in score_result.get("bonuses", []):
        lbl = b.get("label", "")
        if lbl:
            labels.append(lbl.replace(" ", "_").lower())
    return labels
