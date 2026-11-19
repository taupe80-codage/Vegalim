#!/usr/bin/env python3
"""
fix_package_prices_2026_11_16.py — corrige les conditionnements du catalogue de
prix qui avaient tous le même prix (citron à la pièce = filet de 5…).

Cause : scripts/update_prices.py écrivait le prix médian Open Food Facts (taille
de produit inconnue) sur le paquet le MOINS CHER de l'entrée ; relance après
relance, tous les paquets d'une même entrée ont convergé vers ce prix. Le
script fait désormais varier tous les paquets dans la même proportion.

Règle de correction : le prix rafraîchi est gardé sur le conditionnement qu'il
décrit de façon plausible (souvent le lot ou le grand format) ; l'autre est
ramené à un prix moyen de grande surface (estimation manuelle, novembre 2026,
marque de distributeur). Huile d'olive : seule la bouteille de 25 cl, au même
prix que celle de 75 cl, est corrigée.

Idempotent. Usage :
    python scripts/fix_package_prices_2026_11_16.py --dry-run
    python scripts/fix_package_prices_2026_11_16.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent / "backend/data/config/prices_catalog.json"

# clé du catalogue → {label du paquet : prix corrigé en €}
FIXES: dict[str, dict[str, float]] = {
    "butter":            {"plaquette 250g": 2.40},
    "beurre":            {"plaquette 250g": 2.40},
    # "chickpea" : boîte remplacée par la boîte 4/4 relevée (prices_releves_2026_11_19.py)
    "onion":             {"filet 1kg": 1.95},
    "garlic":            {"tête d'ail": 0.85},
    "carrot":            {"sachet 500g": 1.10},
    "sweet_potato":      {"pièce ~400g": 1.40},
    "zucchini":          {"pièce ~350g": 1.10},
    "eggplant":          {"pièce ~400g": 1.95},
    "bell_pepper":       {"pièce": 1.20},
    "red_bell_pepper":   {"pièce": 1.20},
    "shiitake_mushroom": {"séchés 40g": 3.90},
    "green_bean":        {"surgelé 1kg": 2.60},
    "lemon":             {"pièce": 0.55},
    "lime":              {"pièce": 0.60},
    "avocado":           {"pièce": 1.25},
    "ginger":            {"racine ~100g": 0.95},
    "basil":             {"sachets 25g": 1.50},
    "cream":             {"briquette 20cl": 1.20},
    "yogurt":            {"pot individuel 125g": 0.45},
    "parmesan":          {"râpé 60g": 2.10},
    "tofu":              {"bloc 400g": 3.40},
    "soy_sauce":         {"bouteille 15cl": 2.60},
    "olive_oil":         {"25cl": 4.50},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    changed = 0
    for key, fixes in FIXES.items():
        packages = {p.get("label"): p for p in catalog[key]["packages"]}
        for label, price in fixes.items():
            pkg = packages[label]          # KeyError = table à revoir
            if pkg["price"] != price:
                print(f"{key:18} {label:22} {pkg['price']:>6.2f} → {price:.2f} €")
                pkg["price"] = price
                changed += 1
    print(f"{changed} conditionnement(s) corrigé(s)")
    if args.dry_run or not changed:
        return
    with CATALOG_PATH.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
