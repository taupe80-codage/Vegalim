#!/usr/bin/env python3
"""
build_base_recipe_aliases.py
============================
Auto-connexion des recettes base_* vers base_recipe_aliases dans nutrition_aliases_v6.json.

Logique :
  Pour chaque recette dont l'id commence par "base_", déduit la clé canonique :
    base_pizza_dough_6fdabd  →  pizza_dough
    base_vegetable_broth_303b7d  →  vegetable_broth
  Si cette clé est absente de base_recipe_aliases, l'entrée est ajoutée.
  Les entrées existantes ne sont jamais écrasées (les alias manuels ont priorité).

Usage :
  python scripts/nutrition/build_base_recipe_aliases.py
  python scripts/nutrition/build_base_recipe_aliases.py --dry-run
  python scripts/nutrition/build_base_recipe_aliases.py --force   # écrase les existants
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
RECIPES_FILE  = ROOT / "backend" / "data" / "recipes" / "recipes.json"
ALIASES_FILE  = ROOT / "backend" / "data" / "nutrition" / "reference" / "nutrition_aliases_v6.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
HASH_SUFFIX = re.compile(r'_[0-9a-f]{6,8}$')


def extract_canonical_key(recipe_id: str) -> str:
    """
    'base_pizza_dough_6fdabd'  →  'pizza_dough'
    'base_vegetable_broth_303b7d'  →  'vegetable_broth'
    """
    without_prefix = recipe_id[5:]          # retire 'base_'
    return HASH_SUFFIX.sub('', without_prefix)  # retire le hash final


def load_recipes() -> list:
    with open(RECIPES_FILE, encoding='utf-8') as f:
        raw = json.load(f)
    return raw.get('recipes', raw) if isinstance(raw, dict) else raw


def load_aliases() -> dict:
    with open(ALIASES_FILE, encoding='utf-8') as f:
        return json.load(f)


def save_aliases(data: dict) -> None:
    with open(ALIASES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Logique principale
# ---------------------------------------------------------------------------
def run(dry_run: bool = False, force: bool = False) -> None:
    recipes = load_recipes()
    aliases = load_aliases()

    bra: dict = aliases.setdefault('base_recipe_aliases', {})

    # Collecter toutes les recettes base_*
    base_recipes = [
        r for r in recipes
        if isinstance(r, dict) and r.get('id', '').startswith('base_')
    ]

    added: list[tuple[str, str]] = []
    overridden: list[tuple[str, str, str]] = []
    skipped: list[tuple[str, str]] = []

    for recipe in sorted(base_recipes, key=lambda r: r['id']):
        rid = recipe['id']
        key = extract_canonical_key(rid)

        existing = bra.get(key)
        if existing is None:
            added.append((key, rid))
            if not dry_run:
                bra[key] = rid
        elif existing != rid:
            if force:
                overridden.append((key, existing, rid))
                if not dry_run:
                    bra[key] = rid
            else:
                skipped.append((key, existing))
        # Si existing == rid → déjà correct, rien à faire

    # Trier les clés du BRA pour la lisibilité du fichier
    aliases['base_recipe_aliases'] = dict(sorted(bra.items()))

    # ---------- Rapport ----------
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}build_base_recipe_aliases — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"  Recettes base_*       : {len(base_recipes)}")
    print(f"  Ajouts                : {len(added)}")
    print(f"  Écrasements (--force) : {len(overridden)}")
    print(f"  Ignorés (déjà présents, différents) : {len(skipped)}")

    if added:
        print("\n  ✚ Ajoutés :")
        for k, v in added:
            print(f"      {k:<45} → {v}")

    if overridden:
        print("\n  ✏  Écrasés :")
        for k, old, new in overridden:
            print(f"      {k:<45} {old!r} → {new!r}")

    if skipped:
        print("\n  ⚠  Ignorés (alias manuel existant) :")
        for k, existing in skipped:
            print(f"      {k:<45} → {existing}  (conserver)")

    if dry_run:
        print("\n  [DRY-RUN] Aucune écriture.")
        return

    if not added and not overridden:
        print("\n  Rien à mettre à jour.")
        return

    save_aliases(aliases)
    print(f"\n  OK — {ALIASES_FILE.name} mis à jour ({len(aliases['base_recipe_aliases'])} entrées BRA).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true', help="Affiche sans écrire")
    ap.add_argument('--force',   action='store_true', help="Écrase les entrées existantes divergentes")
    args = ap.parse_args()

    if args.force and args.dry_run:
        print("--force et --dry-run sont incompatibles.", file=sys.stderr)
        sys.exit(1)

    run(dry_run=args.dry_run, force=args.force)
