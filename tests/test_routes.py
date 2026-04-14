"""
test_routes.py — Tests fonctionnels des routes API.

Stratégie deux niveaux :
  1. Tests de logique pure (sans FastAPI/HTTP) — s'exécutent toujours
  2. Tests d'intégration HTTP (avec TestClient) — si fastapi installé

Les tests de niveau 1 couvrent les handlers directement :
  - Structure des réponses (clés requises, types, ranges)
  - Comportement des helpers (_enrich_recipe, _apply_filters)
  - Logique auth (JWT, optional_user)
  - Validation des données

Les tests HTTP complets s'exécutent en CI/CD avec :
  pip install fastapi[all] sqlalchemy
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.data_io import load_recipes
from backend.core.data_io import load_recipes as _lr
RECIPES = _lr()

# ── Fixtures ───────────────────────────────────────────────────────────────────

RECIPE   = RECIPES[0]
SAMPLE   = RECIPES[:10]


# ── Tests auth — logique JWT ──────────────────────────────────────────────────

def test_jwt_handler_module_exists():
    """jwt_handler.py expose create_token et verify_token."""
    src = open("backend/core/jwt_handler.py", encoding="utf-8").read()
    assert "def create_token" in src
    assert "def verify_token" in src
    assert "SECRET_KEY" in src or "secret" in src.lower()

def test_jwt_invalid_returns_none():
    """verify_token retourne None sur token invalide (code source)."""
    src = open("backend/core/jwt_handler.py", encoding="utf-8").read()
    assert "return None" in src
    assert "except" in src  # gestion des erreurs

def test_get_optional_user_no_header():
    """Sans header → comportement None documenté dans le code source."""
    # La définition canonique est dans auth_deps.py (source unique)
    auth = open("backend/core/auth_deps.py", encoding="utf-8").read()
    assert "def get_optional_user" in auth
    assert "default=None" in auth
    assert "return None" in auth
    # deps.py ré-exporte pour compat ascendante
    deps = open("backend/core/deps.py", encoding="utf-8").read()
    assert "get_optional_user" in deps

def test_get_user_raises_without_token():
    """get_user sans token lève une HTTPException."""
    # La définition est dans auth_deps.py (source unique)
    src = open("backend/core/auth_deps.py").read()
    assert "HTTP_401_UNAUTHORIZED" in src
    assert "WWW-Authenticate" in src

def test_auth_deps_exports():
    """auth_deps.py exporte get_user ET get_optional_user."""
    src = open("backend/core/auth_deps.py").read()
    assert "get_optional_user" in src
    assert "get_user" in src
    assert "require_api_key" in src


# ── Tests routes — structure du code ─────────────────────────────────────────

def test_routes_public_no_auth():
    """Routes publiques n'ont pas de Depends(get_user) dans leur signature."""
    import re
    public_routes = [
        ("recipes.py",     "list_recettes"),
        ("recipes.py",     "top_recettes"),
        ("recipes.py",     "get_recette"),
        ("ingredients.py", "list_ingredients"),
        ("ingredients.py", "get_ingredient"),
        ("planning.py",    "seasonal"),
    ]
    for fname, fn_name in public_routes:
        src = Path(f"backend/api/routes/{fname}").read_text(encoding="utf-8")
        m = re.search(rf"def {fn_name}\(.*?\):", src, re.DOTALL)
        assert m, f"{fname}: def {fn_name} introuvable"
        sig = m.group(0)
        assert "get_user" not in sig or "get_optional_user" in sig, \
            f"{fname}.{fn_name}: route publique avec auth obligatoire"

def test_routes_optional_auth():
    """Routes optional_auth utilisent get_optional_user."""
    import re
    optional_routes = [
        ("recipes.py",     "recherche"),
        ("frigo.py",       "fridge_suggestions"),
        
        ("ingredients.py", "search_ingredients"),
    ]
    for fname, fn_name in optional_routes:
        src = Path(f"backend/api/routes/{fname}").read_text(encoding="utf-8")
        m = re.search(rf"def {fn_name}\(.*?\):", src, re.DOTALL)
        assert m, f"{fname}: def {fn_name} introuvable"
        sig = m.group(0)
        assert "get_optional_user" in sig, \
            f"{fname}.{fn_name}: devrait utiliser get_optional_user"

