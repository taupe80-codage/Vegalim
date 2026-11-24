"""
diabetes.py — Ingrédients « adaptés au diabète » et ingrédients à surveiller.

Règle par ingrédient (pour 100 g, champs nutrition_v2) — utilisée par
scripts/nutrition/build_dict_v2.py (drapeau diet_profile.diabetic_friendly)
et ici pour les fiches sans drapeau :
  - moins de 10 g de sucres ;
  - au plus 10 g de glucides assimilables, ou critère « 10:1 » de qualité des
    glucides (glucides totaux / fibres ≤ 10, Mozaffarian et al. 2013) ;
  - sans alcool (≥ 1 g ou sous-catégorie alcools).

Ingrédients à surveiller dans une recette (diabetes_watch) : non adaptés ET
apportant par portion au moins 10 g de glucides assimilables ou 5 g de sucres.
Une pincée de sucre ou une cuillère de farine pour lier une sauce n'y figurent
donc pas.

Module sans dépendance lourde au chargement : build_dict_v2.py l'importe.
"""
from __future__ import annotations

WATCH_CARBS_G = 10.0   # glucides assimilables par portion
WATCH_SUGAR_G = 5.0    # sucres par portion

_ALCOHOL_SUBCATEGORIES = frozenset({"alcohol", "alcohols"})


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def digestible_carbs(v: dict) -> float | None:
    """Glucides assimilables pour 100 g : hors fibres (CNF et USDA publient des
    glucides totaux) et hors polyols (comptés dans les glucides CIQUAL et UE)."""
    c = _num(v.get("carbs_g"))
    if c is None:
        return None
    if v.get("_source") in ("CNF", "USDA"):
        c -= _num(v.get("fiber_g")) or 0.0
    c -= _num(v.get("polyols_g")) or 0.0
    return max(c, 0.0)


def is_diabetic_friendly(v: dict, subcategory: str = "") -> bool | None:
    """Règle ci-dessus ; None quand les données ne permettent pas de conclure.

    Jusqu'à 15 g de sucres admis quand les fibres sont abondantes (rapport
    ≤ 5:1 : farine de pois chiche, 10,9 g de sucres et 10,8 g de fibres pour
    47 g de glucides).

    Sucres non renseignés (fréquent dans USDA et les fiches MANUAL) : comme
    les sucres ne dépassent pas les glucides assimilables, la règle conclut
    « oui » sous 10 g de glucides assimilables et « non » quand le critère
    10:1 échoue (farine de blé, sucre de coco) ; sinon inconnu (kaki séché :
    riche en fibres mais très sucré).
    """
    if (_num(v.get("alcohol_g")) or 0.0) >= 1.0 or subcategory.lower() in _ALCOHOL_SUBCATEGORIES:
        return False
    sugar, fiber = _num(v.get("sugar_g")), _num(v.get("fiber_g"))
    if fiber is None:
        return None
    digest = digestible_carbs(v)
    if digest is None:
        carbs_ok, ratio_ok = fiber >= 2.0, False
    else:
        ratio_ok = fiber >= 2.0 and digest + fiber <= 5.0 * fiber
        carbs_ok = digest <= 10.0 or (fiber >= 2.0 and digest + fiber <= 10.0 * fiber)
    if not carbs_ok:
        return False
    if sugar is None:
        return True if digest is not None and digest <= 10.0 else None
    return sugar < 10.0 or (ratio_ok and sugar < 15.0)


def diabetes_watch(recipe: dict) -> list[dict]:
    """Ingrédients à surveiller pour une portion, du plus chargé en glucides au
    moins chargé : [{ingredient, name, grams, carbs_g, sugar_g}]."""
    from backend.db.data_access import get_data
    from backend.engine.nutrition_engine import compute_nutrition

    breakdown: dict[str, dict] = {}
    compute_nutrition(recipe, breakdown=breakdown)
    out = []
    for token, b in breakdown.items():
        n, grams = b["nutrients"], b["grams"]
        if grams <= 0:
            continue
        ing = get_data.ingredients.get_by_name(token) or {}
        flag = (ing.get("diet_profile") or {}).get("diabetic_friendly")
        if flag is None:
            flag = is_diabetic_friendly(n)
        if flag is not False:
            continue
        carbs = (digestible_carbs(n) or 0.0) * grams / 100.0
        sugar = (_num(n.get("sugar_g")) or 0.0) * grams / 100.0
        if carbs < WATCH_CARBS_G and sugar < WATCH_SUGAR_G:
            continue
        out.append({
            "ingredient": token,
            "name": ing.get("canonical_name_fr") or ing.get("name_fr") or token,
            "grams": round(grams),
            "carbs_g": round(carbs, 1),
            "sugar_g": round(sugar, 1),
        })
    return sorted(out, key=lambda x: -x["carbs_g"])
