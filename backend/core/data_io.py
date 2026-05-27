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

Correction P2.2 — nutrition_db :
  load_nutrition_db() migré de @lru_cache vers _MtimeCache.
  nutrition_v2.json est mis à jour à chaque run pipeline (promote_nutrition).
  Avec @lru_cache, le serveur servait des données périmées jusqu'au redémarrage.

Ajout v6.17 — feature dual nutrition source :
  compute_recipe_nutrition() : calcule la nutrition depuis la composition d'une
      base_recipe (pour les laits/crèmes végétaux maison et futurs dual items).
  resolve_ingredient_nutrition() : résout la nutrition d'un ingrédient en tenant
      compte de nutrition_source_mode='dual' dans ingredients_dictionary.

Usage :
    from backend.core.data_io import load_json, load_recipes
    recipes = load_recipes()           # dataset principal
    graph   = load_json(path)          # n'importe quel JSON
    graph   = load_json(path, default={"items": []})

    # Feature dual (laits/crèmes végétaux)
    from backend.core.data_io import resolve_ingredient_nutrition
    nutr = resolve_ingredient_nutrition("milk_plant_oat", source_pref="recipe")
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

_recipes_cache      = _MtimeCache("load_recipes")
_ingredients_cache  = _MtimeCache("load_ingredients_dict")
_score_graph_cache  = _MtimeCache("load_score_graph")
_nutrition_db_cache = _MtimeCache("load_nutrition_db")   # ← P2.2 : pipeline modifie ce fichier


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


def load_nutrition_db() -> dict:
    """
    Base nutritionnelle CIQUAL/USDA — nutrition_v2.json (282 ingrédients, v6.17+).

    Migré de @lru_cache vers _MtimeCache (P2.2) :
    nutrition_v2.json est promu à chaque run pipeline (promote_nutrition.py).
    Avec @lru_cache, le serveur servait les données de démarrage jusqu'au restart.
    Avec _MtimeCache, le rechargement est automatique dès que le fichier change.

    Returns:
        dict {ingredient_id: {variants: {default: {calories_kcal, …}}, …}}
    """
    from backend.engine.config import NUTRITION_PATH
    _path = Path(NUTRITION_PATH)

    def _loader():
        raw  = load_json(_path, default={"ingredients": {}})
        data = raw.get("ingredients", raw) if isinstance(raw, dict) else {}
        logger.info("nutrition_v2 chargé : %d ingrédients (v%s)",
                    len(data), raw.get("schema_version", "?") if isinstance(raw, dict) else "?")
        return data

    return _nutrition_db_cache.get(_path, _loader)

load_nutrition_db.cache_clear = _nutrition_db_cache.cache_clear  # type: ignore[attr-defined]


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


@lru_cache(maxsize=1)
def load_astro_nutrition() -> dict:
    raw = load_json(DATA_ROOT / "modules" / "astro_nutrition.json", default={})
    return raw.get("ingredients_astro_map", {})


_cycle_data_cache = _MtimeCache("load_cycle_data")

def load_cycle_data() -> dict:
    """
    Données du cycle féminin (female_cycle_nutrition.json).

    Chargé via _MtimeCache — rechargé automatiquement si le fichier est modifié.
    Source unique partagée par cycle_engine et graph_engine (évite deux caches
    indépendants sur le même fichier 336 KB).
    """
    path = DATA_ROOT / "modules" / "female_cycle_nutrition.json"
    return _cycle_data_cache.get(path, lambda: load_json(path, default={}))


# ── Feature dual nutrition source (v6.17) ─────────────────────────────────────
#
# Mécanisme : certains ingrédients (laits/crèmes végétaux) ont deux sources de
# données nutritionnelles disponibles :
#   - "industrial" : valeurs CIQUAL/USDA depuis nutrition_v2.json
#   - "recipe"     : calculé depuis la composition de la base_recipe maison
#
# Le champ `nutrition_source_mode: "dual"` dans ingredients_dictionary.json
# marque ces ingrédients. Le champ `base_recipe_key` pointe vers la recette.
#
# resolve_ingredient_nutrition() est le point d'entrée unique pour les engines
# et routes qui ont besoin de la nutrition d'un ingrédient.
# ──────────────────────────────────────────────────────────────────────────────

