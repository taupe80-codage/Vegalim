#!/usr/bin/env python3
"""audit_ingredient_links.py — les ingrédients des recettes sont-ils liés, et au bon ?

1. Liaison (moteur nutritionnel, comme compute_nutrition) :
   - non_resolu      : aucune fiche nutritionnelle trouvée
   - sans_fiche      : absent du dictionnaire d'ingrédients
   - autre_aliment   : la fiche nutritionnelle retenue appartient à un autre
                       aliment de l'arbre (v32_ing_id différent) que l'ingrédient
   - quantite_nulle  : ligne chiffrée qui ne pèse rien (unité non convertie)

2. Bon ingrédient : chaque quantité citée dans les étapes (« 250 g de lentilles
   corail ») est rapprochée de la ligne de composition au nom le plus proche
   (même quantité de préférence), puis comparée à l'ingrédient lié :
   - variete         : qualificatif contradictoire (lentille corail ↔ verte, tofu
                       fumé ↔ nature, lait d'avoine ↔ lait de vache, riz basmati ↔ rond…)
   - etat            : le texte dit cuit / en conserve, l'ingrédient est sec (ou
                       l'inverse) — le poids n'a pas le même sens (×2,5 en calories)
   (rapprochement par le nom : libellé de l'ingrédient + traduction de son id)
   - absent          : aliment cité avec une quantité dans les étapes, sans aucune
                       ligne de composition à ce nom (ingrédient non lié)

Usage :
    python scripts/recipes/audit_ingredient_links.py [--out chemin.txt]
"""
from __future__ import annotations

import logging
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
logging.disable(logging.CRITICAL)
sys.stdout.reconfigure(encoding="utf-8")

from backend.core.data_io import load_catalogue_recipes  # noqa: E402
from backend.engine.nutrition_engine import compute_nutrition, get_data, _qty_to_g  # noqa: E402


def norm(s: str) -> str:
    s = (s or "").replace("œ", "oe").replace("Œ", "oe").replace("’", "'")
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


