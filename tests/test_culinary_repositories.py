"""
test_culinary_repositories.py — Tests unitaires du repository layer culinaire.

Lance avec : pytest tests/test_culinary_repositories.py -v
"""
import pytest
from unittest.mock import patch, MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

FAKE_RECIPES = [
    {
        "id": 1,
        "title_fr": "Ratatouille provençale",
        "title_original": "Ratatouille",
        "composition": [
            {"name": "tomate"}, {"name": "courgette"}, {"name": "aubergine"}
        ],
        "diet_flags": {"vegan": True, "vegetarien": True},
        "nutrition": {"calories": 85, "protein": 2.5, "carbs": 10, "fat": 4},
        "technique": "mijotage",
    },
    {
        "id": 2,
        "title_fr": "Poulet rôti aux herbes",
        "title_original": "Roasted Chicken",
        "composition": [
            {"name": "poulet"}, {"name": "ail"}, {"name": "thym"}
        ],
        "diet_flags": {"vegan": False, "vegetarien": False},
        "nutrition": {"calories": 220, "protein": 30, "carbs": 2, "fat": 10},
        "technique": "rôtissage",
    },
    {
        "id": 3,
        "title_fr": "Soupe de lentilles",
        "title_original": "Lentil Soup",
        "composition": [{"name": "lentilles"}, {"name": "carotte"}, {"name": "tomate"}],
        "diet_flags": {"vegan": True, "vegetarien": True, "gluten_free": True},
        "nutrition": {"calories": 150, "protein": 10, "carbs": 25, "fat": 2},
        "technique": "mijotage",
    },
]

FAKE_NUTRITION = {
    "tomate":    {"calories": 18, "protein": 0.9, "carbs": 3.9, "fat": 0.2, "fiber": 1.2, "category": "légumes"},
    "courgette": {"calories": 17, "protein": 1.2, "carbs": 3.1, "fat": 0.3, "fiber": 1.0, "category": "légumes"},
    "poulet":    {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0, "category": "viandes"},
}

FAKE_INGREDIENTS = [
    {"id": "tomate_1", "name_fr": "tomate", "name_en": "tomato", "category": "légumes",
     "nutrition_key": "tomate", "substitutions": ["tomate cerise", "tomate séchée"]},
    {"id": "beurre_1", "name_fr": "beurre", "name_en": "butter", "category": "produits laitiers",
     "nutrition_key": "beurre", "substitutions": ["margarine", "huile de coco"]},
    {"id": "poulet_1", "name_fr": "poulet", "name_en": "chicken", "category": "viandes",
     "nutrition_key": "poulet", "substitutions": []},
]


# ── RecipeRepository ──────────────────────────────────────────────────────────

class TestRecipeRepository:

    @pytest.fixture(autouse=True)
    def patch_data(self):
        with patch("backend.db.culinary_repositories._recipes_raw", return_value=FAKE_RECIPES), \
             patch("backend.db.culinary_repositories._recipes_index",
                   return_value={r["id"]: r for r in FAKE_RECIPES}):
            yield

    def setup_method(self):
        from backend.db.culinary_repositories import RecipeRepository
        self.repo = RecipeRepository()

    def test_get_by_id_found(self):
        r = self.repo.get_by_id(1)
        assert r is not None
        assert r["title_fr"] == "Ratatouille provençale"

    def test_get_by_id_not_found(self):
        assert self.repo.get_by_id(999) is None

    def test_count(self):
        assert self.repo.count() == 3

    def test_list_ids(self):
        assert set(self.repo.list_ids()) == {1, 2, 3}

    def test_filter_by_diet_vegan(self):
        filtered = self.repo.filter_by_diet(FAKE_RECIPES, "vegan")
        ids = [r["id"] for r in filtered]
        assert 1 in ids and 3 in ids
        assert 2 not in ids

    def test_filter_by_diet_empty(self):
        result = self.repo.filter_by_diet(FAKE_RECIPES, "")
        assert len(result) == 3

    def test_filter_by_technique(self):
        result = self.repo.filter_by_technique(FAKE_RECIPES, "mijotage")
        assert len(result) == 2
        assert all("mijotage" in r["technique"] for r in result)

    def test_filter_by_ingredient(self):
        result = self.repo.filter_by_ingredient(FAKE_RECIPES, "tomate")
        ids = [r["id"] for r in result]
        assert 1 in ids and 3 in ids

    def test_search_by_text(self):
        result = self.repo.search_by_text("poulet")
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_search_by_text_empty_query(self):
        result = self.repo.search_by_text("")
        assert len(result) == 3

    def test_exclude_ids(self):
        result = self.repo.exclude_ids(FAKE_RECIPES, [1, 3])
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_get_many_by_ids(self):
        result = self.repo.get_many_by_ids([1, 3])
        assert len(result) == 2

    def test_get_nutrition(self):
        nutr = self.repo.get_nutrition(1)
        assert nutr["calories"] == 85

    def test_get_ingredients_list(self):
        ingr = self.repo.get_ingredients_list(1)
        assert len(ingr) == 3
        assert ingr[0]["name"] == "tomate"


