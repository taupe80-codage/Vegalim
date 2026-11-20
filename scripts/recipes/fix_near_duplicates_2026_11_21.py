#!/usr/bin/env python3
"""fix_near_duplicates_2026_11_21.py — arbitrage de l'audit de cohérence (compo_quasi_identique) :
13 paires de recettes du même type de plat partageaient au moins 80 % de leurs ingrédients.

Décision (2026-11-21) : les différencier en respectant la culture de chacune. La plupart sont
deux plats réellement différents qui partagent une base ; chacun est rapproché de sa recette
d'origine, sans rien inventer :

  pistou / sauce tomate        le pistou provençal reste sans fromage ; le sugo italien prend
                               l'oignon de son soffritto
  curry rouge / curry jaune    la pâte rouge thaïe n'a pas de curcuma mais du combava et du
                               poivre blanc ; la jaune prend curry en poudre et gingembre
  feuilletée / brisée / bannock  jus de citron dans la détrempe de la feuilletée, pincée de sucre
                               dans la brisée
  couscous express / traditionnel  le traditionnel devient le couscous marocain aux sept légumes
                               (navet, courge, chou ; gingembre, curcuma, safran ; bouquet
                               d'herbes ; semoule cuite deux fois à la vapeur)
  dal tadka / rajma masala     piments séchés dans le tadka ; laurier, cannelle et girofle du rajma
  briam / briam à la feta      le briam devient le briam ladero du Carême (poivron vert, persil,
                               huile d'olive généreuse, sans fromage)
  pancakes salés / crackers    levure chimique dans les pancakes, romarin dans les crackers
  onigiri nature / umeboshi    shio musubi au sésame (sa description parlait à tort de vinaigre de
                               riz) ; l'umeboshi sans sésame, comme au Japon
  bohémienne / pisto           la bohémienne d'Avignon : aubergines et tomates seulement, en
                               compotée ; le pisto manchego prend aussi le poivron vert
  zaalouk / salade d'aubergines  la salade devient la salade marocaine d'aubergines frites à la
                               chermoula
  purée / rösti                muscade dans la purée
  caviar d'aubergine / houmous de haricots  le caviar provençal sans tahini (celui du baba
                               ganoush) ni paprika, servi sur pain grillé

Idempotent. Relancer ensuite fix_recipe_diet_allergens.py, rebuild_graphs.py (deux passes),
build_index.py, extract_recipe_list.py.

Usage :
    python scripts/recipes/fix_near_duplicates_2026_11_21.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.engine.config import RECIPES_PATH  # noqa: E402


def line(ing, qty, unit, role):
    return {"ingredient": ing, "quantity": qty, "unit": unit, "meta": {"role": role}}


# ── ajouts / retraits d'ingrédients ──────────────────────────────────────────────────────────
ADD: dict[str, list[dict]] = {
    "base_sauce_tomate_926bfa": [line("onion_raw", 80, "g", "aromatic")],
    "base_curry_paste_49c97f": [line("kaffir_lime_leaf", 4, "g", "aromatic"),
                                line("white_pepper_spice", 2, "g", "spice")],
    "yellow_curry_paste_077f54": [line("ginger_raw_root_fresh", 10, "g", "aromatic"),
                                  line("curry_powder", 5, "g", "spice")],
    "base_puff_pastry_fca43b": [line("lemon_juice", 5, "ml", "acidity")],
    "base_shortcrust_e6e9f0": [line("white_sugar", 5, "g", "seasoning")],
    "dal_lentil_corail_classic_k1d1p1": [line("red_hot_chili_pepper_spice_dried", 2, "g", "spice")],
    "dal_makhani_vegan_259219": [line("bay_leaf_spice", 1, "g", "spice"),
                                 line("cinnamon_powder", 1, "g", "spice"),
                                 line("cloves_spice", 0.5, "g", "spice")],
    "main_briam_f33bb8": [line("green_bell_pepper_raw", 200, "g", "vegetable"),
                          line("parsley_fresh_herb", 15, "g", "herb")],
    "crepe_pancakes_sales_ultra_stru_1e8bd8": [line("baking_powder", 6, "g", "leavening")],
    "snack_crackers_35f6a8": [line("rosemary_fresh_herb", 5, "g", "herb")],
    "main_pisto_espagnol_7a98be": [line("green_bell_pepper_raw", 200, "g", "vegetable")],
    "side_potatoes_k3d2p1": [line("nutmeg_spice", 0.5, "g", "spice")],
}
REMOVE: dict[str, list[str]] = {
    "base_curry_paste_49c97f": ["turmeric_powder"],
    "rice_onigiri_umeboshi_7a5ef3": ["sesame_raw_seed"],
    "main_caviar_d_aubergine_0e824d": ["sesame_tahini_raw_butter_seed_plant", "paprika_powder"],
}
QTY: dict[str, dict[str, float]] = {
    "main_briam_f33bb8": {"olive_oil_plant": 90},
}

# ── textes : (ancien, nouveau) dans la description ou une étape ─────────────────────────────
TEXT: dict[str, list[tuple[str, str]]] = {
    "base_sauce_tomate_926bfa": [
        ("mijotée avec ail, basilic et huile d'olive,",
         "mijotée sur un fond d'oignon et d'ail à l'huile d'olive, finie au basilic,"),
        ("Ajouter l'ail émincé et faire revenir pendant 1 minute",
         "Ajouter 80 g d'oignon finement émincé et le faire fondre 5 minutes sans coloration, "
         "puis l'ail émincé, et faire revenir pendant 1 minute"),
    ],
    "base_curry_paste_49c97f": [
        ("citronnelle, galanga, ail et curcuma,", "citronnelle, galanga, ail et combava,"),
        ("le cumin, la curcuma, ainsi que le galanga",
         "le cumin, 2 g de poivre blanc, 4 g de feuilles de combava finement ciselées, ainsi que le galanga"),
    ],
    "yellow_curry_paste_077f54": [
        ("30g d'oignon jaune, et 25g de citronnelle fraîche",
         "30g d'oignon jaune, 10 g de gingembre frais et 25g de citronnelle fraîche"),
        ("Ajoutez 5g de cumin et 5g de coriandre en grains.",
         "Ajoutez 5g de cumin, 5g de coriandre en grains et 5 g de curry en poudre."),
        ("dominée par le curcuma et le cumin,", "dominée par le curcuma, le cumin et le curry en poudre,"),
    ],
    "base_puff_pastry_fca43b": [
        ("puis ajoutez progressivement 100ml d'eau froide",
         "puis ajoutez progressivement 100ml d'eau froide additionnée de 5 ml de jus de citron"),
    ],
    "base_shortcrust_e6e9f0": [
        ("Ajouter l'œuf battu, 30ml d'eau froide et 4g de sel.",
         "Ajouter l'œuf battu, 30ml d'eau froide, 4g de sel et 5 g de sucre."),
    ],
    "dal_lentil_corail_classic_k1d1p1": [
        ("y faire grésiller 5 g de graines de cumin, 5 g d'ail émincé",
         "y faire grésiller 5 g de graines de cumin, 2 g de piments rouges séchés entiers, 5 g d'ail émincé"),
        ("finies par un tadka de cumin et de piment grésillé,",
         "finies par un tadka de cumin, de piments séchés et de piment vert grésillés,"),
    ],
    "dal_makhani_vegan_259219": [
        ("Faire grésiller 3 g de cumin dans 35 ml d'huile",
         "Faire grésiller 3 g de cumin, 1 g de laurier (2 feuilles), 1 g de cannelle et 0,5 g de "
         "clous de girofle dans 35 ml d'huile"),
        ("gingembre, ail et garam masala,", "gingembre, ail, épices entières et garam masala,"),
    ],
    "main_briam_f33bb8": [
        ("Ragoût de légumes grecs, où les aubergines, courgettes et pommes de terre fondent en bouche, "
         "parfumés d'ail et d'origan — technique traditionnelle de la cuisine méditerranéenne.",
         "Le briam des jours de Carême, un « ladero » : aubergines, courgettes, pommes de terre, poivron "
         "vert et tomates confits au four dans beaucoup d'huile d'olive, avec ail, origan et persil, "
         "sans fromage."),
        ("les tomates en rondelles de 5 mm, et l'oignon en demi-rondelles fines.",
         "les tomates en rondelles de 5 mm, 200 g de poivron vert en lanières et l'oignon en "
         "demi-rondelles fines."),
        ("avec 45 ml d'huile d'olive, l'ail haché, les herbes (origan), sel et poivre.",
         "avec 90 ml d'huile d'olive, l'ail haché, l'origan, 15 g de persil haché, sel et poivre."),
        ("Arroser d'un filet d'huile d'olive supplémentaire. Enfourner à 180°C pendant 50 à 60 minutes",
         "Couvrir d'une feuille de papier cuisson les 30 premières minutes. Enfourner à 180°C pendant "
         "50 à 60 minutes"),
    ],
    "crepe_pancakes_sales_ultra_stru_1e8bd8": [
        ("mélanger 120 g de farine de blé, 4 g de sel de mer",
         "mélanger 120 g de farine de blé, 6 g de levure chimique, 4 g de sel de mer"),
    ],
    "snack_crackers_35f6a8": [
        ("mélanger 200 g de farine de blé avec 5 g de sel pour créer un mélange homogène.",
         "mélanger 200 g de farine de blé avec 5 g de sel et 5 g de romarin frais finement haché."),
        ("d'huile d'olive et de sel,", "d'huile d'olive, de romarin et de sel,"),
    ],
    "rice_onigiri_nature_cd56ab": [
        ("Riz japonais cuit à la perfection, assaisonné avec du vinaigre de riz, du sel et du sucre, "
         "puis façonné en triangles compacts recouverts de nori croustillant et de sésames grillés — un "
         "plat traditionnel japonais à la texture ferme et parfumée.",
         "Le shio musubi, l'onigiri le plus simple : riz japonais à peine salé, mêlé de sésame grillé, "
         "façonné en triangles compacts et entouré d'une bande de nori croustillante."),
        ("Servir sans attendre, pour apprécier",
         "Entourer chaque triangle d'une bande de nori (12 g en tout) et servir sans attendre, pour apprécier"),
    ],
    "rice_onigiri_umeboshi_7a5ef3": [
        ("Entourer d'une bande de nori croustillante et parsemer de 20g de graines de sésame grillées, "
         "puis servir aussitôt.",
         "Entourer d'une bande de nori croustillante, 12 g en tout, et servir aussitôt."),
    ],
    "main_pisto_espagnol_7a98be": [
        ("l'oignon (150g) et le poivron (320g)", "l'oignon (150g), le poivron rouge (320g) et le poivron vert (200g)"),
        ("en ajoutant le poivron et l'aubergine", "en ajoutant les poivrons et l'aubergine"),
        ("Pisto Espagnol végétarien, riche en saveurs et en textures,",
         "Le pisto de la Manche : poivrons rouge et vert, courgette, aubergine et tomate confits "
         "ensemble à l'huile d'olive, riche en saveurs et en textures,"),
    ],
    "side_potatoes_k3d2p1": [
        ("Assaisonner de 6 g de sel de table et 2 g de poivre noir.",
         "Assaisonner de 6 g de sel de table, 2 g de poivre noir et une pointe de muscade râpée (0,5 g)."),
    ],
    "main_caviar_d_aubergine_0e824d": [
        ("Préparation de caviar d'aubergine à texture lisse et équilibre aromatique précis, avec une "
         "chair fondante et une peau carbonisée, issue de la cuisine méditerranéenne.",
         "Le caviar d'aubergine provençal : chair d'aubergine rôtie écrasée à l'huile d'olive, à l'ail et "
         "au citron, relevée de persil — sans tahini, à la différence du baba ganoush levantin."),
        ("incorporer le tahini, l'ail écrasé et le jus de citron frais",
         "incorporer l'ail écrasé et le jus de citron frais"),
        ("Garnir de persil frais haché, de paprika et d'un filet d'huile d'olive, puis servir à "
         "température ambiante avec du pain pita croustillant, idéal pour être trempé dans le caviar "
         "d'aubergine.",
         "Garnir de persil frais haché et d'un filet d'huile d'olive, puis servir à température "
         "ambiante avec des tranches de pain de campagne grillées."),
    ],
}

# ── recettes refaites entièrement ────────────────────────────────────────────────────────────
FULL: dict[str, dict] = {
    "couscous_traditionnel_132078": {
        "description": "Le couscous marocain du vendredi, aux sept légumes : semoule cuite deux fois à "
                       "la vapeur au-dessus d'un bouillon au gingembre, au curcuma et au safran, où "
                       "cuisent carottes, navets, chou, courgettes, courge, tomates et pois chiches.",
        "composition": [
            line("couscous_to_cook_seed_dried", 300, "g", "base"),
            line("water", 150, "ml", "liquid"),
            line("olive_oil_plant", 30, "ml", "fat"),
            line("onion_raw", 200, "g", "aromatic"),
            line("tomato_raw_ripe", 250, "g", "vegetable"),
            line("carrot_raw", 250, "g", "vegetable"),
            line("turnip_raw", 250, "g", "vegetable"),
            line("cabbage_raw", 200, "g", "vegetable"),
            line("green_zucchini_squash_raw", 250, "g", "vegetable"),
            line("pumpkin_raw", 300, "g", "vegetable"),
            line("chickpea_boiled", 200, "g", "protein"),
            line("vegetable_stock_dried", 10, "g", "ingredient"),
            line("water", 1200, "ml", "ingredient"),
            line("ginger_powder", 3, "g", "spice"),
            line("turmeric_powder", 3, "g", "spice"),
            line("saffron_spice", 0.1, "g", "spice"),
            line("black_pepper_spice", 2, "g", "spice"),
            line("parsley_fresh_herb", 15, "g", "herb"),
            line("coriander_raw_fresh_herb", 15, "g", "herb"),
            line("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        "steps": [
            "Dans la marmite du couscoussier, faire revenir 200 g d'oignon émincé 5 minutes dans 20 ml "
            "d'huile d'olive avec 3 g de gingembre moulu, 3 g de curcuma, 2 g de poivre noir et une "
            "pincée de safran (0,1 g).",
            "Ajouter 250 g de tomates concassées, 200 g de pois chiches cuits et un bouquet de 15 g de "
            "persil et 15 g de coriandre ficelé, puis verser 1,2 litre d'eau avec 10 g de bouillon de "
            "légumes et 2 g de sel. Porter à ébullition.",
            "Mettre 300 g de semoule dans un grand plat, l'arroser de 150 ml d'eau avec 2 g de sel, "
            "l'égrainer entre les mains et la laisser gonfler 10 minutes.",
            "Ajouter au bouillon 250 g de carottes et 250 g de navets coupés en deux dans la longueur, "
            "et 200 g de chou en quartiers. Poser la semoule dans le haut du couscoussier et la cuire "
            "20 minutes à la vapeur, à compter du moment où la vapeur traverse le grain.",
            "Verser la semoule dans le plat et l'égrainer avec 10 ml d'huile d'olive. Ajouter au bouillon "
            "250 g de courgettes et 300 g de courge en gros morceaux, puis remettre la semoule à la "
            "vapeur 15 minutes.",
            "Dresser la semoule en dôme, disposer les légumes en couronne et arroser de bouillon, en "
            "servant le reste du bouillon à part.",
        ],
        "timing": {"prep_active_min": 30, "prep_passive_min": 10, "cook_min": 50, "total_min": 90},
        "technique": ["steaming", "simmering", "sauteing"],
    },
    "main_bohemienne_provencale_781b61": {
        "description": "La bohémienne d'Avignon et du Comtat : une compotée d'aubergines et de tomates "
                       "longuement mijotée à l'huile d'olive, à l'ail et au thym, écrasée à la cuillère "
                       "jusqu'à devenir presque une purée.",
        "composition": [
            line("eggplant_raw", 900, "g", "vegetable"),
            line("tomato_raw_ripe", 700, "g", "vegetable"),
            line("onion_raw", 100, "g", "aromatic"),
            line("garlic_raw", 15, "g", "aromatic"),
            line("olive_oil_plant", 60, "ml", "fat"),
            line("thyme_fresh_herb", 3, "g", "herb"),
            line("basil_fresh_herb", 10, "g", "herb"),
            line("table_salt_unenriched", 5, "g", "seasoning"),
            line("black_pepper_spice", 1, "g", "spice"),
        ],
        "steps": [
            "Peler 900 g d'aubergines et les couper en dés de 2 cm ; peler, épépiner et concasser 700 g "
            "de tomates.",
            "Faire revenir les aubergines 10 minutes dans 40 ml d'huile d'olive à feu moyen, en remuant, "
            "jusqu'à ce qu'elles soient dorées.",
            "Ajouter 100 g d'oignon émincé, 15 g d'ail écrasé, les tomates, 3 g de thym, 5 g de sel et "
            "1 g de poivre.",
            "Laisser compoter 1 heure à feu très doux et à découvert, en remuant et en écrasant peu à peu "
            "les légumes à la cuillère en bois, jusqu'à obtenir une compotée épaisse.",
            "Hors du feu, incorporer 20 ml d'huile d'olive et 10 g de basilic ciselé. Servir tiède ou "
            "froid, avec du pain de campagne grillé.",
        ],
        "timing": {"prep_active_min": 20, "prep_passive_min": 0, "cook_min": 70, "total_min": 90},
        "technique": ["sauteing", "simmering"],
    },
    "salad_daubergines_marocaine_03fd77": {
        "description": "Une salade du repas marocain : rondelles d'aubergine dorées à la poêle puis "
                       "nappées de chermoula, la marinade à l'ail, au cumin, au paprika, aux herbes et "
                       "au citron, servies à température ambiante.",
        "composition": [
            line("eggplant_raw", 600, "g", "vegetable"),
            line("sunflower_oil_plant", 60, "ml", "fat"),
            line("garlic_raw", 9, "g", "aromatic"),
            line("cumin_spice_seed", 3, "g", "spice"),
            line("paprika_powder", 3, "g", "spice"),
            line("coriander_raw_fresh_herb", 15, "g", "herb"),
            line("parsley_fresh_herb", 15, "g", "herb"),
            line("lemon_juice", 20, "ml", "acidity"),
            line("vinegar_liquid", 10, "ml", "acidity"),
            line("olive_oil_plant", 20, "ml", "fat"),
            line("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        "steps": [
            "Couper 600 g d'aubergines en rondelles de 1 cm, les saler avec 2 g de sel et les laisser "
            "dégorger 20 minutes, puis les sécher.",
            "Faire dorer les rondelles en plusieurs fois dans 60 ml d'huile de tournesol, 3 minutes de "
            "chaque côté, et les égoutter sur du papier absorbant.",
            "Chermoula : mélanger 9 g d'ail écrasé, 3 g de cumin, 3 g de paprika, 15 g de coriandre et "
            "15 g de persil ciselés, 20 ml de jus de citron, 10 ml de vinaigre, 20 ml d'huile d'olive et "
            "2 g de sel.",
            "Disposer les aubergines dans un plat en les nappant de chermoula couche par couche et laisser "
            "reposer au moins 30 minutes. Servir à température ambiante, avec du pain.",
        ],
        "timing": {"prep_active_min": 20, "prep_passive_min": 50, "cook_min": 15, "total_min": 85},
        "technique": ["deep_frying", "marinating"],
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = Path(RECIPES_PATH)
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    idx = {r["id"]: r for r in data["recipes"]}
    log: list[str] = []

    for rid, lines in ADD.items():
        have = {c["ingredient"] for c in idx[rid]["composition"]}
        for ln in lines:
            if ln["ingredient"] not in have:
                idx[rid]["composition"].append(ln)
                log.append(f"+ {rid} {ln['ingredient']}")
    for rid, ings in REMOVE.items():
        before = len(idx[rid]["composition"])
        idx[rid]["composition"] = [c for c in idx[rid]["composition"] if c["ingredient"] not in ings]
        if len(idx[rid]["composition"]) != before:
            log.append(f"- {rid} {ings}")
    for rid, q in QTY.items():
        for c in idx[rid]["composition"]:
            if c["ingredient"] in q and c.get("quantity") != q[c["ingredient"]]:
                log.append(f"= {rid} {c['ingredient']} {c.get('quantity')} → {q[c['ingredient']]}")
                c["quantity"] = q[c["ingredient"]]
    for rid, pairs in TEXT.items():
        r = idx[rid]
        for old, new in pairs:
            # déjà appliqué (le nouveau texte peut contenir l'ancien : « 100ml d'eau froide … »)
            if new in (r.get("description") or "") or any(new in s for s in r["instructions"]):
                continue
            if old in (r.get("description") or ""):
                r["description"] = r["description"].replace(old, new)
                log.append(f"desc {rid}")
                continue
            hits = [i for i, s in enumerate(r["instructions"]) if old in s]
            if hits:
                r["instructions"][hits[0]] = r["instructions"][hits[0]].replace(old, new)
                log.append(f"étape {rid}")
            elif not (new in (r.get("description") or "") or any(new in s for s in r["instructions"])):
                raise SystemExit(f"{rid} : texte introuvable « {old[:60]} »")
    for rid, spec in FULL.items():
        r = idx[rid]
        steps = [f"Étape {n} : {t}" for n, t in enumerate(spec["steps"], 1)]
        if r["composition"] != spec["composition"] or r["instructions"] != steps:
            r["composition"], r["instructions"] = spec["composition"], steps
            r["description"] = spec["description"]
            r["timing"] = spec["timing"]
            r.setdefault("tags", {})["technique"] = spec["technique"]
            log.append(f"refaite {rid}")

    # allergènes recalculés là où des ingrédients ont été retirés ou remplacés (sésame du tahini
    # et de l'onigiri) : fix_recipe_diet_allergens.py ne fait qu'en ajouter
    from backend.engine.rule_engine.diet import allergen_tags
    for rid in sorted(set(REMOVE) | set(FULL)):
        r = idx[rid]
        tags = allergen_tags(r)
        if sorted((r.get("tags") or {}).get("allergens") or []) != tags:
            log.append(f"allergènes {rid} : {(r.get('tags') or {}).get('allergens')} → {tags}")
            r.setdefault("tags", {})["allergens"] = tags

    print(*log, f"{len(log)} changement(s)", sep="\n")
    if args.dry_run or not log:
        return
    end = "\n" if raw.endswith("\n") else ""
    write_with_retry(path, json.dumps(data, ensure_ascii=False, indent=2) + end)


def write_with_retry(path: Path, text: str) -> None:
    """Windows : juste après une autre écriture, l'ouverture échoue parfois (OSError 22,
    fichier encore verrouillé par l'antivirus ou l'indexation) : on réessaie."""
    for attempt in range(5):
        try:
            with path.open("w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            return
        except OSError:
            if attempt == 4:
                raise
            time.sleep(1)


if __name__ == "__main__":
    main()
