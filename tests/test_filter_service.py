"""
tests/test_filter_service.py — Tests unitaires filter_service.

Couvre :
  - match_diet()         : aliases FR/EN, baseline végétarienne, health_scores,
                           régime inconnu, diet vide
  - apply_diet_filter()  : comportement liste, pass-through vide, ordre préservé
  - normalize_diet()     : canonicalisation depuis validators
  - RecipeRepository.filter_by_diet() : vérification délégation à filter_service

Lance avec : pytest tests/test_filter_service.py -v
"""
import pytest
from unittest.mock import patch


# ── Recettes de test ──────────────────────────────────────────────────────────

def _make_recipe(rid=1, flags=None, health=None, vegetarian=True):
    base_flags = {"vegetarian": vegetarian}
    if flags:
        base_flags.update(flags)
    return {
        "id": rid,
        "diet_flags": base_flags,
        "health_scores": health or {},
    }


VEGAN_RECIPE          = _make_recipe(1, {"vegan": True,  "gluten_free": True,  "lactose_free": True,  "nut_free": True})
VEGETARIAN_RECIPE     = _make_recipe(2, {"vegan": False, "gluten_free": False, "lactose_free": True})
NON_VEGETARIAN_RECIPE = _make_recipe(3, {"vegan": False, "gluten_free": True}, vegetarian=False)
GLUTEN_FREE_RECIPE    = _make_recipe(4, {"vegan": False, "gluten_free": True,  "lactose_free": True})
DIABETE_RECIPE        = _make_recipe(5, {"vegan": True},  health={"glycemic_category": "low",    "high_protein": False})
HIGH_PROTEIN_RECIPE   = _make_recipe(6, {"vegan": True},  health={"glycemic_category": "medium", "high_protein": True})
NUT_FREE_RECIPE       = _make_recipe(7, {"vegan": True,  "nut_free": True})

ALL_RECIPES = [
    VEGAN_RECIPE, VEGETARIAN_RECIPE, NON_VEGETARIAN_RECIPE,
    GLUTEN_FREE_RECIPE, DIABETE_RECIPE, HIGH_PROTEIN_RECIPE, NUT_FREE_RECIPE,
]


# ── Tests match_diet ──────────────────────────────────────────────────────────

