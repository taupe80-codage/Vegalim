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
from backend.core.data_cache import data_cached
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

_recipes_cache        = _MtimeCache("load_recipes")
_ingredients_cache    = _MtimeCache("load_ingredients_dict")
_ingredients_alias_cache = _MtimeCache("load_ingredients_alias_index")
_score_graph_cache    = _MtimeCache("load_score_graph")
_nutrition_db_cache   = _MtimeCache("load_nutrition_db")   # ← P2.2 : pipeline modifie ce fichier
_ingredient_map_cache = _MtimeCache("load_ingredient_map")


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
    """Dictionnaire ingrédients — rechargé si ingredients_dictionary.json est modifié.

    Structure du fichier (build_dict_v2.py) : categories -> subcategories ->
    ingredient_groups -> {entry_key: entry}. La clé de chaque entrée EST son
    identifiant (canonical_name_fr/canonical_name_en, axes, axes_fr,
    diet_profile, allergens_eu, ... — pas de champ 'id'/'name_fr'/'category'
    interne, contrairement à l'ancien format à plat). Retourne un dict aplati
    {entry_key: entry}, sans renommer ni injecter de champs — les
    consommateurs lisent canonical_name_fr/canonical_name_en/allergens_eu
    directement.
    """
    _path = DATA_ROOT / "ingredients" / "ingredients_dictionary.json"

    def _loader():
        raw = load_json(_path, default={"categories": {}})
        if isinstance(raw, dict) and "ingredients" in raw:
            # Ancien format à plat (rétrocompat, non produit par build_dict_v2.py).
            ings = raw["ingredients"]
            return {i["id"]: i for i in ings if isinstance(i, dict) and "id" in i}
        if isinstance(raw, dict) and "categories" in raw:
            flat: dict = {}
            for cat in raw["categories"].values():
                for sub in (cat or {}).get("subcategories", {}).values():
                    for key, entry in (sub or {}).get("ingredient_groups", {}).items():
                        flat[key] = entry
            return flat
        return {}

    return _ingredients_cache.get(_path, _loader)

load_ingredients_dict.cache_clear = _ingredients_cache.cache_clear  # type: ignore[attr-defined]


def load_ingredients_alias_index() -> dict:
    """alias_index de ingredients_dictionary.json : {ancienne_clé: clé_actuelle}.

    Produit par build_dict_v2.py à chaque rename de clé (fusion, correction
    d'axe...) — sert de table de synonymes pour la résolution de recherche.
    """
    _path = DATA_ROOT / "ingredients" / "ingredients_dictionary.json"

    def _loader():
        raw = load_json(_path, default={"alias_index": {}})
        return raw.get("alias_index", {}) if isinstance(raw, dict) else {}

    return _ingredients_alias_cache.get(_path, _loader)

load_ingredients_alias_index.cache_clear = _ingredients_alias_cache.cache_clear  # type: ignore[attr-defined]


# ── Table de résolution état de cuisson demandé → fallback ────────────────────
# Pour chaque état demandé, ordre de préférence parmi les variants disponibles.
_COOKING_RESOLUTION: dict[str, list[str]] = {
    "boiled":  ["boiled", "steamed", "cooked", "raw"],
    "steamed": ["steamed", "boiled", "cooked", "raw"],
    "sauteed": ["sauteed", "cooked", "boiled", "raw"],
    "roasted": ["roasted", "baked", "cooked", "raw"],
    "baked":   ["baked", "roasted", "cooked", "raw"],
    "grilled": ["grilled", "roasted", "cooked", "raw"],
    "fried":   ["cooked", "boiled", "raw"],
    "cooked":  ["cooked", "boiled", "steamed", "raw"],
    "raw":     ["raw", "default"],
}


