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
from functools import lru_cache
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
            with os.fdopen(fd, "w", encoding="utf-8") as f:
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


@lru_cache(maxsize=1)
def _recipes_raw() -> list[dict]:
    """Cache en mémoire du dataset recettes. Rechargé uniquement au redémarrage."""
    from backend.engine.config import RECIPES_PATH
    data = _load_json(RECIPES_PATH)
    recipes = data.get("recipes", data) if isinstance(data, dict) else data
    logger.info("Recettes chargées en mémoire : %d recettes", len(recipes))
    return recipes


@lru_cache(maxsize=1)
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


@lru_cache(maxsize=1)
def _ingredients_raw() -> list[dict]:
    """Cache en mémoire du dictionnaire d'ingrédients."""
    from backend.engine.config import DICT_PATH
    data = _load_json(DICT_PATH)
    items = data.get("ingredients", data) if isinstance(data, dict) else data
    logger.info("Ingrédients chargés en mémoire : %d entrées", len(items))
    return items


@lru_cache(maxsize=1)
def _ingredients_index() -> dict[str, dict]:
    """Index nom → ingrédient pour accès O(1)."""
    index: dict[str, dict] = {}
    for item in _ingredients_raw():
        for key in ("name_fr", "name_en", "id"):
            if key in item and item[key]:
                index[str(item[key]).lower()] = item
    return index


@lru_cache(maxsize=1)
def _recipes_index() -> dict[int, dict]:
    """Index id → recette pour accès O(1)."""
    return {r["id"]: r for r in _recipes_raw() if "id" in r}


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
    logger.info("Caches culinaires invalidés")


# ── RecipeRepository ──────────────────────────────────────────────────────────

class RecipeRepository:
    """
    Accès aux recettes.

    Interface stable : les engines appellent ces méthodes.
    La source (JSON / PostgreSQL) est transparente.
    """

    # ── Lecture ───────────────────────────────────────────────────────────────

    def get_by_id(self, recipe_id: int) -> dict | None:
        """Retourne une recette par son id, ou None si introuvable."""
        return _recipes_index().get(recipe_id)

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

        Args:
            recipes : liste à filtrer
            diet    : vegan | vegetarien | gluten_free | sans_lactose | halal | kosher

        Returns:
            Liste filtrée (sous-ensemble de recipes).
        """
        if not diet:
            return recipes

        diet_key = diet.lower().replace("-", "_")
        result = []
        for r in recipes:
            flags = r.get("diet_flags") or {}
            # Support dict {diet: bool} et liste [diet, ...]
            if isinstance(flags, dict):
                if flags.get(diet_key) or flags.get(diet):
                    result.append(r)
            elif isinstance(flags, list):
                if diet_key in flags or diet in flags:
                    result.append(r)
        return result

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
    ) -> dict | None:
        """
        Retourne les données nutritionnelles pour un ingrédient.
        Retourne None sans crasher si absent, et logue le manque.

        Args:
            ingredient_name : nom en français ou anglais, insensible à la casse.
            context         : origine de l'appel ("scoring", "graph", "api"…).
            recipe_id       : id de la recette source (pour le log).
            recipe_title    : titre de la recette source (pour le log).
        """
        key = ingredient_name.strip().lower()
        db  = _nutrition_raw()

        # 1. Lookup exact
        if key in db:
            return db[key]

        # 2. Lookup normalisé (accents, tirets, underscores → espaces)
        normalized = self._normalize(key)
        for db_key, entry in db.items():
            if self._normalize(db_key) == normalized:
                return entry

        # 3. Absent → log + None (pas de crash)
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
        db  = _nutrition_raw()
        if key in db:
            return True
        normalized = self._normalize(key)
        return any(self._normalize(k) == normalized for k in db)

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

        Returns:
            dict de l'ingrédient, ou None si introuvable.
        """
        return _ingredients_index().get(name.strip().lower())

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

    def resolve_nutrition(
        self,
        ingredient_name: str,
        context: str = "unknown",
        recipe_id: Any = None,
        recipe_title: str | None = None,
    ) -> dict | None:
        """
        Résout directement les données nutritionnelles d'un ingrédient
        via son nutrition_key. Raccourci fréquemment utilisé par les engines.

        Retourne None sans crasher si introuvable. Log le manque une seule fois
        (NutritionRepository.get() logue si le fallback échoue aussi).
        """
        nutr_repo = NutritionRepository()
        nutr_key = self.get_nutrition_key(ingredient_name)
        if nutr_key:
            data = nutr_repo.get(nutr_key, context=context,
                                 recipe_id=recipe_id, recipe_title=recipe_title)
            if data is not None:
                return data
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
