"""
orchestrator.py — Pipeline principal de recommandation.

Responsabilité UNIQUE : assembler les étapes dans le bon ordre.

Ce module NE contient PAS de logique métier — il délègue :
    - Profil & learning       → personalization.py
    - Score & enrichissement  → scoring.py
    - Recherche               → search_engine.core (nouveau package)
    - Filtrage                → filter_service
    - Données                 → data_access (repository layer)

Pipeline CDC_03c :
    1. Contexte utilisateur    (personalization.resolve_user_context)
    2. Recherche               (search_engine.core.search)
    3. Exclusions historique   (personalization.get_excluded_ids)
    4. Filtrage régime         (filter_service.apply_diet_filter)
    5. Scoring + enrichissement(scoring.batch_score)
    6. Personnalisation        (personalization.apply_learning)
    7. Cycle féminin           (cycle_engine.adjust_ranking — si has_cycle)

API publique (identique à l'ancien recommendation_engine.py) :
    recommend(query, email, diet_override, limit) → RecommendationResult
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ── RecommendationResult ──────────────────────────────────────────────────────

@dataclass
class RecommendationResult:
    """
    DTO de sortie du pipeline.
    Interface identique à l'ancien recommendation_engine.RecommendationResult.
    """
    recipes:       list[dict]
    meta:          dict       = field(default_factory=dict)
    query:         str        = ""
    diet:          str | None = None
    profile_used:  str        = "default"
    total:         int        = 0
    timing_ms:     int        = 0

    def to_dict(self) -> dict:
        return {
            "recipes":      self.recipes,
            "total":        self.total,
            "query":        self.query,
            "diet":         self.diet,
            "profile_used": self.profile_used,
            "timing_ms":    self.timing_ms,
            "meta":         self.meta,
        }


# ── Pipeline ──────────────────────────────────────────────────────────────────

def recommend(
    query:         str        = "",
    email:         str | None = None,
    diet_override: str | None = None,
    limit:         int        = 20,
) -> RecommendationResult:
    """
    Point d'entrée unique du moteur de recommandation.

    Args:
        query         : texte libre ("curry vegan", "salade lentilles"…)
        email         : email utilisateur — active profil + learning
        diet_override : filtre régime forcé (prioritaire sur le profil)
        limit         : nombre de recettes retournées

    Returns:
        RecommendationResult avec recipes, meta, timing.
    """
    t0 = time.monotonic()

    # ── Étape 1 : Contexte utilisateur ───────────────────────────────────────
    from backend.engine.reco_engine.personalization import (
        resolve_user_context,
        apply_learning,
        get_excluded_ids,
    )
    context = resolve_user_context(email, diet_override)

    # Normaliser context.diet vers la clé canonique immédiatement après résolution.
    # resolve_user_context peut retourner un alias brut ("sans_gluten", "vegetarienne"…)
    # issu du profil stocké avant l'étape 1. Le DTO RecommendationResult, les logs
    # et le monitoring doivent toujours voir la forme canonique.
    if context.diet:
        from backend.core.validators import normalize_diet
        context.diet = normalize_diet(context.diet)

    # ── Étape 2 : Recherche ──────────────────────────────────────────────────
    candidates = _search(query, limit * 3)

    # ── Étape 3 : Exclusions historique (dislikes) ───────────────────────────
    excluded = get_excluded_ids(context)
    if excluded:
        excluded_set = set(excluded)
        candidates   = [r for r in candidates if r.get("id") not in excluded_set]
        logger.debug("orchestrator: %d recettes exclues (historique)", len(excluded))

    # ── Étape 4 : Filtrage régime alimentaire ────────────────────────────────
    if context.diet:
        from backend.services.filter_service import apply_diet_filter
        candidates = apply_diet_filter(candidates, context.diet)

    # ── Étape 5 : Scoring + enrichissement ──────────────────────────────────
    from backend.engine.reco_engine.scoring import batch_score
    scored = batch_score(candidates, context)

    # ── Étape 6 : Personnalisation par apprentissage ─────────────────────────
    scored = apply_learning(scored, context)

    # ── Étape 7 : Ajustement cycle féminin ───────────────────────────────────
    if context.has_cycle:
        try:
            from backend.engine.cycle_engine import adjust_ranking
            cycle_phase = context.profile.get("cycle_phase")
            scored = adjust_ranking(scored, phase=cycle_phase)
            logger.debug("orchestrator: cycle ranking appliqué (phase=%s)", cycle_phase)
        except Exception as e:
            logger.debug("orchestrator: cycle_engine indisponible — %s", e)

    results = scored[:limit]
    elapsed = int((time.monotonic() - t0) * 1000)

    return RecommendationResult(
        recipes      = results,
        query        = query,
        diet         = context.diet,
        profile_used = context.profile_used,
        total        = len(results),
        timing_ms    = elapsed,
        meta         = _build_meta(len(candidates), len(scored), context),
    )


# ── Helpers privés ────────────────────────────────────────────────────────────

def _search(query: str, limit: int) -> list[dict]:
    """
    Recherche via search_engine.core (nouveau package unifié).
    Retourne [] en cas d'erreur — pipeline dégradé gracieusement.
    """
    try:
        from backend.engine.search_engine.core import search

        # Résolution des chemins : DATA_ROOT en priorité, fallback Path(__file__)
        # Le fallback est essentiel quand backend.engine.config est mocké (tests d'intégration).
        try:
            from backend.engine.config import DATA_ROOT
            index_path   = str(DATA_ROOT / "indexes"     / "search_index.json")
            mapping_path = str(DATA_ROOT / "ingredients" / "fr_to_en_mapping.json")
        except (ImportError, AttributeError):
            # config mocké ou DATA_ROOT absent — résolution relative à ce fichier
            _project_root = Path(__file__).resolve().parents[3]
            index_path   = str(_project_root / "backend" / "data" / "indexes"     / "search_index.json")
            mapping_path = str(_project_root / "backend" / "data" / "ingredients" / "fr_to_en_mapping.json")

        results = search(
            query_text   = query or "",
            index_path   = index_path,
            mapping_path = mapping_path,
            limit        = limit,
            include_context = False,
        )
        return [r for r in results if isinstance(r, dict)]
    except Exception as e:
        logger.error("orchestrator: search_engine indisponible — %s", e)
        return []


def _build_meta(n_candidates: int, n_scored: int, context) -> dict:
    from backend.engine.config import W_QUALITY, W_RELEVANCE
    return {
        "candidates_total":  n_candidates,
        "candidates_scored": n_scored,
        "learning_active":   context.has_learning,
        "cycle_active":      context.has_cycle,
        "profile_used":      context.profile_used,
        "w_quality":         W_QUALITY,
        "w_relevance":       W_RELEVANCE,
        "formula": (
            f"final = {W_QUALITY}×quality + {W_RELEVANCE}×relevance + learning_bonus"
        ),
    }
