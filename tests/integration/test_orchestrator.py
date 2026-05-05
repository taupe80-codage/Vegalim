"""
tests/integration/test_orchestrator.py

Tests d'intégration — pipeline recommend() (point #10 du backlog ALIM).

Stratégie de mocking
--------------------
Toutes les dépendances backend.* sont injectées via sys.modules avant
chaque test. Les imports inline de recommend() et _search() récupèrent
les mocks transparents ; aucune base de données ni service réel n'est requis.

Contrats vérifiés
-----------------
    Structure
    ✓ timing_ms            int ≥ 0
    ✓ profile_used         str non vide
    ✓ total == len(recipes)
    ✓ to_dict() contient toutes les clés attendues
    ✓ meta contient les clés CDC_03c

    Recettes
    ✓ Chaque recette contient final_score (float)
    ✓ limit est respecté

    Étape 3 — Exclusions historique
    ✓ Les IDs dislikés sont absents du résultat

    Étape 4 — Diet override
    ✓ normalize_diet() appelé quand context.diet est renseigné
    ✓ diet propagé dans result.diet

    Étape 6 — Learning
    ✓ apply_learning toujours appelé (garde interne dans personalization.py)

    Étape 7 — Cycle féminin
    ✓ adjust_ranking appelé si et seulement si has_cycle=True
    ✓ Exception dans cycle_engine → pas de crash (dégradation gracieuse)

    Dégradation gracieuse
    ✓ search_engine lève une exception → recipes=[], timing_ms toujours présent
    ✓ batch_score retourne [] → pipeline se termine normalement
"""
from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Dataclass miroir de personalization.UserContext
# Évite un import backend.* dans le corps du module de test.
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class _Ctx:
    email:             str | None = None
    profile:           dict       = field(default_factory=dict)
    diet:              str | None = None
    profile_used:      str        = "default"
    effective_profile: dict       = field(default_factory=dict)
    has_learning:      bool       = False
    has_cycle:         bool       = False


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _recipe(rid: int = 1, score: float = 7.5) -> dict:
    return {
        "id":              rid,
        "titles":          {"fr": f"Recette {rid}"},
        "final_score":     score,
        "quality_score":   round(score * 0.8, 2),
        "relevance_score": round(score * 0.2, 2),
    }


def _recipes(n: int) -> list[dict]:
    return [_recipe(i, round(8.5 - i * 0.3, 2)) for i in range(1, n + 1)]


def _mod(name: str, **attrs) -> types.ModuleType:
    """Crée un ModuleType minimal avec les attributs donnés."""
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# Fixture centrale
# ═══════════════════════════════════════════════════════════════════════════════

_ORCHESTRATOR_KEY = "backend.engine.reco_engine.orchestrator"


@pytest.fixture()
def pipe(request):
    """
    Monte le pipeline recommend() avec toutes ses dépendances mockées.

    Paramétrage optionnel via @pytest.mark.parametrize(indirect=True) :
        context   _Ctx à retourner par resolve_user_context  (défaut : _Ctx())
        pool      recettes candidates avant scoring           (défaut : 5 recettes)
        scored    recettes retournées par batch_score         (défaut : pool)
        excluded  IDs à exclure par get_excluded_ids          (défaut : [])

    Attributs exposés :
        pipe.recommend   fonction à tester
        pipe.m.*         accès direct aux MagicMock nommés
        pipe.ctx         UserContext utilisé
    """
    param    = getattr(request, "param", {}) or {}
    ctx      = param.get("context",  _Ctx())
    pool     = param.get("pool",     _recipes(5))
    scored   = param.get("scored",   list(pool))
    excluded = param.get("excluded", [])

    # ── MagicMock nommés ──────────────────────────────────────────────────────
    m = types.SimpleNamespace(
        resolve   = MagicMock(return_value=ctx),
        excluded  = MagicMock(return_value=excluded),
        learning  = MagicMock(side_effect=lambda recipes, context: recipes),
        search    = MagicMock(return_value=list(pool)),
        batch     = MagicMock(return_value=list(scored)),
        filter_d  = MagicMock(side_effect=lambda recipes, diet: recipes),
        normalize = MagicMock(side_effect=lambda d: d),
        adjust    = MagicMock(side_effect=lambda recipes, phase=None: recipes),
    )

    # ── Modules factices injectés dans sys.modules ────────────────────────────
    backend_mods: dict[str, types.ModuleType] = {
        # Hiérarchie de packages (nécessaire pour résoudre les imports dotés)
        "backend":                              _mod("backend"),
        "backend.core":                         _mod("backend.core"),
        "backend.engine":                       _mod("backend.engine"),
        "backend.engine.reco_engine":           _mod("backend.engine.reco_engine"),
        "backend.engine.search_engine":         _mod("backend.engine.search_engine"),
        "backend.services":                     _mod("backend.services"),
        # Modules feuilles
        "backend.engine.reco_engine.personalization": _mod(
            "backend.engine.reco_engine.personalization",
            resolve_user_context = m.resolve,
            get_excluded_ids     = m.excluded,
            apply_learning       = m.learning,
        ),
        "backend.engine.reco_engine.scoring": _mod(
            "backend.engine.reco_engine.scoring",
            batch_score = m.batch,
        ),
        "backend.engine.search_engine.core": _mod(
            "backend.engine.search_engine.core",
            search = m.search,
        ),
        "backend.services.filter_service": _mod(
            "backend.services.filter_service",
            apply_diet_filter = m.filter_d,
        ),
        "backend.core.validators": _mod(
            "backend.core.validators",
            normalize_diet = m.normalize,
        ),
        "backend.engine.cycle_engine": _mod(
            "backend.engine.cycle_engine",
            adjust_ranking = m.adjust,
        ),
        "backend.engine.config": _mod(
            "backend.engine.config",
            W_QUALITY   = 0.7,
            W_RELEVANCE = 0.3,
        ),
    }

    # Purge le module orchestrateur pour forcer un re-import avec les mocks en place
    _saved = sys.modules.pop(_ORCHESTRATOR_KEY, None)

    with patch.dict(sys.modules, backend_mods):
        orch = importlib.import_module(_ORCHESTRATOR_KEY)
        yield types.SimpleNamespace(recommend=orch.recommend, m=m, ctx=ctx)

    # Restauration sys.modules
    sys.modules.pop(_ORCHESTRATOR_KEY, None)
    if _saved is not None:
        sys.modules[_ORCHESTRATOR_KEY] = _saved


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Structure du résultat
# ═══════════════════════════════════════════════════════════════════════════════

