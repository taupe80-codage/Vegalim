#!/usr/bin/env python3
"""fix_textures_origins_2026_11_21.py — arbitrage de l'audit de cohérence (texture_absente,
pays_absent), resté sans décision depuis le 2026-09-25.

1. result.texture : 20 recettes, presque toutes des préparations de base (pâtes de curry,
   bouillons, fromages végétaux), sans texture. Valeurs prises dans le vocabulaire déjà
   employé par le catalogue (« lisse », « nappant », « filant »…).
2. origin.country : 14 recettes sans pays. Pays réel quand le produit en a un (mayonnaise et
   bouillon → France, feuilles de riz → Vietnam, beurre de cacahuète → États-Unis, ricotta et
   mozzarella végétales → Italie, cheddar végétal → Royaume-Uni…), la cuisine suivant le pays ;
   « international » pour ce qui n'a pas d'origine réelle (crackers à l'huile d'olive, sauce
   brune au miso et aux shiitakés, oignon frit), convention de 30 recettes du catalogue.

Idempotent. Relancer ensuite rebuild_graphs.py, build_index.py, extract_recipe_list.py.

Usage :
    python scripts/recipes/fix_textures_origins_2026_11_21.py [--dry-run]
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

TEXTURES: dict[str, list[str]] = {
    "base_green_curry_paste_250117": ["lisse", "homogene"],
    "red_curry_paste_3ee8f5": ["lisse", "homogene"],
    "yellow_curry_paste_077f54": ["lisse", "homogene"],
    "chili_paste_95cb92": ["lisse", "legerement_huilee"],
    "tamarind_paste_b740bb": ["lisse", "épais"],
    "base_japanese_curry_roux_385e52": ["ferme", "lisse"],
    "base_vegetable_broth_303b7d": ["liquide", "bouillon_riche"],
    "base_dashi_broth_a3a517": ["liquide", "leger"],
    "miso_broth_618f1e": ["liquide", "leger"],
    "entry_tzatziki_grec_2b21fb": ["cremeux", "frais"],
    "salted_butter_caramel_096c73": ["nappant", "sirupeux"],
    "samosa_dough_c03717": ["ferme", "souple"],
    "vegetarian_brown_sauce_4233df": ["nappant", "sauce_liee"],
    "base_bechamel_vegane_7a210c": ["nappant", "onctueux"],
    "base_buckwheat_crepe_03db22": ["souple", "fin"],
    "base_cashew_ricotta_5c62e9": ["cremeux", "grenu"],
    "base_paneer_04e1db": ["ferme", "tient_la_coupe"],
    "base_vegan_cheddar_024998": ["cremeux", "filant"],
    "base_vegan_mayonnaise_b68322": ["onctueux", "lisse"],
    "base_fried_onion_217e6a": ["croustillant", "dore"],
}

# id : (cuisine, pays) — cuisine None = inchangée
ORIGINS: dict[str, tuple[str | None, str]] = {
    "base_vegetable_broth_303b7d": ("french", "france"),
    "base_vegan_mayonnaise_b68322": ("french", "france"),
    "base_spring_roll_wrappers_eba962": ("vietnamese", "vietnam"),
    "base_peanut_butter_81c37b": ("american", "united_states"),
    "base_mozzarella_vegane_fca8c8": ("italian", "italy"),
    "base_cashew_ricotta_5c62e9": ("italian", "italy"),
    "base_vegan_cheddar_024998": ("british", "united_kingdom"),
    "base_cheddar_vegane_529b97": ("british", "united_kingdom"),
    "chili_paste_95cb92": ("chinese", "china"),            # piment, ail, gingembre, vinaigre
    "tamarind_paste_b740bb": ("thai", "thailand"),
    "salad_asiatique_sesame_948f03": ("japanese", "japan"),  # chou au sésame et au shoyu
    "snack_crackers_35f6a8": (None, "international"),
    "vegetarian_brown_sauce_4233df": ("international", "international"),
    "base_fried_onion_217e6a": (None, "international"),
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
    for rid, tex in TEXTURES.items():
        res = idx[rid].setdefault("result", {})
        if not res.get("texture"):
            res["texture"] = tex
            log.append(f"texture {rid} : {tex}")
    for rid, (cuisine, country) in ORIGINS.items():
        o = idx[rid].setdefault("origin", {})
        if not o.get("country"):
            o["country"] = country
            log.append(f"pays {rid} : {country}")
            if cuisine and o.get("cuisine") != cuisine:
                log.append(f"cuisine {rid} : {o.get('cuisine')} → {cuisine}")
                o["cuisine"] = cuisine
            if o.get("region") == "world":
                o["region"] = ""
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
