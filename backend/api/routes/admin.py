"""
Routes admin : audit qualité, stats API.

MIGRATION étape 3 — imports remplacés :
  diet_flag_auto_engine.batch_update → rule_engine.diet.batch_update     ✅
  diet_flag_auto_engine.audit        → rule_engine.diet.audit             ✅

Conservés (engines actifs non encore migrés) :
  culinary_data_quality_engine       → étape 4
  auth_middleware                    → étape 4
  pipeline                           → étape 4
  search_token_generator             → étape 4
  duplicate_recipe_detector          → étape 4
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from backend.core.auth_deps import require_api_key

router = APIRouter(prefix="/admin", tags=["Admin"])


class PipelineRunRequest(BaseModel):
    profile: str           = Field(default="default")
    limit:   Optional[int] = Field(default=None, ge=1)


class DietFlagsRebuildRequest(BaseModel):
    force: bool = Field(default=False, description="Écraser les flags manuels")


@router.get("/quality_audit")
def quality_audit(_user = Depends(require_api_key)):
    """Audit qualité complet du dataset."""
    from backend.engine.culinary_data_quality_engine import run_quality_audit  # conservé
    return run_quality_audit()


@router.get("/missing_ingredients")
def missing_ingredients_report(_user = Depends(require_api_key)):
    """
    Rapport des ingrédients référencés en recette mais absents du dataset.
    Triés par fréquence décroissante.
    Permet d'identifier les lacunes à combler en priorité.
    """
    from backend.db.culinary_repositories import NutritionRepository
    report = NutritionRepository().get_missing_report()
    return {
        "total_missing": len(report),
        "unresolved": [e for e in report if not e.get("resolved")],
        "resolved":   [e for e in report if e.get("resolved")],
    }


@router.get("/api_stats")
def api_stats(_user = Depends(require_api_key)):
    """Statistiques d'utilisation de l'API."""
    from backend.engine.auth_middleware import get_api_stats                   # conservé
    return get_api_stats()


@router.post("/pipeline")
def pipeline_run(payload: PipelineRunRequest, _user = Depends(require_api_key)):
    """Relance le pipeline de traitement complet sur le dataset."""
    from backend.engine.pipeline import run                                    # conservé
    result = run(profile=payload.profile, limit=payload.limit, skip_errors=True)
    return {"total": result["total"], "skipped": result["skipped"],
            "errors": result["errors"][:10]}


@router.post("/diet_flags/rebuild")
def diet_flags_rebuild(
    payload: DietFlagsRebuildRequest = DietFlagsRebuildRequest(),
    _user = Depends(require_api_key),
):
    """
    Recalcule les diet_flags sur tout le dataset et sauvegarde.
    { "force": true } → écrase même les flags manuels.
    """
    from backend.engine.rule_engine.diet import batch_update                  # ✅ migré
    from backend.core.data_io import load_recipes, save_json
    from backend.engine.config import DATA_ROOT
    import json

    path = DATA_ROOT / "recipes" / "recipes.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    recipes_list = raw.get("recipes", raw) if isinstance(raw, dict) else raw

    result = batch_update(recipes_list, force=payload.force)

    out = {**raw, "recipes": recipes_list} if isinstance(raw, dict) else recipes_list
    save_json(path, out)
    load_recipes.cache_clear()

    return {
        "status":  "ok",
        "total":   result["total"],
        "updated": result["updated"],
        "skipped": result["skipped"],
        "stats":   result["stats"],
    }


@router.get("/diet_flags/audit")
def diet_flags_audit(_user = Depends(require_api_key)):
    """Retourne les recettes dont les diet_flags divergent des valeurs calculées."""
    from backend.engine.rule_engine.diet import audit                         # ✅ migré
    from backend.core.data_io import load_recipes
    recipes = list(load_recipes())
    return {
        "divergences": audit(recipes),
        "total":       len(recipes),
    }


@router.post("/search_tokens/rebuild")
def search_tokens_rebuild(_user = Depends(require_api_key)):
    """Regénère les search_tokens sur toutes les recettes."""
    from backend.engine.search_token_generator import batch_generate           # conservé
    from backend.core.data_io import load_recipes
    load_recipes.cache_clear()
    recipes = list(load_recipes())
    stats   = batch_generate(recipes, save=True)
    load_recipes.cache_clear()
    return {"status": "ok", **stats}


@router.post("/duplicate_check")
def duplicate_check(_user = Depends(require_api_key)):
    """Détecte les doublons dans le dataset."""
    from backend.engine.duplicate_recipe_detector import report               # conservé
    from backend.core.data_io import load_recipes
    load_recipes.cache_clear()
    return report(load_recipes())


@router.get("/quota")
def get_quota(_user: dict = Depends(require_api_key)):
    """Quota et informations de plan pour la clé API courante."""
    from backend.engine.auth_middleware import PLANS                           # conservé
    plan      = _user.get("plan", "free")
    plan_info = PLANS.get(plan, PLANS["free"])

    used = 0
    try:
        from backend.db.session import db_session
        from backend.db.repositories import QuotaRepository
        import hashlib
        raw_key = _user.get("raw_key", "")
        if raw_key:
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            with db_session() as db:          # fix: was next(get_db()) → session never closed
                used = QuotaRepository(db).get_today_count(key_hash)
    except Exception:
        pass

    limit = plan_info.get("daily_limit", 50)
    return {
        "plan":        plan,
        "description": plan_info.get("description", ""),
        "daily_limit": limit,
        "used_today":  used,
        "remaining":   max(0, limit - used),
        "reset":       "midnight UTC",
        "features":    {
            "mealplan":   plan_info.get("features", {}).get("mealplan", False),
            "import":     plan_info.get("features", {}).get("import", False),
            "simulation": plan_info.get("features", {}).get("simulation", False),
        },
        "headers": {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Used":  str(used),
            "X-Plan":            plan,
        },
    }
