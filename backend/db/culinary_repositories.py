"""
culinary_repositories.py — Repository layer pour les données culinaires.

PRINCIPE :
    Les engines et services n'accèdent JAMAIS directement aux JSON.
    Ils passent par ces repositories qui abstraient la source de données.

    Aujourd'hui  → source = JSON (chargé en mémoire avec lru_cache)
    Demain       → source = PostgreSQL (changer _load_* sans toucher les engines)

USAGE :
    from backend.db.culinary_repositories import RecipeRepository, NutritionRepository

    repo = RecipeRepository()
    recipe     = repo.get_by_id(42)
    results    = repo.search(query="poulet", diet="vegan", limit=20)
    all_ids    = repo.list_ids()

    nutr_repo  = NutritionRepository()
    data       = nutr_repo.get("tomate")
    categories = nutr_repo.list_categories()

    ing_repo   = IngredientRepository()
    ingredient = ing_repo.get_by_name("ail")
    subs       = ing_repo.get_substitutions("beurre")
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime, timezone
from backend.core.data_cache import data_cached
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Log des ingrédients manquants ─────────────────────────────────────────────

_missing_lock = threading.Lock()


def _missing_log_path() -> Path:
    from backend.engine.config import DATA_ROOT
    return DATA_ROOT / "logs" / "missing_ingredients_report.json"


def _log_missing_ingredient(
    name: str,
    context: str = "unknown",
    recipe_id: Any = None,
    recipe_title: str | None = None,
) -> None:
    """
    Enregistre un ingrédient introuvable dans le fichier de log JSON.
    Thread-safe, best-effort : ne lève jamais d'exception.

    Format de chaque entrée :
        {ingredient, count, contexts, recipe_ids, first_seen, last_seen}
    """
    try:
        path = _missing_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()

        with _missing_lock:
            # Charger
            if path.exists():
                try:
                    entries: list[dict] = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    entries = []
            else:
                entries = []

            # Chercher une entrée existante
            existing = next((e for e in entries if e.get("ingredient") == name), None)
            if existing:
                existing["count"] = existing.get("count", 1) + 1
                existing["last_seen"] = now
                ctxs = existing.setdefault("contexts", [])
                if context not in ctxs:
                    ctxs.append(context)
                if recipe_id is not None:
                    rids = existing.setdefault("recipe_ids", [])
                    rid_str = str(recipe_id)
                    if rid_str not in rids:
                        rids.append(rid_str)
                if recipe_title:
                    existing.setdefault("recipe_titles", [])
                    if recipe_title not in existing["recipe_titles"]:
                        existing["recipe_titles"].append(recipe_title)
            else:
                entry: dict = {
                    "ingredient":   name,
                    "count":        1,
                    "contexts":     [context],
                    "recipe_ids":   [str(recipe_id)] if recipe_id is not None else [],
                    "recipe_titles":[recipe_title] if recipe_title else [],
                    "first_seen":   now,
                    "last_seen":    now,
                    "resolved":     False,
                }
                entries.append(entry)

            # Trier par count décroissant
            entries.sort(key=lambda e: e.get("count", 0), reverse=True)

            # Sauvegarder (écriture atomique)
            import os, tempfile
            fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)

        logger.warning(
            "ingredient_missing | name=%r | context=%s | recipe=%s",
            name, context, recipe_id or "—",
        )
    except Exception as exc:  # pragma: no cover
        logger.debug("_log_missing_ingredient failed (best-effort): %s", exc)


# ── Chargement JSON (une seule fois en mémoire) ────────────────────────────────

def _load_json(path: Path) -> Any:
    """Charge un fichier JSON. Lève RuntimeError si absent ou corrompu."""
    import json
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Fichier de données introuvable : {path}")
    except Exception as e:
        raise RuntimeError(f"Erreur chargement {path.name} : {e}") from e


@data_cached
def _recipes_raw() -> list[dict]:
    """Cache en mémoire du dataset recettes. Rechargé uniquement au redémarrage."""
    from backend.engine.config import RECIPES_PATH
    data = _load_json(RECIPES_PATH)
    recipes = data.get("recipes", data) if isinstance(data, dict) else data
    logger.info("Recettes chargées en mémoire : %d recettes", len(recipes))
    return recipes


@data_cached
def _nutrition_raw() -> dict[str, dict]:
    """
    Cache en mémoire de la base nutritionnelle (clé = nom ingrédient).
    Ignore la clé _meta du nouveau format v2.
    """
    from backend.engine.config import NUTRITION_PATH
    data = _load_json(NUTRITION_PATH)
    ingredients = data.get("ingredients", data) if isinstance(data, dict) else {}
    # Exclure la clé _meta introduite par nutrition_aligned v2
    clean = {k: v for k, v in ingredients.items()
             if not k.startswith("_") and isinstance(v, dict)}
    logger.info("Nutrition chargée en mémoire : %d clés de lookup", len(clean))
    return clean


@data_cached
def _base_recipe_excluded_raw() -> frozenset:
    """
    Ensemble des ingredient_keys exclus du lookup nutrition_v2.
    Ces clés ont une recette-base dédiée — la nutrition est calculée
    depuis la composition réelle et ne doit pas être interceptée
    par nutrition_v2 (y compris via lookup normalisé).
    Source : nutrition_v2.json _meta._base_recipe_excluded
    """
    from backend.engine.config import NUTRITION_PATH
    try:
        data = _load_json(NUTRITION_PATH)
        meta = data.get("_meta", data.get("metadata", {}))
        excluded = meta.get("_base_recipe_excluded", [])
        result = frozenset(str(k).lower().replace("-", "_") for k in excluded)
        logger.info("Base recipe excluded keys : %d", len(result))
        return result
    except Exception as exc:
        logger.warning("Erreur chargement _base_recipe_excluded : %s", exc)
        return frozenset()


@data_cached
def _ingredients_raw() -> list[dict]:
    """Cache en mémoire du dictionnaire d'ingrédients.

    ingredients_dictionary.json (build_dict_v2.py) a la structure imbriquée
    categories -> subcategories -> ingredient_groups -> {entry_key: entry},
    sans champ 'id'/'name_fr'/'name_en' interne (la clé EST l'identifiant,
    les noms sont dans canonical_name_fr/canonical_name_en). L'ancien code
    supposait un format à plat {"ingredients": [...]} et retombait
    silencieusement sur un dict vide-en-pratique — voir le même bug déjà
    corrigé dans backend/core/data_io.py::load_ingredients_dict().
    """
    from backend.engine.config import DICT_PATH
    data = _load_json(DICT_PATH)
    if isinstance(data, dict) and "ingredients" in data:
        items = data["ingredients"]  # ancien format à plat, rétrocompat
    elif isinstance(data, dict) and "categories" in data:
        items = []
        for cat in data["categories"].values():
            for sub in (cat or {}).get("subcategories", {}).values():
                for key, entry in (sub or {}).get("ingredient_groups", {}).items():
                    e = dict(entry)
                    e["id"] = key
                    e.setdefault("name_fr", e.get("canonical_name_fr", key))
                    e.setdefault("name_en", e.get("canonical_name_en", key))
                    items.append(e)
    else:
        items = data if isinstance(data, list) else []
    logger.info("Ingrédients chargés en mémoire : %d entrées", len(items))
    return items


@data_cached
def _ingredients_index() -> dict[str, dict]:
    """
    Index nom → ingrédient pour accès O(1).

    Deux passes pour rendre la résolution déterministe : de nombreuses
    entrées du dico partagent le même name_fr/name_en (ex: "mustard" ->
    mustard/mustard_oil_plant/mustard_raw_leaf/... partagent tous
    name_en="mustard") - une seule passe fait gagner arbitrairement la
    dernière entrée itérée (ex: get_by_name("garlic") résolvait vers
    garlic_roasted_dry, get_by_name("tomato") vers tomato_dried_in_oil,
    get_by_name("egg") vers egg_powder - trouvé lors de la revue manuelle,
    343/230/109 recettes affectées respectivement).

    Passe 1 (id) : prioritaire, jamais écrasée par la passe 2 - une clé
    de recherche qui correspond exactement à l'id d'une entrée doit
    toujours résoudre vers CETTE entrée.
    Passe 2 (name_fr/name_en) : fallback uniquement pour les clés non
    déjà résolues par un id exact - reste non-déterministe en cas de
    collision (dernier écrivain gagne), mais n'écrase plus jamais un
    match id exact.
    """
    index: dict[str, dict] = {}
    for item in _ingredients_raw():
        key = item.get("id")
        if key:
            index[str(key).lower()] = item
    for item in _ingredients_raw():
        for key in ("name_fr", "name_en"):
            if key in item and item[key]:
                k = str(item[key]).lower()
                if k not in index:
                    index[k] = item
    return index


@data_cached
def _derived_registry() -> dict[str, dict]:
    """
    Registre derived_from_base_recipes.json : nutrition per-100g + diet_profile
    calcules depuis la composition propre des recettes base_* (paneer, ghee,
    bechamel, sauces maison...), pour les recettes qui les referencent comme
    ingredient plutot que de les redecrire. Fiabilite = fiabilite de la
    recette source (pas une donnee de reference verifiee comme CIQUAL) - tenu
    volontairement separe de ingredients_dictionary.json pour cette raison.
    Cle = id complet de la recette base (ex: 'base_paneer_04e1db').
    """
    from backend.engine.config import DATA_ROOT
    path = DATA_ROOT / "ingredients" / "derived_from_base_recipes.json"
    if not path.exists():
        return {}
    data = _load_json(path)
    return data.get("recipes", {}) if isinstance(data, dict) else {}


@data_cached
def _recipes_index() -> dict:
    """
    Index id → recette pour accès O(1).

    Les IDs en v6 sont des strings (ex: 'dip_baba_ghanoush_dbd030').
    L'index est construit avec les IDs bruts du JSON (str).
    get_by_id() gère la résilience de type (str / int).
    """
    return {r["id"]: r for r in _recipes_raw() if "id" in r}


@data_cached
def _aliases_raw() -> dict[str, str]:
    """
    Cache en mémoire des aliases recette → nutrition_key.
    Section 'recipe_aliases' : {ingredient_recette: nutrition_key}
    """
    from backend.engine.config import DATA_ROOT
    path = DATA_ROOT / "nutrition" / "reference" / "nutrition_aliases_v6.json"
    if not path.exists():
        logger.warning("nutrition_aliases_v6.json introuvable — recipe_aliases désactivés")
        return {}
    try:
        data = _load_json(path)
        ra = data.get("recipe_aliases", {})
        logger.info("Recipe aliases chargés : %d entrées", len(ra))
        return ra
    except Exception as exc:
        logger.warning("Erreur chargement recipe_aliases : %s", exc)
        return {}


@data_cached
def _reference_db_raw() -> dict[str, dict]:
    """
    Cache en mémoire de la base de référence secondaire (reference_db.json).
    Utilisée pour résoudre les aliases __ref__/key introduits par le patch v6.
    Structure : {ingredient_key: {variant: {nutriments}}}
    """
    from backend.engine.config import DATA_ROOT
    path = DATA_ROOT / "nutrition" / "reference" / "reference_db.json"
    if not path.exists():
        logger.warning("reference_db.json introuvable — fallback __ref__ désactivé")
        return {}
    try:
        data = _load_json(path)
        ref = data.get("reference", data) if isinstance(data, dict) else {}
        logger.info("reference_db chargé : %d entrées", len(ref))
        return ref
    except Exception as exc:
        logger.warning("Erreur chargement reference_db : %s", exc)
        return {}


# Sentinel retourné pour les aliases __null__ (ingrédients sans valeur nutritive)
_NULL_NUTRITION: dict = {
    "calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0,
    "fiber": 0.0, "sugar": 0.0, "sodium": 0.0, "calcium": 0.0,
    "iron": 0.0, "vitamin_c": 0.0, "_source": "__null__",
}


def _resolve_ref_key(ref_key: str) -> dict | None:
    """
    Résout une clé __ref__/key depuis reference_db.json.
    Retourne le variant 'default' s'il existe, sinon le premier variant disponible.
    """
    ref_db = _reference_db_raw()
    entry = ref_db.get(ref_key)
    if not entry or not isinstance(entry, dict):
        return None
    # Priorité : default → raw → premier variant
    for preferred in ("default", "raw"):
        if preferred in entry and isinstance(entry[preferred], dict):
            return entry[preferred]
    first = next(iter(entry.values()), None)
    return first if isinstance(first, dict) else None


@data_cached
def _v32_ing_id_index() -> dict[str, str]:
    """
    Index inverse : _v32_id (tree ing_group ID) → clé racine dans nutrition_v2.
    Permet de résoudre les ingrédients via v32_ing_id quand nutrition_key est absent.
    Mapping 1:1 — chaque ing_id de l'arbre correspond à exactement une entrée N2.
    """
    db = _nutrition_raw()
    return {
        entry["_v32_id"]: n2_key
        for n2_key, entry in db.items()
        if isinstance(entry, dict) and entry.get("_v32_id")
    }


def _resolve_variant_key(db: dict, target_key: str) -> dict | None:
    """
    Résout une clé nutrition depuis db.
    Supporte deux formats :
      - "base"          → db[base]  (résoud vers le variant 'default' si présent)
      - "base/variant"  → db[base][variants][variant]

    Retourne un dict nutritionnel plat ou None si introuvable.
    """
    if "/" in target_key:
        base, variant = target_key.split("/", 1)
        base_entry = db.get(base)
        if base_entry is None:
            return None
        variant_data = base_entry.get("variants", {}).get(variant)
        if variant_data:
            return variant_data
        # Fallback vers default si variant demandé absent
        return base_entry.get("variants", {}).get("default") or None
    else:
        base_entry = db.get(target_key)
        if base_entry is None:
            return None
        # Retourner directement si c'est un dict plat (ancien format)
        if "calories_kcal" in base_entry or "calories" in base_entry:
            return base_entry
        # Format v2 : retourner variant 'default'
        variants = base_entry.get("variants", {})
        return variants.get("default") or (next(iter(variants.values())) if variants else None)


# États de cuisson reconnus par le système d'axes N2
_COOKED_STATES: frozenset[str] = frozenset({
    "boiled", "cooked", "steamed", "sauteed", "roasted",
    "fried", "baked", "grilled", "canned",
})
_RAW_STATES: frozenset[str] = frozenset({"raw"})
_DRY_STATES: frozenset[str] = frozenset({"dried"})


def _select_cooking_variant(entry: dict, use_cooked: bool) -> dict | None:
    """
    Sélectionne le variant approprié d'une entrée N2 selon l'état de cuisson souhaité.

    Si use_cooked=True  → cherche un variant avec axes.cooking_state ∈ _COOKED_STATES.
    Si use_cooked=False → retourne le variant 'default' (= cru/sec), ou le premier
                          variant dont les axes indiquent un état cru ou séché.

    Retourne None si aucun variant adéquat n'est trouvé (le caller peut alors
    utiliser un autre mécanisme de fallback, ex: cooked_nutrition_key).
    """
    variants = entry.get("variants", {})
    if not variants:
        return None

    if use_cooked:
        # Priorité : variant dont cooking_state est un état de cuisson reconnu
        for vk, vdata in variants.items():
            if not isinstance(vdata, dict):
                continue
            cs = vdata.get("axes", {}).get("cooking_state", "")
            if cs in _COOKED_STATES:
                return vdata
        # Aucun variant cuit dans cette entrée → signal au caller (None)
        return None
    else:
        # use_cooked=False : default d'abord (= état cru/sec canonical)
        default = variants.get("default")
        if default and isinstance(default, dict):
            return default
        # Sinon chercher explicitement raw ou dried
        for vk, vdata in variants.items():
            if not isinstance(vdata, dict):
                continue
            axes = vdata.get("axes", {})
            cs   = axes.get("cooking_state", "")
            ts   = axes.get("thermal_state", "")
            if cs in _RAW_STATES or ts in _DRY_STATES:
                return vdata
        # Dernier recours : premier variant disponible
        return next((v for v in variants.values() if isinstance(v, dict)), None)


def invalidate_caches() -> None:
    """
    Vide tous les caches mémoire.
    À appeler après mise à jour des fichiers JSON (scripts d'import).
    """
    _recipes_raw.cache_clear()
    _nutrition_raw.cache_clear()
    _ingredients_raw.cache_clear()
    _ingredients_index.cache_clear()
    _recipes_index.cache_clear()
    _aliases_raw.cache_clear()
    _base_recipe_excluded_raw.cache_clear()
    _reference_db_raw.cache_clear()
    logger.info("Caches culinaires invalidés")


# ── RecipeRepository ──────────────────────────────────────────────────────────

class RecipeRepository:
    """
    Accès aux recettes.

    Interface stable : les engines appellent ces méthodes.
    La source (JSON / PostgreSQL) est transparente.
    """

    # ── Lecture ───────────────────────────────────────────────────────────────

    def get_by_id(self, recipe_id: "int | str") -> dict | None:
        """
        Retourne une recette par son id, ou None si introuvable.

        Résilient au type : accepte str ou int.
        En v6 les IDs du dataset sont des strings (ex: 'dip_baba_ghanoush_dbd030').
        Fix : la signature était `int` alors que la route `/{recipe_id}/similaires`
        passe un str (path param FastAPI). L'index était jamais touché.
        """
        index = _recipes_index()
        # Tentative directe (type natif)
        if recipe_id in index:
            return index[recipe_id]
        # Fallback : essai avec l'autre type (str ↔ int)
        try:
            alt = int(recipe_id) if isinstance(recipe_id, str) else str(recipe_id)
            return index.get(alt)
        except (ValueError, TypeError):
            return index.get(str(recipe_id))

    def get_many_by_ids(self, ids: list[int]) -> list[dict]:
        """Retourne les recettes correspondant à la liste d'ids (ordre préservé)."""
        index = _recipes_index()
        return [index[i] for i in ids if i in index]

    def list_all(self) -> list[dict]:
        """Retourne toutes les recettes (read-only — ne pas modifier les dicts)."""
        return _recipes_raw()

    def list_ids(self) -> list[int]:
        """Retourne la liste de tous les ids."""
        return [r["id"] for r in _recipes_raw() if "id" in r]

    def count(self) -> int:
        return len(_recipes_raw())

    # ── Filtrage ──────────────────────────────────────────────────────────────

    def filter_by_diet(self, recipes: list[dict], diet: str) -> list[dict]:
        """
        Filtre une liste de recettes selon le régime alimentaire.

        Délègue entièrement à filter_service.match_diet() — source unique de
        vérité pour la logique de filtrage (aliases FR/EN, baseline végétarienne,
        health_scores pour diabete/hyperproteine).

        TOMBSTONE v6.19 — 2025-06 :
            L'ancienne implémentation faisait un accès direct à diet_flags via
            un diet_key calculé localement. Problèmes :
              - Ignorait tous les aliases français ("vegan", "sans_gluten"...).
              - Ne couvrait pas lactose_free, nut_free, diabete, hyperproteine.
              - N'appliquait pas la baseline végétarienne du projet.
            Remplacée par délégation à filter_service.match_diet() qui centralise
            toute cette logique. Ne pas réintroduire de logique ici.

        Args:
            recipes : liste à filtrer
            diet    : identifiant de régime — aliases FR/EN acceptés

        Returns:
            Liste filtrée (sous-ensemble de recipes), ordre préservé.
        """
        if not diet:
            return recipes

        from backend.services.filter_service import match_diet
        return [r for r in recipes if match_diet(r, diet)]

    def filter_by_technique(self, recipes: list[dict], technique: str) -> list[dict]:
        """Filtre par technique culinaire (ex : 'mijotage', 'rôtissage')."""
        t = technique.lower()
        return [
            r for r in recipes
            if t in str(r.get("technique", "")).lower()
        ]

    def filter_by_ingredient(self, recipes: list[dict], ingredient: str) -> list[dict]:
        """Retourne les recettes contenant l'ingrédient (recherche dans le titre ou la composition)."""
        term = ingredient.lower()
        result = []
        for r in recipes:
            ingredients_text = " ".join(
                str(i.get("name", "")) for i in (r.get("composition") or [])
            ).lower()
            if term in ingredients_text or term in r.get("titles", {}).get("fr", "").lower():
                result.append(r)
        return result

    def exclude_ids(self, recipes: list[dict], excluded: list[int]) -> list[dict]:
        """Retire les recettes dont l'id est dans excluded (historique, dislikes)."""
        excluded_set = set(excluded)
        return [r for r in recipes if r.get("id") not in excluded_set]

    # ── Recherche texte simple ────────────────────────────────────────────────

    def search_by_text(self, query: str, recipes: list[dict] | None = None) -> list[dict]:
        """
        Recherche textuelle basique sur titre et ingrédients.
        Pour la recherche avancée (vectorielle), utiliser SearchEngine.
        """
        if not query:
            return recipes if recipes is not None else self.list_all()

        pool = recipes if recipes is not None else _recipes_raw()
        terms = query.lower().split()
        results = []

        for r in pool:
            searchable = " ".join([
                str(r.get("titles", {}).get("fr", "")),
                str(r.get("titles", {}).get("original", "")),
                " ".join(str(i.get("name", "")) for i in (r.get("composition") or [])),
            ]).lower()
            if all(t in searchable for t in terms):
                results.append(r)

        return results

    # ── Champs spécifiques ────────────────────────────────────────────────────

    def get_nutrition(self, recipe_id: int) -> dict:
        """Retourne les données nutritionnelles d'une recette (ou {} si absentes)."""
        recipe = self.get_by_id(recipe_id)
        return recipe.get("nutrition") or {} if recipe else {}

    def get_ingredients_list(self, recipe_id: int) -> list[dict]:
        """Retourne la liste des ingrédients d'une recette."""
        recipe = self.get_by_id(recipe_id)
        return recipe.get("composition") or [] if recipe else []

    def get_diet_flags(self, recipe_id: int) -> dict | list:
        """Retourne les diet_flags d'une recette."""
        recipe = self.get_by_id(recipe_id)
        return recipe.get("diet_flags") or {} if recipe else {}


# ── NutritionRepository ───────────────────────────────────────────────────────

class NutritionRepository:
    """
    Accès à la base nutritionnelle (CIQUAL / USDA — dataset v2).

    Clés de lookup : nom d'ingrédient en français ou anglais (lowercase).
    Le dataset v2 expose 47 champs par ingrédient avec 2 387 clés de lookup.

    Contrat de non-crash :
        get() retourne None si l'ingrédient est absent ET logue le manque
        dans data/logs/missing_ingredients_report.json.
        Les engines traitent None comme "ingrédient inconnu" sans crasher.
    """

    # Champs macros (toujours présents)
    MACRO_FIELDS = (
        "calories", "protein", "carbs", "fat", "fiber",
        "sugar", "added_sugar", "sodium", "cholesterol",
    )

    # Champs micros étendus (v2)
    MICRO_FIELDS = (
        "calcium", "iron", "magnesium", "potassium", "phosphorus",
        "zinc", "selenium", "copper", "manganese",
        "vitamin_a", "vitamin_b1", "vitamin_b2", "vitamin_b3", "vitamin_b5",
        "vitamin_b6", "vitamin_b9", "vitamin_b12",
        "vitamin_c", "vitamin_d", "vitamin_e", "vitamin_k",
    )

    # Lipides détaillés
    FAT_FIELDS = (
        "saturated_fat", "monounsaturated_fat", "polyunsaturated_fat",
        "omega_3", "omega_6",
    )

    # Glycémie
    GLYCEMIC_FIELDS = ("glycemic_index", "glycemic_load")

    # Physique et taxonomie
    PHYSICAL_FIELDS = (
        "water", "density_g_per_ml", "average_unit_weight_g", "edible_pct",
    )

    META_FIELDS = (
        "ingredient_category", "ingredient_family", "ingredient_group",
        "health_tags", "aliases", "slug", "name_fr", "name_en",
    )

    # Champs standard (rétrocompatible v1 + nouveaux champs critiques)
    STANDARD_FIELDS = (
        "calories", "protein", "carbs", "fat", "fiber",
        "sugar", "added_sugar", "sodium", "calcium", "iron",
        "vitamin_c", "vitamin_a", "glycemic_index", "glycemic_load",
        "omega_3", "omega_6",
    )

    def get(
        self,
        ingredient_name: str,
        context: str = "unknown",
        recipe_id: Any = None,
        recipe_title: str | None = None,
        _depth: int = 0,
    ) -> dict | None:
        """
        Retourne les données nutritionnelles pour un ingrédient.
        Retourne None sans crasher si absent, et logue le manque.

        Chaîne de résolution (par ordre de priorité) :
          1. Lookup exact dans nutrition_v2
          2. Lookup normalisé dans nutrition_v2
          3. recipe_aliases (base/variant) dans nutrition_v2
          4. None + log

        Args:
            ingredient_name : nom en français ou anglais, insensible à la casse.
            context         : origine de l'appel ("scoring", "graph", "api"...).
            recipe_id       : id de la recette source (pour le log).
            recipe_title    : titre de la recette source (pour le log).
            _depth          : profondeur de récursion (usage interne).
        """
        if _depth > 3:
            return None

        key      = ingredient_name.strip().lower()
        key_slug = key.replace(" ", "_").replace("-", "_")
        db       = _nutrition_raw()
        excluded = _base_recipe_excluded_raw()   # keys avec recette-base dédiée

        # Guard exclusion : ne pas résoudre via nutrition_v2 si recette-base existe
        is_excluded = (key in excluded or key_slug in excluded)

        # 1. Lookup exact nutrition_v2 (si non exclu)
        if not is_excluded and key in db:
            return db[key]

        # 1b. Lookup direct base/variant (token deja au format feuille)
        #     Ex : 'seeds/hemp', 'butter/dairy', 'flour/wheat'
        #     Le token n'est pas une cle racine mais pointe directement vers un variant.
        if "/" in key and not is_excluded:
            resolved = _resolve_variant_key(db, key)
            if resolved is not None:
                logger.debug("direct leaf resolved | %r", key)
                return resolved

        # 2. Lookup normalise nutrition_v2 (si non exclu)
        if not is_excluded:
            normalized = self._normalize(key)
            for db_key, entry in db.items():
                if self._normalize(db_key) == normalized:
                    return entry

        # 3. recipe_aliases → base/variant dans nutrition_v2, __ref__/key ou __null__
        aliases = _aliases_raw()
        for candidate in (key, key_slug):
            target_key = aliases.get(candidate)
            if not target_key:
                continue

            # Convention __null__ : ingrédient sans valeur nutritive (eau, arôme, vin...)
            if target_key == "__null__":
                logger.debug("recipe_alias __null__ | %r → contribution zéro", ingredient_name)
                return _NULL_NUTRITION

            # Convention __ref__/key : lookup dans reference_db.json
            if target_key.startswith("__ref__/"):
                ref_key = target_key[len("__ref__/"):]
                ref_data = _resolve_ref_key(ref_key)
                if ref_data is not None:
                    logger.debug(
                        "recipe_alias __ref__ | %r → reference_db[%r]",
                        ingredient_name, ref_key,
                    )
                    return ref_data
                # Si ref_db absent/vide : continuer sans logguer
                continue

            # Résolution standard : base/variant dans nutrition_v2
            resolved = _resolve_variant_key(db, target_key)
            if resolved is not None:
                logger.debug(
                    "recipe_alias resolved | %r -> %r", ingredient_name, target_key
                )
                return resolved

        # 4. Absent → log + None
        if _depth == 0:
            _log_missing_ingredient(
                name=ingredient_name,
                context=context,
                recipe_id=recipe_id,
                recipe_title=recipe_title,
            )
        return None

    def get_field(
        self,
        ingredient_name: str,
        field: str,
        default: float = 0.0,
        context: str = "unknown",
    ) -> float:
        """Retourne un nutriment spécifique (ex : 'calories', 'protein')."""
        data = self.get(ingredient_name, context=context)
        if data is None:
            return default
        return float(data.get(field, default) or default)

    def get_many(
        self,
        names: list[str],
        context: str = "unknown",
        recipe_id: Any = None,
    ) -> dict[str, dict]:
        """
        Retourne les données nutritionnelles pour une liste d'ingrédients.
        Les ingrédients absents sont loggués mais ne font pas crasher.

        Returns:
            {nom_ingredient: {nutriments}} — clés absentes si non trouvées.
        """
        result = {}
        for name in names:
            data = self.get(name, context=context, recipe_id=recipe_id)
            if data is not None:
                result[name] = data
        return result

    def exists(self, ingredient_name: str) -> bool:
        """Retourne True si l'ingrédient est dans la base (sans logger)."""
        key = ingredient_name.strip().lower()
        key_slug = key.replace(" ", "_").replace("-", "_")
        db  = _nutrition_raw()
        if key in db:
            return True
        normalized = self._normalize(key)
        if any(self._normalize(k) == normalized for k in db):
            return True
        # Vérifier aussi les recipe_aliases
        aliases = _aliases_raw()
        for candidate in (key, key_slug):
            target = aliases.get(candidate)
            if target and target in db:
                return True
        return False

    def list_all_names(self) -> list[str]:
        """Retourne toutes les clés de lookup disponibles."""
        return list(_nutrition_raw().keys())

    def list_canonical_slugs(self) -> list[str]:
        """Retourne uniquement les slugs EN canoniques (champ 'slug')."""
        seen: set[str] = set()
        result = []
        for entry in _nutrition_raw().values():
            if isinstance(entry, dict):
                slug = entry.get("slug")
                if slug and slug not in seen:
                    seen.add(slug)
                    result.append(slug)
        return sorted(result)

    def list_categories(self) -> list[str]:
        """Retourne les catégories disponibles (ingredient_category v2 + category v1)."""
        cats: set[str] = set()
        for data in _nutrition_raw().values():
            if not isinstance(data, dict):
                continue
            cat = data.get("ingredient_category") or data.get("category")
            if cat:
                cats.add(cat)
        return sorted(cats)

    def coverage_for_recipe(
        self,
        ingredient_names: list[str],
        context: str = "scoring",
        recipe_id: Any = None,
    ) -> float:
        """
        Calcule le taux de couverture nutritionnelle pour une liste d'ingrédients.
        Utilisé par score_reliability_engine.

        Returns:
            float entre 0.0 et 1.0
        """
        if not ingredient_names:
            return 0.0
        found = sum(1 for n in ingredient_names if self.exists(n))
        for name in ingredient_names:
            if not self.exists(name):
                _log_missing_ingredient(name, context=context, recipe_id=recipe_id)
        return round(found / len(ingredient_names), 3)

    def get_missing_report(self) -> list[dict]:
        """Retourne le rapport des ingrédients manquants (lecture du fichier log)."""
        path = _missing_log_path()
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalise un nom pour comparaison floue (accents, tirets, espaces)."""
        import unicodedata
        nfkd = unicodedata.normalize("NFKD", name)
        ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
        return re.sub(r"[\s\-_]+", " ", ascii_str.lower()).strip()


# ── IngredientRepository ──────────────────────────────────────────────────────

class IngredientRepository:
    """
    Accès au dictionnaire d'ingrédients.

    Chaque ingrédient possède : id, name_fr, name_en, category, family,
    parent, nutrition_key, substitutions, ingredient_form, ingredient_product.
    """

    def get_by_name(self, name: str) -> dict | None:
        """
        Retrouve un ingrédient par son nom (fr ou en), insensible à la casse.

        Essaie dans l'ordre :
          1. Match direct (id, name_fr, name_en)
          2. Slash → underscore  (milk_animal/whole → milk_animal_whole)
          3. Préfixe avant le slash (chicken/breast → chicken)

        Returns:
            dict de l'ingrédient, ou None si introuvable.
        """
        idx = _ingredients_index()
        key = name.strip().lower()

        result = idx.get(key)
        if result:
            return result

        normalized = key.replace("/", "_")
        result = idx.get(normalized)
        if result:
            return result

        if "/" in key:
            prefix = key.split("/")[0]
            result = idx.get(prefix)
            if result:
                return result

        derived = _derived_registry().get(key)
        if derived:
            return {
                "id": key,
                "name_fr": derived.get("name_fr", key),
                "name_en": derived.get("name_en", key),
                "category": "derived_base_recipe",
                "diet_profile": derived.get("diet_profile"),
            }

        return None

    def get_by_id(self, ingredient_id: str) -> dict | None:
        """Retrouve un ingrédient par son id unique."""
        return _ingredients_index().get(str(ingredient_id).lower())

    def get_substitutions(self, ingredient_name: str) -> list[str]:
        """
        Retourne la liste des substituts pour un ingrédient.

        Returns:
            Liste de noms (peut être vide).
        """
        item = self.get_by_name(ingredient_name)
        if not item:
            return []
        subs = item.get("substitutions") or []
        if isinstance(subs, str):
            return [s.strip() for s in subs.split(",") if s.strip()]
        return list(subs)

    def get_nutrition_key(self, ingredient_name: str) -> str | None:
        """
        Retourne la clé de lookup dans NutritionRepository.
        Permet de faire le lien dictionnaire → nutrition.
        """
        item = self.get_by_name(ingredient_name)
        return item.get("nutrition_key") if item else None

    def get_cooked_nutrition_key(self, ingredient_name: str) -> str | None:
        """
        Retourne la clé N2 de la variante cuite de l'ingrédient (cooked_nutrition_key).
        Retourne None si l'ingrédient n'a pas de variante cuite connue.
        """
        item = self.get_by_name(ingredient_name)
        return (item.get("cooked_nutrition_key") if item else None) or None

    def get_v32_ing_id(self, ingredient_name: str) -> str | None:
        """Retourne le v32_ing_id (lien vers l'arbre d'ingrédients) pour cet ingrédient."""
        item = self.get_by_name(ingredient_name)
        return item.get("v32_ing_id") if item else None

    def resolve_nutrition(
        self,
        ingredient_name: str,
        context: str = "unknown",
        recipe_id: Any = None,
        recipe_title: str | None = None,
        use_cooked: bool = False,
        cooking_state: str | None = None,
    ) -> dict | None:
        """
        Résout directement les données nutritionnelles d'un ingrédient.

        Ordre de résolution (priorité décroissante) :
          0. ingredient_map_v2 (resolve_cooking_gid) — pont recette→dict v2
             Couvre les IDs sémantiques courts ('garlic', 'carrot', 'onion/yellow')
             avec gestion de l'état de cuisson (cooking_variants).
          1. nutrition_key du dictionnaire ingrédients (entrée directe N2)
          2. v32_ing_id → index N2 (_v32_id)
          3. Fallback nom libre (NutritionRepository.get)

        Args:
            use_cooked    : True si le plat est chaud (cook_min > 0).
            cooking_state : État de cuisson explicite depuis meta.state de la
                            composition ('boiled', 'roasted', 'sauteed', 'raw'…).
                            Prioritaire sur use_cooked si fourni.

        Retourne None sans crasher si introuvable.
        """
        nutr_repo = NutritionRepository()
        db        = _nutrition_raw()

        # ── Étape 0 : ingredient_map_v2 (résolution recette → dict v2) ──────────
        # Court-circuit direct : si l'ID recette est dans le map, on résout
        # le bon group_id (avec cuisson si nécessaire) et on charge l'entrée N2.
        try:
            from backend.core.data_io import resolve_cooking_gid
            mapped_gid = resolve_cooking_gid(
                ingredient_name,
                use_cooked=use_cooked,
                cooking_state=cooking_state,
            )
            if mapped_gid:
                n2_entry = db.get(mapped_gid)
                if n2_entry and isinstance(n2_entry, dict):
                    variants = n2_entry.get("variants", {})
                    if variants:
                        # Toujours un seul variant dans nutrition_v2 — prendre le premier
                        vdata = next(iter(variants.values()))
                        if isinstance(vdata, dict) and vdata.get("calories_kcal") is not None:
                            logger.debug(
                                "ingredient_map_v2 | %r → %r (use_cooked=%s, state=%s)",
                                ingredient_name, mapped_gid, use_cooked, cooking_state,
                            )
                            return vdata
        except Exception as exc:
            logger.debug("ingredient_map_v2 lookup failed for %r: %s", ingredient_name, exc)

        nutr_key = self.get_nutrition_key(ingredient_name)

        if nutr_key:
            if "/" in nutr_key:
                # Clé base/variant explicite — résolution directe (pas de navigation axe)
                resolved = _resolve_variant_key(db, nutr_key)
                if resolved is not None:
                    logger.debug(
                        "dict_nutrition_key base/variant | %r → %r",
                        ingredient_name, nutr_key,
                    )
                    return resolved
            else:
                # Navigation par axe cooking_state dans l'entrée N2 consolidée.
                # C'est la logique principale : une seule entrée racine, variants raw+cooked.
                entry = db.get(nutr_key)
                if entry and isinstance(entry, dict) and entry.get("variants"):
                    variant = _select_cooking_variant(entry, use_cooked)
                    if variant is not None:
                        logger.debug(
                            "axis_variant | %r → %r (use_cooked=%s)",
                            ingredient_name, nutr_key, use_cooked,
                        )
                        return variant
                    elif not use_cooked:
                        # use_cooked=False sans variant raw trouvé → default ou premier
                        fallback = (
                            entry.get("variants", {}).get("default")
                            or next(iter(entry.get("variants", {}).values()), None)
                        )
                        if fallback and isinstance(fallback, dict):
                            return fallback
                # Fallback : cooked_nutrition_key (entrées non encore consolidées)
                if use_cooked:
                    cooked_key = self.get_cooked_nutrition_key(ingredient_name)
                    if cooked_key:
                        resolved = _resolve_variant_key(db, cooked_key + "/default")
                        if resolved is None:
                            resolved = _resolve_variant_key(db, cooked_key)
                        if resolved is not None:
                            logger.debug(
                                "cooked_nutrition_key fallback | %r → %r",
                                ingredient_name, cooked_key,
                            )
                            return resolved

                # Fallback plat (entrées sans variants — ancien format)
                resolved = _resolve_variant_key(db, nutr_key + "/default")
                if resolved is not None:
                    return resolved
                data = nutr_repo.get(nutr_key, context=context,
                                     recipe_id=recipe_id, recipe_title=recipe_title)
                if data is not None and data.get("calories_kcal") is not None:
                    return data

        # 1b. Fallback via v32_ing_id → index N2 (_v32_id)
        #     Couvre les entrées du dictionnaire avec un lien arbre mais sans nutrition_key,
        #     ou dont la résolution nutrition_key a échoué.
        item = self.get_by_name(ingredient_name)
        v32_id = item.get("v32_ing_id") if item else None
        if v32_id:
            n2_key = _v32_ing_id_index().get(v32_id)
            if n2_key:
                entry = db.get(n2_key)
                if entry and isinstance(entry, dict) and entry.get("variants"):
                    variant = _select_cooking_variant(entry, use_cooked)
                    if variant is not None:
                        logger.debug(
                            "v32_ing_id fallback | %r → v32=%r → n2=%r (use_cooked=%s)",
                            ingredient_name, v32_id, n2_key, use_cooked,
                        )
                        return variant
                    fallback = (
                        entry.get("variants", {}).get("default")
                        or next(iter(entry.get("variants", {}).values()), None)
                    )
                    if fallback and isinstance(fallback, dict):
                        logger.debug(
                            "v32_ing_id fallback (default) | %r → v32=%r → n2=%r",
                            ingredient_name, v32_id, n2_key,
                        )
                        return fallback

        # 2b. Recipe aliases : résolution directe sans passer par le dictionnaire
        #     Couvre les ingrédients recettes non présents dans ingredients_dictionary.json
        #     (ex: coconut_milk, olive_oil, shallot, silken_tofu…)
        #     Supporte aussi les conventions __null__ et __ref__/key.
        aliases = _aliases_raw()
        key = ingredient_name.strip().lower()
        key_slug = key.replace(" ", "_").replace("-", "_")
        for candidate in (key, key_slug):
            target_key = aliases.get(candidate)
            if not target_key:
                continue

            # __null__ : ingrédient sans contribution nutritive
            if target_key == "__null__":
                return _NULL_NUTRITION

            # __ref__/key : lookup dans reference_db.json
            if target_key.startswith("__ref__/"):
                ref_key = target_key[len("__ref__/"):]
                ref_data = _resolve_ref_key(ref_key)
                if ref_data is not None:
                    return ref_data
                continue

            # Résolution standard dans nutrition_v2
            db = _nutrition_raw()
            resolved = _resolve_variant_key(db, target_key)
            if resolved is not None:
                logger.debug(
                    "recipe_alias resolve_nutrition | %r → %r",
                    ingredient_name, target_key,
                )
                return resolved

        # Fallback : derived_from_base_recipes.json (paneer, ghee, bechamel,
        # sauces maison... referencees comme ingredient par d'autres recettes)
        derived = _derived_registry().get(key)
        if derived:
            logger.debug("derived_base_recipe resolve_nutrition | %r → %r",
                         ingredient_name, key)
            return dict(derived.get("nutrition_per_100g") or {})

        # Fallback : lookup direct sur le nom d'origine
        return nutr_repo.get(ingredient_name, context=context,
                             recipe_id=recipe_id, recipe_title=recipe_title)

    def list_by_category(self, category: str) -> list[dict]:
        """Retourne tous les ingrédients d'une catégorie."""
        cat = category.lower()
        return [
            i for i in _ingredients_raw()
            if str(i.get("category", "")).lower() == cat
        ]

    def list_categories(self) -> list[str]:
        """Retourne la liste des catégories disponibles."""
        return sorted({
            str(i.get("category", ""))
            for i in _ingredients_raw()
            if i.get("category")
        })

    def search(self, query: str) -> list[dict]:
        """Recherche d'ingrédients par nom (fr ou en) — retourne les 20 premiers."""
        q = query.strip().lower()
        results = []
        for item in _ingredients_raw():
            name_fr = str(item.get("name_fr", "")).lower()
            name_en = str(item.get("name_en", "")).lower()
            if q in name_fr or q in name_en:
                results.append(item)
            if len(results) >= 20:
                break
        return results

    def exists(self, name: str) -> bool:
        return self.get_by_name(name) is not None

    def count(self) -> int:
        return len(_ingredients_raw())
