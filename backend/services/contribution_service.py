"""
contribution_service.py — Recettes proposées par les utilisateurs.

Ce module ne touche pas à la base de données : il travaille sur le formulaire
(`data`, dict) et sur les recettes du catalogue. Les routes
(backend/api/routes/contributions.py) gèrent le stockage et les droits.

  options()                  → listes du formulaire (unités, types de plat…)
  normalize(data)            → formulaire nettoyé et borné
  parse_ingredient_lines(t)  → « 200 g de farine » → ligne structurée + suggestions
  build_recipe(data, …)      → recette au format du catalogue (recipes.json)
  analyze(data)              → vérifications automatiques (régime, nutrition,
                               doublons, complétude) affichées pendant la saisie
  save_photo(raw)            → photo ré-encodée en JPEG, sans métadonnées
  write_community_file(rs)   → backend/data/recipes/community_recipes.json,
                               fusionné au catalogue par data_io.load_recipes()

Le projet est 100 % végétarien : une proposition qui contient de la viande ou
du poisson est bloquée dès la saisie, et une recette annoncée vegan ne peut
pas être envoyée tant qu'un ingrédient d'origine animale y figure.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import secrets
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
COMMUNITY_PATH = _ROOT / "backend" / "data" / "recipes" / "community_recipes.json"
PHOTO_DIR = _ROOT / "backend" / "data" / "user_content" / "photos"

# ── Bornes du formulaire ──────────────────────────────────────────────────────

LIMITS = {
    "title_min": 5, "title_max": 100,
    "description_max": 500,
    "ingredients_min": 2, "ingredients_max": 40,
    "ingredient_name_max": 80, "ingredient_note_max": 60,
    "steps_min": 2, "steps_max": 30, "step_max": 800,
    "tip_max": 500,
    "author_min": 2, "author_max": 40,
    "servings_max": 24, "minutes_max": 2880,
    "photo_max_bytes": 8 * 1024 * 1024,
}

DIETS = [
    {"value": "vegan",      "label": "Vegan"},
    {"value": "vegetarian", "label": "Végétarien"},
]

DISH_TYPES = [
    {"value": "starter",   "label": "Entrée"},
    {"value": "main",      "label": "Plat principal"},
    {"value": "side",      "label": "Accompagnement"},
    {"value": "soup",      "label": "Soupe / velouté"},
    {"value": "dessert",   "label": "Dessert"},
    {"value": "breakfast", "label": "Petit-déjeuner"},
    {"value": "snack",     "label": "En-cas / apéritif"},
    {"value": "bread",     "label": "Pain / viennoiserie"},
    {"value": "sauce",     "label": "Sauce / condiment"},
    {"value": "beverage",  "label": "Boisson"},
]

DIFFICULTIES = [
    {"value": "easy",   "label": "Facile"},
    {"value": "medium", "label": "Moyen"},
    {"value": "hard",   "label": "Difficile"},
]

CUISINES = [
    ("french", "Française"), ("italian", "Italienne"), ("spanish", "Espagnole"),
    ("greek", "Grecque"), ("levantine", "Libanaise / levantine"),
    ("moroccan", "Marocaine"), ("north_african", "Maghrébine"),
    ("turkish", "Turque"), ("persian", "Persane"), ("indian", "Indienne"),
    ("thai", "Thaïlandaise"), ("vietnamese", "Vietnamienne"),
    ("chinese", "Chinoise"), ("japanese", "Japonaise"), ("korean", "Coréenne"),
    ("indonesian", "Indonésienne"), ("mexican", "Mexicaine"),
    ("american", "Américaine"), ("brazilian", "Brésilienne"),
    ("peruvian", "Péruvienne"), ("caribbean", "Antillaise"),
    ("ethiopian", "Éthiopienne"), ("west_african", "Ouest-africaine"),
    ("german", "Allemande"), ("british", "Britannique"),
    ("eastern_european", "Europe de l'Est"), ("scandinavian", "Scandinave"),
    ("international", "Autre / du monde"),
]
_CUISINE_CODES = {c for c, _ in CUISINES}

# Unités proposées → (unité du moteur nutritionnel, libellé, libellé pluriel)
UNITS: dict[str, tuple[str, str, str]] = {
    "g":        ("g",       "g",            "g"),
    "kg":       ("kg",      "kg",           "kg"),
    "ml":       ("ml",      "ml",           "ml"),
    "cl":       ("cl",      "cl",           "cl"),
    "l":        ("l",       "l",            "l"),
    "tbsp":     ("tbsp",    "c. à soupe",   "c. à soupe"),
    "tsp":      ("tsp",     "c. à café",    "c. à café"),
    "pinch":    ("pinch",   "pincée",       "pincées"),
    "piece":    ("piece",   "pièce",        "pièces"),
    "gousse":   ("gousse",  "gousse",       "gousses"),
    "tranche":  ("tranche", "tranche",      "tranches"),
    "botte":    ("botte",   "botte",        "bottes"),
    "poignee":  ("poignee", "poignée",      "poignées"),
    "feuille":  ("feuille", "feuille",      "feuilles"),
    "brin":     ("brin",    "brin",         "brins"),
    "to_taste": ("pinch",   "selon le goût", "selon le goût"),
}
_LIQUID_UNITS = {"ml": 1.0, "cl": 10.0, "l": 1000.0}
_MASS_UNITS = {"g": 1.0, "kg": 1000.0}
_POIGNEE_G = 30.0
# Herbes : une feuille de sauge ou de basilic ≈ 0,5 g, un brin de thym ≈ 1 g
# (l'unité « pièce » du moteur compterait 100 g par feuille).
_SMALL_UNITS_G = {"feuille": 0.5, "brin": 1.0}

STATUSES = {
    "draft":             "Brouillon",
    "submitted":         "En relecture",
    "changes_requested": "À corriger",
    "published":         "Publiée",
    "rejected":          "Refusée",
}
EDITABLE_STATUSES = {"draft", "changes_requested"}

# Viande et poisson : le catalogue d'ingrédients n'en contient pas, mais un nom
# libre (ingrédient hors catalogue) ou une étape peut en mentionner.
_NON_VEG_WORDS = (
    "viande", "boeuf", "bœuf", "veau", "porc", "agneau", "mouton", "poulet",
    "volaille", "dinde", "canard", "lapin", "jambon", "lardon", "lardons",
    "bacon", "chorizo", "saucisse", "saucisson", "salami", "merguez", "steak",
    "foie gras", "gélatine", "gelatine", "poisson", "saumon", "thon", "cabillaud",
    "anchois", "sardine", "maquereau", "truite", "crevette", "crevettes",
    "moule", "moules", "calamar", "calamars", "seiche", "poulpe", "crabe",
    "homard", "langoustine", "fruits de mer", "nuoc mam", "nuoc-mâm",
    "sauce poisson", "sauce de poisson", "bouillon de volaille", "fond de veau",
    "bouillon de boeuf", "bouillon de bœuf", "saindoux", "graisse de canard",
    "chicken", "beef", "pork", "fish", "shrimp", "tuna", "salmon", "ham",
)
_NON_VEG_RE = re.compile(
    r"(?<![\w])(" + "|".join(re.escape(w) for w in sorted(_NON_VEG_WORDS, key=len, reverse=True)) + r")(?![\w])",
    re.IGNORECASE,
)
_LINK_RE = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)

# Pseudos qui feraient passer un membre pour l'équipe (revue de sécurité 2026-11-23)
_RESERVED_NAME_RE = re.compile(
    r"\b(alim|admin|administrat\w*|mod[ée]rat\w*|[ée]quipe|support|officiel\w*|staff)\b",
    re.IGNORECASE,
)


def is_reserved_name(name: str) -> bool:
    """Pseudo réservé (« ALIM », « Modération », « Équipe »…) ?"""
    return bool(_RESERVED_NAME_RE.search(name or ""))
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

ALLERGEN_LABELS = {
    "gluten": "Gluten", "milk": "Lait", "lactose": "Lactose", "eggs": "Œufs",
    "tree_nuts": "Fruits à coque", "peanuts": "Arachides", "soy": "Soja",
    "sesame": "Sésame", "celery": "Céleri", "mustard": "Moutarde",
    "sulphites": "Sulfites", "lupin": "Lupin", "fish": "Poisson",
    "crustaceans": "Crustacés", "molluscs": "Mollusques",
}


def options() -> dict:
    """Listes et bornes du formulaire, servies telles quelles au frontend."""
    return {
        "diets": DIETS,
        "dish_types": DISH_TYPES,
        "difficulties": DIFFICULTIES,
        "cuisines": [{"value": c, "label": l} for c, l in CUISINES],
        "units": [{"value": k, "label": v[1]} for k, v in UNITS.items()],
        "limits": LIMITS,
        "statuses": STATUSES,
    }


# ── Nettoyage du formulaire ───────────────────────────────────────────────────

def _text(value, max_len: int, multiline: bool = False) -> str:
    s = "" if value is None else str(value)
    s = _CTRL_RE.sub("", unicodedata.normalize("NFC", s))
    if multiline:
        s = re.sub(r"[ \t]+", " ", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
    else:
        s = re.sub(r"\s+", " ", s)
    return s.strip()[:max_len]


def _int(value, lo: int, hi: int, default: int | None = None) -> int | None:
    try:
        v = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, v))


def _qty(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        v = float(str(value).replace(",", "."))
    except ValueError:
        return None
    if v <= 0:
        return None
    return round(min(v, 100000.0), 3)


def is_known_ingredient(iid: str) -> bool:
    """Identifiant présent dans le catalogue servi par la recherche d'ingrédients."""
    from backend.services.ingredient_catalog import get_catalog
    global _KNOWN_IDS
    catalog = get_catalog()
    if _KNOWN_IDS is None or _KNOWN_IDS[0] is not catalog:
        _KNOWN_IDS = (catalog, {e["id"] for e in catalog})
    return iid in _KNOWN_IDS[1]


