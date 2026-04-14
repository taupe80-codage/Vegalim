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
