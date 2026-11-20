#!/usr/bin/env python3
"""
add_missing_prices_2026_11_20.py — les 4 derniers ingrédients sans prix (7 recettes
affichaient « Prix inconnu ») reçoivent leur entrée du catalogue de prix.

  feuilles de maïs séchées (tamales, humita) · pilons de moringa (sambar, avial)
  tomatilles (enchiladas) · hibiscus séché (boisson à l'oseille de Guinée)

On les achète en épicerie latino ou indienne, ou en ligne : la forme retenue est celle
qu'on trouve en France (tomatilles en boîte, moringa surgelé, calices d'hibiscus
séchés — la roselle fraîche n'y est pas vendue).

Prix : estimations manuelles (price_source « estimation… » → « prix estimé »).
Carbone : provisoire ici ; carbon_agribalyse_2026_11_19.py le recalcule (analogues
BY_NAME / EXTERNAL du bloc 2026-11-20).

Idempotent.

Usage :
    python scripts/ingredients/add_missing_prices_2026_11_20.py [--dry-run]
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
SOURCE = f"estimation manuelle {DATE} (épicerie spécialisée ou vente en ligne ; produit absent des grandes surfaces)"


def pkg(qty, unit, price, label):
    return {"qty": qty, "unit": unit, "price": price, "label": label}


# clé : (nom, garde-manger, conditionnements, saveur, carbone provisoire de la clé…)
NEW: dict[str, tuple] = {
    "corn_husk":         ("Feuilles de maïs séchées (tamales)", True,
                          [pkg(100, "g", 4.5, "sachet 100g")], ["neutral", "earthy"], "corn"),
    "moringa_drumstick": ("Pilons de moringa (drumsticks)", False,
                          [pkg(400, "g", 2.99, "sachet surgelé 400g")], ["earthy", "fresh"], "green_bean"),
    "tomatillo":         ("Tomatilles", True,
                          [pkg(794, "g", 5.49, "boîte 794g")], ["sour", "fresh"], "tomato"),
    "dried_hibiscus":    ("Fleurs d'hibiscus séchées (bissap)", True,
                          [pkg(100, "g", 2.49, "sachet 100g")], ["sour", "floral", "sweet"], "tea"),
}

# id de recette → clé (corn_husk est déjà l'id)
LINKS: dict[str, str] = {
    "drumstick_horseradish_tree_raw_pod": "moringa_drumstick",
    "tomatillo_raw": "tomatillo",
    "roselle_raw": "dried_hibiscus",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    paths = (CATALOG_PATH, MAP_PATH, FLAVOR_PATH, CARBON_PATH)
    catalog, price_map, flavor, carbon = (json.loads(p.read_text(encoding="utf-8")) for p in paths)
    log: list[str] = []

    for key, (name, pantry, packages, own_flavor, carbon_of) in NEW.items():
        entry = {"name_fr": name, "pantry": pantry, "packages": packages,
                 "last_updated": DATE, "price_source": SOURCE}
        if catalog.get(key) != entry:
            log.append(f"catalogue {key}")
            catalog[key] = entry
        if key not in flavor:
            flavor[key] = own_flavor
            log.append(f"saveur {key}")
        if key not in carbon:
            carbon[key] = carbon[carbon_of]
            log.append(f"carbone {key} (provisoire, de {carbon_of})")

    for rid, key in LINKS.items():
        if price_map.get(rid) != key:
            log.append(f"lien {rid} : {price_map.get(rid)} → {key}")
            price_map[rid] = key

    print(*log, f"{len(log)} changement(s)", sep="\n")
    if args.dry_run or not log:
        return
    for p, d in zip(paths, (catalog, price_map, flavor, carbon)):
        end = "\n" if p.read_bytes().endswith(b"\n") else ""
        with p.open("w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + end)


if __name__ == "__main__":
    main()