_KNOWN_IDS: tuple | None = None


def normalize(data: dict | None) -> dict:
    """Formulaire nettoyé : textes bornés, nombres dans leurs limites, listes tronquées."""
    d = data or {}
    L = LIMITS
    ings = []
    for raw in (d.get("ingredients") or [])[: L["ingredients_max"]]:
        if not isinstance(raw, dict):
            continue
        name = _text(raw.get("name"), L["ingredient_name_max"])
        iid = _text(raw.get("ingredient_id"), 120) or None
        if iid and not is_known_ingredient(iid):
            iid = None                  # id inconnu ou forgé : ingrédient à rattacher
        if not name and not iid:
            continue
        unit = raw.get("unit") if raw.get("unit") in UNITS else "g"
        ings.append({
            "name": name,
            "ingredient_id": iid,
            "quantity": None if unit == "to_taste" else _qty(raw.get("quantity")),
            "unit": unit,
            "note": _text(raw.get("note"), L["ingredient_note_max"]),
        })
    steps = [_text(s, L["step_max"], multiline=True) for s in (d.get("steps") or [])]
    steps = [s for s in steps if s][: L["steps_max"]]
    diet = d.get("diet") if d.get("diet") in {x["value"] for x in DIETS} else "vegetarian"
    dish = d.get("dish_type") if d.get("dish_type") in {x["value"] for x in DISH_TYPES} else ""
    diff = d.get("difficulty") if d.get("difficulty") in {x["value"] for x in DIFFICULTIES} else "easy"
    cuisine = d.get("cuisine") if d.get("cuisine") in _CUISINE_CODES else ""
    return {
        "title": _text(d.get("title"), L["title_max"]),
        "description": _text(d.get("description"), L["description_max"], multiline=True),
        "diet": diet,
        "dish_type": dish,
        "cuisine": cuisine,
        "difficulty": diff,
        "servings": _int(d.get("servings"), 1, L["servings_max"], 4),
        "prep_min": _int(d.get("prep_min"), 0, L["minutes_max"], 0),
        "cook_min": _int(d.get("cook_min"), 0, L["minutes_max"], 0),
        "rest_min": _int(d.get("rest_min"), 0, L["minutes_max"], 0),
        "ingredients": ings,
        "steps": steps,
        "tip": _text(d.get("tip"), L["tip_max"], multiline=True),
    }


