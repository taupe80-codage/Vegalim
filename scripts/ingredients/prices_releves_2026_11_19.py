#!/usr/bin/env python3
"""
prices_releves_2026_11_19.py — confronte aux relevés en ligne les prix ESTIMÉS des entrées
ajoutées le 2026-11-19 (lots n15-n17, légumineuses), et corrige les conserves.

Conserves : fix_legume_prices_2026_11_19.py comptait chaque boîte à 240-265 g égouttés
pour 1,20-1,60 €. Les relevés montrent que ces prix sont ceux de la boîte 4/4 française
(530 g égouttés) : le prix au kilo égoutté était doublé (pois chiches 5,00 au lieu de
2,25 €/kg). Les paquets sont remplacés par le format relevé.

Relevés : prix affichés par carrefour.fr dans les résultats de recherche le 2026-11-19
(les fiches produit refusent la lecture automatique ; le prix dépend du magasin et du
mode de retrait), sauf mention contraire dans « source ».

Restent des ESTIMATIONS faute de relevé : oseille, fèves fraîches. Artichaut : seulement
des fourchettes (gros, vente en ligne). Niébé en conserve : prix des haricots rouges en
conserve, par analogie.

Idempotent.

Usage :
    python scripts/ingredients/prices_releves_2026_11_19.py --dry-run
    python scripts/ingredients/prices_releves_2026_11_19.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
TODAY = "2026-11-19"
CARREFOUR = "relevé carrefour.fr 2026-11-19"


def pkg(qty, unit, price, label, note=None):
    p = {"qty": qty, "unit": unit, "price": price, "label": label}
    if note:
        p["note"] = note
    return p


# clé → (paquets, source du prix)
PACKAGES: dict[str, tuple[list[dict], str]] = {
    # ── Conserves, au poids égoutté ─────────────────────────────────────────────────────
    "chickpea": ([pkg(530, "g", 1.19, "boîte 4/4", "530 g égouttés")],
                 f"{CARREFOUR} (Carrefour Classic')"),
    "white_bean": ([pkg(530, "g", 1.15, "boîte 4/4", "530 g égouttés")],
                   f"{CARREFOUR} (Carrefour Classic')"),
    "kidney_beans": ([pkg(500, "g", 1.45, "boîte 4/4", "500 g égouttés")],
                     f"{CARREFOUR} (Carrefour Classic')"),
    "green_lentil_cooked": ([pkg(265, "g", 0.69, "boîte 1/2", "265 g égouttés")],
                            f"{CARREFOUR} (Carrefour Classic')"),
    "black_eyed_peas_canned": ([pkg(500, "g", 1.45, "boîte 4/4", "500 g égouttés")],
                               "analogie : haricots rouges en conserve (aucun relevé de niébé)"),
    # ── Secs ────────────────────────────────────────────────────────────────────────────
    "chickpea_dry": ([pkg(500, "g", 1.79, "sachet 500g")], f"{CARREFOUR} (Carrefour Le Marché)"),
    "white_bean_dry": ([pkg(500, "g", 2.39, "sachet 500g")], f"{CARREFOUR} (Carrefour Le Marché)"),
    "kidney_beans_dry": ([pkg(500, "g", 2.69, "sachet 500g")], f"{CARREFOUR} (Carrefour Le Marché)"),
    "fava_bean_dry": ([pkg(1000, "g", 4.27, "sachet 1kg")],
                      "relevé épicerie orientale en ligne 2026-11-19 (4,00 à 4,27 €/kg)"),
    "black_rice": ([pkg(500, "g", 3.99, "boîte 500g")], f"{CARREFOUR} (Carrefour Sélection)"),
    # ── Frais ───────────────────────────────────────────────────────────────────────────
    "brussels_sprouts": ([pkg(500, "g", 1.89, "sachet 500g")],
                         f"{CARREFOUR} (origine France ; 2,69 à 2,99 € hors France)"),
    "new_potato": ([pkg(1000, "g", 3.29, "sachet 1kg")],
                   f"{CARREFOUR} (grenaille ; Leclerc 1,99 €, primeur de Noirmoutier 5,98 €/kg)"),
    "artichoke": ([pkg(1, "piece", 2.00, "pièce ~350g")],
                  "fourchette 2026 : gros Rungis 1,50-3 €, vente en ligne 1,68-2,50 € la pièce"),
}

# sans relevé : marquées comme estimations
ESTIMATES: dict[str, str] = {
    "sorrel": "estimation (aucun relevé trouvé)",
    "fresh_fava_bean": "estimation (aucun relevé trouvé ; ~4,50 €/kg en cosses)",
}


def apply(catalog: dict) -> list[str]:
    log = []
    for key, (packages, source) in PACKAGES.items():
        entry = catalog[key]
        if entry.get("packages") != packages or entry.get("price_source") != source:
            old = [(p["qty"], p["price"], p["label"]) for p in entry.get("packages", [])]
            entry["packages"] = [dict(p) for p in packages]
            entry["price_source"] = source
            entry["last_updated"] = TODAY
            log.append(f"{key}: {old} → {[(p['qty'], p['price'], p['label']) for p in packages]}")
    for key, source in ESTIMATES.items():
        if catalog[key].get("price_source") != source:
            catalog[key]["price_source"] = source
            log.append(f"{key}: {source}")
    return log


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    log = apply(catalog)
    for line in log:
        print(line)
    print(f"{len(log)} changement(s)")
    if args.dry_run or not log:
        return
    end = "\n" if CATALOG_PATH.read_bytes().endswith(b"\n") else ""
    with CATALOG_PATH.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(catalog, ensure_ascii=False, indent=2) + end)


if __name__ == "__main__":
    main()
