"""
sources/collector.py
Collecte de recettes brutes depuis 3 sources gratuites :
  - TheMealDB API  (JSON REST, sans clé pour végétarien)
  - Wikibooks      (scraping HTML de Cookbook/)
  - RecipeNLG      (dataset HuggingFace, parquet local)

Sortie : liste de dicts "bruts" avec le champ _source renseigné.
Ces dicts sont ensuite passés au parser.py pour normalisation.
"""

from __future__ import annotations
import sys as _sys
import os as _os
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
import re
import time
import logging
import requests
from typing import Iterator
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS HTTP
# ═══════════════════════════════════════════════════════════════════════════════

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "ALIM-RecipeEngine/1.0 (research project; contact: alim@example.com)"
})

def _get(url: str, params: dict | None = None, retries: int = 3, delay: float = 1.0) -> dict | None:
    """GET JSON avec retry exponentiel."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt < retries - 1:
                wait = delay * (2 ** attempt)
                log.warning(f"GET {url} — retry {attempt+1}/{retries} dans {wait:.0f}s ({e})")
                time.sleep(wait)
            else:
                log.error(f"GET {url} — échec définitif: {e}")
    return None

def _get_html(url: str, retries: int = 3) -> BeautifulSoup | None:
    """GET HTML parsé."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                log.error(f"HTML {url} — échec: {e}")
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 1 — THEMEALDB
# ═══════════════════════════════════════════════════════════════════════════════

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"

# Catégories végétariennes disponibles sans clé
MEALDB_VEGGIE_CATEGORIES = [
    "Vegetarian", "Vegan", "Pasta", "Side", "Dessert",
    "Starter", "Breakfast", "Goat",  # Goat contient des plats levantins végé
]

def _mealdb_parse_raw(meal: dict) -> dict:
    """Extrait ingrédients + mesures des 20 champs TheMealDB."""
    ingredients = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        measure = (meal.get(f"strMeasure{i}") or "").strip()
        if name:
            ingredients.append({"raw_name": name, "raw_measure": measure})
    return {
        "_source": "mealdb",
        "raw_id": meal.get("idMeal", ""),
        "title_en": meal.get("strMeal", ""),
        "title_fr": "",   # sera rempli par le parser
        "category": meal.get("strCategory", ""),
        "area": meal.get("strArea", ""),
        "instructions_raw": meal.get("strInstructions", ""),
        "ingredients_raw": ingredients,
        "thumb_url": meal.get("strMealThumb", ""),
        "tags_raw": meal.get("strTags", "") or "",
        "youtube": meal.get("strYoutube", ""),
    }


def collect_mealdb(
    categories: list[str] | None = None,
    max_per_category: int = 50,
) -> list[dict]:
    """
    Collecte depuis TheMealDB.
    categories=None → utilise MEALDB_VEGGIE_CATEGORIES par défaut.
    """
    categories = categories or MEALDB_VEGGIE_CATEGORIES
    raw_recipes: list[dict] = []
    seen_ids: set[str] = set()

    for cat in categories:
        log.info(f"TheMealDB — catégorie: {cat}")
        data = _get(f"{MEALDB_BASE}/filter.php", params={"c": cat})
        if not data or not data.get("meals"):
            log.warning(f"Aucune recette pour catégorie {cat}")
            continue

        meals_summary = data["meals"][:max_per_category]
        for summary in meals_summary:
            mid = summary.get("idMeal")
            if mid in seen_ids:
                continue
            seen_ids.add(mid)

            # Récupération détaillée
            detail = _get(f"{MEALDB_BASE}/lookup.php", params={"i": mid})
            if detail and detail.get("meals"):
                raw_recipes.append(_mealdb_parse_raw(detail["meals"][0]))
            time.sleep(0.2)   # politesse API

    log.info(f"TheMealDB → {len(raw_recipes)} recettes brutes collectées")
    return raw_recipes


def collect_mealdb_by_ingredient(
    ingredient: str,
    max_results: int = 30,
) -> list[dict]:
    """Recherche TheMealDB par ingrédient principal."""
    data = _get(f"{MEALDB_BASE}/filter.php", params={"i": ingredient})
    if not data or not data.get("meals"):
        return []
    raw = []
    for summary in data["meals"][:max_results]:
        detail = _get(f"{MEALDB_BASE}/lookup.php", params={"i": summary["idMeal"]})
        if detail and detail.get("meals"):
            raw.append(_mealdb_parse_raw(detail["meals"][0]))
        time.sleep(0.2)
    return raw


