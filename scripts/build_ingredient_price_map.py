#!/usr/bin/env python3
"""
build_ingredient_price_map.py — Construit la correspondance entre les IDs
d'ingredients utilises dans recipes.json (ex. "garlic_raw",
"olive_oil_extra_virgin_plant") et les cles de prices_catalog.json (ex.
"garlic", "olive_oil").

Probleme : shopping.py fait `catalog.get(ing_key)` directement sur l'id de
composition de la recette. Comme les deux vocabulaires ont evolue
separement, ~90% des ingredients de recettes ne correspondent a aucune cle
du catalogue -> prix inconnu pour la plupart des articles d'une liste de
courses.

Strategie : pour chaque id d'ingredient de recette, on retire les mots
qualificatifs (etat, cuisson, conditionnement...) pour ne garder que les
mots significatifs ("coeur" de l'ingredient), puis on cherche la cle du
catalogue dont TOUS les mots sont contenus dans ce coeur (containment, pas
un simple mot en commun — evite les faux positifs du type "aubergines
parmigiana" / "aubergines sichuan" deja rencontres sur un probleme voisin).

Niveaux de confiance (repris du style de generate_alias_proposals.py) :
  AUTO_HIGH : tous les mots de la cle catalogue sont dans l'id recette
              (containment = 100%) -> seul niveau mappe automatiquement
  AUTO_MED  : au moins la moitie des mots de la cle catalogue presents,
              mais pas tous -> PAS applique automatiquement (experience
              faite : un score de 0.5 sur une cle a 2 mots matche presque
              toujours sur un simple adjectif partage — "green_peas_raw"
              matchait "green_lentil" juste sur "green", "cherry_raw"
              matchait "cherry_tomato" juste sur "cherry"... — meme piege
              que celui deja rencontre sur la detection de doublons de
              recettes). Liste pour relecture manuelle uniquement.
  NO_MATCH  : rien de convaincant -> laisse sans prix, liste pour revue
              manuelle / ajout au catalogue

Usage :
    python scripts/build_ingredient_price_map.py

Sorties :
    backend/data/config/ingredient_price_map.json   (utilise par shopping.py)
    scripts/ingredient_price_map_review.md           (a relire manuellement)
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECIPES_PATH = ROOT / "backend/data/recipes/recipes.json"
CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
OUT_MAP = ROOT / "backend/data/config/ingredient_price_map.json"
OUT_REVIEW = ROOT / "scripts/ingredient_price_map_review.md"

# Mots qualificatifs a ignorer : etat, cuisson, traitement, conditionnement...
# Ils decrivent une VARIANTE de l'ingredient, pas son identite.
STOPWORDS = {
    "raw", "dried", "fresh", "plant", "extra", "virgin", "unenriched",
    "unbleached", "ground", "powder", "chopped", "sliced", "canned",
    "cooked", "boiled", "unsalted", "salted", "grated", "liquid", "uht",
    "with", "without", "skin", "flesh", "ripe", "pre", "packaged", "plain",
    "reduced", "sodium", "all", "purpose", "cow", "leaf", "leaves", "seed",
    "seeds", "spice", "herb", "root", "whole", "cut", "peeled", "unpeeled",
    "frozen", "canned", "jarred", "bottled", "pure", "pasteurized",
    "unpasteurized", "organic", "large", "small", "medium", "type", "style",
    "natural", "processed", "refined", "unrefined", "crushed", "minced",
    "diced", "shredded", "whole", "brown", "light", "dark", "young", "old",
    "mature", "baby", "wild", "cultivated", "commercial", "homemade",
    "prepackaged", "regular", "low", "high", "fat", "free", "enriched",
}
# tokens numeriques/pourcentages a retirer via regex (ex. "3", "5pct", "80pct")
NUMERIC_TOKEN = re.compile(r"\d")


def _core_words(ingredient_id: str) -> set[str]:
    tokens = ingredient_id.lower().split("_")
    return {
        t for t in tokens
        if t and t not in STOPWORDS and not NUMERIC_TOKEN.search(t) and len(t) >= 2
    }


def _catalog_words(key: str) -> set[str]:
    return {t for t in key.lower().split("_") if t}


def load_recipe_ingredients() -> Counter:
    data = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))
    counts: Counter = Counter()
    for r in data["recipes"]:
        for c in r.get("composition", []):
            ing = c.get("ingredient")
            if ing:
                counts[ing.lower().strip()] += 1
    return counts


def build_mapping(recipe_ids: list[str], catalog_keys: list[str]):
    catalog_word_sets = {k: _catalog_words(k) for k in catalog_keys}

    mapping: dict[str, dict] = {}
    no_match: list[str] = []

    for rid in recipe_ids:
        core = _core_words(rid)
        if not core:
            no_match.append(rid)
            continue

        best_key = None
        best_score = 0.0
        best_size = 0
        for key, cwords in catalog_word_sets.items():
            if not cwords:
                continue
            inter = cwords & core
            score = len(inter) / len(cwords)
            # a score egal, prefere la cle catalogue la plus specifique
            # (le plus de mots -> match le plus riche en information)
            if score > best_score or (score == best_score and len(cwords) > best_size):
                best_key, best_score, best_size = key, score, len(cwords)

        if best_key is None or best_score < 0.5:
            no_match.append(rid)
            continue

        confidence = "AUTO_HIGH" if best_score >= 0.999 else "AUTO_MED"
        mapping[rid] = {"catalog_key": best_key, "confidence": confidence, "score": round(best_score, 2)}

    return mapping, no_match


def main():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog_keys = list(catalog.keys())

    counts = load_recipe_ingredients()
    recipe_ids = sorted(counts.keys())

    # Ne remappe pas ce qui matche deja directement (deja au bon format)
    already_ok = [rid for rid in recipe_ids if rid in catalog]
    to_map = [rid for rid in recipe_ids if rid not in catalog]

    mapping, no_match = build_mapping(to_map, catalog_keys)

    n_high = sum(1 for v in mapping.values() if v["confidence"] == "AUTO_HIGH")
    n_med = sum(1 for v in mapping.values() if v["confidence"] == "AUTO_MED")

    # Seul AUTO_HIGH est applique automatiquement (containment 100%, fiable).
    # AUTO_MED reste dans le rapport de relecture mais pas dans la carte.
    out = {
        rid: v["catalog_key"] for rid, v in mapping.items()
        if v["confidence"] == "AUTO_HIGH"
    }
    OUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    OUT_MAP.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ── Rapport de relecture ────────────────────────────────────────────
    lines = [
        "# Correspondance ingredients recettes -> catalogue de prix",
        "",
        f"- {len(recipe_ids)} ingredients uniques utilises dans les recettes",
        f"- {len(already_ok)} deja presents tels quels dans prices_catalog.json",
        f"- {n_high} mappes automatiquement (AUTO_HIGH, containment 100%) -> ecrits dans ingredient_price_map.json",
        f"- {n_med} candidats a confiance moyenne (AUTO_MED) — PAS appliques automatiquement, a valider ou rejeter a la main",
        f"- {len(no_match)} sans correspondance trouvee — prix restera inconnu",
        "",
        "## AUTO_MED — NON applique, a valider a la main (tri par frequence d'usage)",
        "",
        "Score 0.5 = un seul mot sur deux de la cle catalogue est present cote "
        "recette. Souvent ce mot est un simple adjectif partage (\"green\", "
        "\"red\", \"cherry\"...) qui ne garantit pas que ce soit le meme "
        "ingredient — a verifier un par un avant d'ajouter au mapping.",
        "",
    ]
    med_sorted = sorted(
        ((rid, v) for rid, v in mapping.items() if v["confidence"] == "AUTO_MED"),
        key=lambda x: -counts[x[0]],
    )
    for rid, v in med_sorted:
        lines.append(f"- `{rid}` ({counts[rid]}x) -> `{v['catalog_key']}` (score {v['score']})")

    lines += ["", "## Sans correspondance — tri par frequence d'usage (top 100)", ""]
    no_match_sorted = sorted(no_match, key=lambda x: -counts[x])
    for rid in no_match_sorted[:100]:
        lines.append(f"- `{rid}` ({counts[rid]}x)")
    if len(no_match_sorted) > 100:
        lines.append(f"- ... et {len(no_match_sorted) - 100} autres (frequence plus faible)")

    OUT_REVIEW.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"{len(recipe_ids)} ingredients recette au total")
    print(f"  deja OK (cle directe)  : {len(already_ok)}")
    print(f"  mappes AUTO_HIGH       : {n_high}")
    print(f"  mappes AUTO_MED        : {n_med}")
    print(f"  sans correspondance    : {len(no_match)}")
    print(f"-> {OUT_MAP}")
    print(f"-> {OUT_REVIEW}")


if __name__ == "__main__":
    main()