# Conversion unités → grammes (pour le calcul de composition)
_UNIT_TO_G: dict[str, float] = {
    "g":     1.0,
    "kg":    1000.0,
    "mg":    0.001,
    "ml":    1.0,       # approximation densité eau (suffisant pour lait/crème)
    "l":     1000.0,
    "cl":    10.0,
    "dl":    100.0,
    "tsp":   5.0,
    "tbsp":  15.0,
    "cup":   240.0,
    "oz":    28.35,
    "lb":    453.6,
    "pinch": 0.5,
    "unit":  100.0,     # estimation générique (à affiner par ingrédient si besoin)
}

# Champs nutritionnels inclus dans le calcul de composition
_NUTRIENT_FIELDS: tuple[str, ...] = (
    "calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g",
    "starch_g", "alcohol_g",
    "saturated_fat_g", "monounsaturated_fat_g", "polyunsaturated_fat_g",
    "trans_fat_g", "cholesterol_mg",
    "omega3_g", "omega3_ala_g", "omega3_epa_g", "omega3_dha_g", "omega6_g",
    "sodium_mg", "calcium_mg", "iron_mg", "magnesium_mg", "phosphorus_mg",
    "potassium_mg", "zinc_mg", "copper_mg", "manganese_mg", "selenium_ug",
    "iodine_ug",
    "vitamin_a_ug", "beta_carotene_ug", "vitamin_c_mg", "vitamin_d_ug",
    "vitamin_e_mg", "vitamin_k1_ug", "vitamin_k2_ug",
    "vitamin_b1_mg", "vitamin_b2_mg", "vitamin_b3_mg", "vitamin_b5_mg",
    "vitamin_b6_mg", "vitamin_b12_ug", "folate_ug", "choline_mg",
    "polyols_g", "organic_acids_g",
)


def compute_recipe_nutrition(recipe_id: str, per_100g: bool = True) -> dict:
    """
    Calcule la nutrition d'une base_recipe depuis sa composition.

    Itère sur chaque ingrédient de la composition, récupère ses valeurs
    nutritionnelles dans nutrition_v2.json, pondère par la quantité convertie
    en grammes, somme le tout, puis normalise à 100g de produit fini.

    Args:
        recipe_id : ID de la recette (ex: 'base_oat_milk_3519f4')
        per_100g  : si True (défaut), ramène le résultat à 100g de produit fini
                    via le champ yield_g de la recette

    Returns:
        dict des champs nutritionnels. Clés privées '_recipe_id' et '_yield_g'
        incluses pour traçabilité. Retourne {} si recette introuvable.
    """
    recipes = load_recipes()
    recipe  = next((r for r in recipes if r.get("id") == recipe_id), None)

    if not recipe:
        logger.warning("compute_recipe_nutrition : recette '%s' introuvable", recipe_id)
        return {}

    nutr_db     = load_nutrition_db()
    composition = recipe.get("composition", [])
    yield_g     = float(recipe.get("yield_g") or 100.0)
    totals: dict[str, float] = {}
    missing_ings: list[str] = []

    for item in composition:
        ing_id   = item.get("ingredient", "")
        quantity = float(item.get("quantity") or 0)
        unit     = (item.get("unit") or "g").lower().strip()
        qty_g    = quantity * _UNIT_TO_G.get(unit, 1.0)

        if qty_g <= 0 or not ing_id:
            continue

        ing_entry = nutr_db.get(ing_id, {})
        if not ing_entry:
            missing_ings.append(ing_id)
            continue

        # Prendre la variante default (la seule nécessaire pour les laits/crèmes)
        variant = ing_entry.get("variants", {}).get("default", {})
        ratio   = qty_g / 100.0

        for field in _NUTRIENT_FIELDS:
            val = variant.get(field)
            if isinstance(val, (int, float)):
                totals[field] = totals.get(field, 0.0) + val * ratio

    if missing_ings:
        logger.debug(
            "compute_recipe_nutrition '%s' : %d ingrédients sans données : %s",
            recipe_id, len(missing_ings), missing_ings
        )

    result: dict = {}
    if per_100g and yield_g > 0:
        factor = 100.0 / yield_g
        result = {k: round(v * factor, 3) for k, v in totals.items()}
    else:
        result = {k: round(v, 3) for k, v in totals.items()}

    # Métadonnées de traçabilité (préfixées _ → ignorées par les engines de score)
    result["_recipe_id"] = recipe_id
    result["_yield_g"]   = yield_g
    return result