def load_ingredient_map() -> dict[str, dict]:
    """
    Charge ingredient_map_v2.json — pont entre les IDs recettes sémantiques
    (ex: 'garlic', 'carrot', 'onion/yellow') et les group_ids du dict v2
    (ex: 'garlic_raw', 'carrot', 'yellow_onion_raw').

    Structure d'une entrée :
        {
          "group_id_v2":     "carrot",              # état cru/default
          "cooking_variants": {
              "raw":            "carrot",
              "boiled":         "carrot_boiled_crunchy",
              "steamed":        "carrot_steamed",
              "default_cooked": "carrot_boiled_crunchy",
          },
          "confidence":      0.92,
          "status":          "AUTO_HIGH",
          "canonical_name_en": "carrot",
        }

    Rechargé automatiquement si ingredient_map_v2.json est modifié sur disque.
    Retourne un dict vide (sans crash) si le fichier est absent.
    """
    _path = DATA_ROOT / "recipes" / "ingredient_map_v2.json"

    def _loader() -> dict:
        data = load_json(_path, default={})
        logger.info("ingredient_map_v2 charge : %d entrees", len(data))
        return data

    return _ingredient_map_cache.get(_path, _loader)

load_ingredient_map.cache_clear = _ingredient_map_cache.cache_clear  # type: ignore[attr-defined]


def resolve_cooking_gid(
    recipe_ingredient_id: str,
    use_cooked: bool = False,
    cooking_state: str | None = None,
) -> str | None:
    """
    Résout le group_id du dict v2 pour un ingrédient recette,
    en tenant compte de l'état de cuisson souhaité.

    Priorité de résolution :
      1. cooking_state explicite (meta.state de la composition)
         → cherche dans cooking_variants avec la table de fallback _COOKING_RESOLUTION
      2. use_cooked=True sans cooking_state
         → retourne cooking_variants["default_cooked"] si disponible
      3. Fallback universel
         → retourne group_id_v2 (état cru/default)

    Args:
        recipe_ingredient_id : ID tel qu'il apparaît dans recipes.json
                               (ex: 'garlic', 'carrot', 'onion/yellow')
        use_cooked           : True si le plat est chaud (cook_min > 0)
        cooking_state        : état explicite depuis meta.state
                               ('boiled', 'roasted', 'sauteed', 'raw', …)

    Returns:
        group_id_v2 à utiliser pour le lookup nutrition_v2,
        ou None si l'ingrédient est inconnu dans le map.
    """
    ing_map = load_ingredient_map()
    entry = ing_map.get(recipe_ingredient_id)

    if entry is None:
        # Essai avec la base (avant le /)
        base = recipe_ingredient_id.split("/")[0]
        if base != recipe_ingredient_id:
            entry = ing_map.get(base)

    if entry is None:
        return None

    gid_raw = entry.get("group_id_v2")
    variants = entry.get("cooking_variants") or {}

    # Cas 1 : état de cuisson explicite déclaré
    if cooking_state:
        cs_lower = cooking_state.lower().strip()
        fallbacks = _COOKING_RESOLUTION.get(cs_lower, [cs_lower, "raw", "default"])
        for state in fallbacks:
            if state in variants:
                return variants[state]

    # Cas 2 : plat chaud, utiliser default_cooked
    if use_cooked and "default_cooked" in variants:
        return variants["default_cooked"]

    # Cas 3 : fallback sur l'état cru/default
    return gid_raw


# ── Loaders statiques (@lru_cache) — jamais modifiés en cours d'exécution ──────


@data_cached
def load_ingredients_tree() -> dict:
    """
    Arbre ingrédients v8 — référence taxonomique canonique (1782 groupes, 2077 variants).

    Structure : {categories: [{subcategories: [{ingredient_groups: [
        {id, canonical_name_en, canonical_name_fr, axes_en, axes_fr, variants: [
            {id, source, source_id, axes_en, axes_fr, is_primary, source_rank, …}
        ]}
    ]}]}]}

    Utiliser get_ingredients_tree_index() pour les lookups par nom.
    """
    return load_json(
        DATA_ROOT / "ingredients" / "ingredients_tree.json",
        default={"categories": []}
    )


