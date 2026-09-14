"""
pipeline.py — Orchestration de la transformation complète du dataset.

Ordre : normalize → enrich → servings → diet_flags → search_tokens
        → nutrition → adaptive_score → score_reliability → culinary_rules
        → global_scores → integrity_check

MIGRATION — imports archivés remplacés :
  dictionary_engine.normalize_list      → search_engine.resolver.normalize_list
  servings_engine.normalize_servings    → planning_engine.servings.normalize_servings
  diet_flag_auto_engine.apply_flags     → rule_engine.diet.apply_flags
  score_reliability_engine.attach       → score_engine.reliability.attach
  adaptive_score_engine_v4.score        → score_engine.quality.score_recipe
  culinary_rule_engine.validate / score → rule_engine.validation.validate_recipe

BUG CORRIGÉ : sg_d n'était pas défini avant utilisation (ligne ~130)

Point 7 — imports moteurs montés en tête de module (détection des erreurs au démarrage).
"""
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

from backend.engine.config import DATA_ROOT
from backend.core.data_io import (
    load_json, load_recipes, load_nutrition_graph,
    load_nutrition_db, load_ingredients_dict,
)

# ── Imports moteurs — montés en tête de module pour détection au démarrage ────
from backend.engine.search_engine.resolver   import normalize_list
from backend.engine.planning_engine.servings import normalize_servings
from backend.engine.rule_engine.diet         import apply_flags
from backend.engine.score_engine.reliability import attach as _attach
from backend.engine.score_engine.quality     import score_recipe
from backend.engine.rule_engine.validation   import validate_recipe
from backend.engine.nutrition_engine         import compute_nutrition
from backend.engine.search_token_generator   import generate_tokens as _gen_tokens


def _integrity_check(recipe: dict) -> list:
    """Vérifie l'intégrité d'une recette après traitement."""
    errors = []
    if not recipe.get("ingredients"):
        errors.append("ingredients manquants")
    if "nutrition" not in recipe:
        errors.append("nutrition manquante")
    if "adaptive_score" not in recipe:
        errors.append("adaptive_score manquant")
    return errors


def _enrich(recipe: dict) -> dict:
    """
    Enrichissement minimal : ajoute les champs dérivés absents.
    Complètement idempotent — ne modifie pas les champs déjà présents.
    """
    r = dict(recipe)
    if not r.get("slug"):
        title   = r.get("titles", {}).get("fr") or r.get("titles", {}).get("original") or ""
        r["slug"] = title.lower().replace(" ", "_").replace("(", "").replace(")", "")
    if not r.get("cuisine_origin"):
        from backend.core.data_io import recipe_cuisine
        r["cuisine_origin"] = recipe_cuisine(r)
    if not r.get("timing", {}).get("total_min"):
        prep = r.get("prep_time_min") or 0
        cook = r.get("cook_time_min") or 0
        if prep or cook:
            # Ecriture dans timing.total_min (chemin lu par tous les engines).
            # N'ECRIT PAS r["total_time_min"] a la racine -- aucun consommateur ne lit ce champ.
            if not isinstance(r.get("timing"), dict):
                r["timing"] = {}
            r["timing"]["total_min"] = prep + cook
    return r


def run(profile: str = "default", limit: int = None,
        skip_errors: bool = True) -> dict:
    """
    Pipeline complet sur le dataset.

    Args:
        profile     : profil de scoring adaptatif
        limit       : nb de recettes (None = toutes)
        skip_errors : si True, les recettes en erreur sont exclues avec log

    Returns:
        {"recipes": list, "total": int, "errors": list, "skipped": int, "timing_ms": int}
    """
    t0 = time.monotonic()

    # ── Chargement données ────────────────────────────────────────────────────
    try:
        recipes = load_recipes()
        ng      = load_nutrition_graph()
        sg      = load_json(DATA_ROOT / "graphs" / "recipe_scoring_graph_v1.json",
                            default={})
        nutr_db = load_nutrition_db()
        ings_d  = load_ingredients_dict()
    except Exception as e:
        raise RuntimeError(f"Échec chargement données : {e}")

    if limit:
        recipes = recipes[:limit]

    processed = []
    error_log = []

    for r in recipes:
        rid = str(r.get("id", ""))
        try:
            # 1. Normalisation tokens ingrédients
            r["ingredients"] = normalize_list(r.get("ingredients", []))

            # 2. Enrichissement champs dérivés
            r = _enrich(r)

            # 2a. Normalisation portions
            r = normalize_servings(r)

            # 2b. Diet flags (depuis ingrédients + techniques)
            r = apply_flags(r)

            # 2c. Search tokens
            r["search_tokens"] = _gen_tokens(r)

            # 3. Nutrition (graphe pré-calculé ou calcul à la volée)
            r["nutrition"] = ng.get(rid) or compute_nutrition(r)

            # 4. Scoring adaptatif
            score_result        = score_recipe(r, profile=profile)
            r["adaptive_score"] = score_result.get("adaptive_score", 0.0)

            # 5. Score reliability (couverture CIQUAL)
            r = _attach(r)

            # 5b. Validation règles culinaires (CDC_04)
            cul                      = validate_recipe(r)
            r["culinary_score"]      = cul.get("score", 10)
            r["culinary_violations"] = [
                v for v in cul.get("violations", [])
                if v.get("severity") == "critical"
            ]

            # 6. Scores pré-calculés depuis le graphe
            # P2.2 FIX : si la recette est absente du score_graph (nouvelles recettes,
            # IDs modifiés post-ingestion), on log un warning et on marque _audit_status
            # plutôt que de retourner 0 silencieusement.
            # global_score tombe en fallback sur adaptive_score (calculé à l'étape 4).
            sg_d = sg.get(rid, {})
            if not sg_d:
                _title = r.get("titles", {}).get("fr", "?")
                logger.warning(
                    "Recette %s ('%s') absente du score_graph — "
                    "global_score fallback sur adaptive_score. "
                    "Relancer /admin/pipeline pour recalculer.",
                    rid, _title
                )
                r.setdefault("_audit_status", {})["score_graph_missing"] = True

            r["global_score"] = sg_d.get("overall_score",   r.get("adaptive_score", 0))
            r["health_score"] = sg_d.get("nutrition_score", 0)
            r["flavor_score"] = sg_d.get("flavor_score",    0)

            # 7. Vérification intégrité
            errs = _integrity_check(r)
            if errs:
                error_log.append({"id": rid, "title": r.get("titles", {}).get("fr"), "errors": errs})
                if not skip_errors:
                    raise ValueError(f"Intégrité : {errs}")

            processed.append(r)

        except Exception as e:
            error_log.append({"id": rid, "title": r.get("title_fr", "?"),
                               "errors": [str(e)]})
            if not skip_errors:
                raise

    return {
        "recipes":   processed,
        "total":     len(processed),
        "errors":    error_log,
        "skipped":   len(error_log),
        "timing_ms": int((time.monotonic() - t0) * 1000),
    }


def run_and_save(output_path: str = None, **kwargs) -> dict:
    """Lance le pipeline et sauvegarde le résultat en JSON."""
    result = run(**kwargs)
    out    = (Path(output_path) if output_path
              else DATA_ROOT.parent / "processed" / "recipes_processed.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result