# famille (mot de tête) -> qualificatifs exclusifs entre eux ; chaque
# qualificatif : (libellé, motifs dans le texte FR, motifs dans id/nom de l'ingrédient)
FAMILIES: dict[str, list[tuple[str, tuple[str, ...], tuple[str, ...]]]] = {
    "lentille": [
        ("corail", ("corail", "rouge"), ("red_lentil", "corail", "rouge")),
        ("verte", ("verte", "du puy", "puy"), ("green_lentil", "verte", "puy")),
        ("beluga", ("beluga", "noire"), ("beluga", "black_lentil")),
        ("blonde", ("blonde", "brune"), ("brown_lentil", "blonde", "brune")),
    ],
    "tofu": [
        ("fume", ("fume",), ("smoked", "fume")),
        ("soyeux", ("soyeux",), ("silken", "soyeux")),
    ],
    "lait": [
        ("vache", ("de vache", "entier", "demi-ecreme"), ("cow", "vache")),
        ("avoine", ("d'avoine", "avoine"), ("oat",)),
        ("soja", ("de soja", "soja"), ("soy",)),
        ("amande", ("d'amande", "amande"), ("almond",)),
        ("coco", ("de coco", "coco"), ("coconut",)),
        ("riz", ("de riz",), ("rice_milk", "rice_drink")),
        ("cajou", ("de cajou",), ("cashew",)),
    ],
    "creme": [
        ("vache", ("fraiche", "liquide entiere", "de vache"), ("cow", "creme_fraiche", "cream_")),
        ("soja", ("de soja", "soja"), ("soy",)),
        ("avoine", ("d'avoine",), ("oat",)),
        ("coco", ("de coco", "coco"), ("coconut",)),
        ("cajou", ("de cajou",), ("cashew",)),
    ],
    "yaourt": [
        ("soja", ("de soja", "soja"), ("soy",)),
        ("coco", ("de coco", "coco"), ("coconut",)),
        ("grec", ("grec",), ("greek",)),
    ],
    "beurre": [
        ("vegetal", ("vegetal", "vegan"), ("vegan_butter", "plant_butter", "margarine")),
        ("cacahuete", ("de cacahuete", "cacahuete"), ("peanut",)),
        ("amande", ("d'amande",), ("almond",)),
        ("cajou", ("de cajou",), ("cashew",)),
        ("clarifie", ("clarifie", "ghee"), ("ghee", "clarified")),
    ],
    "haricot": [
        ("rouge", ("rouges",), ("kidney", "red_bean", "rouge")),
        ("blanc", ("blancs", "lingot", "coco"), ("white_bean", "navy", "cannellini", "blanc", "lingot")),
        ("noir", ("noirs",), ("black_bean", "black_turtle", "noir")),
        ("vert", ("verts",), ("green_bean", "snap", "vert")),
        ("mungo", ("mungo", "mung"), ("mung",)),
        ("azuki", ("azuki", "adzuki"), ("adzuki", "azuki")),
        ("pinto", ("pinto",), ("pinto",)),
    ],
    "riz": [
        ("basmati", ("basmati",), ("basmati",)),
        ("jasmin", ("jasmin", "thai"), ("jasmine",)),
        ("rond", ("rond", "arborio", "carnaroli", "risotto", "a sushi", "gluant"), ("short_grain", "arborio", "glutinous", "sushi", "risotto")),
        ("complet", ("complet",), ("brown_rice", "wholegrain_rice", "complet")),
        ("noir", ("noir",), ("black_rice", "noir")),
        ("sauvage", ("sauvage",), ("wild_rice",)),
    ],
    "farine": [
        ("ble", ("de ble", "t45", "t55", "t65"), ("wheat_flour", "white_flour", "ble")),
        ("complete", ("complete", "t110", "t150"), ("whole_wheat_flour", "wholemeal", "complete")),
        ("sarrasin", ("sarrasin",), ("buckwheat",)),
        ("pois chiche", ("pois chiche", "besan"), ("chickpea", "gram_flour", "besan")),
        ("riz", ("de riz",), ("rice_flour",)),
        ("mais", ("de mais", "masa"), ("corn", "masa", "maize")),
        ("epeautre", ("epeautre",), ("spelt",)),
        ("seigle", ("seigle",), ("rye",)),
        ("teff", ("teff",), ("teff",)),
        ("amande", ("d'amande", "poudre d'amande"), ("almond",)),
    ],
    "sucre": [
        ("coco", ("de coco",), ("coconut_sugar",)),
        ("glace", ("glace",), ("powdered", "icing")),
        ("roux", ("roux", "cassonade", "muscovado", "complet", "rapadura", "vergeoise"), ("brown_sugar", "muscovado", "cassonade", "rapadura", "panela", "vergeoise")),
        ("blanc", ("blanc", "semoule", "en poudre"), ("granulated", "white_sugar", "sugars_white")),
    ],
    "huile": [
        ("olive", ("d'olive", "olive"), ("olive",)),
        ("sesame", ("de sesame", "sesame"), ("sesame",)),
        ("coco", ("de coco",), ("coconut",)),
        ("tournesol", ("tournesol",), ("sunflower",)),
        ("colza", ("colza",), ("rapeseed", "canola", "colza")),
        ("arachide", ("arachide",), ("peanut",)),
        ("noix", ("de noix",), ("walnut",)),
        ("moutarde", ("de moutarde",), ("mustard",)),
    ],
    "vinaigre": [
        ("cidre", ("cidre",), ("cider",)),
        ("riz", ("de riz",), ("rice",)),
        ("balsamique", ("balsamique",), ("balsamic",)),
        ("xeres", ("xeres",), ("sherry",)),
        ("vin", ("de vin",), ("wine",)),
    ],
    "oignon": [
        ("rouge", ("rouge",), ("red_onion",)),
        ("nouveau", ("nouveau", "vert", "cebette", "ciboule"), ("green_onion", "spring_onion", "scallion")),
    ],
    "poivron": [
        ("rouge", ("rouge",), ("red",)),
        ("vert", ("vert",), ("green",)),
        ("jaune", ("jaune",), ("yellow",)),
    ],
    "chou": [
        ("rouge", ("rouge",), ("red_cabbage",)),
        ("kale", ("kale", "frise"), ("kale",)),
        ("chinois", ("chinois", "pak", "bok"), ("chinese", "pak_choi", "bok_choy", "napa")),
        ("fleur", ("chou-fleur", "fleur"), ("cauliflower",)),
        ("bruxelles", ("bruxelles",), ("brussels",)),
    ],
    "nouille": [
        ("riz", ("de riz",), ("rice",)),
        ("soba", ("soba", "sarrasin"), ("soba", "buckwheat")),
        ("udon", ("udon",), ("udon",)),
    ],
    "champignon": [
        ("shiitake", ("shiitake",), ("shiitake",)),
        ("pleurote", ("pleurote",), ("oyster",)),
        ("paris", ("de paris", "blond"), ("button", "white_mushroom", "agaricus")),
    ],
    "fromage": [],
}