# ── NutritionRepository ───────────────────────────────────────────────────────

class TestNutritionRepository:

    @pytest.fixture(autouse=True)
    def patch_data(self):
        with patch("backend.db.culinary_repositories._nutrition_raw",
                   return_value=FAKE_NUTRITION):
            yield

    def setup_method(self):
        from backend.db.culinary_repositories import NutritionRepository
        self.repo = NutritionRepository()

    def test_get_known(self):
        data = self.repo.get("tomate")
        assert data is not None
        assert data["calories"] == 18

    def test_get_unknown(self):
        assert self.repo.get("licorne") is None

    def test_get_case_insensitive(self):
        assert self.repo.get("TOMATE") is not None
        assert self.repo.get("Tomate") is not None

    def test_get_field(self):
        assert self.repo.get_field("tomate", "calories") == 18.0
        assert self.repo.get_field("tomate", "unknown_field") == 0.0
        assert self.repo.get_field("licorne", "calories") == 0.0

    def test_exists(self):
        assert self.repo.exists("tomate") is True
        assert self.repo.exists("licorne") is False

    def test_list_all_names(self):
        names = self.repo.list_all_names()
        assert "tomate" in names
        assert len(names) == 3

    def test_list_categories(self):
        cats = self.repo.list_categories()
        assert "légumes" in cats
        assert "viandes" in cats

    def test_coverage_full(self):
        cov = self.repo.coverage_for_recipe(["tomate", "courgette", "poulet"])
        assert cov == 1.0

    def test_coverage_partial(self):
        cov = self.repo.coverage_for_recipe(["tomate", "licorne", "dragon"])
        assert cov == pytest.approx(0.333, abs=0.01)

    def test_coverage_empty(self):
        assert self.repo.coverage_for_recipe([]) == 0.0

    def test_get_many(self):
        result = self.repo.get_many(["tomate", "poulet", "licorne"])
        assert "tomate" in result
        assert "poulet" in result
        assert "licorne" not in result


# ── IngredientRepository ──────────────────────────────────────────────────────

class TestIngredientRepository:

    @pytest.fixture(autouse=True)
    def patch_data(self):
        index = {}
        for item in FAKE_INGREDIENTS:
            for key in ("name_fr", "name_en", "id"):
                if item.get(key):
                    index[item[key].lower()] = item
        with patch("backend.db.culinary_repositories._ingredients_raw",
                   return_value=FAKE_INGREDIENTS), \
             patch("backend.db.culinary_repositories._ingredients_index",
                   return_value=index):
            yield

    def setup_method(self):
        from backend.db.culinary_repositories import IngredientRepository
        self.repo = IngredientRepository()

    def test_get_by_name_fr(self):
        item = self.repo.get_by_name("tomate")
        assert item is not None
        assert item["name_en"] == "tomato"

    def test_get_by_name_en(self):
        item = self.repo.get_by_name("tomato")
        assert item is not None
        assert item["name_fr"] == "tomate"

    def test_get_unknown(self):
        assert self.repo.get_by_name("inexistant") is None

    def test_get_substitutions(self):
        subs = self.repo.get_substitutions("beurre")
        assert "margarine" in subs
        assert "huile de coco" in subs

    def test_get_substitutions_empty(self):
        subs = self.repo.get_substitutions("poulet")
        assert subs == []

    def test_get_substitutions_unknown(self):
        subs = self.repo.get_substitutions("inexistant")
        assert subs == []

    def test_get_nutrition_key(self):
        key = self.repo.get_nutrition_key("tomate")
        assert key == "tomate"

    def test_exists(self):
        assert self.repo.exists("tomate") is True
        assert self.repo.exists("licorne") is False

    def test_count(self):
        assert self.repo.count() == 3

    def test_list_categories(self):
        cats = self.repo.list_categories()
        assert "légumes" in cats

    def test_search(self):
        results = self.repo.search("tom")
        assert any(r["name_fr"] == "tomate" for r in results)


