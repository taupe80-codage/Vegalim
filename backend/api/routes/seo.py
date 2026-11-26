"""
seo.py — Pages HTML indexables par les moteurs de recherche (public).

  GET /idees                 index des thèmes
  GET /idees/style.css       feuille de style des pages
  GET /idees/{slug}          recettes d'un thème
  GET /recette/{id}          fiche recette (schema.org/Recipe)
  GET /ingredient            index des fiches ingrédients
  GET /ingredient/{slug}     fiche ingrédient : tableaux pour 100 g, saison, prix, recettes
  GET /sitemap.xml
  GET /robots.txt

Le contenu est calculé par backend/services/seo_pages.py.
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from backend.services import seo_pages as sp

router = APIRouter(tags=["Pages indexables"])

_CACHE = {"Cache-Control": "public, max-age=3600"}


def _base(request: Request) -> str:
    return sp.base_url(str(request.base_url))


@router.get("/idees", response_class=HTMLResponse, include_in_schema=False)
def idees_index(request: Request):
    """Index des thèmes de recettes (HTML, public)."""
    return HTMLResponse(sp.render_index(_base(request)), headers=_CACHE)


@router.get("/idees/style.css", include_in_schema=False)
def idees_css():
    """Feuille de style des pages indexables."""
    return Response(sp.CSS, media_type="text/css", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/idees/{slug}", response_class=HTMLResponse, include_in_schema=False)
def idees_theme(slug: str, request: Request):
    """Recettes d'un thème : liste et données ItemList (HTML, public)."""
    page = sp.render_theme(slug, _base(request))
    if page is None:
        raise HTTPException(status_code=404, detail="Thème inconnu")
    return HTMLResponse(page, headers=_CACHE)


@router.get("/recette/{recipe_id}", response_class=HTMLResponse, include_in_schema=False)
def recette_page(recipe_id: str, request: Request):
    """Fiche recette avec données schema.org/Recipe (HTML, public)."""
    page = sp.render_recipe(recipe_id, _base(request))
    if page is None:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    return HTMLResponse(page, headers=_CACHE)


@router.get("/ingredient", response_class=HTMLResponse, include_in_schema=False)
def ingredient_index(request: Request):
    """Index des fiches ingrédients, par rayon (HTML, public)."""
    return HTMLResponse(sp.render_ingredient_index(_base(request)), headers=_CACHE)


@router.get("/ingredient/{slug}", response_class=HTMLResponse, include_in_schema=False)
def ingredient_page(slug: str, request: Request):
    """Fiche ingrédient : valeurs pour 100 g, saison, prix, recettes (HTML, public)."""
    page = sp.render_ingredient(slug, _base(request))
    if page is None:
        raise HTTPException(status_code=404, detail="Ingrédient inconnu")
    return HTMLResponse(page, headers=_CACHE)


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request):
    """Plan du site : index, thèmes et fiches recettes."""
    return Response(sp.render_sitemap(_base(request)), media_type="application/xml", headers=_CACHE)


@router.get("/robots.txt", include_in_schema=False)
def robots(request: Request):
    """robots.txt : API exclue, plan du site déclaré."""
    return PlainTextResponse(sp.render_robots(_base(request)), headers=_CACHE)
