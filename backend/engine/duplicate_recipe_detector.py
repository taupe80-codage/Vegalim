"""
duplicate_recipe_detector.py — Détection de doublons dans le dataset (CDC_04).

Combine :
  - Similarité Jaccard sur les ingrédients (≥ 0.85 → doublon probable)
  - Distance de Levenshtein sur les titres (≤ 5 → titre similaire)

Seuil composite : Jaccard ≥ 0.85 ET Levenshtein ≤ 5 → doublon confirmé.

API publique :
    find_duplicates(recipes, threshold)  → list[dict]
    is_duplicate(r1, r2, threshold)       → bool
    report(recipes)                       → dict
"""
import logging
from itertools import combinations

logger = logging.getLogger(__name__)

_DEFAULT_JACCARD    = 0.85
_DEFAULT_LEVENSHTEIN = 5


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ingredient_set(recipe: dict) -> set[str]:
    return {
        (i.get("ingredient_id", "") if isinstance(i, dict) else str(i)).lower()
        for i in recipe.get("ingredients", [])
    } - {""}


def _normalize_title(title: str) -> str:
    import unicodedata
    t = title.lower().strip()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    # Retirer les suffixes courants (Vegan), (Végétarien), etc.
    import re
    t = re.sub(r'\s*\([^)]*\)\s*', '', t).strip()
    return t


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _levenshtein(s1: str, s2: str) -> int:
    if len(s1) > 40 or len(s2) > 40:
        return abs(len(s1) - len(s2))
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if s1[i-1] == s2[j-1] else 1 + min(prev, dp[j], dp[j-1])
            prev = temp
    return dp[n]


# ── API publique ──────────────────────────────────────────────────────────────

def is_duplicate(r1: dict, r2: dict,
                 jaccard_threshold: float = _DEFAULT_JACCARD,
                 lev_threshold:     int   = _DEFAULT_LEVENSHTEIN) -> bool:
    """Retourne True si deux recettes sont considérées comme doublons."""
    ings1 = _ingredient_set(r1)
    ings2 = _ingredient_set(r2)
    jac   = _jaccard(ings1, ings2)
    if jac < jaccard_threshold:
        return False
    t1  = _normalize_title(r1.get("titles", {}).get("fr", "") or r1.get("titles", {}).get("original", ""))
    t2  = _normalize_title(r2.get("titles", {}).get("fr", "") or r2.get("titles", {}).get("original", ""))
    lev = _levenshtein(t1, t2)
    return lev <= lev_threshold


def find_duplicates(recipes: list[dict],
                    jaccard_threshold: float = _DEFAULT_JACCARD,
                    lev_threshold:     int   = _DEFAULT_LEVENSHTEIN) -> list[dict]:
    """
    Trouve tous les paires de doublons dans un dataset.

    Returns:
        list[{id_1, title_1, id_2, title_2, jaccard, levenshtein}]
    """
    pairs = []
    for r1, r2 in combinations(recipes, 2):
        ings1 = _ingredient_set(r1)
        ings2 = _ingredient_set(r2)
        jac   = _jaccard(ings1, ings2)
        if jac < jaccard_threshold:
            continue
        t1  = _normalize_title(r1.get("titles", {}).get("fr", "") or "")
        t2  = _normalize_title(r2.get("titles", {}).get("fr", "") or "")
        lev = _levenshtein(t1, t2)
        if lev <= lev_threshold:
            pairs.append({
                "id_1":        r1.get("id"),
                "title_1":     r1.get("titles", {}).get("fr", ""),
                "id_2":        r2.get("id"),
                "title_2":     r2.get("titles", {}).get("fr", ""),
                "jaccard":     round(jac, 3),
                "levenshtein": lev,
                "confidence":  "high" if jac >= 0.95 and lev <= 2 else "medium",
            })
    pairs.sort(key=lambda x: (-x["jaccard"], x["levenshtein"]))
    return pairs


def report(recipes: list[dict]) -> dict:
    """
    Génère un rapport de doublons pour tout le dataset.

    Returns:
        {total_pairs, high_confidence, medium_confidence, duplicates: list}
    """
    pairs = find_duplicates(recipes)
    high  = [p for p in pairs if p["confidence"] == "high"]
    med   = [p for p in pairs if p["confidence"] == "medium"]
    return {
        "total_recipes":    len(recipes),
        "duplicate_pairs":  len(pairs),
        "high_confidence":  len(high),
        "medium_confidence":len(med),
        "duplicates":       pairs,
    }
