#!/usr/bin/env python3
"""
carbon_agribalyse_2026_11_19.py — recale carbon_footprint.json sur AGRIBALYSE 3.2 (ADEME).

La table d'origine (premier commit, source non documentée) était en moyenne 1,4 fois
au-dessus d'Agribalyse, avec de gros écarts : œuf ×3,6, huile d'olive ×5, lait de coco
×7, épices 12 fois en dessous.

Source : AGRIBALYSE® v3.2, fichier de synthèse publié par l'ADEME sur data.gouv.fr
(https://www.data.gouv.fr/datasets/agribalyse-synthese, Licence Ouverte 2.0), colonne
« Changement climatique » (kg CO₂ eq / kg de produit, au stade consommateur). Le CSV
n'est pas versionné : les valeurs retenues et leurs codes sont écrits dans
backend/data/config/carbon_footprint_sources.json.

Méthode, pour chaque clé de la table utilisée par une recette :
  1. « nom » : clé rattachée à la main à un ou plusieurs produits Agribalyse (BY_NAME,
     moyenne des codes AGB) — pour les ingrédients sans code Ciqual commun, ou quand le
     code Ciqual désigne un autre état que celui de la recette ;
  2. « ciqual » : sinon, moyenne pondérée par l'usage des produits Agribalyse dont le
     code Ciqual est celui des ingrédients de recette rattachés à la clé
     (ingredients_dictionary.json, source CIQUAL) ;
  3. « non_recale » : sinon, la valeur d'origine est gardée (NOT_IN_AGRIBALYSE).
La table est en kg CO₂e pour 100 g : valeur Agribalyse ÷ 10.

Variantes saisonnières : quand Agribalyse donne pour un même code Ciqual une valeur « de
saison » et une « hors saison » (tomate, fraise dans la v3.2), la source de la clé les
porte (« saisonnier ») ; carbon_score(recipe, month) les applique aux ingrédients frais
selon le calendrier de saisonnalité.

Idempotent pour un même CSV.

Usage :
    python scripts/ingredients/carbon_agribalyse_2026_11_19.py --csv agribalyse.csv --dry-run
    python scripts/ingredients/carbon_agribalyse_2026_11_19.py --csv agribalyse.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
CARBON_PATH = ROOT / "backend/data/config/carbon_footprint.json"
SOURCES_PATH = ROOT / "backend/data/config/carbon_footprint_sources.json"

# clé → codes AGB (moyenne). Rattachements par le nom, relus à la main.
BY_NAME: dict[str, list[str]] = {
    "water": ["18066"],                       # Eau du robinet
    "sparkling_water": ["18430"],             # Eau embouteillée de source
    "tomato": ["20047_1"],                    # Tomate, crue (moyenne annuelle)
    "lemon_juice_fresh": ["2028"],            # Jus de citron, pur jus
    "lime_juice_fresh_fruit": ["2028"],
    "bouillon": ["11172"],                    # bouillon aromatique déshydraté (poids sec)
    "soy_sauce": ["11104"],                   # Sauce soja, préemballée
    "sauce_soja": ["11104"],
    "green_onion": ["11003"],                 # Ciboule ou ciboulette, fraîche
    "zucchini": ["20020"],
    "chayote": ["20020"],                     # analogue : courgette
    "coconut_oil": ["16060"],                 # Huile de coco (coprah)
    "dried_chili": ["11088"],                 # Piment de Cayenne
    "gochugaru": ["11088"],
    "berbere": ["11088"],
    "coriander_ground": ["11026"],            # Coriandre, graine
    "graines_de_moutarde": ["11026"],         # analogue : graine d'épice
    "parmesan": ["12120"],
    "vanilla_extract": ["11065"],
    "vanilla_pod": ["11065"],
    "palm_sugar": ["31017"],                  # Sucre roux
    "red_onion": ["20034"],
    "garam_masala": ["11005"],                # Curry, poudre
    "sambar_powder": ["11005"],
    "allspice": ["11015"], "sumac": ["11015"], "sichuan_pepper": ["11015"],
    "star_anise": ["11015"], "juniper_berries": ["11015"], "amchur": ["11015"],
    "five_spice": ["11015"],                  # épices : Poivre noir, poudre (proxy Agribalyse)
    "vegetable_oil": ["17440"],               # Huile de tournesol
    "tomato_paste": ["20068"],                # Tomate, concentré, appertisé
    "sauce_tomate": ["20169"],                # Tomate, pulpe, appertisée
    "plant_milk": ["18905", "18900", "18107"],  # boissons avoine, soja, amande
    "curry_leaf": ["11033"], "lemongrass": ["11033"], "kaffir_lime_leaf": ["11033"],  # herbes fraîches
    "black_bean_cooked": ["20503"],           # analogue : Haricot rouge, cuit
    "black_eyed_peas_canned": ["20503"],
    "black_eyed_peas": ["20525"],             # analogue : Haricot rouge, sec
    "red_bean_paste": ["20503"],
    "breadcrumbs": ["7004"],                  # Pain grillé
    "olive": ["13147"],                       # Olives (seule entrée Agribalyse)
    "capre": ["13147"],
    "creme_fraiche": ["19410"],               # Crème de lait 30 % MG, épaisse
    "mascarpone": ["19410"],
    "oats": ["9311"],
    "cashew": ["15019"], "cashew_butter": ["15019"],
    "polenta": ["9614"], "masa_harina": ["9614"], "precooked_corn_flour": ["9614"],
    "mirin": ["1006"],                        # Vin doux
    "ricotta": ["19646"],                     # analogue : fromage blanc 3 %
    "cottage_cheese": ["19646"],
    "peanut_butter": ["15202"],
    "gruyere_cheese": ["12114"], "tomme_de_savoie": ["12114"],
    "pistachios": ["15044"],
    "baking_soda": ["11507"],
    "pumpkin_seeds": ["15010"],               # analogue : Sésame, graine
    "okra": ["58103"],
    "fresh_fava_bean": ["20517"],             # Fève à écosser, fraîche
    "soybean": ["20901"], "soy_flour": ["20901"], "edamame": ["20901"],
    "galangal": ["11074"],                    # analogue : Gingembre, racine
    "urad_lentil": ["20504"],
    "flax_seeds": ["15034"], "hemp_seeds": ["15034"],
    "farine_de_seigle": ["9532"],
    "white_bean_dry": ["20501"],
    "rice_wrapper": ["9900"], "glass_noodles": ["9900"],
    "wasabi": ["11016"],                      # Raifort, cru
    "sauerkraut": ["25220"],
    "fresh_cheese": ["12340"],
    "cranberries_dried": ["13046"],           # analogue : Raisin sec
    "lingonberry": ["13113"],                 # analogue : Canneberge
    "bok_choy": ["20167"],
    "wheat_gluten": ["25598"],                # Seitan
    "udon": ["9086"],
    "tteok": ["9104"], "riz_rond": ["9104"],
    "tempura_flour": ["9435"],
    "preserved_lemon": ["13009"],
    "ladyfinger_biscuits": ["24430"],
    "grape": ["13112"],
    "cognac": ["1023"], "calvados": ["1023"], "kirsch": ["1023"],
    "chestnuts": ["15020"],
    "chana_dal": ["20516"],
    "attieke": ["54034"],
    "almond_butter": ["15000"],
    "agar_agar": ["11084"], "dried_seaweed": ["20987"],
    "vegetarian_bacon": ["20912"],            # Tofu fumé
    "sauce_okonomiyaki": ["11008"],           # analogue : Ketchup
    "pecan": ["15023"],
    "mixed_berries": ["13015", "13028"],
    "kiwi": ["13021"],
    "kabocha_squash": ["20134"],
    "falafel": ["25590"],
    "black_rice": ["9100"],
    "camembert": ["12001"],
    "green_papaya": ["13035"],
}

# ── 2026-11-20 : clés sans produit Agribalyse direct ─────────────────────────────────
# analogues Agribalyse (même logique que BY_NAME), relus à la main
BY_NAME.update({
    "jackfruit": ["13025_1"],          # Mangue importée par bateau (fruit tropical importé)
    "lotus_root": ["54031"],           # Manioc, racine crue
    "farine_de_teff": ["9532"],        # Farine de seigle T85 (farine de céréale)
    "farine_de_manioc": ["9570"],      # Farine de châtaigne (farine de féculent)
    "acai": ["13132"],                 # Myrtille surgelée (baie surgelée)
    "chutney": ["11008"],              # Ketchup (condiment sucré-acide)
    "ketchup": ["11008"],              # Ketchup (entrée propre depuis ketchup_2026_11_20.py)
    "truffle_oil": ["17270"],          # Huile d'olive vierge extra (huile aromatisée)
    "prune_umeboshi": ["13100"],       # Prune, crue
    "vine_leaf": ["20059"], "taro_leaf": ["20059"],   # Épinard, cru (feuille)
    "gundruk": ["25220"],              # Choucroute égouttée (légume fermenté)
    "pickles": ["25220"],
    "loroco": ["11033"],               # herbe / fleur fraîche
    "hominy_corn": ["9615"],           # Polenta cuite
    "rose_water": ["18430"], "orange_blossom_water": ["18430"],  # eau embouteillée
})

# ── 2026-11-20 : produits séparés de leur ancienne entrée (split_catalog_entries_2026_11_20.py)
# rattachés par le nom, faute de code Ciqual commun ; analogues relus à la main
BY_NAME.update({
    "almond_milk": ["18107"],          # Boisson à l'amande
    "almond_powder": ["15041"],        # Amande émondée
    "buttermilk": ["19801"],           # Lait fermenté à boire, nature, maigre
    "kefir": ["19805"],                # Lait fermenté à boire, nature, au lait entier
    "canned_green_chili": ["20151"],   # Piment, cru
    "chinese_broccoli": ["20057"],     # Brocoli, cru
    "chinese_cabbage": ["20167"],      # Chou chinois (pak-choi ou pé-tsai), cru
    "crushed_tomato": ["20169"],       # Tomate, pulpe, appertisée
    "daikon": ["20089"],               # Radis noir, cru
    "dried_coriander_leaf": ["11024"], # Persil, séché (herbe séchée)
    "dried_mint": ["11024"],
    "glutinous_rice": ["9100"],        # Riz blanc, cru
    "glutinous_rice_flour": ["9520"],  # Farine de riz
    "instant_coffee": ["18003"],       # Café, moulu (pas de café soluble en poudre)
    "naan": ["7260"],                  # Pain blanc maison
    "pain_pita": ["7180"],             # Pain pita
    "oat_milk": ["18905"],             # Boisson à base d'avoine, nature
    "soy_milk": ["18900"],             # Boisson au soja, nature
    "pecorino": ["12827"],             # Fromage de brebis à pâte pressée
    "pigeon_pea": ["20515"],           # Pois cassé, sec
    "pomegranate_juice": ["2"],        # Jus de fruits rouges
    "red_wine_vinegar": ["11018"],     # Vinaigre
    "rice_cakes": ["7352"],            # Galette de riz soufflé complet
    "soy_yogurt": ["19693"],           # Dessert au soja, nature, rayon frais
    "sweet_potato_flour": ["9570"],    # Farine de châtaigne (farine de féculent)
    "tamari": ["11104"],               # Sauce soja, préemballée
    "tofu_soyeux": ["20904"],          # Tofu, nature
    "vanilla_ice_cream": ["39515"],    # Glace ou crème glacée, en bac
    "vegan_butter": ["16615"],         # Matière grasse végétale ou margarine, 80 % MG, doux
    "whole_wheat_flour": ["9415"],     # Farine de blé tendre T150
    "anise_seed": ["11066"],           # Fenouil, graine (l'anis vert n'y est pas)
})

# ── 2026-11-20 : derniers ingrédients sans prix (add_missing_prices_2026_11_20.py)
BY_NAME.update({
    "corn_husk": ["9615"],             # Polenta cuite (sous-produit du maïs ; enveloppe non mangée)
    "moringa_drumstick": ["20061_1"],    # Haricot vert, cru (gousse verte)
    "tomatillo": ["20169"],            # Tomate, pulpe, appertisée (vendue en boîte)
})

# valeurs d'une autre source (kg CO₂e / kg), faute de produit dans Agribalyse 3.2
EXTERNAL: dict[str, tuple[float, str]] = {
    "yeast": (0.734, "COFALEC / PwC, Carbon Footprint of Yeast produced in the EU (2012) : levure pressée"),
    "levure_maltee": (3.204, "COFALEC / PwC (2012) : levure sèche (proxy de la levure maltée)"),
    "mushroom": (1.55, "Bon pour le climat, tableau comparatif repris par ecolozen.com (source secondaire)"),
    "shiitake_mushroom": (1.55, "idem champignon cultivé (source secondaire)"),
    "wood_ear_mushroom": (1.55, "idem champignon cultivé (source secondaire)"),
    "oyster_mushroom": (1.55, "idem champignon cultivé (source secondaire)"),
    # thé infusé Agribalyse 0,0436 kg/kg pour ~8 g de feuilles par kg d'infusion
    "tea": (5.45, "dérivé d'Agribalyse 18020 « Thé infusé » (0,0436 kg/kg ÷ 8 g de feuilles/kg)"),
    "matcha": (5.45, "idem thé (dérivé d'Agribalyse 18020)"),
    "dried_hibiscus": (5.45, "dérivé d'Agribalyse 18022 « Tisane infusée » (0,0436 kg/kg ÷ 8 g de plante/kg)"),
}

# sans équivalent sérieux : valeur d'origine gardée
NOT_IN_AGRIBALYSE = {
    "wild_mushroom",     # cueillette : Agribalyse n'a que la morille (6,17), non représentative
    "shiitake_dried", "corn_husk", "aquafaba",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="synthèse AGRIBALYSE 3.2 (data.gouv.fr)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from backend.core.data_io import (load_ingredients_dict, load_recipes,
                                      resolve_catalog_key)
    by_agb, by_ciqual = {}, {}
    with open(args.csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_agb[row["Code AGB"].strip()] = row
            by_ciqual.setdefault(row["Code CIQUAL"].strip(), []).append(row)
    # plusieurs produits pour un même code Ciqual (« Mangue importée par bateau » _1 /
    # « par avion » _2, « Tomate, crue » _1 / « de saison » _2 / « hors saison » _3) :
    # le produit de même code, sinon la variante _1 (moyenne ou transport courant)
    # variantes « de saison » (code saison 1) / « hors saison » (0) d'un même code Ciqual
    seasonal = {}
    for c, rows in by_ciqual.items():
        de = [r for r in rows if r["code saison"].strip() == "1"]
        hors = [r for r in rows if r["code saison"].strip() == "0"]
        if de and hors:
            seasonal[c] = {"de_saison": round(float(de[0]["Changement climatique"]) / 10, 4),
                           "hors_saison": round(float(hors[0]["Changement climatique"]) / 10, 4),
                           "codes_agb": [de[0]["Code AGB"], hors[0]["Code AGB"]]}
    by_ciqual = {c: next((r for r in rows if r["Code AGB"].strip() == c),
                         next((r for r in rows if r["Code AGB"].strip().endswith("_1")), rows[0]))
                 for c, rows in by_ciqual.items()}
    carbon = json.loads(CARBON_PATH.read_text(encoding="utf-8"))
    dico = load_ingredients_dict()
    use = Counter(str(c["ingredient"]) for r in load_recipes() for c in r.get("composition") or []
                  if not str(c["ingredient"]).startswith("base_"))
    ids_by_key: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for iid, n in use.items():
        k = resolve_catalog_key(iid, carbon)
        if k:
            ids_by_key[k].append((iid, n))

    def _ref(row):
        return {"code_agb": row["Code AGB"], "code_ciqual": row["Code CIQUAL"],
                "nom": row["Nom du Produit en Français"],
                "kg_co2e_par_kg": float(row["Changement climatique"])}

    sources, counts, changes = {}, Counter(), []
    for key in sorted(ids_by_key):
        old = carbon[key]
        if key in EXTERNAL:
            value, why = EXTERNAL[key]
            refs = [{"source": why, "kg_co2e_par_kg": value}]
            method = "externe"
        elif key in BY_NAME:
            refs = [_ref(by_agb[c]) for c in BY_NAME[key]]
            value = sum(r["kg_co2e_par_kg"] for r in refs) / len(refs)
            method = "nom"
        else:
            weighted = []
            for iid, n in ids_by_key[key]:
                d = dico.get(iid) or {}
                row = by_ciqual.get(str(d.get("source_id") or "")) if d.get("source") == "CIQUAL" else None
                if row:
                    weighted.append((_ref(row), n))
            if weighted:
                refs = list({r["code_agb"]: r for r, _ in weighted}.values())
                value = sum(r["kg_co2e_par_kg"] * n for r, n in weighted) / sum(n for _, n in weighted)
                method = "ciqual"
            else:
                if key not in NOT_IN_AGRIBALYSE:
                    raise SystemExit(f"{key} : aucun rattachement (BY_NAME ou NOT_IN_AGRIBALYSE)")
                sources[key] = {"methode": "non_recale", "kg_co2e_pour_100g": old}
                counts["non_recale"] += sum(n for _, n in ids_by_key[key])
                continue
        new = round(value / 10, 4)
        carbon[key] = new
        counts[method] += sum(n for _, n in ids_by_key[key])
        sources[key] = {"methode": method, "kg_co2e_pour_100g": new, "agribalyse": refs}
        variants = [seasonal[r["code_ciqual"]] for r in refs if r.get("code_ciqual") in seasonal]
        if variants:
            # utilisé par carbon_score(recipe, month) pour les ingrédients frais
            sources[key]["saisonnier"] = variants[0]
        if abs(new - old) > 1e-9:
            changes.append((key, old, new))

    print(f"lignes de recettes par méthode : {dict(counts)}")
    print(f"{len(changes)} valeurs changent")
    for key, old, new in sorted(changes, key=lambda x: -abs(x[2] - x[1]))[:25]:
        print(f"  {key:28} {old:7.4f} → {new:7.4f} kg/100 g")
    if args.dry_run:
        print("[dry-run] rien n'est écrit")
        return
    meta = {"_meta": {
        "source": "AGRIBALYSE 3.2 — ADEME, synthèse (data.gouv.fr/datasets/agribalyse-synthese)",
        "licence": "Licence Ouverte / Open Licence 2.0 (Etalab)",
        "indicateur": "Changement climatique, kg CO2 eq / kg de produit ; table en kg / 100 g",
        "genere_par": "scripts/ingredients/carbon_agribalyse_2026_11_19.py",
        "date": "2026-11-19",
    }}
    for path, data in ((CARBON_PATH, carbon), (SOURCES_PATH, {**meta, **sources})):
        end = "\n" if not path.exists() or path.read_bytes().endswith(b"\n") else ""
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + end)


if __name__ == "__main__":
    main()
