#!/usr/bin/env python3
"""
resolve_auto_med_candidates.py — Traite manuellement les 46 candidats a
confiance moyenne (AUTO_MED, score 0.5-0.67) laisses de cote par
build_ingredient_price_map.py (voir scripts/ingredient_price_map_review.md).

Chaque candidat a ete relu individuellement : le score 0.5 vient presque
toujours d'un simple mot partage ("green", "red", "cherry", "coconut"...)
qui ne garantit pas que ce soit le meme ingredient (ex. "green_peas_raw"
matchait "green_lentil" juste sur "green" -- des petits pois n'ont rien a
voir avec des lentilles). Decision au cas par cas :

  - KEEP        : le match propose par l'algorithme est en fait correct
                  (juste un pluriel ou une variante d'etat : "kidney_bean_
                  boiled" / "kidney_beans")
  - CORRECTED   : match propose faux, mais une AUTRE cle catalogue
                  existante convient ("vegetable_stock_dried" n'est pas de
                  l'huile, c'est du "bouillon")
  - NO_MARKET_PRICE : reference a une sous-recette base_*, comme dans
                  resolve_missing_ingredient_prices.py
  - NEW_ENTRY   : vrai trou du catalogue, nouvelle entree avec prix de
                  depart estime (a affiner par update_prices.py)

Usage :
    python scripts/resolve_auto_med_candidates.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
MAP_PATH = ROOT / "backend/data/config/ingredient_price_map.json"

# Match automatique correct, on l'ajoute simplement au mapping
KEEP = {
    "black_bean_boiled": "black_bean_cooked",
    "kidney_bean_boiled": "kidney_beans",
    "snow_peas_raw": "snow_pea",
    "gruyere": "gruyere_cheese",
    "nori": "feuilles_nori",
    "split_peas_dried": "split_pea",
    "great_northern_bean_dried": "white_bean",
    "wakame_dried": "wakame_seaweed",
    "flageolet_bean_canned": "white_bean",
    "gigante_bean": "white_bean",
    "wakame_raw_fresh": "wakame_seaweed",
}

# Match automatique faux -> corrige vers une autre cle catalogue existante
CORRECTED = {
    "vegetable_stock_dried": "bouillon",                 # pas de l'huile
    "mustard": "moutarde",                                # generique, pas forcement dijon
    "french_bean_raw": "green_bean",                      # "French bean" = haricot vert (UK)
    "yellow_mustard_spice_seed": "graines_de_moutarde",
    "mung_bean_sprouts_raw_seed_sprouted": "bean_sprout",  # "germes de soja" couvre les pousses de mungo
    "green_peas_raw": "pea",                               # petits pois, pas des lentilles
    "bamboo_raw_sprout": "bamboo_shoot",
    "phyllo_filo_pastry_raw_paste": "phyllo_sheet",
    "black_bean_dried": "black_beans",                     # sec, pas "cuit"
    "sweet_and_sour_gherkin_flavored_pre_packaged": "pickles",
    "medium_red_bean_dried": "kidney_beans",               # haricot rouge, pas lentille rouge
    "mixed_seaweed_dulse_porphyre_nori_dried": "dried_seaweed",  # melange, pas nori seul
    "tomate": "tomato",                                    # mot FR, cle catalogue EN
}

# References a une sous-recette (meme logique que resolve_missing_ingredient_prices.py)
NO_MARKET_PRICE = {
    "base_teriyaki_03b2ff",
    "base_hoisin_033e33",
    "base_shortcrust_e6e9f0",
    "base_worcestershire_vegan_5f26ec",
}

# Vrais trous du catalogue -> nouvelles entrees (prix de depart estime,
# affine ensuite par update_prices.py)
# recipe_id -> (catalog_key, name_fr, pantry, [(qty, unit, price, label)])
NEW_ENTRIES = {
    "coconut_flesh_dried":  ("coconut_flesh", "Noix de Coco Séchée / Râpée", True, [(150, "g", 2.20, "sachet 150g")]),
    "coconut_flesh_fresh":  ("coconut_flesh", "Noix de Coco Fraîche/Séchée", True, [(150, "g", 2.20, "sachet 150g")]),
    "white_wine_liquid":    ("white_wine", "Vin Blanc", True, [(750, "ml", 5.90, "bouteille 75cl")]),
    "macadamia_nuts_raw_unsalted": ("macadamia_nuts", "Noix de Macadamia", True, [(150, "g", 6.90, "sachet 150g")]),
    "pistachio_nuts_raw":   ("pistachios", "Pistaches", True, [(150, "g", 4.90, "sachet 150g")]),
    "puff_pastry_vegetable_fat_raw_paste_plant": ("puff_pastry", "Pâte Feuilletée", False, [(230, "g", 1.80, "rouleau 230g")]),
    "cherry_raw_with_skin": ("cherry", "Cerise", False, [(500, "g", 4.90, "barquette 500g")]),
    "green_grape_raw":      ("grape", "Raisin", False, [(500, "g", 2.90, "barquette 500g")]),
    "matcha_green_tea_powder": ("matcha", "Thé Matcha en Poudre", True, [(30, "g", 6.90, "boîte 30g")]),
    "papaya_raw":            ("papaya", "Papaye", False, [(1, "piece", 2.90, "pièce")]),
    "red_wine_liquid":      ("red_wine", "Vin Rouge", True, [(750, "ml", 5.90, "bouteille 75cl")]),
    "sunflower_raw_seed":   ("sunflower_seeds", "Graines de Tournesol", True, [(200, "g", 1.90, "sachet 200g")]),
    "anise_spice_seed":     ("anise_seed", "Graines d'Anis Vert", True, [(25, "g", 2.20, "pot 25g")]),
    "black_eyed_peas_cowpeas_boiled": ("black_eyed_peas", "Haricots à Œil Noir (Niébé)", True, [(500, "g", 1.90, "sachet 500g")]),
    "cherry_jam":            ("cherry_jam", "Confiture de Cerises", True, [(370, "g", 3.20, "pot 370g")]),
    "european_chestnuts_sweet_raw_peeled": ("chestnuts", "Châtaignes", False, [(500, "g", 4.90, "sachet 500g")]),
    "red_bean_paste":        ("red_bean_paste", "Pâte de Haricot Rouge (dessert asiatique)", True, [(400, "g", 3.90, "boîte 400g")]),
    "green_salad_raw_plain": ("salade", "Salade Verte", False, [(1, "piece", 1.50, "pièce")]),
}


def main():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    price_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))

    for rid, key in KEEP.items():
        assert key in catalog, f"cle catalogue introuvable (KEEP) : {key}"
        price_map[rid] = key

    for rid, key in CORRECTED.items():
        assert key in catalog, f"cle catalogue introuvable (CORRECTED) : {key}"
        price_map[rid] = key

    new_keys = []
    for rid, (key, name_fr, pantry, pkgs) in NEW_ENTRIES.items():
        if key not in catalog:
            catalog[key] = {
                "name_fr": name_fr,
                "pantry": pantry,
                "packages": [
                    {"qty": qty, "unit": unit, "price": price, "label": label}
                    for qty, unit, price, label in pkgs
                ],
                "last_updated": "2026-07-30",
            }
            new_keys.append(key)
        price_map[rid] = key

    total = len(KEEP) + len(CORRECTED) + len(NO_MARKET_PRICE) + len(NEW_ENTRIES)
    print(f"{len(KEEP)} matches automatiques valides, conserves tels quels")
    print(f"{len(CORRECTED)} matches automatiques faux, corriges vers une autre cle existante")
    print(f"{len(NO_MARKET_PRICE)} laisses sans prix (references a des sous-recettes base_*)")
    print(f"{len(NEW_ENTRIES)} relies a {len(new_keys)} nouvelles entrees catalogue (prix estimes)")
    print(f"total traite : {total} (attendu 46)")

    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MAP_PATH.write_text(json.dumps(price_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print()
    print("Nouvelles cles catalogue crees :")
    print(" ".join(new_keys))


if __name__ == "__main__":
    main()
