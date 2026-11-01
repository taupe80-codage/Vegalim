"""
astro.py — Correspondance ingrédients de recette → astro_nutrition.json.

API :
    astro_key(ingredient_id) → str | None
    astro_info(ingredient_id) → dict  {element, moon_phases} ou {}

astro_nutrition.json utilise 310 noms génériques d'avant la migration CIQUAL
('tomato', 'oeuf', 'sauce_soja') ; les recettes utilisent les ids CIQUAL
('tomato_raw_ripe', 'egg_raw', 'soy_sauce_shoyu_reduced_sodium') : seuls 58
des 593 ids se retrouvaient tels quels dans la carte.

Résolution, dans l'ordre :
    1. ASTRO_ID_ALIASES (table relue : ingrédients courants sans
       correspondance automatique, et corrections des correspondances
       automatiques fausses) ;
    2. id exact ;
    3. plus long préfixe de segments présent dans la carte
       ('almond_raw_skinless_unsalted' → 'almond') ;
    4. ingredient_price_map (data_io.resolve_catalog_key).
ASTRO_NO_MATCH écarte les rapprochements automatiques absurdes.
"""
from __future__ import annotations

ASTRO_ID_ALIASES: dict[str, str] = {
    # Œufs, laitages
    "egg_raw": "oeuf", "egg_yolk_raw": "oeuf", "egg_white_raw": "oeuf",
    "egg_hard_boiled": "oeufs_dur", "egg_pasta_raw_dried": "pasta",
    "milk_liquid_uht_3_5pct": "lait", "milk_liquid_pasteurized_3_5pct": "lait",
    "milk_powder_whole": "lait", "buttermilk_1pct": "lait",
    "condensed_milk_concentrated_sweetened_canned_whole": "lait",
    "condensed_milk_concentrated_unsweetened_whole": "lait",
    "kefir_fermented": "yogurt",
    "cream": "creme", "cream_heavy": "creme", "cream_heavy_refrigerated_18pct": "creme",
    "cream_heavy_refrigerated_30pct": "creme", "cream_liquid_uht": "creme",
    "cream_sour_18pct": "creme", "cream_sour_fermented": "creme",
    "sour_cream_fermented_18pct": "creme",
    "base_soy_cream_4dc027": "creme", "base_oat_cream_954865": "creme",
    "base_coconut_cream_10c770": "lait_coco",
    "cows_milk_mozzarella_cow": "mozzarella",
    "mascarpone": "fresh_cheese", "cream_cheese_block_whole_cow": "fresh_cheese",
    "cottage_cheese_4pct_cow": "fresh_cheese",
    "comte_cow": "cheese", "emmental_de_savoie_cow": "cheese", "tomme_de_savoie_cow": "cheese",
    "gouda_cow": "cheese", "provolone_paste_cow": "cheese", "camembert_pasteurized_cow": "cheese",
    "roquefort": "cheese", "pecorino_sheep": "cheese", "cotija_block_cow": "cheese",
    "queso_fresco_block_cow": "cheese", "queso_chihuahua_whole_cow": "cheese",
    "goat_cheese_log": "cheese", "base_halloumi_293d5e": "cheese",
    "base_vegan_cheddar_024998": "cheddar_vegane",
    "base_fromage_en_grain_a00941": "fromage_en_grain",
    "base_salted_ricotta_1ecd1c": "salted_ricotta",
    "nutritional_yeast_flakes": "levure_maltee",
    # Laits et dérivés végétaux
    "coconut_milk_plant": "lait_coco", "coconut_flesh_dried": "lait_coco",
    "coconut_flesh_fresh": "lait_coco",
    "oat_milk_refrigerated_plain_plant": "oats",
    "base_cashew_milk_71947e": "noix_de_cajou",
    "cashew_nuts_raw": "noix_de_cajou", "cashew_nuts_grilled_unsalted": "noix_de_cajou",
    "cashew_butter_plain_plant": "noix_de_cajou",
    "sesame_tahini_raw_butter_seed_plant": "tahini",
    "edamame_raw": "soybean",
    # Légumes
    "potato_raw_flesh": "pommes_de_terre", "potato_raw_with_skin": "pommes_de_terre",
    "potato_boiled_with_skin": "pommes_de_terre", "potato_gnocchi_to_cook": "gnocchi",
    "shallot_raw": "onion",
    "leeks": "poireau", "leeks_raw": "poireau",
    "red_cabbage_raw": "cabbage", "white_cabbage_raw": "cabbage", "savoy_cabbage_raw": "cabbage",
    "collard_raw": "kale", "curly_kale_raw": "kale",
    "celeriac": "celery", "celeriac_raw": "celery",
    "green_salad_raw_plain": "lettuce", "arugula": "lettuce", "arugula_raw": "lettuce",
    "watercress": "lettuce",
    "endive_raw": "chicory", "belgium_endive_raw": "chicory", "green_chicory_raw": "chicory",
    "butternut_squash_raw_skinless": "squash",
    "green_asparagus_raw": "asparagus", "white_asparagus_raw_peeled": "asparagus",
    "beetroot_cooked_root": "beet",
    "sweet_corn_canned": "corn", "sweet_corn_on_the_cob_cooked": "corn",
    "pickles_cucumber_canned_in_vinegar": "cucumber", "pickles_raw": "cucumber",
    "red_hot_chili_pepper_raw": "red_chili", "chilli_pepper_raw": "red_chili",
    "serrano_pepper_raw": "green_chili", "jalapeno_pepper_raw": "green_chili",
    "red_hot_chili_pepper_spice_dried": "dried_chili",
    "ancho_pepper_spice_dried": "ancho_chili",
    # Légumineuses
    "white_bean_boiled": "white_bean_cooked", "white_bean_canned": "white_bean_cooked",
    "white_bean_dried_canned": "white_bean_cooked", "white_bean_raw": "white_bean_cooked",
    "flageolet_bean_canned": "white_bean_cooked", "lima_bean_boiled_canned": "white_bean_cooked",
    "gigante_bean": "haricots_geant",
    "kidney_bean_boiled": "red_bean_cooked", "kidney_bean_dried": "red_bean_cooked",
    "red_bean_paste": "red_bean_cooked",
    "black_eyed_peas_cowpeas_boiled": "black_eyed_bean_cooked",
    "black_eyed_peas_cowpeas_dried": "black_eyed_bean_cooked",
    "pinto_bean_boiled": "bean", "mung_bean_dried": "bean", "pigeon_peas_red_gram_raw": "bean",
    "broadbeans_fava_beans_boiled_fresh": "fava_bean",
    "broadbeans_fava_beans_raw_dried": "fava_bean", "broadbeans_fava_beans_raw_fresh": "fava_bean",
    "green_peas_raw": "dried_pea", "green_peas_boiled_frozen_salted": "dried_pea",
    "aquafaba": "chickpea",
    # Céréales, farines, pâtes
    "wheat_flour_t55": "flour", "whole_wheat_flour_seed": "flour",
    "vital_wheat_gluten_flour": "flour",
    "cornstarch_flour": "starch", "potato_starch_flour": "fecule",
    "rye_flour": "farine_de_seigle", "teff_flour": "farine_de_teff",
    "cassava_flour": "farine_de_manioc", "manioc_flour": "farine_de_manioc",
    "chickpea_flour": "farine_de_pois_chiche",
    "hominy_boiled_flour_canned": "hominy_corn",
    "tapioca_raw_dried": "fecule_de_tapioca",
    "cornmeal_whole_dried": "polenta",
    "wheat_semolina_raw": "semoule_de_couscous_moyenne",
    "durum_wheat_semolina": "semoule_de_couscous_moyenne",
    "freekeh_immature_wheat_raw_cracked_seed": "bulgur",
    "quinoa_raw_dried": "quinoa_grain",
    "white_rice_long_grain_seed_dried": "rice", "white_rice_cooked_short_grain_seed": "rice",
    "tteok": "gateaux_de_riz",
    "croutons_dried_plain_pre_packaged": "bread", "hot_dog_bun_pre_packaged": "bread",
    "bagel": "bread",
    "puff_pastry_all_butter_raw_paste_pre_packaged": "shortcrust_pastry",
    "puff_pastry_vegetable_fat_raw_paste_plant": "shortcrust_pastry",
    "base_shortcrust_e6e9f0": "shortcrust_pastry",
    "base_spaetzle_a22916": "spatzle",
    "base_reshteh_noodles_6f783e": "reshteh_noodles",
    "base_nouilles_de_patate_douce_fdeb79": "nouilles_de_patate_douce",
    # Sauces, pâtes et bouillons
    "soy_sauce_shoyu_reduced_sodium": "sauce_soja", "soy_sauce_tamari": "sauce_soja",
    "miso_fermented": "miso_paste", "base_miso_paste_1faeef": "miso_paste",
    "base_japanese_curry_roux_385e52": "japanese_curry_roux",
    "base_hoisin_033e33": "hoisin_sauce", "base_laksa_paste_bc7fd5": "laksa_paste",
    "base_mala_broth_1ab129": "mala_broth", "base_mole_d0034f": "mole_sauce",
    "base_dashi_broth_a3a517": "bouillon_dashi_vegetarien",
    "base_teriyaki_03b2ff": "teriyaki_sauce", "base_za_atar_2badf3": "zaatar",
    "black_olive_canned_in_oil": "olive", "capers_canned_in_vinegar": "capre",
    # Fruits à coque, graines
    "pine_nuts_raw": "pine_nut",
    "peanut_raw": "cacahuete", "peanut_roasted_salted_dry": "cacahuete",
    "flaxseed_linseed_ground": "ground_flaxseeds",
    # Sucres, cacao, thé
    "sugars_granulated": "sugar", "molasses": "sugar", "agave_syrup": "sugar",
    "cocoa_powder_unsweetened": "dark_chocolate",
    "matcha_green_tea_powder": "matcha_tea",
    # Herbes, épices, algues
    "coriander": "coriander_ground", "coriander_raw_fresh_herb": "coriander_ground",
    "coriander_spice_leaf_dried": "coriander_ground", "coriander_spice_seed": "coriander_ground",
    "oregano_spice_dried": "origan", "marjoram_spice_dried": "marjolaine",
    "nutmeg": "noix_de_muscade", "bay_leaf": "feuille_laurier",
    "spearmint_dried_herb": "mint",
    "nori_dried": "feuilles_nori",
    "japanese_kombu_dried": "dried_seaweed", "agar_dried": "dried_seaweed",
    # Fruits
    "blueberry": "myrtill", "blueberry_raw": "myrtill", "bilberry_raw": "myrtill",
}

