"""
core.py — Recherche principale + fusion multi-sources.

Corrections :
  - search_index exploité comme index inversé (token → [ids]) avec correspondance
    string/int pour compatibilité avec les deux formats d'IDs (migration CDC v4)
  - ings_text inclut désormais TOUS les champs textuels utiles : ingredient (EN),
    name (FR si présent), ingredient_id, et les search_tokens déjà bilinguaux
  - _MIN_STRUCTURED abaissé à 1 : fallback sémantique activé dès qu'il y a peu
    de résultats stricts (ex: "fondue" → 0 résultats exacts → TF-IDF)
  - score final non nul même sans hit titre : base_score depuis l'index inversé
  - Meilleur logging pour diagnostiquer les misses

API :
    search(query, limit, profile) → list[dict]
"""
from __future__ import annotations
import logging
import re
import math
from collections import Counter
from functools import lru_cache

logger = logging.getLogger(__name__)

_MIN_STRUCTURED = 1    # fallback sémantique si moins de 1 résultat strict
_W_STRUCTURED   = 0.70
_W_SEMANTIC     = 0.30


# ── Tokenisation ──────────────────────────────────────────────────────────────

_STOPWORDS = {"de", "du", "la", "le", "les", "au", "aux", "et", "en", "à", "avec", "sans",
              "un", "une", "des", "sur", "par", "pour", "dans", "the", "and", "of", "with"}

def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-záàâéèêëîïôùûüçœæ]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 2]


@lru_cache(maxsize=1)
def _recipes() -> list[dict]:
    from backend.db.data_access import get_data
    return get_data.recipes.list_all()


@lru_cache(maxsize=1)
def _search_index() -> dict:
    from backend.core.data_io import load_search_index
    return load_search_index() or {}


# ── Texte de recherche d'une recette ─────────────────────────────────────────

def _recipe_text(recipe: dict) -> tuple[str, str]:
    """
    Retourne (title_text, full_text) pour une recette.

    full_text inclut :
      - titre FR + titre original
      - search_tokens (bilingues par construction)
      - ingrédients : ingredient (EN) + name (FR si présent) + ingredient_id
    """
    title_fr   = recipe.get("titles", {}).get("fr", "").lower()
    title_orig = recipe.get("titles", {}).get("original", "").lower()

    tokens_text = " ".join(recipe.get("search_tokens", [])).lower()

    # Fix : ingrédients — on prend TOUS les champs textuels disponibles
    ing_parts = []
    for item in (recipe.get("composition") or []):
        if not isinstance(item, dict):
            ing_parts.append(str(item))
            continue
        # ingredient = nom EN (ex: "tomato")
        if item.get("ingredient"):
            ing_parts.append(str(item["ingredient"]))
        # name = nom FR si présent (ex: "tomate")
        if item.get("name"):
            ing_parts.append(str(item["name"]))
        # ingredient_id = clé snake_case (ex: "cherry_tomato")
        if item.get("ingredient_id"):
            ing_parts.append(str(item["ingredient_id"]).replace("_", " "))

    ings_text  = " ".join(ing_parts).lower()
    full_text  = f"{title_fr} {title_orig} {tokens_text} {ings_text}"
    return title_fr, full_text


# ── Usage correct du search_index (index inversé) ────────────────────────────

def _index_score(rid_str: str, terms: list[str]) -> float:
    """
    Calcule un score depuis l'index inversé {token → [ids]}.

    Compatibilité ID : l'index contient des IDs entiers (ancien schéma)
    et les recettes ont maintenant des IDs strings (CDC v4). On compare
    les deux représentations pour couvrir les deux cas.
    """
    index    = _search_index()
    tokens   = index.get("tokens", {})
    if not tokens or not terms:
        return 0.0

    hits = 0
    for term in terms:
        recipe_ids = tokens.get(term, [])
        if not recipe_ids:
            continue
        # Convertir rid_str en int si possible pour comparer avec les IDs entiers
        try:
            rid_int = int(rid_str)
        except (ValueError, TypeError):
            rid_int = None

        for rid in recipe_ids:
            if str(rid) == rid_str or (rid_int is not None and rid == rid_int):
                hits += 1
                break

    return hits / max(1, len(terms)) * 8.0   # max 8 points depuis l'index


# ── Recherche structurée ──────────────────────────────────────────────────────

