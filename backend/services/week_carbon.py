"""
week_carbon.py — Empreinte carbone de la semaine planifiée (2026-11-26).

Pour chaque repas du planning : la recette réellement cuisinée (version vegan
ou modifiée par le membre, plan_entry_recipe), au mois en cours (fruits et
légumes de saison ou non, Agribalyse), multipliée par les portions du créneau.

Renvoie le total, la moyenne par portion comparée à celle des plats du
catalogue, les repas qui pèsent le plus (avec des recettes proches qui
émettent nettement moins), les ingrédients qui pèsent le plus (avec des
équivalents en cuisine moins émetteurs) et les produits frais hors saison.
"""
from __future__ import annotations

import datetime
import logging
import threading

from backend.services.week_balance import DAYS, MEALS

logger = logging.getLogger(__name__)

LOWER_RATIO = 0.6            # une alternative émet au moins 40 % de moins
N_TOP = 3
MAIN_DISHES = {"main", "soup", "salad", "bowl", "curry", "stew", "pasta"}

_cache_lock = threading.Lock()
_cache: dict = {"key": None, "data": None}


def portion_carbon(month: int) -> dict[str, float]:
    """{id: kg CO₂e par portion} de toutes les recettes du catalogue, au mois donné."""
    from backend.core.data_cache import data_generation
    from backend.core.data_io import load_catalogue_recipes
    from backend.engine.rule_engine.carbon import carbon_score
    key = (data_generation(), month)
    with _cache_lock:
        if _cache["key"] != key:
            data = {}
            for r in load_catalogue_recipes():
                try:
                    cs = carbon_score(r, month=month)
                    if cs.get("coverage", 0) >= 0.5:
                        data[str(r["id"])] = float(cs["per_portion_kg"])
                except Exception:
                    logger.debug("portion_carbon %s", r.get("id"), exc_info=True)
            _cache.update(key=key, data=data)
        return _cache["data"]


def _catalogue_average(month: int) -> float | None:
    from backend.core.data_io import load_catalogue_recipes
    pc = portion_carbon(month)
    vals = [pc[str(r["id"])] for r in load_catalogue_recipes()
            if str(r["id"]) in pc and r.get("dish_type") in MAIN_DISHES]
    return round(sum(vals) / len(vals), 3) if vals else None


def _entries(slot) -> list[dict]:
    if not isinstance(slot, dict) or slot.get("skip"):
        return []
    items = slot.get("recipes") or ([slot] if slot.get("id") else [])
    return [r for r in items if isinstance(r, dict) and r.get("id")]


def _title(r: dict) -> str:
    return (r.get("titles") or {}).get("fr") or r.get("title_fr") or str(r.get("id"))


def _lower_alternatives(recipe: dict, per_portion: float, month: int, diet: str | None) -> list[dict]:
    """Recettes proches (même type de plat) qui émettent nettement moins."""
    from backend.engine.search_engine.similar import find_similar_by_id
    pc = portion_carbon(month)
    out = []
    try:
        similar = find_similar_by_id(recipe["id"], limit=20, diet=diet)
    except Exception:
        similar = []
    for s in similar:
        sid = str(s.get("id"))
        if s.get("dish_type") and recipe.get("dish_type") and s["dish_type"] != recipe["dish_type"]:
            continue                       # un dessert ne remplace pas un plat
        v = pc.get(sid)
        if v is not None and v <= per_portion * LOWER_RATIO:
            out.append({"id": sid, "title_fr": _title(s), "per_portion_kg": round(v, 2)})
        if len(out) >= 3:
            break
    return out


def _lower_ingredients(iid: str) -> list[dict]:
    """Équivalents en cuisine qui émettent nettement moins par kilo."""
    from backend.services.ingredient_sheet import carbon_info
    from backend.services.recipe_edits import culinary_equivalents, display_name
    ref = carbon_info(iid)
    if not ref:
        return []
    out = []
    for cid, _ in culinary_equivalents(iid):
        c = carbon_info(cid)
        if c and c["kg_co2_per_kg"] <= ref["kg_co2_per_kg"] * LOWER_RATIO:
            out.append({"id": cid, "name_fr": display_name(cid), "kg_co2_per_kg": c["kg_co2_per_kg"]})
    out.sort(key=lambda x: x["kg_co2_per_kg"])
    return out[:3]


