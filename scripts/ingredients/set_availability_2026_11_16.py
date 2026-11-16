#!/usr/bin/env python3
"""
set_availability_2026_11_16.py — renseigne `available_in_france` pour les
ingrédients des recettes qui ne l'avaient pas.

Avant : 57 ingrédients de recettes sur 482 étaient renseignés ; le score
d'accessibilité (quality._d_accessibility) retombait sur « présent au
catalogue de prix → 8 », ce qui donnait 8 à 788 recettes sur 894 (écart-type
0,39) et 5 à des produits courants absents du catalogue (cannelle, sucre,
farine T55…).

Règle (rayon d'un supermarché français moyen, pas d'un hypermarché parisien) :
  True      trouvable en grande surface (rayon frais, épicerie, bio ou
            « produits du monde » courant) ;
  "partial" épicerie spécialisée (asiatique, africaine, indienne, mexicaine),
            magasin bio, saison courte ou grande ville seulement ;
  False     quasi introuvable en France hors import / commande en ligne.

Seules les entrées à None sont écrites : une valeur déjà renseignée n'est
jamais modifiée. Idempotent.

Usage :
    python scripts/ingredients/set_availability_2026_11_16.py --dry-run
    python scripts/ingredients/set_availability_2026_11_16.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

AVAIL_PATH = ROOT / "backend/data/graphs/ingredient_availability_graph_v1.json"

PARTIAL = {
    # piments et légumes d'Amérique latine
    "ancho_pepper_spice_dried", "serrano_pepper_raw", "jalapeno_pepper_raw",
    "green_chili_pepper_spice_canned", "chayote_raw", "queso_fresco_block_cow",
    # légumes et produits d'Asie
    "bamboo_raw_sprout", "chinese_broccoli_cooked", "lotus_raw_root",
    "oriental_daikon_radish_raw", "japanese_kombu_dried",
    "mixed_seaweed_dulse_porphyre_nori_dried", "wakame_dried", "wakame_raw_fresh",
    "white_glutinous_rice_flour", "white_glutinous_rice_seed_dried",
    "jackfruit_raw", "kabocha_squash_raw", "mustard_raw_leaf",
    # légumineuses et farines d'épicerie africaine / orientale / bio
    "black_eyed_peas_cowpeas_boiled", "black_eyed_peas_cowpeas_dried",
    "pigeon_peas_red_gram_raw", "fava_bean_dried", "broadbeans_fava_beans_raw_dried",
    "mung_bean_dried", "soybean_raw_dried", "soybean_boiled_dried",
    "pinto_bean_boiled", "lima_bean_boiled_canned",
    "cassava_flour", "sweet_potato_flour", "soybean_flour_raw_whole",
    "vital_wheat_gluten_flour", "freekeh_immature_wheat_raw_cracked_seed",
    "buckwheat_groats_roasted_dried_dry",
    # légumes et fruits peu distribués
    "okra_raw", "plantain_banana_raw", "plantain_banana_raw_ripe", "tamarind_raw",
    "collard_raw", "dandelion_greens_raw_leaf", "sour_cherry_raw",
    # champignons sauvages frais (saison courte)
    "porcini_mushroom_raw", "chanterelle_mushroom_raw",
    # magasin bio
    "nutritional_yeast_flakes", "tempeh_tempe_raw_fermented", "spirulina_dried",
    "hemp_seed_hulled", "cashew_butter_plain_plant",
    # épices et crèmerie rares en rayon
    "fenugreek_spice_seed", "sour_cream_fermented_18pct", "cream_sour_18pct",
    "cream_sour_fermented",
}

UNAVAILABLE = {
    "cotija_block_cow", "queso_chihuahua_whole_cow", "tomatillo_raw",
    "hominy_boiled_flour_canned", "drumstick_horseradish_tree_raw_pod",
    "wasabi_japanese_horseradish_raw_root", "roselle_raw",
}


def recipe_ingredient_ids() -> set[str]:
    from backend.core.data_io import load_recipes
    from backend.engine.score_engine.quality import _get_ings
    return {i for r in load_recipes() for i in _get_ings(r) if not i.startswith("base_")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    graph = json.loads(AVAIL_PATH.read_text(encoding="utf-8"))
    ids = recipe_ingredient_ids()

    unknown = (PARTIAL | UNAVAILABLE) - ids
    if unknown:
        sys.exit(f"Ids absents des recettes (table à mettre à jour) : {sorted(unknown)}")

    counts = {True: 0, "partial": 0, False: 0}
    for iid in sorted(ids):
        entry = graph.setdefault(iid, {"available_in_france": None})
        if entry.get("available_in_france") is not None:
            continue
        value = False if iid in UNAVAILABLE else "partial" if iid in PARTIAL else True
        entry["available_in_france"] = value
        counts[value] += 1

    print(f"Renseignés : {counts[True]} courants, {counts['partial']} partiels, "
          f"{counts[False]} introuvables")
    if args.dry_run:
        print("[dry-run] rien n'est écrit")
        return
    with AVAIL_PATH.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(graph, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
