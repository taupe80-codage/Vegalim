"""
tests/test_audit_2026_11_01.py — Régressions relevées par l'audit de cohérence du 2026-11-01.
"""
from __future__ import annotations

import pytest

from backend.core.data_io import load_recipes
from backend.services.filter_service import apply_filters


# ── Filtre difficulté : « Difficile » renvoyait 0 recette ────────────────────

@pytest.mark.parametrize("value", ["hard", "difficile", "advanced"])
def test_filtre_difficile_trouve_les_recettes_hard(value):
    recipes = load_recipes()
    page, total = apply_filters(recipes, difficulty=value, limit=len(recipes))
    expected = sum(1 for r in recipes if r.get("difficulty_level") == "hard")
    assert expected > 0
    assert total == expected
    assert all(r["difficulty_level"] == "hard" for r in page)


# ── Filtre technique : lisait r["technique"], absent des données ──────────────

def test_filtre_technique_lit_tags_technique():
    recipes = load_recipes()
    page, total = apply_filters(recipes, technique="Blending", limit=len(recipes))
    expected = sum(1 for r in recipes if "blending" in r["tags"].get("technique", []))
    assert expected > 0
    assert total == expected


# ── GET /ingredients/{id} : recettes associées lues dans composition[] ────────

def test_fiche_ingredient_liste_ses_recettes():
    from fastapi.testclient import TestClient
    from backend.api.main import app

    recipes = load_recipes()
    iid = recipes[0]["composition"][0]["ingredient"]
    expected = sum(1 for r in recipes if any(c.get("ingredient") == iid for c in r["composition"]))
    res = TestClient(app).get(f"/ingredients/{iid}")
    assert res.status_code == 200, res.text
    assert res.json()["recipes_count"] == expected > 0


# ── /nutrition : identifiants de recette textuels (répondaient 422) ───────────

def test_nutrition_accepte_les_ids_textuels():
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.core.auth_deps import get_user

    rid = load_recipes()[0]["id"]
    app.dependency_overrides[get_user] = lambda: {"email": "test@exemple.com"}
    try:
        c = TestClient(app)
        res = c.post("/nutrition/ajr_score", json={"recipe_id": rid})
        assert res.status_code == 200, res.text
        assert res.json()["ajr_score"] > 0
        res = c.post("/nutrition/alerts", json={"recipe_ids": [rid]})
        assert res.status_code == 200, res.text
        assert res.json()["avg_per_meal"].get("calories", 0) > 0
    finally:
        app.dependency_overrides.pop(get_user, None)


# ── /profil : sauvegarde sans objectif, consentement, révocation ──────────────

@pytest.fixture
def profil_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.core.auth_deps import get_user
    from backend.services import profile_service

    monkeypatch.setattr(profile_service, "_use_db", lambda: False)
    monkeypatch.setattr(profile_service, "_FILE", tmp_path / "user_profiles.json")
    app.dependency_overrides[get_user] = lambda: {"email": "profil@exemple.com"}
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_user, None)


def test_profil_regime_et_objectif_vide_sans_consentement(profil_client):
    # La page envoyait toujours goal="" : 403 à chaque sauvegarde
    res = profil_client.post("/profil/update", json={"diet": "vegan", "goal": ""})
    assert res.status_code == 200, res.text
    assert profil_client.get("/profil/").json()["diet"] == "vegan"


def test_profil_objectif_exige_le_consentement(profil_client):
    assert profil_client.post("/profil/update", json={"goal": "energie"}).status_code == 403
    assert profil_client.patch("/profil/consent", json={"health_consent": True}).status_code == 200
    assert profil_client.post("/profil/update", json={"goal": "energie"}).status_code == 200
    assert profil_client.get("/profil/").json()["health_goal"] == "energie"


def test_profil_revocation_efface_les_donnees_de_sante(profil_client):
    profil_client.patch("/profil/consent", json={"health_consent": True})
    profil_client.post("/profil/update", json={"goal": "energie", "diet": "vegan"})
    res = profil_client.patch("/profil/consent", json={"health_consent": False})
    assert res.status_code == 200
    p = profil_client.get("/profil/").json()
    assert not p.get("health_goal") and not p.get("goal") and not p.get("cycle_phase")
    assert p["health_consent"] is False
    assert p["diet"] == "vegan"


# ── FODMAP : identifiants CIQUAL reconnus (634/643 recettes ail/oignon « low ») ─

_ALLIACEES = {"garlic_raw", "onion_raw", "yellow_onion_raw", "white_onion_raw",
              "red_onion_raw", "shallot_raw"}