def week_carbon(plan: dict, month: int | None = None, diet: str | None = None) -> dict:
    from backend.core.data_io import load_recipes
    from backend.engine.rule_engine.carbon import carbon_score
    from backend.services.ingredient_sheet import carbon_info, season_info
    from backend.services.recipe_edits import display_name, plan_entry_recipe

    month = month or datetime.date.today().month
    index = {str(r.get("id")): r for r in load_recipes()}
    meals: list[dict] = []
    by_ing: dict[str, float] = {}
    total = 0.0
    portions = 0
    unknown: list[str] = []
    for day in DAYS:
        for meal in MEALS:
            slot = (plan.get(day) or {}).get(meal)
            for entry in _entries(slot):
                rid = str(entry["id"])
                recipe = index.get(rid)
                if not recipe:
                    continue
                cooked = plan_entry_recipe(recipe, entry)
                cs = carbon_score(cooked, month=month)
                if cs.get("coverage", 0) < 0.5:
                    unknown.append(rid)
                    continue
                srv = max(1, int(cooked.get("servings") or 4))
                n = int((slot or {}).get("servings") or 0) or srv
                kg = cs["per_portion_kg"] * n
                total += kg
                portions += n
                meals.append({"day": day, "meal": meal, "id": rid, "title_fr": _title(recipe),
                              "variant": entry.get("variant"), "portions": n,
                              "per_portion_kg": round(cs["per_portion_kg"], 3), "kg": round(kg, 3),
                              "label": cs["label"]})
                for x in cs.get("ingredients_co2") or []:
                    by_ing[x["ingredient"]] = by_ing.get(x["ingredient"], 0.0) + x["kg_co2"] * n / srv

    out = {"month": month, "total_kg": round(total, 2), "portions": portions, "n_meals": len(meals),
           "per_portion_kg": round(total / portions, 3) if portions else 0.0,
           "catalogue_avg_kg": _catalogue_average(month), "recipes_without_data": unknown,
           "top_meals": [], "top_ingredients": [], "off_season": []}
    if not meals:
        return out

    # repas qui pèsent le plus (par portion), chacun une fois
    seen: set[str] = set()
    for m in sorted(meals, key=lambda m: -m["per_portion_kg"]):
        if m["id"] in seen or len(out["top_meals"]) >= N_TOP:
            continue
        seen.add(m["id"])
        out["top_meals"].append({**m, "alternatives": _lower_alternatives(index[m["id"]], m["per_portion_kg"], month, diet)})

    # ingrédients qui pèsent le plus sur la semaine
    for iid, kg in sorted(by_ing.items(), key=lambda kv: -kv[1])[:5]:
        out["top_ingredients"].append({"id": iid, "name_fr": display_name(iid), "kg": round(kg, 2),
                                       "share_pct": round(kg / total * 100) if total else 0,
                                       "lower": _lower_ingredients(iid) if not iid.startswith("base_") else []})

    # produits frais hors saison ce mois-ci (serre chauffée ou avion)
    for iid in sorted(by_ing, key=lambda k: -by_ing[k]):
        season = season_info(iid)
        if not season or month in season["months"]:
            continue
        c = carbon_info(iid) or {}
        if c.get("off_season_kg") and c.get("in_season_kg") is not None and c["off_season_kg"] > c["in_season_kg"]:
            out["off_season"].append({"id": iid, "name_fr": display_name(iid), "months": season["label"],
                                      "kg": round(by_ing[iid], 2),
                                      "saving_pct": round((1 - c["in_season_kg"] / c["off_season_kg"]) * 100)})
    out["off_season"] = out["off_season"][:5]
    return out
