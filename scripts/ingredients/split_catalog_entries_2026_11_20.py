#!/usr/bin/env python3
"""
split_catalog_entries_2026_11_20.py — des produits différents partageaient une même
entrée du catalogue de prix (ingredient_price_map) : tofu soyeux et fumé sous « Tofu
ferme », graines de fenouil sous « Anis vert », glace à la vanille sous « Crème
liquide », beurre végétal sous « Beurre », yaourt de soja sous « Yaourt nature »…
Ils en prenaient le prix, l'empreinte carbone et la saveur, et la liste de courses les
fusionnait sur une seule ligne (« Tofu soyeux (dont tofu fumé) »).

Chaque produit qu'on achète à part reçoit sa propre entrée, ou est relié à l'entrée
qui existait déjà sans servir (pain pita, chou chinois, daikon, tofu soyeux, farine de
manioc). Restent ensemble les variantes d'un même achat (oignon jaune / blanc, riz
rond / long) et les substituts voulus des recettes (queso fresco → feta, crème aigre →
crème fraîche, chou cavalier → chou kale).

Prix : estimations manuelles (prix courant en grande surface, novembre 2026), signalées
comme telles (price_source « estimation… » → « prix estimé » dans l'application).
Carbone : valeur de l'ancienne entrée en attendant ; relancer ensuite
carbon_agribalyse_2026_11_19.py, qui recalcule chaque nouvelle clé sur AGRIBALYSE 3.2.
Saveur : profil de l'ancienne entrée, ajusté quand le produit diffère.

Idempotent.

Usage :
    python scripts/ingredients/split_catalog_entries_2026_11_20.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
MAP_PATH = ROOT / "backend/data/config/ingredient_price_map.json"
FLAVOR_PATH = ROOT / "backend/data/graphs/flavor_graph.json"
CARBON_PATH = ROOT / "backend/data/config/carbon_footprint.json"

DATE = "2026-11-20"
SOURCE = f"estimation manuelle {DATE} (prix courant en grande surface ; produit séparé de son ancienne entrée)"


def pkg(qty, unit, price, label):
    return {"qty": qty, "unit": unit, "price": price, "label": label}


# clé : (nom, garde-manger, conditionnements, ancienne clé (carbone, saveur), saveur propre, poids d'une pièce)
NEW: dict[str, tuple] = {
    "almond_powder":        ("Poudre d'amande", False, [pkg(125, "g", 2.19, "sachet 125g")], "almond", None, None),
    "fennel_seed":          ("Graines de fenouil", False, [pkg(35, "g", 2.3, "pot 35g")], "anise_seed", ["sweet", "fresh", "floral"], None),
    "apple_juice":          ("Jus de pomme", False, [pkg(1000, "ml", 1.89, "bouteille 1L")], "apple", ["sweet", "sour"], None),
    "white_pepper":         ("Poivre blanc moulu", True, [pkg(40, "g", 3.2, "pot 40g")], "black_pepper", None, None),
    "naan":                 ("Pains naan", False, [pkg(2, "piece", 1.99, "sachet 2 naans")], "bread", ["neutral", "rich"], 120),
    "hot_dog_bun":          ("Pains à hot-dog", False, [pkg(250, "g", 1.39, "sachet 6 pains")], "bread", ["neutral", "sweet"], None),
    "sandwich_bread":       ("Pain de mie aux céréales", False, [pkg(500, "g", 1.89, "paquet 500g")], "bread", ["neutral", "nutty"], None),
    "chinese_broccoli":     ("Brocoli chinois (gai lan)", False, [pkg(300, "g", 2.5, "botte 300g")], "broccoli", None, None),
    "buckwheat_flour":      ("Farine de sarrasin", False, [pkg(500, "g", 2.29, "sachet 500g")], "buckwheat", ["earthy", "nutty"], None),
    "freekeh":              ("Freekeh (blé vert concassé)", False, [pkg(400, "g", 3.9, "sachet 400g")], "bulgur", ["nutty", "earthy", "smoky"], None),
    "vegan_butter":         ("Beurre végétal", False, [pkg(250, "g", 2.79, "plaquette 250g")], "butter", ["rich"], None),
    "pigeon_pea":           ("Pois cajan (toor dal)", False, [pkg(500, "g", 2.99, "sachet 500g")], "chana_dal", None, None),
    "goat_cheese":          ("Fromage de chèvre", False, [pkg(150, "g", 1.99, "chèvre frais 150g"),
                                                          pkg(180, "g", 2.29, "bûche 180g")], "cheese", ["tangy", "rich", "salty"], None),
    "canned_green_chili":   ("Piments verts en conserve", False, [pkg(113, "g", 2.49, "boîte 113g")], "chili_pepper", ["spicy", "sour"], None),
    "coconut_fresh":        ("Noix de coco fraîche", False, [pkg(1, "piece", 1.99, "pièce")], "coconut_flesh", ["sweet", "fresh"], 350),
    "instant_coffee":       ("Café soluble", True, [pkg(100, "g", 3.49, "bocal 100g")], "coffee", None, None),
    "evaporated_milk":      ("Lait concentré non sucré", False, [pkg(410, "g", 1.69, "boîte 410g")], "condensed_milk", ["rich"], None),
    "dried_coriander_leaf": ("Coriandre séchée (feuilles)", False, [pkg(10, "g", 1.79, "pot 10g")], "coriander_ground", ["fresh", "floral"], None),
    "vanilla_ice_cream":    ("Glace à la vanille", False, [pkg(520, "g", 2.99, "bac 1L")], "cream", ["sweet", "rich"], 50),
    "sweet_potato_flour":   ("Farine de patate douce", False, [pkg(500, "g", 4.5, "sachet 500g")], "farine_de_manioc", ["sweet", "earthy"], None),
    "tempura_flour":        ("Farine à tempura", False, [pkg(500, "g", 2.99, "sachet 500g")], "flour", None, None),
    "whole_wheat_flour":    ("Farine complète (T150)", False, [pkg(1000, "g", 1.79, "sachet 1kg")], "flour", ["nutty", "earthy"], None),
    "lambs_lettuce":        ("Mâche", False, [pkg(150, "g", 1.69, "sachet 150g")], "lettuce", ["fresh", "nutty"], None),
    "watermelon":           ("Pastèque", False, [pkg(1, "piece", 3.99, "pièce ~3kg")], "melon", ["sweet", "fresh"], 3000),
    "buttermilk":           ("Lait ribot (babeurre)", False, [pkg(1000, "ml", 1.59, "bouteille 1L")], "milk", ["sour", "tangy"], None),
    "dried_mint":           ("Menthe séchée", True, [pkg(15, "g", 1.99, "pot 15g")], "mint", None, None),
    "oyster_mushroom":      ("Pleurotes", False, [pkg(200, "g", 2.79, "barquette 200g")], "mushroom", None, None),
    "pecorino":             ("Pecorino romano", False, [pkg(150, "g", 3.49, "portion 150g")], "parmesan", ["salty", "tangy", "rich"], None),
    "oat_milk":             ("Boisson à l'avoine", False, [pkg(1000, "ml", 1.69, "brique 1L")], "plant_milk", ["sweet", "neutral"], None),
    "almond_milk":          ("Boisson à l'amande", False, [pkg(1000, "ml", 2.09, "brique 1L")], "plant_milk", ["nutty", "sweet"], None),
    "soy_milk":             ("Boisson au soja", False, [pkg(1000, "ml", 1.49, "brique 1L")], "plant_milk", ["neutral", "nutty"], None),
    "pomegranate_juice":    ("Jus de grenade", False, [pkg(750, "ml", 3.99, "bouteille 75cl")], "pomegranate", None, None),
    "puff_pastry_butter":   ("Pâte feuilletée pur beurre", False, [pkg(230, "g", 1.99, "rouleau 230g")], "puff_pastry", None, None),
    "glutinous_rice":       ("Riz gluant", False, [pkg(1000, "g", 3.29, "sachet 1kg")], "rice", ["neutral", "sweet"], None),
    "rice_cakes":           ("Galettes de riz soufflé", False, [pkg(130, "g", 1.49, "paquet 130g")], "rice", ["neutral", "nutty"], None),
    "glutinous_rice_flour": ("Farine de riz gluant", False, [pkg(400, "g", 1.99, "sachet 400g")], "rice_flour", None, None),
    "crushed_tomato":       ("Tomates concassées", False, [pkg(400, "g", 0.99, "boîte 400g")], "sauce_tomate", ["sour", "sweet", "umami"], None),
    "tamari":               ("Tamari (sauce soja sans blé)", False, [pkg(250, "ml", 4.49, "bouteille 25cl")], "soy_sauce", None, None),
    "brown_sugar":          ("Sucre roux (cassonade)", True, [pkg(1000, "g", 2.29, "sachet 1kg")], "sugar", ["sweet", "rich"], None),
    "vanilla_sugar":        ("Sucre vanillé", True, [pkg(75, "g", 1.29, "10 sachets (75g)")], "sugar", ["sweet", "floral"], None),
    "dried_thyme":          ("Thym séché", True, [pkg(15, "g", 1.59, "pot 15g")], "thyme", None, None),
    "smoked_tofu":          ("Tofu fumé", False, [pkg(200, "g", 2.59, "bloc 200g")], "tofu", ["smoky", "umami"], None),
    "balsamic_vinegar":     ("Vinaigre balsamique", True, [pkg(250, "ml", 2.49, "bouteille 25cl")], "vinegar", ["sweet", "sour", "rich"], None),
    "cider_vinegar":        ("Vinaigre de cidre", True, [pkg(500, "ml", 1.39, "bouteille 50cl")], "vinegar", ["sour", "fresh"], None),
    "red_wine_vinegar":     ("Vinaigre de vin rouge", True, [pkg(500, "ml", 1.19, "bouteille 50cl")], "vinegar", None, None),
    "soy_yogurt":           ("Yaourt au soja nature", False, [pkg(400, "g", 2.19, "4 pots (400g)")], "yogurt", ["sour", "neutral"], None),
    "greek_yogurt":         ("Yaourt à la grecque", False, [pkg(500, "g", 2.29, "pot 500g")], "yogurt", None, None),
    "kefir":                ("Kéfir de lait", False, [pkg(1000, "ml", 2.49, "bouteille 1L")], "yogurt", ["sour", "tangy"], None),
    "ginger_powder":        ("Gingembre moulu", True, [pkg(38, "g", 2.83, "pot 38g")], "ginger", ["spicy", "earthy"], None),
}

# id de recette → clé (nouvelle, ou existante qui ne servait pas)
LINKS: dict[str, str] = {
    "almond_flour": "almond_powder",
    "fennel_spice_seed": "fennel_seed",
    "apple_juice_plain": "apple_juice",
    "white_pepper_spice": "white_pepper",
    "indian_bread_naan": "naan",
    "hot_dog_bun_pre_packaged": "hot_dog_bun",
    "multigrain_toast_bread_roasted_sliced_pre_packaged": "sandwich_bread",
    "white_pita_bread": "pain_pita",
    "chinese_broccoli_cooked": "chinese_broccoli",
    "buckwheat_flour": "buckwheat_flour",
    "freekeh_immature_wheat_raw_cracked_seed": "freekeh",
    "vegan_butter": "vegan_butter",
    "napa_cabbage_raw": "chinese_cabbage",
    "pigeon_peas_red_gram_raw": "pigeon_pea",
    "goat_cheese_fresh": "goat_cheese",
    "goat_cheese_log": "goat_cheese",
    "green_chili_pepper_spice_canned": "canned_green_chili",
    "coconut_flesh_fresh": "coconut_fresh",
    "coffee_powder_instant": "instant_coffee",
    "condensed_milk_concentrated_unsweetened_whole": "evaporated_milk",
    "coriander_spice_leaf_dried": "dried_coriander_leaf",
    "vanilla_ice_cream": "vanilla_ice_cream",
    "sweet_potato_flour": "sweet_potato_flour",
    "tempura_flour": "tempura_flour",
    "whole_wheat_flour_seed": "whole_wheat_flour",
    "manioc_flour": "farine_de_manioc",
    "lambs_lettuce_raw": "lambs_lettuce",
    "watermelon_raw": "watermelon",
    "buttermilk_1pct": "buttermilk",
    "dried_mint_herb": "dried_mint",
    "spearmint_dried_herb": "dried_mint",
    "oyster_mushroom_raw": "oyster_mushroom",
    "pecorino_sheep": "pecorino",
    "oat_milk_refrigerated_plain_plant": "oat_milk",
    "almond_milk_refrigerated_unsweetened_plant": "almond_milk",
    "soybean_milk_unsweetened_plant": "soy_milk",
    "pomegranate_juice_plain": "pomegranate_juice",
    "puff_pastry_all_butter_raw_paste_pre_packaged": "puff_pastry_butter",
    "oriental_daikon_radish_raw": "daikon",
    "white_glutinous_rice_seed_dried": "glutinous_rice",
    "puffed_rice_cakes": "rice_cakes",
    "white_glutinous_rice_flour": "glutinous_rice_flour",
    "tomato_crushed_canned": "crushed_tomato",
    "soy_sauce_tamari": "tamari",
    "brown_sugar": "brown_sugar",
    "vanilla_sugar": "vanilla_sugar",
    "thyme_dried_herb": "dried_thyme",
    "silken_tofu_pre_packaged": "tofu_soyeux",
    "tofu_smoked_pre_packaged": "smoked_tofu",
    "balsamic_vinegar_liquid": "balsamic_vinegar",
    "cider_vinegar_liquid": "cider_vinegar",
    "red_wine_vinegar_liquid": "red_wine_vinegar",
    "soybean_yogurt_plain_plant": "soy_yogurt",
    "yogurt_greek_plain_4pct": "greek_yogurt",
    "yogurt_greek_style_plain_8pct": "greek_yogurt",
    "kefir_fermented": "kefir",
    "ginger_powder": "ginger_powder",
}

# entrées existantes précisées : la pâte feuilletée restante est la végétale (le pur
# beurre a la sienne) ; le gingembre moulu a la sienne, la racine garde la sienne.
RENAME = {"puff_pastry": "Pâte feuilletée (matière grasse végétale)"}
DROP_PACKAGE = {"ginger": "moulu pot 38g"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    paths = (CATALOG_PATH, MAP_PATH, FLAVOR_PATH, CARBON_PATH)
    catalog, price_map, flavor, carbon = (json.loads(p.read_text(encoding="utf-8")) for p in paths)
    log: list[str] = []

    for key, (name, pantry, packages, old, own_flavor, piece_g) in NEW.items():
        entry = {"name_fr": name, "pantry": pantry, "packages": packages,
                 "last_updated": DATE, "price_source": SOURCE}
        if piece_g:
            entry["unit_weight_g"] = piece_g
        if catalog.get(key) != entry:
            log.append(f"catalogue {key}")
            catalog[key] = entry
        if key not in flavor:
            flavor[key] = own_flavor or flavor[old]
            log.append(f"saveur {key}")
        if key not in carbon:
            carbon[key] = carbon[old]
            log.append(f"carbone {key} (provisoire, de {old})")

    for rid, key in LINKS.items():
        if key not in catalog:
            raise SystemExit(f"{rid} → {key} : clé absente du catalogue")
        if price_map.get(rid) != key:
            log.append(f"lien {rid} : {price_map.get(rid)} → {key}")
            price_map[rid] = key

    for key, name in RENAME.items():
        if catalog[key]["name_fr"] != name:
            log.append(f"nom {key} : {catalog[key]['name_fr']} → {name}")
            catalog[key]["name_fr"] = name
    for key, label in DROP_PACKAGE.items():
        kept = [p for p in catalog[key]["packages"] if p.get("label") != label]
        if len(kept) != len(catalog[key]["packages"]):
            log.append(f"conditionnement {key} : « {label} » retiré")
            catalog[key]["packages"] = kept

    print(*log, f"{len(log)} changement(s)", sep="\n")
    if args.dry_run or not log:
        return
    for p, d in zip(paths, (catalog, price_map, flavor, carbon)):
        end = "\n" if p.read_bytes().endswith(b"\n") else ""
        with p.open("w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + end)


if __name__ == "__main__":
    main()
