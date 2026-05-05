"""explainer.py — Raisons lisibles du score. Fusionne : score_explainer"""
from __future__ import annotations

from backend.engine.config import (
    EXPLAINER_HI_NUTRITION,     EXPLAINER_LO_NUTRITION,
    EXPLAINER_HI_AUTHENTICITY,
    EXPLAINER_HI_ACCESSIBILITY, EXPLAINER_LO_ACCESSIBILITY,
    EXPLAINER_HI_COST,          EXPLAINER_LO_COST,
    EXPLAINER_HI_EASE,          EXPLAINER_LO_EASE,
    EXPLAINER_HI_CARBON,        EXPLAINER_LO_CARBON,
    EXPLAINER_HI_FLAVOR,
)

_DIM_RULES = [
    {"dim": "nutrition",     "hi": EXPLAINER_HI_NUTRITION,     "pos": "riche_en_nutriments",       "lo": EXPLAINER_LO_NUTRITION,     "neg": "valeur_nutritive_limitée"},
    {"dim": "authenticity",  "hi": EXPLAINER_HI_AUTHENTICITY,  "pos": "recette_authentique",       "lo": None,                       "neg": None},
    {"dim": "accessibility", "hi": EXPLAINER_HI_ACCESSIBILITY, "pos": "ingrédients_accessibles",   "lo": EXPLAINER_LO_ACCESSIBILITY, "neg": "ingrédients_difficiles_à_trouver"},
    {"dim": "cost",          "hi": EXPLAINER_HI_COST,          "pos": "budget_économique",         "lo": EXPLAINER_LO_COST,          "neg": "recette_coûteuse"},
    {"dim": "ease",          "hi": EXPLAINER_HI_EASE,          "pos": "recette_simple",            "lo": EXPLAINER_LO_EASE,          "neg": "recette_technique"},
    {"dim": "carbon",        "hi": EXPLAINER_HI_CARBON,        "pos": "faible_empreinte_carbone",  "lo": EXPLAINER_LO_CARBON,        "neg": None},
    {"dim": "flavor",        "hi": EXPLAINER_HI_FLAVOR,        "pos": "profil_gustatif_équilibré", "lo": None,                       "neg": None},
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