@data_cached
def get_ingredients_tree_index() -> dict:
    """
    Index plat du tree pour résolution rapide : canonical_name_en normalisé → liste de groupes.

    Chaque groupe contient ses variants avec axes_en (cooking_state, thermal_state, etc.)
    et source_id pour lien vers la base nutritionnelle.

    Usage :
        idx = get_ingredients_tree_index()
        groups = idx.get('carrot', [])
        raw_group   = next((g for g in groups if g['axes_en'].get('cooking_state') == 'raw'), None)
        boiled_group = next((g for g in groups if g['axes_en'].get('cooking_state') == 'boiled'), None)
    """
    tree = load_ingredients_tree()
    index: dict[str, list] = {}

    def _normalize(name: str) -> str:
        return name.lower().replace(' ', '_').replace('-', '_').replace(',', '').strip()

    for cat in tree.get('categories', []):
        for subcat in cat.get('subcategories', []):
            for grp in subcat.get('ingredient_groups', []):
                en = grp.get('canonical_name_en', '')
                if not en:
                    continue
                key = _normalize(en)
                # index par nom complet
                index.setdefault(key, []).append(grp)
                # index par premier mot (pour carrot → carrot_baby, etc.)
                first = key.split('_')[0]
                if first != key:
                    index.setdefault(first, []).append(grp)

    logger.info("Tree index construit : %d clés pour %d groupes",
                len(index), sum(len(v) for v in index.values()))
    return index


def resolve_ingredient_cooking_variant(
    ingredient_id: str,
    cooking_state: str | None = None,
) -> dict | None:
    """
    Résout le groupe tree le plus précis pour un ingrédient de recette.

    Args:
        ingredient_id : ID recette simple (ex: 'carrot', 'lentils/green')
        cooking_state : état de cuisson souhaité ('raw', 'boiled', 'steamed', …)
                        Si None, retourne le groupe raw ou le premier disponible.

    Returns:
        Le groupe ingredient_tree le plus adapté, ou None si non trouvé.
    """
    idx = get_ingredients_tree_index()
    base = ingredient_id.split('/')[0].replace('-', '_').lower()

    candidates = idx.get(base, [])
    if not candidates:
        return None

    target = cooking_state or 'raw'

    # 1. Correspondance exacte sur cooking_state du groupe
    exact = [g for g in candidates if g.get('axes_en', {}).get('cooking_state') == target]
    if exact:
        return exact[0]

    # 2. Correspondance dans les variants
    for g in candidates:
        for v in g.get('variants', []):
            if v.get('axes_en', {}).get('cooking_state') == target:
                return g

    # 3. Fallback : premier candidat sans cooking_state (neutre)
    neutral = [g for g in candidates if not g.get('axes_en', {}).get('cooking_state')]
    if neutral:
        return neutral[0]

    return candidates[0]


@data_cached
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


@data_cached
def load_substitution_graph() -> dict:
    return load_json(
        DATA_ROOT / "graphs" / "ingredient_substitution_rules_graph_v1.json",
        default={}
    )


@data_cached
def load_search_index() -> dict:
    return load_json(DATA_ROOT / "indexes" / "search_index.json", default={})


@data_cached
def load_seasonality() -> dict:
    return load_json(DATA_ROOT / "modules" / "seasonality.json", default={})


@data_cached
def load_prices() -> dict:
    return load_json(DATA_ROOT / "config" / "prices.json", default={})

@data_cached
def load_prices_catalog() -> dict:
    return load_json(DATA_ROOT / "config" / "prices_catalog.json", default={})

@data_cached
def load_ingredient_price_map() -> dict:
    """Correspondance id d'ingredient de recette -> cle prices_catalog.json.

    Genere par scripts/build_ingredient_price_map.py : les deux vocabulaires
    (ids de composition des recettes vs cles du catalogue de prix) ont
    evolue separement, la plupart ne correspondent pas telles quelles.
    """
    return load_json(DATA_ROOT / "config" / "ingredient_price_map.json", default={})


