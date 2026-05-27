"""
router.py — Agrégateur de routes ALIM v6.

Organisation par domaine :
  /auth      → authentification JWT B2C
  /profil    → préférences utilisateur
  /recettes  → recherche + recommandation + graphe
  /nutrition → AJR, carences, cycle féminin
  /planning  → plan semaine, liste courses, export .ics
  /admin     → audit qualité, stats, pipeline
  /prototype → route GET simple sans auth (démo)
"""
from fastapi import APIRouter
from backend.api.routes import auth, profile, recipes, nutrition, planning, admin, ingredients, frigo, graph

router = APIRouter()
router.include_router(auth.router)
router.include_router(profile.router)
router.include_router(recipes.router)
router.include_router(nutrition.router)
router.include_router(planning.router)
router.include_router(admin.router)
router.include_router(ingredients.router)
router.include_router(frigo.router)
router.include_router(graph.router)
