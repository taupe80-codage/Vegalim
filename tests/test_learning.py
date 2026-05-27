"""
tests/test_learning.py — Tests unitaires de reco_engine/learning.py.

Couverture :
    _load_history_from_json   chargement / fichier absent / JSON corrompu
    load_history              fallback DB → JSON
    save_interaction          écriture JSON (DB indisponible)
    _get_liked_recipes        filtrage par IDs
    extract_preferences       inactif (<MIN_LIKES) / actif / cuisine / technique /
                              difficulté / time_window
    compute_learning_bonus    malus dislike / bonus par dimension / cap MAX_BONUS
    apply_learning_bonus      bornes 0-10
    rank_with_learning        sans email / tri / champs injectés
    get_user_stats            structure de retour
"""
from __future__ import annotations

import json
import sys
import types
import tempfile
from pathlib import Path
from collections import Counter

import pytest
from unittest.mock import MagicMock, patch


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures et helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _make_recipe(rid, cuisine="", techniques=None, difficulty=2, total_min=30,
                 final_score=7.0):
    return {
        "id":           rid,
        "title_fr":     f"Recette {rid}",
        "final_score":  final_score,
        "iconic_status": {"cuisine_origin": cuisine} if cuisine else {},
        "cuisine_origin": cuisine,
        "technique":    techniques or [],
        "difficulty":   difficulty,
        "timing":       {"total_min": total_min},
        "diet_flags":   {"vegan": True},
    }


def _prefs(**kw):
    """Construit un dict prefs minimal avec des valeurs par défaut."""
    base = {
        "active":               True,
        "liked_count":          10,
        "cuisines_favorite":    set(),
        "techniques_preferred": set(),
        "difficulty_comfort":   None,
        "time_window":          None,
        "disliked_ids":         set(),
    }
    base.update(kw)
    return base


@pytest.fixture()
def tmp_history_dir(tmp_path):
    """Crée un répertoire d'historique temporaire."""
    d = tmp_path / "users" / "history"
    d.mkdir(parents=True)
    return d


@pytest.fixture()
def learning(tmp_history_dir):
    """
    Charge learning.py avec toutes les dépendances mockées.
    Retourne le module et expose le répertoire d'historique.
    """
    # Purge le module s'il était déjà importé
    for key in [k for k in sys.modules if "learning" in k]:
        del sys.modules[key]

    # Mocks modules backend
    for mod in ["backend", "backend.engine", "backend.core",
                "backend.db", "backend.db.session", "backend.db.repositories"]:
        sys.modules.setdefault(mod, types.ModuleType(mod))

    config = types.ModuleType("backend.engine.config")
    config.DATA_ROOT            = tmp_history_dir.parent.parent  # …/tmp/backend/data
    config.MIN_LIKES_TO_ACTIVATE = 5
    config.MAX_LEARNING_BONUS    = 2.0
    sys.modules["backend.engine.config"] = config

    # data_io : load_recipes retourne une liste vide par défaut
    data_io = types.ModuleType("backend.core.data_io")
    data_io.load_recipes = lambda: []
    sys.modules["backend.core.data_io"] = data_io

    # DB indisponible par défaut
    session_mod = sys.modules["backend.db.session"]
    session_mod.db_session = MagicMock(side_effect=Exception("DB KO"))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "learning",
        Path(__file__).parent.parent / "backend" / "engine" / "reco_engine" / "learning.py",
    )
    m = importlib.util.module_from_spec(spec)
    # Patch _HISTORY_DIR avant exec du module
    spec.loader.exec_module(m)
    m._HISTORY_DIR = tmp_history_dir   # override après chargement

    yield types.SimpleNamespace(mod=m, history_dir=tmp_history_dir,
                                 data_io=data_io)

    # Nettoyage
    for key in [k for k in sys.modules if "learning" in k]:
        del sys.modules[key]


# ═══════════════════════════════════════════════════════════════════════════════
# _load_history_from_json
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadHistoryFromJson:

    def test_fichier_absent_retourne_vide(self, learning):
        result = learning.mod._load_history_from_json("inconnu@test.com")
        assert result == {}

    def test_charge_fichier_existant(self, learning):
        data = {"liked": [1, 2, 3], "disliked": [4], "viewed": [1, 2, 3, 4]}
        path = learning.history_dir / "user_at_test_com.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = learning.mod._load_history_from_json("user@test.com")
        assert result["liked"]    == {1, 2, 3}
        assert result["disliked"] == {4}
        assert result["viewed"]   == {1, 2, 3, 4}

    def test_json_corrompu_retourne_vide(self, learning):
        path = learning.history_dir / "corrompu_at_test_com.json"
        path.write_text("{ ceci n'est pas du json", encoding="utf-8")
        result = learning.mod._load_history_from_json("corrompu@test.com")
        assert result == {}

    def test_encodage_email(self, learning):
        """@ → _at_ et . → _ dans le nom de fichier."""
        data = {"liked": [99], "disliked": [], "viewed": []}
        path = learning.history_dir / "thomas_at_alim_fr.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = learning.mod._load_history_from_json("thomas@alim.fr")
        assert 99 in result["liked"]


