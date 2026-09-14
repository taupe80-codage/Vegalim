"""
Search Engine v4.3
===================
Moteur de recherche standalone — filtres contextuels étendus (Point 8).

Correctifs v4.3 (vs v4.2) :
  - BUG 11 : CLI smoke test étendu — flags --cycle, --astro, --moon, --limit
  - BUG 12 : active_context sorti de chaque recette ; search() retourne désormais
             {"results": list[dict], "context": dict} au lieu de list[dict]
  - BUG 13 : repli IDF-aware pour tokens stop — tri par IDF décroissant et garde
             max 3 tokens les plus discriminants (au lieu de relancer sur tout)

Correctifs v4.2 (inchangés) :
  - BUG 10 : _fuzzy_threshold plafonne à 3 pour les mots >= 9 chars

Correctifs v4.1 (vs v4.0) :
  - BUG 1  : paramètre `query` accepté en alias de `query_text` (compat orchestrateur)
  - BUG 2  : chemins par défaut via DATA_ROOT (config.py) — plus de FileNotFoundError
  - BUG 3  : recettes chargées via data_io.load_recipes() quand non injectées
  - BUG 5  : `titles.fr` + `title_fr` + `title_original` tous cherchés pour le fuzzy
  - BUG 6  : `month` déduit automatiquement depuis datetime si absent
  - BUG ID : IDs recettes gérés en int ET string (CDC v4 format)

Améliorations v4.2 — Filtres & scoring contextuels (Point 8) :
  A — Filtres directs (exclusion avant scoring) :
    A1 : allergen_exclude    — liste d'allergènes à exclure (tags.allergens)
    A2 : dish_type           — type de plat (main, soup, dessert, breakfast…)
    A3 : max_spice           — niveau d'épices max 0–3 (scoring.spice_level)
    A4 : health_tags         — tags santé étendus (diabetes_friendly, high_protein,
                               kid_friendly, low_calorie, raw…)
  B — Bonus contextuels (influence scoring, n'exclut pas) :
    B1 : cycle_phase         — phase du cycle menstruel (menstrual|follicular|
                               ovulatory|luteal) → bonus/malus via female_cycle_nutrition
    B2 : astro_element       — élément astrologique (Feu|Air|Terre|Eau) → bonus
                               proportionnel via astro_nutrition ingredients_astro_map
    B3 : moon_phase          — phase lunaire (nouvelle_lune|pleine_lune|
                               premier_quartier|dernier_quartier) → bonus proportionnel
  C — Profil utilisateur global :
    C  : user_profile        — dict de préférences persistantes appliquées en fond
                               {diet, allergens, cycle_phase, max_spice, health_tags,
                                astro_element, moon_phase, dish_type}

Améliorations v4.1 (inchangées) :
  - Mode dual : recherche directe ET recommandations (requête vide)
  - Recommandation : recette du jour → nouveautés → populaires → aléatoire
  - Section `_similar` dans les résultats (sous-propositions thématiques)
  - Scoring ingrédients pondéré par position (ingrédient principal > secondaire)
  - Fallback texte pour recettes hors index (titres + tags + cuisine)
  - Boost saisonnier activable via month
  - Filtres combinés en une passe (diet, difficulty, max_time, cuisine)
  - Tolérance orthographique (Levenshtein adaptatif)
  - FR→EN via mapping intégré
"""

from __future__ import annotations
import logging
logger = logging.getLogger(__name__)

import datetime
import json
import math
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

# ── Chemins par défaut via DATA_ROOT ──────────────────────────────────────────
# Priorité : variable d'env > DATA_ROOT (config.py) > fallback relatif
def _default_index_path() -> str:
    if os.environ.get("SEARCH_INDEX_PATH"):
        return os.environ["SEARCH_INDEX_PATH"]
    try:
        from backend.engine.config import DATA_ROOT
        return str(DATA_ROOT / "indexes" / "search_index.json")
    except Exception:
        return str(Path(__file__).resolve().parents[3] / "data" / "indexes" / "search_index.json")


def _default_mapping_path() -> str:
    if os.environ.get("FR_EN_MAPPING_PATH"):
        return os.environ["FR_EN_MAPPING_PATH"]
    try:
        from backend.engine.config import DATA_ROOT
        return str(DATA_ROOT / "ingredients" / "fr_to_en_mapping.json")
    except Exception:
        return str(Path(__file__).resolve().parents[3] / "data" / "ingredients" / "fr_to_en_mapping.json")


def _default_cycle_path() -> str:
    if os.environ.get("CYCLE_NUTRITION_PATH"):
        return os.environ["CYCLE_NUTRITION_PATH"]
    try:
        from backend.engine.config import DATA_ROOT
        return str(DATA_ROOT / "modules" / "female_cycle_nutrition.json")
    except Exception:
        p = Path(__file__).resolve()
        parents = p.parents
        # Remonte jusqu'à 4 niveaux, prend le plus haut disponible
        root = parents[min(3, len(parents) - 1)]
        return str(root / "data" / "modules" / "female_cycle_nutrition.json")


def _default_astro_path() -> str:
    if os.environ.get("ASTRO_NUTRITION_PATH"):
        return os.environ["ASTRO_NUTRITION_PATH"]
    try:
        from backend.engine.config import DATA_ROOT
        return str(DATA_ROOT / "modules" / "astro_nutrition.json")
    except Exception:
        p = Path(__file__).resolve()
        parents = p.parents
        root = parents[min(3, len(parents) - 1)]
        return str(root / "data" / "modules" / "astro_nutrition.json")


# Seuil IDF : token ignoré si couvre > X% du corpus (stop-words culinaires)
_IDF_STOP_RATIO = 0.60

# Seuil Levenshtein selon la longueur du token
def _fuzzy_threshold(n: int) -> int:
    # BUG 10 FIX : les mots longs (>= 9 chars) tolerent une distance 3
    # au lieu de 2 — couvre les variantes de noms composes comme
    # "courgette" (9), "pamplemousse" (12), "ratatouille" (11), etc.
    if n <= 3:  return 0
    if n <= 5:  return 1
    if n <= 8:  return 2
    return 3


# ═══════════════════════════════════════════════════════════════════════════════
# Utilitaires texte
# ═══════════════════════════════════════════════════════════════════════════════

def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _normalize_token(t: str) -> str:
    return _strip_accents(t.lower().strip())


def _tokenize(text: str) -> list[str]:
    """Découpe un texte en tokens normalisés (min 2 chars)."""
    raw = re.split(r"[\s,;/|+\-–'\"]+", text.strip())
    return [_normalize_token(t) for t in raw if len(t.strip()) >= 2]


def _get_title(recipe: dict) -> str:
    """Extrait le titre FR d'une recette (multi-format)."""
    return (
        recipe.get("title_fr") or
        (recipe.get("titles") or {}).get("fr") or
        recipe.get("title_original") or
        recipe.get("title") or
        ""
    )


def _get_cuisine(recipe: dict) -> str:
    """Extrait la cuisine d'origine (multi-format)."""
    from backend.core.data_io import recipe_cuisine
    return recipe_cuisine(recipe) or str(recipe.get("cuisine") or "").lower()


