#!/usr/bin/env python3
"""fix_light_portions_2026_11_21.py — arbitrage de l'audit de cohérence (portion_legere) :
8 recettes servaient des portions trop petites (moins de 80 % du poids minimal servi de leur
type de plat, et moins de 300 kcal).

Décision (2026-11-21) : augmenter les portions. La recette reste la même (quantités et étapes
inchangées) et se partage en moins de parts, ce qui grossit chaque portion jusqu'au minimum de
l'audit (PORTION_MIN_G) ; le planning et la liste de courses recalculent les quantités à partir
de servings, donc un repas pour 4 achète bien deux fois la recette à 2 parts.

  cookies chocolat vegan  18 → 10 parts (≈ 2 cookies, 77 g)
  brigadeiros             10 → 7       (≈ 3 boules sur les 20 formées, 76 g)
  dan chao fan             4 → 3       (250 g)
  batata harra, jeera aloo, gamja jorim, pizza marinara  4 → 2  (300 à 360 g)
  salade de pousses de soja coréenne  4 → 2  (138 g)

Idempotent. Relancer ensuite rebuild_graphs.py (nutrition par portion), build_index.py,
extract_recipe_list.py.

Usage :
    python scripts/recipes/fix_light_portions_2026_11_21.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.engine.config import RECIPES_PATH  # noqa: E402

SERVINGS: dict[str, tuple[int, int]] = {     # id : (avant, après)
    "dessert_cookie_chocolat_vegan_b9c6cc": (18, 10),
    "dessert_brigadeiros_9d63a4": (10, 7),
    "main_fried_rice_a6e811": (4, 3),
    "main_batata_harra_c2de57": (4, 2),
    "main_jeera_aloo_f4c7a0": (4, 2),
    "main_pommes_de_terre_braisees_7a56a8": (4, 2),
    "tarte_pizza_margherita_vegan_02bb9a": (4, 2),
    "salad_de_pousses_de_soja_coreen_d07502": (4, 2),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = Path(RECIPES_PATH)
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    idx = {r["id"]: r for r in data["recipes"]}
    log: list[str] = []
    for rid, (before, after) in SERVINGS.items():
        r = idx[rid]
        if r.get("servings") == after and r.get("servings_default") == after:
            continue
        if r.get("servings") != before:
            raise SystemExit(f"{rid} : {r.get('servings')} parts, {before} attendues — vérifier à la main")
        r["servings"] = r["servings_default"] = after
        log.append(f"{rid} : {before} → {after} parts")
    print(*log, f"{len(log)} changement(s)", sep="\n")
    if args.dry_run or not log:
        return
    end = "\n" if raw.endswith("\n") else ""
    write_with_retry(path, json.dumps(data, ensure_ascii=False, indent=2) + end)


def write_with_retry(path: Path, text: str) -> None:
    """Windows : juste après une autre écriture, l'ouverture échoue parfois (OSError 22,
    fichier encore verrouillé par l'antivirus ou l'indexation) : on réessaie."""
    for attempt in range(5):
        try:
            with path.open("w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            return
        except OSError:
            if attempt == 4:
                raise
            time.sleep(1)


if __name__ == "__main__":
    main()