def search_mealdb(query: str, max_results: int = 20) -> list[dict]:
    """Recherche TheMealDB par nom de recette."""
    data = _get(f"{MEALDB_BASE}/search.php", params={"s": query})
    if not data or not data.get("meals"):
        return []
    results = []
    for meal in (data["meals"] or [])[:max_results]:
        results.append(_mealdb_parse_raw(meal))
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 2 — WIKIBOOKS COOKBOOK
# ═══════════════════════════════════════════════════════════════════════════════

WIKIBOOKS_BASE = "https://en.wikibooks.org"
WIKIBOOKS_COOKBOOK_INDEX = f"{WIKIBOOKS_BASE}/wiki/Cookbook:Table_of_Contents"

def _wikibooks_recipe_links(index_url: str, max_links: int = 200) -> list[str]:
    """Extrait les liens de recettes depuis l'index Wikibooks Cookbook."""
    soup = _get_html(index_url)
    if not soup:
        return []

    links = []
    for a in soup.select("a[href^='/wiki/Cookbook:']"):
        href = a.get("href", "")
        # Exclure les pages de catégorie / navigation
        if any(x in href for x in ["Table_of_Contents", "Category:", "Help:", "Special:"]):
            continue
        full = WIKIBOOKS_BASE + href
        if full not in links:
            links.append(full)
        if len(links) >= max_links:
            break

    log.info(f"Wikibooks — {len(links)} liens trouvés")
    return links


def _wikibooks_parse_page(url: str) -> dict | None:
    """Parse une page de recette Wikibooks → dict brut."""
    soup = _get_html(url)
    if not soup:
        return None

    title_tag = soup.find("h1", {"id": "firstHeading"})
    title = title_tag.get_text(strip=True) if title_tag else ""
    title = re.sub(r"^Cookbook:", "", title).strip()

    if not title:
        return None

    # Instructions : contenu principal, paragraphes et listes
    content_div = soup.find("div", {"id": "mw-content-text"})
    if not content_div:
        return None

    # Ingrédients : souvent dans une liste avant les instructions
    ingredients_raw = []
    instructions_raw_parts = []

    in_ingredients = False
    in_procedure = False

    for tag in content_div.find_all(["h2", "h3", "ul", "ol", "p"]):
        text = tag.get_text(strip=True).lower()

        if tag.name in ("h2", "h3"):
            in_ingredients = "ingredient" in text
            in_procedure   = any(w in text for w in ("procedure", "method", "direction", "instruction", "step"))
            continue

        if in_ingredients and tag.name in ("ul", "ol"):
            for li in tag.find_all("li"):
                raw = li.get_text(strip=True)
                if raw:
                    ingredients_raw.append({"raw_name": raw, "raw_measure": ""})

        elif in_procedure and tag.name in ("ul", "ol"):
            for li in tag.find_all("li"):
                step = li.get_text(strip=True)
                if step:
                    instructions_raw_parts.append(step)

        elif in_procedure and tag.name == "p":
            txt = tag.get_text(strip=True)
            if txt:
                instructions_raw_parts.append(txt)

    if not ingredients_raw and not instructions_raw_parts:
        return None

    return {
        "_source": "wikibooks",
        "raw_id": url.split("/")[-1],
        "title_en": title,
        "title_fr": "",
        "category": "",
        "area": "",
        "instructions_raw": "\n".join(instructions_raw_parts),
        "ingredients_raw": ingredients_raw,
        "thumb_url": "",
        "tags_raw": "",
        "source_url": url,
    }


def collect_wikibooks(
    max_recipes: int = 100,
    categories_filter: list[str] | None = None,
) -> list[dict]:
    """
    Collecte depuis Wikibooks Cookbook.
    categories_filter : filtrer par mots-clés dans le titre (ex: ["vegan","vegetarian"]).
    """
    links = _wikibooks_recipe_links(WIKIBOOKS_COOKBOOK_INDEX, max_links=max_recipes * 3)

    raw_recipes: list[dict] = []
    for url in links:
        if len(raw_recipes) >= max_recipes:
            break

        # Filtre optionnel par catégorie
        if categories_filter:
            url_lower = url.lower()
            if not any(cat.lower() in url_lower for cat in categories_filter):
                continue

        recipe = _wikibooks_parse_page(url)
        if recipe:
            raw_recipes.append(recipe)
        time.sleep(0.5)   # politesse crawler

    log.info(f"Wikibooks → {len(raw_recipes)} recettes brutes collectées")
    return raw_recipes


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 3 — RECIPENLG (dataset HuggingFace, mode local)
# ═══════════════════════════════════════════════════════════════════════════════