def _get_overall_score(recipe: dict, score_graph: dict | None = None) -> float:
    """Score qualité global (0–10), depuis recipe ou score_graph."""
    # 1. Champ direct
    # BUG 3 FIX : le champ réel sur 779/845 recettes est "_quality_score" (underscore
    # préfixe) — ajouté en tête de liste pour qu'il soit lu en priorité.
    for field in ("_quality_score", "overall_score", "quality_score", "final_score"):
        v = recipe.get(field)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    # 2. Score graph
    if score_graph:
        rid = str(recipe.get("id", ""))
        sg_entry = score_graph.get(rid, {})
        if sg_entry.get("overall_score"):
            return float(sg_entry["overall_score"])
    # 3. Scoring imbriqué
    scoring = recipe.get("scoring", {})
    if scoring.get("overall"):
        try:
            return float(scoring["overall"])
        except (TypeError, ValueError):
            pass
    return 5.0


# ═══════════════════════════════════════════════════════════════════════════════
# Fuzzy matching — Levenshtein
# ═══════════════════════════════════════════════════════════════════════════════

def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) > 32 or len(b) > 32:
        return abs(len(a) - len(b))
    m, n = len(a), len(b)
    if m < n:
        a, b, m, n = b, a, n, m
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


# ═══════════════════════════════════════════════════════════════════════════════
# Cache index + mapping (singleton, rechargé si chemin change)
# ═══════════════════════════════════════════════════════════════════════════════

