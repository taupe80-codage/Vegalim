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


WARNINGS: list[str] = []


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
           "haricots", "lentilles", "pois", "chiches", "champignons", "aubergine", "aubergines",
           "mangue", "banane", "bananes", "avocat", "chocolat", "pomme", "poire", "gluant",
           "vapeur", "frais", "fraiche", "fraiches", "herbes", "tofu", "vermicelles", "nouilles",
           "citronnelle", "gingembre", "coriandre", "menthe", "basilic", "cacahuetes", "sesame",
           "tempeh", "seitan", "quinoa", "boulgour", "sarrasin", "polenta", "semoule",
           "spaghetti", "pates", "gnocchi", "risotto", "millet", "orge", "haricot", "blancs",
           "oeuf", "oeufs", "soupe", "salade", "porridge", "chaud", "chauds", "confites",
           "legumes",
           # mots qui veulent dire « plat » ou un ingrédient de base dans une autre langue
           "sopa", "caldo", "ensalada", "pasta", "pane", "arroz", "riz", "dal", "curry", "wat",
           "wot", "chorba", "shorba", "polo", "pilav", "pilaf",
           "aux", "des", "les", "sur", "lait", "eau", "mais", "paneer", "gallo", "tofu",
           "blanc", "blanche", "blancs", "vert", "verte", "verts", "rouge", "rouges", "noir",
           "noirs", "jaune", "maison", "chou", "carotte", "erable", "sirop", "sucre", "cidre",
           "matin", "jardin", "hiver", "ete", "printemps", "automne", "pain", "tarte", "gateau",
           "raisins", "raisin", "noix", "amandes", "grenade", "yaourt", "crème", "froide",
           "galettes", "galette", "quenelles", "fromage"}

# adjectifs de pays et de région : ils ne distinguent pas un plat d'un autre
GENTILES = {"francais", "francaise", "italien", "italienne", "italiennes", "espagnol", "espagnole",
            "grec", "grecque", "grecques", "turc", "turque", "libanais", "libanaise", "marocain",
            "marocaine", "tunisien", "tunisienne", "egyptien", "egyptienne", "ethiopien",
            "ethiopienne", "kenyane", "ghaneen", "senegalais", "nigerian", "mexicain", "mexicaine",
            "mexicaines", "peruvien", "peruvienne", "argentin", "argentine", "bresilien",
            "bresilienne", "indien", "indienne", "indiennes", "japonais", "japonaise", "chinois",
            "chinoise", "coreen", "coreenne", "coreennes", "thai", "thaie", "thailandais",
            "vietnamien", "vietnamienne", "indonesien", "indonesienne", "indonesiennes",
            "malaisien", "malaisienne", "philippin", "philippine", "polonais", "polonaise",
            "ukrainien", "ukrainienne", "allemand", "allemande", "anglais", "anglaise", "suisse",
            "portugais", "portugaise", "hongrois", "hongroise", "bulgare", "georgien", "georgienne",
            "persan", "persane", "iranien", "iranienne", "afghan", "afghane", "nepalais",
            "sri", "lankais", "provencal", "provencale", "nicois", "nicoise", "bretonnes",
            "castillane", "andalouse", "sicilienne", "napolitaine", "romaine", "milanais",
            "costaricien", "salvadorien", "canadien", "canadienne", "quebecois", "quebecoise", "americain",
            "americaine", "vegetariens", "vegetariennes", "vegane", "veganes"}


def _title_tokens(title: str) -> set[str]:
    import re, unicodedata
    t = unicodedata.normalize("NFKD", title.lower().replace("œ", "oe")).encode("ascii", "ignore").decode()
    return {w for w in re.split(r"[^a-z]+", t)
            if len(w) >= 3 and w not in GENERIC and w not in GENTILES}


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
        allowed = set(r.get("_allow_similar") or ())
        for tok in sorted(_title_tokens(r["titles"]["fr"].split(",")[0]) - allowed):
            hits = index.get(tok, [])
            if not hits:
                continue
            # un mot long et unique dans tout le dataset = presque sûrement le même plat
            if len(tok) >= 5 and len(hits) == 1:
                raise RecipeError(f"{r['id']} « {r['titles']['fr']} » : le mot « {tok} » figure déjà "
                                  f"dans {hits} — plat probablement déjà présent "
                                  f"(allow_similar=(\"{tok}\",) si c'est un faux positif)")
            WARNINGS.append(f"{r['id']} « {r['titles']['fr']} » : « {tok} » aussi dans {hits[:3]}")
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
        recipes.append({k: v for k, v in r.items() if not k.startswith("_")})
    if WARNINGS:
        print(f"{len(WARNINGS)} rapprochement(s) de titre à vérifier :")
        for w in WARNINGS:
            print("  ?", w)
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
