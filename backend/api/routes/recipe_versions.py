"""
routes/recipe_versions.py — Recettes modifiées par les membres (2026-11-26).

Public :
  POST   /recettes/{id}/personnaliser          fiche de la version modifiée (nutrition, prix,
                                               carbone, allergènes, étapes recalculés)
  GET    /recettes/{id}/remplacements?ingredient=…   remplaçants proposés pour un ingrédient

Membre connecté :
  GET    /mes-versions                         mes recettes modifiées enregistrées
  GET    /mes-versions/{recipe_id}             ma version d'une recette (404 : aucune)
  PUT    /mes-versions/{recipe_id}             enregistrer (ou remplacer) ma version
  DELETE /mes-versions/{recipe_id}             revenir à la recette d'origine

Format des modifications : services/recipe_edits.py.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.auth_deps import get_user
from backend.core.data_io import load_recipes
from backend.core.rate_limiter import check_rate_limit
from backend.db.models import RecipeVersion
from backend.db.session import get_db
from backend.services import recipe_edits as E

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Recettes modifiées"])

MAX_VERSIONS_PER_USER = 300


class EditRow(BaseModel):
    src:        Optional[int]   = Field(default=None, ge=0, le=500,
                                        description="Ligne de la composition de base (null : ajout)")
    orig:       Optional[str]   = Field(default=None, max_length=120,
                                        description="Ingrédient d'origine de cette ligne")
    ingredient: str             = Field(..., min_length=1, max_length=120)
    quantity:   Optional[float] = Field(default=None, gt=0, le=E.MAX_QTY,
                                        description="Quantité pour la recette entière (null : inchangée)")
    unit:       Optional[Literal["g", "ml"]] = None


class Edits(BaseModel):
    base: Literal["original", "vegan"] = "original"
    rows: list[EditRow] = Field(..., min_length=1, max_length=E.MAX_ROWS)

    def as_dict(self) -> dict:
        return {"base": self.base, "rows": [r.model_dump() for r in self.rows]}


class SaveVersion(Edits):
    servings: Optional[int] = Field(default=None, ge=1, le=100)


def _recipe(recipe_id: str) -> dict:
    recipe = next((r for r in load_recipes() if str(r.get("id", "")) == recipe_id), None)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recette introuvable.")
    return recipe


def _title(recipe: dict) -> str:
    return (recipe.get("titles") or {}).get("fr") or recipe.get("title_fr") or recipe.get("id", "")


def _serialize(v: RecipeVersion, recipe: dict | None = None) -> dict:
    out = {"recipe_id": v.recipe_id, "base": v.base, "rows": v.rows, "servings": v.servings,
           "updated_at": v.updated_at.isoformat() if v.updated_at else None}
    if recipe is not None:
        out["title"] = _title(recipe)
        try:
            out["changes"] = E.apply_edits(recipe, {"base": v.base, "rows": v.rows})["changes"]
        except E.EditError as e:
            out["changes"], out["error"] = [], str(e)
    return out


# ── Public ────────────────────────────────────────────────────────────────────

@router.post("/recettes/{recipe_id}/personnaliser")
def customize(recipe_id: str, payload: Edits, request: Request):
    """Fiche d'une version modifiée, sans l'enregistrer. **Public.**"""
    check_rate_limit(request, limit=90, window_seconds=60)
    recipe = _recipe(recipe_id)
    try:
        return E.custom_view(recipe, payload.as_dict())
    except E.EditError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/recettes/{recipe_id}/remplacements")
def replacements(recipe_id: str, request: Request,
                 ingredient: str = Query(..., min_length=1, max_length=120),
                 limit: int = Query(default=8, ge=1, le=20)):
    """Remplaçants proposés pour un ingrédient de la recette. **Public.**"""
    check_rate_limit(request, limit=90, window_seconds=60)
    _recipe(recipe_id)
    if not E.is_known_ingredient(ingredient):
        raise HTTPException(status_code=404, detail="Ingrédient inconnu.")
    return {"ingredient": ingredient, "name_fr": E.display_name(ingredient),
            "results": E.replacement_suggestions(ingredient, limit=limit)}


# ── Membre connecté ───────────────────────────────────────────────────────────

@router.get("/mes-versions")
def my_versions(user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Mes recettes modifiées enregistrées, avec la liste des modifications."""
    index = {str(r.get("id", "")): r for r in load_recipes()}
    rows = (db.query(RecipeVersion).filter(RecipeVersion.user_email == user["email"])
            .order_by(RecipeVersion.updated_at.desc()).all())
    # une recette retirée du catalogue : sa version n'a plus de fiche
    return {"results": [_serialize(v, index[v.recipe_id]) for v in rows if v.recipe_id in index]}


@router.get("/mes-versions/{recipe_id}")
def my_version(recipe_id: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Ma version d'une recette (404 : aucune)."""
    v = (db.query(RecipeVersion)
         .filter(RecipeVersion.user_email == user["email"], RecipeVersion.recipe_id == recipe_id).first())
    if not v:
        raise HTTPException(status_code=404, detail="Pas de version enregistrée pour cette recette.")
    return _serialize(v)


@router.put("/mes-versions/{recipe_id}")
def save_version(recipe_id: str, payload: SaveVersion, request: Request,
                 user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Enregistrer (ou remplacer) ma version d'une recette : une par recette."""
    check_rate_limit(request, limit=60, window_seconds=60)
    recipe = _recipe(recipe_id)
    edits = payload.as_dict()
    try:
        res = E.apply_edits(recipe, edits)
    except E.EditError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not res["changes"]:
        raise HTTPException(status_code=422, detail="Aucune modification à enregistrer.")
    q = db.query(RecipeVersion).filter(RecipeVersion.user_email == user["email"])
    v = q.filter(RecipeVersion.recipe_id == recipe_id).first()
    if v is None:
        if q.count() >= MAX_VERSIONS_PER_USER:
            raise HTTPException(status_code=429,
                                detail=f"{MAX_VERSIONS_PER_USER} recettes modifiées au plus : supprimez-en une.")
        v = RecipeVersion(user_email=user["email"], recipe_id=recipe_id)
        db.add(v)
    v.base, v.rows, v.servings = edits["base"], res["rows"], payload.servings
    v.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(v)
    return _serialize(v, recipe)


@router.delete("/mes-versions/{recipe_id}", status_code=204)
def delete_version(recipe_id: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Supprimer ma version : la fiche revient à la recette d'origine."""
    n = (db.query(RecipeVersion)
         .filter(RecipeVersion.user_email == user["email"], RecipeVersion.recipe_id == recipe_id)
         .delete())
    db.commit()
    if not n:
        raise HTTPException(status_code=404, detail="Pas de version enregistrée pour cette recette.")
    return Response(status_code=204)


def delete_user_versions(db: Session, email: str) -> int:
    """Suppression du compte : ses versions modifiées disparaissent avec lui."""
    return db.query(RecipeVersion).filter(RecipeVersion.user_email == email).delete()
