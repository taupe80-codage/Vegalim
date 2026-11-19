#!/usr/bin/env python3
"""
ketchup_2026_11_20.py — le ketchup avait la clé de prix « tomato » (prix et empreinte
de la tomate fraîche, et suivait donc la saison de la tomate côté carbone sans le
garde-fou du calendrier). Il reçoit sa propre entrée.

Prix : Carrefour Classic' 560 g, 1,25 € (relevé carrefour.fr 2026-11-20 ; Heinz 342 g
1,45-1,49 €). Carbone : AGRIBALYSE 3.2 « Ketchup » (11008), appliqué par
carbon_agribalyse_2026_11_19.py (BY_NAME) — relancer ce script après celui-ci.

Idempotent.

Usage :
    python scripts/ingredients/ketchup_2026_11_20.py [--dry-run]
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

ENTRY = {"name_fr": "Ketchup", "pantry": True,
         "packages": [{"qty": 560, "unit": "g", "price": 1.25, "label": "flacon 560g"}],
         "last_updated": "2026-11-20",
         "price_source": "relevé carrefour.fr 2026-11-20 (Carrefour Classic' ; Heinz 342 g 1,45-1,49 €)"}
LINKS = {"tomato_ketchup_catsup_pre_packaged_normal": "ketchup"}
FLAVOR = ["sweet", "sour", "umami"]
CARBON_PLACEHOLDER = 0.119   # Agribalyse 11008, 1,19 kg CO₂e/kg ; recalculé par le script Agribalyse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    paths = (CATALOG_PATH, MAP_PATH, FLAVOR_PATH, CARBON_PATH)
    catalog, price_map, flavor, carbon = (json.loads(p.read_text(encoding="utf-8")) for p in paths)
    log = []
    if catalog.get("ketchup") != ENTRY:
        catalog["ketchup"] = ENTRY
        log.append("catalogue ketchup")
    for rid, key in LINKS.items():
        if price_map.get(rid) != key:
            log.append(f"lien {rid}: {price_map.get(rid)} → {key}")
            price_map[rid] = key
    if "ketchup" not in flavor:
        flavor["ketchup"] = FLAVOR
        log.append("saveur ketchup")
    if "ketchup" not in carbon:
        carbon["ketchup"] = CARBON_PLACEHOLDER
        log.append("carbone ketchup")
    print(*log, f"{len(log)} changement(s)", sep="\n")
    if args.dry_run or not log:
        return
    for p, d in zip(paths, (catalog, price_map, flavor, carbon)):
        end = "\n" if p.read_bytes().endswith(b"\n") else ""
        with p.open("w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(d, ensure_ascii=False, indent=2) + end)


if __name__ == "__main__":
    main()
