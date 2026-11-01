"""
seasonality.py — Saisonnalité des ingrédients.
Fusionne : seasonality_engine

API :
    in_season(ingredient, month) → bool
    seasonal_ingredients(month)  → list[str]
    season_ratio(recipe, month)  → float | None
    season_bonus(recipe, month)  → float
"""
from __future__ import annotations


# Identifiants CIQUAL des recettes → clés de modules/seasonality.json, qui
# utilise les noms courts d'avant la migration ('spinach' et non
# 'spinach_raw_baby'). Produits frais uniquement : conserves, surgelés,
# séchés, jus, farines et graines ne suivent pas la saison (un rapprochement
# par préfixe ferait de 'tomato_paste_unsalted_canned' une tomate de saison).
# Table relue ; seules comptent les clés à saison réelle (voir _is_seasonal).
SEASON_ID_ALIASES: dict[str, str] = {
    "asparagus_raw": "asparagus", "green_asparagus_raw": "asparagus",
    "white_asparagus_raw_peeled": "asparagus",
    "basil_fresh_herb": "basil",
    "beetroot_raw_root": "beet", "beetroot_cooked_root": "beet",
    "red_bell_pepper_raw": "red_bell_pepper", "green_bell_pepper_raw": "green_bell_pepper",
    "cabbage_raw": "cabbage", "green_cabbage_raw": "cabbage", "white_cabbage_raw": "cabbage",
    "red_cabbage_raw": "cabbage", "savoy_cabbage_raw": "cabbage",
    "cauliflower_raw_flower": "cauliflower",
    "cherry_tomato_raw": "cherry_tomato",
    "sweet_corn_raw_fresh": "corn", "sweet_corn_on_the_cob_cooked": "corn",
    "cucumber_raw": "cucumber", "cucumber_raw_with_skin": "cucumber",
    "oriental_daikon_radish_raw": "daikon",
    "eggplant_raw": "eggplant",
    "fennel_raw": "fennel",
    "french_bean_raw": "green_bean",
    "green_onion_raw": "green_onion",
    "kabocha_squash_raw": "kabocha_squash",
    "kale_raw": "kale", "curly_kale_raw": "kale",
    "mint_fresh_herb": "mint",
    "button_mushroom_raw": "mushroom", "porcini_mushroom_raw": "mushroom",
    "chanterelle_mushroom_raw": "mushroom", "oyster_mushroom_raw": "mushroom",
    "shiitake_mushroom_raw": "shiitake_mushroom",
    "pomegranate_raw": "pomegranate",
    "black_radish_raw": "radish",
    "snow_peas_raw": "snow_pea",
    "spinach_raw_baby": "spinach", "spinach_raw_mature": "spinach",
    "spinach_cooked": "spinach",
    "pumpkin_raw": "pumpkin", "butternut_squash_raw": "squash",
    "butternut_squash_raw_skinless": "squash", "red_kuri_squash_raw_skinless": "squash",
    "sweet_potato_raw": "sweet_potato",
    "turnip_raw": "turnip",
    "green_zucchini_squash_raw": "zucchini",
    "tomato_raw_ripe": "tomato", "tomate": "tomato",
    # Clés disponibles 12 mois sur 12 dans le fichier : sans effet sur le ratio
    "carrot_raw": "carrot", "garlic_raw": "garlic",
    "onion_raw": "onion", "yellow_onion_raw": "onion", "white_onion_raw": "onion",
    "ginger_raw_root_fresh": "ginger",
}


def _db() -> dict:
    # Cherchait un graphe « seasonality » inexistant (get_data.graphs) : la
    # table était toujours vide. Le fichier est data/modules/seasonality.json.
    from backend.core.data_io import load_seasonality
    return load_seasonality() or {}


def _is_seasonal(entry: dict) -> bool:
    """Vraie saison : des mois renseignés, mais pas les 12. Les 243 entrées
    « year_round » (eau, sel, huile…) ne sont pas « de saison »."""
    months = set(entry.get("months") or [])
    return bool(months) and len(months) < 12


def season_key(ingredient_id: str, data: dict | None = None) -> str | None:
    """Clé de seasonality.json pour un id de recette ('spinach_raw_baby' →
    'spinach'), ou None."""
    data = _db() if data is None else data
    iid = str(ingredient_id).lower().strip()
    if iid in SEASON_ID_ALIASES:
        return SEASON_ID_ALIASES[iid]
    return iid if iid in data else None


def in_season(ingredient: str, month: int) -> bool:
    """Retourne True si l'ingrédient est de saison au mois donné (1-12)."""
    data = _db()
    key = season_key(ingredient, data)
    return bool(key) and month in data.get(key, {}).get("months", [])


def seasonal_ingredients(month: int) -> list[str]:
    """Ingrédients (clés de seasonality.json) de saison pour un mois donné,
    hors ingrédients disponibles toute l'année."""
    return [ing for ing, entry in _db().items()
            if _is_seasonal(entry) and month in entry.get("months", [])]


def season_ratio(recipe: dict, month: int, data: dict | None = None) -> float | None:
    """Part des ingrédients saisonniers de la recette qui sont de saison au
    mois donné. None si la recette n'a aucun ingrédient saisonnier connu."""
    data = _db() if data is None else data
    keys = set()
    for item in recipe.get("composition") or recipe.get("ingredients") or []:
        iid = (item.get("ingredient") or item.get("ingredient_id", "")) if isinstance(item, dict) else str(item)
        key = season_key(iid, data) if iid else None
        if key and _is_seasonal(data.get(key, {})):
            keys.add(key)
    if not keys:
        return None
    return sum(1 for k in keys if month in data[k].get("months", [])) / len(keys)


def season_bonus(recipe: dict, month: int | None) -> float:
    """Bonus saisonnalité pour une recette : +2 si >50% des ingrédients
    saisonniers sont de saison, +1 si >25%."""
    if month is None:
        return 0.0
    ratio = season_ratio(recipe, month)
    if ratio is None:
        return 0.0
    return 2.0 if ratio > 0.5 else (1.0 if ratio > 0.25 else 0.0)
