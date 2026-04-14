import logging
logger = logging.getLogger(__name__)

"""
Application des substitutions d'ingrédients (ex : milk → plant milk).
Utile pour les régimes vegan ou sans lactose.

Les règles sont chargées depuis le graphe de substitution
(ingredient_substitution_rules_graph_v1.json) via data_io.
"""
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_subs() -> dict:
    """Charge les substitutions depuis le graphe de référence (source unique)."""
    from backend.core.data_io import load_substitution_graph
    graph = load_substitution_graph()
    # Le graphe stocke les substitutions sous la clé 'substitutions' ou directement
    subs = graph.get("substitutions", {})
    if not subs and isinstance(graph, dict):
        # Fallback : format plat {ingredient_id: replacement}
        subs = {k: v for k, v in graph.items() if not k.startswith("_")}
    return subs


def apply_substitutions(recipes: list[dict]) -> list[dict]:
    logger.debug("apply_substitutions : %d recettes", len(recipes))
    """
    Applique les substitutions d'ingrédients.
    Ajoute un champ 'substitutions_applied' listant les remplacements effectués.
    """
    subs   = _load_subs()
    result = []

    for recipe in recipes:
        applied      = []
        new_ings     = []

        for ing in recipe.get("ingredients", []):
            # Accepte str (ancien format) ou dict {ingredient_id: ...}
            if isinstance(ing, dict):
                ing_id = ing.get("ingredient_id", "")
                if ing_id in subs:
                    new_ing = dict(ing)
                    new_ing["ingredient_id"] = subs[ing_id]
                    new_ings.append(new_ing)
                    applied.append({"original": ing_id, "replacement": subs[ing_id]})
                else:
                    new_ings.append(ing)
            else:
                if ing in subs:
                    new_ings.append(subs[ing])
                    applied.append({"original": ing, "replacement": subs[ing]})
                else:
                    new_ings.append(ing)

        entry = recipe.copy()
        entry["ingredients"]           = new_ings
        entry["substitutions_applied"] = applied
        result.append(entry)

    return result
