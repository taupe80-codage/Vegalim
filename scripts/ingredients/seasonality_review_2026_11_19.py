#!/usr/bin/env python3
"""
seasonality_review_2026_11_19.py — relecture du calendrier de saisonnalité
(data/modules/seasonality.json), après l'ajout des produits d'hiver
(seasonality_winter_2026_11_19.py).

Mois : calendrier des fruits et légumes de saison en France métropolitaine
(production locale de plein champ ou de conservation ; agrumes : saison
d'importation méditerranéenne). Les liens ids de recettes → clés sont dans
SEASON_ID_ALIASES (backend/engine/rule_engine/seasonality.py).

1. NEW_ENTRIES : fruits et légumes des recettes absents du calendrier
   (fraise, petits pois, fèves fraîches, rhubarbe, cerise, fruits rouges,
   figue, raisin, melon, pastèque, cresson, chou chinois, roquette,
   tomatillo, radis noir).
2. MONTHS_FIX : entrées existantes fausses —
   - « toute l'année » pour des légumes à saison nette (brocoli, blette,
     chicorée frisée/scarole, orange, pissenlit) ;
   - haricot vert dès mars, épinard absent l'hiver, chou-fleur et navet
     réduits à décembre-février, courges absentes après novembre alors
     qu'elles se conservent jusqu'en février, daikon de printemps.

Restent volontairement neutres (absents ou 12 mois sur 12) : produits
importés sans saison française (banane, avocat, mangue, ananas, citron
vert, citronnelle, gombo, pousse de bambou), légumes de garde (pomme de
terre, oignon, échalote, ail, carotte), herbes aromatiques et piments frais
(quelques grammes dans 100 à 200 recettes : ils feraient basculer le ratio
sans dire grand-chose de la saison du plat), salade et céleri branche.

Idempotent.

Usage :
    python scripts/ingredients/seasonality_review_2026_11_19.py --dry-run
    python scripts/ingredients/seasonality_review_2026_11_19.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "backend/data/modules/seasonality.json"

NEW_ENTRIES: dict[str, list[int]] = {
    "strawberry":      [4, 5, 6, 7],
    "green_peas":      [5, 6, 7],
    "fresh_fava_bean": [4, 5, 6, 7],
    "rhubarb":         [4, 5, 6],
    "cherry":          [5, 6, 7],
    "raspberry":       [6, 7, 8, 9],
    "blueberry":       [7, 8, 9],
    "fig":             [8, 9, 10],
    "grape":           [8, 9, 10],
    "melon":           [6, 7, 8, 9],
    "watermelon":      [7, 8, 9],
    "watercress":      [1, 2, 3, 4, 5, 9, 10, 11, 12],
    "napa_cabbage":    [1, 2, 9, 10, 11, 12],
    "arugula":         [3, 4, 5, 6, 9, 10],
    "tomatillo":       [7, 8, 9],
    "black_radish":    [1, 2, 3, 10, 11, 12],
}

MONTHS_FIX: dict[str, list[int]] = {
    "broccoli":       [6, 7, 8, 9, 10, 11],            # était 12 mois
    "swiss_chard":    [5, 6, 7, 8, 9, 10, 11],         # était 12 mois
    "chicory":        [1, 2, 3, 9, 10, 11, 12],        # frisée, scarole ; était 12 mois
    "orange":         [1, 2, 3, 4, 11, 12],            # était 12 mois
    "green_bean":     [6, 7, 8, 9],                    # était mars-août
    "spinach":        [1, 2, 3, 4, 5, 9, 10, 11, 12],  # était mars-mai, sept-oct
    "cauliflower":    [1, 2, 3, 4, 9, 10, 11, 12],     # était déc-fév
    "turnip":         [1, 2, 3, 4, 5, 10, 11, 12],     # était déc-fév
    "squash":         [1, 2, 9, 10, 11, 12],           # était sept-nov
    "pumpkin":        [1, 2, 9, 10, 11, 12],           # était sept-nov
    "kabocha_squash": [1, 2, 9, 10, 11, 12],           # était sept-nov
    "daikon":         [1, 2, 3, 10, 11, 12],           # était mars-mai
    "radish":         [3, 4, 5, 6, 7, 8],              # radis rose ; était mars-mai
    "mushroom":       [8, 9, 10, 11],                  # cèpe, girolle (sauvages) ; était sept-nov
    "dandelion":      [3, 4, 5],                       # était 12 mois
}

_SEASONS = {"winter": {12, 1, 2}, "spring": {3, 4, 5}, "summer": {6, 7, 8}, "autumn": {9, 10, 11}}


def seasons_of(months: list[int]) -> list[str]:
    """Saisons dont au moins deux mois sont couverts."""
    return [s for s, ms in _SEASONS.items() if len(ms & set(months)) >= 2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = json.loads(PATH.read_text(encoding="utf-8"))
    changed = []
    for key, months in NEW_ENTRIES.items():
        if key not in data:
            data[key] = {"months": months, "seasons": seasons_of(months)}
            changed.append(f"+{key}")
    for key, months in MONTHS_FIX.items():
        entry = data.setdefault(key, {})
        if entry.get("months") != months:
            changed.append(f"{key} {entry.get('months')} -> {months}")
            entry["months"] = months
            entry["seasons"] = seasons_of(months)
    print(f"{len(changed)} changement(s) :", *changed, sep="\n  ")
    if args.dry_run or not changed:
        return
    end = "\n" if PATH.read_bytes().endswith(b"\n") else ""
    with PATH.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + end)


if __name__ == "__main__":
    main()