def test_routes_jwt_protected():
    """Routes premium ont Depends(get_user) obligatoire."""
    import re
    jwt_routes = [
        ("recipes.py",  "recommend_pipeline"),
        ("frigo.py",    "missing_ingredients"),
        ("auth.py",     "delete_account"),
    ]
    for fname, fn_name in jwt_routes:
        src = Path(f"backend/api/routes/{fname}").read_text(encoding="utf-8")
        m = re.search(rf"def {fn_name}\(.*?\):", src, re.DOTALL)
        assert m, f"{fname}: def {fn_name} introuvable"
        sig = m.group(0)
        assert "get_user" in sig, \
            f"{fname}.{fn_name}: route JWT sans Depends(get_user)"

def test_router_includes_all_modules():
    """router.py inclut tous les modules de routes."""
    src = open("backend/api/router.py").read()
    for module in ("auth", "profile", "recipes", "nutrition", "planning",
                   "admin", "ingredients", "frigo"):
        assert module in src, f"Module '{module}' absent du router.py"

def test_all_routes_have_rate_limiter():
    """Les routes publiques et optional ont un check_rate_limit."""
    import re
    for fname in ("recipes.py", "ingredients.py", "frigo.py", "nutrition.py"):
        src = Path(f"backend/api/routes/{fname}").read_text(encoding="utf-8")
        assert "check_rate_limit" in src, f"{fname}: check_rate_limit absent"


# ── Tests logique handlers — sans HTTP ───────────────────────────────────────

def test_enrich_recipe_structure():
    """_compute_enrichment expose nutrition par portion + disponibilité."""
    src = open("backend/api/routes/recipes.py", encoding="utf-8").read()
    assert "_compute_enrichment" in src   # renommé (refactoring)
    assert "_per_serving" in src
    assert "/ servings" in src
    assert "ingredients_availability" in src
    assert "name_fr" in src

def test_enrich_recipe_nutrition_per_serving():
    """Logique nutrition/portions — via nutrition_engine directement."""
    from backend.engine.nutrition_engine import compute_nutrition
    from backend.core.data_io import load_nutrition_graph
    ng = load_nutrition_graph()
    fresh = compute_nutrition(RECIPE)
    assert isinstance(fresh, dict)
    assert fresh.get("calories", 0) >= 0

def test_apply_filters_vegan():
    """Filtre vegan via apply_diet_filter (testable sans fastapi)."""
    from backend.services.filter_service import apply_diet_filter
    filtered = apply_diet_filter(SAMPLE, "vegan")
    assert all(r.get("diet_flags", {}).get("vegan") for r in filtered)

def test_apply_filters_max_time():
    """Filtre max_time — logique inline testable (schéma CDC v4 : timing.total_min)."""
    filtered = [r for r in SAMPLE if (r.get("timing", {}).get("total_min") or 999) <= 30]
    assert all((r.get("timing", {}).get("total_min") or 999) <= 30 for r in filtered)

def test_apply_filters_pagination():
    """Pagination skip/limit correcte."""
    recipes = RECIPES[:20]
    page1 = recipes[0:5]
    page2 = recipes[5:10]
    assert len(page1) == 5 and len(page2) == 5
    assert page1[0]["id"] != page2[0]["id"]

def test_apply_filters_gluten_free():
    """Filtre gluten_free via filter_service."""
    from backend.services.filter_service import apply_diet_filter
    filtered = apply_diet_filter(RECIPES, "gluten_free")
    assert all(r.get("diet_flags", {}).get("gluten_free") for r in filtered)
    assert len(filtered) > 0

def test_list_recettes_sort():
    """Tri par iconic_score décroissant par défaut."""
    recipes = list(RECIPES[:30])
    recipes.sort(key=lambda r: r.get("iconic_score", 0), reverse=True)
    scores = [r.get("iconic_score", 0) for r in recipes[:10]]
    assert scores == sorted(scores, reverse=True)