class _IndexCache:
    _instance: "_IndexCache | None" = None

    def __init__(self) -> None:
        self._index:   dict[str, list] = {}     # token → [recipe_ids (int ou str)]
        self._idf:     dict[str, float] = {}
        self._mapping: dict[str, str]   = {}    # fr_term → en_term
        self._total:   int = 1
        self._idx_path = ""
        self._map_path = ""
        # v4.2 — modules contextuels
        self._cycle:      dict = {}             # phase → {ingredient_ids, avoid_ingredient_ids}
        self._astro:      dict = {}             # ingredient → {element, moon_phases}
        self._cycle_path  = ""
        self._astro_path  = ""
        # BUG 8 FIX : mtime par fichier pour invalidation temporelle du cache
        self._mtime: dict[str, float] = {}      # path → mtime au dernier chargement

    @classmethod
    def get(cls) -> "_IndexCache":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _is_stale(self, path: str) -> bool:
        """Retourne True si le fichier a été modifié depuis le dernier chargement."""
        try:
            current_mtime = Path(path).stat().st_mtime
        except OSError:
            return False   # fichier inaccessible → on garde le cache actuel
        return current_mtime != self._mtime.get(path, -1.0)

    def _record_mtime(self, path: str) -> None:
        try:
            self._mtime[path] = Path(path).stat().st_mtime
        except OSError:
            pass

    def load_index(self, path: str) -> None:
        if path == self._idx_path and not self._is_stale(path):
            return
        try:
            # Essaie d'abord via data_io (cache mtime-aware)
            try:
                from backend.core.data_io import load_search_index
                raw = load_search_index()
            except Exception:
                raw = json.loads(Path(path).read_text(encoding="utf-8"))
            tokens = raw.get("tokens", {})
            self._index = {_normalize_token(k): v for k, v in tokens.items()}
            self._total = raw.get("total_recipes", max(len(self._index), 1))
            N = self._total
            self._idf = {
                tok: math.log((N + 1) / (len(ids) + 1)) + 1.0
                for tok, ids in self._index.items()
            }
            self._idx_path = path
            self._record_mtime(path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("search_engine: échec chargement index — %s", e)

    def load_mapping(self, path: str) -> None:
        if path == self._map_path and not self._is_stale(path):
            return
        try:
            try:
                from backend.core.data_io import load_fr_to_en
                mapping_raw = load_fr_to_en()
            except Exception:
                raw = json.loads(Path(path).read_text(encoding="utf-8"))
                mapping_raw = raw.get("mapping", raw) if isinstance(raw, dict) else {}
            self._mapping = {}
            for k, v in mapping_raw.items():
                nk = _normalize_token(k).replace(" ", "_")
                nk2 = _normalize_token(k)
                self._mapping[nk]  = str(v)
                self._mapping[nk2] = str(v)

            # ── Aliases ingrédients (abréviations, argot, fautes courantes) ──────
            # Fichier : data/ingredients/ingredient_search_aliases.json
            # Les entrées du mapping principal ont priorité (setdefault).
            _aliases_path = Path(path).parent / "ingredient_search_aliases.json"
            try:
                _aliases_raw = json.loads(_aliases_path.read_text(encoding="utf-8"))
                for k, v in (_aliases_raw.get("aliases") or {}).items():
                    nk  = _normalize_token(k).replace(" ", "_")
                    nk2 = _normalize_token(k)
                    self._mapping.setdefault(nk,  str(v))
                    self._mapping.setdefault(nk2, str(v))
            except Exception:
                pass   # fichier optionnel — silencieux

            self._map_path = path
            self._record_mtime(path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("search_engine: échec chargement mapping — %s", e)

    def load_cycle(self, path: str) -> None:
        """Charge female_cycle_nutrition.json — phases et ingrédients associés."""
        if path == self._cycle_path and not self._is_stale(path):
            return
        try:
            try:
                from backend.core.data_io import load_cycle_nutrition
                raw = load_cycle_nutrition()
            except Exception:
                raw = json.loads(Path(path).read_text(encoding="utf-8"))
            phases = raw.get("cycle_phases", {})
            # Normalise les ingredient_ids en set pour lookup O(1)
            self._cycle = {
                phase: {
                    "recommended": set(pdata.get("ingredient_ids", [])),
                    "avoid":       set(pdata.get("avoid_ingredient_ids", [])),
                }
                for phase, pdata in phases.items()
            }
            self._cycle_path = path
            self._record_mtime(path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("search_engine: cycle non chargé — %s", e)

    def load_astro(self, path: str) -> None:
        """Charge astro_nutrition.json — mapping ingrédient → élément + phases lunaires."""
        if path == self._astro_path and not self._is_stale(path):
            return
        try:
            try:
                from backend.core.data_io import load_astro_nutrition
                raw = load_astro_nutrition()
            except Exception:
                raw = json.loads(Path(path).read_text(encoding="utf-8"))
            self._astro = raw.get("ingredients_astro_map", {})
            self._astro_path = path
            self._record_mtime(path)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("search_engine: astro non chargé — %s", e)

    def cycle_sets(self, phase: str) -> tuple[set, set]:
        """Retourne (recommended_ids, avoid_ids) pour une phase du cycle."""
        entry = self._cycle.get(phase, {})
        return entry.get("recommended", set()), entry.get("avoid", set())

    def astro_info(self, ingredient: str) -> dict:
        """Retourne {element, moon_phases} pour un ingrédient, ou {} si absent."""
        return self._astro.get(ingredient, {})

    def translate(self, token: str) -> list[str]:
        """Retourne toutes les variantes d'un token (original + EN + underscore/espace)."""
        variants: set[str] = {token, token.replace(" ", "_"), token.replace("_", " ")}
        for v in list(variants):
            t = self._mapping.get(v)
            if t:
                nt = _normalize_token(t)
                variants.add(nt)
                variants.add(nt.replace("_", " "))
                variants.add(nt.replace(" ", "_"))
        return list(variants)

    def exact_ids(self, token: str) -> set:
        return set(self._index.get(token, []))

    def fuzzy_ids(self, token: str, max_dist: int) -> dict[str, set]:
        if max_dist == 0:
            return {}
        n = len(token)
        result: dict[str, set] = {}
        for idx_tok, ids in self._index.items():
            if abs(len(idx_tok) - n) > max_dist:
                continue
            d = _levenshtein(token, idx_tok)
            if 0 < d <= max_dist:
                result[idx_tok] = set(ids)
        return result

    def idf(self, token: str) -> float:
        return self._idf.get(token, math.log(self._total + 1) + 1.0)

    def is_stop(self, token: str) -> bool:
        ids = self._index.get(token, [])
        return len(ids) / max(self._total, 1) > _IDF_STOP_RATIO


# ═══════════════════════════════════════════════════════════════════════════════
# Construction de la hit-map (index → scores)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_hit_map(
    tokens: list[str],
    cache: _IndexCache,
    enable_fuzzy: bool = True,
) -> dict[Any, float]:
    """recipe_id → score IDF cumulé pour la liste de tokens."""
    scores: dict[Any, float] = {}

    for raw_tok in tokens:
        variants  = cache.translate(raw_tok)
        max_dist  = _fuzzy_threshold(len(raw_tok))

        # Hits exacts (toutes variantes)
        exact: set = set()
        best_idf = 0.0
        for v in variants:
            ids = cache.exact_ids(v)
            if ids and not cache.is_stop(v):
                best_idf = max(best_idf, cache.idf(v))
                exact |= ids

        for rid in exact:
            scores[rid] = scores.get(rid, 0.0) + best_idf

        # Hits fuzzy (seulement si aucun exact)
        if enable_fuzzy and max_dist > 0 and not exact:
            for ftok, fids in cache.fuzzy_ids(raw_tok, max_dist).items():
                if cache.is_stop(ftok):
                    continue
                dist   = _levenshtein(raw_tok, ftok)
                f_idf  = cache.idf(ftok) * (1.0 / (dist + 1))
                for rid in fids:
                    scores[rid] = scores.get(rid, 0.0) + f_idf

    return scores


# ═══════════════════════════════════════════════════════════════════════════════
# Scores individuels
# ═══════════════════════════════════════════════════════════════════════════════

def _title_score(query_tokens: list[str], recipe: dict) -> float:
    """Score fuzzy entre les tokens de la requête et tous les champs texte du titre."""
    if not query_tokens:
        return 0.0
    # BUG 5 FIX : cherche dans title_fr ET titles.fr ET title_original ET cuisine ET tags
    tags = recipe.get("tags") or {}
    # tags est un dict de listes ({"diet": [...], "allergens": [...], "technique": [...]})
    if isinstance(tags, dict):
        tag_values: list[str] = []
        for v in tags.values():
            if isinstance(v, list):
                tag_values.extend(str(t) for t in v)
            elif isinstance(v, str):
                tag_values.append(v)
        tags_str = " ".join(tag_values)
    elif isinstance(tags, list):
        tags_str = " ".join(str(t) for t in tags)
    else:
        tags_str = ""

    text_fields = [
        _get_title(recipe),
        _get_cuisine(recipe),
        tags_str,
    ]
    title_tokens: list[str] = []
    for f in text_fields:
        title_tokens.extend(_tokenize(str(f)))
    if not title_tokens:
        return 0.0

    matched = sum(
        1 for qt in query_tokens
        if any(_levenshtein(qt, tt) <= _fuzzy_threshold(len(qt)) for tt in title_tokens)
    )
    return matched / len(query_tokens)


def _ingredient_score(
    query_tokens: set[str],
    recipe: dict,
    max_missing: int,
    cache: _IndexCache,
) -> tuple[float, set[str]]:
    """
    Score ingrédients pondéré par position (ingrédient principal > secondaire).
    Retourne (-1, missing) si trop d'ingrédients manquants.
    """
    if not query_tokens:
        return 0.0, set()

    composition = recipe.get("composition") or []
    if not composition:
        return 0.0, query_tokens.copy()

    # Set des ingrédients de la recette avec variantes
    recipe_ings: set[str] = set()
    for item in composition:
        raw = (item.get("ingredient") or item.get("name") or "").lower().strip()
        if not raw:
            continue
        norm = _normalize_token(raw).replace(" ", "_")
        recipe_ings.add(norm)
        recipe_ings.add(norm.replace("_", " "))
        for v in cache.translate(norm):
            recipe_ings.add(v)

    present: set[str] = set()
    missing: set[str] = set()
    for tok in query_tokens:
        variants = {tok, tok.replace("_", " "), tok.replace(" ", "_")}
        variants |= set(cache.translate(tok))
        if variants & recipe_ings:
            present.add(tok)
        else:
            missing.add(tok)

    if len(missing) > max_missing:
        return -1.0, missing

    if not present:
        return 0.0, missing

    # BUG 2 FIX : pondération par role culinaire x decroissance positionnelle.
    # Un ingredient "base" ou "protein" en position 5 doit peser plus
    # qu'un "seasoning" en position 1.
    _ROLE_WEIGHT = {
        "base":          2.0,
        "protein":       1.8,
        "plant_protein": 1.8,
        "carbohydrate":  1.6,
        "vegetable":     1.4,
        "liquid":        1.2,
        "fat":           1.0,
        "ingredient":    1.0,
        "aromatic":      0.7,
        "condiment":     0.6,
        "seasoning":     0.5,
        "garnish":       0.3,
    }

    weighted = total_w = 0.0
    for idx, item in enumerate(composition):
        raw = _normalize_token(item.get("ingredient") or item.get("name") or "")
        if not raw:
            continue
        role = (item.get("meta") or {}).get("role") or "ingredient"
        role_w = _ROLE_WEIGHT.get(role, 1.0)
        pos_decay = 1.0 / (1.0 + 0.15 * idx)
        weight = role_w * pos_decay
        total_w += weight
        for qt in present:
            qvars = {qt, qt.replace("_", " "), qt.replace(" ", "_")}
            if raw in qvars or any(raw in v or v in raw for v in qvars):
                weighted += weight
                break

    score = (weighted / total_w) if total_w > 0 else (len(present) / len(query_tokens))
    return round(score, 4), missing


def _season_bonus(recipe: dict, month: int, season_data: dict) -> float:
    if not month or not season_data:
        return 0.0
    # BUG 1 FIX : les recettes n'ont pas de champ "ingredients" — les IDs sont dans
    # composition[].ingredient. On extrait les variantes (avec/sans underscore) pour
    # maximiser le matching contre les clés de seasonality.json.
    composition = recipe.get("composition") or []
    ings: list[str] = []
    for item in composition:
        raw = (item.get("ingredient") or item.get("name") or "").lower().strip()
        if not raw:
            continue
        norm = raw.replace(" ", "_")
        # Essaie les deux formes : "spinach" et "spinach_cooked" → match direct
        for variant in (norm, norm.replace("_", " ")):
            if variant in season_data:
                ings.append(variant)
                break
        else:
            # Fallback préfixe : "baby_spinach" matche "spinach" dans season_data
            base = norm.split("_")[0]
            if base in season_data:
                ings.append(base)

    # Ne calcule le bonus que sur les ingrédients avec saisonnalité connue
    # (exclut les ingrédients disponibles toute l'année selon le schéma year_round)
    strict = [i for i in ings
              if season_data.get(i, {}).get("seasons", ["year_round"]) != ["year_round"]]
    if not strict:
        return 0.0
    in_s = [i for i in strict if month in season_data.get(i, {}).get("months", [])]
    ratio = len(in_s) / len(strict)
    return 0.5 if ratio == 1.0 else 0.2 if ratio >= 0.5 else 0.0


# ── B1 : Bonus cycle menstruel ───────────────────────────────────────────────

def _cycle_bonus(recipe: dict, cycle_phase: str | None, cache: "_IndexCache") -> float:
    """
    Score bonus/malus basé sur la phase du cycle menstruel (B1).

    Logique :
      - Chaque ingrédient de la recette est comparé aux ingredient_ids recommandés
        et aux avoid_ingredient_ids de la phase active (female_cycle_nutrition.json).
      - Bonus  = ratio d'ingrédients recommandés présents   → +0.0 à +1.0
      - Malus  = ratio d'ingrédients à éviter présents      → −0.0 à −0.4
      - Score final clippé à 0.0 minimum (jamais négatif ici, géré dans la pondération)

    Retourne un float 0.0–1.0 (ou légèrement négatif si pénalité forte).
    """
    if not cycle_phase:
        return 0.0
    recommended, avoid = cache.cycle_sets(cycle_phase)
    if not recommended and not avoid:
        return 0.0

    comp = recipe.get("composition") or []
    if not comp:
        return 0.0

    recipe_ings = {(item.get("ingredient") or "").lower().strip() for item in comp}
    recipe_ings.discard("")

    n = len(recipe_ings)
    if n == 0:
        return 0.0

    # BUG 4 FIX : le matching exact rate les variantes composees.
    # "baby_spinach" ne matchait pas "spinach", "chickpea_cooked" ne matchait
    # pas "chickpea". Matching par segment d'underscore dans les deux sens,
    # avec garde longueur >= 5 pour les suffixes afin d'eviter les faux
    # positifs ("oil" vs "flaxseed_oil", "pepper" vs "bell_pepper").
    def _segment_match(r_ing: str, ref_id: str) -> bool:
        if r_ing == ref_id:
            return True
        # r_ing est une variante plus specifique : "chickpea_cooked" → "chickpea"
        if r_ing.startswith(ref_id + "_"):
            return True
        # ref_id est un suffixe substantiel : "walnut_halves" → "walnut" (len>=5)
        if len(ref_id) >= 5 and r_ing.endswith("_" + ref_id):
            return True
        return False

    def _count_matches(recipe_set: set, ref_set: set) -> int:
        return sum(
            1 for r_ing in recipe_set
            if any(_segment_match(r_ing, ref_id) for ref_id in ref_set)
        )

    hits_rec   = _count_matches(recipe_ings, recommended)
    hits_avoid = _count_matches(recipe_ings, avoid)

    bonus = hits_rec   / n          # 0–1 : part d'ingrédients recommandés
    malus = hits_avoid / n * 0.4    # 0–0.4 : pénalité modérée (on n'exclut pas)

    return round(max(bonus - malus, 0.0), 4)


# ── B2 : Bonus élément astrologique ─────────────────────────────────────────

def _astro_element_bonus(recipe: dict, astro_element: str | None, cache: "_IndexCache") -> float:
    """
    Score bonus basé sur l'élément astrologique demandé (B2).

    Logique :
      - Pour chaque ingrédient de la recette mappé dans astro_nutrition,
        on récupère son élément (Feu | Air | Terre | Eau).
      - Score = ratio d'ingrédients mappés dont l'élément correspond.
      - Couverture : 840/845 recettes ont au moins 1 ingrédient mappé.

    Retourne un float 0.0–1.0.
    """
    if not astro_element:
        return 0.0
    target = astro_element.strip()  # Feu, Air, Terre, Eau (casse respectée dans le JSON)

    comp = recipe.get("composition") or []
    if not comp:
        return 0.0

    mapped = 0
    matched = 0
    for item in comp:
        ing = (item.get("ingredient") or "").lower().strip()
        if not ing:
            continue
        info = cache.astro_info(ing)
        if not info:
            continue
        mapped += 1
        if info.get("element") == target:
            matched += 1

    if mapped == 0:
        return 0.0
    return round(matched / mapped, 4)


# ── B3 : Bonus phase lunaire ─────────────────────────────────────────────────

def _moon_phase_bonus(recipe: dict, moon_phase: str | None, cache: "_IndexCache") -> float:
    """
    Score bonus basé sur la phase lunaire active (B3).

    Logique :
      - Pour chaque ingrédient mappé dans astro_nutrition, on vérifie si
        la moon_phase demandée figure dans sa liste moon_phases.
      - Score = ratio d'ingrédients mappés favorables à cette phase lunaire.
      - Phases valides : nouvelle_lune | pleine_lune | premier_quartier | dernier_quartier

    Retourne un float 0.0–1.0.
    """
    if not moon_phase:
        return 0.0
    target = moon_phase.strip()

    comp = recipe.get("composition") or []
    if not comp:
        return 0.0

    mapped = 0
    matched = 0
    for item in comp:
        ing = (item.get("ingredient") or "").lower().strip()
        if not ing:
            continue
        info = cache.astro_info(ing)
        if not info:
            continue
        mapped += 1
        if target in info.get("moon_phases", []):
            matched += 1

    if mapped == 0:
        return 0.0
    return round(matched / mapped, 4)


def _fallback_text_score(query_tokens: list[str], recipe: dict) -> float:
    """
    Score textuel pour les recettes hors-index (titres + tags + cuisine).
    Utilisé quand le hit_map ne contient pas la recette.
    """
    if not query_tokens:
        return 0.0
    title_s = _title_score(query_tokens, recipe)
    if title_s > 0:
        return title_s * 0.6   # décote par rapport aux recettes indexées

    # Recherche dans les tags cuisine/diet
    tag_text = " ".join([
        _get_cuisine(recipe),
        " ".join(recipe.get("diet_flags", {}).keys() if isinstance(recipe.get("diet_flags"), dict) else []),
    ])
    tag_tokens = _tokenize(tag_text)
    if tag_tokens:
        matched = sum(
            1 for qt in query_tokens
            if any(_levenshtein(qt, tt) <= _fuzzy_threshold(len(qt)) for tt in tag_tokens)
        )
        return (matched / len(query_tokens)) * 0.3
    return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# Filtres directs — v4.2 (A1–A4 + existants)
# ═══════════════════════════════════════════════════════════════════════════════

def _passes_filters(
    recipe:          dict,
    diet:            str | None,
    cuisine:         str | None,
    difficulty:      str | None,
    max_time:        int | None,
    # v4.2 — nouveaux filtres directs
    allergen_exclude: list[str] | None = None,
    dish_type:        str | None       = None,
    max_spice:        int | None       = None,
    health_tags:      list[str] | None = None,
) -> bool:
    """
    Filtre une recette avant scoring.  Retourne False dès qu'une condition échoue.

    Filtres existants :
      diet        : vegan | vegetarian | vegetarien | gluten_free | lactose_free | nut_free
      cuisine     : sous-chaîne de cuisine_origin
      difficulty  : easy | medium | advanced (et alias FR)
      max_time    : minutes totales max

    Filtres v4.2 :
      allergen_exclude : liste d'allergènes à exclure (tags.allergens)
                         ex. ["gluten", "eggs", "peanuts"]
      dish_type        : type de plat exact (main|soup|side|dessert|starter|
                         snack|breakfast|sauce|beverage…)
      max_spice        : niveau d'épices max 0–3 (scoring.spice_level)
                         0=neutre, 1=léger, 2=moyen, 3=épicé
      health_tags      : un ou plusieurs tags santé requis (tags.diet)
                         ex. ["diabetes_friendly"], ["kid_friendly"], ["high_protein"]
    """
    # ── Régimes (diet_flags) ─────────────────────────────────────────────────
    df = recipe.get("diet_flags") or {}
    if diet == "vegan"        and not df.get("vegan"):        return False
    if diet == "vegetarian"   and not df.get("vegetarian"):   return False
    if diet == "vegetarien"   and not df.get("vegetarian"):   return False
    if diet == "gluten_free"  and not df.get("gluten_free"):  return False
    if diet == "lactose_free" and not df.get("lactose_free"): return False
    if diet == "nut_free"     and not df.get("nut_free"):     return False

    # ── Cuisine ──────────────────────────────────────────────────────────────
    if cuisine and cuisine.lower() not in _get_cuisine(recipe):
        return False

    # ── Difficulté (alias FR/EN) ──────────────────────────────────────────────
    if difficulty:
        lvl = (
            recipe.get("difficulty_level") or
            recipe.get("difficulty") or
            ""
        ).lower().strip()
        # Alias FR → EN
        diff_map = {"facile": "easy", "moyen": "medium", "difficile": "advanced"}
        norm_diff = diff_map.get(difficulty.lower().strip(), difficulty.lower().strip())
        # BUG 5 FIX : égalité stricte (évite "easy" qui matchait dans "not_easy")
        if norm_diff != lvl:
            return False

    # ── Temps total ───────────────────────────────────────────────────────────
    if max_time:
        total = (
            (recipe.get("timing") or {}).get("total_min") or
            recipe.get("total_time") or
            recipe.get("cook_time_minutes") or
            recipe.get("prep_time")
        )
        if total:
            try:
                if int(total) > max_time:
                    return False
            except (TypeError, ValueError):
                pass

    # ── A1 : Allergènes à exclure ────────────────────────────────────────────
    if allergen_exclude:
        recipe_allergens: set[str] = set()
        # Source prioritaire : tags.allergens (couverture 845/845)
        tags = recipe.get("tags") or {}
        if isinstance(tags, dict):
            recipe_allergens.update(a.lower() for a in tags.get("allergens", []))
        # Source secondaire : champ allergens direct (66 recettes bases)
        for a in recipe.get("allergens") or []:
            recipe_allergens.add(str(a).lower())
        for excl in allergen_exclude:
            if excl.lower() in recipe_allergens:
                return False

    # ── A2 : Type de plat ────────────────────────────────────────────────────
    if dish_type:
        recipe_dt = (recipe.get("dish_type") or "").lower().strip()
        if recipe_dt != dish_type.lower().strip():
            return False

    # ── A3 : Niveau d'épices max ─────────────────────────────────────────────
    if max_spice is not None:
        # scoring.spice_level (couverture 780/845) ou champ direct spice_level (66/845)
        spice = (
            (recipe.get("scoring") or {}).get("spice_level") or
            recipe.get("spice_level")
        )
        if spice is not None:
            try:
                if int(spice) > max_spice:
                    return False
            except (TypeError, ValueError):
                pass

    # ── A4 : Tags santé étendus ──────────────────────────────────────────────
    if health_tags:
        tags = recipe.get("tags") or {}
        recipe_diet_tags: set[str] = set()
        if isinstance(tags, dict):
            recipe_diet_tags.update(t.lower() for t in tags.get("diet", []))
        # Tous les health_tags demandés doivent être présents (logique ET)
        for ht in health_tags:
            if ht.lower() not in recipe_diet_tags:
                return False

    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Mode recommandation (requête vide)
# ═══════════════════════════════════════════════════════════════════════════════

def _recommend(
    recipes: list[dict],
    *,
    limit: int,
    month: int,
    season_data: dict,
    score_graph: dict | None,
    # v4.2 — contexte
    cycle_phase:    str | None      = None,
    astro_element:  str | None      = None,
    moon_phase:     str | None      = None,
    cache:          "_IndexCache | None" = None,
    active_context: dict | None     = None,
) -> list[dict]:
    """
    Ordre de recommandation (requête vide) :
      1. Recette du jour (déterministe, saisonnière si possible)
      2. Nouveautés (date ajout)
      3. Populaires (score global élevé)
      4. Aléatoire (diversité)

    Les bonus contextuels (cycle, astro, lune) sont intégrés dans le score
    final de recommandation avec un poids de 0.08 chacun (max).
    """
    import random

    today    = datetime.date.today()
    day_seed = int(today.strftime("%Y%j"))   # déterministe par jour
    rng      = random.Random(day_seed)

    # Poids bonus contextuels en mode recommandation
    cyc_w  = 0.08 if cycle_phase   else 0.0
    ast_w  = 0.08 if astro_element else 0.0
    moon_w = 0.08 if moon_phase    else 0.0
    ctx_total = cyc_w + ast_w + moon_w

    # Poids base renormalisés : qualité(40%) nouveauté(25%) popularité(20%) saison(10%) bruit(5%)
    base_weights = {"quality": 0.40, "novelty": 0.25, "pop": 0.20, "season": 0.10, "noise": 0.05}
    if ctx_total > 0:
        scale = (1.0 - ctx_total)
        base_weights = {k: v * scale for k, v in base_weights.items()}

    scored: list[tuple[float, dict, dict]] = []

    for r in recipes:
        quality = _get_overall_score(r, score_graph) / 10.0
        sea     = _season_bonus(r, month, season_data)

        novelty = 0.0
        ds = r.get("created_at") or r.get("date_added") or ""
        if ds:
            try:
                d = datetime.date.fromisoformat(str(ds)[:10])
                age = (today - d).days
                novelty = max(0.0, 1.0 - age / 180.0)
            except ValueError:
                pass

        pop = 0.0
        try:
            nv = int(r.get("views_count") or r.get("reviews_count") or r.get("num_ratings") or 0)
            pop = math.log1p(nv) / 10.0
        except (TypeError, ValueError):
            pass

        noise = rng.random() * 0.08

        # Bonus contextuels
        cyc_b  = _cycle_bonus(r, cycle_phase, cache) if (cycle_phase and cache) else 0.0
        ast_b  = _astro_element_bonus(r, astro_element, cache) if (astro_element and cache) else 0.0
        moon_b = _moon_phase_bonus(r, moon_phase, cache) if (moon_phase and cache) else 0.0

        bw = base_weights
        final = round(
            quality  * bw["quality"] +
            novelty  * bw["novelty"] +
            pop      * bw["pop"]     +
            sea      * bw["season"]  +
            noise    * bw["noise"]   +
            cyc_b    * cyc_w         +
            ast_b    * ast_w         +
            moon_b   * moon_w,
            4,
        )
        bonuses = {"cycle_bonus": cyc_b, "astro_element_bonus": ast_b, "moon_phase_bonus": moon_b}
        scored.append((final, r, bonuses))

    scored.sort(key=lambda x: -x[0])

    results = [
        {
            **r,
            "_search_v3": {
                "ingredient_match":    0.0,
                "fuzzy_score":         0.0,
                "index_score":         0.0,
                "adaptive_score":      0.0,
                "base_score":          round(_get_overall_score(r, score_graph), 2),
                "season_bonus":        sea,
                "cycle_bonus":         bonuses["cycle_bonus"],
                "astro_element_bonus": bonuses["astro_element_bonus"],
                "moon_phase_bonus":    bonuses["moon_phase_bonus"],
                "final_score":         round(final * 10, 3),
                "missing":             [],
                "profile":             "default",
                "source":              "recommendation",
            },
        }
        for final, r, bonuses in scored[:limit]
    ]
    # Retourne la liste directement — c'est search() qui décide si elle
    # enveloppe dans un dict (include_context=True) ou non.
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Recherche de recettes similaires (sous-propositions Q&A #5)
# ═══════════════════════════════════════════════════════════════════════════════

def _find_similar_ids(
    search_tokens: list[str],
    top_ids: set,
    cache: _IndexCache,
    all_recipes: list[dict],
    limit: int = 5,
) -> list[dict]:
    """
    Recettes similaires thématiques (tokens spécifiques, hors résultats principaux).
    Retourne des dicts recette légers (id, title, score).

    BUG 9 FIX :
      - Plus de limite arbitraire a 4 tokens : tous les tokens specifiques sont utilises.
      - Fallback texte pour les recettes hors-index (non couvertes par sim_hits),
        afin qu'elles apparaissent aussi dans _similar quand elles sont pertinentes.
    """
    specific = [t for t in search_tokens if cache.idf(t) > math.log(2) and not cache.is_stop(t)]
    if not specific:
        return []

    # BUG 9a FIX : utilise tous les tokens specifiques, pas seulement les 4 premiers
    sim_hits = _build_hit_map(specific, cache, enable_fuzzy=False)
    recipe_map = {r.get("id"): r for r in all_recipes}

    seen_ids: set = set(top_ids)
    candidates = []

    # 1. Recettes couvertes par l'index
    for rid, score in sorted(sim_hits.items(), key=lambda x: -x[1]):
        if rid in seen_ids:
            continue
        r = recipe_map.get(rid)
        if r:
            candidates.append({
                "id":         rid,
                "title_fr":   _get_title(r),
                "cuisine":    _get_cuisine(r),
                "_sim_score": round(score, 3),
            })
            seen_ids.add(rid)
        if len(candidates) >= limit:
            break

    # BUG 9b FIX : fallback texte pour recettes hors-index si quota non atteint
    if len(candidates) < limit:
        fallback = []
        for r in all_recipes:
            rid = r.get("id")
            if rid in seen_ids:
                continue
            fs = _fallback_text_score(specific, r)
            if fs > 0.0:
                fallback.append((fs, rid, r))
        fallback.sort(key=lambda x: -x[0])
        for fs, rid, r in fallback:
            candidates.append({
                "id":         rid,
                "title_fr":   _get_title(r),
                "cuisine":    _get_cuisine(r),
                "_sim_score": round(fs, 3),
            })
            seen_ids.add(rid)
            if len(candidates) >= limit:
                break

    return candidates


# ═══════════════════════════════════════════════════════════════════════════════
# Fonction principale search()
# ═══════════════════════════════════════════════════════════════════════════════

def search(
    # ── Requête ──────────────────────────────────────────────────────────────
    query_text:        str   | None = None,
    query:             str   | None = None,   # alias backward-compat orchestrateur
    query_ingredients: list  | None = None,
    # ── Données injectables ──────────────────────────────────────────────────
    recipes:           list  | None = None,
    score_graph:       dict  | None = None,
    season_data:       dict  | None = None,
    index_path:        str   | None = None,
    mapping_path:      str   | None = None,
    cycle_path:        str   | None = None,
    astro_path:        str   | None = None,
    # ── Filtres directs (A1–A4 + existants) ──────────────────────────────────
    diet:              str   | None = None,
    cuisine:           str   | None = None,
    difficulty:        str   | None = None,
    max_time:          int   | None = None,
    max_missing:       int          = 0,
    allergen_exclude:  list  | None = None,   # A1 : ex. ["gluten", "eggs"]
    dish_type:         str   | None = None,   # A2 : ex. "breakfast", "dessert"
    max_spice:         int   | None = None,   # A3 : 0–3
    health_tags:       list  | None = None,   # A4 : ex. ["diabetes_friendly"]
    # ── Scoring contextuel (B1–B3) ────────────────────────────────────────────
    cycle_phase:       str   | None = None,   # B1 : menstrual|follicular|ovulatory|luteal
    astro_element:     str   | None = None,   # B2 : Feu|Air|Terre|Eau
    moon_phase:        str   | None = None,   # B3 : nouvelle_lune|pleine_lune|…
    # ── Profil utilisateur global (C) ────────────────────────────────────────
    user_profile:      dict  | None = None,   # C  : préférences persistantes
    # ── Scoring général ───────────────────────────────────────────────────────
    month:             int   | None = None,   # 1–12, auto-détecté si absent
    profile:           str          = "default",
    context:           dict  | None = None,
    # ── Résultats ────────────────────────────────────────────────────────────
    limit:             int          = 20,
    enable_fuzzy:      bool         = True,
    include_similar:   bool         = True,
    include_context:   bool         = False,   # BUG 12 compat : True → dict wrapper, False → list
) -> list[dict] | dict:
    """
    Recherche intelligente v4.2 — dual mode + filtres contextuels complets.

    Args:
        query_text / query  : texte libre FR ou EN (alias compat orchestrateur)
        query_ingredients   : tokens ingrédients FR ou EN
        recipes             : liste recettes injectée (si None → data_io)
        score_graph         : graphe de scoring (si None → data_io)
        season_data         : données saisonnalité (si None → data_io)
        cycle_path          : chemin female_cycle_nutrition.json (si None → défaut)
        astro_path          : chemin astro_nutrition.json (si None → défaut)

        — Filtres directs (excluent des recettes avant scoring) —
        diet                : vegan|vegetarien|gluten_free|lactose_free|nut_free
        cuisine             : sous-chaîne de cuisine_origin
        difficulty          : easy|medium|advanced (ou facile|moyen|difficile)
        max_time            : minutes totales max
        max_missing         : ingrédients manquants tolérés
        allergen_exclude    : liste allergènes à exclure (gluten|eggs|soy|sesame…)
        dish_type           : type de plat exact (main|soup|dessert|breakfast…)
        max_spice           : épices max 0=neutre, 1=léger, 2=moyen, 3=épicé
        health_tags         : tags santé requis (diabetes_friendly|kid_friendly|
                              high_protein|low_calorie|raw) — logique ET

        — Bonus contextuels (influencent le scoring, n'excluent pas) —
        cycle_phase         : menstrual|follicular|ovulatory|luteal
        astro_element       : Feu|Air|Terre|Eau
        moon_phase          : nouvelle_lune|pleine_lune|premier_quartier|dernier_quartier

        — Profil utilisateur (C) —
        user_profile        : dict de préférences persistantes — appliqué en fond,
                              surchargeable par les paramètres explicites ci-dessus.
                              Clés supportées : diet, allergen_exclude, cuisine,
                              difficulty, max_time, max_spice, health_tags, dish_type,
                              cycle_phase, astro_element, moon_phase

        month               : 1–12 (auto si absent)
        limit               : nombre max de résultats
        enable_fuzzy        : active le matching Levenshtein
        include_similar     : ajoute _similar dans chaque résultat

    Returns:
        dict {"results": list[dict], "context": dict}
          results : recettes scorées, triées par final_score décroissant.
            Chaque recette contient un champ _search_v3 :
            {ingredient_match, fuzzy_score, index_score, base_score,
             season_bonus, cycle_bonus, astro_element_bonus, moon_phase_bonus,
             final_score, missing, profile, source, _similar?}
          context : active_context partagé par toutes les recettes de la requête
            (diet, allergen_exclude, dish_type, max_spice, health_tags,
             cycle_phase, astro_element, moon_phase) — BUG 12 FIX.
    """
    # ── BUG 1 FIX : alias query → query_text ─────────────────────────────────
    effective_query = query_text or query or ""

    # ── BUG 6 FIX : mois auto ────────────────────────────────────────────────
    if month is None:
        month = datetime.date.today().month

    # ── C : Fusion profil utilisateur (les args explicites ont priorité) ──────
    if user_profile:
        def _up(param, key):
            return param if param is not None else user_profile.get(key)
        diet             = _up(diet,             "diet")
        cuisine          = _up(cuisine,           "cuisine")
        difficulty       = _up(difficulty,        "difficulty")
        max_time         = _up(max_time,          "max_time")
        max_spice        = _up(max_spice,         "max_spice")
        dish_type        = _up(dish_type,         "dish_type")
        cycle_phase      = _up(cycle_phase,       "cycle_phase")
        astro_element    = _up(astro_element,     "astro_element")
        moon_phase       = _up(moon_phase,        "moon_phase")
        # BUG 7 FIX : listes → union (profil de base + arg situationnel, sans doublons)
        # Ex : profil=["gluten"] + appel=["eggs"] → ["gluten", "eggs"]
        def _merge_list(arg, key):
            prof_val = user_profile.get(key) or []
            if arg is None and not prof_val:
                return None
            return list(dict.fromkeys((prof_val or []) + (arg or [])))
        allergen_exclude = _merge_list(allergen_exclude, "allergen_exclude")
        health_tags      = _merge_list(health_tags,      "health_tags")

    # ── BUG 2 FIX : chemins via DATA_ROOT ────────────────────────────────────
    idx_path   = index_path   or _default_index_path()
    map_path   = mapping_path or _default_mapping_path()
    cyc_path   = cycle_path   or _default_cycle_path()
    ast_path   = astro_path   or _default_astro_path()

    # ── Chargement cache ─────────────────────────────────────────────────────
    cache = _IndexCache.get()
    cache.load_index(idx_path)
    cache.load_mapping(map_path)
    # Modules contextuels (chargés seulement si utiles)
    if cycle_phase:
        cache.load_cycle(cyc_path)
    if astro_element or moon_phase:
        cache.load_astro(ast_path)

    # ── BUG 3 FIX : recettes via data_io si non injectées ────────────────────
    if not recipes:
        try:
            from backend.core.data_io import load_recipes
            recipes = load_recipes()
        except Exception:
            try:
                rpath = Path(idx_path).parent.parent / "recipes" / "recipes.json"
                raw   = json.loads(rpath.read_text(encoding="utf-8"))
                recipes = raw.get("recipes", raw) if isinstance(raw, dict) else raw
            except Exception:
                return []

    if not score_graph:
        try:
            from backend.core.data_io import load_score_graph
            score_graph = load_score_graph()
        except Exception:
            logger.warning("search : erreur ignorée (repli)", exc_info=True)
            score_graph = {}

    if not season_data:
        try:
            from backend.core.data_io import load_seasonality
            season_data = load_seasonality()
        except Exception:
            logger.warning("search : erreur ignorée (repli)", exc_info=True)
            season_data = {}

    # ── Filtrage combiné — une seule passe (A1–A4 inclus) ────────────────────
    filtered = [
        r for r in recipes
        if _passes_filters(
            r,
            diet=diet, cuisine=cuisine, difficulty=difficulty, max_time=max_time,
            allergen_exclude=allergen_exclude, dish_type=dish_type,
            max_spice=max_spice, health_tags=health_tags,
        )
    ]

    # Contexte actif — exposé dans _search_v3 pour transparence
    active_context = {k: v for k, v in {
        "diet":             diet,
        "allergen_exclude": allergen_exclude,
        "dish_type":        dish_type,
        "max_spice":        max_spice,
        "health_tags":      health_tags,
        "cycle_phase":      cycle_phase,
        "astro_element":    astro_element,
        "moon_phase":       moon_phase,
    }.items() if v is not None}

    # ── Mode recommandation (requête vide) ────────────────────────────────────
    has_query = bool(
        (effective_query and effective_query.strip()) or
        (query_ingredients and any(str(t).strip() for t in query_ingredients))
    )

    if not has_query:
        results = _recommend(
            filtered,
            limit=limit,
            month=month,
            season_data=season_data,
            score_graph=score_graph,
            cycle_phase=cycle_phase,
            astro_element=astro_element,
            moon_phase=moon_phase,
            cache=cache,
            active_context=active_context,
        )
        if include_context:
            return {"results": results, "context": active_context}
        return results

    # ── Tokenisation ─────────────────────────────────────────────────────────
    query_tokens: list[str] = []
    if effective_query:
        query_tokens = _tokenize(effective_query)
    if query_ingredients:
        for ing in query_ingredients:
            query_tokens.extend(_tokenize(str(ing)))
    query_tokens = list(dict.fromkeys(query_tokens))   # déduplique, ordre conservé

    # BUG 13 FIX : stratégie de repli IDF-aware pour les tokens stop.
    #
    # Ancienne logique : non_stop vide → on repart sur query_tokens complets,
    # sans tenir compte de l'IDF réel de chaque token.  Problème : pour "soupe"
    # (token présent dans 65 % du corpus), le repli renvoyait toutes les recettes
    # avec un score uniforme, ce qui noyait les résultats pertinents.
    #
    # Nouvelle logique :
    #   1. On préfère toujours les tokens non-stop (idf élevé).
    #   2. Si tous les tokens sont stop, on trie query_tokens par IDF décroissant
    #      et on garde les N tokens les plus discriminants (min 1, max 3).
    #      On conserve ainsi « soupe » seul mais en lui donnant au moins une chance
    #      de matcher, plutôt que de relancer sur un ensemble qui noie les résultats.
    non_stop = [t for t in query_tokens if not cache.is_stop(t)]
    if non_stop:
        search_tokens = non_stop
    else:
        # Tous stop : trier par IDF desc, garder au plus 3 tokens les plus rares
        _sorted_by_idf = sorted(query_tokens, key=lambda t: -cache.idf(t))
        search_tokens  = _sorted_by_idf[:max(1, min(3, len(_sorted_by_idf)))]

    # ── Lookup index ─────────────────────────────────────────────────────────
    hit_map = _build_hit_map(search_tokens, cache, enable_fuzzy=enable_fuzzy)

    # Normalisation IDF max pour comparabilité des scores
    max_idf = sum(cache.idf(t) for t in search_tokens if not cache.is_stop(t)) or 1.0

    # Tokens ingrédients normalisés (pour _ingredient_score)
    ing_tokens: set[str] = (
        {_normalize_token(t).replace(" ", "_") for t in query_tokens}
        if query_ingredients else set()
    )

    # ── Scoring recette par recette ───────────────────────────────────────────
    results: list[dict] = []

    for recipe in filtered:
        rid = recipe.get("id")

        # Score index (recettes couvertes)
        raw_idx   = hit_map.get(rid, 0.0)
        index_s   = min(raw_idx / max_idf, 1.0)

        # Fallback texte pour recettes hors-index
        if raw_idx == 0.0:
            fallback_s = _fallback_text_score(search_tokens, recipe)
            if fallback_s == 0.0 and not ing_tokens:
                continue   # aucun signal → exclure
            index_s = fallback_s

        # BUG 5 FIX : score titre (titles.fr + title_fr + tags)
        fuzzy_s = _title_score(search_tokens, recipe)

        # Score ingrédients
        ing_s, missing = _ingredient_score(ing_tokens, recipe, max_missing, cache)
        if ing_s < 0:
            continue

        # Score qualité de base (normalisé 0–1)
        base_s = _get_overall_score(recipe, score_graph) / 10.0

        # Bonus saisonnier
        sea_b = _season_bonus(recipe, month, season_data)

        # ── Bonus contextuels v4.2 (B1–B3) ───────────────────────────────────
        cyc_b  = _cycle_bonus(recipe, cycle_phase, cache)
        ast_b  = _astro_element_bonus(recipe, astro_element, cache)
        moon_b = _moon_phase_bonus(recipe, moon_phase, cache)

        # ── Pondération dynamique ─────────────────────────────────────────────
        if index_s >= 0.7:
            idx_w, fuz_w, ing_w, base_w = 0.50, 0.20, 0.18, 0.12
        elif index_s >= 0.3:
            idx_w, fuz_w, ing_w, base_w = 0.42, 0.20, 0.22, 0.16
        elif fuzzy_s >= 0.7:
            idx_w, fuz_w, ing_w, base_w = 0.20, 0.45, 0.20, 0.15
        elif ing_tokens:
            idx_w, fuz_w, ing_w, base_w = 0.22, 0.10, 0.48, 0.20
        else:
            idx_w, fuz_w, ing_w, base_w = 0.35, 0.28, 0.12, 0.25

        # Poids bonus contextuels — additifs, prélevés proportionnellement sur les autres
        # Chaque bonus actif prend 0.04 (max 3 × 0.04 = 0.12 au total)
        sea_w  = 0.04 if month else 0.0
        cyc_w  = 0.04 if cycle_phase   else 0.0
        ast_w  = 0.04 if astro_element else 0.0
        moon_w = 0.04 if moon_phase    else 0.0

        # Renormalisation des poids principaux pour que la somme totale = 1.0
        total_ctx_w = sea_w + cyc_w + ast_w + moon_w
        total_base_w = idx_w + fuz_w + ing_w + base_w
        if total_base_w > 0:
            f = (1.0 - total_ctx_w) / total_base_w
            idx_w *= f; fuz_w *= f; ing_w *= f; base_w *= f

        raw_score = (
            index_s         * idx_w  +
            fuzzy_s         * fuz_w  +
            max(ing_s, 0.0) * ing_w  +
            base_s          * base_w +
            sea_b           * sea_w  +
            cyc_b           * cyc_w  +
            ast_b           * ast_w  +
            moon_b          * moon_w
        )
        final = round(raw_score * 10.0, 3)

        results.append({
            **recipe,
            "_search_v3": {
                "ingredient_match":    round(max(ing_s, 0.0), 3),
                "fuzzy_score":         round(fuzzy_s, 3),
                "index_score":         round(index_s, 3),
                "adaptive_score":      round(index_s, 3),   # alias compat scoring.py
                "base_score":          round(base_s * 10, 2),
                "season_bonus":        sea_b,
                "cycle_bonus":         cyc_b,
                "astro_element_bonus": ast_b,
                "moon_phase_bonus":    moon_b,
                "final_score":         final,
                "missing":             sorted(missing),
                "profile":             profile,
                "source":              "index" if raw_idx > 0 else "fallback",
            },
        })

    # ── Tri décroissant ───────────────────────────────────────────────────────
    results.sort(key=lambda x: -x["_search_v3"]["final_score"])
    results = results[:limit]

    # ── Sous-propositions similaires (Q&A #5) ─────────────────────────────────
    if include_similar and results:
        top_ids = {r.get("id") for r in results}
        similar = _find_similar_ids(search_tokens, top_ids, cache, filtered, limit=6)
        if results:
            results[0]["_search_v3"]["_similar_recipes"] = similar

    # BUG 12 compat : retourne list[dict] par défaut (backward-compat tests/orchestrateurs).
    # Passer include_context=True pour obtenir le wrapper {"results": ..., "context": ...}.
    if include_context:
        return {"results": results, "context": active_context}
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# CLI / smoke test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Search Engine smoke test")
    parser.add_argument("query", nargs="*", default=["curry", "tofu"],
                        help="Termes de recherche (défaut: 'curry tofu')")
    parser.add_argument("--cycle", metavar="PHASE",
                        help="Tester le module cycle (ex: menstrual, follicular, ovulatory, luteal)")
    parser.add_argument("--astro", metavar="ELEMENT",
                        help="Tester le module astro (ex: Feu, Air, Terre, Eau)")
    parser.add_argument("--moon", metavar="PHASE",
                        help="Tester la phase lunaire (ex: nouvelle_lune, pleine_lune)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Nombre de résultats (défaut: 10)")
    args = parser.parse_args()

    query = " ".join(args.query)
    print(f"Query      : {query!r}")
    if args.cycle:
        print(f"Cycle      : {args.cycle!r}")
    if args.astro:
        print(f"Astro      : {args.astro!r}")
    if args.moon:
        print(f"Moon       : {args.moon!r}")

    cache = _IndexCache.get()
    try:
        cache.load_index(_default_index_path())
        cache.load_mapping(_default_mapping_path())
    except Exception as e:
        print(f"Erreur chargement index : {e}")
        sys.exit(1)

    # ── Test module cycle ────────────────────────────────────────────────────
    if args.cycle:
        try:
            cache.load_cycle(_default_cycle_path())
            rec, avoid = cache.cycle_sets(args.cycle)
            print(f"\n[cycle:{args.cycle}] {len(rec)} ingrédients recommandés, "
                  f"{len(avoid)} à éviter")
            if rec:
                print(f"  recommandés (5 premiers) : {sorted(rec)[:5]}")
            if avoid:
                print(f"  à éviter   (5 premiers) : {sorted(avoid)[:5]}")
        except Exception as e:
            print(f"[cycle] Erreur : {e}")

    # ── Test module astro ────────────────────────────────────────────────────
    if args.astro or args.moon:
        try:
            cache.load_astro(_default_astro_path())
            # Sonde quelques ingrédients connus
            probes = ["spinach", "lemon", "ginger", "tofu", "salmon"]
            print(f"\n[astro] Sonde de {len(probes)} ingrédients :")
            for ing in probes:
                info = cache.astro_info(ing)
                if info:
                    elem  = info.get("element", "?")
                    moons = info.get("moon_phases", [])
                    match_e = "✓" if (args.astro and elem == args.astro) else " "
                    match_m = "✓" if (args.moon  and args.moon in moons) else " "
                    print(f"  {match_e}{match_m} {ing:<20} élément={elem}  lune={moons}")
                else:
                    print(f"     {ing:<20} (non mappé)")
        except Exception as e:
            print(f"[astro] Erreur : {e}")

    # ── Recherche standard ───────────────────────────────────────────────────
    print()
    toks = _tokenize(query)
    hits = _build_hit_map(toks, cache)
    top  = sorted(hits.items(), key=lambda x: -x[1])[:args.limit]
    print(f"Tokens  : {toks}")
    print(f"Top IDs : {top}")