# ═══════════════════════════════════════════════════════════════════════════════
# load_history
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoadHistory:

    def test_fallback_json_quand_db_ko(self, learning):
        data = {"liked": [10, 11], "disliked": [], "viewed": [10]}
        path = learning.history_dir / "alice_at_test_com.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = learning.mod.load_history("alice@test.com")
        assert {10, 11} == result["liked"]

    def test_retourne_sets_vides_si_aucun_historique(self, learning):
        result = learning.mod.load_history("nouveau@test.com")
        assert result["liked"]    == set()
        assert result["disliked"] == set()
        assert result["viewed"]   == set()
        assert result["raw"]      == []

    def test_structure_retour_complete(self, learning):
        result = learning.mod.load_history("x@x.com")
        assert all(k in result for k in ("liked", "disliked", "viewed", "raw"))


# ═══════════════════════════════════════════════════════════════════════════════
# save_interaction
# ═══════════════════════════════════════════════════════════════════════════════

class TestSaveInteraction:

    def test_sauvegarde_like_en_json(self, learning):
        ok = learning.mod.save_interaction("bob@test.com", 42, "like")
        assert ok is True
        path = learning.history_dir / "bob_at_test_com.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert 42 in data["liked"]

    def test_sauvegarde_dislike_en_json(self, learning):
        learning.mod.save_interaction("bob@test.com", 99, "dislike")
        path = learning.history_dir / "bob_at_test_com.json"
        data = json.loads(path.read_text())
        assert 99 in data["disliked"]

    def test_pas_de_doublon_dans_liked(self, learning):
        learning.mod.save_interaction("bob@test.com", 42, "like")
        learning.mod.save_interaction("bob@test.com", 42, "like")
        path = learning.history_dir / "bob_at_test_com.json"
        data = json.loads(path.read_text())
        assert data["liked"].count(42) == 1

    def test_viewed_capped_a_500(self, learning):
        for i in range(510):
            learning.mod.save_interaction("cap@test.com", i, "view")
        path = learning.history_dir / "cap_at_test_com.json"
        data = json.loads(path.read_text())
        assert len(data["viewed"]) <= 500


# ═══════════════════════════════════════════════════════════════════════════════
# _get_liked_recipes
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetLikedRecipes:

    def test_retourne_recettes_correspondantes(self, learning):
        recipes = [_make_recipe(1), _make_recipe(2), _make_recipe(3)]
        result  = learning.mod._get_liked_recipes({1, 3}, recipes)
        ids = {r["id"] for r in result}
        assert ids == {1, 3}

    def test_ids_absents_ignores(self, learning):
        recipes = [_make_recipe(1)]
        result  = learning.mod._get_liked_recipes({1, 999}, recipes)
        assert len(result) == 1

    def test_ensemble_vide(self, learning):
        result = learning.mod._get_liked_recipes(set(), [_make_recipe(1)])
        assert result == []