# Rapprochements automatiques (préfixe ou table des prix) à écarter
ASTRO_NO_MATCH: frozenset[str] = frozenset({
    "rose_water",            # → water
    "orange_blossom_water",  # → orange
    "vegan_butter",          # → butter (graisse végétale, pas du beurre)
})


def _map() -> dict:
    from backend.core.data_io import load_astro_nutrition
    return load_astro_nutrition() or {}


def astro_key(ingredient_id: str, data: dict | None = None) -> str | None:
    """Clé d'astro_nutrition.json pour un id de recette, ou None."""
    data = _map() if data is None else data
    iid = str(ingredient_id).lower().strip()
    if not iid or iid in ASTRO_NO_MATCH:
        return None
    alias = ASTRO_ID_ALIASES.get(iid)
    if alias:
        return alias if alias in data else None
    if iid in data:
        return iid
    seg = iid.split("/")[0].split("_")
    for n in range(len(seg) - 1, 0, -1):
        key = "_".join(seg[:n])
        if key in data:
            return key
    from backend.core.data_io import resolve_catalog_key
    return resolve_catalog_key(iid, data)


def astro_info(ingredient_id: str, data: dict | None = None) -> dict:
    """{element, moon_phases} pour un id de recette, ou {} s'il n'est pas couvert."""
    data = _map() if data is None else data
    key = astro_key(ingredient_id, data)
    return data.get(key, {}) if key else {}


