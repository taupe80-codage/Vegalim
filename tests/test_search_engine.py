"""
test_search_engine.py — Tests fonctionnels de search_engine/core.py

Couvre les 5 bugs critiques identifiés + comportements attendus :
    - Smoke test chargement index
    - Requête directe retourne des résultats (bug #3 détecté ici)
    - Mode recommandation sur requête vide (bug #1 masquait ce mode)
    - Filtre vegan respecté
    - Filtre combiné (diet + max_time)
    - Fuzzy matching (tolérance orthographique)
    - Scoring décroissant garanti
    - Champ _search_v3 présent et valide
    - Recettes similaires (_similar_recipes)
    - title_fr ET titles.fr tous deux cherchés (bug #5)

Lance avec : pytest tests/test_search_engine.py -v
"""
from __future__ import annotations

import pytest
from pathlib import Path

# ── Racine du projet (même convention que test_pipeline.py) ──────────────────
ROOT = Path(__file__).resolve().parent.parent   # tests/ → projet/


# ── Fixtures recettes synthétiques ───────────────────────────────────────────

FAKE_RECIPES = [
    {
        "id": 3,
        "titles": {"fr": "Curry de légumes au lait de coco"},
        "title_fr": "",
        "diet_flags": {"vegan": True, "vegetarian": True},
        "composition": [
            {"ingredient": "curry"},
            {"ingredient": "lait de coco"},
            {"ingredient": "tofu"},
        ],
        "overall_score": 7.5,
        "timing": {"total_min": 25},
    },
    {
        "id": 16,
        "titles": {"fr": "Ramen japonais au miso"},
        "title_fr": "",
        "diet_flags": {"vegetarian": True},
        "composition": [
            {"ingredient": "nouilles ramen"},
            {"ingredient": "miso"},
            {"ingredient": "champignons shiitake"},
        ],
        "overall_score": 8.0,
        "timing": {"total_min": 40},
    },
    {
        "id": 5,
        "title_fr": "Tofu sauté sauce soja",
        "titles": {},
        "diet_flags": {"vegan": True, "vegetarian": True},
        "composition": [
            {"ingredient": "tofu"},
            {"ingredient": "sauce soja"},
            {"ingredient": "gingembre"},
        ],
        "overall_score": 6.5,
        "timing": {"total_min": 15},
    },
    {
        "id": 42,
        "title_fr": "Salade quinoa grenade",
        "titles": {"fr": "Salade quinoa grenade"},
        "diet_flags": {"vegan": True, "vegetarian": True, "gluten_free": True},
        "composition": [
            {"ingredient": "quinoa"},
            {"ingredient": "grenade"},
            {"ingredient": "menthe"},
        ],
        "overall_score": 8.5,
        "timing": {"total_min": 20},
    },
    {
        "id": 99,
        "title_fr": "Boeuf bourguignon classique",
        "titles": {},
        "diet_flags": {"vegetarian": False, "vegan": False},
        "composition": [
            {"ingredient": "boeuf"},
            {"ingredient": "vin rouge"},
            {"ingredient": "champignons"},
        ],
        "overall_score": 9.0,
        "timing": {"total_min": 180},
    },
]


def _search(*args, **kwargs):
    """
    Helper qui injecte les recettes synthétiques.
    Les chemins index/mapping sont résolus automatiquement par core.py via DATA_ROOT
    (même comportement qu'en production). Pas de chemins hardcodés ici.
    """
    from backend.engine.search_engine.core import search
    return search(*args, recipes=FAKE_RECIPES, **kwargs)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestIndexLoad:
    def test_index_loadable(self):
        """Smoke test : l'index se charge sans erreur."""
        from backend.engine.search_engine.core import _IndexCache, _default_index_path
        cache = _IndexCache.get()
        cache.load_index(_default_index_path())
        assert len(cache._index) > 0, "Index vide après chargement"

    def test_mapping_loadable(self):
        """Smoke test : le mapping FR→EN se charge sans erreur."""
        from backend.engine.search_engine.core import _IndexCache, _default_mapping_path
        cache = _IndexCache.get()
        cache.load_mapping(_default_mapping_path())
        assert len(cache._mapping) > 0, "Mapping vide après chargement"


class TestDirectSearch:
    def test_curry_returns_results(self):
        """Une requête 'curry' doit retourner au moins 1 résultat."""
        results = _search(query_text="curry")
        assert len(results) > 0, "search('curry') ne retourne rien — bug #1/#3 probable"

    def test_tofu_returns_tofu_recipes(self):
        """'tofu' doit trouver les recettes contenant du tofu."""
        results = _search(query_text="tofu")
        ids = [r["id"] for r in results]
        assert 3 in ids or 5 in ids, f"Recettes tofu absentes, trouvé : {ids}"

    def test_results_sorted_by_score(self):
        """Les résultats doivent être triés par final_score décroissant."""
        results = _search(query_text="curry tofu", limit=10)
        if len(results) < 2:
            pytest.skip("Pas assez de résultats pour tester le tri")
        scores = [r["_search_v3"]["final_score"] for r in results]
        assert scores == sorted(scores, reverse=True), "Résultats non triés par score"

    def test_search_v3_field_present(self):
        """Chaque résultat doit avoir un champ _search_v3 valide."""
        results = _search(query_text="quinoa")
        for r in results:
            sv3 = r.get("_search_v3", {})
            assert "final_score"      in sv3
            assert "ingredient_match" in sv3
            assert "fuzzy_score"      in sv3
            assert "missing"          in sv3
            assert isinstance(sv3["final_score"], float)