# l'ingrédient est « sec » (poids cru d'un produit à réhydrater ou cuire)
DRY_ID = re.compile(r"(_dried|_dry|raw_seed|_seed_dried|_mature_seeds?_raw)")
LEGUME_OR_GRAIN = re.compile(r"(lentil|chickpea|bean|pea|rice|quinoa|bulgur|barley|millet|couscous|semolina|split_pea|cowpea|lupin|freekeh|farro|spelt|buckwheat_groat)")
COOKED_TEXT = re.compile(r"\b(cuit|cuite|cuits|cuites|en conserve|en boite|egoutte|egouttes|egouttees|rinces? et egoutt)")
DRY_TEXT = re.compile(r"\b(sec|secs|seche|seches|crus?|deshydrate)\b")
COOKED_ID = re.compile(r"(cooked|boiled|canned|_drained)")

QTY_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g|ml|cl|l)\b\.?\s*(?:de |d'|d’|du |des )?([^,.;:()\n]{0,45})", re.I)
UNIT_G = {"g": 1, "kg": 1000, "ml": 1, "cl": 10, "l": 1000}
STOP = {"de", "d", "du", "des", "la", "le", "les", "et", "a", "au", "aux", "en", "un", "une", "pour", "avec", "dans", "l"}


def words(s: str) -> set[str]:
    out = set()
    for w in re.split(r"[^a-z0-9]+", norm(s)):
        if len(w) > 2 and w not in STOP:
            out.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)
    return out


def ing_label(token: str) -> tuple[str, str]:
    ing = get_data.ingredients.get_by_name(token) or {}
    fr = ing.get("canonical_name_fr") or ing.get("name_fr") or ""
    en = ing.get("canonical_name_en") or ing.get("name_en") or ""
    return fr, f"{token} {norm(en)} {norm(fr)}"


