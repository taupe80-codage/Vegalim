"""
week_balance.py — Bilan nutritionnel de la semaine planifiée.

Remplace la comparaison « apports de la semaine / AJR × 7 » de la page
Nutrition (2026-11-25) : un planning sans petits-déjeuners paraissait
toujours en manque de tout. L'objectif est désormais la part des besoins
couverte par les repas RÉELLEMENT planifiés (petit-déjeuner 25 %, déjeuner et
dîner 37,5 % chacun), puis :

  - manques  : nutriment sous 70 % de son objectif (fort sous 50 %), avec un
               conseil et des recettes du catalogue qui le comblent ;
  - excès    : sel, sucres, graisses saturées au-delà de 110 % ;
  - calories : affichées pour information (les besoins varient selon la personne).

Valeurs par portion : graphe nutrition (load_nutrition_graph), recettes du
catalogue et recettes proposées publiées.
"""
from __future__ import annotations

MEAL_SHARE = {"breakfast": 0.25, "lunch": 0.375, "dinner": 0.375}
MEALS = tuple(MEAL_SHARE)
DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")

# Références journalières pour un adulte (backend/engine/score_engine/ajr.py,
# complétées des valeurs nutritionnelles de référence UE, règlement 1169/2011)
DAILY = {
    "calories": 2000.0, "protein": 50.0, "fiber": 30.0,
    "iron": 14.0, "calcium": 1000.0, "magnesium": 400.0, "potassium": 3500.0,
    "zinc": 10.0, "vitamin_c": 90.0, "vitamin_b12": 2.5, "vitamin_d": 15.0,
    "folate": 200.0, "vitamin_a": 800.0, "omega3": 2.0,
    # à limiter
    "sodium": 2300.0, "sugar": 90.0, "saturated_fat": 20.0,
}
LIMITS = ("sodium", "sugar", "saturated_fat")
TO_REACH = ("protein", "fiber", "iron", "calcium", "magnesium", "potassium", "zinc",
            "vitamin_c", "vitamin_b12", "vitamin_d", "folate", "vitamin_a", "omega3")

LABELS = {
    "calories": ("Énergie", "kcal"), "protein": ("Protéines", "g"), "fiber": ("Fibres", "g"),
    "iron": ("Fer", "mg"), "calcium": ("Calcium", "mg"), "magnesium": ("Magnésium", "mg"),
    "potassium": ("Potassium", "mg"), "zinc": ("Zinc", "mg"), "vitamin_c": ("Vitamine C", "mg"),
    "vitamin_b12": ("Vitamine B12", "µg"), "vitamin_d": ("Vitamine D", "µg"),
    "folate": ("Folates (B9)", "µg"), "vitamin_a": ("Vitamine A", "µg"), "omega3": ("Oméga-3", "g"),
    "sodium": ("Sodium", "mg"), "sugar": ("Sucres", "g"), "saturated_fat": ("Graisses saturées", "g"),
}

GAP = 0.70          # sous 70 % de l'objectif : manque
STRONG_GAP = 0.50   # sous 50 % : manque marqué
EXCESS = 1.10       # au-delà de 110 % d'une limite : excès

TIPS = {
    "protein": "Associez légumineuses et céréales, ajoutez tofu, tempeh, œufs ou fromage.",
    "fiber": "Légumineuses, céréales complètes, légumes et fruits avec la peau.",
    "iron": "Lentilles, pois chiches, tofu, épinards, graines — avec de la vitamine C "
            "(citron, poivron) dans le même repas pour mieux l'absorber.",
    "calcium": "Fromages, yaourts, tofu au calcium, choux, amandes, sésame (tahini).",
    "magnesium": "Légumineuses, céréales complètes, oléagineux, chocolat noir.",
    "potassium": "Légumineuses, pommes de terre, légumes verts, bananes.",
    "zinc": "Légumineuses, graines de courge, céréales complètes, fromages.",
    "vitamin_c": "Poivrons, choux, agrumes, kiwi et herbes fraîches, de préférence crus.",
    "vitamin_b12": "Œufs et produits laitiers en apportent ; en alimentation vegan, un "
                   "complément de B12 est indispensable (aucun végétal n'en fournit).",
    "vitamin_d": "Peu d'aliments en contiennent : le soleil reste la source principale. "
                 "Un complément est souvent conseillé d'octobre à mars, voyez avec un médecin.",
    "folate": "Légumes verts à feuilles, légumineuses, asperges, avocat.",
    "vitamin_a": "Carotte, patate douce, courge, épinards (bêta-carotène), avec un peu de gras.",
    "omega3": "Noix, graines de lin ou de chia moulues, huile de colza ou de noix.",
    "sodium": "Réduisez sauces soja, bouillons et fromages salés ; les herbes et épices prennent le relais.",
    "sugar": "Allégez les desserts et préférez les fruits entiers.",
    "saturated_fat": "Moins de beurre, crème, fromage et huile de coco ; plus d'huiles de colza et d'olive.",
}

