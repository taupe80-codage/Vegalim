#!/usr/bin/env python3
"""
surveyed_prices_2026_11_20.py — les prix estimés les plus fréquents (créés par
split_catalog_entries_2026_11_20.py) remplacés par des prix relevés.

Relevés : prix affichés par carrefour.fr dans les résultats de recherche le 2026-11-20
(les fiches produit refusent la lecture automatique ; le prix dépend du magasin et du
mode de retrait). Marque distributeur ou premier prix courant quand il existe. Le
tamari n'a pas de prix chez Carrefour : relevé d'une épicerie japonaise en ligne.

Un price_source « relevé… » fait disparaître la mention « prix estimé » de la fiche.

Idempotent.

Usage :
    python scripts/ingredients/surveyed_prices_2026_11_20.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
DATE = "2026-11-20"


def pkg(qty, unit, price, label):
    return {"qty": qty, "unit": unit, "price": price, "label": label}


def carrefour(detail: str) -> str:
    return f"relevé carrefour.fr {DATE} ({detail})"


# clé : (conditionnements, source)
SURVEY: dict[str, tuple[list[dict], str]] = {
    "dried_thyme":       ([pkg(32, "g", 1.5, "pot 32g"), pkg(85, "g", 4.19, "pot 85g")],
                          carrefour("Epicea 32 g ; Ducros 85 g")),
    "red_wine_vinegar":  ([pkg(1000, "ml", 0.55, "bouteille 1L"), pkg(750, "ml", 1.05, "bouteille 75cl")],
                          carrefour("Carrefour 1 L ; Carrefour Classic' 75 cl")),
    "cider_vinegar":     ([pkg(750, "ml", 0.89, "bouteille 75cl")], carrefour("Carrefour Classic' 75 cl")),
    "brown_sugar":       ([pkg(1000, "g", 2.99, "boîte 1kg")], carrefour("Béghin Say sucre blond en poudre 1 kg")),
    "oat_milk":          ([pkg(1000, "ml", 1.56, "brique 1L")], carrefour("boisson avoine Carrefour 1 L")),
    "crushed_tomato":    ([pkg(400, "g", 1.09, "boîte 400g"), pkg(1200, "g", 2.55, "3 boîtes 400g")],
                          carrefour("Mutti Polpa 400 g et lot de 3")),
    "vegan_butter":      ([pkg(250, "g", 2.35, "plaquette 250g")], carrefour("Flora alternative végétale au beurre 250 g")),
    "buckwheat_flour":   ([pkg(500, "g", 3.85, "paquet 500g")], carrefour("Ethiquable Bretagne bio 500 g")),
    "goat_cheese":       ([pkg(180, "g", 1.89, "bûche 180g")], carrefour("bûche de chèvre Carrefour 180 g")),
    "soy_yogurt":        ([pkg(600, "g", 1.79, "6 pots (600g)")], carrefour("Carrefour Sensation soja nature 6 × 100 g")),
    "balsamic_vinegar":  ([pkg(500, "ml", 1.69, "bouteille 50cl")], carrefour("Carrefour Extra balsamique de Modène 50 cl")),
    "tamari":            ([pkg(250, "ml", 5.99, "bouteille 25cl")],
                          f"relevé satsuki.fr {DATE} (Kikkoman tamari 250 ml ; absent de carrefour.fr)"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    log: list[str] = []
    for key, (packages, source) in SURVEY.items():
        e = catalog[key]
        if e.get("packages") != packages or e.get("price_source") != source:
            log.append(f"{key} : {[p['price'] for p in e['packages']]} → {[p['price'] for p in packages]}")
            e.update(packages=packages, price_source=source, last_updated=DATE)
    print(*log, f"{len(log)} changement(s)", sep="\n")
    if args.dry_run or not log:
        return
    end = "\n" if CATALOG_PATH.read_bytes().endswith(b"\n") else ""
    with CATALOG_PATH.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(catalog, ensure_ascii=False, indent=2) + end)


if __name__ == "__main__":
    main()