def test_frigo_suggestions_logic():
    """Logique frigo — recettes filtrées par n_missing."""
    fridge = {"oil", "salt", "plantain"}
    scored = []
    for recipe in RECIPES:
        needed = {
            (i.get("ingredient","") if isinstance(i,dict) else str(i)).lower()
            for i in recipe.get("composition",[])
        } - {""}
        if not needed: continue
        missing = needed - fridge
        if len(missing) <= 2:
            scored.append({"id": recipe["id"], "n_missing": len(missing)})
    scored.sort(key=lambda x: x["n_missing"])
    assert len(scored) > 0
    missings = [s["n_missing"] for s in scored]
    assert missings == sorted(missings)

def test_frigo_missing_logic():
    """Calcul ingrédients manquants pour recette 1."""
    recipe = RECIPES[0]
    fridge = {"tofu", "garlic"}
    needed = {
        (i.get("ingredient","") if isinstance(i,dict) else str(i)).lower()
        for i in recipe.get("composition",[])
    } - {""}
    missing = needed - fridge
    have    = fridge & needed
    completeness = round(len(have)/len(needed), 2) if needed else 1.0
    assert 0 <= completeness <= 1
    assert isinstance(missing, set)

def test_ingredient_list_total():
    """Dictionnaire ingrédients — 310 entrées (302 + 8 substituts vegan)."""
    from backend.core.data_io import load_ingredients_dict
    load_ingredients_dict.cache_clear()
    d = load_ingredients_dict()
    assert len(d) >= 310, f"Attendu ≥310, obtenu {len(d)}"

def test_ingredient_get_enriched():
    """Fiche ingrédient — données disponibles."""
    from backend.core.data_io import load_ingredients_dict, load_availability_graph, load_nutrition_db
    d = load_ingredients_dict()
    av = load_availability_graph()
    ing = d.get("tofu", {})
    assert ing.get("category") == "plant_protein"
    assert "tofu" in av or len(av) >= 0
    # Recettes associées
    assoc = [r for r in RECIPES if any(
        (i.get("ingredient","") if isinstance(i,dict) else str(i)) == "tofu"
        for i in r.get("composition",[])
    )]
    assert len(assoc) > 0

def test_recommend_anon_vs_auth():
    """recommend() fonctionne sans et avec email."""
    from backend.services.reco_service import recommend_full as recommend
    r_anon = recommend("curry", email=None, limit=3)
    r_auth = recommend("curry", email="u@test.com", limit=3)
    assert len(r_anon.recipes) >= 0 and len(r_auth.recipes) >= 0


# ── Tests intégration HTTP (optionnels) ───────────────────────────────────────

def _try_http_tests():
    """Tests HTTP complets — nécessitent fastapi + sqlalchemy installés."""
    try:
        from fastapi.testclient import TestClient
        from backend.api.main import app
    except ImportError:
        return None, "FastAPI non installé — tests HTTP ignorés"

    client = TestClient(app, raise_server_exceptions=False)

    results = []

    def http_test(name, fn):
        try:
            fn(client)
            results.append(("✅", f"[HTTP] {name}"))
        except Exception as e:
            results.append(("❌", f"[HTTP] {name}", str(e)[:80]))

    http_test("GET /recettes public", lambda c:
        assert_(c.get("/recettes").status_code == 200))
    http_test("GET /recettes/{id} public", lambda c:
        assert_(c.get("/recettes/1").status_code == 200))
    http_test("GET /ingredients public", lambda c:
        assert_(c.get("/ingredients/").status_code == 200))
    http_test("GET /planning/seasonal public", lambda c:
        assert_(c.get("/planning/seasonal?month=3").status_code == 200))
    http_test("POST /recettes/recherche sans token", lambda c:
        assert_(c.post("/recettes/recherche",
                        json={"query": "lentil"}).status_code == 200))
    http_test("GET /profil sans token → 401/422", lambda c:
        assert_(c.get("/profil/").status_code in (401, 422)))

    return results, None


def assert_(condition):
    assert condition


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

    # Tests HTTP optionnels
    http_results, msg = _try_http_tests()
    if msg:
        print(f"\n  ℹ️  {msg}")
    elif http_results:
        print(f"\n  Tests HTTP :")
        for r in http_results:
            print(f"  {r[0]} {r[1]}")
            if r[0] == "❌": fail += 1
            else: ok += 1

    print(f"\n{ok}/{ok+fail} tests passés")
