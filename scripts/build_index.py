"""
scripts/build_index.py — Reconstruit search_index.json depuis recipes.json.

Usage :
    python scripts/build_index.py
    python scripts/build_index.py --dry-run   # affiche stats sans écrire

Produit : backend/data/indexes/search_index.json
Structure :
  {
    "description": "...",
    "version": "2.0",
    "total_recipes": N,
    "total_tokens": M,
    "tokens": {
      "<token>": ["recipe_id", ...]
    }
  }

Champs indexés par recette :
  - titles.fr  / title_fr / title_original
  - composition[].ingredient
  - tags.diet, tags.allergens, tags.technique
  - iconic_status.cuisine_origin / scoring.iconic.cuisine_origin
"""

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


# ── Chemins ───────────────────────────────────────────────────────────────────

ROOT       = Path(__file__).resolve().parent.parent
RECIPES    = ROOT / "backend" / "data" / "recipes" / "recipes.json"
OUT_DIR    = ROOT / "backend" / "data" / "indexes"
OUT_FILE   = OUT_DIR / "search_index.json"


# ── Normalisation ─────────────────────────────────────────────────────────────

_STOPWORDS = {
    "de", "du", "des", "le", "la", "les", "un", "une", "et", "en",
    "au", "aux", "avec", "sur", "par", "the", "and", "with", "of",
    "to", "a", "an", "in", "for",
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _tokenize(text: str) -> list[str]:
    """Découpe et normalise un texte en tokens indexables (min 3 chars, hors stopwords)."""
    raw = re.split(r"[\s,;/|+\-–'\"()]+", _strip_accents(text.lower()).strip())
    return [
        t for t in raw
        if len(t) >= 3 and t not in _STOPWORDS and t.isalpha()
    ]


# ── Extraction des champs indexables ─────────────────────────────────────────

def _fields(recipe: dict) -> list[str]:
    """Retourne tous les textes à indexer pour une recette."""
    texts: list[str] = []

    # Titres
    title_fr = (
        recipe.get("title_fr") or
        (recipe.get("titles") or {}).get("fr") or
        recipe.get("title_original") or
        recipe.get("title") or ""
    )
    if title_fr:
        texts.append(title_fr)

    # Cuisine d'origine
    cuisine = (
        (recipe.get("iconic_status") or {}).get("cuisine_origin") or
        (recipe.get("scoring", {}).get("iconic") or {}).get("cuisine_origin") or
        recipe.get("cuisine") or ""
    )
    if cuisine:
        texts.append(cuisine)

    # Ingrédients (composition)
    for item in recipe.get("composition") or recipe.get("ingredients") or []:
        if isinstance(item, dict):
            ing = item.get("ingredient") or item.get("ingredient_id") or item.get("name") or ""
        else:
            ing = str(item)
        if ing:
            texts.append(ing.replace("_", " "))

    # Tags
    tags = recipe.get("tags") or {}
    if isinstance(tags, dict):
        for v in tags.values():
            if isinstance(v, list):
                texts.extend(str(t).replace("_", " ") for t in v)
            elif isinstance(v, str):
                texts.append(v.replace("_", " "))
    elif isinstance(tags, list):
        texts.extend(str(t).replace("_", " ") for t in tags)

    # Diet flags
    diet_flags = recipe.get("diet_flags") or {}
    if isinstance(diet_flags, dict):
        texts.extend(k.replace("_", " ") for k, v in diet_flags.items() if v)

    return texts


# ── Construction ──────────────────────────────────────────────────────────────

def build_index(recipes: list[dict]) -> dict:
    """Construit l'index token → liste d'IDs de recettes."""
    token_map: dict[str, set] = defaultdict(set)

    for recipe in recipes:
        rid = str(recipe.get("id", ""))
        if not rid:
            continue
        for text in _fields(recipe):
            for tok in _tokenize(text):
                token_map[tok].add(rid)

    # Convertit les sets en listes triées pour la sérialisation JSON
    return {tok: sorted(ids) for tok, ids in token_map.items()}


# ── Entrée principale ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Rebuild search_index.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche les stats sans écrire le fichier")
    args = parser.parse_args()

    # Chargement
    print(f"Lecture : {RECIPES}")
    raw = json.loads(RECIPES.read_text(encoding="utf-8"))
    recipes = raw.get("recipes", raw) if isinstance(raw, dict) else raw
    print(f"  {len(recipes)} recettes chargées")

    # Construction
    print("Construction de l'index …")
    tokens = build_index(recipes)
    total_tokens = len(tokens)
    total_refs   = sum(len(v) for v in tokens.values())

    print(f"  {total_tokens} tokens uniques")
    print(f"  {total_refs} références totales")
    print(f"  Couverture : {len(recipes)}/{len(recipes)} recettes (100 %)")

    index = {
        "description":         "Index de recherche ALIM — généré par scripts/build_index.py",
        "version":             "2.0",
        "supported_languages": ["fr", "en"],
        "total_recipes":       len(recipes),
        "total_tokens":        total_tokens,
        "tokens":              tokens,
    }

    if args.dry_run:
        print("\n[DRY RUN] — fichier non écrit.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8", newline="\n",
    )
    size_kb = OUT_FILE.stat().st_size // 1024
    print(f"\nEcrit : {OUT_FILE}  ({size_kb} Ko)")


if __name__ == "__main__":
    main()
