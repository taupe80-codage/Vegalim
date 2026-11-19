#!/usr/bin/env python3
"""
ingredients_lot_17_2026_11_19.py — prix, liens de prix, profils et disponibilité
des ingrédients nouveaux du lot de recettes n17 (plats de printemps).

Chaque ingrédient de recette doit avoir un prix (ou figurer dans UNPRICED_OK) et une
disponibilité renseignée (tests/test_data_integrity.py). Une nouvelle clé du catalogue
reçoit un profil de saveur et de carbone dérivé.

Prix : ESTIMATIONS d'après les prix de saison usuels en grande surface et sur les marchés
(artichaut ~1,60 € la pièce de 350 g, pommes de terre primeur ~2,80 € le kg, oseille
~2 € la barquette de 100 g), aucun relevé daté.

Idempotent ; n'écrase aucune disponibilité déjà renseignée.

Usage :
    python scripts/ingredients/ingredients_lot_17_2026_11_19.py --dry-run
    python scripts/ingredients/ingredients_lot_17_2026_11_19.py
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
AVAIL_PATH = ROOT / "backend/data/graphs/ingredient_availability_graph_v1.json"
TODAY = "2026-11-19"


def pkg(qty, unit, price, label):
    return {"qty": qty, "unit": unit, "price": price, "label": label}


NEW_ENTRIES: dict[str, dict] = {
    "artichoke":  {"name_fr": "Artichaut", "unit_weight_g": 350,            # estimation
                   "packages": [pkg(1, "piece", 1.60, "pièce ~350g")]},
    "new_potato": {"name_fr": "Pommes de terre nouvelles",                 # estimation
                   "packages": [pkg(1000, "g", 2.79, "filet 1kg")]},
    "sorrel":     {"name_fr": "Oseille",                                   # estimation
                   "packages": [pkg(100, "g", 1.99, "barquette 100g")]},
}

MAP_FIXES: dict[str, str] = {
    "artichoke_raw": "artichoke",
    "new_potato_raw": "new_potato",
    "dock_sorrel_raw": "sorrel",
}

# nouvelle clé → (source saveur, source carbone)
DERIVED_PROFILES: dict[str, tuple[str, str]] = {
    "new_potato": ("pommes_de_terre", "pommes_de_terre"),
    "sorrel": ("spinach", "spinach"),
}

# id → (disponibilité, catégorie, nom)
AVAILABILITY: dict[str, tuple[object, str, str]] = {
    "artichoke_raw": (True, "vegetable", "artichaut"),
    "new_potato_raw": (True, "vegetable", "pomme de terre nouvelle"),
    "dock_sorrel_raw": (True, "vegetable", "oseille"),
}


def apply(catalog, price_map, flavor, carbon, avail) -> list[str]:
    log = []
    for key, e in NEW_ENTRIES.items():
        if key not in catalog:
            catalog[key] = {"name_fr": e["name_fr"], "pantry": False,
                            "packages": [dict(p) for p in e["packages"]],
                            "last_updated": TODAY,
                            **({"unit_weight_g": e["unit_weight_g"]} if "unit_weight_g" in e else {})}
            log.append(f"+ catalogue {key}")
    for rid, key in MAP_FIXES.items():
        if key not in catalog:
            raise SystemExit(f"clé de catalogue inconnue pour {rid} : {key}")
        if price_map.get(rid) != key:
            log.append(f"lien {rid}: {price_map.get(rid)} → {key}")
            price_map[rid] = key
    for key, (f_src, c_src) in DERIVED_PROFILES.items():
        if key not in flavor:
            flavor[key] = list(flavor[f_src])
            log.append(f"saveur {key} ← {f_src}")
        if key not in carbon:
            carbon[key] = carbon[c_src]
            log.append(f"carbone {key} ← {c_src}")
    for iid, (value, cat, name) in AVAILABILITY.items():
        entry = avail.setdefault(iid, {"available_in_france": None, "category": cat, "name_fr": name})
        if entry.get("available_in_france") is None:
            entry["available_in_france"] = value
            log.append(f"dispo {iid} → {value}")
    return log


def _write(path: Path, data: dict) -> None:
    end = "\n" if path.read_bytes().endswith(b"\n") else ""
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + end)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    paths = (CATALOG_PATH, MAP_PATH, FLAVOR_PATH, CARBON_PATH, AVAIL_PATH)
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
