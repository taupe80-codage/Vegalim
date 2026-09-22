#!/usr/bin/env python3
"""add_new_recipes.py — ajoute les lots de nouvelles recettes (scripts/recipes/new_recipes/n*.py).

Chaque module expose RECIPES : liste de recettes construites par new_recipes._schema.recipe().
Idempotent : une recette dont l'id existe déjà est ignorée. Contrôles avant écriture :
identifiants uniques, champs obligatoires, ingrédients pourvus d'une fiche nutritionnelle,
titre non déjà utilisé.

Relancer ensuite le pipeline : fix_recipe_diet_allergens.py, build_derived_base_registry.py,
rebuild_graphs.py, build_index.py, puis extract_recipe_list.py.

Usage :
    python scripts/recipes/add_new_recipes.py --dry-run
    python scripts/recipes/add_new_recipes.py
"""
import argparse, importlib, json, logging, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
logging.disable(logging.WARNING)

from backend.engine.config import RECIPES_PATH

LOT_DIR = Path(__file__).parent / "new_recipes"
REQUIRED = ("id", "titles", "origin", "servings", "timing", "composition", "tags",
            "dish_type", "description", "instructions", "diet_flags")


class RecipeError(Exception):
    pass


def load_lots() -> list[dict]:
    out, seen = [], set()
    for f in sorted(LOT_DIR.glob("n*.py")):
        mod = importlib.import_module(f"new_recipes.{f.stem}")
        for r in mod.RECIPES:
            if r["id"] in seen:
                raise RecipeError(f"{r['id']} : défini dans deux lots")
            seen.add(r["id"])
            out.append(r)
    return out


def _has_nutrition(iid: str) -> bool:
    from backend.engine.nutrition_engine import get_data
    try:
        n = get_data.ingredients.resolve_nutrition(iid, use_cooked=False) or {}
    except Exception:
        return False
    return n.get("calories_kcal") is not None


GENERIC = {"riz", "sauce", "salade", "soupe", "legumes", "legume", "maison", "vegan", "vegetarien",
           "vegetarienne", "grille", "grillee", "grilles", "grillees", "roti", "rotie", "roties",
           "farci", "farcie", "gratin", "gratine", "gratinee", "puree", "creme", "cremeux", "express",
           "traditionnel", "traditionnelle", "classique", "poele", "poelee", "four", "beurre", "huile",
           "tomate", "tomates", "oignon", "oignons", "pommes", "terre", "epices", "epice", "epicee",
           "fromage", "citron", "coco", "curry", "sautee", "saute", "sautes", "sautees", "petits",
           "haricots", "lentilles", "pois", "chiches", "champignons", "aubergine", "aubergines"}


def _title_tokens(title: str) -> set[str]:
    import re, unicodedata
    t = unicodedata.normalize("NFKD", title.lower().replace("œ", "oe")).encode("ascii", "ignore").decode()
    return {w for w in re.split(r"[^a-z]+", t) if len(w) >= 4 and w not in GENERIC}


def check(new: list[dict], existing: list[dict]) -> None:
    have_ids = {r["id"] for r in existing}
    have_titles = {r["titles"]["fr"].strip().lower() for r in existing}
    sub_ids = have_ids | {r["id"] for r in new}
    # jeton distinctif -> titres existants qui le portent (un plat déjà présent sous un autre nom
    # est le piège principal : « Misir wot » vs « Ethiopian Misir Wot »)
    index: dict[str, list[str]] = {}
    for r in existing:
        for tok in (_title_tokens(r["titles"]["fr"].split(",")[0])
                    | _title_tokens((r["titles"].get("en") or "").split(",")[0])):
            index.setdefault(tok, []).append(r["titles"]["fr"])
    for r in new:
        missing = [k for k in REQUIRED if k not in r]
        if missing:
            raise RecipeError(f"{r['id']} : champs manquants {missing}")
        if r["id"] in have_ids:
            continue
        if r["titles"]["fr"].strip().lower() in have_titles:
            raise RecipeError(f"{r['id']} : titre déjà utilisé « {r['titles']['fr']} »")
        # seulement le nom du plat (avant la première virgule) : les ingrédients cités ensuite
        # sont partagés par beaucoup de recettes
        for tok in sorted(_title_tokens(r["titles"]["fr"].split(",")[0])):
            hits = index.get(tok, [])
            if hits and len(hits) <= 3:
                raise RecipeError(f"{r['id']} « {r['titles']['fr']} » : le mot « {tok} » figure déjà "
                                  f"dans {hits} — plat probablement déjà présent")
        for c in r["composition"]:
            iid = c["ingredient"]
            if iid in sub_ids:  # sous-recette (préparation de base)
                continue
            if not _has_nutrition(iid):
                raise RecipeError(f"{r['id']} : pas de fiche nutritionnelle pour {iid}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))
    recipes = raw["recipes"]
    new = load_lots()
    try:
        check(new, recipes)
    except RecipeError as e:
        print("ERREUR :", e)
        return 1

    have = {r["id"] for r in recipes}
    added = [r for r in new if r["id"] not in have]
    for r in added:
        recipes.append(r)
    print(f"{len(new)} recettes dans les lots, {len(added)} ajoutée(s)"
          + (" (dry-run)" if args.dry_run else ""))
    for r in added:
        print("  +", r["id"], "—", r["titles"]["fr"])
    if added and not args.dry_run:
        RECIPES_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2),
                                encoding="utf-8", newline="\n")
        print("écrit :", RECIPES_PATH, f"({len(recipes)} recettes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