# ═══════════════════════════════════════════════════════════════════════════════
# extract_preferences
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractPreferences:

    def _setup_history(self, learning, liked_ids, disliked_ids=None):
        """Écrit un fichier historique et configure load_recipes."""
        data = {
            "liked":    list(liked_ids),
            "disliked": list(disliked_ids or []),
            "viewed":   list(liked_ids),
        }
        path = learning.history_dir / "user_at_test_com.json"
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_inactif_si_pas_assez_de_likes(self, learning):
        self._setup_history(learning, [1, 2])  # < 5
        prefs = learning.mod.extract_preferences("user@test.com")
        assert prefs["active"] is False
        assert prefs["liked_count"] == 2

    def test_actif_avec_suffisamment_de_likes(self, learning):
        ids = [1, 2, 3, 4, 5]
        self._setup_history(learning, ids)
        recipes = [_make_recipe(i, cuisine="japonais") for i in ids]
        learning.data_io.load_recipes = lambda: recipes

        prefs = learning.mod.extract_preferences("user@test.com")
        assert prefs["active"] is True

    def test_cuisine_favorite_extraite(self, learning):
        ids = list(range(1, 8))
        self._setup_history(learning, ids)
        recipes = (
            [_make_recipe(i, cuisine="japonais") for i in ids[:5]] +
            [_make_recipe(i, cuisine="mexicain")  for i in ids[5:]]
        )
        learning.data_io.load_recipes = lambda: recipes

        prefs = learning.mod.extract_preferences("user@test.com")
        assert "japonais" in prefs["cuisines_favorite"]

    def test_techniques_preferees_extraites(self, learning):
        ids = list(range(1, 7))
        self._setup_history(learning, ids)
        recipes = [_make_recipe(i, techniques=["sauter", "blanchir"]) for i in ids]
        learning.data_io.load_recipes = lambda: recipes

        prefs = learning.mod.extract_preferences("user@test.com")
        assert len(prefs["techniques_preferred"]) > 0

    def test_difficulty_comfort_mode(self, learning):
        ids = list(range(1, 8))
        self._setup_history(learning, ids)
        # 5 recettes difficulté 2, 2 recettes difficulté 3
        recipes = (
            [_make_recipe(i, difficulty=2) for i in ids[:5]] +
            [_make_recipe(i, difficulty=3) for i in ids[5:]]
        )
        learning.data_io.load_recipes = lambda: recipes

        prefs = learning.mod.extract_preferences("user@test.com")
        assert prefs["difficulty_comfort"] == 2

    def test_time_window_percentile(self, learning):
        ids = list(range(1, 11))
        self._setup_history(learning, ids)
        # Durées : 10, 20, 30, ..., 100
        recipes = [_make_recipe(i, total_min=i * 10) for i in ids]
        learning.data_io.load_recipes = lambda: recipes

        prefs = learning.mod.extract_preferences("user@test.com")
        assert prefs["time_window"] is not None
        lo, hi = prefs["time_window"]
        assert lo < hi

    def test_disliked_ids_transmis(self, learning):
        self._setup_history(learning, [1, 2, 3, 4, 5], disliked_ids=[99, 100])
        learning.data_io.load_recipes = lambda: [_make_recipe(i) for i in range(1, 6)]

        prefs = learning.mod.extract_preferences("user@test.com")
        assert 99 in prefs["disliked_ids"]
        assert 100 in prefs["disliked_ids"]


# ═══════════════════════════════════════════════════════════════════════════════
# compute_learning_bonus
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeLearningBonus:

    def test_zero_si_prefs_inactives(self, learning):
        bonus = learning.mod.compute_learning_bonus(
            _make_recipe(1), _prefs(active=False))
        assert bonus == 0.0

    def test_malus_dislike_immediat(self, learning):
        bonus = learning.mod.compute_learning_bonus(
            _make_recipe(42), _prefs(disliked_ids={42}))
        assert bonus == learning.mod.MALUS_DISLIKED

    def test_bonus_cuisine_favorite(self, learning):
        recipe = _make_recipe(1, cuisine="japonais")
        bonus  = learning.mod.compute_learning_bonus(
            recipe, _prefs(cuisines_favorite={"japonais"}))
        assert bonus == pytest.approx(learning.mod.BONUS_CUISINE)

    def test_bonus_technique_preferee(self, learning):
        recipe = _make_recipe(1, techniques=["sauter"])
        bonus  = learning.mod.compute_learning_bonus(
            recipe, _prefs(techniques_preferred={"sauter"}))
        assert bonus == pytest.approx(learning.mod.BONUS_TECHNIQUE)

    def test_bonus_difficulty_confort(self, learning):
        recipe = _make_recipe(1, difficulty=2)
        bonus  = learning.mod.compute_learning_bonus(
            recipe, _prefs(difficulty_comfort=2))
        assert bonus == pytest.approx(learning.mod.BONUS_DIFFICULTY)

    def test_bonus_time_window(self, learning):
        recipe = _make_recipe(1, total_min=30)
        bonus  = learning.mod.compute_learning_bonus(
            recipe, _prefs(time_window=(20, 45)))
        assert bonus == pytest.approx(learning.mod.BONUS_TIME)

    def test_bonus_cumule_multiple_dimensions(self, learning):
        recipe = _make_recipe(1, cuisine="japonais", techniques=["sauter"],
                              difficulty=2, total_min=30)
        prefs  = _prefs(
            cuisines_favorite={"japonais"},
            techniques_preferred={"sauter"},
            difficulty_comfort=2,
            time_window=(20, 45),
        )
        bonus = learning.mod.compute_learning_bonus(recipe, prefs)
        expected = (learning.mod.BONUS_CUISINE + learning.mod.BONUS_TECHNIQUE +
                    learning.mod.BONUS_DIFFICULTY + learning.mod.BONUS_TIME)
        assert bonus == pytest.approx(expected)

    def test_bonus_cap_max(self, learning):
        """Le bonus ne peut pas dépasser MAX_BONUS même avec toutes les dimensions."""
        recipe = _make_recipe(1, cuisine="japonais", techniques=["sauter",
                              "blanchir"], difficulty=1, total_min=20)
        prefs  = _prefs(
            cuisines_favorite={"japonais"},
            techniques_preferred={"sauter", "blanchir"},
            difficulty_comfort=1,
            time_window=(10, 30),
        )
        bonus = learning.mod.compute_learning_bonus(recipe, prefs)
        assert bonus <= learning.mod.MAX_BONUS

    def test_hors_time_window_pas_de_bonus(self, learning):
        recipe = _make_recipe(1, total_min=120)
        bonus  = learning.mod.compute_learning_bonus(
            recipe, _prefs(time_window=(20, 45)))
        assert learning.mod.BONUS_TIME not in [bonus]
        # Vérifie surtout que le bonus temps n'est pas inclus
        bonus_sans_temps = learning.mod.compute_learning_bonus(
            _make_recipe(1, total_min=30), _prefs(time_window=(20, 45)))
        assert bonus < bonus_sans_temps or bonus == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# apply_learning_bonus
