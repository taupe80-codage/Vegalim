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

# sans équivalent sérieux dans Agribalyse 3.2 : valeur d'origine gardée
NOT_IN_AGRIBALYSE = {
    "mushroom", "shiitake_mushroom", "wild_mushroom", "shiitake_dried", "wood_ear_mushroom",
    "levure_maltee", "yeast", "rose_water", "orange_blossom_water", "pickles", "tea",
    "matcha", "corn_husk", "loroco", "hominy_corn", "aquafaba", "vine_leaf", "truffle_oil",
    "taro_leaf", "prune_umeboshi", "lotus_root", "jackfruit", "gundruk", "farine_de_teff",
    "chutney", "acai", "farine_de_manioc",
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
        if key in BY_NAME:
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
