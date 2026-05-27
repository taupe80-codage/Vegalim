"""
shopping.py — Liste de courses depuis un plan de repas.
Fusionne : shopping_engine

API :
    shopping_list(meal_plan, eco) → dict
"""
from __future__ import annotations
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# Catégories anglaises → libellés FR
_CAT_FR = {
    "vegetables":       "Légumes",
    "legumes":          "Légumes",
    "fruits":           "Fruits",
    "proteins":         "Protéines",
    "meat":             "Viandes",
    "poultry":          "Volaille",
    "fish":             "Poissons",
    "seafood":          "Poissons & fruits de mer",
    "dairy":            "Produits laitiers",
    "eggs":             "Œufs",
    "grains":           "Céréales & féculents",
    "cereals":          "Céréales & féculents",
    "leguminous":       "Légumineuses",
    "legumes_sec":      "Légumineuses",
    "nuts":             "Noix & graines",
    "seeds":            "Noix & graines",
    "condiments":       "Condiments & sauces",
    "spices":           "Épices & aromates",
    "herbs":            "Herbes fraîches",
    "oils":             "Huiles & matières grasses",
    "fats":             "Huiles & matières grasses",
    "sweeteners":       "Sucres & édulcorants",
    "beverages":        "Boissons",
    "baking":           "Pâtisserie",
    "canned":           "Conserves",
    "frozen":           "Surgelés",
    "autre":            "Autre",
    "other":            "Autre",
}


def shopping_list(meal_plan: dict, eco: bool = False) -> dict:
    """
    Génère la liste de courses pour un plan de repas hebdomadaire.

    Args:
        meal_plan : output de generate_plan()
        eco       : marque les ingrédients réutilisés (> 2 fois)

    Returns:
        {
          items:           [{ingredient, name_fr, occurrences, price_eur, eco_reuse?}]
          estimated_cost:  float (€)
          n_recipes:       int
          by_category:     {cat_fr: [{ingredient, name_fr, occurrences}]}
        }
    """
    from backend.core.data_io import load_prices, load_ingredients_dict

    prices    = load_prices()
    ings_dict = load_ingredients_dict()

    def _get_name_fr(iid: str) -> str:
        """Résout le nom FR depuis le dictionnaire, avec fallback hiérarchique."""
        d = ings_dict.get(iid)
        if d and d.get("name_fr"):
            name = d["name_fr"]
            return name[0].upper() + name[1:] if name else iid
        # Partie avant '/' (ex: 'butter' pour 'butter/dairy')
        base = iid.split("/")[0]
        d = ings_dict.get(base)
        if d and d.get("name_fr"):
            name = d["name_fr"]
            return (name[0].upper() + name[1:]) if name else base
        # Fallback : humanise l'ID
        return iid.replace("_", " ").replace("/", " ").capitalize()

    def _get_category_fr(iid: str) -> str:
        """Retourne la catégorie en français pour un ingredient_id."""
        d = ings_dict.get(iid) or ings_dict.get(iid.split("/")[0]) or {}
        cat_en = d.get("category", "autre").lower()
        return _CAT_FR.get(cat_en, cat_en.capitalize())

    ing_count: dict[str, int] = defaultdict(int)
    n_recipes  = 0
    seen_ids   = set()

    for day, data in meal_plan.items():
        if day == "meta":
            continue
        if not isinstance(data, dict):
            continue
        for meal in ("lunch", "dinner"):
            meal_data = data.get(meal)
            if not meal_data:
                continue

            rid = meal_data.get("id") if isinstance(meal_data, dict) else None
            if not rid:
                continue
            if rid in seen_ids:
                continue   # batch cooking : ne pas doubler

            # Charge la recette complète pour accéder à composition
            try:
                from backend.core.data_io import load_recipes
                recipe = next((r for r in load_recipes() if r.get("id") == rid), None)
            except Exception:
                recipe = None

            if not recipe:
                continue

            seen_ids.add(rid)
            n_recipes += 1

            # Support des deux schémas : composition (CDC v4) et ingredients (legacy)
            items_list = recipe.get("composition") or recipe.get("ingredients", [])
            for ing in items_list:
                if isinstance(ing, dict):
                    key = (
                        ing.get("ingredient") or
                        ing.get("ingredient_id") or
                        str(ing)
                    ).lower().strip()
                else:
                    key = str(ing).lower().strip()
                if key:
                    ing_count[key] += 1

    # ── Construire la liste d'items ───────────────────────────────────────────
    items      = []
    total_eur  = 0.0

    for ing, count in sorted(ing_count.items(), key=lambda x: -x[1]):
        price_eur = float(prices.get(ing, 0.0)) * count

        item: dict = {
            "ingredient":  ing,
            "name_fr":     _get_name_fr(ing),
            "occurrences": count,
            "price_eur":   round(price_eur, 2),
        }
        if eco:
            item["eco_reuse"] = count > 2
        items.append(item)
        total_eur += price_eur

    # ── Regrouper par catégorie (FR) ──────────────────────────────────────────
    by_cat: dict[str, list] = defaultdict(list)
    for item in items:
        cat_fr = _get_category_fr(item["ingredient"])
        by_cat[cat_fr].append({
            "ingredient":  item["ingredient"],
            "name_fr":     item["name_fr"],
            "occurrences": item["occurrences"],
        })

    # Tri alphabétique des catégories, "Autre" en dernier
    def _cat_sort(kv):
        k = kv[0]
        return (1 if k == "Autre" else 0, k)

    return {
        "items":          items,
        "estimated_cost": round(total_eur, 2),
        "n_recipes":      n_recipes,
        "by_category":    dict(sorted(by_cat.items(), key=_cat_sort)),
    }
