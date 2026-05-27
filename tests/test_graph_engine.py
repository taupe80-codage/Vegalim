"""
tests/test_graph_engine.py — Tests unitaires de graph_engine/core.py.

Couverture :
    _load_graph           chargement via _MtimeCache / graphe non vide
    compute_graph_score   bénéfices / risques / profil adaptatif /
                          ingrédients inconnus ignorés / liste vide
    analyze_recipe        structure retour / bénéfices / risques / substituts /
                          cycle_match avec phase / cycle_bonus / tags /
                          recette vide / pas de doublons risks/tags
    get_substitutes       ingrédient connu / inconnu
    get_cycle_ingredients délégation à load_cycle_data (testé via cycle_engine)
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Graphe de test minimal
# ═══════════════════════════════════════════════════════════════════════════════

GRAPH = {
    "lentils": {
        "benefits":    ["high_protein", "diabete_safe"],
        "risks":       [],
        "substitutes": ["chickpeas", "black_beans"],
        "cycle":       ["follicular_phase", "luteal_phase"],
        "cycle_reason": "Riche en protéines et fibres",
        "tags":        ["vegan", "high_fiber"],
    },
    "spinach": {
        "benefits":    [],
        "risks":       [],
        "substitutes": ["kale"],
        "cycle":       ["menstrual_phase"],
        "cycle_reason": "Riche en fer",
        "tags":        ["vegan"],
    },
    "processed_meat": {
        "benefits":    [],
        "risks":       ["diabetes"],
        "substitutes": ["tofu"],
        "cycle":       [],
        "tags":        [],
    },
    "walnut": {
        "benefits":    ["high_protein"],
        "risks":       [],
        "substitutes": [],
        "cycle":       ["luteal_phase"],
        "tags":        ["vegan", "omega3"],
    },
}

CYCLE_DATA = {
    "cycle_phases": {
        "follicular_phase": {
            "ingredient_ids": ["lentils", "quinoa"],
            "recommended_foods": [],
        }
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# Fixture
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def ge():
    """Charge graph_engine/core.py avec un graphe de test injecté."""
    for key in [k for k in sys.modules
                if "graph_engine" in k or "graph_engine_core" in k]:
        del sys.modules[key]

    for mod in ["backend", "backend.core", "backend.engine"]:
        sys.modules.setdefault(mod, types.ModuleType(mod))

    # _MtimeCache minimal
    class _MtimeCache:
        def __init__(self, name=""): self._val = None
        def get(self, path, loader):
            if self._val is None:
                self._val = loader()
            return self._val
        def cache_clear(self): self._val = None

    data_io = types.ModuleType("backend.core.data_io")
    data_io._MtimeCache      = _MtimeCache
    data_io.load_json        = lambda path, default=None, required=False: GRAPH
    data_io.load_cycle_data  = lambda: CYCLE_DATA
    sys.modules["backend.core.data_io"] = data_io

    config = types.ModuleType("backend.engine.config")
    config.DATA_ROOT = Path("/tmp/fake")
    sys.modules["backend.engine.config"] = config

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "graph_engine_core",
        Path(__file__).parent.parent / "backend" /
        "engine" / "graph_engine" / "core.py",
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["graph_engine_core"] = m
    spec.loader.exec_module(m)
    return m


def _recipe(ingredients=None):
    return {"id": 1, "ingredients": ingredients or []}


# ═══════════════════════════════════════════════════════════════════════════════
# _load_graph
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadGraph:

    def test_retourne_dict(self, ge):
        assert isinstance(ge._load_graph(), dict)

    def test_non_vide(self, ge):
        assert len(ge._load_graph()) > 0

    def test_contient_ingredients_de_test(self, ge):
        g = ge._load_graph()
        assert "lentils" in g
        assert "spinach"  in g

    def test_cache_clear_accessible(self, ge):
        """_load_graph.cache_clear doit exister (compat admin/tests)."""
        assert callable(ge._load_graph.cache_clear)


# ═══════════════════════════════════════════════════════════════════════════════
# compute_graph_score
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeGraphScore:

    def test_liste_vide_retourne_zero(self, ge):
        assert ge.compute_graph_score([]) == 0.0

    def test_ingredient_inconnu_ignore(self, ge):
        assert ge.compute_graph_score(["ingredient_inexistant"]) == 0.0

    def test_benefice_high_protein_profil_defaut(self, ge):
        score = ge.compute_graph_score(["lentils"])
        # lentils a high_protein (2.0) + diabete_safe (1.0) → 3.0
        assert score == pytest.approx(3.0)

    def test_benefice_amplifie_profil_hyperproteine(self, ge):
        score_default = ge.compute_graph_score(["lentils"])
        score_hyper   = ge.compute_graph_score(["lentils"],
                                                {"diet": "hyperproteine"})
        # hyperproteine → high_protein vaut 4.0 au lieu de 2.0
        assert score_hyper > score_default

    def test_risque_diabetes_profil_defaut(self, ge):
        score = ge.compute_graph_score(["processed_meat"])
        # diabetes pénalité default = -3.0
        assert score == pytest.approx(-3.0)

    def test_risque_amplifie_profil_diabete(self, ge):
        score_default = ge.compute_graph_score(["processed_meat"])
        score_diabete = ge.compute_graph_score(["processed_meat"],
                                               {"diet": "diabete"})
        # diabete → diabetes vaut -6.0 au lieu de -3.0
        assert score_diabete < score_default

    def test_accumulation_plusieurs_ingredients(self, ge):
        score_lentils = ge.compute_graph_score(["lentils"])
        score_walnut  = ge.compute_graph_score(["walnut"])
        score_cumul   = ge.compute_graph_score(["lentils", "walnut"])
        assert score_cumul == pytest.approx(score_lentils + score_walnut)

    def test_insensible_a_la_casse(self, ge):
        score_lower = ge.compute_graph_score(["lentils"])
        score_upper = ge.compute_graph_score(["LENTILS"])
        assert score_lower == score_upper


# ═══════════════════════════════════════════════════════════════════════════════
# analyze_recipe
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyzeRecipe:

    def test_structure_retour_complete(self, ge):
        result = ge.analyze_recipe(_recipe())
        required = {"score", "graph_score", "cycle_bonus",
                    "risks", "substitutes", "cycle_match", "tags"}
        assert required <= result.keys()

    def test_recette_vide_valeurs_neutres(self, ge):
        result = ge.analyze_recipe(_recipe([]))
        assert result["score"]       == 0.0
        assert result["risks"]       == []
        assert result["substitutes"] == []
        assert result["tags"]        == []

    def test_benefices_incrementent_score(self, ge):
        result = ge.analyze_recipe(_recipe(["lentils"]))
        assert result["graph_score"] > 0.0

    def test_risques_detectes(self, ge):
        result = ge.analyze_recipe(_recipe(["processed_meat"]))
        assert "diabetes" in result["risks"]
        assert result["graph_score"] < 0.0

    def test_pas_de_doublons_dans_risks(self, ge):
        """Le même risque sur deux ingrédients ne doit apparaître qu'une fois."""
        result = ge.analyze_recipe(_recipe(["processed_meat", "processed_meat"]))
        assert result["risks"].count("diabetes") == 1

    def test_substituts_retournes(self, ge):
        result = ge.analyze_recipe(_recipe(["lentils"]))
        subs = result["substitutes"]
        assert any(s["from"] == "lentils" for s in subs)
        assert any(s["to"] == "chickpeas" for s in subs)

    def test_tags_collectes(self, ge):
        result = ge.analyze_recipe(_recipe(["lentils", "spinach"]))
        assert "vegan" in result["tags"]

    def test_pas_de_doublons_dans_tags(self, ge):
        """lentils et spinach ont tous deux le tag vegan → un seul."""
        result = ge.analyze_recipe(_recipe(["lentils", "spinach"]))
        assert result["tags"].count("vegan") == 1

    def test_cycle_match_avec_phase_correspondante(self, ge):
        """follicular_phase dans profil → lentils (cycle=[follicular_phase]) matche."""
        result = ge.analyze_recipe(
            _recipe(["lentils"]),
            profile={"cycle_phase": "follicular_phase"},
        )
        assert "lentils"  in result["cycle_match"]
        assert result["cycle_bonus"] == pytest.approx(3.0)

    def test_cycle_bonus_cumulatif(self, ge):
        """Deux ingrédients matchant la phase → cycle_bonus = 6.0."""
        result = ge.analyze_recipe(
            _recipe(["lentils", "walnut"]),
            profile={"cycle_phase": "luteal_phase"},
        )
        # lentils et walnut ont tous deux luteal_phase
        assert result["cycle_bonus"] == pytest.approx(6.0)

    def test_cycle_match_sans_phase_collecte_toutes_phases(self, ge):
        """Sans cycle_phase dans profil, cycle_match collecte toutes les phases."""
        result = ge.analyze_recipe(_recipe(["spinach"]))
        assert "menstrual_phase" in result["cycle_match"]

    def test_score_total_inclut_cycle_bonus(self, ge):
        result = ge.analyze_recipe(
            _recipe(["lentils"]),
            profile={"cycle_phase": "follicular_phase"},
        )
        assert result["score"] == pytest.approx(
            result["graph_score"] + result["cycle_bonus"]
        )

    def test_profil_diabete_amplifie_penalite(self, ge):
        r_default = ge.analyze_recipe(_recipe(["processed_meat"]))
        r_diabete = ge.analyze_recipe(
            _recipe(["processed_meat"]),
            profile={"diet": "diabete"},
        )
        assert r_diabete["graph_score"] < r_default["graph_score"]

    def test_insensible_casse_ingredients(self, ge):
        r_lower = ge.analyze_recipe(_recipe(["lentils"]))
        r_upper = ge.analyze_recipe(_recipe(["LENTILS"]))
        assert r_lower["graph_score"] == r_upper["graph_score"]


# ═══════════════════════════════════════════════════════════════════════════════
# get_substitutes
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetSubstitutes:

    def test_ingredient_connu(self, ge):
        subs = ge.get_substitutes("lentils")
        assert isinstance(subs, list)
        assert "chickpeas" in subs

    def test_ingredient_inconnu_retourne_vide(self, ge):
        assert ge.get_substitutes("ingredient_inconnu") == []

    def test_insensible_casse(self, ge):
        assert ge.get_substitutes("LENTILS") == ge.get_substitutes("lentils")

    def test_ingredient_sans_substituts(self, ge):
        assert ge.get_substitutes("walnut") == []
