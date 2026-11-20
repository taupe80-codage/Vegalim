#!/usr/bin/env python3
"""
shortcrust_split_2026_11_20.py — pâte brisée végétale et pur beurre séparées.

La variante vegan remplace désormais la pâte brisée pur beurre par la pâte brisée à
la matière grasse végétale, qui n'avait pas d'entrée de prix (« Prix inconnu ») ni
d'empreinte carbone. L'entrée existante « Pâte brisée » portait déjà le carbone de
la pâte pur beurre (AGRIBALYSE 23414) : elle devient « Pâte brisée pur beurre », et
la pâte végétale reçoit la sienne, comme pour la pâte feuilletée. Carbone : AGRIBALYSE
donne 3,59 kg CO₂e/kg aux deux (23412 végétale, 23414 pur beurre) ; la valeur est donc
reprise telle quelle (carbon_agribalyse_2026_11_19.py ne recalcule que les clés présentes
dans les compositions, et la pâte végétale n'apparaît que dans la variante vegan).

Prix relevés sur carrefour.fr le 2026-11-20 (rouleaux de 230 g).

Idempotent.

Usage :
    python scripts/ingredients/shortcrust_split_2026_11_20.py [--dry-run]
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

ENTRIES = {
    "shortcrust_pastry": {
        "name_fr": "Pâte brisée pur beurre", "pantry": False,
        "packages": [{"qty": 230, "unit": "g", "price": 1.19, "label": "rouleau 230g"}],
        "last_updated": DATE,
        "price_source": f"relevé carrefour.fr {DATE} (Carrefour Original pur beurre 230 g)",
        "unit_weight_g": 230.0},
    "shortcrust_pastry_vegetable": {
        "name_fr": "Pâte brisée (matière grasse végétale)", "pantry": False,
        "packages": [{"qty": 230, "unit": "g", "price": 0.65, "label": "rouleau 230g"}],
        "last_updated": DATE,
        "price_source": f"relevé carrefour.fr {DATE} (Carrefour Classic' 230 g)",
        "unit_weight_g": 230.0},
}
LINKS = {
    "shortcrust_pastry_vegetable_fat_raw_paste_pre_packaged_plant": "shortcrust_pastry_vegetable",
    "shortcrust_pastry_vegetable_fat_cooked_paste_pre_packaged_plant": "shortcrust_pastry_vegetable",
    "shortcrust_pastry_all_butter_cooked_paste_pre_packaged": "shortcrust_pastry",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    paths = (CATALOG_PATH, MAP_PATH, FLAVOR_PATH, CARBON_PATH)
    catalog, price_map, flavor, carbon = (json.loads(p.read_text(encoding="utf-8")) for p in paths)
    log: list[str] = []
    for key, entry in ENTRIES.items():
        if catalog.get(key) != entry:
            log.append(f"catalogue {key}")
            catalog[key] = entry
    new = "shortcrust_pastry_vegetable"
    if new not in flavor:
        flavor[new] = flavor["shortcrust_pastry"]
        log.append(f"saveur {new}")
    if new not in carbon:
        carbon[new] = carbon["shortcrust_pastry"]
        log.append(f"carbone {new} (provisoire)")
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
