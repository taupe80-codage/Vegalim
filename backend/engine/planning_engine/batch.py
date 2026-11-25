"""
batch.py — Session de batch cooking du dimanche, depuis le planning.

La case « batch » du planning se contentait de servir le dîner au déjeuner
du lendemain. Ici, la semaine planifiée devient une session de préparation à
l'avance, dans l'ordre où l'on s'y prend :

  1. la veille      : faire tremper les légumineuses sèches ;
  2. cuissons       : légumineuses (les plus longues d'abord), céréales ;
  3. préparations   : sous-recettes maison (sauces, pâtes, bouillons, paneer…) ;
  4. légumes        : laver, éplucher, tailler ;
  5. plats entiers  : (au choix) soupes, dals, curries, ragoûts qui se gardent.

Quantités additionnées sur la semaine, à l'échelle des portions de chaque
créneau. Conservation (session le dimanche, lundi = J+1) : au-delà de la durée
au réfrigérateur, la part concernée est à congeler — ou, pour les légumes, à
tailler plus tard.

Durées de conservation prudentes (repères ANSES / FSA) : riz cuit 1 jour
(Bacillus cereus), autres céréales et légumineuses cuites 4 jours, légumes
taillés 3 jours, plats mijotés 3 jours.
"""
from __future__ import annotations

import re

DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
MEALS = ("breakfast", "lunch", "dinner")
MEAL_FR = {"breakfast": "petit-déj.", "lunch": "déjeuner", "dinner": "dîner"}

# Légumineuses sèches : (motif d'id, cuisson min après trempage, trempage ?, rendement cuit)
LEGUMES = [
    (r"^chickpea.*dried|^chickpea_raw", 75, True, 2.2),
    (r"kidney_bean.*dried|red_bean.*dried|medium_red_bean", 60, True, 2.4),
    (r"(white|navy|great_northern|cannellini).*bean.*dried|^white_bean_dried$", 60, True, 2.4),
    (r"black_bean.*dried|black_turtle", 60, True, 2.4),
    (r"fava.*dried|broadbean.*dried", 60, True, 2.2),
    (r"black_eyed_peas.*dried|cowpea.*dried", 45, False, 2.3),
    (r"split_peas.*dried", 40, False, 2.4),
    (r"green_lentil.*dried|brown_lentil.*dried|beluga|puy", 25, False, 2.5),
    (r"mung_bean_dried", 35, False, 2.4),
]
# Céréales : (motif, cuisson min, rendement cuit, jours au frigo)
GRAINS = [
    (r"rice.*(raw|seed|dried)(?!.*cooked)", 15, 2.8, 1),
    (r"quinoa.*(raw|dried)", 15, 2.7, 4),
    (r"bulgur", 12, 2.5, 4),
    (r"barley.*(raw|seed)", 40, 3.0, 4),
    (r"buckwheat.*(raw|groat|seed)", 15, 2.5, 4),
    (r"millet.*raw", 20, 3.0, 4),
    (r"freekeh", 25, 2.5, 4),
    (r"farro|spelt.*(raw|seed)", 30, 2.5, 4),
]
# Légumes qui se taillent à l'avance sans s'abîmer (3 jours au frigo)
VEG = re.compile(r"^(onion|red_onion|yellow_onion|shallot|carrot|celery|celeriac|leek|.*bell_pepper|"
                 r"cabbage|green_cabbage|red_cabbage|white_cabbage|savoy|napa|kale|curly_kale|broccoli|"
                 r"cauliflower|fennel|butternut|pumpkin|red_kuri|kabocha|.*squash(?!.*zucchini)|"
                 r"garlic|ginger|parsnip|turnip|beetroot|radish|green_bean|french_bean)")
HERB = re.compile(r"fresh_herb|chives_raw")
NOT_FRESH = re.compile(r"powder|ground|juice|dried|paste|puree|canned|frozen|pickled|spice")
MIN_HERB_G = 10           # quelques brins de thym : rien à préparer
# Plats entiers qui se gardent et se réchauffent bien
KEEPING_DISH = re.compile(r"^(soup|stew|curry|dal|chili)_|soupe|ragout|ragoût|curry|dal|dahl|chili|tajine|mijot")

