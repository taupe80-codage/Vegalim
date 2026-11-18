#!/usr/bin/env python3
"""
fix_price_mapping_2026_11_16.py — fiabilise le chiffrage des recettes.

Constats (2026-11-16, 894 plats) :
  * 375 recettes avaient au moins un ingrédient sans prix (compté 0 €) : 140 ids
    de recettes n'étaient reliés à aucune entrée de prices_catalog.json, dont
    des produits courants (cannelle, sucre, farine T55, lait, feta, gruyère…) ;
  * des liens faux dans ingredient_price_map.json : piment frais → poivre
    (86 €/kg, 97 recettes), lait de coco / d'avoine / d'amande → lait de vache,
    farine d'amande / de pois chiche / de manioc → farine de blé, tahini et
    purées d'oléagineux → beurre, pâte feuilletée → beurre, eau de rose → eau,
    huile de truffe → huile neutre, cèpes et girolles → champignons de Paris…
  * des prix aberrants dans le catalogue (kiwi 3,48 € pièce, fenouil 21 €/kg,
    brocoli 11 €/kg, botte de persil 2,77 €, rhum 2,73 € la bouteille…) ;
  * les jus d'agrumes étaient chiffrés au poids du fruit (≈ 3 fois trop bas :
    un citron donne ≈ 40 ml de jus).

Tous les prix ajoutés ou corrigés ici sont des ESTIMATIONS manuelles de prix
moyens en grande surface (novembre 2026, marque de distributeur), pas des
relevés. Idempotent.

Usage :
    python scripts/fix_price_mapping_2026_11_16.py --dry-run
    python scripts/fix_price_mapping_2026_11_16.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
FLAVOR_PATH = ROOT / "backend/data/graphs/flavor_graph.json"
CARBON_PATH = ROOT / "backend/data/config/carbon_footprint.json"
MAP_PATH = ROOT / "backend/data/config/ingredient_price_map.json"
TODAY = "2026-11-16"


def pkg(qty, unit, price, label):
    return {"qty": qty, "unit": unit, "price": price, "label": label}


# ── Nouvelles entrées du catalogue ─────────────────────────────────────────────
NEW_ENTRIES: dict[str, dict] = {
    "plant_milk":       {"name_fr": "Boisson végétale (amande, avoine, soja)", "packages": [pkg(1000, "ml", 1.95, "brique 1L")]},
    "almond_butter":    {"name_fr": "Purée d'amande", "packages": [pkg(250, "g", 6.50, "pot 250g")]},
    "cashew_butter":    {"name_fr": "Purée de cajou", "packages": [pkg(250, "g", 6.90, "pot 250g")]},
    "rose_water":       {"name_fr": "Eau de rose", "packages": [pkg(250, "ml", 3.20, "flacon 25cl")]},
    "orange_blossom_water": {"name_fr": "Eau de fleur d'oranger", "packages": [pkg(250, "ml", 2.40, "flacon 25cl")]},
    "sun_dried_tomato": {"name_fr": "Tomates séchées", "packages": [pkg(280, "g", 3.20, "bocal 280g")]},
    "truffle_oil":      {"name_fr": "Huile aromatisée à la truffe", "packages": [pkg(100, "ml", 6.90, "flacon 10cl")]},
    "nut_oil":          {"name_fr": "Huile de noix ou de noisette", "packages": [pkg(500, "ml", 5.90, "bouteille 50cl")]},
    "wild_mushroom":    {"name_fr": "Champignons sauvages frais (cèpes, girolles)", "packages": [pkg(250, "g", 8.50, "barquette 250g")]},
    "dates":            {"name_fr": "Dattes", "packages": [pkg(500, "g", 3.50, "boîte 500g")]},
    "condensed_milk":   {"name_fr": "Lait concentré", "packages": [pkg(397, "g", 2.10, "boîte 397g")]},
    "camembert":        {"name_fr": "Camembert", "packages": [pkg(250, "g", 2.20, "boîte 250g")]},
    "cider":            {"name_fr": "Cidre brut", "packages": [pkg(750, "ml", 2.90, "bouteille 75cl")]},
    "fig":              {"name_fr": "Figues fraîches", "packages": [pkg(250, "g", 2.90, "barquette 250g")]},
    "lotus_root":       {"name_fr": "Racine de lotus", "packages": [pkg(300, "g", 3.90, "sachet 300g")]},
    "milk_powder":      {"name_fr": "Lait en poudre", "packages": [pkg(300, "g", 3.90, "boîte 300g")]},
    "millet":           {"name_fr": "Millet", "packages": [pkg(500, "g", 2.40, "sachet 500g")]},
    "mung_bean":        {"name_fr": "Haricots mungo secs", "packages": [pkg(500, "g", 2.90, "sachet 500g")]},
    "pecan":            {"name_fr": "Noix de pécan", "packages": [pkg(125, "g", 3.90, "sachet 125g")]},
    "chayote":          {"name_fr": "Christophine (chayote)", "packages": [pkg(1, "piece", 1.50, "pièce ~350g")], "unit_weight_g": 350},
    "poppy_seed":       {"name_fr": "Graines de pavot", "packages": [pkg(100, "g", 2.50, "sachet 100g")]},
    "sour_cherry":      {"name_fr": "Griottes", "packages": [pkg(350, "g", 3.50, "bocal 350g")]},
    "sage":             {"name_fr": "Sauge fraîche", "packages": [pkg(1, "piece", 1.50, "barquette 20g")], "unit_weight_g": 20},
    "soy_flour":        {"name_fr": "Farine de soja", "packages": [pkg(500, "g", 3.50, "sachet 500g")]},
    "wheat_gluten":     {"name_fr": "Gluten de blé", "packages": [pkg(500, "g", 6.50, "sachet 500g")]},
    "prune":            {"name_fr": "Pruneaux", "packages": [pkg(250, "g", 2.90, "sachet 250g")]},
    "falafel":          {"name_fr": "Falafels prêts à cuire", "packages": [pkg(220, "g", 2.90, "barquette 220g")]},
    # Jus frais : prix du fruit pressé (citron ≈ 40 ml, citron vert ≈ 30 ml,
    # orange ≈ 80 ml) — chiffrer le jus au poids du fruit le sous-estimait ≈ 3 fois.
    "lemon_juice_fresh": {"name_fr": "Citron (pour le jus)", "packages": [
        pkg(40, "ml", 0.55, "1 citron (≈ 40 ml de jus)"), pkg(200, "ml", 2.21, "filet 5 citrons (≈ 200 ml de jus)")]},
    "lime_juice_fresh_fruit": {"name_fr": "Citron vert (pour le jus)", "packages": [
        pkg(30, "ml", 0.60, "1 citron vert (≈ 30 ml de jus)"), pkg(150, "ml", 2.63, "filet 5 citrons verts (≈ 150 ml de jus)")]},
    "orange_juice_fresh": {"name_fr": "Oranges (pour le jus)", "packages": [
        pkg(400, "ml", 2.61, "1 kg d'oranges (≈ 400 ml de jus)")]},
}

# ── Prix corrigés dans le catalogue : clé → (label du paquet → nouveau prix) ───
PRICE_FIXES: dict[str, dict[str, float]] = {
    "kiwi":         {"pièce": 0.40},
    "fennel":       {"pièce": 1.10},
    "broccoli":     {"tête ~500g": 1.60},
    "chicory":      {"pièce": 1.80},
    "chinese_cabbage": {"pièce ~1kg": 2.50},
    "cucumber":     {"pièce ~400g": 1.00},
    "lettuce":      {"pièce": 1.10},
    "leek":         {"2 poireaux": 1.30},
    "radish":       {"botte ~200g": 1.20},
    "dandelion_greens": {"200g": 3.00},
    "passion_fruit": {"pièce": 0.70},
    "pomegranate":  {"pièce": 1.80},
    "grapefruit":   {"pièce": 1.00},
    "asparagus":    {"botte 500g": 4.50},
    "chili_pepper": {"2 piments": 0.40},
    "lemongrass":   {"2 tiges": 1.50},
    "bagel":        {"pièce": 0.65},
    "croutons":     {"sachet 100g": 1.50},
    "parsley":      {"bouquet": 1.20},
    "mint":         {"bouquet": 1.30},
    "chives":       {"barquette 20g": 1.50},
    "aneth":        {"barquette 20g": 1.50},
    "tarragon":     {"bouquet": 1.60},
    "chervil":      {"bouquet": 1.50},
    "thyme":        {"bouquet 20g": 1.50},
    "rosemary":     {"bouquet 20g": 1.50},
    "rum":          {"bouteille 70cl": 14.90},
    "kirsch":       {"bouteille 70cl": 16.90},
    "calvados":     {"bouteille 70cl": 16.90},
    "salt":         {"paquet 1kg": 0.65},
    "vinegar":      {"bouteille 1L": 1.20},
    "canola_oil":   {"bouteille 1L": 2.20},
    "sauce_soja":   {"bouteille 15cl": 2.60},
    "olive_oil":    {"1L": 9.50},
}

# Paquets dont la quantité ou le libellé change (clé → label actuel → nouveau paquet)
PACKAGE_REPLACE: dict[str, dict[str, dict]] = {
    "parsley":   {None: pkg(1, "piece", 1.20, "bouquet")},
    "leek":      {None: pkg(2, "piece", 1.30, "2 poireaux")},
    "radish":    {None: pkg(200, "g", 1.20, "botte ~200g")},
    "dandelion_greens": {None: pkg(200, "g", 3.00, "200g")},
    "asparagus": {None: pkg(500, "g", 4.50, "botte 500g")},
    "chili_pepper": {None: pkg(2, "piece", 0.40, "2 piments")},
    "lemongrass": {None: pkg(2, "piece", 1.50, "2 tiges")},
    "croutons":  {None: pkg(100, "g", 1.50, "sachet 100g")},
    "mint":      {None: pkg(1, "piece", 1.30, "bouquet")},
    "chives":    {None: pkg(20, "g", 1.50, "barquette 20g")},
    "aneth":     {None: pkg(20, "g", 1.50, "barquette 20g")},
    "tarragon":  {None: pkg(1, "piece", 1.60, "bouquet")},
    "chervil":   {None: pkg(1, "piece", 1.50, "bouquet")},
    "thyme":     {None: pkg(20, "g", 1.50, "bouquet 20g")},
    "rosemary":  {None: pkg(20, "g", 1.50, "bouquet 20g")},
    "rum":       {None: pkg(700, "ml", 14.90, "bouteille 70cl")},
    "kirsch":    {None: pkg(700, "ml", 16.90, "bouteille 70cl")},
    "calvados":  {None: pkg(700, "ml", 16.90, "bouteille 70cl")},
    "salt":      {None: pkg(1000, "g", 0.65, "paquet 1kg")},
    "vinegar":   {None: pkg(1000, "ml", 1.20, "bouteille 1L")},
    "canola_oil": {None: pkg(1000, "ml", 2.20, "bouteille 1L")},
    "sauce_soja": {None: pkg(150, "ml", 2.60, "bouteille 15cl")},
}

# Poids moyen d'une pièce (pour chiffrer des grammes quand le catalogue vend à la pièce)
UNIT_WEIGHTS: dict[str, float] = {
    "parsley": 60, "mint": 40, "tarragon": 25, "chervil": 30, "fennel": 300,
    "lemongrass": 25, "passion_fruit": 50, "basil": 50, "leek": 200,
    "chili_pepper": 15, "baguette": 250, "lettuce": 300, "green_papaya": 800,
    "onion": 150,
}

# Le safran : la dose de 0,1 g reste ; un pot de 1 g, courant en épicerie fine, coûte moins au gramme.
EXTRA_PACKAGES: dict[str, list[dict]] = {
    "saffron": [pkg(1, "g", 14.90, "pot 1g")],
    "blueberry": [pkg(500, "g", 4.50, "surgelées 500g")],
}

# ── Table id de recette → clé du catalogue ─────────────────────────────────────
MAP_FIXES: dict[str, str] = {
    # liens faux corrigés
    "almond_butter_plain_plant": "almond_butter",
    "almond_flour": "almond",
    "almond_milk_refrigerated_unsweetened_plant": "plant_milk",
    "oat_milk_refrigerated_plain_plant": "plant_milk",
    "soybean_milk_unsweetened_plant": "plant_milk",
    "soybean_yogurt_plain_plant": "yogurt",
    "coconut_milk_plant": "lait_coco",
    "cows_milk_mozzarella_cow": "mozzarella",
    "cream_cheese_block_whole_cow": "fresh_cheese",
    "sour_cream_fermented_18pct": "creme_fraiche",
    "chilli_pepper_raw": "chili_pepper",
    "jalapeno_pepper_raw": "chili_pepper",
    "ancho_pepper_spice_dried": "dried_chili",
    "red_hot_chili_pepper_spice_dried": "dried_chili",
    "white_pepper_spice": "black_pepper",
    "black_olive_canned_in_oil": "olive",
    "capers_canned_in_vinegar": "capre",
    "cashew_butter_plain_plant": "cashew_butter",
    "sesame_tahini_raw_butter_seed_plant": "tahini",
    "puff_pastry_all_butter_raw_paste_pre_packaged": "puff_pastry",
    "cassava_flour": "farine_de_manioc",
    "sweet_potato_flour": "farine_de_manioc",
    "chickpea_flour": "farine_de_pois_chiche",
    "rye_flour": "farine_de_seigle",
    "teff_flour": "farine_de_teff",
    "buckwheat_flour": "buckwheat",
    "cornstarch_flour": "fecule",
    "potato_starch_flour": "fecule",
    "hominy_boiled_flour_canned": "hominy_corn",
    "lemon_grass_fresh_herb": "lemongrass",
    "nutritional_yeast_flakes": "levure_maltee",
    "orange_blossom_water": "orange_blossom_water",
    "rose_water": "rose_water",
    "potato_gnocchi_to_cook": "gnocchi",
    "pumpkin_squash_raw_seed": "pumpkin_seeds",
    "rice_paper": "rice_wrapper",
    "tomato_dried_in_oil": "sun_dried_tomato",
    "tomato_sauce_salted_canned": "sauce_tomate",
    "truffle_oil": "truffle_oil",
    "hazelnut_oil_plant": "nut_oil",
    "walnut_oil_plant": "nut_oil",
    "canola_oil_plant": "canola_oil",
    "coriander_spice_seed": "coriander_ground",
    "coriander_spice_leaf_dried": "coriander_ground",
    "coconut_sugar": "palm_sugar",
    "porcini_mushroom_raw": "wild_mushroom",
    "chanterelle_mushroom_raw": "wild_mushroom",
    "lemon_juice": "lemon_juice_fresh",
    "lime_juice_fresh": "lime_juice_fresh_fruit",
    # ids sans lien
    "almond_raw_skinless_unsalted": "almond",
    "apple_raw": "apple",
    "golden_apple_raw_with_skin": "apple",
    "arugula_raw": "arugula",
    "barley_raw_whole_seed": "barley",
    "beetroot_cooked_root": "beet",
    "belgium_endive_raw": "endive",
    "bilberry_raw": "blueberry",
    "blueberry_raw": "blueberry",
    "black_eyed_peas_cowpeas_dried": "black_eyed_peas",
    "black_radish_raw": "daikon",
    "broadbeans_fava_beans_boiled_fresh": "fava_bean",
    "broadbeans_fava_beans_raw_dried": "fava_bean",
    "broadbeans_fava_beans_raw_fresh": "fava_bean",
    "buckwheat_groats_roasted_dried_dry": "buckwheat",
    "buttermilk_1pct": "milk",
    "butternut_squash_raw_skinless": "butternut",
    "cabbage_raw": "cabbage",
    "red_cabbage_raw": "cabbage",
    "savoy_cabbage_raw": "cabbage",
    "white_cabbage_raw": "cabbage",
    "calvados_liquid": "calvados",
    "camembert_pasteurized_cow": "camembert",
    "cardamom_powder": "cardamom",
    "cashew_nuts_grilled_unsalted": "cashew",
    "chasselas_grape_raw": "grape",
    "chayote_raw": "chayote",
    "cheddar_cow": "cheddar",
    "chickpea_rinsed_canned": "chickpea",
    "chicory_greens_raw_leaf": "chicory",
    "green_chicory_raw": "chicory",
    "cinnamon_powder": "cinnamon",
    "coffee_ground": "coffee",
    "collard_raw": "kale",
    "curly_kale_raw": "kale",
    "mustard_raw_leaf": "kale",
    "condensed_milk_concentrated_sweetened_canned_whole": "condensed_milk",
    "condensed_milk_concentrated_unsweetened_whole": "condensed_milk",
    "corn_flour_seed": "precooked_corn_flour",
    "cornmeal_whole_dried": "polenta",
    "cotija_block_cow": "feta",
    "queso_fresco_block_cow": "feta",
    "queso_chihuahua_whole_cow": "cheese",
    "cottage_cheese_4pct_cow": "cottage_cheese",
    "couscous_to_cook_seed_dried": "couscous",
    "cream_heavy_refrigerated_30pct": "cream",
    "cream_liquid_uht": "cream",
    "cream_sour_18pct": "creme_fraiche",
    "cream_sour_fermented": "creme_fraiche",
    "cucumber_raw": "cucumber",
    "date_with_skin_dried": "dates",
    "dry_cider_liquid_unsweetened": "cider",
    "durum_wheat_semolina": "semolina",
    "wheat_semolina_raw": "semolina",
    "edamame_raw": "edamame",
    "egg_pasta_raw_dried": "pasta",
    "emmental_de_savoie_cow": "cheese",
    "gouda_cow": "cheese",
    "provolone_paste_cow": "cheese",
    "goat_cheese_log": "cheese",
    "pecorino_sheep": "parmesan",
    "european_chestnuts_sweet_cooked": "chestnuts",
    "falafel": "falafel",
    "fennel_spice_seed": "anise_seed",
    "feta_cow": "feta",
    "fig_raw": "fig",
    "freekeh_immature_wheat_raw_cracked_seed": "bulgur",
    "green_asparagus_raw": "asparagus",
    "white_asparagus_raw_peeled": "asparagus",
    "green_peas_boiled_frozen_salted": "pea",
    "gruyere_whole_cow": "gruyere_cheese",
    "hazelnut_dry_roasted_dried_unsalted": "hazelnut",
    "hot_dog_bun_pre_packaged": "bread",
    "jackfruit_raw": "jackfruit",
    "kefir_fermented": "yogurt",
    "kidney_bean_dried": "kidney_beans",
    "pinto_bean_boiled": "kidney_beans",
    "kiwi_raw": "kiwi",
    "lima_bean_boiled_canned": "white_bean",
    "white_bean_canned": "white_bean",
    "white_bean_dried_canned": "white_bean",
    "white_bean_raw": "white_bean",
    "lime_raw_juice_fresh": "lime_juice_fresh_fruit",
    "orange_raw_juice_fresh": "orange_juice_fresh",
    "lotus_raw_root": "lotus_root",
    "mango_raw": "mango",
    "marjoram_spice_dried": "marjolaine",
    "marsala_liquid": "marsala",
    "mascarpone_cow": "mascarpone",
    "milk_liquid_pasteurized_3_5pct": "milk",
    "milk_powder_whole": "milk_powder",
    "millet_raw_whole_seed": "millet",
    "mung_bean_dried": "mung_bean",
    "nori_dried": "feuilles_nori",
    "oregano_spice_dried": "origan",
    "palm_oil_refined_plant": "palm_oil",
    "peanut_butter_natural_plant": "peanut_butter",
    "pecans_nuts_raw": "pecan",
    "pickles_cucumber_canned_in_vinegar": "pickles",
    "pigeon_peas_red_gram_raw": "chana_dal",
    "plantain_banana_raw_ripe": "plantain",
    "poppy_spice_seed": "poppy_seed",
    "prune_raw_pitted_dried": "prune",
    "red_radish_raw": "radish",
    "ricotta_whole_cow": "ricotta",
    "roquefort_sheep": "roquefort",
    "rum_liquid": "rum",
    "saffron_spice": "saffron",
    "sage_fresh_herb": "sage",
    "sauerkraut_canned_low_sodium": "sauerkraut",
    "serrano_pepper_raw": "chili_pepper",
    "sesame_seed_hulled_dried": "sesame",
    "shiitake_mushroom_dried": "shiitake_dried",    # entrée propre depuis fix_prices_2026_11_19
    "sour_cherry_canned_in_water": "sour_cherry",
    "sour_cherry_raw": "sour_cherry",
    "soybean_boiled_dried": "soybean",
    "soybean_flour_raw_whole": "soy_flour",
    "spearmint_dried_herb": "mint",
    "strawberry_raw": "strawberry",
    "sugars_granulated": "sugar",
    "sunflower_seed_dried": "sunflower_seeds",
    "sweet_corn_canned": "corn",
    "sweet_corn_on_the_cob_cooked": "corn",
    "tapioca_raw_dried": "fecule_de_tapioca",
    "tea_leaf": "tea",
    "tofu_smoked_pre_packaged": "tofu",
    "tomato_crushed_canned": "sauce_tomate",
    "tomato_dried": "sun_dried_tomato",
    "vital_wheat_gluten_flour": "wheat_gluten",
    "watercress_raw": "watercress",
    "watermelon_raw": "melon",
    "wheat_flour_t55": "flour",
    "whole_wheat_flour_seed": "flour",
    "white_rice_cooked_short_grain_seed": "riz_rond",
    "white_rice_long_grain_seed_dried": "rice",
    "yogurt_fermented_plain": "yogurt",
    "yogurt_greek_plain_4pct": "yogurt",
}

# Liens retirés : aucun produit du catalogue ne correspond (mieux vaut « prix inconnu » qu'un faux prix)
MAP_REMOVE = {"corn_husk"}

# Ingrédients volontairement sans prix (introuvables en France, cf. disponibilité)
UNPRICED_OK = {"corn_husk", "drumstick_horseradish_tree_raw_pod", "roselle_raw", "tomatillo_raw"}


# Saveur et carbone passent aussi par resolve_catalog_key : une nouvelle clé du
# catalogue reprend le profil du produit d'origine (sinon le jus de citron perd
# son acidité dans 139 recettes, le piment son piquant dans 97).
# nouvelle clé → (source saveur, source carbone)
DERIVED_PROFILES: dict[str, tuple[str, str]] = {
    "lemon_juice_fresh": ("lemon", "lemon"),
    "lime_juice_fresh_fruit": ("lime", "lime"),
    "orange_juice_fresh": ("orange", "orange"),
    "chili_pepper": ("pepper", "bell_pepper"),
    "canola_oil": ("oil", "oil"),
    "nut_oil": ("walnut", "oil"),
    "truffle_oil": ("oil", "oil"),
    "almond_butter": ("almond", "almond"),
    "cashew_butter": ("almond", "almond"),
    "wild_mushroom": ("mushroom", "mushroom"),
    "levure_maltee": ("yeast", "yeast"),
    "puff_pastry": ("butter", "butter"),
    "buckwheat": ("flour", "flour"),
    "plant_milk": ("soybean", "soybean"),
    "sun_dried_tomato": ("tomato", "tomato"),
    "rose_water": ("water", "water"),
    "orange_blossom_water": ("orange", "water"),
}


def apply_profiles(flavor: dict, carbon: dict) -> list[str]:
    log = []
    for key, (f_src, c_src) in DERIVED_PROFILES.items():
        if key not in flavor:
            flavor[key] = list(flavor[f_src])
            log.append(f"saveur {key} ← {f_src}")
        if key not in carbon:
            carbon[key] = carbon[c_src]
            log.append(f"carbone {key} ← {c_src}")
    return log


def apply_catalog(catalog: dict) -> list[str]:
    log = []
    for key, entry in NEW_ENTRIES.items():
        if key not in catalog:
            catalog[key] = {"name_fr": entry["name_fr"], "pantry": False,
                            "packages": [dict(p) for p in entry["packages"]],
                            "last_updated": TODAY,
                            **({"unit_weight_g": entry["unit_weight_g"]} if "unit_weight_g" in entry else {})}
            log.append(f"+ {key}")
    for key, repl in PACKAGE_REPLACE.items():
        new = repl[None]
        pkgs = catalog[key]["packages"]
        if pkgs != [new]:
            log.append(f"~ {key}: {[(p['qty'], p['unit'], p['price']) for p in pkgs]} → {(new['qty'], new['unit'], new['price'])}")
            catalog[key]["packages"] = [dict(new)]
            catalog[key]["last_updated"] = TODAY
    for key, fixes in PRICE_FIXES.items():
        if key in PACKAGE_REPLACE:
            continue
        by_label = {p.get("label"): p for p in catalog[key]["packages"]}
        for label, price in fixes.items():
            p = by_label[label]
            if p["price"] != price:
                log.append(f"~ {key} {label}: {p['price']} → {price}")
                p["price"] = price
                catalog[key]["last_updated"] = TODAY
    for key, w in UNIT_WEIGHTS.items():
        if catalog[key].get("unit_weight_g") != w:
            log.append(f"~ {key} unit_weight_g → {w}")
            catalog[key]["unit_weight_g"] = w
    for key, extra in EXTRA_PACKAGES.items():
        labels = {p.get("label") for p in catalog[key]["packages"]}
        for p in extra:
            if p["label"] not in labels:
                catalog[key]["packages"].append(dict(p))
                log.append(f"+ {key} paquet {p['label']}")
    return log


def apply_map(price_map: dict, catalog: dict) -> list[str]:
    log = []
    for rid, key in MAP_FIXES.items():
        if key not in catalog:
            raise SystemExit(f"clé de catalogue inconnue pour {rid} : {key}")
        if price_map.get(rid) != key:
            log.append(f"{rid}: {price_map.get(rid)} → {key}")
            price_map[rid] = key
    for rid in MAP_REMOVE:
        if rid in price_map:
            log.append(f"{rid}: {price_map.pop(rid)} → (retiré)")
    return log


def _write(path: Path, data: dict) -> None:
    # garde la fin de fichier d'origine (flavor_graph et carbon_footprint n'ont pas de saut final)
    end = "\n" if path.read_bytes().endswith(b"\n") else ""
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + end)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    price_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    log_c = apply_catalog(catalog)
    log_m = apply_map(price_map, catalog)
    flavor = json.loads(FLAVOR_PATH.read_text(encoding="utf-8"))
    carbon = json.loads(CARBON_PATH.read_text(encoding="utf-8"))
    log_p = apply_profiles(flavor, carbon)
    for line in log_c + log_m + log_p:
        print(line)
    print(f"{len(log_c)} changement(s) au catalogue, {len(log_m)} lien(s) modifié(s)")
    if args.dry_run:
        print("[dry-run] rien n'est écrit")
        return
    if log_c:
        _write(CATALOG_PATH, catalog)
    if log_m:
        _write(MAP_PATH, price_map)
    if log_p:
        _write(FLAVOR_PATH, flavor)
        _write(CARBON_PATH, carbon)


if __name__ == "__main__":
    main()