# ── Saisie rapide : « 200 g de farine » ───────────────────────────────────────

_FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3}
_NUMBER_WORDS = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6,
    "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "douze": 12, "demi": 0.5,
    "demie": 0.5, "quelques": 3,
}
# (motif, unité) — les motifs les plus longs d'abord
_UNIT_PATTERNS: list[tuple[str, str]] = [
    (r"cuill[eè]res?\s+[àa]\s+soupe|c\.?\s*[àa]\s*s(?:oupe)?\.?|c\.?\s*s\.?|càs|cas", "tbsp"),
    (r"cuill[eè]res?\s+[àa]\s+caf[ée]|c\.?\s*[àa]\s*c(?:af[ée])?\.?|c\.?\s*c\.?|càc|cac", "tsp"),
    (r"kilos?|kilogrammes?|kg", "kg"),
    (r"grammes?|gr|g", "g"),
    (r"millilitres?|ml", "ml"),
    (r"centilitres?|cl", "cl"),
    (r"décilitres?|decilitres?|dl", "dl"),
    (r"litres?|l", "l"),
    (r"pinc[ée]es?", "pinch"),
    (r"gousses?", "gousse"),
    (r"tranches?", "tranche"),
    (r"bottes?|bouquets?", "botte"),
    (r"poign[ée]es?", "poignee"),
    (r"feuilles?", "feuille"),
    (r"brins?", "brin"),
    (r"pi[eè]ces?", "piece"),
]
_QTY_RE = r"(?P<qty>\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?|[½¼¾⅓⅔])(?:\s*(?:-|à)\s*(?P<qty2>\d+(?:[.,]\d+)?))?"
_LINE_RE = re.compile(
    r"^\s*" + _QTY_RE + r"\s*(?P<unit>" + "|".join(p for p, _ in _UNIT_PATTERNS) + r")?\.?(?=\s|$|\d)\s*(?P<rest>.*)$",
    re.IGNORECASE,
)
_TO_TASTE_RE = re.compile(r"\b(selon (le|votre) go[uû]t|à volonté|a volonte|qs|q\.s\.|facultatif)\b", re.IGNORECASE)
_PREP_WORDS = (
    "émincé", "émincée", "émincés", "émincées", "haché", "hachée", "hachés", "hachées",
    "râpé", "râpée", "râpés", "râpées", "coupé", "coupée", "coupés", "coupées",
    "pelé", "pelée", "pelés", "pelées", "en dés", "en rondelles", "en lamelles",
    "écrasé", "écrasée", "fondu", "fondue", "ciselé", "ciselée", "tranché", "tranchée",
    "concassé", "concassée", "égoutté", "égouttés", "égouttée", "égouttées",
    "rincé", "rincés", "rincée", "rincées", "trempé", "trempés",
)