KEEP_DAYS = {"legume": 4, "veg": 3, "herb": 4, "dish": 3}
# Sous-recettes : conservation selon leur nature (par défaut 3 jours)
BASE_LONG = re.compile(r"ghee|harissa|za_atar|gochujang|curry_paste|pate_piment|roux|teriyaki|fish_sauce|"
                       r"oyster_sauce|kimchi|pickle|dukkah|spice|masala|chutney|jam|confit|vinaigre|vinegar")
BASE_SHORT = re.compile(r"tortilla|noodle|crepe|dough|pate_a|bread|naan|chapati|paratha")


def _uses(day_i: int, meal: str, title: str) -> dict:
    return {"day": DAYS[day_i], "day_index": day_i, "meal": MEAL_FR.get(meal, meal), "title": title}


def _storage(kind_days: int, uses: list[dict], freezable: bool = True) -> dict:
    """Session le dimanche : lundi = J+1. Parts au-delà de la durée au frigo."""
    late = sorted({u["day"] for u in uses if u["day_index"] + 1 > kind_days},
                  key=DAYS.index)
    return {"fridge_days": kind_days, "late_days": late, "freezable": freezable}


def batch_session(plan: dict) -> dict:
    from backend.core.data_io import load_recipes
    from backend.services.ingredient_catalog import names_of
    from backend.engine.nutrition_engine import _qty_to_g

    index = {str(r.get("id")): r for r in load_recipes()}
    items: dict[tuple[str, str], dict] = {}
    dishes: list[dict] = []
    meals = 0

    def add(kind: str, key: str, grams: float, use: dict, **extra):
        it = items.setdefault((kind, key), {"kind": kind, "key": key, "grams": 0.0, "uses": [], **extra})
        it["grams"] += grams
        same = next((u for u in it["uses"] if u["day"] == use["day"] and u["meal"] == use["meal"]
                     and u["title"] == use["title"]), None)
        if same:
            same["grams"] += grams
        else:
            it["uses"].append({**use, "grams": grams})

    for day_i, day in enumerate(DAYS):
        for meal in MEALS:
            slot = (plan.get(day) or {}).get(meal)
            if not isinstance(slot, dict) or slot.get("skip"):
                continue
            for entry in slot.get("recipes") or []:
                r = index.get(str((entry or {}).get("id") or ""))
                if not r:
                    continue
                meals += 1
                title = (r.get("titles") or {}).get("fr") or r["id"]
                servings = int(slot.get("servings") or 0) or int(r.get("servings") or 4)
                scale = servings / max(1, int(r.get("servings") or 4))
                use = _uses(day_i, meal, title)
                if KEEPING_DISH.search(str(r["id"])) or KEEPING_DISH.search(title.lower()) or r.get("dish_type") == "soup":
                    dishes.append({"id": r["id"], "title": title, "servings": servings, **use,
                                   "storage": _storage(KEEP_DAYS["dish"], [use])})
                for c in r.get("composition") or []:
                    t = str(c.get("ingredient") or "")
                    if not t or (c.get("meta") or {}).get("role") == "serving_suggestion":
                        continue
                    try:
                        g = _qty_to_g(t, c) * scale if c.get("quantity") is not None else 0.0
                    except Exception:
                        g = 0.0
                    if g <= 0:
                        continue
                    if t.startswith("base_") and t in index:
                        add("base", t, g, use)
                        continue
                    leg = next((x for x in LEGUMES if re.search(x[0], t)), None)
                    if leg and "sprout" not in t and "canned" not in t and "boiled" not in t:
                        add("legume", t, g, use, cook_min=leg[1], soak=leg[2], yield_factor=leg[3])
                        continue
                    grain = next((x for x in GRAINS if re.search(x[0], t)), None)
                    if grain and "cooked" not in t and "flour" not in t:
                        add("grain", t, g, use, cook_min=grain[1], yield_factor=grain[2], fridge_days=grain[3])
                        continue
                    if NOT_FRESH.search(t):
                        continue
                    if HERB.search(t):
                        add("herb", t, g, use)
                    elif VEG.match(t):
                        add("veg", t, g, use)

    names = names_of([k for _, k in items])
    out_items = []
    for (kind, key), it in items.items():
        if kind == "herb" and it["grams"] < MIN_HERB_G:
            continue
        it["name"] = names.get(key) or key.replace("_", " ")
        it["uses"].sort(key=lambda u: (u["day_index"], u["meal"]))
        if kind == "legume":
            days, freezable = KEEP_DAYS["legume"], True
        elif kind == "grain":
            days, freezable = it.pop("fridge_days"), True
        elif kind == "base":
            days = 14 if BASE_LONG.search(key) else 2 if BASE_SHORT.search(key) else 3
            freezable = True
        else:
            days, freezable = KEEP_DAYS[kind], False
        it["storage"] = _storage(days, it["uses"], freezable)
        # Part utilisée au-delà de la conservation au frigo : congelée (cuissons,
        # préparations) ou préparée plus tard (légumes, herbes)
        late_g = sum(u["grams"] for u in it["uses"] if u["day_index"] + 1 > days)
        if not freezable:
            it["later_grams"] = round(late_g)
            it["grams"] = round(it["grams"] - late_g)
        else:
            it["freeze_grams"] = round(late_g)
            it["grams"] = round(it["grams"])
        for u in it["uses"]:
            u["grams"] = round(u["grams"])
        if kind in ("legume", "grain"):
            it["cooked_grams"] = round(it["grams"] * it["yield_factor"])
            it["active_min"] = 5
        elif kind == "base":
            b = index[key]
            tm = b.get("timing") or {}
            it["active_min"] = int((tm.get("prep_active_min") or 0) + (tm.get("cook_min") or 0)) or 15
            it["passive_min"] = int(tm.get("prep_passive_min") or 0)
        else:
            it["active_min"] = max(1, round(it["grams"] / 100 * (1.5 if kind == "veg" else 0.5))) if it["grams"] else 0
        out_items.append(it)

    # Légumes à tailler plus tard (milieu de semaine) : listés à part
    later = [{"key": i["key"], "name": i["name"], "grams": i["later_grams"], "days": i["storage"]["late_days"]}
             for i in out_items if i.get("later_grams")]
    out_items = [i for i in out_items if not (i["kind"] in ("veg", "herb") and i["grams"] <= 0)]

    soak = sorted((i for i in out_items if i["kind"] == "legume" and i["soak"]), key=lambda i: -i["grams"])
    legumes = sorted((i for i in out_items if i["kind"] == "legume"), key=lambda i: -i["cook_min"])
    grains = sorted((i for i in out_items if i["kind"] == "grain"), key=lambda i: -i["cook_min"])
    bases = sorted((i for i in out_items if i["kind"] == "base"), key=lambda i: -(i["active_min"] + i.get("passive_min", 0)))
    veg = sorted((i for i in out_items if i["kind"] in ("veg", "herb")), key=lambda i: -i["grams"])

    # Durée : actives additionnées ; les cuissons mijotent pendant le reste
    active = sum(i["active_min"] for i in legumes + grains + bases + veg)
    longest_cook = max([i["cook_min"] for i in legumes + grains] or [0])
    total = max(active, longest_cook + 10)
    covered = sorted({(u["day_index"], u["meal"], u["title"]) for i in out_items for u in i["uses"]}
                     | {(d["day_index"], d["meal"], d["title"]) for d in dishes})
    return {
        "eve": [{"key": i["key"], "name": i["name"], "grams": i["grams"]} for i in soak],
        "steps": [
            {"id": "legumes", "title": "Cuire les légumineuses", "items": legumes,
             "tip": "Dans une grande casserole d'eau non salée (le sel durcit la peau), à petits frémissements. "
                    "Égoutter, laisser refroidir, puis au frais en boîtes avec un peu d'eau de cuisson."},
            {"id": "grains", "title": "Cuire les céréales", "items": grains,
             "tip": "Étaler pour refroidir vite, puis au frais dans l'heure. Le riz cuit se garde 24 h : "
                    "congelez en portions celui des jours suivants."},
            {"id": "bases", "title": "Préparations maison", "items": bases,
             "tip": "Pendant que cuisent légumineuses et céréales. Bocaux propres, étiquetés avec la date."},
            {"id": "veg", "title": "Laver et tailler les légumes", "items": veg,
             "tip": "Boîtes hermétiques avec un papier absorbant ; herbes lavées, séchées, roulées dans un linge humide."},
        ],
        "later": sorted(later, key=lambda x: -x["grams"]),
        "dishes": dishes,
        "active_min": active,
        "total_min": total,
        "meals": meals,
        "meals_helped": len({(d, m) for d, m, _ in covered}),
    }
