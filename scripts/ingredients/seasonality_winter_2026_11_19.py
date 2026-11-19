#!/usr/bin/env python3
"""
seasonality_winter_2026_11_19.py — ajoute au calendrier de saisonnalité
(data/modules/seasonality.json) les fruits et légumes d'automne et d'hiver qui
en étaient absents.

Constat (lots n15/n16) : poireau, panais, céleri-rave, endive, chou de
Bruxelles, topinambour, poire, pomme, châtaigne, mâche et kiwi n'y figuraient
pas. Les recettes qui en contiennent passaient pour « sans ingrédient
saisonnier » : elles n'apparaissaient jamais comme de saison en hiver, et
l'analyse d'équilibre comptait 38 à 43 plats d'hiver seulement.

Mois : calendrier des fruits et légumes de saison en France métropolitaine
(production locale de plein champ ou de conservation). Les entrées existantes
ne sont pas modifiées. Les ids de recettes sont reliés à ces clés par
SEASON_ID_ALIASES (backend/engine/rule_engine/seasonality.py).

Idempotent.

Usage :
    python scripts/ingredients/seasonality_winter_2026_11_19.py --dry-run
    python scripts/ingredients/seasonality_winter_2026_11_19.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "backend/data/modules/seasonality.json"

NEW_ENTRIES: dict[str, list[int]] = {
    "leek":                [1, 2, 3, 4, 9, 10, 11, 12],
    "parsnip":             [1, 2, 3, 10, 11, 12],
    "celeriac":            [1, 2, 3, 10, 11, 12],
    "endive":              [1, 2, 3, 4, 10, 11, 12],
    "brussels_sprouts":    [1, 2, 3, 10, 11, 12],
    "jerusalem_artichoke": [1, 2, 3, 10, 11, 12],
    "pear":                [1, 8, 9, 10, 11, 12],
    "apple":               [1, 2, 3, 4, 8, 9, 10, 11, 12],
    "chestnut":            [10, 11, 12],
    "lambs_lettuce":       [1, 2, 3, 10, 11, 12],
    "kiwi":                [1, 2, 3, 4, 11, 12],
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
    added = []
    for key, months in NEW_ENTRIES.items():
        if key not in data:
            data[key] = {"months": months, "seasons": seasons_of(months)}
            added.append(key)
    print(f"{len(added)} entrée(s) ajoutée(s) : {added}")
    if args.dry_run or not added:
        return
    end = "\n" if PATH.read_bytes().endswith(b"\n") else ""
    with PATH.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + end)


if __name__ == "__main__":
    main()
