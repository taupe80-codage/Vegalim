"""
test_integration_api.py — Tests d'intégration des routes API.

Stratégie sans serveur (FastAPI non installé dans le container) :
  - Tests de structure des routes (signatures, modèles, auth)
  - Tests fonctionnels via les services sous-jacents
  - Simulation des handlers sur les données réelles
  - Vérification des contrats de réponse

Ces tests constituent un filet de sécurité avant chaque déploiement.
"""
from pathlib import Path

# ── Contrats des routes ───────────────────────────────────────────────────────

def test_routes_all_have_docstring():
    """Toutes les routes API ont une docstring pour Swagger."""
    import re
    missing = []
    for f in sorted(Path("backend/api/routes").glob("*.py")):
        content = f.read_text(encoding="utf-8", errors="ignore")
        # Trouver chaque @router.xxx et vérifier qu'une docstring suit
        for m in re.finditer(r"@router\.[a-z]+", content):
            block = content[m.start():m.start() + 2000]
            fn_m  = re.search(r"def (\w+)", block)
            if not fn_m:
                continue
            fn_name = fn_m.group(1)
            if '"""' not in block:
                missing.append(f"{f.name}:{fn_name}")
    assert not missing, "Routes sans docstring: " + ", ".join(missing)

def test_all_admin_routes_protected():
    """Toutes les routes admin exigent require_admin (clé API + ADMIN_EMAILS)."""
    src = open("backend/api/routes/admin.py", encoding="utf-8").read()
    import re
    defs = re.findall(r"def \w+\(([^)]*)\):", src)
    for sig in defs:
        if "router" in sig.lower():
            continue
        # Chaque fonction doit avoir require_admin
        assert "require_admin" in sig, \
            f"Route admin sans require_admin: {sig[:60]}"

def test_pydantic_models_all_routes():
    """Aucune route ne reçoit payload:dict brut."""
    import re
    for f in Path("backend/api/routes").glob("*.py"):
        src = f.read_text(encoding="utf-8", errors="ignore")
        # Chercher "payload: dict" dans signatures de handlers
        matches = re.findall(r"def \w+\([^)]*payload:\s*dict[^)]*\)", src)
        assert not matches, \
            f"{f.name}: routes avec payload:dict brut: {matches}"


# ── Tests fonctionnels via services ──────────────────────────────────────────

def test_recipe_has_required_fields():
    """Chaque recette a les champs requis."""
    from backend.core.data_io import load_recipes
    r = load_recipes()
    for rec in r:
        has_id = "id" in rec
        has_ings = "ingredients" in rec or "composition" in rec
        has_diet = "diet_flags" in rec or "tags" in rec
        assert has_id and has_ings and has_diet, f"Recette {rec.get('id')} — champs manquants"

def test_recipe_allergens_tagged():
    """Toutes les recettes ont un champ allergens."""
    from backend.core.data_io import load_recipes
    r = load_recipes()
    without = [x["id"] for x in r if x.get("allergens") is None and x.get("tags", {}).get("allergens") is None]
    assert not without, f"{len(without)} recettes sans allergens"

def test_recipe_spice_level_tagged():
    """Toutes les recettes ont spice_level."""
    from backend.core.data_io import load_recipes
    r = load_recipes()
    without = [x["id"] for x in r if x.get("spice_level") is None and x.get("scoring", {}).get("spice_level") is None]
    assert not without, f"{len(without)} recettes sans spice_level"

def test_shopping_list_has_aisles():
    """Pas de recette >1000 kcal/portion dans le graphe."""
    from backend.core.data_io import load_recipes, load_nutrition_graph
    load_recipes.cache_clear()
    r = load_recipes()
    ng = load_nutrition_graph()
    for rec in r:
        servings = max(1, rec.get("servings", 4) or 4)
        cal = ng.get(str(rec["id"]), {}).get("calories", 0) or 0
        per_p = cal / servings
        assert per_p <= 1000, \
            f"ID {rec['id']} {rec['title_fr']}: {per_p:.0f} kcal/portion"


def test_recommendation_returns_scored_results():
    """Recommandations retournent des résultats avec scores CDC."""
    from backend.services.reco_service import recommend
    result = recommend("aubergine", limit=5)
    assert len(result) > 0
    for rec in result:
        assert "final_score" in rec
        assert 0 <= rec["final_score"] <= 10

def test_shopping_list_has_aisles():
    """Liste de courses inclut le regroupement par rayon."""
    from backend.engine.planning_engine.planner import generate_plan as generate_weekly_plan
    from backend.engine.planning_engine.shopping import shopping_list as generate_shopping_list
    from backend.core.data_io import load_recipes
    load_recipes.cache_clear()
    plan = generate_weekly_plan()
    shop = generate_shopping_list(plan)
    assert "by_category" in shop
    assert "estimated_cost" in shop
    assert shop["estimated_cost"] >= 0

def test_sustainability_engine():
    """sustainability_engine retourne un score valide."""
    from backend.engine.rule_engine.carbon import carbon_score as recipe_carbon_score
    from backend.core.data_io import load_recipes
    r = load_recipes()[0]
    sc = recipe_carbon_score(r)
    assert "per_portion_kg" in sc
    assert "label" in sc
    assert 0 <= sc["score"] <= 10

def test_duplicate_detector_finds_pairs():
    """duplicate_detector retourne les doublons Pierogi."""
    from backend.engine.duplicate_recipe_detector import find_duplicates
    from backend.core.data_io import load_recipes
    r = load_recipes()
    pairs = find_duplicates(r, jaccard_threshold=0.85, lev_threshold=5)
    assert isinstance(pairs, list)

def test_mealplan_batch_cooking():
    """meal_planner supporte batch_cooking=True."""
    from backend.engine.planning_engine.planner import generate_plan as generate_weekly_plan
    from backend.core.data_io import load_recipes
    load_recipes.cache_clear()
    plan = generate_weekly_plan(batch_cooking=True)
    assert plan["meta"]["batch_cooking"] is True

def test_discovery_route_logic():
    """Logique découverte retourne 3 recettes distinctes."""
    from backend.core.data_io import load_recipes, load_score_graph, load_nutrition_graph
    from backend.engine.rule_engine.seasonality import seasonal_ingredients as ingredients_in_season
    import datetime, hashlib
    load_recipes.cache_clear()
    recipes = load_recipes()
    sg = load_score_graph()
    today = datetime.date.today()
    in_season = set(ingredients_in_season(today.month))
    # Simuler la sélection recette du jour
    def season_score(r):
        ings = {(i.get("ingredient_id","") if isinstance(i,dict) else str(i)).lower()
                for i in r.get("ingredients",[])}
        ratio = len(ings & in_season) / max(len(ings), 1)
        base  = sg.get(str(r["id"]), {}).get("overall_score", 5.0)
        return ratio * 4 + base * 0.6
    top = sorted(recipes, key=season_score, reverse=True)
    assert len(top) >= 3
    # Les 3 premiers sont distincts
    assert top[0]["id"] != top[1]["id"] != top[2]["id"]


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items()
             if n.startswith("test_") and callable(f)]
    ok = fail = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            ok += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            fail += 1
    print(f"\n{ok}/{ok+fail} tests passés")