# Nutriments pour lesquels proposer des recettes n'a pas de sens : la vitamine D
# vient du soleil ; la B12 d'un complément en vegan (recettes proposées si non vegan).
NO_RECIPE = {"vitamin_d"}
SUGGEST_DISHES = {"main", "soup", "side", "starter", "breakfast"}
N_SUGGEST = 4


def _slot_ids(slot) -> list[str]:
    if not isinstance(slot, dict) or slot.get("skip"):
        return []
    items = slot.get("recipes") or ([slot] if slot.get("id") else [])
    return [str(r.get("id")) for r in items if isinstance(r, dict) and r.get("id")]


def balance(plan: dict, diet: str | None = None) -> dict:
    """Bilan de la semaine : objectifs, totaux, manques (+ recettes), excès."""
    from backend.core.data_io import load_nutrition_graph

    ng = load_nutrition_graph()
    totals = {k: 0.0 for k in DAILY}
    share_sum = 0.0
    meals = {m: 0 for m in MEALS}
    in_plan: list[str] = []
    missing: list[str] = []

    for day in DAYS:
        day_data = plan.get(day) or {}
        for meal in MEALS:
            ids = _slot_ids(day_data.get(meal))
            if not ids:
                continue
            meals[meal] += 1
            share_sum += MEAL_SHARE[meal]
            for rid in ids:
                in_plan.append(rid)
                nutr = ng.get(rid)
                if not nutr:
                    missing.append(rid)
                    continue
                for k in DAILY:
                    v = nutr.get(k)
                    if isinstance(v, (int, float)):
                        totals[k] += float(v)

    n_meals = sum(meals.values())
    out = {"meals": meals, "n_meals": n_meals, "days_equivalent": round(share_sum, 2),
           "recipes_without_data": missing, "nutrients": [], "gaps": [], "excess": []}
    if not n_meals:
        return out

    for k, daily in DAILY.items():
        target = daily * share_sum
        ratio = totals[k] / target if target else 0.0
        label, unit = LABELS[k]
        out["nutrients"].append({
            "key": k, "label": label, "unit": unit, "total": round(totals[k], 1),
            "target": round(target, 1), "pct": round(ratio * 100),
            "kind": "limit" if k in LIMITS else "info" if k == "calories" else "reach",
        })
        if k in TO_REACH and ratio < GAP:
            out["gaps"].append({"key": k, "label": label, "unit": unit, "pct": round(ratio * 100),
                                "missing": round(target - totals[k], 1),
                                "severity": "high" if ratio < STRONG_GAP else "medium",
                                "tip": TIPS[k]})
        elif k in LIMITS and ratio > EXCESS:
            out["excess"].append({"key": k, "label": label, "unit": unit, "pct": round(ratio * 100),
                                  "tip": TIPS[k]})

    out["gaps"].sort(key=lambda g: g["pct"])
    _suggest(out["gaps"], set(in_plan), diet, ng)
    return out


def _suggest(gaps: list[dict], in_plan: set[str], diet: str | None, ng: dict) -> None:
    """Recettes qui comblent chaque manque : les plus riches par portion parmi
    les plats du régime choisi, hors planning, sans en répéter une d'un manque
    à l'autre."""
    from backend.core.data_io import load_recipes, load_score_graph, is_component_recipe

    vegan = (diet or "").lower() == "vegan"
    sg = load_score_graph()
    pool = []
    for r in load_recipes():
        rid = str(r.get("id"))
        if rid in in_plan or is_component_recipe(r) or str(r.get("dish_type")) not in SUGGEST_DISHES:
            continue
        if vegan and not (r.get("diet_flags") or {}).get("vegan"):
            continue
        if rid in ng:
            pool.append(r)
    used: set[str] = set()
    for g in gaps:
        g["recipes"] = []
        if g["key"] in NO_RECIPE or (g["key"] == "vitamin_b12" and vegan):
            continue
        k = g["key"]
        ranked = sorted(pool, key=lambda r: (float(ng[str(r["id"])].get(k) or 0),
                                              float((sg.get(str(r["id"])) or {}).get("overall_score") or 0)),
                        reverse=True)
        for r in ranked:
            rid = str(r["id"])
            amount = float(ng[rid].get(k) or 0)
            if amount <= 0 or len(g["recipes"]) >= N_SUGGEST:
                break
            if rid in used:
                continue
            used.add(rid)
            g["recipes"].append({
                "id": rid,
                "title_fr": (r.get("titles") or {}).get("fr") or rid,
                "titles": r.get("titles"),
                "dish_type": r.get("dish_type"),
                "amount": round(amount, 1),
                "calories": ng[rid].get("calories"),
            })