def recipe_cuisine(recipe: dict) -> str:
    """Cuisine d'origine d'une recette. Schéma actuel : origin.cuisine ;
    iconic_status.cuisine_origin / cuisine_origin sont des champs d'anciens
    formats, absents de recipes.json (les lire seuls donnait toujours "")."""
    return str(
        (recipe.get("origin") or {}).get("cuisine")
        or (recipe.get("iconic_status") or {}).get("cuisine_origin")
        or recipe.get("cuisine_origin")
        or ""
    ).lower()


# dish_type des préparations servant d'ingrédient à d'autres recettes
COMPONENT_DISH_TYPES = frozenset({
    "sauce", "condiment", "paste", "base", "ingredient", "broth", "roux", "dairy",
})


def is_component_recipe(recipe: dict) -> bool:
    """Sous-recette / préparation de base (béchamel, pâte de curry, bouillon,
    cheddar vegan…) plutôt qu'un plat : exclue des classements généraux
    (top, découverte, recommandation sans requête), toujours trouvable par
    une recherche explicite."""
    return (str(recipe.get("id", "")).startswith("base_")
            or str(recipe.get("dish_type") or "").lower() in COMPONENT_DISH_TYPES)


def recipe_techniques(recipe: dict) -> list[str]:
    """Techniques culinaires : tags.technique (schéma actuel), sinon technique."""
    raw = (recipe.get("tags") or {}).get("technique") or recipe.get("technique") or []
    if isinstance(raw, str):
        raw = [raw]
    return [str(t).lower() for t in raw]


def resolve_catalog_key(ingredient_id: str, keys) -> str | None:
    """Ramène un id de composition de recette (ex. 'garlic_raw', 'oats/rolled')
    vers une clé des référentiels génériques partagés (prices_catalog,
    carbon_footprint, flavor_graph — ex. 'garlic', 'oats').

    Ordre : id exact, préfixe avant '/', puis ingredient_price_map. Retourne
    None si aucune clé de `keys` ne correspond.
    """
    if not ingredient_id:
        return None
    iid = str(ingredient_id).lower().strip()
    base = iid.split("/")[0]
    for candidate in (iid, base):
        if candidate in keys:
            return candidate
    price_map = load_ingredient_price_map()
    mapped = price_map.get(iid) or price_map.get(base)
    return mapped if mapped in keys else None


@data_cached
def load_flavor_graph() -> dict:
    """Profils gustatifs par ingrédient générique : {'tomato': ['sour', 'sweet', 'umami'], …}.
    (Pointait vers flavor_pairing_graph_v1.json, qui n'a jamais existé.)"""
    return load_json(DATA_ROOT / "graphs" / "flavor_graph.json", default={})


@data_cached
def load_carbon_footprint() -> dict:
    return load_json(DATA_ROOT / "config" / "carbon_footprint.json", default={})


@data_cached
def load_availability_graph() -> dict:
    return load_json(DATA_ROOT / "graphs" / "ingredient_availability_graph_v1.json", default={})


@data_cached
def load_vegan_variants_index() -> dict:
    return load_json(DATA_ROOT / "config" / "vegan_variants_index.json", default={})


@data_cached
def load_fr_to_en() -> dict:
    """Mapping FR→EN pour la migration des clés ingrédients (879 entrées, v1.0)."""
    raw = load_json(DATA_ROOT / "ingredients" / "fr_to_en_mapping.json",
                    default={"mapping": {}})
    return raw.get("mapping", raw) if isinstance(raw, dict) else {}


_ingredient_physical_cache = _MtimeCache("load_ingredient_physical")

def load_ingredient_physical() -> dict:
    """
    Données physiques par ingrédient : unités, densité, edible_pct, ciqual_id, fallback/blend.

    Migré de @lru_cache vers _MtimeCache : ingredient_physical.json est désormais
    modifié par les scripts de pipeline (overrides CIQUAL/USDA, fallback_slug, blend_components).
    Rechargement automatique dès que le fichier change sur disque.
    """
    _path = DATA_ROOT / "ingredients" / "ingredient_physical.json"

    def _loader():
        raw = load_json(_path, default={})
        # Exclure les entrées système (_meta, _orphans, etc.)
        return {k: v for k, v in raw.items() if not k.startswith("_")}

    return _ingredient_physical_cache.get(_path, _loader)