class TestMatchDiet:

    def setup_method(self):
        from backend.services.filter_service import match_diet
        self.match = match_diet

    # ── Diet vide / None ─────────────────────────────────────────────────────

    def test_empty_diet_always_true(self):
        assert self.match(NON_VEGETARIAN_RECIPE, "") is True

    def test_none_diet_always_true(self):
        assert self.match(NON_VEGETARIAN_RECIPE, None) is True

    # ── Baseline végétarienne ────────────────────────────────────────────────

    def test_non_vegetarian_blocked_on_vegan(self):
        assert self.match(NON_VEGETARIAN_RECIPE, "vegan") is False

    def test_non_vegetarian_blocked_on_gluten_free(self):
        """Baseline bloquée même si le flag gluten_free est True."""
        assert self.match(NON_VEGETARIAN_RECIPE, "gluten_free") is False

    def test_non_vegetarian_blocked_on_sans_gluten(self):
        assert self.match(NON_VEGETARIAN_RECIPE, "sans_gluten") is False

    def test_vegetarian_check_self_no_double_check(self):
        """Le check vegetarien sur lui-même n'est pas bloqué par la baseline."""
        assert self.match(VEGETARIAN_RECIPE, "vegetarien") is True

    def test_absent_vegetarian_flag_passthrough(self):
        """Si vegetarian est absent (données partielles), pas de blocage."""
        recipe_no_flag = {"id": 99, "diet_flags": {}, "health_scores": {}}
        assert self.match(recipe_no_flag, "gluten_free") is True

    # ── Aliases FR ───────────────────────────────────────────────────────────

    def test_alias_sans_gluten(self):
        assert self.match(VEGAN_RECIPE, "sans_gluten") is True
        assert self.match(VEGETARIAN_RECIPE, "sans_gluten") is False

    def test_alias_vegetarienne(self):
        assert self.match(VEGETARIAN_RECIPE, "vegetarienne") is True

    def test_alias_sans_lactose(self):
        assert self.match(VEGAN_RECIPE, "sans_lactose") is True
        assert self.match(GLUTEN_FREE_RECIPE, "sans_lactose") is True

    def test_alias_dairy_free(self):
        assert self.match(VEGAN_RECIPE, "dairy_free") is True

    def test_alias_sans_lait(self):
        assert self.match(VEGAN_RECIPE, "sans_lait") is True

    def test_alias_sans_noix(self):
        assert self.match(NUT_FREE_RECIPE, "sans_noix") is True

    def test_alias_sans_fruits_a_coque(self):
        assert self.match(NUT_FREE_RECIPE, "sans_fruits_a_coque") is True

    def test_alias_cru(self):
        recipe_raw = _make_recipe(10, {"raw": True})
        assert self.match(recipe_raw, "cru") is True

    # ── Aliases EN ───────────────────────────────────────────────────────────

    def test_alias_vegetarian_en(self):
        assert self.match(VEGETARIAN_RECIPE, "vegetarian") is True

    def test_alias_gluten_free_en(self):
        assert self.match(VEGAN_RECIPE, "gluten_free") is True

    # ── Casse et séparateurs ─────────────────────────────────────────────────

    def test_uppercase(self):
        assert self.match(VEGAN_RECIPE, "VEGAN") is True

    def test_hyphen_separator(self):
        assert self.match(VEGAN_RECIPE, "gluten-free") is True

    def test_mixed_case_alias(self):
        assert self.match(VEGAN_RECIPE, "Sans_Gluten") is True

    # ── Résolution via diet_flags ────────────────────────────────────────────

    def test_vegan_true(self):
        assert self.match(VEGAN_RECIPE, "vegan") is True

    def test_vegan_false(self):
        assert self.match(VEGETARIAN_RECIPE, "vegan") is False

    def test_gluten_free_true(self):
        assert self.match(GLUTEN_FREE_RECIPE, "gluten_free") is True

    def test_gluten_free_false(self):
        assert self.match(VEGETARIAN_RECIPE, "gluten_free") is False

    def test_nut_free_true(self):
        assert self.match(NUT_FREE_RECIPE, "nut_free") is True

    def test_nut_free_false(self):
        assert self.match(VEGETARIAN_RECIPE, "nut_free") is False

    # ── Résolution via health_scores ─────────────────────────────────────────

    def test_diabete_low_gi(self):
        assert self.match(DIABETE_RECIPE, "diabete") is True

    def test_diabete_medium_gi_rejected(self):
        assert self.match(HIGH_PROTEIN_RECIPE, "diabete") is False

    def test_hyperproteine_true(self):
        assert self.match(HIGH_PROTEIN_RECIPE, "hyperproteine") is True

    def test_hyperproteine_false(self):
        assert self.match(DIABETE_RECIPE, "hyperproteine") is False

    def test_health_scores_absent_returns_false(self):
        """Données partielles : diabete et hyperproteine retournent False silencieusement."""
        recipe = _make_recipe(99, {"vegan": True}, health={})
        assert self.match(recipe, "diabete") is False
        assert self.match(recipe, "hyperproteine") is False

    # ── Régime inconnu ────────────────────────────────────────────────────────

    def test_unknown_diet_passthrough(self):
        """Un régime inconnu laisse passer (avec warning) — ne bloque pas."""
        assert self.match(VEGAN_RECIPE, "cetogene") is True


# ── Tests apply_diet_filter ───────────────────────────────────────────────────