def _parse_number(txt: str) -> float | None:
    txt = txt.strip()
    if txt in _FRACTIONS:
        return _FRACTIONS[txt]
    if "/" in txt:
        a, _, b = txt.partition("/")
        try:
            return float(a) / float(b)
        except (ValueError, ZeroDivisionError):
            return None
    try:
        return float(txt.replace(",", "."))
    except ValueError:
        return None


def _unit_code(raw: str | None) -> str | None:
    if not raw:
        return None
    for pat, code in _UNIT_PATTERNS:
        if re.fullmatch(pat, raw.strip().rstrip("."), re.IGNORECASE):
            return code
    return None


def _strip_article(name: str) -> str:
    return re.sub(r"^(de la |de l['’]|d['’]|de |des |du |la |le |les |l['’])", "", name.strip(), flags=re.IGNORECASE)


def parse_line(line: str) -> dict | None:
    """Une ligne de liste d'ingrédients → {name, quantity, unit, note}."""
    raw = _text(line, 200)
    raw = re.sub(r"^[-•*·–]\s*", "", raw)
    if not raw:
        return None
    note = ""
    m_par = re.search(r"\(([^)]*)\)", raw)
    if m_par:
        note = m_par.group(1).strip()
        raw = (raw[: m_par.start()] + raw[m_par.end():]).strip()
    to_taste = bool(_TO_TASTE_RE.search(raw))
    raw = _TO_TASTE_RE.sub("", raw).strip(" ,;")

    qty = None
    unit = None
    rest = raw
    words = raw.split(" ", 1)
    m = _LINE_RE.match(raw)
    if m:
        qty = _parse_number(m.group("qty"))
        if m.group("qty2") and qty is not None:
            q2 = _parse_number(m.group("qty2"))
            if q2:
                qty = (qty + q2) / 2
        unit = _unit_code(m.group("unit"))
        rest = m.group("rest")
    elif words and words[0].lower() in _NUMBER_WORDS:
        qty = float(_NUMBER_WORDS[words[0].lower()])
        rest = words[1] if len(words) > 1 else ""
        first = rest.split(" ", 1)
        maybe = _unit_code(first[0]) if first else None
        if maybe and maybe not in {"g", "l"}:      # « une gousse d'ail », pas « un l… »
            unit, rest = maybe, (first[1] if len(first) > 1 else "")

    if unit == "dl" and qty is not None:
        unit, qty = "ml", qty * 100
    if qty is not None and unit is None:
        unit = "piece"
    name = _strip_article(rest)
    # « 1 oignon, émincé » → note
    if "," in name:
        head, _, tail = name.partition(",")
        if tail.strip():
            note = (note + " " + tail.strip()).strip() if note else tail.strip()
        name = head.strip()
    else:
        for w in _PREP_WORDS:
            m2 = re.search(r"\s" + re.escape(w) + r"\b.*$", name, re.IGNORECASE)
            if m2:
                note = (note + " " + m2.group(0).strip()).strip() if note else m2.group(0).strip()
                name = name[: m2.start()].strip()
                break
    if not name:
        return None
    if to_taste and qty is None:
        unit = "to_taste"
    return {
        "name": name[: LIMITS["ingredient_name_max"]],
        "quantity": None if unit == "to_taste" else (round(qty, 3) if qty else None),
        "unit": unit or "to_taste",
        "note": note[: LIMITS["ingredient_note_max"]],
    }


def _pct(v: str) -> str:
    m = re.fullmatch(r"(sup|inf)?(\d+(?:[._]\d+)?)pct", v)
    if not m:
        return v
    num = m.group(2).replace("_", ",").replace(".", ",")
    return {"sup": "> ", "inf": "< "}.get(m.group(1) or "", "") + f"{num} % MG"


def ingredient_detail(iid: str) -> str:
    """Précision qui distingue deux ingrédients de même nom (« conserve, rincé »)."""
    from backend.db.culinary_repositories import IngredientRepository
    try:
        axes = (IngredientRepository().get_by_name(iid) or {}).get("axes_fr") or {}
    except Exception:
        return ""
    vals = [_pct(str(v)) for v in axes.values() if v and str(v) not in {"liquide", "entier"}]
    return ", ".join(vals)


def match_ingredient(name: str, limit: int = 5) -> list[dict]:
    """Suggestions du catalogue pour un nom saisi (le premier est le plus probable)."""
    from backend.services.ingredient_catalog import search
    if not name or _NON_VEG_RE.search(name):
        return []
    try:
        results = search(name, limit=limit)
    except Exception as e:  # le catalogue ne doit jamais casser la saisie
        logger.warning("match_ingredient(%r) : %s", name, e)
        return []
    return [{"id": r["id"], "name_fr": r["name_fr"], "detail": ingredient_detail(r["id"])} for r in results]


