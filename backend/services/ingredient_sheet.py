"""
ingredient_sheet.py — Fiche d'un ingrédient (2026-11-26).

Tableaux pour 100 g (valeurs de la base source : Ciqual, Fichier canadien,
USDA), pourcentage des valeurs nutritionnelles de référence (VNR, règlement
UE 1169/2011), saison, prix, empreinte carbone, allergènes, régimes,
remplacements et recettes qui l'utilisent. Sert la page de l'application
(GET /ingredients/{id}/fiche) et la page publique /ingredient/<slug>.

Corrections proposées par les membres et acceptées par la modération
(source à l'appui) : backend/data/ingredients/ingredient_corrections.json,
appliquées par-dessus la base (culinary_repositories.resolve_nutrition) sans
la réécrire ; la fiche les signale.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[2]
CORRECTIONS_PATH = _ROOT / "backend" / "data" / "ingredients" / "ingredient_corrections.json"

# ── Tableau nutritionnel ─────────────────────────────────────────────────────
# (clé de la base, libellé, unité, VNR pour 100 % ; None : pas de référence)
# VNR : règlement (UE) n° 1169/2011, annexe XIII ; fibres : repère ANSES (30 g).
NUTRIENT_GROUPS: list[tuple[str, list[tuple[str, str, str, float | None]]]] = [
    ("Énergie et macronutriments", [
        ("calories_kcal", "Énergie", "kcal", 2000),
        ("protein_g", "Protéines", "g", 50),
        ("carbs_g", "Glucides", "g", 260),
        ("sugar_g", "dont sucres", "g", 90),
        ("fiber_g", "Fibres", "g", 30),
        ("fat_g", "Lipides", "g", 70),
        ("fa_saturated_g", "dont acides gras saturés", "g", 20),
        ("fa_mufa_g", "dont mono-insaturés", "g", None),
        ("fa_pufa_g", "dont poly-insaturés", "g", None),
        ("omega3_g", "dont oméga-3 (ALA)", "g", None),
        ("salt_g", "Sel", "g", 6),
        ("water_g", "Eau", "g", None),
    ]),
    ("Minéraux", [
        ("calcium_mg", "Calcium", "mg", 800),
        ("iron_mg", "Fer", "mg", 14),
        ("magnesium_mg", "Magnésium", "mg", 375),
        ("phosphorus_mg", "Phosphore", "mg", 700),
        ("potassium_mg", "Potassium", "mg", 2000),
        ("sodium_mg", "Sodium", "mg", None),
        ("zinc_mg", "Zinc", "mg", 10),
        ("copper_mg", "Cuivre", "mg", 1),
        ("manganese_mg", "Manganèse", "mg", 2),
        ("selenium_ug", "Sélénium", "µg", 55),
        ("iodine_ug", "Iode", "µg", 150),
    ]),
    ("Vitamines", [
        ("vitamin_a_rae_ug", "Vitamine A", "µg", 800),
        ("beta_carotene_ug", "dont bêta-carotène", "µg", None),
        ("vitamin_d_ug", "Vitamine D", "µg", 5),
        ("alpha_tocopherol_mg", "Vitamine E", "mg", 12),
        ("vitamin_k1_ug", "Vitamine K", "µg", 75),
        ("vitamin_c_mg", "Vitamine C", "mg", 80),
        ("vitamin_b1_mg", "Vitamine B1 (thiamine)", "mg", 1.1),
        ("vitamin_b2_mg", "Vitamine B2 (riboflavine)", "mg", 1.4),
        ("vitamin_b3_mg", "Vitamine B3 (niacine)", "mg", 16),
        ("vitamin_b5_mg", "Vitamine B5", "mg", 6),
        ("vitamin_b6_mg", "Vitamine B6", "mg", 1.4),
        ("folate_dfe_ug", "Folates (B9)", "µg", 200),
        ("vitamin_b12_ug", "Vitamine B12", "µg", 2.5),
    ]),
]
NUTRIENTS = {k: (label, unit, vnr) for _, rows in NUTRIENT_GROUPS for k, label, unit, vnr in rows}

SOURCES = {
    "CIQUAL": ("Table Ciqual (Anses)", "https://ciqual.anses.fr/#/aliments/{id}"),
    "CNF": ("Fichier canadien sur les éléments nutritifs (Santé Canada)",
            "https://food-nutrition.canada.ca/cnf-fce/foodDetails?id={id}"),
    "USDA": ("FoodData Central (USDA)", "https://fdc.nal.usda.gov/food-details/{id}/nutrients"),
    "MANUAL": ("Valeurs établies par ALIM (étiquettes et recoupements)", None),
}

ALLERGENS_FR = {
    "cereals_gluten": "Gluten", "gluten": "Gluten", "milk": "Lait", "eggs": "Œufs",
    "tree_nuts": "Fruits à coque", "peanuts": "Arachides", "soybeans": "Soja", "soy": "Soja",
    "sesame": "Sésame", "celery": "Céleri", "mustard": "Moutarde", "sulphites": "Sulfites",
    "lupin": "Lupin",
}
DIETS_FR = [("vegan", "Vegan"), ("gluten_free", "Sans gluten"), ("lactose_free", "Sans lactose"),
            ("nut_free", "Sans fruits à coque"), ("soy_free", "Sans soja"), ("egg_free", "Sans œufs")]
MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
             "septembre", "octobre", "novembre", "décembre"]
MIN_RECIPES_FOR_PUBLIC_PAGE = 3
NO_PUBLIC_PAGE = {"water"}          # rien à dire pour 100 g


# ── Corrections acceptées ────────────────────────────────────────────────────

_corr_lock = threading.Lock()
_corr_cache: dict = {"sig": None, "data": {}}


def load_corrections() -> dict:
    """{ingredient_id: {"source_id": …, "fields": {clé: {value, previous, source, url, date}}}}."""
    try:
        st = os.stat(CORRECTIONS_PATH)
        sig = (st.st_mtime_ns, st.st_size)
    except OSError:
        return {}
    with _corr_lock:
        if _corr_cache["sig"] != sig:
            try:
                data = json.loads(CORRECTIONS_PATH.read_text(encoding="utf-8"))
                _corr_cache["data"] = data.get("corrections", {}) if isinstance(data, dict) else {}
            except (OSError, ValueError):
                logger.warning("ingredient_corrections.json illisible : ignoré")
                _corr_cache["data"] = {}
            _corr_cache["sig"] = sig
        return _corr_cache["data"]


def apply_corrections(iid: str, n_data: dict | None) -> dict | None:
    """Valeurs corrigées de l'ingrédient, seulement pour la fiche de la base
    qui a été corrigée (même code source : pas la version cuite)."""
    if not n_data:
        return n_data
    corr = load_corrections().get(iid)
    if not corr or str(n_data.get("_source_id")) != str(corr.get("source_id")):
        return n_data
    out = dict(n_data)
    for key, c in (corr.get("fields") or {}).items():
        out[key] = c["value"]
        if key == "sodium_mg":
            out["salt_g"] = round(c["value"] * 2.54 / 1000, 3)
        if key == "salt_g":
            out["sodium_mg"] = round(c["value"] / 2.54 * 1000, 1)
    out["_corrected"] = sorted((corr.get("fields") or {}).keys())
    return out


def write_corrections(rows: list[dict]) -> None:
    """Réécrit le fichier depuis les corrections acceptées (la base de données
    reste la référence) ; écriture atomique."""
    data: dict = {}
    for r in sorted(rows, key=lambda r: r["reviewed_at"] or ""):
        e = data.setdefault(r["ingredient_id"], {"source_id": r["source_id"], "fields": {}})
        e["fields"][r["field"]] = {"value": r["proposed_value"], "previous": r["current_value"],
                                   "source": r["source_ref"], "url": r["source_url"],
                                   "date": (r["reviewed_at"] or "")[:10], "id": r["id"]}
    CORRECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CORRECTIONS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps({"_meta": {
        "description": "Corrections des valeurs nutritionnelles proposées par les membres, "
                       "source à l'appui, acceptées par la modération (table ingredient_corrections).",
    }, "corrections": data}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, CORRECTIONS_PATH)


# ── Données de la fiche ───────────────────────────────────────────────────────

def raw_nutrition(iid: str) -> dict | None:
    """Fiche de la base pour 100 g, ingrédient cru / tel qu'acheté (corrections comprises)."""
    from backend.db.data_access import get_data
    try:
        return get_data.ingredients.resolve_nutrition(iid, use_cooked=False, cooking_state=None)
    except Exception:
        logger.debug("raw_nutrition %s", iid, exc_info=True)
        return None


