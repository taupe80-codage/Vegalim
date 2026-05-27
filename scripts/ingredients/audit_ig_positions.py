#!/usr/bin/env python3
"""
scripts/ingredients/audit_ig_positions.py
==========================================
Vérifie la position des IGs dans le tree catégoriel.

4 vérifications :
  A. CORRESPONDANCE CROISÉE   — le nom de l'IG correspond mieux à une AUTRE sous-cat ?
  B. FORM ↔ CATÉGORIE         — form=oil/butter/juice/flour dans la bonne cat ?
  C. FORM VALEUR INVALIDE     — texture/taille mal encodée dans l'axe form ?
  D. RÈGLES EXPLICITES        — cas identifiés manuellement (allspice, fiddlehead…)

Logique Check A :
  Pour chaque IG, on extrait les tokens de son nom (+ expansion mots composés).
  Si un token correspond à un label de SOUS-CATÉGORIE EXISTANTE différente de
  la sienne → candidat de déplacement.
  Filtrage : on ignore les tokens trop courts ou polysémiques (ex. "spring",
  "white", "red", "sweet", "common"…).

Usage :
  python scripts/ingredients/audit_ig_positions.py
  python scripts/ingredients/audit_ig_positions.py --json-only
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT      = Path(__file__).resolve().parents[2]
TREE_FILE = ROOT / "backend/data/ingredients/ingredients_tree.json"
OUT_DIR   = ROOT / "scripts/ingredients"


# ── Singularisation basique EN ───────────────────────────────────────────────
_IRREG = {
    "seaweeds": "seaweed", "berries": "berry", "cherries": "cherry",
    "raspberries": "raspberry", "strawberries": "strawberry",
    "blueberries": "blueberry", "cranberries": "cranberry",
    "gooseberries": "gooseberry", "mulberries": "mulberry",
    "bilberries": "bilberry", "blackberries": "blackberry",
    "potatoes": "potato", "tomatoes": "tomato", "avocados": "avocado",
    "mangoes": "mango", "olives": "olive", "grapes": "grape",
    "plums": "plum", "pears": "pear", "peaches": "peach",
    "apricots": "apricot", "prunes": "prune", "lychees": "lychee",
    "guavas": "guava", "papayas": "papaya", "bananas": "banana",
    "pineapples": "pineapple", "lemons": "lemon", "limes": "lime",
    "oranges": "orange", "artichokes": "artichoke", "mushrooms": "mushroom",
    "beans": "bean", "peas": "pea", "lentils": "lentil",
    "almonds": "almond", "walnuts": "walnut", "cashews": "cashew",
    "pistachios": "pistachio", "hazelnuts": "hazelnut",
    "peanuts": "peanut", "chestnuts": "chestnut", "pecans": "pecan",
    "oats": "oat", "vinegars": "vinegar", "mustards": "mustard",
    "honeys": "honey", "sugars": "sugar", "syrups": "syrup",
    "oils": "oil", "butters": "butter", "cheeses": "cheese",
    "eggs": "egg", "seeds": "seed", "dates": "date", "figs": "fig",
    "cloves": "clove", "clementines": "clementine", "quinces": "quince",
    "pomegranates": "pomegranate", "persimmons": "persimmon",
    "kiwis": "kiwi", "kumquats": "kumquat", "mandarins": "mandarin",
    "melons": "melon", "nectarines": "nectarine", "plantains": "plantain",
    "tamarinds": "tamarind", "beets": "beet", "eggplants": "eggplant",
    "cucumbers": "cucumber", "carrots": "carrot", "leeks": "leek",
    "radishes": "radish", "rutabagas": "rutabaga",
    "grapefruits": "grapefruit", "currants": "currant",
    "onions": "onion", "cowpeas": "cowpea", "chickpeas": "chickpea",
    "shallots": "shallot", "chayotes": "chayote", "yams": "yam",
    "lettuces": "lettuce", "blackcurrants": "blackcurrant",
    "spices": "spice", "herbs": "herb",
}

def _sing(w: str) -> str:
    if w in _IRREG: return _IRREG[w]
    if w.endswith("ies") and len(w) > 4: return w[:-3] + "y"
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3: return w[:-1]
    return w


# ── Expansion des mots composés dans les noms ────────────────────────────────
_COMPOUND: dict[str, set[str]] = {
    "beetroot":     {"beet"},
    "cornmeal":     {"corn"}, "cornstarch": {"corn"}, "cornflour": {"corn"},
    "peppermint":   {"mint"}, "spearmint": {"mint"},
    "soybean":      {"soy"}, "soybeans": {"soy"},
    "lemongrass":   {"lemon"},
    "buttermilk":   {"milk"},
    "blackcurrant": {"currant"}, "redcurrant": {"currant"},
    "brazilnut":    {"brazil"}, "brazilnuts": {"brazil"},
    "applesauce":   {"apple"}, "crabapple": {"apple"},
    "kiwifruit":    {"kiwi"},
    "gooseberry":   {"gooseberry"},
    "mulberry":     {"mulberry"},
    "huckleberries":{"blueberry"},
    "buckwheat":    {"buckwheat"},
}

def _expand_name(name: str) -> set[str]:
    toks = set(re.findall(r"[a-z]+", name.lower()))
    extra: set[str] = set()
    for t in list(toks):
        if t in _COMPOUND:
            extra |= _COMPOUND[t]
    return toks | extra


# ── Tokens polysémiques à ignorer dans Check A ───────────────────────────────
# (trop communs ou trop ambigus pour déduire un déplacement)
_AMBIGUOUS_TOKENS: set[str] = {
    "spring", "white", "red", "green", "black", "yellow", "blue",
    "dark", "light", "sweet", "bitter", "common", "wild", "garden",
    "hot", "soft", "hard", "long", "short", "flat", "round",
    "whole", "raw", "dried", "fresh", "frozen", "cooked",
    "type", "mix", "mixed", "blend", "powder", "leaf", "leaves",
    "small", "large", "medium", "baby", "young", "mature", "old",
    "ground", "sliced", "diced", "crushed", "chopped",
    "oil", "fat", "meat", "flesh", "root", "stem", "seed",
    "juice", "flour", "milk", "butter",
    "plant", "herb", "spice", "grain", "cereal",
    "food", "product", "ingredient",
    # mots de nationalité
    "chinese", "japanese", "korean", "indian", "italian", "french",
    "thai", "mexican", "american", "european",
}

# Mots bruit du label sous-catégorie (non extraits comme tokens clés)
_LABEL_NOISE: set[str] = {
    "and", "or", "the", "of", "with", "in", "a", "an",
    "general", "various", "other", "miscellaneous", "mixed",
    "products", "dishes", "agents", "prepared", "processed",
    "varieties", "based", "tropical", "exotic", "heritage",
    "root", "salad", "asian", "nut", "sea",
}


def _label_key_tokens(label: str) -> set[str]:
    """Tokens discriminants du label sous-catégorie."""
    toks: set[str] = set()
    for raw in label.replace("_", " ").split():
        w = raw.lower()
        if w in _LABEL_NOISE or w in _AMBIGUOUS_TOKENS or len(w) <= 2:
            continue
        toks.add(w)
        s = _sing(w)
        if s != w:
            toks.add(s)
    return toks

# Overrides manuels : label → tokens clés (remplace la dérivation automatique)
_LABEL_OVERRIDE: dict[str, set[str]] = {
    "passion_fruits":       {"passion"},
    "goji_berries":         {"goji"},
    "asian_cabbages":       {"bok", "pak"},
    "sweet_potatoes":       {"sweet_potato"},   # token composite intentionnel
    "jerusalem_artichokes": {"jerusalem"},
    "fava_beans":           {"fava", "broad"},
    "mustard_greens":       {"mustard"},
    "mustard_seeds":        {"mustard"},
    "quatre_epices":        set(),              # skip — nom FR
    "bay_leaf":             {"bay"},
    "creme_fraiche":        set(),              # skip — nom FR
    "macadamia_nuts":       {"macadamia"},
    "brazil_nuts":          {"brazil"},
    "pine_nuts":            {"pine"},
    "lemongrass":           {"lemongrass", "citronella"},
    "blackcurrants":        {"blackcurrant"},
    "wheat_semolinas":      {"semolina"},
    "brans_and_germs":      set(),              # skip
}

# Sous-catégories à exclure complètement du Check A
# (nommées par variété/espèce où le label n'apparaît pas dans le nom)
_SKIP_A: set[str] = {
    "seaweeds",        # dulse, kelp, spirulina ≠ "seaweed"
    "cheeses",         # Asiago, Beaufort ≠ "cheese"
    "oils",            # form=oil retiré du nom canonique
    "alcohols", "wines", "cacao",
    "miscellaneous_condiments",
    "eggs_general",
    "brans_and_germs", "heritage_varieties",
    "exotic_fruits", "tropical_tubers", "root_vegetables", "salad_greens",
    "seeds", "nut_butters",
    "prepared_eggs", "broths_and_stocks", "breads_and_pastries",
    "pastry_doughs_and_pie_crusts", "prepared_sauces_and_condiments",
    "vegetarian_products_and_prepared_soy", "prepared_desserts_and_confectionery",
    "leavening_agents_and_additives", "acidifying_agents",
    "gelling_agents", "sweeteners", "baking_powders", "additives",
    "creme_fraiche", "condensed_milk", "powdered_milk",
    "honeys",  # royal jelly, pollen ≠ "honey" par nom
    "quatre_epices", "palm",
    # Multi-variétés où le token du label est souvent absent du nom canonique
    "wheat",           # triticale, durum, freekeh, hard red spring…
    "beans",           # mung, borlotti, flageolet…
    "squash",          # dishcloth gourd, calabash gourd…
    "cabbage",         # kale, kohlrabi, pak choi…
    "peas",            # snap, snow, field peas…
    "soy",             # soybean → "soy" via compound OK mais tofu, miso pas
    "mushrooms",       # truffe, pied-de-beurre, etc. — cas gérés par Check D
    "bilberries",      # blueberries, huckleberries ≠ bilberry
    "chicory",         # endive, escarole = famille
    "watercress",      # cress, garden cress ≠ watercress
    "onions",          # chives, shallots = famille Allium
    "breads",          # wheat flour, bagel, naan ≠ "bread"
    "corn",            # cornmeal → OK via compound, mais masa, polenta
    "salt",            # fleur de sel ≠ "salt" en token exact
    "currants",        # gooseberry ≠ currant → géré Check D
    "walnuts",         # acorn ≠ walnut → géré Check D
    "blackberries",    # mulberry ≠ blackberry → géré Check D
    "grapes",          # vine leaf, raisin → géré Check D
    "figs",            # prickly pear → géré Check D
    "lemons",          # lime → géré Check D
    "bananas",         # plantain → géré Check D
    "chili_peppers",   # allspice → géré Check D
    "tomatoes",        # tomatillo ≈ tomate → toléré
    "plums",           # prune = plum séché → toléré
    "oranges",         # mixed citrus → toléré
    "yogurts",         # yogourt (orthographe) → toléré
    "syrups",          # molasses → toléré
    "sugars",          # fructose → toléré
    "milk",            # buttermilk → milk via compound OK, dulce de leche non
    "cowpeas",         # hyacinth bean → géré Check D
}


def _build_subcat_index(tree: dict) -> dict[str, list[dict]]:
    """token → liste de {cat_label, sub_id, sub_label}."""
    idx: dict[str, list[dict]] = defaultdict(list)
    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            lbl = sub["label"]
            if lbl in _SKIP_A:
                continue
            if lbl in _LABEL_OVERRIDE:
                toks = _LABEL_OVERRIDE[lbl]
            else:
                toks = _label_key_tokens(lbl)
            for t in toks:
                idx[t].append({
                    "cat_label": cat["label"],
                    "sub_id":    sub["id"],
                    "sub_label": lbl,
                })
    return dict(idx)


# ── B. Form ↔ catégorie ──────────────────────────────────────────────────────
_FORM_EXPECTED: dict[str, set[str]] = {
    "oil":    {"fats_and_oils"},
    "butter": {"dairy_products", "nuts_and_seeds", "fats_and_oils"},
    "milk":   {"dairy_products", "beverages", "nuts_and_seeds",
               "cereals_and_grains", "legumes"},
    "juice":  {"beverages", "fruits", "vegetables"},
    "flour":  {"cereals_and_grains", "vegetables", "legumes", "nuts_and_seeds"},
}

# ── C. Valeurs form invalides ────────────────────────────────────────────────
_INVALID_FORM: dict[str, str] = {
    "creamy":       "texture → supprimer ou garder uniquement pour les nut butters",
    "crunchy":      "texture → supprimer (ex: broccoli bouilli 'al dente' n'est pas une forme)",
    "long_grain":   "taille de grain → appartient au nom canonique, pas à form",
    "medium_grain": "taille de grain → appartient au nom canonique, pas à form",
    "short_grain":  "taille de grain → appartient au nom canonique, pas à form",
}
_BORDERLINE_FORM: dict[str, str] = {
    "sliced":      "découpe/conditionnement, pas une forme alimentaire",
    "diced":       "découpe, pas une forme alimentaire",
    "grated":      "râpage, pas une forme alimentaire",
    "crushed":     "découpe, pas une forme alimentaire",
    "whipped":     "texture (acceptable pour cream/butter whipped)",
    "pieces":      "conditionnement, pas une forme",
    "rolled":      "procédé (rolled oats) — défendable",
    "plant_water": "valeur non-standard (ex: coconut water)",
    "whole":       "état du grain — chevauchement possible avec le nom",
}

# ── D. Règles explicites : cas confirmés manuellement ───────────────────────
# (pattern_nom, sous-cat_actuelle, sous-cat_attendue, explication)
_EXPLICIT_RULES: list[dict] = [
    # Buckwheat dans oats
    {
        "pattern":      r"\bbuckwheat\b",
        "current_sub":  "oats",
        "expected_sub": "buckwheat",
        "detail":       "buckwheat groats ≠ oat — sous-catégorie 'buckwheat' existe",
    },
    # Lime dans lemons
    {
        "pattern":      r"\blimes?\b",
        "current_sub":  "lemons",
        "expected_sub": "limes",
        "detail":       "lime ≠ lemon — sous-catégorie 'limes' existe",
    },
    # Prickly pear dans figs
    {
        "pattern":      r"\bprickly\b",
        "current_sub":  "figs",
        "expected_sub": "exotic_fruits",
        "detail":       "prickly pear = figue de barbarie ≠ figue — déplacer vers exotic_fruits",
    },
    # Fiddlehead (fougère) dans mushrooms
    {
        "pattern":      r"\bfiddlehead\b",
        "current_sub":  "mushrooms",
        "expected_sub": "salad_greens",
        "detail":       "fiddlehead = jeune pousse de fougère ≠ champignon — déplacer vers salad_greens",
    },
    # Allspice dans chili_peppers
    {
        "pattern":      r"\ballspice\b",
        "current_sub":  "chili_peppers",
        "expected_sub": "herbs_and_spices/[nouvelle sous-cat allspice]",
        "detail":       "allspice (piment de la Jamaïque) = épice aromatique ≠ piment — créer sous-cat allspice",
    },
    # Plantains dans bananas (singulier ET pluriel)
    {
        "pattern":      r"\bplantains?\b",
        "current_sub":  "bananas",
        "expected_sub": "plantains",
        "detail":       "plantain ≠ banana — sous-catégorie 'plantains' dédiée existe",
    },
    # Acorns dans walnuts
    {
        "pattern":      r"\bacorns?\b",
        "current_sub":  "walnuts",
        "expected_sub": "nuts_and_seeds/seeds ou nouvelle sous-cat acorns",
        "detail":       "acorn (gland de chêne) ≠ noix (Juglans) — famille botanique différente",
    },
    # Mulberry dans blackberries
    {
        "pattern":      r"\bmulberr",
        "current_sub":  "blackberries",
        "expected_sub": "exotic_fruits",
        "detail":       "mulberry (Morus) ≠ blackberry (Rubus) — déplacer vers exotic_fruits",
    },
    # Gooseberry dans currants
    {
        "pattern":      r"\bgooseberr",
        "current_sub":  "currants",
        "expected_sub": "exotic_fruits ou nouvelle sous-cat gooseberries",
        "detail":       "gooseberry (groseille à maquereau) ≠ currant (groseille) — genre botanique différent",
    },
    # Hyacinth bean dans cowpeas
    {
        "pattern":      r"\bhyacinth\b",
        "current_sub":  "cowpeas",
        "expected_sub": "beans",
        "detail":       "hyacinth bean (Lablab purpureus) ≠ cowpea (Vigna unguiculata) — déplacer vers beans",
    },
    # Watermelon dans melons (sous-cat watermelons existe)
    {
        "pattern":      r"\bwatermelons?\b",
        "current_sub":  "melons",
        "expected_sub": "watermelons",
        "detail":       "watermelon ≠ melon — sous-catégorie 'watermelons' dédiée existe",
    },
    # SEUL l'IG chair de potiron (part=peeled, pas part=seed) dans seeds
    {
        "pattern":      r"\bpie pumpkin\b",
        "current_sub":  "seeds",
        "expected_sub": "squash",
        "detail":       "pie pumpkin squash (USDA:2727578, part=peeled) = chair de légume ≠ graine — déplacer vers vegetables/squash",
    },
    # Carob dans root_vegetables
    {
        "pattern":      r"\bcarob\b",
        "current_sub":  "root_vegetables",
        "expected_sub": "legumes/[nouvelle sous-cat carob] ou herbs_and_spices",
        "detail":       "carob (caroube) = légumineuse arborée ≠ légume-racine",
    },
]

# ── A. Paires tolérées dans la correspondance croisée ────────────────────────
# (current_location, candidate_location) → ne pas signaler
# Format : "cat_label/sub_label"
_TOLERATED_CROSS: set[tuple[str, str]] = {
    # Même ingrédient présent sous deux formes dans deux sous-cats
    ("herbs_and_spices/garlic",         "vegetables/garlic"),
    ("vegetables/garlic",               "herbs_and_spices/garlic"),
    ("herbs_and_spices/celery",         "vegetables/celery"),
    ("vegetables/celery",               "herbs_and_spices/celery"),
    ("herbs_and_spices/fennel",         "vegetables/fennel"),
    ("vegetables/fennel",               "herbs_and_spices/fennel"),
    ("herbs_and_spices/onion",          "vegetables/onions"),
    ("vegetables/onions",               "herbs_and_spices/onion"),
    # Pepper (épice) vs bell_peppers (légume)
    ("herbs_and_spices/pepper",         "vegetables/bell_peppers"),
    ("vegetables/bell_peppers",         "herbs_and_spices/pepper"),
    # Moutarde : condiment, graine épice, feuille légume
    ("condiments_and_sauces/mustards",  "herbs_and_spices/mustard_seeds"),
    ("condiments_and_sauces/mustards",  "vegetables/mustard_greens"),
    ("herbs_and_spices/mustard_seeds",  "condiments_and_sauces/mustards"),
    ("herbs_and_spices/mustard_seeds",  "vegetables/mustard_greens"),
    ("vegetables/mustard_greens",       "condiments_and_sauces/mustards"),
    ("vegetables/mustard_greens",       "herbs_and_spices/mustard_seeds"),
    ("vegetables/mustard_greens",       "vegetables/spinach"),      # mustard spinach
    # Patate douce vs pomme de terre
    ("vegetables/sweet_potatoes",       "vegetables/potatoes"),
    # Topinambour vs artichaut
    ("vegetables/jerusalem_artichokes", "vegetables/artichokes"),
    # Beurre sucré ("sweet cream butter") → token cream
    ("dairy_products/butter",           "dairy_products/cream"),
    # Goyave fraise (variété de goyave)
    ("fruits/guavas",                   "fruits/strawberries"),
    # Crème de pruneaux (produit de pruneau)
    ("fruits/prunes",                   "dairy_products/cream"),
    # Cacahuète chocolatée
    ("nuts_and_seeds/peanuts",          "sugars_honeys_and_confectionery/chocolate"),
    # Semoule de couscous = semoule de blé fine
    ("cereals_and_grains/wheat_semolinas", "cereals_and_grains/couscous"),
}


def walk(tree: dict):
    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                yield cat, sub, ig


def run_checks(tree: dict) -> dict[str, list[dict]]:
    issues: dict[str, list[dict]] = defaultdict(list)

    # Construire l'index sous-catégorie pour Check A
    subcat_idx = _build_subcat_index(tree)

    for cat, sub, ig in walk(tree):
        ig_id   = ig["id"]
        en_name = ig.get("canonical_name_en", "")
        axes_en = ig.get("axes_en", {})
        cat_lbl = cat["label"]
        sub_lbl = sub["label"]
        loc     = f"{cat_lbl} / {sub_lbl}"

        # ── A. Correspondance croisée ────────────────────────────────────────
        if sub_lbl not in _SKIP_A:
            name_toks = _expand_name(en_name)
            candidates: list[str] = []
            for tok in name_toks:
                if tok in _AMBIGUOUS_TOKENS or len(tok) <= 2:
                    continue
                if tok not in subcat_idx:
                    continue
                for match in subcat_idx[tok]:
                    if match["sub_id"] == sub["id"]:
                        continue
                    cand = f"{match['cat_label']}/{match['sub_label']}"
                    cur_norm = f"{cat_lbl}/{sub_lbl}"
                    # Filtrer les paires croisées connues et tolérées
                    if (cur_norm, cand) in _TOLERATED_CROSS:
                        continue
                    candidates.append(cand)
            if candidates:
                issues["CROSS_MATCH_SUBCAT"].append({
                    "id": ig_id, "name": en_name, "location": loc,
                    "candidates": sorted(set(candidates)),
                    "detail": (
                        f"Token(s) du nom correspondent à d'autres sous-cats : "
                        f"{sorted(set(candidates))}"
                    ),
                })

        # ── B. Form ↔ catégorie ──────────────────────────────────────────────
        form_val = axes_en.get("form")
        if form_val and form_val in _FORM_EXPECTED:
            if cat_lbl not in _FORM_EXPECTED[form_val]:
                issues["WRONG_CAT_FOR_FORM"].append({
                    "id": ig_id, "name": en_name, "location": loc,
                    "form": form_val,
                    "expected_cats": sorted(_FORM_EXPECTED[form_val]),
                    "detail": (
                        f"form={form_val!r} mais cat={cat_lbl!r} "
                        f"(attendu: {sorted(_FORM_EXPECTED[form_val])})"
                    ),
                })

        # ── C. Valeurs form invalides ────────────────────────────────────────
        if form_val in _INVALID_FORM:
            issues["INVALID_FORM_VALUE"].append({
                "id": ig_id, "name": en_name, "location": loc,
                "form": form_val, "detail": _INVALID_FORM[form_val],
            })
        elif form_val in _BORDERLINE_FORM:
            issues["BORDERLINE_FORM_VALUE"].append({
                "id": ig_id, "name": en_name, "location": loc,
                "form": form_val, "detail": _BORDERLINE_FORM[form_val],
            })

        # ── D. Règles explicites ─────────────────────────────────────────────
        for rule in _EXPLICIT_RULES:
            if sub_lbl == rule["current_sub"]:
                if re.search(rule["pattern"], en_name, re.I):
                    issues["EXPLICIT_MISPLACEMENT"].append({
                        "id": ig_id, "name": en_name, "location": loc,
                        "expected_sub": rule["expected_sub"],
                        "detail": rule["detail"],
                    })
                    break

    return dict(issues)


def print_report(issues: dict[str, list[dict]]) -> None:
    sections = [
        ("A. CORRESPONDANCE CROISÉE",  "CROSS_MATCH_SUBCAT"),
        ("B. FORM ↔ CATÉGORIE",        "WRONG_CAT_FOR_FORM"),
        ("C. FORM VALEUR INVALIDE",    "INVALID_FORM_VALUE"),
        ("C'. FORM VALEUR LIMITE",     "BORDERLINE_FORM_VALUE"),
        ("D. DÉPLACEMENTS CONFIRMÉS",  "EXPLICIT_MISPLACEMENT"),
    ]
    total = sum(len(v) for v in issues.values())
    print("\n" + "=" * 72)
    print("AUDIT POSITIONS IG")
    print("=" * 72)

    for title, key in sections:
        lst = issues.get(key, [])
        print(f"\n{title} ({len(lst)}) :")
        if not lst:
            print("  (aucun)")
            continue
        for item in sorted(lst, key=lambda x: x["location"] + x["id"]):
            print(f"  [{item['id']}] {item['name']!r}")
            print(f"    loc    : {item['location']}")
            print(f"    détail : {item['detail']}")

    print(f"\n{'=' * 72}")
    print(f"TOTAL : {total}")
    for _, key in sections:
        n = len(issues.get(key, []))
        if n:
            print(f"  {key:30s}: {n}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    print("Chargement du tree...")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))
    igs_total = sum(
        len(sub.get("ingredient_groups", []))
        for cat in tree["categories"]
        for sub in cat.get("subcategories", [])
    )
    print(f"{igs_total} IGs analysés\n")

    issues = run_checks(tree)

    if not args.json_only:
        print_report(issues)

    total = sum(len(v) for v in issues.values())
    print(f"\nTotal issues : {total}")

    report = {
        "generated_at": datetime.now().isoformat(),
        "igs_analysed": igs_total,
        "total_issues": total,
        "counts": {k: len(v) for k, v in issues.items()},
        "issues": issues,
    }
    out = OUT_DIR / "audit_ig_positions_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapport : {out}")


if __name__ == "__main__":
    main()
