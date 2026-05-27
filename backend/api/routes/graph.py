"""
routes/graph.py — Routes graphe ingrédient × cycle × analyse.

Extraites de recipes.py (748 lignes → separation of concerns).
Toutes ces routes nécessitent une authentification JWT.

Routes :
  GET  /recettes/graph/ingredient/{name}  — propriétés d'un ingrédient
  GET  /recettes/graph/cycle/{phase}      — ingrédients pour une phase du cycle
  POST /recettes/graph/analyze            — analyse complète d'une recette
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.core.auth_deps import get_user, get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recettes", tags=["Graphe"])


class GraphAnalyzeRequest(BaseModel):
    recipe:  dict = Field(..., description="Recette à analyser")
    profile: dict = Field(default_factory=dict)


@router.get("/graph/ingredient/{name}")
def graph_ingredient(name: str, user: dict = Depends(get_user)):
    """Propriétés d'un ingrédient depuis le graphe. **Authentifié.**"""
    from backend.engine.graph_engine import _load_graph
    data = _load_graph().get(name.lower())
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Ingrédient '{name}' absent du graphe",
        )
    return {"ingredient": name, **data}


@router.get("/graph/cycle/{phase}")
def graph_cycle(phase: str, user: dict | None = Depends(get_optional_user)):
    """Ingrédients recommandés pour une phase du cycle féminin. **Public si connecté.**"""
    from backend.engine.graph_engine import get_cycle_ingredients
    VALID = {
        "menstrual", "follicular", "ovulatory", "luteal",
        "menstrual_phase", "follicular_phase", "ovulatory_phase", "luteal_phase",
    }
    if phase not in VALID:
        raise HTTPException(
            status_code=400,
            detail=f"Phase invalide. Valeurs : {sorted({'menstrual','follicular','ovulatory','luteal'})}",
        )
    ings = get_cycle_ingredients(phase)
    return {"phase": phase, "ingredients": ings, "count": len(ings)}


@router.post("/graph/analyze")
def graph_analyze(payload: GraphAnalyzeRequest, user: dict = Depends(get_user)):
    """Analyse complète d'une recette via le graphe. **Authentifié.**"""
    from backend.engine.graph_engine import analyze_recipe
    if not payload.recipe.get("ingredients"):
        raise HTTPException(status_code=400, detail="'recipe.ingredients' requis")
    return analyze_recipe(payload.recipe, payload.profile)