def parse_ingredient_lines(text: str) -> list[dict]:
    """Liste collée (une ligne par ingrédient) → lignes structurées avec suggestions."""
    out = []
    for line in str(text or "").splitlines()[: LIMITS["ingredients_max"]]:
        parsed = parse_line(line)
        if not parsed:
            continue
        candidates = match_ingredient(parsed["name"])
        parsed["candidates"] = candidates
        parsed["ingredient_id"] = candidates[0]["id"] if candidates else None
        parsed["non_vegetarian"] = bool(_NON_VEG_RE.search(parsed["name"]))
        out.append(parsed)
    return out


# ── Conversion des quantités vers le format du catalogue (g / ml) ─────────────

def _grams_per_unit(iid: str, unit: str) -> float:
    """Poids d'une unité (pièce, cuillère…) pour cet ingrédient, hors part non comestible."""
    from backend.engine import nutrition_engine as ne
    if unit == "poignee":
        return _POIGNEE_G
    if unit in _SMALL_UNITS_G:
        return _SMALL_UNITS_G[unit]
    engine_unit = UNITS.get(unit, ("g",))[0]
    try:
        g = ne._qty_to_g(iid, {"quantity": 1, "unit": engine_unit})
        edible = ne._physical_edible_pct(iid) or 1.0
        g = g / edible
    except Exception as e:
        logger.warning("conversion %s/%s impossible : %s", iid, unit, e)
        g = ne.UNIT_TO_G.get(engine_unit, 50.0)
    return float(g or 0)


def to_catalogue_quantity(iid: str, quantity: float | None, unit: str) -> tuple[float, str]:
    """(quantité, unité) saisies → (quantité, « g » | « ml ») comme dans recipes.json."""
    if unit == "to_taste" or not quantity:
        return (1.0 if unit == "to_taste" else 0.0), "g"
    if unit in _MASS_UNITS:
        return round(quantity * _MASS_UNITS[unit], 1), "g"
    if unit in _LIQUID_UNITS:
        return round(quantity * _LIQUID_UNITS[unit], 1), "ml"
    return round(quantity * _grams_per_unit(iid, unit), 1), "g"


def quantity_label(quantity: float | None, unit: str) -> str:
    """« 2 c. à soupe », « 1 pièce », « selon le goût » — pour l'aperçu et la modération."""
    if unit == "to_taste":
        return "selon le goût"
    if not quantity:
        return ""
    q = int(quantity) if float(quantity).is_integer() else round(quantity, 2)
    label = UNITS.get(unit, ("", unit, unit))
    return f"{str(q).replace('.', ',')} {label[2] if quantity > 1 else label[1]}"


# ── Construction de la recette du catalogue ───────────────────────────────────