# ── Intégration : data_access façade ─────────────────────────────────────────

class TestDataAccessFacade:

    @pytest.fixture(autouse=True)
    def patch_data(self):
        with patch("backend.db.culinary_repositories._recipes_raw", return_value=FAKE_RECIPES), \
             patch("backend.db.culinary_repositories._recipes_index",
                   return_value={r["id"]: r for r in FAKE_RECIPES}), \
             patch("backend.db.culinary_repositories._nutrition_raw",
                   return_value=FAKE_NUTRITION), \
             patch("backend.db.culinary_repositories._ingredients_raw",
                   return_value=FAKE_INGREDIENTS):
            yield

    def test_facade_recipe_count(self):
        from backend.db.data_access import get_data
        assert get_data.recipes.count() == 3

    def test_facade_nutrition_get(self):
        from backend.db.data_access import get_data
        assert get_data.nutrition.get("tomate") is not None

    def test_facade_ingredients_search(self):
        from backend.db.data_access import get_data
        results = get_data.ingredients.search("tomate")
        assert len(results) >= 1

    def test_resolve_nutrition_via_ingredient(self):
        """Test du chaînage IngredientRepository → NutritionRepository."""
        from backend.db.data_access import get_data
        with patch("backend.db.culinary_repositories._nutrition_raw",
                   return_value=FAKE_NUTRITION):
            nutr = get_data.ingredients.resolve_nutrition("tomate")
            assert nutr is not None
            assert nutr["calories"] == 18


