#!/usr/bin/env python3
"""
fix_prices_2026_11_19.py — confronte aux prix réels les entrées du catalogue
qui pèsent le plus dans le coût des recettes.

Les 70 premières entrées de prices_catalog.json font 72 % du coût cumulé des
894 plats. Les prix nettement décalés ont été vérifiés le 2026-11-19 sur des
relevés publics (sources en commentaire) ; les autres sont restés tels quels.

Shiitakés séchés : ils partageaient l'entrée des frais, chiffrée au prix du
gramme le moins cher, donc celui du frais (≈ 23 €/kg) alors que le séché vaut
90 à 195 €/kg (10 g de séché ≈ 100 g de frais). Ils ont désormais leur entrée.

Idempotent.

Usage :
    python scripts/fix_prices_2026_11_19.py --dry-run
    python scripts/fix_prices_2026_11_19.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
FLAVOR_PATH = ROOT / "backend/data/graphs/flavor_graph.json"
CARBON_PATH = ROOT / "backend/data/config/carbon_footprint.json"
MAP_PATH = ROOT / "backend/data/config/ingredient_price_map.json"
TODAY = "2026-11-19"

# clé → {libellé du paquet: nouveau prix}
PRICE_FIXES: dict[str, dict[str, float]] = {
    # baguette classique : 1,09 € en boulangerie, 0,45 € en grande surface
    # (enquête mars 2026) ; INSEE 4,12 €/kg en octobre 2026. Était 2,19 €.
    "bread": {"baguette": 1.10},
    # lait UHT demi-écrémé : 0,80 à 1,30 €/L (relevés 2026). Était 1,75 €.
    "milk": {"brique 1L": 1.05},
    # chou-fleur : ≈ 1,90 € la pièce en grande surface, gros 1,56 €/kg (nov. 2026)
    "cauliflower": {"pièce ~900g": 2.20},
    # aubergine : gros 2 à 4 €/kg (moyenne 12 mois 2,63 €) → ≈ 4 €/kg au détail
    "eggplant": {"pièce ~400g": 1.60, "2 aubergines": 3.00},
    # haricots blancs 400 g : 0,80 à 1,55 € (Carrefour), 2,49 € en bio
    "white_bean": {"boîte 400g": 1.20},
    # ricotta Galbani 250 g : 2,95 € (Monoprix)
    "ricotta": {"pot 250g": 2.80},
    # banane plantain : 1,99 €/kg (verte) à 2,99 €/kg (mûre) → pièce de 250 g
    "plantain": {"pièce": 0.70},
    # cacahuètes grillées sans sel 200 g : 0,75 € (Netto) à 1,05 € (Leclerc)
    "peanut": {"sachet 200g": 1.10},
    # maïs doux 285 g : 0,46 à 0,85 € (Carrefour, U)
    "corn": {"boîte 280g": 0.85},
    # œufs plein air x12 : 3,79 € (Carrefour), 3,89 € (C'est qui le Patron)
    "egg": {"boîte 6 œufs": 2.10, "boîte 12 œufs": 3.80},
    # épinards frais 400 g : 2,79 € (Carrefour)
    "spinach": {"sachet 200g": 1.95, "sachet 400g": 2.79},
    # tofu nature 400 g : ≈ 2 à 3 € (Naturalia 2,99 € en bio)
    "tofu": {"bloc 400g": 2.90},
    # shiitaké frais : 15 €/kg (bio, colis 1 kg), gros 10,86 €/kg → barquette
    "shiitake_mushroom": {"barquette 100g": 2.30},
}

# paquets retirés d'une entrée (clé → libellés)
REMOVE_PACKAGES: dict[str, set[str]] = {
    "shiitake_mushroom": {"séchés 40g"},     # ont désormais leur propre entrée
}

NEW_ENTRIES: dict[str, dict] = {
    # shiitakés séchés 50 g : 4,50 € (origine Chine) à 9,75 € (France, bio)
    "shiitake_dried": {"name_fr": "Shiitakés séchés",
                       "packages": [{"qty": 50, "unit": "g", "price": 5.50,
                                     "label": "sachet 50g"}]},
}

MAP_FIXES: dict[str, str] = {
    "shiitake_mushroom_dried": "shiitake_dried",
}

# nouvelle clé → (source saveur, source carbone) : sans profil, la saveur et
# le carbone, qui passent aussi par resolve_catalog_key, perdraient l'ingrédient
DERIVED_PROFILES: dict[str, tuple[str, str]] = {
    "shiitake_dried": ("shiitake_mushroom", "shiitake_mushroom"),
}


def apply_catalog(catalog: dict) -> list[str]:
    log = []
    for key, entry in NEW_ENTRIES.items():
        if key not in catalog:
            catalog[key] = {"name_fr": entry["name_fr"], "pantry": True,
                            "packages": [dict(p) for p in entry["packages"]],
                            "last_updated": TODAY}
            log.append(f"+ {key}")
    for key, labels in REMOVE_PACKAGES.items():
        pkgs = catalog[key]["packages"]
        kept = [p for p in pkgs if p.get("label") not in labels]
        if len(kept) != len(pkgs):
            catalog[key]["packages"] = kept
            catalog[key]["last_updated"] = TODAY
            log.append(f"- {key}: paquet(s) {sorted(labels)}")
    for key, fixes in PRICE_FIXES.items():
        by_label = {p.get("label"): p for p in catalog[key]["packages"]}
        for label, price in fixes.items():
            p = by_label[label]
            if p["price"] != price:
                log.append(f"~ {key} {label}: {p['price']} → {price}")
                p["price"] = price
                catalog[key]["last_updated"] = TODAY
    return log


def apply_map(price_map: dict, catalog: dict) -> list[str]:
    log = []
    for rid, key in MAP_FIXES.items():
        if key not in catalog:
            raise SystemExit(f"clé de catalogue inconnue pour {rid} : {key}")
        if price_map.get(rid) != key:
            log.append(f"{rid}: {price_map.get(rid)} → {key}")
            price_map[rid] = key
    return log


def apply_profiles(flavor: dict, carbon: dict) -> list[str]:
    log = []
    for key, (f_src, c_src) in DERIVED_PROFILES.items():
        if key not in flavor:
            flavor[key] = list(flavor[f_src])
            log.append(f"saveur {key} ← {f_src}")
        if key not in carbon:
            carbon[key] = carbon[c_src]
            log.append(f"carbone {key} ← {c_src}")
    return log


def _write(path: Path, data: dict) -> None:
    # garde la fin de fichier d'origine (flavor_graph et carbon_footprint n'ont pas de saut final)
    end = "\n" if path.read_bytes().endswith(b"\n") else ""
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + end)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    price_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    flavor = json.loads(FLAVOR_PATH.read_text(encoding="utf-8"))
    carbon = json.loads(CARBON_PATH.read_text(encoding="utf-8"))
    log_c = apply_catalog(catalog)
    log_m = apply_map(price_map, catalog)
    log_p = apply_profiles(flavor, carbon)
    for line in log_c + log_m + log_p:
        print(line)
    print(f"{len(log_c)} changement(s) au catalogue, {len(log_m)} lien(s), {len(log_p)} profil(s)")
    if args.dry_run:
        print("[dry-run] rien n'est écrit")
        return
    if log_c:
        _write(CATALOG_PATH, catalog)
    if log_m:
        _write(MAP_PATH, price_map)
    if log_p:
        _write(FLAVOR_PATH, flavor)
        _write(CARBON_PATH, carbon)


if __name__ == "__main__":
    main()