# mots français d'un ingrédient : son libellé + traduction des segments de l'id
ID_FR = {
    "oil": "huile", "butter": "beurre", "juice": "jus", "flour": "farine", "sugar": "sucre",
    "sugars": "sucre", "milk": "lait", "cream": "creme", "yogurt": "yaourt", "vinegar": "vinaigre",
    "stock": "bouillon", "water": "eau", "salt": "sel", "egg": "oeuf", "cheese": "fromage",
    "rice": "riz", "lentil": "lentille", "bean": "haricot", "beans": "haricot", "chickpea": "pois chiche",
    "chickpeas": "pois chiche", "pea": "pois petit", "peas": "pois petit", "pasta": "pate", "noodle": "nouille",
    "noodles": "nouille", "bread": "pain", "breadcrumbs": "chapelure panko", "tahini": "tahin tahini",
    "paste": "pate concentre puree", "sauce": "sauce", "seed": "graine", "nuts": "noix", "peanut": "cacahuete arachide",
    "garlic": "ail", "onion": "oignon", "ginger": "gingembre", "tomato": "tomate", "pepper": "poivre poivron piment",
    "chili": "piment", "chilli": "piment", "coriander": "coriandre", "parsley": "persil", "mint": "menthe",
    "basil": "basilic", "lemon": "citron", "lime": "citron", "semolina": "semoule", "couscous": "semoule couscous",
    "yeast": "levure", "baking": "levure", "cornstarch": "fecule maizena", "starch": "fecule", "honey": "miel",
    "syrup": "sirop", "wine": "vin", "soy": "soja", "tofu": "tofu", "tempeh": "tempeh", "seitan": "seitan",
    "mushroom": "champignon", "potato": "pomme terre", "sweet": "patate", "squash": "courge", "pumpkin": "courge potiron",
    "zucchini": "courgette", "eggplant": "aubergine", "spinach": "epinard", "cabbage": "chou", "carrot": "carotte",
    "leek": "poireau", "leeks": "poireau", "celery": "celeri", "apple": "pomme", "banana": "banane", "coconut": "coco",
    "almond": "amande", "cashew": "cajou", "walnut": "noix", "hazelnut": "noisette", "sesame": "sesame",
    "cumin": "cumin", "cinnamon": "cannelle", "vanilla": "vanille", "chocolate": "chocolat", "cocoa": "cacao",
    "ghee": "ghee beurre clarifie", "margarine": "margarine beurre", "mustard": "moutarde", "olive": "olive",
    "raisin": "raisin", "date": "datte", "dates": "datte", "orange": "orange", "cucumber": "concombre",
    "lettuce": "salade laitue", "kale": "chou kale", "cauliflower": "chou fleur", "broccoli": "brocoli",
    "turmeric": "curcuma", "paprika": "paprika", "oat": "avoine flocon", "oats": "avoine flocon",
    "quinoa": "quinoa", "bulgur": "boulgour", "polenta": "polenta", "corn": "mais", "maize": "mais",
    "shallot": "echalote", "thyme": "thym", "rosemary": "romarin", "dill": "aneth", "chive": "ciboulette",
    "chives": "ciboulette", "radish": "radis", "beet": "betterave", "beetroot": "betterave", "fennel": "fenouil",
    "artichoke": "artichaut", "asparagus": "asperge", "avocado": "avocat", "mango": "mangue", "pineapple": "ananas",
    "strawberry": "fraise", "raspberry": "framboise", "blueberry": "myrtille", "pear": "poire", "plum": "prune",
    "prune": "pruneau", "fig": "figue", "apricot": "abricot", "cherry": "cerise", "lentils": "lentille",
    "feta": "feta", "mozzarella": "mozzarella", "parmesan": "parmesan", "ricotta": "ricotta",
    "cheddar": "cheddar", "halloumi": "halloumi", "paneer": "paneer", "miso": "miso", "harissa": "harissa",
    "gnocchi": "gnocchi", "tortilla": "tortilla galette", "pita": "pita pain", "rum": "rhum", "seaweed": "algue",
    "nori": "nori algue", "kombu": "kombu algue", "wakame": "wakame algue", "agar": "agar",
    "cow": "fromage", "sheep": "fromage brebis", "goat": "fromage chevre", "tomme": "fromage tomme",
    "gruyere": "fromage gruyere", "queso": "fromage", "pigeon": "toor lentille", "gram": "lentille",
    "mung": "moong mungo", "sprouts": "pousse germe", "sprouted": "pousse germe", "wonton": "feuille wonton",
    "wrapper": "feuille", "roux": "roux", "fried": "frit", "noodles": "nouille", "vegan": "vegetal",
}
NOT_IN_COMPOSITION = {"eau", "bouillon", "glace", "glacon", "sel", "pate", "sauce", "melange", "farce",
                      "garniture", "appareil", "liquide", "jus", "puree", "total", "chaque", "reste",
                      "tout", "usage", "portion", "pratique", "feuille"}
_vocab: dict[str, set[str]] = {}


def vocab(token: str) -> set[str]:
    if token not in _vocab:
        fr, _ = ing_label(token)
        v = words(fr)
        for seg in token.split("_"):
            v |= words(ID_FR.get(seg, ""))
        if token.startswith("base_"):
            v |= words(token[5:].rsplit("_", 1)[0].replace("_", " "))
        _vocab[token] = v
    return _vocab[token]


FOOD_WORDS: set[str] = set()


def qualifiers(family: str, text: str, ident: str) -> tuple[set[str], set[str]]:
    in_text, in_ing = set(), set()
    for label, tpat, ipat in FAMILIES[family]:
        if any(re.search(r"(?<![a-z])" + re.escape(p), text) for p in tpat):
            in_text.add(label)
        if any(p in ident for p in ipat):
            in_ing.add(label)
    return in_text, in_ing


