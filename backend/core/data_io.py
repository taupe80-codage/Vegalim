"""
data_io.py — Chargement sécurisé des fichiers JSON.

Remplace tous les json.load(open(...)) directs par une fonction
qui gère les erreurs proprement sans crasher l'application.

Correction P2.1 :
  Les loaders critiques (recettes, ingrédients, score_graph) utilisent
  _MtimeCache au lieu de @lru_cache. Le cache est invalidé automatiquement
  si le fichier JSON est modifié sur disque, sans nécessiter de redémarrage.
  Cela couvre les writes produits par : pipeline, search_token_generator,
  culinary_product_engine, scripts d'import.

  Les loaders statiques (graphes de nutrition, saisons, etc.) conservent
  @lru_cache — ils ne sont jamais mis à jour pendant l'exécution du serveur.

Usage :
    from backend.core.data_io import load_json, load_recipes
    recipes = load_recipes()           # dataset principal
    graph   = load_json(path)          # n'importe quel JSON
    graph   = load_json(path, default={"items": []})
"""
import json
import logging
import os
import threading
from functools import lru_cache
from pathlib import Path

from backend.engine.config import DATA_ROOT

logger = logging.getLogger(__name__)


# ── Cache mtime-aware ──────────────────────────────────────────────────────────

class _MtimeCache:
    """
    Cache à invalidation automatique basée sur la date de modification du fichier.

    Principe : à chaque appel, on compare le mtime courant du fichier avec celui
    mémorisé. Si le fichier a changé, on recharge. Sinon, on retourne le cache.

    Thread-safe via RLock.
    Expose cache_clear() pour compatibilité avec le code existant (admin.py).
    """

    def __init__(self, name: str = ""):
        self._data  = None
        self._mtime = 0.0
        self._lock  = threading.RLock()
        self._name  = name

    def get(self, path: Path, loader):
        """Retourne les données, rechargées si le fichier a été modifié."""
        with self._lock:
            try:
                mtime = path.stat().st_mtime
            except OSError:
                mtime = 0.0

            if self._data is None or mtime > self._mtime:
                self._data  = loader()
                self._mtime = mtime
                logger.debug("Cache rechargé : %s (mtime=%.0f)", self._name or path.name, mtime)

            return self._data

    def cache_clear(self) -> None:
        """Force le rechargement au prochain accès. Compatible lru_cache API."""
        with self._lock:
            self._data  = None
            self._mtime = 0.0
        logger.debug("Cache invalidé : %s", self._name)


def load_json(path: str | Path, default=None, required: bool = False):
    """
    Charge un fichier JSON de manière sécurisée.

    Args:
        path     : chemin vers le fichier JSON
        default  : valeur retournée si le fichier est absent ou corrompu
        required : si True, lève une RuntimeError au lieu de retourner default

    Returns:
        Contenu du JSON ou default en cas d'erreur.
    """
    p = Path(path)
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("JSON chargé : %s (%d octets)", p.name, p.stat().st_size)
        return data
    except FileNotFoundError:
        msg = f"Fichier JSON introuvable : {p}"
        if required:
            logger.critical(msg)
            raise RuntimeError(msg)
        logger.warning(msg)
        return default if default is not None else {}
    except json.JSONDecodeError as e:
        msg = f"JSON corrompu : {p} — {e}"
        if required:
            logger.critical(msg)
            raise RuntimeError(msg)
        logger.error(msg)
        return default if default is not None else {}
    except PermissionError as e:
        msg = f"Permission refusée : {p} — {e}"
        logger.error(msg)
        return default if default is not None else {}
    except Exception as e:
        msg = f"Erreur inattendue lors du chargement de {p} : {e}"
        logger.error(msg)
        return default if default is not None else {}


def save_json(path: str | Path, data, indent: int = 2) -> bool:
    """
    Sauvegarde un fichier JSON de manière sécurisée.
    Utilise une écriture atomique (temp file + os.replace).

    Returns:
        True si succès, False si erreur.
    """
    import os, tempfile
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        os.replace(tmp_path, p)
        logger.debug("JSON sauvegardé : %s", p.name)
        return True
    except Exception as e:
        if 'tmp_path' in locals() and Path(tmp_path).exists():
            try: os.unlink(tmp_path)
            except: pass
        logger.error("Erreur sauvegarde JSON %s : %s", p, e)
        return False


# ── Caches mtime-aware (fichiers modifiés pendant l'exécution du serveur) ──────

_recipes_cache     = _MtimeCache("load_recipes")
_ingredients_cache = _MtimeCache("load_ingredients_dict")
_score_graph_cache = _MtimeCache("load_score_graph")


