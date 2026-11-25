"""budget.py — Budget estimé par recette. Fusionne : ingredient_price_engine"""
from __future__ import annotations
import logging
logger = logging.getLogger(__name__)

_ECO  = 1.0
_PREM = 2.5

def budget_label(price_per_portion: float) -> str:
    if price_per_portion < _ECO:  return "€ Économique"
    if price_per_portion < _PREM: return "€€ Standard"
    return "€€€ Premium"

def estimate_price(recipe: dict, servings: int | None = None) -> dict:
    """Coût estimé par recette et par portion, au prix du catalogue
    (prices_catalog.json) pour la quantité réellement utilisée.

    Remplace l'ancien calcul sur prices.json (clés couvrant ~5 % des ids de
    composition, 50 g supposés pour toute unité inconnue)."""
    from backend.engine.planning_engine.shopping import recipe_cost
    from backend.services.ingredient_catalog import names_of

    cost   = recipe_cost(recipe)
    n_serv = max(1, servings or recipe.get("servings", 4) or 4)
    per_p  = round(cost["total_eur"] / n_serv, 2)
    # Ingrédients sans prix (sous-recettes comprises) : le coût affiché est un
    # minimum — l'interface doit le dire (« prix inconnu pour … »).
    names = names_of(cost["unknown"]) if cost["unknown"] else {}
    # Ingrédients chiffrés sans relevé de prix (price_source « estimation… » ou
    # « analogie… » dans prices_catalog.json) : la fiche le signale.
    from backend.core.data_io import load_prices_catalog, resolve_catalog_key
    catalog = load_prices_catalog()
    estimated = []
    for d in cost["details"]:
        key = resolve_catalog_key(d["ingredient"], catalog)
        src = str((catalog.get(key) or {}).get("price_source") or "") if key else ""
        if src.startswith(("estimation", "analogie")) and d["ingredient"] not in estimated:
            estimated.append(d["ingredient"])
    est_names = names_of(estimated) if estimated else {}
    return {
        "total_eur":        cost["total_eur"],
        "per_portion_eur":  per_p,
        "label":            budget_label(per_p),
        "currency":         "EUR",
        "ingredients_cost": cost["details"][:8],
        "n_unknown_price":  len(cost["unknown"]),
        "unknown_ingredients": [{"id": i, "name_fr": names.get(i) or i.replace("_", " ")}
                                for i in cost["unknown"]],
        "complete":         not cost["unknown"],
        "estimated_ingredients": [{"id": i, "name_fr": est_names.get(i) or i.replace("_", " ")}
                                  for i in estimated],
    }


# ── Semaine à budget fixe (2026-11-25) ───────────────────────────────────────
import threading as _threading

_costs_lock = _threading.Lock()
_costs: dict = {"key": None, "data": {}}


def portion_costs() -> dict[str, tuple[float, bool]]:
    """{id: (coût consommé par portion en €, prix complet ?)} de toutes les
    recettes, recalculé quand les données (recettes, prix) changent."""
    from backend.core.data_cache import data_generation
    from backend.core.data_io import load_prices_catalog, load_recipes
    from backend.engine.planning_engine.shopping import recipe_cost

    recipes = load_recipes()
    key = (data_generation(), id(recipes))
    with _costs_lock:
        if _costs["key"] != key:
            catalog = load_prices_catalog()
            index = {str(r.get("id")): r for r in recipes}
            data = {}
            for rid, r in index.items():
                try:
                    c = recipe_cost(r, catalog, index)
                    data[rid] = (float(c["per_portion_eur"]), not c["unknown"])
                except Exception:
                    logger.debug("portion_costs : %s non chiffrée", rid, exc_info=True)
            _costs.update(key=key, data=data)
        return _costs["data"]


MEAL_ORDER = ("breakfast", "lunch", "dinner")
DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def week_cost(plan: dict) -> dict:
    """Coût de la semaine planifiée.

    consumed_eur : ce que consomment les repas (coût par portion × portions du
                   créneau) — base du budget ;
    shopping_eur : ce que coûtent les courses en emballages entiers (liste de
                   courses), restes compris.
    """
    from backend.engine.planning_engine.shopping import shopping_list

    costs = portion_costs()
    consumed = 0.0
    portions = 0
    unpriced: list[str] = []
    shop_plan: dict = {}
    for day in DAYS:
        shop_plan[day] = {}
        i = 0
        for meal in MEAL_ORDER:
            slot = (plan.get(day) or {}).get(meal)
            if not isinstance(slot, dict) or slot.get("skip"):
                continue
            servings = int(slot.get("servings") or 0) or None
            for r in slot.get("recipes") or []:
                rid = str((r or {}).get("id") or "")
                if not rid:
                    continue
                n = servings or 4
                portions += n
                per, complete = costs.get(rid, (0.0, False))
                consumed += per * n
                if not complete and rid not in unpriced:
                    unpriced.append(rid)
                entry = {"id": rid, "title": r.get("title_fr") or ""}
                if servings:
                    entry["servings"] = servings
                if r.get("variant"):
                    entry["variant"] = r["variant"]
                shop_plan[day][f"{meal}_{i}"] = entry
                i += 1
    shopping = shopping_list(shop_plan) if portions else {"estimated_cost": 0.0, "items": []}
    # Courses en emballages entiers, séparées en produits frais (à acheter
    # cette semaine) et produits qui se conservent (épices, riz, légumes secs,
    # huile… : à prévoir seulement si le placard est vide, ils resservent).
    fresh = keeps = 0.0
    for item in shopping.get("items") or []:
        price = float(item.get("price_eur") or 0)
        if item.get("pantry") or _keeps(str(item.get("ingredient") or "")):
            keeps += price
        else:
            fresh += price
    return {
        "consumed_eur": round(consumed, 2),
        "portions": portions,
        "per_portion_eur": round(consumed / portions, 2) if portions else 0.0,
        "shopping_eur": shopping.get("estimated_cost", 0.0),
        "shopping_fresh_eur": round(fresh, 2),
        "shopping_keeps_eur": round(keeps, 2),
        "unpriced": unpriced,
    }


def _keeps(iid: str) -> bool:
    """Produit de longue conservation (même règle que l'anti-gaspillage)."""
    from backend.engine.planning_engine.planner import _KEEPS
    from backend.services.fridge_scoring import tier_of_id, STAPLE
    iid = iid.lower()
    if "fresh_herb" in iid:
        return False
    return any(k in iid for k in _KEEPS) or tier_of_id(iid) == STAPLE