def _slug(text: str, max_len: int = 40) -> str:
    t = unicodedata.normalize("NFD", text or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower()
    t = re.sub(r"[^a-z0-9]+", "_", t).strip("_")
    return (t[:max_len].rstrip("_")) or "recette"


def recipe_id_for(submission_id: str, title: str) -> str:
    h = hashlib.sha1(str(submission_id).encode()).hexdigest()[:6]
    return f"comm_{_slug(title)}_{h}"


def _role_for(iid: str) -> str:
    from backend.db.culinary_repositories import IngredientRepository
    try:
        item = IngredientRepository().get_by_name(iid) or {}
    except Exception:
        item = {}
    cat = str(item.get("category") or item.get("category_id") or "").lower()
    for key, role in (("spice", "spice"), ("herb", "herb"), ("oil", "fat"), ("fat", "fat"),
                      ("legume", "plant_protein"), ("tofu", "plant_protein"),
                      ("vegetable", "vegetable"), ("fruit", "fruit"),
                      ("cereal", "carbohydrate"), ("grain", "carbohydrate"),
                      ("dairy", "dairy"), ("sweet", "sweetener"), ("condiment", "condiment")):
        if key in cat:
            return role
    return "ingredient"


def build_recipe(data: dict, *, submission_id: str = "draft", author_name: str = "",
                 photo_url: str | None = None, published_at: str | None = None) -> dict:
    """Formulaire (normalisé) → recette au schéma de recipes.json.

    Les ingrédients non rattachés au catalogue ne figurent pas dans la
    composition (le moteur nutritionnel ne les connaît pas) : ils sont listés
    dans community.unmatched et bloquent la publication.
    """
    from backend.engine.rule_engine.diet import compute_diet_flags, allergen_tags
    from backend.engine.search_token_generator import generate_tokens

    d = normalize(data)
    composition, unmatched = [], []
    for ing in d["ingredients"]:
        iid = ing.get("ingredient_id")
        if not iid:
            unmatched.append(ing["name"])
            continue
        qty, unit = to_catalogue_quantity(iid, ing.get("quantity"), ing["unit"])
        composition.append({
            "ingredient": iid,
            "quantity": qty,
            "unit": unit,
            "meta": {
                "role": _role_for(iid),
                "form": "",
                "state": "",
                "preparation": ing.get("note", ""),
                "entered": quantity_label(ing.get("quantity"), ing["unit"]),
                "entered_name": ing.get("name", ""),
            },
        })

    prep, cook, rest = d["prep_min"] or 0, d["cook_min"] or 0, d["rest_min"] or 0
    title = d["title"] or "Recette sans titre"
    recipe = {
        "id": recipe_id_for(submission_id, title),
        "titles": {"original": title, "fr": title, "en": title},
        "origin": {"cuisine": d["cuisine"] or "international", "country": "", "region": "", "city": ""},
        "servings": d["servings"] or 4,
        "servings_default": d["servings"] or 4,
        "timing": {
            "prep_active_min": prep, "prep_passive_min": rest,
            "cook_min": cook, "total_min": prep + rest + cook,
        },
        "composition": composition,
        "tags": {"diet": [], "allergens": [], "technique": [], "process": []},
        "equipment": [],
        "result": {"texture": [], "taste": [], "visual": []},
        "metrics": {
            "total_weight_g": round(sum(c["quantity"] for c in composition)),
            "hydration_ratio": None,
        },
        "scoring": {"confidence": 0.7, "spice_level": 0,
                    "iconic": {"status": False, "score": 0, "tags": []}},
        "dish_type": d["dish_type"] or "main",
        "difficulty_level": d["difficulty"],
        "description": d["description"],
        "instructions": [f"Étape {i}: {s}" for i, s in enumerate(d["steps"], 1)],
        "community": {
            "author_name": author_name or "",
            "submission_id": str(submission_id),
            "declared_diet": d["diet"],
            "published_at": published_at,
            "unmatched": unmatched,
        },
    }
    if d["tip"]:
        recipe["_chef_note"] = d["tip"]
    if photo_url:
        recipe["image_url"] = photo_url
    try:
        recipe["tags"]["allergens"] = allergen_tags(recipe)
    except Exception as e:
        logger.warning("allergen_tags (contribution) : %s", e)
    try:
        recipe["diet_flags"] = compute_diet_flags(recipe)
    except Exception as e:
        logger.warning("compute_diet_flags (contribution) : %s", e)
        recipe["diet_flags"] = {}
    if d["diet"] == "vegan" and not recipe["diet_flags"].get("vegan"):
        recipe["tags"]["diet"] = []
    elif recipe["diet_flags"].get("vegan"):
        recipe["tags"]["diet"] = ["vegan"]
    try:
        recipe["search_tokens"] = generate_tokens(recipe)
    except Exception as e:
        logger.warning("generate_tokens (contribution) : %s", e)
        recipe["search_tokens"] = []
    return recipe


# ── Vérifications automatiques ────────────────────────────────────────────────

def _issue(level: str, field: str, message: str, **extra) -> dict:
    return {"level": level, "field": field, "message": message, **extra}


def _non_vegan_ingredients(d: dict) -> list[dict]:
    """Ingrédients rattachés au catalogue et d'origine animale (lait, œuf, miel…)."""
    from backend.engine.rule_engine.variants import _is_vegan_id, VEGAN_SUBS_CIQUAL
    from backend.services.ingredient_catalog import names_of
    found = []
    for idx, ing in enumerate(d["ingredients"]):
        iid = ing.get("ingredient_id")
        if not iid:
            continue
        try:
            vegan = _is_vegan_id(iid)
        except Exception:
            vegan = None
        if vegan is False:
            sub = VEGAN_SUBS_CIQUAL.get(iid)
            sub_name = names_of([sub]).get(sub) if sub else None
            found.append({
                "index": idx, "ingredient_id": iid, "name": ing.get("name") or iid,
                "substitute": {"id": sub, "name_fr": sub_name} if sub else None,
            })
    return found


_TITLE_STOP = {"aux", "les", "des", "une", "avec", "sans", "pour", "facon", "maison",
               "recette", "vegan", "vegetarien", "vegetarienne", "rapide", "facile"}


def _title_words(title: str) -> set[str]:
    from backend.engine.duplicate_recipe_detector import _normalize_title
    words = re.findall(r"[a-z0-9]+", _normalize_title(title or ""))
    return {w[:-1] if w.endswith("s") and len(w) > 4 else w
            for w in words if len(w) > 2 and w not in _TITLE_STOP}


def _similar_recipes(recipe: dict, limit: int = 3) -> list[dict]:
    """Recettes du catalogue proches : mêmes mots dans le titre, mêmes ingrédients."""
    from backend.core.data_io import load_recipes
    from backend.engine.duplicate_recipe_detector import _ingredient_set, _jaccard
    mine_ings = _ingredient_set(recipe)
    mine_words = _title_words(recipe["titles"]["fr"])
    if not mine_words and len(mine_ings) < 3:
        return []
    scored = []
    for r in load_recipes():
        if r.get("id") == recipe.get("id") or (r.get("community") or {}).get("submission_id") ==                 (recipe.get("community") or {}).get("submission_id"):
            continue
        words = _title_words((r.get("titles") or {}).get("fr", ""))
        overlap = len(mine_words & words) / len(mine_words) if mine_words else 0.0
        jac = _jaccard(mine_ings, _ingredient_set(r)) if len(mine_ings) >= 3 else 0.0
        score = 0.6 * overlap + 0.4 * jac
        if overlap >= 0.99 or jac >= 0.7 or score >= 0.6:
            reason = "titre proche" if overlap >= 0.99 else ("mêmes ingrédients" if jac >= 0.7 else "titre et ingrédients proches")
            scored.append((score, reason, r))
    scored.sort(key=lambda x: -x[0])
    return [{"id": r["id"], "title": (r.get("titles") or {}).get("fr", r["id"]), "reason": reason}
            for _, reason, r in scored[:limit]]


def _nutrition_summary(recipe: dict) -> dict:
    from backend.engine.nutrition_engine import compute_nutrition
    if not recipe["composition"]:
        return {}
    try:
        n = compute_nutrition(recipe)
    except Exception as e:
        logger.warning("compute_nutrition (contribution) : %s", e)
        return {}
    out = {k: round(float(n.get(k) or 0), 1) for k in ("calories", "protein", "carbs", "fat", "fiber", "sugar")}
    out["salt"] = round(float(n.get("sodium") or 0) * 0.00254, 2)
    return out


def analyze(data: dict, *, submission_id: str = "draft", author_name: str = "") -> dict:
    """Vérifications affichées pendant la saisie et à la modération.

    level :
      blocking → empêche l'envoi (complétude, viande/poisson, vegan non tenu)
      warning  → à vérifier (ingrédient hors catalogue, doublon possible, lien…)
      tip      → conseil (équilibre, aromates…), n'empêche rien
    """
    from backend.engine.rule_engine.validation import validate_recipe
    d = normalize(data)
    L = LIMITS
    recipe = build_recipe(d, submission_id=submission_id, author_name=author_name)
    issues: list[dict] = []

    # Complétude
    if len(d["title"]) < L["title_min"]:
        issues.append(_issue("blocking", "title", f"Donnez un titre d'au moins {L['title_min']} caractères."))
    if not d["dish_type"]:
        issues.append(_issue("blocking", "dish_type", "Choisissez le type de plat."))
    if len(d["ingredients"]) < L["ingredients_min"]:
        issues.append(_issue("blocking", "ingredients", f"Ajoutez au moins {L['ingredients_min']} ingrédients."))
    for i, ing in enumerate(d["ingredients"]):
        if ing["unit"] != "to_taste" and not ing["quantity"]:
            issues.append(_issue("blocking", f"ingredients.{i}",
                                 f"Indiquez la quantité de « {ing['name'] or ing['ingredient_id']} » "
                                 "(ou choisissez « selon le goût »)."))
    if len(d["steps"]) < L["steps_min"]:
        issues.append(_issue("blocking", "steps", f"Décrivez au moins {L['steps_min']} étapes."))
    if (d["prep_min"] or 0) + (d["cook_min"] or 0) <= 0:
        issues.append(_issue("blocking", "timing", "Indiquez le temps de préparation (et de cuisson s'il y en a)."))

    # 100 % végétarien
    texts = [("title", d["title"]), ("description", d["description"]), ("tip", d["tip"])]
    texts += [(f"ingredients.{i}", ing["name"]) for i, ing in enumerate(d["ingredients"])]
    for field, txt in texts:
        m = _NON_VEG_RE.search(txt or "")
        if m:
            issues.append(_issue("blocking", field,
                                 f"« {m.group(0)} » : ALIM ne publie que des recettes végétariennes "
                                 "(ni viande ni poisson)."))
    for i, step in enumerate(d["steps"]):
        m = _NON_VEG_RE.search(step)
        if m:
            issues.append(_issue("warning", f"steps.{i}",
                                 f"L'étape {i + 1} mentionne « {m.group(0)} » : vérifiez qu'il s'agit "
                                 "d'une version végétale."))

    # Régime annoncé
    non_vegan = _non_vegan_ingredients(d)
    detected_vegan = bool(recipe["diet_flags"].get("vegan")) and not non_vegan
    if d["diet"] == "vegan" and non_vegan:
        names = ", ".join(x["name"] for x in non_vegan)
        issues.append(_issue("blocking", "diet",
                             f"Recette annoncée vegan, mais ces ingrédients sont d'origine animale : {names}. "
                             "Remplacez-les ou annoncez-la végétarienne.",
                             ingredients=non_vegan))
    elif d["diet"] == "vegetarian" and detected_vegan and d["ingredients"]:
        issues.append(_issue("tip", "diet", "Aucun ingrédient d'origine animale : vous pouvez l'annoncer vegan."))

    # Rattachement au catalogue
    unmatched = recipe["community"]["unmatched"]
    for name in unmatched:
        if not _NON_VEG_RE.search(name):
            issues.append(_issue("warning", "ingredients",
                                 f"« {name} » n'est pas dans notre base d'ingrédients : choisissez une "
                                 "suggestion si possible. Sinon l'équipe le rattachera, et la nutrition "
                                 "ne le compte pas encore."))

    # Liens et cohérence
    all_text = " ".join([d["description"], d["tip"], *d["steps"]])
    if _LINK_RE.search(all_text):
        issues.append(_issue("warning", "steps", "Les liens vers d'autres sites ne sont pas publiés : retirez-les."))
    if d["steps"] and max(len(s) for s in d["steps"]) < 15:
        issues.append(_issue("tip", "steps", "Des étapes plus détaillées (gestes, temps, repères visuels) aident à réussir."))
    if not d["description"]:
        issues.append(_issue("tip", "description", "Une courte présentation donne envie : origine, goût, occasion."))

    similar = _similar_recipes(recipe)
    if similar:
        issues.append(_issue("warning", "title",
                             "Une recette proche existe déjà : précisez ce qui rend la vôtre différente.",
                             similar=similar))

    # Conseils culinaires du moteur de validation (jamais bloquants)
    if recipe["composition"]:
        try:
            v = validate_recipe(recipe)
            for viol in v.get("violations", []):
                if viol.get("code") in {"NO_PLANT_PROTEIN", "NO_AROMATIC"}:
                    issues.append(_issue("tip", "ingredients", f"{viol.get('message')} — {viol.get('suggestion', '')}".strip(" —")))
        except Exception as e:
            logger.warning("validate_recipe (contribution) : %s", e)

    allergens = sorted({ALLERGEN_LABELS.get(a, a) for a in recipe["tags"]["allergens"] if a != "lactose"})
    blocking = [x for x in issues if x["level"] == "blocking"]
    return {
        "ready": not blocking,
        "issues": issues,
        "diet": {
            "declared": d["diet"],
            "vegan": detected_vegan,
            "vegetarian": not any(_NON_VEG_RE.search(t or "") for _, t in texts),
            "non_vegan_ingredients": non_vegan,
        },
        "allergens": allergens,
        "nutrition": _nutrition_summary(recipe),
        "similar": similar,
        "unmatched": unmatched,
        "total_min": recipe["timing"]["total_min"],
        "recipe_id": recipe["id"],
    }


# ── Photo ─────────────────────────────────────────────────────────────────────

MAX_PHOTO_PIXELS = 40_000_000


def save_photo(raw: bytes, max_side: int = 1600) -> str:
    """Valide et ré-encode une photo (JPEG, ≤ max_side px, sans EXIF ni GPS).

    Returns: le jeton (nom de fichier sans extension).
    Raises: ValueError si le fichier n'est pas une image exploitable.
    """
    import warnings
    from PIL import Image, ImageOps, UnidentifiedImageError
    if not raw or len(raw) > LIMITS["photo_max_bytes"]:
        raise ValueError("Photo absente ou trop lourde (8 Mo maximum).")
    try:
        # Bombe de décompression : un PNG de quelques Mo peut décoder des
        # centaines de mégapixels (Pillow n'avertit qu'à partir de 89 Mpx).
        # Les dimensions sont lues avant tout décodage ; l'avertissement de
        # Pillow est traité comme une erreur (revue de sécurité 2026-11-23).
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as probe:
                if probe.width * probe.height > MAX_PHOTO_PIXELS:
                    raise ValueError("Photo trop grande : 40 mégapixels au plus.")
                probe.verify()
            img = Image.open(io.BytesIO(raw))
            if img.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Format accepté : JPEG, PNG ou WebP.")
            if img.width < 400 or img.height < 300:
                raise ValueError("Photo trop petite : 400 × 300 pixels au minimum.")
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((max_side, max_side))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError("Ce fichier n'est pas une image lisible.")
    token = secrets.token_hex(16)
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    img.save(PHOTO_DIR / f"{token}.jpg", "JPEG", quality=85, optimize=True, progressive=True)
    return token


def photo_path(token: str) -> Path | None:
    if not token or not re.fullmatch(r"[0-9a-f]{32}", token):
        return None
    p = PHOTO_DIR / f"{token}.jpg"
    return p if p.exists() else None


def delete_photo(token: str | None) -> None:
    p = photo_path(token or "")
    if p:
        try:
            p.unlink()
        except OSError as e:
            logger.warning("Suppression photo %s : %s", token, e)


def photo_url(token: str | None) -> str | None:
    return f"/contributions/photos/{token}.jpg" if token else None


# ── Fichier des recettes publiées ─────────────────────────────────────────────

def write_community_file(recipes: list[dict], path: Path | None = None) -> None:
    """Écrit les recettes publiées (écriture atomique : jamais de fichier à moitié écrit)."""
    path = path or COMMUNITY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_meta": {
            "description": "Recettes proposées par les utilisateurs et publiées après relecture. "
                           "Généré depuis la table recipe_submissions — ne pas modifier à la main.",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "count": len(recipes),
        },
        "recipes": recipes,
    }
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".community_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


__all__ = [
    "options", "normalize", "parse_line", "parse_ingredient_lines", "match_ingredient",
    "build_recipe", "analyze", "save_photo", "photo_path", "photo_url", "delete_photo",
    "write_community_file", "recipe_id_for", "quantity_label", "STATUSES",
    "EDITABLE_STATUSES", "COMMUNITY_PATH", "PHOTO_DIR",
]