def audit() -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    recipes = load_catalogue_recipes()
    recipe_ids = {x["id"] for x in recipes}
    for x in recipes:                     # vocabulaire alimentaire du catalogue
        for c in x.get("composition") or []:
            FOOD_WORDS.update(vocab(c["ingredient"]))
    for r in recipes:
        rid = r["id"]
        b: dict = {}
        compute_nutrition(r, breakdown=b)
        comp = r.get("composition") or []
        for c in comp:
            t = c["ingredient"]
            ing = get_data.ingredients.get_by_name(t)
            if t in recipe_ids:
                continue                                  # renvoi vers une recette
            if ing is None:
                out["sans_fiche"].append(f"{rid} {t}")
            if t not in b:
                out["non_resolu"].append(f"{rid} {t}")
                continue
            v = b[t]["nutrients"]
            if ing and v.get("_v32_ing_id") and ing.get("v32_ing_id") and v["_v32_ing_id"] != ing["v32_ing_id"]:
                out["autre_aliment"].append(f"{rid} {t} [{ing.get('canonical_name_fr')}] → {v.get('name_fr')} {v.get('axes_fr')}")
            if isinstance(c.get("quantity"), (int, float)) and c["quantity"] > 0 and t != "water" \
                    and _qty_to_g(t, c) <= 0:
                out["quantite_nulle"].append(f"{rid} {t} {c['quantity']} {c.get('unit')}")

        # ── Bon ingrédient : quantités citées dans les étapes ────────────────
        lines = [c for c in comp if c["ingredient"].startswith("base_") or c["ingredient"] not in recipe_ids]
        steps = r.get("instructions") or r.get("steps") or []
        text = " ".join((s.get("text") if isinstance(s, dict) else str(s)) for s in steps)
        for m in QTY_RE.finditer(text):
            qty = float(m.group(1).replace(",", ".")) * UNIT_G[m.group(2).lower()]
            phrase = norm(m.group(3)).strip()
            head = [w for w in words(" ".join(phrase.split()[:4]))]
            if not head:
                continue
            first = next((w for w in re.split(r"[^a-z0-9]+", phrase) if len(w) > 2 and w not in STOP), "")
            first = first[:-1] if first.endswith("s") and len(first) > 4 else first
            cands = []
            for c in lines:
                score = len(set(head) & vocab(c["ingredient"]))
                if score:
                    unit = (c.get("unit") or "").lower()
                    cq = float(c["quantity"]) * UNIT_G.get(unit, 0) if isinstance(c.get("quantity"), (int, float)) else 0
                    cands.append((score, abs(cq - qty) <= 0.5, c))
            quote = f"« {m.group(0).strip()} »"
            if not cands:
                # aliment cité avec une quantité, sans aucune ligne de composition
                if first in FOOD_WORDS and first not in NOT_IN_COMPOSITION:
                    out["absent"].append(f"{rid} {quote}")
                continue
            _, _, c = max(cands, key=lambda x: (x[0], x[1]))
            t = c["ingredient"]
            fr, ident = ing_label(t)
            nfr = norm(fr)
            near = " ".join(phrase.split()[:5])
            for fam in FAMILIES:
                if not FAMILIES[fam] or fam not in near or fam not in (nfr + " " + ident):
                    continue
                q_text, q_ing = qualifiers(fam, near, ident)
                if q_text and q_ing and not (q_text & q_ing):
                    out["variete"].append(f"{rid} {quote} ↔ {t} [{fr}]")
                elif q_text and not q_ing and fam in ("lait", "creme", "yaourt", "beurre") and q_text - {"vache"}:
                    # texte végétal, ingrédient sans qualificatif = laitier
                    out["variete"].append(f"{rid} {quote} ↔ {t} [{fr}]")
            if LEGUME_OR_GRAIN.search(t):
                if COOKED_TEXT.search(near) and not DRY_TEXT.search(near) and DRY_ID.search(t) \
                        and not re.search(r"\bet (les|la|le) egoutt|laisser egoutt|l'egoutt", phrase):
                    out["etat"].append(f"{rid} {quote} ↔ {t} (sec)")
                elif DRY_TEXT.search(near) and COOKED_ID.search(t):
                    out["etat"].append(f"{rid} {quote} ↔ {t} (cuit)")
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "scripts" / "recipes" / "audit_ingredient_links.txt")
    args = ap.parse_args()
    res = audit()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        for k in ("non_resolu", "sans_fiche", "autre_aliment", "quantite_nulle", "variete", "etat", "absent"):
            fh.write(f"## {k} ({len(res.get(k, []))})\n")
            for line in res.get(k, []):
                fh.write(f"  {line}\n")
            fh.write("\n")
    for k in ("non_resolu", "sans_fiche", "autre_aliment", "quantite_nulle", "variete", "etat", "absent"):
        print(f"  {len(res.get(k, [])):4d}  {k}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