def _structured_search(query: str, limit: int) -> list[dict]:
    """Recherche sur titre, ingrédients, tokens et index inversé."""
    if not query:
        return _recipes()[:limit]

    terms   = _tokenize(query)
    if not terms:
        return _recipes()[:limit]

    recipes = _recipes()
    results = []

    for recipe in recipes:
        rid = str(recipe.get("id", ""))

        title_fr, full_text = _recipe_text(recipe)

        # Score depuis l'index inversé (compatibilité int/string)
        idx_score   = _index_score(rid, terms)

        # Score depuis le texte direct
        hits        = sum(1 for t in terms if t in full_text)
        title_hits  = sum(2 for t in terms if t in title_fr)   # titre = double poids
        text_score  = (hits + title_hits) / max(1, len(terms)) * 10.0

        final = round(max(idx_score, text_score), 2)

        if final > 0:
            r = dict(recipe)
            r["_match_score"] = final
            r["_search_v3"]   = {"final_score": final, "engine": "structured"}
            results.append(r)

    results.sort(key=lambda x: x.get("_match_score", 0), reverse=True)

    if not results and query:
        logger.debug("structured_search: aucun résultat pour '%s' — fallback sémantique", query)

    return results[:limit]


# ── Recherche sémantique TF-IDF (fallback) ────────────────────────────────────

@lru_cache(maxsize=128)
def _tfidf_corpus() -> tuple[list[dict], dict]:
    """Construit le corpus TF-IDF une seule fois en mémoire."""
    recipes = _recipes()
    docs    = []
    df      = Counter()

    for recipe in recipes:
        title_fr, full_text = _recipe_text(recipe)
        tokens = _tokenize(full_text)
        tf = Counter(tokens)
        docs.append({"recipe": recipe, "tf": tf, "tokens": set(tokens)})
        df.update(set(tokens))

    n   = max(1, len(docs))
    idf = {term: math.log(n / (freq + 1)) for term, freq in df.items()}
    return docs, idf


def _semantic_search(query: str, limit: int) -> list[dict]:
    """TF-IDF cosine similarity sur le corpus de recettes."""
    if not query:
        return []
    docs, idf = _tfidf_corpus()
    q_tokens  = _tokenize(query)
    if not q_tokens:
        return []

    q_vec  = {t: idf.get(t, 0) for t in q_tokens}
    q_norm = math.sqrt(sum(v**2 for v in q_vec.values())) or 1.0

    scored = []
    for doc in docs:
        tf   = doc["tf"]
        norm = math.sqrt(sum((tf[t] * idf.get(t, 0))**2 for t in tf)) or 1.0
        sim  = sum(q_vec.get(t, 0) * tf[t] * idf.get(t, 0)
                   for t in q_tokens) / (q_norm * norm)
        if sim > 0:
            r = dict(doc["recipe"])
            r["_match_score"] = round(sim * 10, 2)
            r["_search_v3"]   = {"final_score": round(sim * 10, 2), "engine": "tfidf"}
            scored.append(r)

    scored.sort(key=lambda x: x["_match_score"], reverse=True)
    return scored[:limit]


# ── Fusion et dédoublonnage ───────────────────────────────────────────────────

def _merge(structured: list[dict], semantic: list[dict]) -> list[dict]:
    """Fusionne en dédoublonnant par id. Les résultats structurés ont priorité."""
    merged = {r["id"]: r for r in structured if "id" in r}
    for r in semantic:
        rid = r.get("id")
        if rid and rid not in merged:
            r["_match_score"] = round(r.get("_match_score", 0) * _W_SEMANTIC, 2)
            merged[rid] = r
    return list(merged.values())


# ── API publique ──────────────────────────────────────────────────────────────

def search(
    query:   str | None  = None,
    limit:   int         = 20,
    profile: dict | None = None,
) -> list[dict]:
    """
    Point d'entrée unique de recherche.

    Étapes :
        1. Recherche structurée (index inversé + texte FR/EN)
        2. Fallback sémantique TF-IDF si résultats insuffisants (< _MIN_STRUCTURED)
        3. Fusion + dédoublonnage + tri
    """
    q = (query or "").strip()

    structured = _structured_search(q, limit * 2)

    if len(structured) < _MIN_STRUCTURED and q:
        logger.debug("search: %d résultats structurés pour '%s' → fallback TF-IDF",
                     len(structured), q)
        semantic = _semantic_search(q, limit)
        combined = _merge(structured, semantic)
    else:
        combined = structured

    combined.sort(key=lambda x: x.get("_match_score", 0), reverse=True)

    if not combined and q:
        logger.info("search: aucun résultat pour '%s' (structured=%d, corpus size=%d)",
                    q, len(structured), len(_recipes()))

    return combined[:limit]