# ═══════════════════════════════════════════════════════════════════════════════
# Tests complémentaires — lacunes identifiées lors de l'audit
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecipeRepositoryComplement:
    """
    Complète TestRecipeRepository sur les cas non couverts :
    filter_by_diet multi-régimes, search_by_text multi-termes,
    filter_by_ingredient, get_many_by_ids.
    """

    @pytest.fixture(autouse=True)
    def patch_data(self):
        with patch("backend.db.culinary_repositories._recipes_raw",
                   return_value=FAKE_RECIPES), \
             patch("backend.db.culinary_repositories._recipes_index",
                   return_value={r["id"]: r for r in FAKE_RECIPES}):
            yield

    def setup_method(self):
        from backend.db.culinary_repositories import RecipeRepository
        self.repo = RecipeRepository()

    # ── filter_by_diet ────────────────────────────────────────────────────────

    def test_filter_by_diet_vegetarien(self):
        """Régime végétarien : recettes 1 et 3 seulement."""
        with patch("backend.services.filter_service.match_diet",
                   side_effect=lambda r, d: r["diet_flags"].get("vegetarien", False)):
            result = self.repo.filter_by_diet(FAKE_RECIPES, "vegetarien")
        ids = [r["id"] for r in result]
        assert 1 in ids and 3 in ids
        assert 2 not in ids

    def test_filter_by_diet_gluten_free(self):
        """Régime gluten_free : seule la recette 3 le respecte."""
        with patch("backend.services.filter_service.match_diet",
                   side_effect=lambda r, d: r["diet_flags"].get("gluten_free", False)):
            result = self.repo.filter_by_diet(FAKE_RECIPES, "gluten_free")
        assert len(result) == 1
        assert result[0]["id"] == 3

    def test_filter_by_diet_inconnu_retourne_vide(self):
        """Régime inconnu : match_diet retourne False → liste vide."""
        with patch("backend.services.filter_service.match_diet",
                   return_value=False):
            result = self.repo.filter_by_diet(FAKE_RECIPES, "fruitarien")
        assert result == []

    def test_filter_by_diet_preserve_ordre(self):
        """L'ordre original des recettes doit être préservé."""
        with patch("backend.services.filter_service.match_diet",
                   return_value=True):
            result = self.repo.filter_by_diet(FAKE_RECIPES, "vegan")
        assert [r["id"] for r in result] == [r["id"] for r in FAKE_RECIPES]

    # ── search_by_text ────────────────────────────────────────────────────────

    def test_search_by_text_multi_termes(self):
        """Tous les termes doivent être présents (AND implicite).
        search_by_text lit titles.fr via le champ 'titles' — on passe un pool
        enrichi avec ce champ pour tester la logique multi-termes.
        """
        pool_with_titles = [
            dict(r, titles={"fr": r.get("title_fr", ""), "original": r.get("title_original", "")})
            for r in FAKE_RECIPES
        ]
        result = self.repo.search_by_text("soupe lentilles", recipes=pool_with_titles)
        assert len(result) == 1
        assert result[0]["id"] == 3

    def test_search_by_text_aucun_resultat(self):
        result = self.repo.search_by_text("quinoa")
        assert result == []

    def test_search_by_text_insensible_casse(self):
        result_lower = self.repo.search_by_text("ratatouille")
        result_upper = self.repo.search_by_text("RATATOUILLE")
        assert [r["id"] for r in result_lower] == [r["id"] for r in result_upper]

    def test_search_by_text_pool_personnalise(self):
        """Pool restreint passé en paramètre — seules les recettes du pool cherchées."""
        pool   = [r for r in FAKE_RECIPES if r["id"] in (1, 2)]
        result = self.repo.search_by_text("lentilles", recipes=pool)
        assert result == []   # recette 3 absente du pool

    def test_search_by_text_recherche_dans_composition(self):
        """La recherche doit matcher les noms dans la composition."""
        result = self.repo.search_by_text("aubergine")
        assert any(r["id"] == 1 for r in result)

    # ── filter_by_ingredient ─────────────────────────────────────────────────

    def test_filter_by_ingredient_present(self):
        FAKE_COMP = [
            dict(r, composition=[{"name": n} for n in names])
            for r, names in zip(FAKE_RECIPES, [
                ["tomate", "courgette"],
                ["poulet", "ail"],
                ["lentilles", "tomate"],
            ])
        ]
        result = self.repo.filter_by_ingredient(FAKE_COMP, "tomate")
        ids = [r["id"] for r in result]
        assert 1 in ids and 3 in ids
        assert 2 not in ids

    def test_filter_by_ingredient_absent_retourne_vide(self):
        result = self.repo.filter_by_ingredient(FAKE_RECIPES, "truffe_noire_xy99")
        assert result == []

    def test_filter_by_ingredient_insensible_casse(self):
        FAKE_COMP = [dict(FAKE_RECIPES[0], composition=[{"name": "Tomate"}])]
        r_lower = self.repo.filter_by_ingredient(FAKE_COMP, "tomate")
        r_upper = self.repo.filter_by_ingredient(FAKE_COMP, "TOMATE")
        assert len(r_lower) == len(r_upper)

    # ── get_many_by_ids ───────────────────────────────────────────────────────

    def test_get_many_by_ids_connus(self):
        result = self.repo.get_many_by_ids([1, 3])
        ids = [r["id"] for r in result]
        assert 1 in ids and 3 in ids
        assert 2 not in ids

    def test_get_many_by_ids_inconnu_ignore(self):
        result = self.repo.get_many_by_ids([1, 999])
        ids = [r["id"] for r in result]
        assert 1 in ids
        assert 999 not in ids

    def test_get_many_by_ids_liste_vide(self):
        result = self.repo.get_many_by_ids([])
        assert result == []
