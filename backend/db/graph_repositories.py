"""
graph_repositories.py — Repository layer pour les graphes culinaires.

Les graphes JSON sont des données de référence read-only (connaissance culinaire).
Ils sont chargés une seule fois en mémoire et exposés via une interface stable.

GRAPHES DISPONIBLES :
    culinary_knowledge_graph_v2    → 461KB  — connaissance culinaire globale
    ingredient_relation_graph      → 734KB  — relations entre ingrédients
    knowledge_graph_unified_v1     → 1.6MB  — graphe unifié (usage rare, lourd)
    flavor_graph                   → 14KB   — associations de saveurs
    ingredient_substitution_rules  → 17KB   — règles de substitution
    recipe_scoring_graph_v1        → 92KB   — pondérations scoring recettes
    recipe_nutrition_graph_v1      → 200KB  — nutrition par recette
    ingredient_cost_graph_v1       → 36KB   — coûts ingrédients
    seasonality (module)           → 53KB   — saisonnalité

USAGE :
    from backend.db.graph_repositories import GraphRepository, ScoringGraphRepository

    graph_repo = GraphRepository()
    nodes      = graph_repo.get_nodes("culinary")
    edges      = graph_repo.get_edges("culinary")

    score_repo = ScoringGraphRepository()
    weights    = score_repo.get_weights_for_diet("vegan")
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Chargement ─────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> Any:
    import json
    if not path.exists():
        logger.warning("Graphe introuvable : %s", path.name)
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Graphe chargé : %s (%d KB)", path.name, path.stat().st_size // 1024)
        return data
    except Exception as e:
        logger.error("Erreur chargement graphe %s : %s", path.name, e)
        return {}


# ── GraphRepository ────────────────────────────────────────────────────────────

class GraphRepository:
    """
    Accès générique aux graphes culinaires JSON.

    Chaque graphe est identifié par un alias court (voir GRAPH_ALIASES).
    Les graphes sont chargés à la première demande et mis en cache.
    """

    # Alias courts → nom de fichier (sans extension)
    # IMPORTANT : vérifier que le fichier existe dans backend/data/graphs/ avant d'ajouter un alias.
    GRAPH_ALIASES: dict[str, str] = {
        # fix: "culinary_knowledge_graph_v2" n'existe pas dans graphs/ → corrigé vers culinary_meta_graph_v1
        "culinary":           "culinary_meta_graph_v1",
        "culinary_knowledge": "knowledge_graph_unified_v1",   # graphe unifié complet (2.1MB, usage ponctuel)
        "relations":          "ingredient_relation_graph",
        "unified":            "knowledge_graph_unified_v1",
        "flavor":             "flavor_graph",
        "substitutions":      "ingredient_substitution_rules_graph_v1",
        "scoring":            "recipe_scoring_graph_v1",
        "nutrition":          "recipe_nutrition_graph_v1",
        "cost":               "ingredient_cost_graph_v1",
        "availability":       "ingredient_availability_graph_v1",
        # fix: flavor_pairing_graph_v1.json est un stub 215B (3 ingrédients) — le vrai graphe est flavor_graph
        "flavor_pairing":     "flavor_graph",
        "flavor_pairing_stub":"flavor_pairing_graph_v1",      # stub conservé si besoin
        "meta":               "unified_meta_graph",
    }

    def __init__(self):
        from backend.engine.config import GRAPHS_PATH
        self._root = GRAPHS_PATH
        self._cache: dict[str, Any] = {}

    def _get(self, alias: str) -> Any:
        """Retourne le graphe (depuis cache ou fichier)."""
        if alias not in self._cache:
            filename = self.GRAPH_ALIASES.get(alias, alias)
            path = self._root / f"{filename}.json"
            self._cache[alias] = _load_json(path)
        return self._cache[alias]

    def get_raw(self, alias: str) -> Any:
        """Retourne le graphe brut (dict ou list). Usage déconseillé — préférer les méthodes dédiées."""
        return self._get(alias)

    def get_nodes(self, alias: str) -> list[dict]:
        """Retourne la liste des nœuds du graphe."""
        data = self._get(alias)
        if isinstance(data, dict):
            return data.get("nodes", [])
        return []

    def get_edges(self, alias: str) -> list[dict]:
        """Retourne la liste des arêtes du graphe."""
        data = self._get(alias)
        if isinstance(data, dict):
            return data.get("edges", data.get("links", []))
        return []

    def get_metadata(self, alias: str) -> dict:
        """Retourne les métadonnées du graphe (version, description, etc.)."""
        data = self._get(alias)
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k not in ("nodes", "edges", "links")}
        return {}

    def available(self) -> list[str]:
        """Retourne la liste des alias disponibles."""
        return list(self.GRAPH_ALIASES.keys())

    def invalidate(self, alias: str | None = None) -> None:
        """Vide le cache pour un graphe ou tous les graphes."""
        if alias:
            self._cache.pop(alias, None)
        else:
            self._cache.clear()
        logger.info("Cache graphe invalidé : %s", alias or "all")


# ── ScoringGraphRepository ────────────────────────────────────────────────────

class ScoringGraphRepository:
    """
    Accès aux pondérations de scoring recettes.

    Source : recipe_scoring_graph_v1.json et scoring_weight_profiles_v1.json
    Ces données pilotent les coefficients du score engine.
    """

    def __init__(self):
        self._graph_repo = GraphRepository()
        from backend.engine.config import GRAPHS_PATH
        self._root = GRAPHS_PATH

    def get_weights_for_diet(self, diet: str | None = None) -> dict:
        """
        Retourne les pondérations de scoring selon le régime alimentaire.

        Args:
            diet : vegan | vegetarien | omnivore | None (→ défaut)

        Returns:
            dict de pondérations {dimension: weight}
        """
        data = self._graph_repo.get_raw("scoring")
        if not data:
            return self._default_weights()

        profiles = data.get("weight_profiles", {})
        if diet and diet in profiles:
            return profiles[diet]
        return profiles.get("default", self._default_weights())

    def get_scoring_dimensions(self) -> list[str]:
        """Retourne la liste des dimensions de scoring disponibles."""
        data = self._graph_repo.get_raw("scoring")
        return data.get("dimensions", []) if data else []

    def get_recipe_base_score(self, recipe_id: int) -> dict | None:
        """
        Retourne le score pré-calculé d'une recette si disponible.
        Peut être None si le graphe ne contient pas de scores pré-calculés.
        """
        data = self._graph_repo.get_raw("scoring")
        if not data:
            return None
        scores = data.get("recipe_scores", {})
        return scores.get(str(recipe_id)) or scores.get(recipe_id)

    @staticmethod
    def _default_weights() -> dict:
        """Pondérations par défaut (CDC_03c) si le graphe est absent."""
        return {
            "nutrition":     0.25,
            "saisonnalite":  0.15,
            "accessibilite": 0.15,
            "simplicite":    0.10,
            "diversite":     0.10,
            "ecologie":      0.15,
            "sante":         0.10,
        }


# ── SubstitutionGraphRepository ───────────────────────────────────────────────

class SubstitutionGraphRepository:
    """
    Accès aux règles de substitution d'ingrédients.

    Source : ingredient_substitution_rules_graph_v1.json
    """

    def __init__(self):
        self._graph_repo = GraphRepository()

    def get_substitutes(self, ingredient: str,
                        diet: str | None = None) -> list[dict]:
        """
        Retourne les substituts pour un ingrédient.
        Retourne [] sans crasher si l'ingrédient est absent du graphe.

        Args:
            ingredient : nom de l'ingrédient source
            diet       : filtre optionnel (ex : "vegan")

        Returns:
            Liste de dicts {substitute, ratio, notes, diet_compatible}
        """
        data = self._graph_repo.get_raw("substitutions")
        if not data:
            return []

        rules = data.get("substitutions", data)
        key = ingredient.lower()
        candidates = rules.get(key, [])

        if not candidates:
            # Tentative normalisée (accents → ascii)
            import unicodedata, re
            def _norm(s: str) -> str:
                nfkd = unicodedata.normalize("NFKD", s)
                a = "".join(c for c in nfkd if not unicodedata.combining(c))
                return re.sub(r"[\s\-_]+", " ", a.lower()).strip()
            norm_key = _norm(key)
            for rk, rv in rules.items():
                if _norm(rk) == norm_key:
                    candidates = rv
                    break

        if not candidates:
            # Ingrédient absent du graphe de substitution → log (best-effort)
            try:
                from backend.db.culinary_repositories import _log_missing_ingredient
                _log_missing_ingredient(ingredient, context="graph")
            except Exception:
                logger.warning("get_substitutes : erreur ignorée (repli)", exc_info=True)
            return []

        if diet:
            candidates = [
                c for c in candidates
                if diet in (c.get("diets") or []) or c.get("diet_compatible")
            ]
        return candidates

    def has_substitutes(self, ingredient: str) -> bool:
        return bool(self.get_substitutes(ingredient))


# ── FlavorGraphRepository ─────────────────────────────────────────────────────

class FlavorGraphRepository:
    """
    Accès aux associations de saveurs (flavor pairing).

    Source : flavor_graph.json + flavor_pairing_graph_v1.json
    """

    def __init__(self):
        self._graph_repo = GraphRepository()

    def get_flavor_profile(self, ingredient: str) -> dict | None:
        """Retourne le profil de saveur d'un ingrédient."""
        data = self._graph_repo.get_raw("flavor")
        if not data:
            return None
        profiles = data.get("flavor_profiles", data)
        return profiles.get(ingredient.lower())

    def get_pairings(self, ingredient: str) -> list[str]:
        """Retourne les ingrédients qui s'associent bien avec l'ingrédient donné."""
        data = self._graph_repo.get_raw("flavor_pairing")
        if not data:
            return []
        pairings = data.get("pairings", data)
        return pairings.get(ingredient.lower(), [])

    def compute_harmony_score(self, ingredients: list[str]) -> float:
        """
        Calcule un score d'harmonie pour une combinaison d'ingrédients.
        Score entre 0.0 (incompatible) et 1.0 (très harmonieux).
        """
        if len(ingredients) < 2:
            return 1.0

        pairs_ok = 0
        pairs_total = 0
        for i, ing_a in enumerate(ingredients):
            pairings_a = set(self.get_pairings(ing_a))
            for ing_b in ingredients[i + 1:]:
                pairs_total += 1
                if ing_b.lower() in pairings_a:
                    pairs_ok += 1

        return round(pairs_ok / pairs_total, 3) if pairs_total else 0.5


