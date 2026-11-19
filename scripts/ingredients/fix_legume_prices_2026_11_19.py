#!/usr/bin/env python3
"""
fix_legume_prices_2026_11_19.py — sépare les légumineuses sèches, en conserve et fraîches
dans le catalogue de prix.

Constat : ingredient_cost_eur prend le paquet le moins cher au gramme. Pois chiches,
haricots blancs, haricots rouges et fèves n'avaient qu'une entrée, une boîte comptée à
son poids BRUT (400 g), alors qu'elle contient 240 à 265 g de légumineuses égouttées :
  - les légumineuses cuites (*_boiled, *_canned, poids égoutté dans les recettes)
    coûtaient ~40 % de moins qu'en réalité ;
  - les sèches (*_dried, *_raw) étaient chiffrées au prix de la conserve ;
  - les fèves fraîches écossées (lot n17) au prix de la boîte de fèves.

Correction :
  1. CANNED_DRAINED : la boîte garde son étiquette (ce qu'on achète) mais sa quantité
     devient le poids égoutté (ce que la recette compte) ; la liste de courses compte
     ainsi le bon nombre de boîtes.
  2. NEW_ENTRIES : entrées « sec » séparées, lentilles cuites et niébé en conserve,
     fèves fraîches vendues en cosses (≈ 30 % de grains écossés).
  3. MAP_FIXES : chaque id de recette vers l'entrée de son état (sec / cuit / frais).

Poids égouttés : mentions usuelles des boîtes 4/4 de 400 g (240 g pour les pois chiches
et haricots noirs, 250 g pour les haricots, 265 g pour les lentilles, 280 g pour les
petits pois). Prix des nouvelles entrées : ESTIMATIONS alignées sur les sachets secs
déjà au catalogue (lentilles vertes 1,41 €, niébé 1,90 € les 500 g) ; fèves en cosses
~4,50 € le kg sur les marchés en saison. Aucun relevé daté.

Idempotent.

Usage :
    python scripts/ingredients/fix_legume_prices_2026_11_19.py --dry-run
    python scripts/ingredients/fix_legume_prices_2026_11_19.py
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
TODAY = "2026-11-19"


def pkg(qty, unit, price, label, note=None):
    p = {"qty": qty, "unit": unit, "price": price, "label": label}
    if note:
        p["note"] = note
    return p


# clé → {étiquette de la boîte : poids égoutté en g}
CANNED_DRAINED: dict[str, dict[str, int]] = {
    "chickpea": {"boîte 400g": 240},
    "white_bean": {"boîte 400g": 250},
    "kidney_beans": {"boîte 400g": 250},
    "black_bean_cooked": {"boîte 400g": 240},
    "fava_bean": {"boîte 400g": 250},
    "pea": {"boîte 400g": 280},
}

# paquets « sec » à sortir d'une entrée de conserve vers une entrée dédiée
MOVE_PACKAGES: dict[str, tuple[str, str]] = {
    "chickpea": ("sec 500g", "chickpea_dry"),
}

NEW_ENTRIES: dict[str, dict] = {
    "chickpea_dry":          {"name_fr": "Pois chiches secs", "packages": []},  # paquet déplacé
    "white_bean_dry":        {"name_fr": "Haricots blancs secs",
                              "packages": [pkg(500, "g", 1.99, "sachet 500g")]},
    "kidney_beans_dry":      {"name_fr": "Haricots rouges secs",
                              "packages": [pkg(500, "g", 1.99, "sachet 500g")]},
    "fava_bean_dry":         {"name_fr": "Fèves sèches",
                              "packages": [pkg(500, "g", 2.49, "sachet 500g")]},
    "fresh_fava_bean":       {"name_fr": "Fèves fraîches",
                              "packages": [pkg(300, "g", 4.50, "1 kg en cosses",
                                               "≈ 300 g de grains écossés")]},
    "green_lentil_cooked":   {"name_fr": "Lentilles cuites",
                              "packages": [pkg(265, "g", 1.35, "boîte 400g",
                                               "400 g brut, 265 g égouttés")]},
    "black_eyed_peas_canned": {"name_fr": "Niébé en conserve",
                               "packages": [pkg(240, "g", 1.59, "boîte 400g",
                                                "400 g brut, 240 g égouttés")]},
}

MAP_FIXES: dict[str, str] = {
    # sec
    "chickpea_raw_dried": "chickpea_dry",
    "roasted_chickpea": "chickpea_dry",
    "white_bean_raw": "white_bean_dry",
    "great_northern_bean_dried": "white_bean_dry",
    "kidney_bean_dried": "kidney_beans_dry",
    "medium_red_bean_dried": "kidney_beans_dry",
    "fava_bean_dried": "fava_bean_dry",
    "broadbeans_fava_beans_raw_dried": "fava_bean_dry",
    # frais
    "broadbeans_fava_beans_raw_fresh": "fresh_fava_bean",
    "broadbeans_fava_beans_boiled_fresh": "fresh_fava_bean",
    # cuit, égoutté
    "green_lentil_boiled": "green_lentil_cooked",
    "black_eyed_peas_cowpeas_boiled": "black_eyed_peas_canned",
}

# nouvelle clé → (source carbone, saveur ; None = celle de la source)
PROFILES: dict[str, tuple[str, list[str] | None]] = {
    "chickpea_dry": ("chickpea", None),
    "white_bean_dry": ("white_bean_cooked", None),
    "kidney_beans_dry": ("red_bean_cooked", None),
    "fava_bean_dry": ("dried_fava_bean", None),
    "fresh_fava_bean": ("fava_bean", ["sweet", "fresh", "earthy"]),
    "green_lentil_cooked": ("green_lentil", None),
    "black_eyed_peas_canned": ("black_eyed_bean_cooked", None),
}


def apply(catalog, price_map, flavor, carbon) -> list[str]:
    log = []
    for key, e in NEW_ENTRIES.items():
        if key not in catalog:
            catalog[key] = {"name_fr": e["name_fr"], "pantry": False,
                            "packages": [dict(p) for p in e["packages"]],
                            "last_updated": TODAY}
            log.append(f"+ catalogue {key}")
    for src, (label, dest) in MOVE_PACKAGES.items():
        moving = [p for p in catalog[src]["packages"] if p.get("label") == label]
        if moving:
            catalog[src]["packages"] = [p for p in catalog[src]["packages"] if p.get("label") != label]
            catalog[dest]["packages"].extend(moving)
            catalog[src]["last_updated"] = catalog[dest]["last_updated"] = TODAY
            log.append(f"paquet « {label} » : {src} → {dest}")
    for key, drained in CANNED_DRAINED.items():
        for p in catalog[key]["packages"]:
            g = drained.get(p.get("label"))
            if g and p["qty"] != g:
                log.append(f"{key} {p['label']} : {p['qty']} g → {g} g égouttés")
                p["qty"] = g
                p["note"] = f"400 g brut, {g} g égouttés"
                catalog[key]["last_updated"] = TODAY
    for rid, key in MAP_FIXES.items():
        if key not in catalog:
            raise SystemExit(f"clé de catalogue inconnue pour {rid} : {key}")
        if price_map.get(rid) != key:
            log.append(f"lien {rid}: {price_map.get(rid)} → {key}")
            price_map[rid] = key
    for key, (src, tags) in PROFILES.items():
        if key not in carbon:
            carbon[key] = carbon[src]
            log.append(f"carbone {key} ← {src}")
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
    paths = (CATALOG_PATH, MAP_PATH, FLAVOR_PATH, CARBON_PATH)
    data = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    before = [json.dumps(d, sort_keys=True) for d in data]
    log = apply(*data)
    for line in log:
        print(line)
    print(f"{len(log)} changement(s)")
    if args.dry_run:
        print("[dry-run] rien n'est écrit")
        return
    for p, d, b in zip(paths, data, before):
        if json.dumps(d, sort_keys=True) != b:
            _write(p, d)


if __name__ == "__main__":
    main()
