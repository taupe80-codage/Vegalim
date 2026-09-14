"""
carbon.py — Empreinte carbone recette.
Fusionne : sustainability_engine

API :
    carbon_score(recipe) → dict  {total_kg_co2, per_portion_kg, label, score, coverage, ingredients_co2}

carbon_footprint.json est indexé par ingrédient générique (kg CO₂e / 100 g :
'chickpea', 'olive_oil'…), pas par id de composition ('chickpea_boiled') :
la résolution passe par resolve_catalog_key (id exact → préfixe →
ingredient_price_map). Les quantités sont converties en grammes par le même
moteur que la nutrition (_qty_to_g). Les sous-recettes base_* sont calculées
depuis leur propre composition.
"""
from __future__ import annotations
from backend.core.data_cache import data_cached

_LOW  = 0.5   # kg CO₂e / portion
_HIGH = 1.5

@data_cached
def _carbon_db() -> dict:
    from backend.core.data_io import load_carbon_footprint
    return load_carbon_footprint()

def eco_label(kg_co2: float) -> str:
    if kg_co2 < _LOW:  return "🟢 Faible"
    if kg_co2 < _HIGH: return "🟡 Moyen"
    return "🔴 Élevé"

def _co2_per_100g(raw) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, dict):
        return float(raw.get("co2_per_100g", 0.0))
    return 0.0

def _recipe_co2(recipe: dict, _visiting: frozenset = frozenset()) -> tuple[float, float, int, int, list]:
    """(kg CO₂e total, poids total g, lignes chiffrées, lignes connues-poids, détail)."""
    from backend.core.data_io import resolve_catalog_key, load_recipes
    from backend.engine.nutrition_engine import _qty_to_g

    db = _carbon_db()
    total = weight = 0.0
    n_known = n_lines = 0
    per_ing = []
    for item in recipe.get("composition", []) or []:
        if not isinstance(item, dict) or (item.get("meta") or {}).get("role") == "serving_suggestion":
            continue
        iid = item.get("ingredient", "")
        qty_g = _qty_to_g(iid, item) if iid else 0.0
        if qty_g <= 0:
            continue
        n_lines += 1
        weight += qty_g

        co2 = None
        if iid.startswith("base_") and iid not in _visiting:
            sub = next((r for r in load_recipes() if r.get("id") == iid), None)
            if sub:
                s_total, s_weight, s_known, _, _ = _recipe_co2(sub, _visiting | {iid})
                if s_weight and s_known:
                    co2 = s_total / s_weight * qty_g
        else:
            key = resolve_catalog_key(iid, db)
            if key:
                co2 = _co2_per_100g(db[key]) * qty_g / 100
        if co2 is None:
            continue
        n_known += 1
        total += co2
        per_ing.append({"ingredient": iid, "kg_co2": round(co2, 4)})
    return total, weight, n_known, n_lines, per_ing

def carbon_score(recipe: dict) -> dict:
    """Calcule l'empreinte carbone et le score éco (0-10, 10=très faible)."""
    servings = max(1, recipe.get("servings", 4) or 4)
    total, _, n_known, n_lines, per_ing = _recipe_co2(recipe)

    per_portion = round(total / servings, 3)
    score       = round(max(1.0, min(10.0, 10.0 - per_portion * 6.0)), 2)

    return {
        "total_kg_co2":   round(total, 3),
        "per_portion_kg": per_portion,
        "label":          eco_label(per_portion),
        "score":          score,
        "coverage":       round(n_known / n_lines, 2) if n_lines else 0.0,
        "ingredients_co2": sorted(per_ing, key=lambda x: -x["kg_co2"])[:8],
    }
