"""
Recipe Embedding Engine
========================
Calcule la similarité entre recettes sur 4 dimensions réelles :
  1. Ingrédients partagés     (Jaccard)          poids 0.40
  2. Profils saveur partagés  (Jaccard)           poids 0.25
  3. Origine culinaire        (même cuisine +1)   poids 0.20
  4. Technique partagée       (Jaccard)           poids 0.15

Résultat : score 0.0 → 1.0 sémantiquement interprétable.
"""

import json
from pathlib import Path
from backend.engine.config import DATA_ROOT

def _safe_json(path, encoding="utf-8"):
    """Chargement JSON sécurisé avec context manager."""
    with open(path, encoding=encoding) as _f:
        return json.load(_f)


# ── Charger les flavor profiles précalculés ──────────────────────────────────
_FLAVOR_PROFILES: dict = {}

def _load_flavor_profiles() -> dict:
    global _FLAVOR_PROFILES
    if _FLAVOR_PROFILES:
        return _FLAVOR_PROFILES
    try:
        eng = _safe_json(DATA_ROOT / "config" / "fridge_engine.json")
        # Essayer le moteur optimisé du projet
        fridge_opt = DATA_ROOT.parent.parent.parent / "export_final" / "engines" / "engines_fridge_optimized.json"
        if not fridge_opt.exists():
            fridge_opt = DATA_ROOT / "config" / "fridge_engine.json"
        data = _safe_json(fridge_opt) if fridge_opt.exists() else {}
        _FLAVOR_PROFILES = data.get("recipe_flavor_profiles", {})
    except Exception:
        _FLAVOR_PROFILES = {}
    return _FLAVOR_PROFILES


def _jaccard(set_a: set, set_b: set) -> float:
    """Jaccard similarity entre deux ensembles."""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _recipe_vector(recipe: dict, flavor_profiles: dict) -> dict:
    """Extrait les composantes d'une recette pour la comparaison."""
    rid = str(recipe.get("id", ""))
    return {
        "ingredients":  set(recipe.get("ingredients", [])),
        "flavors":      set(flavor_profiles.get(rid, [])),
        "origin":       (recipe.get("iconic_status") or {}).get("cuisine_origin", ""),
        "techniques":   set(recipe.get("technique", [])),
    }


def recipe_similarity(recipe_a: dict, recipe_b: dict) -> float:
    """
    Calcule la similarité entre deux recettes.
    Retourne un score 0.0 → 1.0.
    """
    fp = _load_flavor_profiles()
    va = _recipe_vector(recipe_a, fp)
    vb = _recipe_vector(recipe_b, fp)

    ing_sim    = _jaccard(va["ingredients"], vb["ingredients"])
    flavor_sim = _jaccard(va["flavors"],     vb["flavors"])
    origin_sim = 1.0 if (va["origin"] and va["origin"] == vb["origin"]) else 0.0
    tech_sim   = _jaccard(va["techniques"],  vb["techniques"])

    score = (
        ing_sim    * 0.40 +
        flavor_sim * 0.25 +
        origin_sim * 0.20 +
        tech_sim   * 0.15
    )
    return round(score, 3)


def find_similar_recipes(recipe: dict, dataset: list, limit: int = 5) -> list[dict]:
    """
    Trouve les recettes les plus similaires dans dataset.

    Args:
        recipe  : recette de référence (dict avec id, ingredients, technique, iconic_status)
        dataset : liste de recettes à comparer
        limit   : nombre de résultats retournés

    Returns:
        Liste triée par similarité décroissante :
        [{"id", "title", "similarity", "shared_ingredients", "shared_flavors"}, ...]
    """
    fp      = _load_flavor_profiles()
    base_v  = _recipe_vector(recipe, fp)
    base_id = recipe.get("id")

    results = []
    for r in dataset:
        if r.get("id") == base_id:
            continue  # exclure la recette elle-même

        score      = recipe_similarity(recipe, r)
        cmp_v      = _recipe_vector(r, fp)
        shared_ing = sorted(base_v["ingredients"] & cmp_v["ingredients"])
        shared_fl  = sorted(base_v["flavors"]     & cmp_v["flavors"])

        results.append({
            "id":                r.get("id"),
            "title":             r.get("titles", {}).get("fr") or r.get("titles", {}).get("original") or r.get("title"),
            "similarity":        score,
            "shared_ingredients": shared_ing[:6],
            "shared_flavors":    shared_fl,
        })

    results.sort(key=lambda x: -x["similarity"])
    return results[:limit]