def _fmt_num(v: float) -> float:
    if v >= 100:
        return round(v)
    if v >= 10:
        return round(v, 1)
    if v >= 1:
        return round(v, 2)
    return round(v, 3)


def nutrition_table(n: dict | None) -> list[dict]:
    corrected = set((n or {}).get("_corrected") or [])
    groups = []
    for title, rows in NUTRIENT_GROUPS:
        out = []
        for key, label, unit, vnr in rows:
            v = (n or {}).get(key)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                out.append({"key": key, "label": label, "unit": unit, "value": None, "pct": None})
                continue
            out.append({"key": key, "label": label, "unit": unit, "value": _fmt_num(float(v)),
                        "pct": round(float(v) / vnr * 100) if vnr else None,
                        **({"corrected": True} if key in corrected else {})})
        groups.append({"title": title, "rows": out})
    return groups


def source_info(iid: str, n: dict | None, entry: dict) -> dict:
    src = str((n or {}).get("_source") or entry.get("source") or "MANUAL").upper()
    sid = (n or {}).get("_source_id") or entry.get("source_id")
    name, url = SOURCES.get(src, (src, None))
    return {"code": src, "name": name, "id": str(sid) if sid else None,
            "label": entry.get("source_label") or (n or {}).get("name_fr"),
            "url": url.format(id=sid) if url and sid else None}