def test_fodmap_aucune_recette_ail_oignon_en_low():
    from backend.engine.rule_engine.diet import compute_fodmap
    recipes = [r for r in load_recipes()
               if any(c.get("ingredient") in _ALLIACEES for c in r["composition"])]
    assert len(recipes) > 500
    low = [r["id"] for r in recipes if compute_fodmap(r)["fodmap_level"] == "low"]
    assert low == []


def test_filtre_low_fodmap_exclut_ail_et_oignon():
    recipes = load_recipes()
    page, total = apply_filters(recipes, fodmap="low", limit=len(recipes))
    assert 0 < total < len(recipes) // 4
    assert not [r["id"] for r in page
                if any(c.get("ingredient") in _ALLIACEES for c in r["composition"])]


@pytest.mark.parametrize("iid", ["cornstarch_flour", "buckwheat_flour", "almond_flour",
                                 "pumpkin_squash_raw_seed", "napa_cabbage_raw",
                                 "sourdough_bread", "chives_raw_fresh", "base_soy_cream_4dc027"])
def test_fodmap_pas_de_faux_declencheur(iid):
    # La table des prix les rangeait sous flour / pumpkin / cabbage / cream
    from backend.engine.rule_engine.diet import _fodmap_key
    assert _fodmap_key(iid) is None


def test_fodmap_deplie_les_sous_recettes():
    from backend.engine.rule_engine.diet import compute_fodmap
    r = {"servings": 1, "composition": [
        {"ingredient": "white_rice_raw_seed_unenriched", "quantity": 80, "unit": "g"},
        {"ingredient": "base_pesto_905db7", "quantity": 15, "unit": "g"},  # pesto à l'ail
    ]}
    res = compute_fodmap(r)
    assert res["fodmap_level"] != "low"
    assert "fructanes" in res["fodmap_categories"]


def test_fodmap_quantite_inconnue_reste_prudente():
    from backend.engine.rule_engine.diet import compute_fodmap
    r = {"servings": 4, "composition": [
        {"ingredient": "strawberry", "quantity": 500, "unit": "g"},
        {"ingredient": "toast", "quantity": None, "unit": "2-3 toasts"},
    ]}
    assert compute_fodmap(r)["fodmap_level"] != "low"


def test_fodmap_meme_calcul_pour_filtres_et_health_scores():
    from backend.engine.rule_engine.diet import compute_fodmap
    from backend.services.filter_service import _build_hs_cache
    cache = _build_hs_cache()
    for r in load_recipes()[:200]:
        fm = compute_fodmap(r)
        assert cache[r["id"]]["fodmap_level"] == fm["fodmap_level"], r["id"]


# ── Cycle : ids CIQUAL (le filtre trouvait 4 / 0 / 5 / 0 recettes) ────────────

_PHASES = ("menstrual", "follicular", "ovulatory", "luteal")


@pytest.mark.parametrize("phase", _PHASES)
def test_filtre_cycle_trouve_des_recettes(phase):
    from backend.engine.cycle_engine import cycle_id_map
    recipes = load_recipes()
    page, total = apply_filters(recipes, cycle_phase=phase, limit=len(recipes))
    assert total >= 100
    good = set(cycle_id_map(phase))
    assert all(any(c["ingredient"] in good for c in r["composition"]) for r in page)


def test_cycle_table_pointe_vers_des_ids_reels():
    from backend.engine.cycle_engine import CYCLE_CONCEPT_IDS
    ids = {c["ingredient"] for r in load_recipes() for c in r["composition"]}
    assert {i for v in CYCLE_CONCEPT_IDS.values() for i in v} <= ids


def test_cycle_score_sur_une_vraie_recette_et_phase_courte():
    from backend.engine.cycle_engine import cycle_score, get_phase_info
    assert get_phase_info("menstrual") == get_phase_info("menstrual_phase") != {}
    r = next(r for r in load_recipes()
             if any(c["ingredient"].startswith("spinach") for c in r["composition"]))
    res = cycle_score(r, phase="menstrual")
    assert "spinach" in res["recommended"]
    assert res["score"] > 0


def test_moteur_recherche_bonus_cycle_phase_courte():
    from backend.engine.search_engine.core import _IndexCache, _cycle_bonus, _default_cycle_path
    cache = _IndexCache.get()
    cache.load_cycle(_default_cycle_path())
    recommended, _ = cache.cycle_sets("menstrual")
    assert "spinach_raw_baby" in recommended
    r = next(r for r in load_recipes()
             if any(c["ingredient"].startswith("spinach") for c in r["composition"]))
    assert _cycle_bonus(r, "menstrual", cache) > 0