def load_recipes() -> list[dict]:
    """Dataset principal — rechargé automatiquement si recipes.json est modifié."""
    _path = DATA_ROOT / "recipes" / "recipes.json"

    def _loader():
        data    = load_json(_path, default={"recipes": []}, required=True)
        recipes = data.get("recipes", data) if isinstance(data, dict) else data
        logger.info("Dataset chargé : %d recettes", len(recipes))
        return recipes

    return _recipes_cache.get(_path, _loader)

# Compatibilité avec le code existant qui appelle load_recipes.cache_clear()
load_recipes.cache_clear = _recipes_cache.cache_clear  # type: ignore[attr-defined]


def load_score_graph() -> dict:
    """Graphe de scoring — rechargé si recipe_scoring_graph_v1.json est modifié."""
    _path = DATA_ROOT / "graphs" / "recipe_scoring_graph_v1.json"
    return _score_graph_cache.get(_path, lambda: load_json(_path, default={}))

load_score_graph.cache_clear = _score_graph_cache.cache_clear  # type: ignore[attr-defined]


def load_ingredients_dict() -> dict:
    """Dictionnaire ingrédients — rechargé si ingredients_dictionary.json est modifié."""
    _path = DATA_ROOT / "ingredients" / "ingredients_dictionary.json"

    def _loader():
        raw  = load_json(_path, default={"ingredients": []})
        ings = raw.get("ingredients", raw) if isinstance(raw, dict) else raw
        return {i["id"]: i for i in ings if isinstance(i, dict) and "id" in i}

    return _ingredients_cache.get(_path, _loader)

load_ingredients_dict.cache_clear = _ingredients_cache.cache_clear  # type: ignore[attr-defined]


# ── Loaders statiques (@lru_cache) — jamais modifiés en cours d'exécution ──────

@lru_cache(maxsize=1)
def load_nutrition_graph() -> dict:
    return load_json(DATA_ROOT / "graphs" / "recipe_nutrition_graph_v1.json", default={})


@lru_cache(maxsize=1)
def load_nutrition_db() -> dict:
    """Base nutritionnelle nettoyée CIQUAL/USDA — source unique."""
    from backend.engine.config import NUTRITION_PATH
    raw = load_json(NUTRITION_PATH, default={"ingredients": {}})
    return raw.get("ingredients", raw) if isinstance(raw, dict) else {}


@lru_cache(maxsize=1)
def load_substitution_graph() -> dict:
    return load_json(
        DATA_ROOT / "graphs" / "ingredient_substitution_rules_graph_v1.json",
        default={}
    )


@lru_cache(maxsize=1)
def load_search_index() -> dict:
    return load_json(DATA_ROOT / "indexes" / "search_index.json", default={})


@lru_cache(maxsize=1)
def load_scoring_profiles() -> dict:
    return load_json(DATA_ROOT / "graphs" / "scoring_weight_profiles_v1.json", default={})


@lru_cache(maxsize=1)
def load_seasonality() -> dict:
    return load_json(DATA_ROOT / "modules" / "seasonality.json", default={})


@lru_cache(maxsize=1)
def load_prices() -> dict:
    return load_json(DATA_ROOT / "config" / "prices.json", default={})


@lru_cache(maxsize=1)
def load_flavor_graph() -> dict:
    return load_json(DATA_ROOT / "graphs" / "flavor_pairing_graph_v1.json", default={})


@lru_cache(maxsize=1)
def load_global_cuisine_graph() -> dict:
    return load_json(DATA_ROOT / "graphs" / "global_cuisine_graph_v1.json", default={})

@lru_cache(maxsize=1)
def load_unit_conversion_graph() -> dict:
    return load_json(DATA_ROOT / "graphs" / "unit_conversion_graph_v1.json", default={})


@lru_cache(maxsize=1)
def load_carbon_footprint() -> dict:
    return load_json(DATA_ROOT / "config" / "carbon_footprint.json", default={})


@lru_cache(maxsize=1)
def load_availability_graph() -> dict:
    return load_json(DATA_ROOT / "graphs" / "ingredient_availability_graph_v1.json", default={})


@lru_cache(maxsize=1)
def load_vegan_variants_index() -> dict:
    return load_json(DATA_ROOT / "config" / "vegan_variants_index.json", default={})


@lru_cache(maxsize=1)
def load_fr_to_en() -> dict:
    """Mapping FR→EN pour la migration des clés ingrédients (879 entrées, v1.0)."""
    raw = load_json(DATA_ROOT / "ingredients" / "fr_to_en_mapping.json",
                    default={"mapping": {}})
    return raw.get("mapping", raw) if isinstance(raw, dict) else {}


@lru_cache(maxsize=1)
def load_ingredient_physical() -> dict:
    """Données physiques par ingrédient : unités, densité, edible_pct, ciqual_id (116 entrées)."""
    raw = load_json(DATA_ROOT / "ingredients" / "ingredient_physical.json",
                    default={})
    return {k: v for k, v in raw.items() if not k.startswith("_")}
