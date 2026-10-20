"""
fridge_scoring.py — pondération des ingrédients pour « Mon frigo ».

Avoir des œufs ne doit pas faire remonter une omelette devant un gratin de
courges quand le frigo contient aussi des courges : un ingrédient « spécial »
(tofu, courge butternut, poireau, ghee…) dit beaucoup plus sur ce qu'on peut
cuisiner qu'un produit courant (œufs, lait) ou un basique (sel, poivre, huile,
beurre, farine…).

Chaque ingrédient d'une recette reçoit un poids = niveau × importance :

  niveau       spécial 1.0 · courant 0.4 · accent 0.15 · basique 0.05
  importance   ×3 si l'ingrédient porte la recette (légume, protéine, féculent,
               ou plus d'un cinquième de la masse), ×1 sinon, ×0.5 si facultatif

Le classement mélange deux mesures :
  fit  — part du poids de la recette que le frigo couvre (la recette est-elle
         complète ?)
  use  — poids absolu que la recette tire du frigo, plafonné à _USE_REF (la
         recette met-elle à profit des ingrédients qui comptent ?)
"""
from __future__ import annotations

import re

# ── Niveaux ──────────────────────────────────────────────────────────────────

SPECIAL, COMMON, ACCENT, STAPLE = "special", "common", "accent", "staple"

_TIER_WEIGHT = {SPECIAL: 1.0, COMMON: 0.4, ACCENT: 0.15, STAPLE: 0.05}

# Basiques : présents dans toutes les cuisines, jamais le sujet d'une recette.
_STAPLE_TOKENS = frozenset({
    "salt", "water", "oil", "vinegar", "sugar", "sugars", "stock", "bouillon",
    "broth", "cornstarch", "starch",
})
_STAPLE_PREFIXES = (
    "butter", "vegan_butter", "black_pepper", "white_pepper", "pepper",
    "wheat_flour", "wheat_all_purpose_flour", "baking", "sodium_bicarbonate",
    "bicarbonate",
)
# « beurre » de cacahuète / de sésame n'est pas le beurre de cuisine.
_STAPLE_EXCLUDED = ("peanut", "sesame", "nut_butter", "almond_butter", "tahini")

# Courants : on en a souvent chez soi, mais ils peuvent porter une recette.
_COMMON_EXACT = frozenset({"egg", "whole_egg", "egg_raw", "milk", "cream", "yogurt"})
_COMMON_PREFIXES = (
    "egg_white", "egg_yolk", "egg_hard", "milk", "cream_heavy", "cream_light",
    "yogurt",
)

# Accents : aromates et assaisonnements, par identifiant (côté frigo, où l'on
# ne connaît pas le rôle) ou par rôle (côté recette).
_ACCENT_TOKENS = frozenset({
    "garlic", "onion", "shallot", "ginger", "parsley", "chives", "basil",
    "mint", "thyme", "oregano", "coriander", "cumin", "paprika", "turmeric",
    "cinnamon", "nutmeg", "vanilla", "mustard", "honey", "curry", "bay",
})
_ACCENT_ROLES = frozenset({
    "seasoning", "spice", "herb", "condiment", "sweetener", "garnish",
    "serving_suggestion", "aroma", "aromatic", "aromatic_base",
    "aromatic_support", "acidity", "acidifier", "acid", "flavor",
    "flavor_enhancer", "flavoring", "freshness", "finishing", "accent",
    "umami", "balance", "sweetness", "sweetness_balance", "signature_flavor",
    "heat", "coloring", "glaze", "topping", "sweet_garnish", "garnish_base",
})
# Rôles de simple technique : basiques, quel que soit l'ingrédient.
_STAPLE_ROLES = frozenset({
    "fat", "fat_cooking", "fat_frying", "searing", "wok_searing", "non_stick",
    "cooking_medium", "leavening", "raising_agent", "yeast", "thickener",
    "cooking_stabilizer", "stabilizer", "gelling_agent", "hydration",
    "dilution", "cooking_liquid", "water_extraction", "deglazing",
    "emulsifier", "emulsion", "salt", "preserving",
})

# Rôles qui portent la recette.
_MAIN_ROLES = frozenset({
    "vegetable", "fruit", "protein", "plant_protein", "animal_protein",
    "protein_base", "carbohydrate", "base", "legume", "grain", "starch",
    "main_vegetable", "main_fruit", "main_herb", "main_aromatic", "salad",
    "stuffing", "dough_base", "biscuit_base", "sauce_base", "cheese",
})

_MAIN_BOOST = 3.0
_OPTIONAL_FACTOR = 0.5
_MAIN_MASS_SHARE = 0.2

