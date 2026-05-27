"""
sources/collector.py
Collecte des recettes depuis les sources supportées.

Sources :
  - mealdb    : TheMealDB API (filtre végétarien, gratuit, ~70 recettes)
  - wikibooks : Wikibooks Cookbook (stub — non implémenté)
  - recipenlg : RecipeNLG dataset parquet (nécessite pandas + pyarrow)

Format de sortie : liste de dicts compatibles engine/parser.parse_batch()
"""

from __future__ import annotations
import json
import logging
import time
import urllib.request
import urllib.error
from typing import Optional

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# MEALDB
# ═══════════════════════════════════════════════════════════════════════════════

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"
MEALDB_DELAY = 0.3   # politesse API (req/s)


def _mealdb_get(url: str) -> Optional[dict]:
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        log.warning(f"MealDB HTTP error [{url}]: {e}")
        return None


def _mealdb_list_vegetarian() -> list[dict]:
    data = _mealdb_get(f"{MEALDB_BASE}/filter.php?c=Vegetarian")
    return (data or {}).get("meals") or []


def _mealdb_fetch_detail(meal_id: str) -> Optional[dict]:
    data = _mealdb_get(f"{MEALDB_BASE}/lookup.php?i={meal_id}")
    meals = (data or {}).get("meals")
    return meals[0] if meals else None


def _mealdb_to_raw(meal: dict) -> dict:
    ingredients = []
    for i in range(1, 21):
        name    = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        if name:
            ingredients.append({"raw_name": name, "raw_measure": measure})

    return {
        "_source":          "mealdb",
        "title_en":         (meal.get("strMeal") or "").strip(),
        "title_fr":         "",
        "raw_id":           str(meal.get("idMeal", "")),
        "ingredients_raw":  ingredients,
        "instructions_raw": meal.get("strInstructions") or "",
        "area":             meal.get("strArea") or "",
        "tags_raw":         meal.get("strTags") or "",
    }


def collect_mealdb(max_recipes: int = 0) -> list[dict]:
    """Collecte les recettes végétariennes depuis TheMealDB."""
    log.info("MealDB — récupération liste végétarienne...")
    meals_list = _mealdb_list_vegetarian()
    if not meals_list:
        log.warning("MealDB — aucune recette trouvée (problème réseau ?)")
        return []

    if max_recipes:
        meals_list = meals_list[:max_recipes]

    log.info(f"MealDB — {len(meals_list)} repas à télécharger...")
    results = []
    for i, m in enumerate(meals_list):
        meal_id = m.get("idMeal")
        if not meal_id:
            continue
        detail = _mealdb_fetch_detail(str(meal_id))
        if detail:
            raw = _mealdb_to_raw(detail)
            if raw["title_en"] and raw["ingredients_raw"]:
                results.append(raw)
        if (i + 1) % 20 == 0:
            log.info(f"  MealDB — {i + 1}/{len(meals_list)} récupérés")
        time.sleep(MEALDB_DELAY)

    log.info(f"MealDB — {len(results)} recettes collectées")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# WIKIBOOKS (stub)
# ═══════════════════════════════════════════════════════════════════════════════

def collect_wikibooks(max_recipes: int = 100) -> list[dict]:
    """
    Collecte depuis Wikibooks Cookbook (en).
    Non implémenté — retourne une liste vide avec un avertissement.
    Nécessiterait beautifulsoup4 + scraping de la table des matières.
    """
    log.warning(
        "Wikibooks collector — non implémenté (0 recettes). "
        "Pour l'implémenter, scraper https://en.wikibooks.org/wiki/Cookbook "
        "avec beautifulsoup4 et remplir cette fonction."
    )
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# RECIPENLG (parquet / csv)
# ═══════════════════════════════════════════════════════════════════════════════

def collect_recipenlg(parquet_path: str, max_recipes: int = 0) -> list[dict]:
    """
    Charge les recettes depuis un fichier RecipeNLG (.parquet ou .csv).
    Nécessite : pip install pandas pyarrow
    """
    try:
        import pandas as pd
    except ImportError:
        log.error("RecipeNLG — 'pandas' requis : pip install pandas pyarrow")
        return []

    try:
        if parquet_path.endswith(".parquet"):
            df = pd.read_parquet(parquet_path)
        else:
            df = pd.read_csv(parquet_path)
    except Exception as e:
        log.error(f"RecipeNLG — lecture impossible ({parquet_path}): {e}")
        return []

    if max_recipes:
        df = df.head(max_recipes)

    results: list[dict] = []
    for _, row in df.iterrows():
        name = str(row.get("title") or "").strip()
        if not name:
            continue

        ner  = row.get("NER") or []
        ings = row.get("ingredients") or []
        raw_ings = ner if ner else ings

        ingredients = [
            {"raw_name": str(x).strip(), "raw_measure": ""}
            for x in raw_ings
            if str(x).strip()
        ]

        directions = row.get("directions") or []
        instr_text = (
            "\n".join(str(s) for s in directions)
            if isinstance(directions, list)
            else str(directions)
        )

        results.append({
            "_source":          "recipenlg",
            "title_en":         name,
            "title_fr":         "",
            "raw_id":           str(row.get("id", len(results))),
            "ingredients_raw":  ingredients,
            "instructions_raw": instr_text,
            "area":             "",
            "tags_raw":         "",
        })

    log.info(f"RecipeNLG — {len(results)} recettes chargées depuis {parquet_path}")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE UNIQUE
# ═══════════════════════════════════════════════════════════════════════════════

def collect_all(
    sources: list[str],
    wikibooks_max: int = 100,
    recipenlg_path: Optional[str] = None,
) -> list[dict]:
    """
    Collecte depuis toutes les sources activées.
    Retourne une liste de dicts bruts compatibles engine/parser.parse_batch().
    """
    all_raw: list[dict] = []

    for source in sources:
        if source == "mealdb":
            all_raw.extend(collect_mealdb())
        elif source == "wikibooks":
            all_raw.extend(collect_wikibooks(max_recipes=wikibooks_max))
        elif source == "recipenlg":
            if recipenlg_path:
                all_raw.extend(collect_recipenlg(recipenlg_path))
            else:
                log.warning("recipenlg sélectionné mais --recipenlg-path non fourni — ignoré")
        else:
            log.warning(f"Source inconnue ignorée : {source!r}")

    log.info(f"collect_all → {len(all_raw)} entrées brutes ({' + '.join(sources)})")
    return all_raw