def collect_recipenlg_local(
    parquet_path: str,
    max_recipes: int = 500,
    vegetarian_only: bool = True,
) -> list[dict]:
    """
    Charge le dataset RecipeNLG depuis un fichier parquet local.
    Téléchargement : https://huggingface.co/datasets/recipe_nlg
    Ou : huggingface-cli download recipe_nlg --repo-type dataset

    vegetarian_only : filtre heuristique sur les ingrédients.
    """
    try:
        import pandas as pd
    except ImportError:
        log.error("pip install pandas pyarrow  pour RecipeNLG")
        return []

    NON_VEGGIE_KW = {
        "chicken","beef","pork","lamb","veal","turkey","duck","bacon","ham",
        "salmon","tuna","shrimp","crab","lobster","anchovy","lard","gelatin",
        "meat","sausage","chorizo","pepperoni","prosciutto","venison",
    }

    try:
        df = pd.read_parquet(parquet_path)
    except Exception as e:
        log.error(f"Lecture RecipeNLG: {e}")
        return []

    raw_recipes = []
    for _, row in df.iterrows():
        if len(raw_recipes) >= max_recipes:
            break

        title    = str(row.get("title", ""))
        ner      = row.get("NER", [])          # liste d'ingrédients normalisés
        ingrs    = row.get("ingredients", [])  # liste avec mesures
        steps    = row.get("directions", [])

        if not title or not ingrs:
            continue

        # Filtre végétarien heuristique
        if vegetarian_only:
            ner_lower = " ".join(str(n).lower() for n in ner)
            if any(kw in ner_lower for kw in NON_VEGGIE_KW):
                continue

        ingredients_raw = []
        for line in ingrs:
            ingredients_raw.append({"raw_name": str(line), "raw_measure": ""})

        raw_recipes.append({
            "_source": "recipenlg",
            "raw_id": str(row.get("id", len(raw_recipes))),
            "title_en": title,
            "title_fr": "",
            "category": "",
            "area": "",
            "instructions_raw": "\n".join(str(s) for s in steps),
            "ingredients_raw": ingredients_raw,
            "thumb_url": str(row.get("image", "")),
            "tags_raw": "",
            "ner": [str(n) for n in ner],
        })

    log.info(f"RecipeNLG → {len(raw_recipes)} recettes brutes chargées")
    return raw_recipes


# ═══════════════════════════════════════════════════════════════════════════════
# INTERFACE UNIFIÉE
# ═══════════════════════════════════════════════════════════════════════════════

def collect_all(
    sources: list[str] | None = None,
    mealdb_categories: list[str] | None = None,
    wikibooks_max: int = 100,
    recipenlg_path: str | None = None,
    recipenlg_max: int = 500,
) -> list[dict]:
    """
    Point d'entrée unique : collecte depuis toutes les sources activées.
    sources = ["mealdb", "wikibooks", "recipenlg"] (ou sous-ensemble)
    """
    sources = sources or ["mealdb", "wikibooks"]
    all_raw: list[dict] = []

    if "mealdb" in sources:
        try:
            all_raw.extend(collect_mealdb(categories=mealdb_categories))
        except Exception as e:
            log.error(f"TheMealDB collect error: {e}")

    if "wikibooks" in sources:
        try:
            all_raw.extend(collect_wikibooks(max_recipes=wikibooks_max))
        except Exception as e:
            log.error(f"Wikibooks collect error: {e}")

    if "recipenlg" in sources and recipenlg_path:
        try:
            all_raw.extend(collect_recipenlg_local(recipenlg_path, max_recipes=recipenlg_max))
        except Exception as e:
            log.error(f"RecipeNLG collect error: {e}")

    log.info(f"collect_all → {len(all_raw)} recettes brutes au total")
    return all_raw