def season_info(iid: str) -> dict | None:
    from backend.engine.rule_engine.seasonality import _db, season_key
    key = season_key(iid)
    months = ((_db().get(key) or {}).get("months") or []) if key else []
    if not months:
        return None
    now = datetime.date.today().month
    return {"months": months, "in_season": now in months,
            "label": ", ".join(MONTHS_FR[m - 1] for m in sorted(months))}


def price_info(iid: str) -> dict | None:
    from backend.core.data_io import load_prices_catalog, resolve_catalog_key
    from backend.engine.planning_engine.shopping import recipe_cost
    try:
        cost = recipe_cost({"id": f"_ing_{iid}", "servings": 1,
                            "composition": [{"ingredient": iid, "quantity": 1000, "unit": "g", "meta": {}}]})
    except Exception:
        return None
    if cost.get("unknown") or not cost.get("total_eur"):
        return None
    catalog = load_prices_catalog()
    key = resolve_catalog_key(iid, catalog)
    entry = catalog.get(key) or {}
    pkg = (entry.get("packages") or [{}])[0]
    src = str(entry.get("price_source") or "")
    return {"per_kg_eur": round(float(cost["total_eur"]), 2),
            "package": f"{pkg.get('label')} : {float(pkg['price']):.2f} €".replace(".", ",") if pkg.get("price") else None,
            "estimated": src.startswith(("estimation", "analogie")),
            "updated": entry.get("last_updated")}


def carbon_info(iid: str) -> dict | None:
    from backend.core.data_io import resolve_catalog_key
    from backend.engine.rule_engine.carbon import _carbon_db, _co2_per_100g, _seasonal_db
    db = _carbon_db()
    key = resolve_catalog_key(iid, db)
    if not key:
        return None
    per_kg = _co2_per_100g(db[key]) * 10
    # repères par kilo (Agribalyse) : légumes, céréales < 1,5 ; fromages, chocolat > 5
    label = "🟢 Faible" if per_kg < 1.5 else "🟡 Moyenne" if per_kg < 5 else "🔴 Élevée"
    out = {"kg_co2_per_kg": round(per_kg, 2), "label": label}
    seasonal = _seasonal_db().get(key)
    if seasonal:
        out["in_season_kg"] = round(float(seasonal["de_saison"]) * 10, 2)
        out["off_season_kg"] = round(float(seasonal["hors_saison"]) * 10, 2)
    return out