class TestResultStructure:
    """RecommendationResult doit exposer tous les champs du contrat CDC_03c."""

    def test_timing_ms_is_non_negative_int(self, pipe):
        r = pipe.recommend()
        assert isinstance(r.timing_ms, int), "timing_ms doit être un int"
        assert r.timing_ms >= 0,             "timing_ms doit être ≥ 0"

    def test_profile_used_is_non_empty_string(self, pipe):
        r = pipe.recommend()
        assert isinstance(r.profile_used, str), "profile_used doit être une str"
        assert r.profile_used,                  "profile_used ne doit pas être vide"

    def test_total_equals_len_recipes(self, pipe):
        r = pipe.recommend(limit=5)
        assert r.total == len(r.recipes), (
            f"total ({r.total}) ≠ len(recipes) ({len(r.recipes)})"
        )

    def test_to_dict_has_all_required_keys(self, pipe):
        required = {"recipes", "total", "query", "diet", "profile_used", "timing_ms", "meta"}
        d = pipe.recommend().to_dict()
        missing = required - d.keys()
        assert not missing, f"Clés manquantes dans to_dict() : {missing}"

    def test_meta_has_cdc_required_keys(self, pipe):
        required = {
            "candidates_total",
            "candidates_scored",
            "learning_active",
            "cycle_active",
            "profile_used",
            "w_quality",
            "w_relevance",
            "formula",
        }
        meta = pipe.recommend().meta
        missing = required - meta.keys()
        assert not missing, f"Clés manquantes dans meta : {missing}"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Contenu des recettes
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecipeContent:
    """Chaque recette doit contenir final_score après le passage dans le pipeline."""

    def test_each_recipe_has_final_score(self, pipe):
        r = pipe.recommend()
        assert r.recipes, "La liste de recettes ne doit pas être vide"
        for rec in r.recipes:
            assert "final_score" in rec, (
                f"final_score absent de la recette id={rec.get('id')}"
            )

    def test_final_score_is_numeric(self, pipe):
        r = pipe.recommend()
        for rec in r.recipes:
            assert isinstance(rec["final_score"], (int, float)), (
                f"final_score doit être numérique, got {type(rec['final_score'])}"
            )

    def test_limit_is_respected(self, pipe):
        r = pipe.recommend(limit=3)
        assert len(r.recipes) <= 3, (
            f"limit=3 non respecté : {len(r.recipes)} recettes retournées"
        )

    def test_query_propagated_in_result(self, pipe):
        r = pipe.recommend(query="curry vegan")
        assert r.query == "curry vegan"


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Étape 3 : Exclusions historique
# ═══════════════════════════════════════════════════════════════════════════════

class TestExclusions:
    """Les recettes dislikées doivent être exclues avant le scoring."""

    @pytest.mark.parametrize("pipe", [
        {
            "pool":     _recipes(5),
            "excluded": [2, 4],
            "scored":   [_recipe(1, 8.2), _recipe(3, 7.6), _recipe(5, 6.9)],
        }
    ], indirect=True)
    def test_excluded_ids_absent_from_result(self, pipe):
        r = pipe.recommend()
        returned_ids = {rec["id"] for rec in r.recipes}
        assert 2 not in returned_ids, "Recette id=2 (dislikée) présente dans les résultats"
        assert 4 not in returned_ids, "Recette id=4 (dislikée) présente dans les résultats"

    @pytest.mark.parametrize("pipe", [
        {"pool": _recipes(5), "excluded": [2, 4]}
    ], indirect=True)
    def test_get_excluded_ids_called_once(self, pipe):
        pipe.recommend()
        pipe.m.excluded.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Étape 4 : Diet override et normalisation
# ═══════════════════════════════════════════════════════════════════════════════

