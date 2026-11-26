"""
router.py — Agrégateur de routes ALIM v6.

Organisation par domaine :
  /auth      → authentification JWT B2C
  /profil    → préférences utilisateur
  /recettes  → recherche + recommandation + graphe
  /nutrition → AJR, carences, cycle féminin
  /planning  → plan semaine, liste courses, export .ics
  /admin     → audit qualité, stats, pipeline
  /contributions → recettes proposées par les utilisateurs + modération
  /avis      → notes et commentaires sur les recettes
  /notifications → nouveautés affichées sous la cloche
  /prototype → route GET simple sans auth (démo)
  /idees, /recette/{id}, /sitemap.xml, /robots.txt → pages HTML indexables
"""
from fastapi import APIRouter
from backend.api.routes import auth, profile, recipes, nutrition, planning, admin, ingredients, frigo, graph, contributions, reviews, notifications, seo, photo_proposals, recipe_versions

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
router.include_router(contributions.router)
router.include_router(reviews.router)
router.include_router(notifications.router)
router.include_router(seo.router)
router.include_router(photo_proposals.router)
router.include_router(recipe_versions.router)