# L'eau de cuisson pèserait plus que tout le reste (« Eau » dominant pour
# toutes les soupes) : exclue de la pondération.
_ASTRO_IGNORED_KEYS = frozenset({"water", "sparkling_water"})


def astro_shares(recipe: dict, data: dict | None = None) -> tuple[dict, dict]:
    """Parts pondérées par le poids des ingrédients couverts :
    ({élément: part}, {phase_lunaire: part}), parts entre 0 et 1.

    Pondération en grammes (5 g de sel ne pèsent pas autant que 400 g de
    courgette) ; si aucune quantité n'est connue, chaque ingrédient compte 1.
    """
    from collections import defaultdict
    from backend.engine.rule_engine.diet import _item_grams
    data = _map() if data is None else data
    items = []
    for c in recipe.get("composition") or []:
        if not isinstance(c, dict):
            continue
        key = astro_key(c.get("ingredient") or c.get("ingredient_id") or "", data)
        if key and key not in _ASTRO_IGNORED_KEYS:
            items.append((data[key], _item_grams(c, "") or 0.0))
    if not items:
        return {}, {}
    if not any(g > 0 for _, g in items):
        items = [(info, 1.0) for info, _ in items]
    total = sum(g for _, g in items)
    elements: dict[str, float] = defaultdict(float)
    moons: dict[str, float] = defaultdict(float)
    for info, g in items:
        if info.get("element"):
            elements[info["element"].lower()] += g / total
        for phase in info.get("moon_phases", []):
            moons[phase.lower()] += g / total
    return dict(elements), dict(moons)


def dominant_element(recipe: dict, data: dict | None = None) -> str | None:
    """Élément (minuscules : feu | terre | air | eau) qui pèse le plus."""
    elements, _ = astro_shares(recipe, data)
    return max(elements, key=elements.get) if elements else None
