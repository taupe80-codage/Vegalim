#!/usr/bin/env python3
"""
carbon_flavor_profiles_2026_11_19.py — donne une empreinte carbone et un profil de saveur
à chaque clé du catalogue de prix qui n'en avait pas.

Constat : resolve_catalog_key() ramène un ingrédient de recette à sa clé de prix (« egg »,
« potato », « milk »…), puis cherche cette clé dans carbon_footprint.json et
flavor_graph.json. Ces deux tables nomment souvent le même aliment autrement (« oeuf »,
« pommes_de_terre », « lait »), si bien que 138 clés du catalogue — environ 1 430 lignes de
recettes, dont les œufs, le lait, la crème, les pommes de terre et la sauce soja — étaient
comptées à 0 kg CO₂e et sans saveur.

Méthode : chaque clé reprend l'empreinte d'une clé existante — le même aliment sous un
autre nom, ou à défaut l'aliment le plus proche (fruit, noix, épice, alcool…) — pour rester
à l'échelle de la table, sans chiffre nouveau. Le profil de saveur est celui de la source
quand c'est le même aliment, sinon il est donné explicitement (vocabulaire de la table).
FLAVOR_ONLY complète 9 clés qui avaient une empreinte mais pas de saveur.

Idempotent ; n'écrase aucune valeur existante.

Usage :
    python scripts/ingredients/carbon_flavor_profiles_2026_11_19.py --dry-run
    python scripts/ingredients/carbon_flavor_profiles_2026_11_19.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
FLAVOR_PATH = ROOT / "backend/data/graphs/flavor_graph.json"
CARBON_PATH = ROOT / "backend/data/config/carbon_footprint.json"

# Clés qui avaient une empreinte mais pas de saveur (sources des alias ci-dessous)
FLAVOR_ONLY: dict[str, list[str]] = {
    "poireau": ["sweet", "pungent"],
    "menthe": ["fresh"],
    "green_tea": ["bitter", "fresh"],
    "matcha_tea": ["bitter", "umami"],
    "falafel": ["earthy", "spicy"],
    "flocons_d_avoine": ["nutty"],
    "huile_de_palme": ["rich", "neutral"],
    "kombucha": ["sour", "sweet"],
    "pate_d_arachide": ["nutty", "rich"],
}

# clé du catalogue → (clé source de l'empreinte, saveur ; None = celle de la source)
PROFILES: dict[str, tuple[str, list[str] | None]] = {
    # ── Même aliment, autre nom ─────────────────────────────────────────────────────────
    "egg": ("oeuf", None),
    "milk": ("lait", None),
    "cream": ("creme", None),
    "beurre": ("butter", None),
    "potato": ("pommes_de_terre", None),
    "soy_sauce": ("sauce_soja", None),
    "miso": ("miso_paste", None),
    "tomato_paste": ("concentre_de_tomate", None),
    "leek": ("poireau", None),
    "salade": ("lettuce", None),
    "peanut": ("cacahuete", None),
    "almonds": ("almond", None),
    "walnuts": ("walnut", None),
    "pine_nuts": ("pine_nut", None),
    "flax_seeds": ("ground_flaxseeds", None),
    "quinoa": ("quinoa_grain", None),
    "riz_basmati": ("basmati_rice", None),
    "semolina": ("semoule_de_couscous_moyenne", None),
    "white_bean": ("white_bean_cooked", None),
    "kidney_beans": ("red_bean_cooked", None),
    "black_beans": ("black_bean_cooked", None),
    "black_eyed_peas": ("black_eyed_bean_cooked", None),
    "lentils": ("green_lentil", None),
    "lentilles_corail": ("red_lentil", None),
    "butternut": ("squash", None),
    "dandelion_greens": ("dandelion", None),
    "gundruk": ("fermented_leaf_gundruk", None),
    "umeboshi": ("prune_umeboshi", None),
    "comte": ("gruyere_cheese", None),
    "dijon_mustard": ("moutarde", None),
    "mola_sauce": ("mole_sauce", None),
    "gnocchi_vegan": ("gnocchi", None),
    "tea": ("green_tea", None),
    "matcha": ("matcha_tea", None),
    # ── Produits laitiers et substituts ─────────────────────────────────────────────────
    "condensed_milk": ("creme", ["sweet", "rich"]),
    "milk_powder": ("cheese", ["rich", "sweet"]),
    "mascarpone": ("creme_fraiche", ["rich", "sweet"]),
    "cottage_cheese": ("fresh_cheese", ["rich", "sour"]),
    "fromage": ("cheese", ["salty", "rich"]),
    "camembert": ("cheese", ["salty", "rich", "earthy"]),
    "roquefort": ("cheese", ["salty", "pungent", "rich"]),
    "tomme_de_savoie": ("cheese", ["nutty", "rich"]),
    "mozzarella_vegane": ("lait_coco", ["rich"]),
    # ── Légumineuses, soja, blé ─────────────────────────────────────────────────────────
    "pea": ("snow_pea", ["sweet", "fresh"]),
    "edamame": ("soybean", ["sweet", "nutty", "fresh"]),
    "mung_bean": ("green_lentil", ["earthy"]),
    "aquafaba": ("chickpea", ["neutral"]),
    "soy_flour": ("soybean", ["nutty"]),
    "red_bean_paste": ("red_bean_cooked", ["sweet", "earthy"]),
    "seitan": ("flour", ["umami", "neutral"]),
    "wheat_gluten": ("flour", ["neutral"]),
    "vegetarian_bacon": ("tempeh", ["smoky", "salty", "umami"]),
    # ── Céréales et pains ───────────────────────────────────────────────────────────────
    "brown_rice": ("rice", ["nutty", "earthy"]),
    "barley": ("oats", ["nutty", "earthy"]),
    "millet": ("oats", ["nutty"]),
    "tteok": ("rice", ["neutral"]),
    "bagel": ("bread", ["neutral"]),
    "croutons": ("bread", ["salty"]),
    "ladyfinger_biscuits": ("bread", ["sweet"]),
    # ── Noix et graines ─────────────────────────────────────────────────────────────────
    "cashew": ("almond", ["rich", "sweet", "nutty"]),
    "cashews": ("almond", ["rich", "sweet", "nutty"]),
    "hazelnut": ("almond", ["nutty", "sweet"]),
    "pistachios": ("almond", ["nutty", "sweet"]),
    "macadamia_nuts": ("almond", ["rich", "nutty"]),
    "pecan": ("walnut", ["nutty", "sweet", "rich"]),
    "chestnuts": ("oats", ["sweet", "nutty", "earthy"]),
    "hemp_seeds": ("sesame_seed", ["nutty", "earthy"]),
    "sunflower_seeds": ("pumpkin_seeds", ["nutty"]),
    "poppy_seed": ("sesame_seed", ["nutty"]),
    "coconut_flesh": ("lait_coco", ["sweet", "rich"]),
    # ── Légumes et herbes ───────────────────────────────────────────────────────────────
    "coriander": ("parsley", ["fresh", "floral"]),
    "shallot": ("onion", ["pungent", "sweet"]),
    "arugula": ("lettuce", ["bitter", "pungent", "fresh"]),
    "watercress": ("lettuce", ["pungent", "fresh", "bitter"]),
    "endive": ("chicory", ["bitter", "fresh"]),
    "celeriac": ("celery", ["earthy", "fresh"]),
    "parsnip": ("carrot", ["sweet", "earthy"]),
    "jerusalem_artichoke": ("pommes_de_terre", ["sweet", "nutty", "earthy"]),
    "lotus_root": ("pommes_de_terre", ["earthy", "neutral"]),
    "chayote": ("zucchini", ["fresh", "neutral"]),
    "pickles": ("cucumber", ["sour", "salty"]),
    "kombu": ("dried_seaweed", ["umami", "salty"]),
    "agar_agar": ("dried_seaweed", ["neutral"]),
    "wasabi": ("radish", ["pungent", "spicy"]),
    "sage": ("thyme", ["earthy", "bitter"]),
    "tarragon": ("aneth", ["fresh", "sweet"]),
    "chervil": ("parsley", ["fresh", "sweet"]),
    # ── Fruits ──────────────────────────────────────────────────────────────────────────
    "apple": ("lemon", ["sweet", "sour", "fresh"]),
    "pear": ("lemon", ["sweet", "fresh"]),
    "rhubarb": ("lemon", ["sour", "fresh"]),
    "strawberry": ("pineapple", ["sweet", "sour", "fresh"]),
    "raspberry": ("myrtill", ["sweet", "sour"]),
    "blueberry": ("myrtill", ["sweet", "sour"]),
    "mixed_berries": ("myrtill", ["sweet", "sour"]),
    "lingonberry": ("myrtill", ["sour", "bitter"]),
    "cherry": ("myrtill", ["sweet", "sour"]),
    "sour_cherry": ("myrtill", ["sour", "sweet"]),
    "acai": ("myrtill", ["earthy", "sour"]),
    "grape": ("orange", ["sweet"]),
    "melon": ("orange", ["sweet", "fresh", "floral"]),
    "kiwi": ("orange", ["sour", "sweet", "fresh"]),
    "grapefruit": ("orange", ["bitter", "sour"]),
    "plum": ("orange", ["sweet", "sour"]),
    "fig": ("banana", ["sweet", "rich"]),
    "mango": ("pineapple", ["sweet", "floral"]),
    "papaya": ("pineapple", ["sweet", "floral"]),
    "passion_fruit": ("pineapple", ["sour", "floral", "sweet"]),
    "dates": ("raisins_sec", ["sweet", "rich"]),
    "dried_fig": ("raisins_sec", ["sweet", "rich"]),
    "dried_apricot": ("raisins_sec", ["sweet", "sour"]),
    "prune": ("raisins_sec", ["sweet", "rich"]),
    "cranberries_dried": ("raisins_sec", ["sweet", "sour"]),
    # ── Sucres, confitures, condiments ──────────────────────────────────────────────────
    "strawberry_jam": ("sugar", ["sweet"]),
    "cherry_jam": ("sugar", ["sweet"]),
    "molasses": ("sugar", ["sweet", "bitter", "rich"]),
    "agave_syrup": ("sirop_d_erable", ["sweet"]),
    "chutney": ("sugar", ["sweet", "sour", "spicy"]),
    # ── Épices ──────────────────────────────────────────────────────────────────────────
    "cloves": ("cinnamon", ["spicy", "sweet", "pungent"]),
    "caraway": ("cinnamon", ["earthy", "spicy"]),
    "anise_seed": ("cinnamon", ["sweet", "floral"]),
    "five_spice": ("cinnamon", ["spicy", "sweet"]),
    "juniper_berries": ("cinnamon", ["bitter", "floral"]),
    "curry_powder": ("cinnamon", ["spicy", "earthy"]),
    "chili_powder": ("cinnamon", ["spicy", "smoky"]),
    "vanilla_extract": ("cinnamon", ["sweet", "floral"]),
    "vanilla_pod": ("cinnamon", ["sweet", "floral"]),
    # ── Café, cacao, alcools, levants ───────────────────────────────────────────────────
    "coffee": ("dark_chocolate", ["bitter", "rich"]),
    "cocoa_powder": ("dark_chocolate", ["bitter", "rich"]),
    "white_wine": ("vinegar", ["sour", "fresh"]),
    "red_wine": ("vinegar", ["sour", "rich"]),
    "cider": ("vinegar", ["sour", "sweet"]),
    "marsala": ("vinegar", ["sweet", "rich"]),
    "cognac": ("vinegar", ["rich", "sweet"]),
    "rum": ("vinegar", ["sweet", "rich"]),
    "kirsch": ("vinegar", ["sweet", "floral"]),
    "calvados": ("vinegar", ["sweet", "fresh"]),
    "baking_powder": ("salt", ["neutral"]),
    "baking_soda": ("salt", ["neutral"]),
}

VOCAB = {"earthy", "sweet", "rich", "spicy", "neutral", "bitter", "sour", "fresh", "nutty",
         "umami", "salty", "floral", "pungent", "tangy", "smoky"}


def apply(catalog: dict, flavor: dict, carbon: dict) -> list[str]:
    log = []
    for key, tags in FLAVOR_ONLY.items():
        if key not in flavor:
            flavor[key] = list(tags)
            log.append(f"saveur {key} = {tags}")
    for key, (src, tags) in PROFILES.items():
        if key not in catalog:
            raise SystemExit(f"{key} n'est pas une clé du catalogue")
        if src not in carbon:
            raise SystemExit(f"source carbone inconnue pour {key} : {src}")
        if tags is None and src not in flavor:
            raise SystemExit(f"source saveur inconnue pour {key} : {src}")
        if tags and not set(tags) <= VOCAB:
            raise SystemExit(f"{key} : saveur hors vocabulaire {set(tags) - VOCAB}")
        if key not in carbon:
            carbon[key] = carbon[src]
            log.append(f"carbone {key} ← {src} ({carbon[src]})")
        if key not in flavor:
            flavor[key] = list(tags) if tags else list(flavor[src])
            log.append(f"saveur {key} = {flavor[key]}")
    return log


def _write(path: Path, data: dict) -> None:
    end = "\n" if path.read_bytes().endswith(b"\n") else ""
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + end)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    flavor = json.loads(FLAVOR_PATH.read_text(encoding="utf-8"))
    carbon = json.loads(CARBON_PATH.read_text(encoding="utf-8"))
    before = (json.dumps(flavor, sort_keys=True), json.dumps(carbon, sort_keys=True))
    log = apply(catalog, flavor, carbon)
    print(f"{len(log)} changement(s)")
    missing = sorted(k for k in catalog if k not in carbon or k not in flavor)
    print(f"clés du catalogue encore sans profil : {missing}")
    if args.dry_run:
        print("[dry-run] rien n'est écrit")
        return
    if json.dumps(flavor, sort_keys=True) != before[0]:
        _write(FLAVOR_PATH, flavor)
    if json.dumps(carbon, sort_keys=True) != before[1]:
        _write(CARBON_PATH, carbon)


if __name__ == "__main__":
    main()