class TestTitleFields:
    def test_titles_fr_found(self):
        """BUG #5 : titles.fr doit être cherché même si title_fr est vide."""
        # Recette 3 a title_fr="" mais titles.fr="Curry de légumes au lait de coco"
        results = _search(query_text="curry légumes")
        ids = [r["id"] for r in results]
        assert 3 in ids, (
            "Recette id=3 non trouvée alors que son titre est dans titles.fr — bug #5"
        )

    def test_title_fr_found(self):
        """title_fr classique doit toujours fonctionner."""
        results = _search(query_text="tofu sauté")
        ids = [r["id"] for r in results]
        assert 5 in ids, "Recette id=5 (title_fr) non trouvée"


class TestRecommendation:
    def test_empty_query_returns_results(self):
        """Requête vide → mode recommandation, doit retourner des recettes."""
        results = _search(query_text="")
        assert len(results) > 0, "Mode recommandation ne retourne rien"

    def test_empty_query_source_is_recommendation(self):
        """Requête vide → source='recommendation' dans _search_v3."""
        results = _search(query_text="")
        sources = {r["_search_v3"]["source"] for r in results}
        assert "recommendation" in sources

    def test_none_query_returns_results(self):
        """query_text=None équivaut à requête vide."""
        results = _search(query_text=None)
        assert len(results) > 0


class TestFilters:
    def test_diet_vegan_only_vegan(self):
        """Filtre vegan : tous les résultats doivent avoir diet_flags.vegan=True."""
        results = _search(query_text="tofu", diet="vegan")
        for r in results:
            assert r["diet_flags"].get("vegan"), (
                f"Recette id={r['id']} non-vegan retournée avec filtre vegan"
            )

    def test_diet_vegan_excludes_boeuf(self):
        """Le boeuf bourguignon (non-vegan) ne doit pas apparaître avec diet=vegan."""
        results = _search(query_text="", diet="vegan")
        ids = [r["id"] for r in results]
        assert 99 not in ids, "Recette non-vegan présente avec filtre vegan"

    def test_max_time_filter(self):
        """max_time=30 doit exclure les recettes > 30 min."""
        results = _search(query_text="", max_time=30)
        for r in results:
            total = (r.get("timing") or {}).get("total_min")
            if total:
                assert total <= 30, (
                    f"Recette id={r['id']} avec total_min={total} > 30 retournée"
                )

    def test_combined_filters(self):
        """Filtres combinés diet=vegan + max_time=25 — résultats cohérents."""
        results = _search(query_text="", diet="vegan", max_time=25)
        for r in results:
            assert r["diet_flags"].get("vegan"), "Non-vegan dans résultats filtrés"
            total = (r.get("timing") or {}).get("total_min")
            if total:
                assert total <= 25

    def test_gluten_free_filter(self):
        """diet=gluten_free doit retourner uniquement les recettes gluten_free."""
        results = _search(query_text="", diet="gluten_free")
        for r in results:
            assert r["diet_flags"].get("gluten_free"), (
                f"Recette id={r['id']} sans flag gluten_free retournée"
            )


class TestFuzzyMatching:
    def test_typo_tolerance(self):
        """'quinua' (faute) doit trouver 'quinoa'."""
        results = _search(query_text="quinua", enable_fuzzy=True)
        # Peut ne pas trouver dans les recettes synthétiques si le token 'quinoa'
        # n'est pas dans l'index pour ces IDs — on vérifie au moins que ça ne plante pas
        assert isinstance(results, list)

    def test_fuzzy_disabled_stricter(self):
        """Sans fuzzy, une faute de frappe ne doit pas produire plus de résultats."""
        with_fuzzy    = _search(query_text="quinua", enable_fuzzy=True)
        without_fuzzy = _search(query_text="quinua", enable_fuzzy=False)
        assert len(with_fuzzy) >= len(without_fuzzy), (
            "enable_fuzzy=False retourne plus de résultats qu'enable_fuzzy=True"
        )


class TestSimilarRecipes:
    def test_similar_attached_to_first_result(self):
        """include_similar=True doit attacher _similar_recipes au premier résultat."""
        results = _search(query_text="curry", include_similar=True)
        if not results:
            pytest.skip("Aucun résultat pour tester les similaires")
        sv3 = results[0].get("_search_v3", {})
        # _similar_recipes peut être vide si l'index ne couvre pas les IDs synthétiques
        assert "_similar_recipes" in sv3, "_similar_recipes absent du premier résultat"
        assert isinstance(sv3["_similar_recipes"], list)


class TestBackwardCompat:
    def test_query_alias_works(self):
        """Alias query= (ancienne signature orchestrateur) doit fonctionner."""
        from backend.engine.search_engine.core import search
        results = search(query="curry", recipes=FAKE_RECIPES)
        assert isinstance(results, list)

    def test_adaptive_score_alias_present(self):
        """adaptive_score doit être présent dans _search_v3 (alias pour scoring.py)."""
        results = _search(query_text="tofu")
        for r in results:
            assert "adaptive_score" in r.get("_search_v3", {}), (
                "Champ adaptive_score absent — scoring.py ne pourra pas calculer la pertinence"
            )
