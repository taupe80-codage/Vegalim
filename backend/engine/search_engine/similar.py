"""
similar.py — Recettes similaires ("vous aimerez aussi").
Fusionne : similarity_engine + recipe_embedding_engine

API :
    find_similar(recipe, limit)      → list[dict]
    find_similar_by_id(recipe_id, n) → list[dict]
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def _all_recipes() -> list[dict]:
    # FIX #9 : suppression du @lru_cache local — data_io.load_recipes() possède
    # déjà son propre cache mtime-aware qui se rafraîchit si recipes.json change.
    # Le double cache empêchait la prise en compte des nouvelles recettes du pipeline.
    try:
        from backend.core.data_io import load_recipes
        return load_recipes()
    except Exception:
        from backend.db.data_access import get_data
        return get_data.recipes.list_all()


def _ingredient_similarity(a: dict, b: dict) -> float:
    """Jaccard sur les ingrédients (composition v6 ou ingredients legacy)."""
    def _ids(r):
        # v6 : composition [{ingredient: "id", ...}]
        comp = r.get("composition") or r.get("ingredients", [])
        return {
            (
                i.get("ingredient", i.get("ingredient_id", str(i)))
                if isinstance(i, dict) else str(i)
            ).lower()
            for i in comp
        }
    sa, sb = _ids(a), _ids(b)
    if not sa or not sb: return 0.0
    return len(sa & sb) / len(sa | sb)

def _technique_similarity(a: dict, b: dict) -> float:
    ta = set(str(t).lower() for t in (a.get("technique") or []))
    tb = set(str(t).lower() for t in (b.get("technique") or []))
    if not ta or not tb: return 0.0
    return len(ta & tb) / len(ta | tb)

def _iconic_similarity(a: dict, b: dict) -> float:
    """Même cuisine d'origine → bonus."""
    ca = (a.get("iconic_status") or {}).get("cuisine_origin", "")
    cb = (b.get("iconic_status") or {}).get("cuisine_origin", "")
    return 1.0 if ca and ca == cb else 0.0


def find_similar(recipe: dict, limit: int = 5) -> list[dict]:
    """
    Retourne les recettes les plus similaires sur 3 dimensions :
    ingrédients partagés (50%), techniques (30%), cuisine d'origine (20%).
    """
    rid     = recipe.get("id")
    results = []

    for r in _all_recipes():
        if r.get("id") == rid:
            continue
        score = (
            _ingredient_similarity(recipe, r) * 0.50 +
            _technique_similarity(recipe, r)  * 0.30 +
            _iconic_similarity(recipe, r)     * 0.20
        )
        if score > 0:
            r2 = dict(r)
            r2["_similarity_score"] = round(score, 3)
            results.append(r2)

    results.sort(key=lambda x: x["_similarity_score"], reverse=True)
    return results[:limit]


def find_similar_by_id(recipe_id: "str | int", limit: int = 5) -> list[dict]:
    """Raccourci : find_similar depuis un id. Accepte str ou int (IDs v6 = strings)."""
    from backend.db.data_access import get_data
    recipe = get_data.recipes.get_by_id(recipe_id)
    if not recipe:
        logger.warning("find_similar_by_id: recette %s introuvable", recipe_id)
        return []
    return find_similar(recipe, limit)