# ── CostGraphRepository ───────────────────────────────────────────────────────

class CostGraphRepository:
    """
    Accès aux coûts estimés des ingrédients.

    Source : ingredient_cost_graph_v1.json
    """

    def __init__(self):
        self._graph_repo = GraphRepository()

    def get_cost(self, ingredient: str, unit: str = "kg") -> float | None:
        """
        Retourne le coût estimé d'un ingrédient (€/kg par défaut).

        Returns:
            float ou None si inconnu.
        """
        data = self._graph_repo.get_raw("cost")
        if not data:
            return None
        costs = data.get("costs", data)
        entry = costs.get(ingredient.lower())
        if entry is None:
            return None
        if isinstance(entry, (int, float)):
            return float(entry)
        if isinstance(entry, dict):
            return float(entry.get(unit, entry.get("kg", 0)) or 0) or None
        return None

    def estimate_recipe_cost(self, ingredient_quantities: list[dict]) -> float:
        """
        Estime le coût total d'une recette.

        Args:
            ingredient_quantities : [{"name": "tomate", "quantity_g": 200}, ...]

        Returns:
            Coût total estimé en euros (0.0 si données insuffisantes).
        """
        total = 0.0
        for item in ingredient_quantities:
            name = item.get("name", "")
            qty_g = float(item.get("quantity_g") or 0)
            cost_per_kg = self.get_cost(name, "kg")
            if cost_per_kg and qty_g:
                total += (qty_g / 1000) * cost_per_kg
        return round(total, 2)
