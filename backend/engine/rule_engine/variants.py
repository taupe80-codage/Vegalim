"""
variants.py — Variantes vegan d'une recette.
Fusionne : vegan_variant_engine

API :
    vegan_variant(recipe) → dict  {recipe, substitutions, source}
"""
from __future__ import annotations
import logging
from backend.core.data_cache import data_cached

logger = logging.getLogger(__name__)

VEGAN_SUBS: dict[str, str | None] = {
    "oeuf": "tofu", "oeufs": "tofu", "lait": "lait_coco",
    "beurre": "olive_oil", "butter": "olive_oil", "ghee": "coconut_oil",
    "creme": "lait_coco", "creme_fraiche": "tofu_soyeux",
    "fromage_blanc": "tofu_soyeux", "yogurt": "tofu_soyeux", "yaourt": "tofu_soyeux",
    "feta": "tofu_feta", "mozzarella": "mozzarella_vegane",
    "cheese": "tofu_soyeux", "fromage": "tofu_soyeux",
    "parmesan": "levure_maltee", "ricotta": "noix_de_cajou",
    "cheddar": "cheddar_vegane", "gruyere": "levure_maltee",
    "paneer": "tofu", "kashk": "tofu_soyeux",
    "miel": "sirop_agave", "honey": "sirop_agave",
    "mayonnaise": "mayonnaise_vegan",
}

@data_cached
def _variant_index() -> dict:
    """
    Charge l'index des variantes vegan pré-calculées.
    Source : backend/data/config/vegan_variants_index.json

    Fix : l'ancienne implémentation appelait get_data.graphs.get_raw("vegan_variants")
    mais l'alias "vegan_variants" n'existait pas dans GraphRepository.GRAPH_ALIASES,
    et le fichier est dans data/config/ (pas data/graphs/). L'index retournait toujours {}.
    """
    try:
        from backend.core.data_io import load_vegan_variants_index
        raw = load_vegan_variants_index()
        return raw.get("original_to_vegan", raw) if isinstance(raw, dict) else {}
    except Exception:
        return {}

def vegan_variant(recipe: dict) -> dict:
    """
    Retourne la version vegan d'une recette.

    Étapes :
        1. Cherche dans l'index pré-calculé
        2. Génère à la volée via VEGAN_SUBS si absent

    Returns:
        {recipe: dict, substitutions: list[dict], source: str}
    """
    rid = str(recipe.get("id", ""))

    # 1. Index pré-calculé
    index = _variant_index()
    if rid in index:
        return {"recipe": recipe, "substitutions": [], "source": "index"}

    # 2. Génération à la volée
    import copy
    r = copy.deepcopy(recipe)
    applied = []

    has_composition = "composition" in r
    target_list = r.get("composition", r.get("ingredients", []))
    new_ings = []
    
    for item in target_list:
        if isinstance(item, dict):
            # Support both v5 and v6 keys
            iid = item.get("ingredient", item.get("ingredient_id", ""))
            sub = VEGAN_SUBS.get(iid.lower())
            if sub:
                applied.append({"original": iid, "substitute": sub})
                if "ingredient" in item:
                    item = {**item, "ingredient": sub}
                else:
                    item = {**item, "ingredient_id": sub}
        else:
            sub = VEGAN_SUBS.get(str(item).lower())
            if sub:
                applied.append({"original": str(item), "substitute": sub})
                item = sub
        new_ings.append(item)

    if has_composition:
        r["composition"] = new_ings
    else:
        r["ingredients"] = new_ings
        
    r["_vegan_variant"] = True

    if "tags" in r and isinstance(r["tags"], dict):
        if "diet" not in r["tags"]: r["tags"]["diet"] = []
        if "vegan" not in r["tags"]["diet"]: r["tags"]["diet"].append("vegan")
        if "vegetarien" not in r["tags"]["diet"]: r["tags"]["diet"].append("vegetarien")
    elif r.get("diet_flags"):
        r["diet_flags"] = {**r["diet_flags"], "vegan": True, "vegetarian": True}

    return {
        "recipe":        r,
        "substitutions": applied,
        "source":        "generated" if applied else "already_vegan",
    }
