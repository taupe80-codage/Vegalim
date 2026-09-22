"""Fabrique de recettes au schéma CDC v4, pour les lots d'ajout (new_recipes/n*.py).

Les régimes sont posés à vrai et les allergènes laissés vides : fix_recipe_diet_allergens.py,
lancé juste après, les recalcule à partir de la composition (il ne fait que restreindre).
Les search_tokens, la nutrition et le scoring sont régénérés par rebuild_graphs.py.
"""

DIET_FLAGS = ("vegan", "vegetarian", "gluten_free", "lactose_free", "nut_free")


def recipe(*, rid, fr, en, cuisine, country, region="", city="", dish, servings=4,
           prep=0, rest=0, cook=0, compo, steps, desc, texture=(), taste=(),
           difficulty="easy", spice=0, kid_friendly=True, technique=(), meal=None,
           original=None, allow_similar=(), raw=False):
    """Construit une recette complète.

    compo : [(ingredient, quantité, unité, rôle[, état]), …] ; quantité None = suggestion de service.
    steps : étapes sans numérotation (« Étape N : » est ajouté).
    allow_similar : mots du titre que le contrôle de doublon doit ignorer (mot générique dans la
        langue d'origine, par exemple « nasi » — riz — qui ne fait pas de nasi lemak un nasi goreng).
    """
    lines = []
    for item in compo:
        iid, q, unit, role, *st = item
        lines.append({"ingredient": iid, "quantity": q, "unit": unit,
                      "meta": {"role": role, "form": "", "state": st[0] if st else "raw",
                               "preparation": ""}})
    return {
        "id": rid,
        "titles": {"fr": fr, "en": en, "original": original or en},
        "origin": {"cuisine": cuisine, "country": country, "region": region, "city": city},
        "servings": servings,
        "servings_default": servings,
        "timing": {"prep_active_min": prep, "prep_passive_min": rest, "cook_min": cook,
                   "total_min": prep + rest + cook},
        "composition": lines,
        "tags": {"diet": list(DIET_FLAGS), "meal": [meal or dish], "season": [],
                 "allergens": [], "technique": list(technique), "process": []},
        "result": {"texture": list(texture), "taste": list(taste), "visual": []},
        "scoring": {"confidence": 0.9, "spice_level": spice},
        "dish_type": dish,
        "difficulty_level": difficulty,
        "description": desc,
        "instructions": [f"Étape {n} : {t}" for n, t in enumerate(steps, 1)],
        "diet_flags": {**{f: True for f in DIET_FLAGS}, "raw": raw,
                       "kid_friendly": kid_friendly},
        "_allow_similar": list(allow_similar),
    }