class TestApplyDietFilter:

    def setup_method(self):
        from backend.services.filter_service import apply_diet_filter
        self.filter = apply_diet_filter

    def test_empty_diet_returns_all(self):
        result = self.filter(ALL_RECIPES, "")
        assert len(result) == len(ALL_RECIPES)

    def test_empty_list(self):
        assert self.filter([], "vegan") == []

    def test_vegan_filter(self):
        result = self.filter(ALL_RECIPES, "vegan")
        ids = [r["id"] for r in result]
        assert 1 in ids       # VEGAN_RECIPE
        assert 2 not in ids   # VEGETARIAN_RECIPE (vegan=False)
        assert 3 not in ids   # NON_VEGETARIAN (baseline)

    def test_gluten_free_excludes_non_vegetarian(self):
        """NON_VEGETARIAN_RECIPE a gluten_free=True mais est bloqué par la baseline."""
        result = self.filter(ALL_RECIPES, "gluten_free")
        ids = [r["id"] for r in result]
        assert 3 not in ids

    def test_alias_fr_equals_canonical(self):
        result_fr = self.filter(ALL_RECIPES, "sans_gluten")
        result_en = self.filter(ALL_RECIPES, "gluten_free")
        assert [r["id"] for r in result_fr] == [r["id"] for r in result_en]

    def test_order_preserved(self):
        subset = [VEGAN_RECIPE, GLUTEN_FREE_RECIPE]
        result = self.filter(subset, "gluten_free")
        ids = [r["id"] for r in result]
        if 1 in ids and 4 in ids:
            assert ids.index(1) < ids.index(4)

    def test_diabete_filter(self):
        result = self.filter(ALL_RECIPES, "diabete")
        ids = [r["id"] for r in result]
        assert 5 in ids       # DIABETE_RECIPE
        assert 6 not in ids   # HIGH_PROTEIN (medium GI)

    def test_hyperproteine_filter(self):
        result = self.filter(ALL_RECIPES, "hyperproteine")
        ids = [r["id"] for r in result]
        assert 6 in ids
        assert 5 not in ids


# ── Tests normalize_diet ──────────────────────────────────────────────────────

class TestNormalizeDiet:

    def setup_method(self):
        from backend.core.validators import normalize_diet
        self.normalize = normalize_diet

    def test_canonical_unchanged(self):
        assert self.normalize("vegan") == "vegan"
        assert self.normalize("gluten_free") == "gluten_free"
        assert self.normalize("vegetarien") == "vegetarien"

    def test_alias_fr(self):
        assert self.normalize("sans_gluten") == "gluten_free"
        assert self.normalize("sans_lactose") == "lactose_free"
        assert self.normalize("sans_noix") == "nut_free"
        assert self.normalize("vegetarienne") == "vegetarien"
        assert self.normalize("sans_lait") == "lactose_free"

    def test_alias_en(self):
        assert self.normalize("vegetarian") == "vegetarien"
        assert self.normalize("dairy_free") == "lactose_free"

    def test_uppercase(self):
        assert self.normalize("VEGAN") == "vegan"
        assert self.normalize("Sans_Gluten") == "gluten_free"

    def test_hyphen(self):
        assert self.normalize("gluten-free") == "gluten_free"

    def test_none_returns_none(self):
        assert self.normalize(None) is None

    def test_empty_returns_none(self):
        assert self.normalize("") is None

    def test_unknown_returns_lowercased(self):
        assert self.normalize("cetogene") == "cetogene"


# ── Tests RecipeRepository.filter_by_diet — délégation (étape 3) ─────────────

class TestRecipeRepositoryFilterByDietDelegation:
    """
    Vérifie que filter_by_diet() délègue à filter_service.match_diet
    et non plus à l'ancienne logique locale (tombstone v6.19).
    """

    @pytest.fixture(autouse=True)
    def patch_data(self):
        with patch("backend.db.culinary_repositories._recipes_raw",
                   return_value=ALL_RECIPES), \
             patch("backend.db.culinary_repositories._recipes_index",
                   return_value={r["id"]: r for r in ALL_RECIPES}):
            yield

    def setup_method(self):
        from backend.db.culinary_repositories import RecipeRepository
        self.repo = RecipeRepository()

    def test_result_matches_filter_service(self):
        from backend.services.filter_service import apply_diet_filter
        assert (
            [r["id"] for r in self.repo.filter_by_diet(ALL_RECIPES, "vegan")]
            == [r["id"] for r in apply_diet_filter(ALL_RECIPES, "vegan")]
        )

    def test_alias_fr_handled(self):
        """L'ancienne logique ignorait les aliases FR — la délégation les gère."""
        r_alias = self.repo.filter_by_diet(ALL_RECIPES, "sans_gluten")
        r_canon = self.repo.filter_by_diet(ALL_RECIPES, "gluten_free")
        assert [r["id"] for r in r_alias] == [r["id"] for r in r_canon]

    def test_baseline_applied(self):
        """Baseline végétarienne absente de l'ancienne logique — présente via délégation."""
        result = self.repo.filter_by_diet(ALL_RECIPES, "gluten_free")
        assert NON_VEGETARIAN_RECIPE["id"] not in [r["id"] for r in result]

    def test_empty_diet_passthrough(self):
        assert len(self.repo.filter_by_diet(ALL_RECIPES, "")) == len(ALL_RECIPES)