class TestDietOverride:
    """diet_override doit être normalisé et propagé dans le résultat."""

    @pytest.mark.parametrize("pipe", [
        {"context": _Ctx(diet="vegan", profile_used="vegan_strict")}
    ], indirect=True)
    def test_diet_propagated_in_result(self, pipe):
        r = pipe.recommend(diet_override="vegan")
        assert r.diet == "vegan", f"diet attendu 'vegan', obtenu '{r.diet}'"

    @pytest.mark.parametrize("pipe", [
        {"context": _Ctx(diet="vegetarien")}
    ], indirect=True)
    def test_normalize_diet_called_when_diet_present(self, pipe):
        pipe.recommend()
        pipe.m.normalize.assert_called_once_with("vegetarien")

    def test_normalize_diet_not_called_when_no_diet(self, pipe):
        """Sans diet (contexte anonyme par défaut), normalize_diet ne doit pas être appelé."""
        pipe.recommend()
        pipe.m.normalize.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Étape 6 : Learning
# ═══════════════════════════════════════════════════════════════════════════════

class TestLearning:
    """
    apply_learning est TOUJOURS appelé dans le pipeline.
    La garde has_learning est interne à personalization.apply_learning,
    pas dans l'orchestrateur.
    """

    def test_apply_learning_always_called(self, pipe):
        pipe.recommend()
        pipe.m.learning.assert_called_once()

    @pytest.mark.parametrize("pipe", [
        {"context": _Ctx(has_learning=True, email="user@test.com")}
    ], indirect=True)
    def test_apply_learning_called_with_active_learning(self, pipe):
        pipe.recommend()
        call_args = pipe.m.learning.call_args
        # Vérifie que le context transmis a bien has_learning=True
        _, context_arg = call_args.args if call_args.args else (None, call_args.kwargs.get("context"))
        assert context_arg.has_learning is True


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Étape 7 : Cycle féminin
# ═══════════════════════════════════════════════════════════════════════════════

class TestCycleEngine:
    """adjust_ranking n'est appelé que si context.has_cycle est True."""

    @pytest.mark.parametrize("pipe", [
        {"context": _Ctx(has_cycle=True, profile={"cycle_phase": "follicular"})}
    ], indirect=True)
    def test_adjust_ranking_called_when_has_cycle(self, pipe):
        pipe.recommend()
        pipe.m.adjust.assert_called_once()

    @pytest.mark.parametrize("pipe", [
        {"context": _Ctx(has_cycle=True, profile={"cycle_phase": "luteal"})}
    ], indirect=True)
    def test_adjust_ranking_receives_cycle_phase(self, pipe):
        pipe.recommend()
        call_kwargs = pipe.m.adjust.call_args.kwargs
        assert call_kwargs.get("phase") == "luteal", (
            f"phase incorrecte transmise à adjust_ranking : {call_kwargs}"
        )

    def test_adjust_ranking_not_called_without_cycle(self, pipe):
        """Sans cycle (contexte par défaut), adjust_ranking ne doit pas être appelé."""
        pipe.recommend()
        pipe.m.adjust.assert_not_called()

    @pytest.mark.parametrize("pipe", [
        {"context": _Ctx(has_cycle=True, profile={"cycle_phase": "luteal"})}
    ], indirect=True)
    def test_cycle_engine_exception_does_not_crash(self, pipe):
        """Une exception dans adjust_ranking ne doit pas propager jusqu'à l'appelant."""
        pipe.m.adjust.side_effect = RuntimeError("cycle_engine KO")
        r = pipe.recommend()
        assert r is not None,          "recommend() doit retourner un résultat même si cycle_engine plante"
        assert isinstance(r.timing_ms, int)
        assert r.timing_ms >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Dégradation gracieuse
# ═══════════════════════════════════════════════════════════════════════════════

class TestGracefulDegradation:
    """Le pipeline doit se dégrader sans exception sur les pannes partielles."""

    def test_search_engine_exception_returns_empty_recipes(self, pipe):
        """Si search lève une exception, recipes doit être [] sans crash."""
        pipe.m.search.side_effect = ConnectionError("search_engine KO")
        r = pipe.recommend(query="test")
        assert r.recipes == [], "Panne search → recipes doit être []"
        assert r.total   == 0,  "Panne search → total doit être 0"

    def test_search_engine_exception_preserves_timing_ms(self, pipe):
        """timing_ms doit être présent même quand search plante."""
        pipe.m.search.side_effect = Exception("crash inattendu")
        r = pipe.recommend()
        assert hasattr(r, "timing_ms")
        assert isinstance(r.timing_ms, int)
        assert r.timing_ms >= 0

    def test_batch_score_empty_result_does_not_crash(self, pipe):
        """Si batch_score retourne [], le pipeline se termine normalement."""
        pipe.m.batch.return_value = []
        r = pipe.recommend()
        assert r.recipes == []
        assert r.total   == 0

    def test_result_always_serializable(self, pipe):
        """to_dict() doit toujours fonctionner, même sur un résultat vide."""
        pipe.m.batch.return_value = []
        r = pipe.recommend()
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["total"] == 0
