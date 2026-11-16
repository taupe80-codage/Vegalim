"""Un ingrédient sans prix doit être signalé (fiche recette : « prix inconnu pour … »),
y compris quand il se cache dans une sous-recette chiffrée en partie."""
from backend.engine.planning_engine.shopping import recipe_cost

CATALOG = {"rice": {"packages": [{"qty": 1000, "unit": "g", "price": 2.0, "label": "1kg"}]}}


def _r(rid, compo, servings=2):
    return {"id": rid, "servings": servings,
            "composition": [{"ingredient": i, "quantity": q, "unit": "g"} for i, q in compo]}


def test_ingredient_sans_prix_liste():
    r = _r("x", [("rice", 500), ("tomatillo_raw", 200)])
    c = recipe_cost(r, CATALOG, {})
    assert c["total_eur"] == 1.0
    assert c["unknown"] == ["tomatillo_raw"]


def test_prix_manquant_dans_une_sous_recette():
    base = _r("base_salsa_x", [("rice", 100), ("tomatillo_raw", 100)])
    plat = _r("plat", [("rice", 500), ("base_salsa_x", 50)])
    c = recipe_cost(plat, CATALOG, {"base_salsa_x": base})
    assert c["unknown"] == ["tomatillo_raw"]
    assert c["n_unknown"] == 0          # la sous-recette elle-même a un prix (partiel)


def test_recette_complete_sans_avertissement():
    c = recipe_cost(_r("y", [("rice", 300)]), CATALOG, {})
    assert c["unknown"] == []


def test_estimate_price_expose_les_noms():
    from backend.core.data_io import load_recipes
    from backend.engine.planning_engine.budget import estimate_price
    sambar = next(r for r in load_recipes() if r["titles"]["fr"].startswith("Sambar tamoul"))
    p = estimate_price(sambar)
    assert p["complete"] is False
    assert p["unknown_ingredients"] and all(u["name_fr"] for u in p["unknown_ingredients"])
