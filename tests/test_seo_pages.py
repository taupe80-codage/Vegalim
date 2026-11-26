"""
tests/test_seo_pages.py — Pages HTML indexables (backend/api/routes/seo.py).

La SPA est routée « en dièse » : sans ces pages, aucune recette n'était
indexable. On vérifie le contenu, les données structurées schema.org, le plan
du site, robots.txt et la pertinence des thèmes.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.services import seo_pages as sp

client = TestClient(app)


def _jsonld(html: str) -> list[dict]:
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


@pytest.fixture(scope="module")
def built():
    return sp.build()


def test_index_liste_les_themes(built):
    themes, _ = built
    r = client.get("/idees")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "<h1>Idées de recettes végétariennes</h1>" in r.text
    for slug in themes:
        assert f'href="/idees/{slug}"' in r.text


def test_chaque_theme_a_assez_de_recettes(built):
    themes, _ = built
    assert len(themes) >= 60
    assert all(len(t.recipes) >= sp.MIN_RECIPES for t in themes.values())
    assert {"recettes-vegetariennes-riches-en-fer", "recettes-vegan",
            "recettes-de-saison-novembre", "cuisine-indienne-vegetarienne"} <= set(themes)


def test_page_theme_fer(built):
    themes, _ = built
    th = themes["recettes-vegetariennes-riches-en-fer"]
    r = client.get("/idees/recettes-vegetariennes-riches-en-fer")
    assert r.status_code == 200
    assert '<link rel="canonical"' in r.text and 'name="description"' in r.text
    assert all(float(i.nutr.get("iron") or 0) >= 4.2 for i in th.recipes)
    item_list = next(d for d in _jsonld(r.text) if d["@type"] == "ItemList")
    urls = [e["url"] for e in item_list["itemListElement"]]
    assert len(urls) == min(len(th.recipes), sp.MAX_LISTED)
    assert all("/recette/" in u for u in urls)
    # trié par fer décroissant
    irons = [float(i.nutr.get("iron") or 0) for i in th.recipes[:sp.MAX_LISTED]]
    assert irons == sorted(irons, reverse=True)


def test_themes_par_ingredient_sans_faux_amis(built):
    themes, _ = built
    courge = themes["recettes-vegetariennes-courge"].recipes
    assert not any("courgette" in i.title.lower() and "courge " not in i.title.lower() + " " for i in courge)
    pdt = themes["recettes-vegetariennes-pommes-de-terre"].recipes
    assert not any(all(t.startswith("sweet_potato") for t in i.tokens if "potato" in t) for i in pdt)
    # l'ingrédient pèse au moins 10 % du plat ou est nommé dans le titre
    carotte = themes["recettes-vegetariennes-carotte"]
    assert carotte.recipes[0].title.lower().startswith("carotte")


def test_fiche_recette_donnees_structurees():
    r = client.get("/recette/dal_harira_822880")
    assert r.status_code == 200
    rec = next(d for d in _jsonld(r.text) if d["@type"] == "Recipe")
    assert rec["name"] == "Harira express aux vermicelles"
    assert "30 ml huile d'olive" in rec["recipeIngredient"]       # libellé de l'application
    assert rec["recipeInstructions"] and rec["recipeInstructions"][0]["@type"] == "HowToStep"
    assert not rec["recipeInstructions"][0]["text"].lower().startswith("étape")
    assert rec["nutrition"]["calories"].endswith("kcal")
    assert "https://schema.org/VegetarianDiet" in rec["suitableForDiet"]
    assert rec["totalTime"].startswith("PT")
    assert 'href="/ui#/recette/dal_harira_822880"' in r.text


def test_pages_inconnues_404():
    assert client.get("/idees/n-existe-pas").status_code == 404
    assert client.get("/recette/n_existe_pas").status_code == 404


def test_plan_du_site_et_robots(built):
    themes, infos = built
    s = client.get("/sitemap.xml")
    assert s.status_code == 200 and "xml" in s.headers["content-type"]
    from backend.services.ingredient_sheet import public_ingredients
    # index, thèmes, recettes, puis l'index et les fiches ingrédients
    assert s.text.count("<url>") == 1 + len(themes) + len(infos) + 1 + len(public_ingredients())
    robots = client.get("/robots.txt").text
    assert "Sitemap: " in robots and "/sitemap.xml" in robots
    assert "Disallow: /recettes/" in robots
    assert not re.search(r"^Disallow: /(recette/|idees|images|ingredient/|ingredient$)", robots, re.M)


def test_adresse_publique_depuis_app_base_url(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://alim.exemple.fr/ui")
    r = client.get("/idees/recettes-vegan")
    assert '<link rel="canonical" href="https://alim.exemple.fr/idees/recettes-vegan">' in r.text


def test_csp_des_pages_html_et_de_l_api():
    css = client.get("/idees/recettes-vegan").headers["content-security-policy"]
    assert "style-src 'self'" in css
    assert client.get("/idees/style.css").headers["content-type"].startswith("text/css")
    # l'API /recettes garde la politique stricte (« /recette/ » ne la couvre pas)
    assert client.get("/recettes/dal_harira_822880").headers["content-security-policy"].startswith("default-src 'none'")