def resolve_ingredient_nutrition(
    ingredient_id: str,
    variant:      str = "default",
    source_pref:  str = "industrial",
) -> dict:
    """
    Résout la nutrition d'un ingrédient avec gestion du mode dual.

    Pour les ingrédients standard (nutrition_source_mode absent ou 'industrial') :
      → retourne toujours nutrition_v2.json[ingredient_id][variant]

    Pour les ingrédients dual (laits/crèmes végétaux, etc.) :
      - source_pref='industrial' (défaut) → nutrition_v2.json (données CIQUAL/USDA)
      - source_pref='recipe'              → calcul depuis composition de base_recipe_key

    Si le calcul recette échoue (recette introuvable, composition vide), bascule
    automatiquement sur la source industrielle avec un warning.

    Args:
        ingredient_id : clé ingrédient (ex: 'milk_plant_oat', 'cream_plant_soy')
        variant       : variante nutritionnelle dans nutrition_v2 (ex: 'oat', 'default')
        source_pref   : 'industrial' | 'recipe'

    Returns:
        dict des champs nutritionnels pour 100g.
        Champs privés inclus : '_source' ('industrial'|'recipe'), '_recipe_id' (si recipe).

    Exemples :
        # Source industrielle (CIQUAL/USDA)
        nutr = resolve_ingredient_nutrition("milk_plant_oat")

        # Source recette maison (calcul depuis composition)
        nutr = resolve_ingredient_nutrition("milk_plant_oat", source_pref="recipe")

        # Ingrédient standard (non-dual) — source_pref ignoré
        nutr = resolve_ingredient_nutrition("spinach")
    """
    ings_dict       = load_ingredients_dict()
    ing             = ings_dict.get(ingredient_id, {})
    mode            = ing.get("nutrition_source_mode", "industrial")
    base_recipe_key = ing.get("base_recipe_key")

    # ── Mode recipe (dual uniquement) ──────────────────────────────────────────
    if mode == "dual" and source_pref == "recipe" and base_recipe_key:
        nutr = compute_recipe_nutrition(base_recipe_key, per_100g=True)
        if nutr and any(
            k for k in nutr if not k.startswith("_")
        ):
            nutr["_source"]    = "recipe"
            # _recipe_id déjà inclus par compute_recipe_nutrition
            return nutr

        logger.warning(
            "resolve_ingredient_nutrition : calcul recette vide pour '%s' "
            "(recipe_id=%s) → fallback industriel",
            ingredient_id, base_recipe_key
        )

    # ── Mode industriel (défaut + fallback) ────────────────────────────────────
    nutr_db   = load_nutrition_db()
    ing_entry = nutr_db.get(ingredient_id, {})
    variants  = ing_entry.get("variants", {})

    # Chercher la variante demandée, sinon default
    result = variants.get(variant) or variants.get("default")

    if not result:
        logger.debug(
            "resolve_ingredient_nutrition : '%s' variant='%s' introuvable dans nutrition_v2",
            ingredient_id, variant
        )
        return {"_source": "industrial", "_missing": True}

    result          = dict(result)   # copie pour ne pas muter le cache
    result["_source"] = "industrial"
    return result