load_ingredient_physical.cache_clear = _ingredient_physical_cache.cache_clear  # type: ignore[attr-defined]


@data_cached
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
# Clés alignées sur nutrition_v2.json (notation CIQUAL/N2)
_NUTRIENT_FIELDS: tuple[str, ...] = (
    # Macros
    "calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g",
    "starch_g", "alcohol_g", "polyols_g", "organic_acids_g",
    # Acides gras (notation fa_* de N2/CIQUAL)
    "fa_saturated_g", "fa_mufa_g", "fa_pufa_g", "cholesterol_mg",
    # Oméga-3 détaillés
    "omega3_g", "fa_18_3_ala_g", "fa_20_5_epa_g", "fa_22_6_dha_g",
    # Sodium + minéraux
    "sodium_mg", "calcium_mg", "iron_mg", "magnesium_mg", "phosphorus_mg",
    "potassium_mg", "zinc_mg", "copper_mg", "manganese_mg", "selenium_ug",
    "iodine_ug",
    # Vitamines
    "vitamin_a_rae_ug", "beta_carotene_ug", "vitamin_c_mg", "vitamin_d_ug",
    "alpha_tocopherol_mg", "vitamin_k1_ug", "vitamin_k2_ug",
    "vitamin_b1_mg", "vitamin_b2_mg", "vitamin_b3_mg", "vitamin_b5_mg",
    "vitamin_b6_mg", "vitamin_b12_ug", "folate_dfe_ug",
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
    ing_map     = load_ingredient_map()
    composition = recipe.get("composition", [])
    totals: dict[str, float] = {}
    missing_ings: list[str] = []

    # Poids de chaque ligne en grammes, calculé une fois (réutilisé pour le
    # yield_g de repli — somme des quantités — et pour la pondération nutrition).
    qty_g_by_item = [
        float(item.get("quantity") or 0) * _UNIT_TO_G.get((item.get("unit") or "g").lower().strip(), 1.0)
        for item in composition
    ]
    # yield_g explicite sinon poids total de la composition (aucune perte d'eau
    # supposée) — un défaut fixe à 100g était faux dès que la recette ne pesait
    # pas exactement 100g au total (quasi toujours), ex. lait d'avoine
    # 100g flocons + 800g eau + 1g sel ≈ 901g, pas 100g.
    yield_g = float(recipe.get("yield_g") or sum(qty_g_by_item) or 100.0)

    def _resolve_nutrition_key(raw_id: str) -> str | None:
        """'oats/rolled' -> clé nutrition_v2 via ingredient_map_v2 (group_id_v2 /
        cooking_variants). Fallback sur raw_id tel quel si pas de mapping (couvre
        les cas où l'id recette EST déjà une clé nutrition_v2 valide)."""
        base, _, variant_suffix = raw_id.partition("/")
        entry = ing_map.get(base)
        if entry:
            cooking_variants = entry.get("cooking_variants") or {}
            if variant_suffix and variant_suffix in cooking_variants:
                return cooking_variants[variant_suffix]
            if "default" in cooking_variants:
                return cooking_variants["default"]
            if entry.get("group_id_v2"):
                return entry["group_id_v2"]
        return raw_id

    for item, qty_g in zip(composition, qty_g_by_item):
        ing_id = item.get("ingredient", "")

        if qty_g <= 0 or not ing_id:
            continue

        nutr_key  = _resolve_nutrition_key(ing_id)
        ing_entry = nutr_db.get(nutr_key, {}) if nutr_key else {}
        if not ing_entry:
            missing_ings.append(ing_id)
            continue

        # Prend la variante 'default' si elle existe, sinon la première
        # disponible (la quasi-totalité des IGs n'ont qu'un seul variant, dont
        # la clé reflète ses axes plutôt que le mot littéral 'default').
        variants = ing_entry.get("variants", {})
        variant  = variants.get("default") or next(iter(variants.values()), {})
        ratio    = qty_g / 100.0

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

    # Chercher la variante demandée, sinon 'default' littéral, sinon la seule
    # variante disponible (la quasi-totalité des IGs n'ont qu'un variant, dont
    # la clé reflète ses axes plutôt que le mot littéral 'default' — ex.
    # 'milk_refrigerated_plain_plant', pas 'default').
    result = (variants.get(variant) or variants.get("default")
              or (next(iter(variants.values())) if len(variants) == 1 else None))

    if result:
        result            = dict(result)   # copie pour ne pas muter le cache
        result["_source"] = "industrial"
        return result

    # ── Résolution physique (fallback_slug / blend_components) ─────────────────
    # L'ingrédient n'est pas dans nutrition_v2 : on tente la résolution via
    # ingredient_physical.json (_fallback_slug ou _blend_components).
    logger.debug(
        "resolve_ingredient_nutrition : '%s' variant='%s' absent de nutrition_v2 "
        "→ résolution physique",
        ingredient_id, variant,
    )
    return _resolve_via_physical(ingredient_id)


# ── Résolution via ingredient_physical.json ────────────────────────────────────
#
# Deux mécanismes complémentaires, appliqués dans l'ordre :
#
#   1. _fallback_slug   : l'ingrédient délègue à un autre slug (ex: sriracha → hot_sauce).
#                         On rappelle resolve_ingredient_nutrition() sur le slug cible,
#                         avec une garde anti-boucle (_seen).
#
#   2. _blend_components: mélange d'épices défini par composition fixe en % de masse.
#                         On somme les nutriments pondérés de chaque composant,
#                         puis on normalise à 100 g.
#
# _resolve_via_physical() est intentionnellement privée (préfixe _) : seul
# resolve_ingredient_nutrition() doit l'appeler.
# ──────────────────────────────────────────────────────────────────────────────

_MAX_FALLBACK_DEPTH = 4   # garde anti-boucle / chaînes profondes


def _resolve_via_physical(
    ingredient_id: str,
    _seen: frozenset[str] | None = None,
    _depth: int = 0,
) -> dict:
    """
    Tente de résoudre la nutrition d'un slug via ingredient_physical.json.

    Ordre de résolution :
      1. _fallback_slug  → délégation récursive au slug cible
      2. _blend_components → moyenne pondérée par masse des composants
      3. Échec documenté  → {"_source": "physical", "_missing": True, …}

    Args:
        ingredient_id : slug à résoudre
        _seen         : ensemble des slugs déjà visités (anti-boucle)
        _depth        : profondeur de récursion courante

    Returns:
        dict des champs nutritionnels pour 100 g, avec clés privées de traçabilité.
    """
    seen = (_seen or frozenset()) | {ingredient_id}

    if _depth >= _MAX_FALLBACK_DEPTH:
        logger.warning(
            "_resolve_via_physical : profondeur max atteinte (%d) pour '%s'",
            _MAX_FALLBACK_DEPTH, ingredient_id,
        )
        return {"_source": "physical", "_missing": True, "_reason": "max_depth"}

    physical   = load_ingredient_physical()
    entry      = physical.get(ingredient_id, {})

    if not entry:
        logger.debug(
            "_resolve_via_physical : '%s' absent de ingredient_physical", ingredient_id,
        )
        return {"_source": "physical", "_missing": True, "_reason": "absent_physical"}

    # ── 1. Fallback slug ───────────────────────────────────────────────────────
    fallback_slug = entry.get("_fallback_slug")

    if fallback_slug is not None:
        # None explicite = non_nutritive (corn_husk, liquid_smoke)
        if fallback_slug == "" or entry.get("_fallback_reason") == "non_nutritive":
            logger.debug(
                "_resolve_via_physical : '%s' marqué non_nutritive → zéros", ingredient_id,
            )
            return {
                "_source":   "physical",
                "_slug":     ingredient_id,
                "_reason":   "non_nutritive",
                **{f: 0.0 for f in _NUTRIENT_FIELDS},
            }

        if fallback_slug in seen:
            logger.warning(
                "_resolve_via_physical : boucle détectée '%s' → '%s' (seen=%s)",
                ingredient_id, fallback_slug, seen,
            )
            return {"_source": "physical", "_missing": True, "_reason": "cycle_detected"}

        logger.debug(
            "_resolve_via_physical : '%s' → fallback '%s' (depth=%d)",
            ingredient_id, fallback_slug, _depth,
        )
        result = _resolve_via_physical(fallback_slug, _seen=seen, _depth=_depth + 1)

        # Si physical n'a rien, tenter nutrition_v2 directement (slug cible connu dans la DB)
        if result.get("_missing"):
            nutr_db   = load_nutrition_db()
            ing_entry = nutr_db.get(fallback_slug, {})
            direct    = ing_entry.get("variants", {}).get("default")
            if direct:
                result            = dict(direct)
                result["_source"] = "industrial"

        if not result.get("_missing"):
            result["_fallback_from"] = ingredient_id
            result["_fallback_to"]   = fallback_slug
        return result

    # ── 2. Blend components ────────────────────────────────────────────────────
    components = entry.get("_blend_components")

    if components:
        totals:    dict[str, float] = {}
        total_pct: float            = 0.0
        missing_comps:  list[str]   = []

        for comp in components:
            slug = comp.get("slug", "")
            pct  = float(comp.get("pct", 0))

            if not slug or pct <= 0:
                continue

            if slug in seen:
                logger.warning(
                    "_resolve_via_physical : boucle blend '%s' → '%s'",
                    ingredient_id, slug,
                )
                continue

            comp_nutr = _resolve_via_physical(slug, _seen=seen, _depth=_depth + 1)

            # Tenter nutrition_v2 si physical échoue (composant connu dans la DB)
            if comp_nutr.get("_missing"):
                nutr_db   = load_nutrition_db()
                ing_entry = nutr_db.get(slug, {})
                direct    = ing_entry.get("variants", {}).get("default")
                if direct:
                    comp_nutr = dict(direct)

            if comp_nutr.get("_missing"):
                missing_comps.append(slug)
                logger.debug(
                    "_resolve_via_physical blend '%s' : composant '%s' introuvable",
                    ingredient_id, slug,
                )
                continue

            weight = pct / 100.0
            for field in _NUTRIENT_FIELDS:
                val = comp_nutr.get(field)
                if isinstance(val, (int, float)):
                    totals[field] = totals.get(field, 0.0) + val * weight
            total_pct += pct

        if total_pct <= 0:
            return {
                "_source":  "physical",
                "_missing": True,
                "_reason":  "blend_all_components_missing",
                "_slug":    ingredient_id,
            }

        # Renormaliser si la somme des pct résolus < 100 (composants manquants)
        if missing_comps and total_pct < 100.0:
            factor = 100.0 / total_pct
            totals = {k: round(v * factor, 4) for k, v in totals.items()}
        else:
            totals = {k: round(v, 4) for k, v in totals.items()}

        result = {
            "_source":           "physical",
            "_blend_from":       ingredient_id,
            "_blend_total_pct":  total_pct,
            **totals,
        }
        if missing_comps:
            result["_blend_missing_components"] = missing_comps

        logger.debug(
            "_resolve_via_physical blend '%s' : %d/%d composants résolus (pct=%.1f%%)",
            ingredient_id, len(components) - len(missing_comps), len(components), total_pct,
        )
        return result

    # ── 3. Aucune résolution possible ─────────────────────────────────────────
    reason = entry.get("_usda_status", "no_fallback_no_blend")
    logger.debug(
        "_resolve_via_physical : '%s' sans fallback ni blend (%s)", ingredient_id, reason,
    )
    return {
        "_source":  "physical",
        "_missing": True,
        "_reason":  reason,
        "_slug":    ingredient_id,
    }