def _recipes_using(iid: str) -> list[dict]:
    from backend.core.data_io import load_catalogue_recipes
    out = []
    for r in load_catalogue_recipes():
        lines = [c for c in r.get("composition") or [] if isinstance(c, dict) and c.get("ingredient") == iid]
        if not lines:
            continue
        core = [c for c in lines if (c.get("meta") or {}).get("role") != "serving_suggestion"]
        out.append({"id": r["id"], "title": (r.get("titles") or {}).get("fr") or r["id"],
                    "vegan": bool((r.get("diet_flags") or {}).get("vegan")),
                    "main": any((c.get("meta") or {}).get("role") in ("base", "protein", "main") for c in core),
                    "iconic": ((r.get("scoring") or {}).get("iconic") or {}).get("score") or 0})
    out.sort(key=lambda x: (not x["main"], -x["iconic"], x["title"]))
    return out


def display_name(iid: str) -> str:
    from backend.services.recipe_edits import display_name as dn
    n = dn(iid)
    return n[:1].upper() + n[1:]


def public_slug(iid: str) -> str:
    from backend.services.seo_pages import slugify
    return slugify(display_name(iid))


def sheet(iid: str, *, with_recipes: int = 24) -> dict | None:
    """Fiche complète, ou None si l'ingrédient est inconnu."""
    from backend.core.data_io import load_availability_graph, load_ingredients_dict
    from backend.engine.planning_engine.shopping import aisle_of
    entry = load_ingredients_dict().get(iid)
    if not entry:
        return None
    n = raw_nutrition(iid)
    dp = entry.get("diet_profile") or {}
    recipes = _recipes_using(iid)
    try:
        from backend.services.recipe_edits import replacement_suggestions
        repl = replacement_suggestions(iid, limit=8)
    except Exception:
        logger.debug("remplacements %s", iid, exc_info=True)
        repl = []
    corr = (load_corrections().get(iid) or {}).get("fields") or {}
    kcal = (n or {}).get("calories_kcal")
    return {
        "id": iid,
        "name_fr": display_name(iid),
        "name_en": entry.get("canonical_name_en"),
        "slug": public_slug(iid),
        "public_page": len(recipes) >= MIN_RECIPES_FOR_PUBLIC_PAGE and iid not in NO_PUBLIC_PAGE,
        "source": source_info(iid, n, entry),
        "nutrition": nutrition_table(n),
        "nutrition_per_100g": {k: (n or {}).get(k) for k in NUTRIENTS if isinstance((n or {}).get(k), (int, float))},
        "kcal_100g": round(kcal) if isinstance(kcal, (int, float)) else None,
        "allergens": sorted({ALLERGENS_FR.get(a, a) for a in entry.get("allergens_eu") or []}),
        "diets": [label for key, label in DIETS_FR if dp.get(key) is True],
        "nova_group": entry.get("nova_group"),
        "aisle": aisle_of(iid),
        "available_in_france": (load_availability_graph().get(iid) or {}).get("available_in_france", True),
        "season": season_info(iid),
        "price": price_info(iid),
        "carbon": carbon_info(iid),
        "replacements": repl,
        "recipes_count": len(recipes),
        "recipes": recipes[:with_recipes],
        "corrections": [{"field": k, "label": (NUTRIENTS.get(k) or (k,))[0], "unit": (NUTRIENTS.get(k) or ("", ""))[1],
                         **v} for k, v in corr.items()],
    }


def public_ingredients() -> dict[str, str]:
    """{slug: id} des ingrédients qui ont une page publique (≥ 3 recettes du
    catalogue) ; à nom égal, le plus utilisé."""
    from backend.core.data_io import load_catalogue_recipes, load_ingredients_dict
    from collections import Counter
    d = load_ingredients_dict()
    counts: Counter = Counter()
    for r in load_catalogue_recipes():
        for iid in {c.get("ingredient") for c in r.get("composition") or [] if isinstance(c, dict)}:
            if iid in d:
                counts[iid] += 1
    out: dict[str, tuple[int, str]] = {}
    for iid, n in counts.items():
        if n < MIN_RECIPES_FOR_PUBLIC_PAGE or iid in NO_PUBLIC_PAGE:
            continue
        slug = public_slug(iid)
        if slug and (slug not in out or n > out[slug][0]):
            out[slug] = (n, iid)
    return {slug: iid for slug, (_, iid) in out.items()}