# Poids tiré du frigo à partir duquel la recette « met à profit » le frigo :
# un ingrédient spécial principal (1.0 × 3) suffit à saturer.
_USE_REF = 3.0
_COMMON_CAP = _TIER_WEIGHT[COMMON] * _MAIN_BOOST
_FIT_SHARE = 0.45

_SPLIT = re.compile(r"[/_]")
_MASS_UNITS = {"g": 1.0, "kg": 1000.0, "ml": 1.0, "cl": 10.0, "l": 1000.0}


def _tokens(iid: str) -> set[str]:
    return set(_SPLIT.split(iid.lower()))


def _has_prefix(iid: str, prefixes: tuple[str, ...]) -> bool:
    """Préfixe à frontière de mot : « butter_salted » oui, « butternut » non."""
    return any(iid == p or iid.startswith((p + "_", p + "/")) for p in prefixes)


def tier_of_id(iid: str) -> str:
    """Niveau d'un ingrédient d'après son seul identifiant (frigo ou recette)."""
    iid = iid.lower()
    if not any(x in iid for x in _STAPLE_EXCLUDED):
        if _has_prefix(iid, _STAPLE_PREFIXES) or _tokens(iid) & _STAPLE_TOKENS:
            return STAPLE
    if iid in _COMMON_EXACT or _has_prefix(iid, _COMMON_PREFIXES):
        return COMMON
    if _tokens(iid) & _ACCENT_TOKENS:
        return ACCENT
    return SPECIAL


def tier_of_item(item: dict) -> str:
    """Niveau d'une ligne de composition : l'identifiant d'abord, puis le rôle."""
    iid = str(item.get("ingredient") or item.get("ingredient_id") or "")
    tier = tier_of_id(iid)
    if tier != SPECIAL:
        return tier
    role = (item.get("meta") or {}).get("role") or ""
    if role in _STAPLE_ROLES:
        return STAPLE
    if role in _ACCENT_ROLES:
        return ACCENT
    return SPECIAL


def _mass(item: dict) -> float:
    try:
        qty = float(item.get("quantity"))
    except (TypeError, ValueError):
        return 0.0
    return qty * _MASS_UNITS.get(str(item.get("unit") or "").lower(), 0.0)


def recipe_weights(composition: list) -> dict[str, tuple[float, str]]:
    """Poids et niveau de chaque ingrédient d'une recette : {id: (poids, niveau)}."""
    items = [i for i in composition if isinstance(i, dict)]
    tiers = {id(i): tier_of_item(i) for i in items}
    # Masse totale hors basiques : l'eau ou l'huile ne disent rien de l'équilibre.
    total_mass = sum(_mass(i) for i in items if tiers[id(i)] != STAPLE)

    weights: dict[str, tuple[float, str]] = {}
    for item in items:
        iid = str(item.get("ingredient") or item.get("ingredient_id") or "").lower()
        if not iid:
            continue
        tier = tiers[id(item)]
        meta = item.get("meta") or {}
        role = meta.get("role") or ""
        share = _mass(item) / total_mass if total_mass else 0.0
        is_main = role in _MAIN_ROLES or (
            tier in (SPECIAL, COMMON) and share >= _MAIN_MASS_SHARE
        )
        w = _TIER_WEIGHT[tier] * (_MAIN_BOOST if is_main and tier != STAPLE else 1.0)
        if meta.get("optional") or role == "serving_suggestion":
            w *= _OPTIONAL_FACTOR
        # Un même identifiant répété garde son poids le plus fort.
        if iid not in weights or w > weights[iid][0]:
            weights[iid] = (w, tier)
    return weights


def relevance(
    weights: dict[str, tuple[float, str]], have: set[str],
) -> tuple[float, float, float]:
    """(pertinence, fit, use) d'une recette pour un frigo, toutes entre 0 et 1.

    Les produits courants (œufs, lait) cumulent au plus _COMMON_CAP dans `use` :
    un frigo d'œufs, de lait et de beurre doit pouvoir faire des crêpes, mais
    pas écraser une recette bâtie sur la courge qu'on a aussi.
    """
    total = sum(w for w, _ in weights.values())
    got = common = 0.0
    for iid, (w, tier) in weights.items():
        if iid not in have:
            continue
        if tier == COMMON:
            common += w
        else:
            got += w
    fit = (got + common) / total if total else 0.0
    use = min((got + min(common, _COMMON_CAP)) / _USE_REF, 1.0)
    return _FIT_SHARE * fit + (1.0 - _FIT_SHARE) * use, fit, use


def has_substance(weights: dict[str, tuple[float, str]], have: set[str]) -> bool:
    """True si la recette tire du frigo autre chose que des basiques et des accents."""
    return any(
        tier in (SPECIAL, COMMON) for iid, (_, tier) in weights.items() if iid in have
    )
