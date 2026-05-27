"""
explainer.py — Raisons lisibles du score CDC_03c.

Fusionne : score_explainer

API :
    ScoreLabel          → constantes nommées pour tous les labels
    explain(score_result) → list[str]

Utilisation recommandée pour les consommateurs :
    from backend.engine.score_engine.explainer import ScoreLabel
    if ScoreLabel.RICH_NUTRITION in recipe["score_reasons"]:
        ...

Cela évite les fautes de frappe silencieuses sur les chaînes magic.
L'API publique (list[str]) est inchangée — aucun consommateur existant à modifier.
"""
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


# ── Constantes nommées ────────────────────────────────────────────────────────
# Source de vérité unique pour tous les labels de score_reasons.
# Modifier un label ici suffit — pas de rechercher/remplacer dans la codebase.

class ScoreLabel:
    """Labels retournés par explain() dans score_reasons."""

    # Positifs
    RICH_NUTRITION     = "riche_en_nutriments"
    AUTHENTIC          = "recette_authentique"
    ACCESSIBLE         = "ingrédients_accessibles"
    BUDGET             = "budget_économique"
    SIMPLE             = "recette_simple"
    LOW_CARBON         = "faible_empreinte_carbone"
    BALANCED_FLAVOR    = "profil_gustatif_équilibré"

    # Négatifs
    LOW_NUTRITION      = "valeur_nutritive_limitée"
    HARD_TO_FIND       = "ingrédients_difficiles_à_trouver"
    EXPENSIVE          = "recette_coûteuse"
    TECHNICAL          = "recette_technique"

    @classmethod
    def all(cls) -> frozenset[str]:
        """Retourne l'ensemble de tous les labels connus."""
        return frozenset(
            v for k, v in vars(cls).items()
            if not k.startswith("_") and isinstance(v, str)
        )


# ── Règles par dimension ──────────────────────────────────────────────────────

_DIM_RULES = [
    {
        "dim": "nutrition",
        "hi": EXPLAINER_HI_NUTRITION,    "pos": ScoreLabel.RICH_NUTRITION,
        "lo": EXPLAINER_LO_NUTRITION,    "neg": ScoreLabel.LOW_NUTRITION,
    },
    {
        "dim": "authenticity",
        "hi": EXPLAINER_HI_AUTHENTICITY, "pos": ScoreLabel.AUTHENTIC,
        "lo": None,                       "neg": None,
    },
    {
        "dim": "accessibility",
        "hi": EXPLAINER_HI_ACCESSIBILITY, "pos": ScoreLabel.ACCESSIBLE,
        "lo": EXPLAINER_LO_ACCESSIBILITY, "neg": ScoreLabel.HARD_TO_FIND,
    },
    {
        "dim": "cost",
        "hi": EXPLAINER_HI_COST,         "pos": ScoreLabel.BUDGET,
        "lo": EXPLAINER_LO_COST,         "neg": ScoreLabel.EXPENSIVE,
    },
    {
        "dim": "ease",
        "hi": EXPLAINER_HI_EASE,         "pos": ScoreLabel.SIMPLE,
        "lo": EXPLAINER_LO_EASE,         "neg": ScoreLabel.TECHNICAL,
    },
    {
        "dim": "carbon",
        "hi": EXPLAINER_HI_CARBON,       "pos": ScoreLabel.LOW_CARBON,
        "lo": EXPLAINER_LO_CARBON,       "neg": None,
    },
    {
        "dim": "flavor",
        "hi": EXPLAINER_HI_FLAVOR,       "pos": ScoreLabel.BALANCED_FLAVOR,
        "lo": None,                       "neg": None,
    },
]


# ── API publique ──────────────────────────────────────────────────────────────

def explain(score_result: dict) -> list[str]:
    """
    Retourne les labels lisibles depuis un dict score_recipe().

    Args:
        score_result : retour de score_recipe() ou dict avec clé "dims"

    Returns:
        list[str] de labels ScoreLabel — jamais None, jamais de doublons.
        Ordre : dimensions 7D en premier, bonus profil ensuite.
    """
    labels: list[str] = []
    seen:   set[str]  = set()

    dims = score_result.get("dims", score_result.get("details", score_result))

    for rule in _DIM_RULES:
        val = float(dims.get(rule["dim"], 0) or 0)
        lbl = None
        if val >= rule["hi"] and rule["pos"]:
            lbl = rule["pos"]
        elif rule["lo"] and val < rule["lo"] and rule["neg"]:
            lbl = rule["neg"]
        if lbl and lbl not in seen:
            labels.append(lbl)
            seen.add(lbl)

    for b in score_result.get("bonuses", []):
        raw = b.get("label", "")
        if raw:
            lbl = raw.replace(" ", "_").lower()
            if lbl not in seen:
                labels.append(lbl)
                seen.add(lbl)

    return labels