# ═══════════════════════════════════════════════════════════════════════════════

class TestApplyLearningBonus:

    def test_borne_inferieure_zero(self, learning):
        recipe = _make_recipe(42)
        prefs  = _prefs(disliked_ids={42})
        final, _ = learning.mod.apply_learning_bonus(recipe, 0.5, prefs)
        assert final >= 0.0

    def test_borne_superieure_dix(self, learning):
        recipe = _make_recipe(1, cuisine="japonais")
        prefs  = _prefs(cuisines_favorite={"japonais"})
        final, _ = learning.mod.apply_learning_bonus(recipe, 9.8, prefs)
        assert final <= 10.0

    def test_retourne_bonus_applique(self, learning):
        recipe = _make_recipe(1, cuisine="japonais")
        prefs  = _prefs(cuisines_favorite={"japonais"})
        final, bonus = learning.mod.apply_learning_bonus(recipe, 7.0, prefs)
        assert bonus == pytest.approx(learning.mod.BONUS_CUISINE)
        assert final == pytest.approx(7.0 + learning.mod.BONUS_CUISINE)

    def test_prefs_inactives_score_inchange(self, learning):
        recipe = _make_recipe(1)
        final, bonus = learning.mod.apply_learning_bonus(
            recipe, 6.5, _prefs(active=False))
        assert final == pytest.approx(6.5)
        assert bonus == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# rank_with_learning
# ═══════════════════════════════════════════════════════════════════════════════

class TestRankWithLearning:

    def test_sans_email_retourne_liste_inchangee(self, learning):
        recipes = [_make_recipe(1, final_score=8.0),
                   _make_recipe(2, final_score=6.0)]
        result  = learning.mod.rank_with_learning(recipes, email="")
        assert result is recipes  # même objet

    def test_injecte_learning_bonus_et_personalized_score(self, learning):
        # Historique insuffisant → prefs inactives → bonus 0
        path = learning.history_dir / "rank_at_test_com.json"
        path.write_text(json.dumps({"liked": [1], "disliked": [], "viewed": []}))

        recipes = [_make_recipe(1, final_score=7.0)]
        result  = learning.mod.rank_with_learning(recipes, "rank@test.com")
        assert "_learning_bonus"     in result[0]
        assert "_personalized_score" in result[0]

    def test_tri_par_score_personnalise(self, learning):
        # Préparer un historique avec assez de likes
        ids = list(range(1, 7))
        path = learning.history_dir / "tri_at_test_com.json"
        path.write_text(json.dumps({
            "liked": ids, "disliked": [], "viewed": ids
        }))
        recipes_db = [_make_recipe(i, cuisine="japonais") for i in ids]
        learning.data_io.load_recipes = lambda: recipes_db

        # Recette 99 a la cuisine favorite → doit remonter
        to_rank = [
            _make_recipe(10, final_score=7.0, cuisine="autre"),
            _make_recipe(11, final_score=7.0, cuisine="japonais"),
        ]
        result = learning.mod.rank_with_learning(to_rank, "tri@test.com")
        # La recette avec cuisine favorite doit être en tête
        assert result[0]["id"] == 11


# ═══════════════════════════════════════════════════════════════════════════════
# get_user_stats
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetUserStats:

    def test_structure_de_retour(self, learning):
        stats = learning.mod.get_user_stats("stats@test.com")
        required = {"email", "liked_count", "disliked_count", "viewed_count",
                    "personalization_active", "min_likes_required", "preferences"}
        assert required <= stats.keys()

    def test_email_dans_retour(self, learning):
        stats = learning.mod.get_user_stats("hello@test.com")
        assert stats["email"] == "hello@test.com"

    def test_preferences_vides_si_inactif(self, learning):
        stats = learning.mod.get_user_stats("nouveau@test.com")
        assert stats["personalization_active"] is False
        assert stats["preferences"] == {}

    def test_min_likes_required_coherent(self, learning):
        stats = learning.mod.get_user_stats("x@test.com")
        assert stats["min_likes_required"] == learning.mod.MIN_LIKES_TO_ACTIVATE
