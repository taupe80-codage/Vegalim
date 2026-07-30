#!/usr/bin/env python3
"""
resolve_missing_ingredient_prices.py — Traite les 98 ingredients de recettes
restes "sans correspondance" dans scripts/ingredient_price_map_review.md.

Trois cas :
  1. DIRECT_LINKS   : l'ingredient correspond en fait a une entree deja
                      existante du catalogue, ratee par le containment
                      automatique (souvent un ecart de langue FR/EN, ex.
                      "oregano" (EN) vs cle catalogue "origan" (FR)).
                      -> ajoute directement au mapping, pas de nouvelle
                         entree catalogue.
  2. NO_MARKET_PRICE : l'id est en fait une reference vers une AUTRE recette
                      de base (ids "base_xxx_hexid"), pas un produit du
                      marche -- son cout depend de sa propre composition,
                      pas d'un prix catalogue. Laisse sans prix
                      intentionnellement (hors scope : calcul recursif du
                      cout d'une base recette).
  3. NEW_ENTRIES     : vrai trou du catalogue -> nouvelle entree creee avec
                      une estimation de prix de depart (raisonnable, prix
                      FR courants), destinee a etre affinee par
                      scripts/update_prices.py ensuite.

Usage :
    python scripts/resolve_missing_ingredient_prices.py

Modifie backend/data/config/prices_catalog.json (nouvelles entrees) et
backend/data/config/ingredient_price_map.json (liens directs + nouvelles
entrees), puis il faut relancer build_ingredient_price_map.py pour que le
mapping automatique integre proprement les nouvelles cles (ou laisser ce
script le faire directement, plus simple ici).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
MAP_PATH = ROOT / "backend/data/config/ingredient_price_map.json"

# ── 1. Liens directs vers des cles catalogue existantes ────────────────────
DIRECT_LINKS = {
    "nutmeg_spice": "noix_de_muscade",
    "oat_flakes_whole_seed": "oats",
    "cornstarch": "starch",
    "maple_syrup": "sirop_d_erable",
    "leeks_raw": "leek",
    "bay_leaf_spice": "feuille_laurier",
    "dill_weed_fresh_herb_leaf": "aneth",
    "oregano": "origan",
    "beetroot_raw_root": "beet",
    "flaxseed_linseed_ground": "flax_seeds",
    "amchoor_powder": "amchur",
    "grape_dried": "raisins_sec",
    "persil": "parsley",
    "coriandre": "coriander",
    "marjoram": "marjolaine",
    "toast": "bread",
}

# ── 2. References a une sous-recette (pas de prix marche pertinent) ───────
NO_MARKET_PRICE = {
    "base_dashi_broth_a3a517",
    "base_applesauce_b0627b",
    "base_mole_d0034f",
    "base_za_atar_2badf3",
    "base_mala_broth_1ab129",
    "base_spaetzle_a22916",
    "base_strawberry_coulis_49d4ea",
}

# ── 3. Nouvelles entrees catalogue ──────────────────────────────────────────
# recipe_id -> (catalog_key, name_fr, pantry, [(qty, unit, price_estime, label)])
NEW_ENTRIES = {
    "vanilla_extract":       ("vanilla_extract", "Extrait de Vanille", True, [(50, "ml", 5.90, "flacon 50ml")]),
    "vanilla_pod":            ("vanilla_pod", "Gousse de Vanille", True, [(2, "piece", 4.50, "2 gousses")]),
    "shallot_raw":            ("shallot", "Échalote", False, [(250, "g", 1.90, "filet 250g")]),
    "strawberry":             ("strawberry", "Fraise", False, [(500, "g", 3.90, "barquette 500g")]),
    "strawberry_jam":         ("strawberry_jam", "Confiture de Fraises", True, [(370, "g", 2.90, "pot 370g")]),
    "baking_powder":          ("baking_powder", "Levure Chimique", True, [(170, "g", 0.90, "sachet 170g")]),
    "baking_soda_powder":     ("baking_soda", "Bicarbonate de Soude", True, [(500, "g", 1.90, "boîte 500g")]),
    "dark_chocolate_40_cocoa_baking_tablet": ("dark_chocolate", "Chocolat Noir", True, [(200, "g", 2.50, "tablette 200g")]),
    "mango":                  ("mango", "Mangue", False, [(1, "piece", 2.20, "pièce")]),
    "blueberry":              ("blueberry", "Myrtille", False, [(125, "g", 2.90, "barquette 125g")]),
    "chia_raw_seed_dried":    ("chia_seeds", "Graines de Chia", True, [(200, "g", 3.90, "sachet 200g")]),
    "agave_syrup":            ("agave_syrup", "Sirop d'Agave", True, [(250, "ml", 4.50, "flacon 250ml")]),
    "comte_cow":              ("comte", "Comté", False, [(200, "g", 3.90, "portion 200g")]),
    "rum":                    ("rum", "Rhum", True, [(700, "ml", 14.90, "bouteille 70cl")]),
    "turnip_raw":             ("turnip", "Navet", False, [(500, "g", 1.60, "botte 500g")]),
    "arugula":                ("arugula", "Roquette", False, [(100, "g", 1.90, "sachet 100g")]),
    "canola":                 ("canola_oil", "Huile de Colza", True, [(1000, "ml", 2.90, "1L")]),
    "celeriac_raw":           ("celeriac", "Céleri-rave", False, [(1, "piece", 2.20, "pièce")]),
    "cocoa_powder_unsweetened": ("cocoa_powder", "Cacao en Poudre Non Sucré", True, [(250, "g", 3.50, "boîte 250g")]),
    "endive_raw":             ("endive", "Endive", False, [(500, "g", 2.20, "500g")]),
    "fennel_raw":             ("fennel", "Fenouil", False, [(1, "piece", 1.80, "pièce")]),
    "hazelnut_raw_unsalted":  ("hazelnut", "Noisette", True, [(200, "g", 3.90, "sachet 200g")]),
    "agar_dried":             ("agar_agar", "Agar-Agar", True, [(20, "g", 3.50, "sachet 20g")]),
    "aquafaba":               ("aquafaba", "Aquafaba (jus de pois chiches)", False, [(240, "ml", 0.90, "boîte pois chiches 240ml jus")]),
    "cloves_spice":           ("cloves", "Clou de Girofle", True, [(30, "g", 2.20, "pot 30g")]),
    "cognac":                 ("cognac", "Cognac", True, [(700, "ml", 24.90, "bouteille 70cl")]),
    "cranberry_dried_sweetened": ("cranberries_dried", "Canneberges Séchées", True, [(150, "g", 3.20, "sachet 150g")]),
    "dandelion_greens_raw_leaf": ("dandelion_greens", "Pissenlit", False, [(200, "g", 2.50, "botte 200g")]),
    "hemp_seed_hulled":       ("hemp_seeds", "Graines de Chanvre", True, [(150, "g", 4.50, "sachet 150g")]),
    "japanese_kombu_dried":   ("kombu", "Algue Kombu Séchée", True, [(30, "g", 4.90, "sachet 30g")]),
    "ladyfinger":             ("ladyfinger_biscuits", "Biscuits à la Cuillère", True, [(200, "g", 2.20, "paquet 200g")]),
    "loroco":                 ("loroco", "Loroco (fleur, spécialité centraméricaine)", True, [(50, "g", 3.00, "sachet 50g (estimation)")]),
    "mascarpone":             ("mascarpone", "Mascarpone", False, [(250, "g", 2.50, "pot 250g")]),
    "passion_fruit_raw":      ("passion_fruit", "Fruit de la Passion", False, [(1, "piece", 1.20, "pièce")]),
    "pear_raw_with_skin":     ("pear", "Poire", False, [(1000, "g", 2.90, "filet 1kg")]),
    "prune_umeboshi":         ("umeboshi", "Prune Umeboshi", True, [(100, "g", 5.90, "pot 100g")]),
    "raspberry_raw":          ("raspberry", "Framboise", False, [(125, "g", 3.50, "barquette 125g")]),
    "roquefort":              ("roquefort", "Roquefort", False, [(100, "g", 3.20, "portion 100g")]),
    "wasabi_japanese_horseradish_raw_root": ("wasabi", "Wasabi", True, [(43, "g", 2.90, "tube 43g")]),
    "acai_puree":             ("acai", "Purée d'Açaï", True, [(100, "g", 4.50, "sachet surgelé 100g")]),
    "apricot_pitted_dried":   ("dried_apricot", "Abricot Sec", True, [(250, "g", 3.20, "sachet 250g")]),
    "bagel":                  ("bagel", "Bagel", False, [(1, "piece", 1.20, "pièce")]),
    "calvados":               ("calvados", "Calvados", True, [(700, "ml", 19.90, "bouteille 70cl")]),
    "cantaloupe_melon_charentais_raw": ("melon", "Melon", False, [(1, "piece", 2.90, "pièce")]),
    "caraway_spice_seed":     ("caraway", "Carvi", True, [(30, "g", 2.20, "pot 30g")]),
    "chervil_fresh_herb":     ("chervil", "Cerfeuil", False, [(1, "piece", 1.50, "botte")]),
    "chicory":                ("chicory", "Chicorée", False, [(1, "piece", 1.50, "pièce")]),
    "chutney":                ("chutney", "Chutney", True, [(210, "g", 3.20, "pot 210g")]),
    "coffee":                 ("coffee", "Café", True, [(250, "g", 4.50, "paquet moulu 250g")]),
    "coffee_powder_instant":  ("coffee", "Café Instantané", True, [(100, "g", 4.50, "pot 100g")]),
    "cottage_uncreamed_curd_0_4_m_f_dried_4pct_cow": ("cottage_cheese", "Fromage Cottage", False, [(200, "g", 2.50, "pot 200g")]),
    "croutons_dried_plain_pre_packaged": ("croutons", "Croûtons", True, [(100, "g", 1.90, "sachet 100g")]),
    "fig_dried":              ("dried_fig", "Figue Séchée", True, [(200, "g", 3.50, "sachet 200g")]),
    "five_spice":             ("five_spice", "Cinq Épices Chinois", True, [(35, "g", 2.50, "pot 35g")]),
    "grapefruit_raw":         ("grapefruit", "Pamplemousse", False, [(1, "piece", 1.30, "pièce")]),
    "gundruk":                ("gundruk", "Gundruk (légume fermenté, spécialité népalaise)", True, [(50, "g", 3.50, "sachet 50g (estimation)")]),
    "jerusalem_artichoke_raw": ("jerusalem_artichoke", "Topinambour", False, [(500, "g", 2.90, "500g")]),
    "juniper_berry":          ("juniper_berries", "Baies de Genièvre", True, [(20, "g", 2.50, "pot 20g")]),
    "kirsch":                 ("kirsch", "Kirsch", True, [(700, "ml", 16.90, "bouteille 70cl")]),
    "kiwi":                   ("kiwi", "Kiwi", False, [(1, "piece", 0.60, "pièce")]),
    "lingonberry":            ("lingonberry", "Airelle Rouge", True, [(200, "g", 4.90, "pot confiture 200g")]),
    "marsala":                ("marsala", "Vin de Marsala", True, [(750, "ml", 8.90, "bouteille 75cl")]),
    "mixed_berries":          ("mixed_berries", "Fruits Rouges Mélangés", False, [(300, "g", 4.50, "sachet surgelé 300g")]),
    "molasses":               ("molasses", "Mélasse", True, [(350, "g", 3.20, "pot 350g")]),
    "parsnip_raw":            ("parsnip", "Panais", False, [(500, "g", 2.20, "500g")]),
    "pickles_raw":            ("pickles", "Cornichons", True, [(370, "g", 2.20, "pot 370g")]),
    "plum_raw_pitted":        ("plum", "Prune", False, [(500, "g", 2.90, "barquette 500g")]),
    "rhubarb_raw_stem":       ("rhubarb", "Rhubarbe", False, [(500, "g", 2.90, "botte 500g")]),
    "spirulina_dried":        ("spirulina", "Spiruline", True, [(100, "g", 8.90, "sachet 100g")]),
    "taro_leaf":              ("taro_leaf", "Feuille de Taro", True, [(200, "g", 3.50, "sachet 200g (estimation)")]),
    "tarragon_fresh_herb":    ("tarragon", "Estragon", False, [(1, "piece", 1.80, "botte")]),
    "tea":                    ("tea", "Thé", True, [(100, "g", 3.50, "boîte 100g")]),
    "tomme_de_savoie_cow":    ("tomme_de_savoie", "Tomme de Savoie", False, [(200, "g", 3.50, "portion 200g")]),
    "vegetarian_bacon":       ("vegetarian_bacon", "Bacon Végétal", True, [(100, "g", 3.20, "paquet 100g")]),
    "watercress":             ("watercress", "Cresson", False, [(125, "g", 1.90, "botte 125g")]),
}


def main():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    price_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))

    n_direct = 0
    for rid, catalog_key in DIRECT_LINKS.items():
        assert catalog_key in catalog, f"cle catalogue introuvable : {catalog_key}"
        price_map[rid] = catalog_key
        n_direct += 1

    n_new = 0
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
        n_new += 1

    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MAP_PATH.write_text(json.dumps(price_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{n_direct} liens directs ajoutes au mapping")
    print(f"{n_new} ingredients relies a {len(new_keys)} nouvelles entrees catalogue (prix estimes, a affiner)")
    print(f"{len(NO_MARKET_PRICE)} laisses sans prix (references a des sous-recettes base_*)")
    print()
    print("Nouvelles cles catalogue crees :")
    print(" ".join(new_keys))


if __name__ == "__main__":
    main()
