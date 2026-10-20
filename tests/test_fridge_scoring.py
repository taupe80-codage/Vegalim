"""
Mon frigo : pondération basique / courant / spécial / ingrédient principal.

Régression visée : avoir des œufs ne doit pas faire remonter une omelette
devant un gratin de courges quand le frigo contient aussi des courges.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes import frigo
from backend.services.fridge_scoring import (
    ACCENT, COMMON, SPECIAL, STAPLE,
    has_substance, recipe_weights, relevance, tier_of_id,
)


def _ing(iid, role, qty=100, unit="g", **meta):
    return {"ingredient": iid, "quantity": qty, "unit": unit, "meta": {"role": role, **meta}}


GRATIN = {
    "id": "gratin_courge",
    "titles": {"fr": "Gratin de courge"},
    "composition": [
        _ing("butternut_squash_raw", "vegetable", 800),
        _ing("egg_raw", "binder", 55),
        _ing("butter_sup80pct", "fat", 30),
        _ing("table_salt_unenriched", "seasoning", 5),
        _ing("black_pepper_spice", "spice", 1),
    ],
}
OMELETTE = {
    "id": "omelette",
    "titles": {"fr": "Omelette nature"},
    "composition": [
        _ing("egg_raw", "protein", 220),
        _ing("butter_sup80pct", "fat", 10),
        _ing("table_salt_unenriched", "seasoning", 2),
    ],
}
SOUP_WITH_GARLIC = {
    "id": "soupe_ail",
    "titles": {"fr": "Soupe à l'ail"},
    "composition": [
        _ing("garlic_raw", "aromatic", 40),
        _ing("water", "liquid", 500, "ml"),
        _ing("table_salt_unenriched", "seasoning", 3),
    ],
}


SOUPE_POIREAU = {
    "id": "soupe_poireau",
    "titles": {"fr": "Soupe de poireaux"},
    "composition": [
        _ing("leeks_raw", "vegetable", 500),
        _ing("potato_raw_flesh", "vegetable", 300),
        _ing("spinach_raw_mature", "vegetable", 100),
        _ing("water", "liquid", 800, "ml"),
    ],
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(frigo, "load_recipes",
                        lambda: [OMELETTE, GRATIN, SOUP_WITH_GARLIC, SOUPE_POIREAU])
    monkeypatch.setattr(frigo, "load_ingredients_dict", lambda: {})
    monkeypatch.setattr(frigo, "_recipe_ing_cache", None)   # rebuilt from the recipes above
    app = FastAPI()
    app.include_router(frigo.router)
    return TestClient(app)


def _suggest(client, ingredients, max_missing=3):
    r = client.post("/frigo/suggestions", json={"ingredients": ingredients, "max_missing": max_missing})
    assert r.status_code == 200, r.text
    return r.json()["results"]


# ── Niveaux ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("iid,tier", [
    ("table_salt_unenriched", STAPLE),
    ("black_pepper_spice", STAPLE),
    ("water", STAPLE),
    ("olive_oil_plant", STAPLE),
    ("butter_sup80pct", STAPLE),
    ("butter", STAPLE),
    ("egg", COMMON),
    ("egg_raw", COMMON),
    ("milk_liquid_uht_3_5pct", COMMON),
    ("garlic", ACCENT),
    ("tofu", SPECIAL),
    ("leek", SPECIAL),
    ("ghee", SPECIAL),
    ("butternut", SPECIAL),                 # ne commence pas « beurre » pour autant
    ("butternut_squash_raw", SPECIAL),
    ("peanut_butter", SPECIAL),
    ("sesame_tahini_raw_butter_seed_plant", SPECIAL),
    ("sichuan_pepper", SPECIAL),            # pas le poivre noir de cuisine
    ("red_bell_pepper_raw", SPECIAL),
    ("coconut_milk_plant", SPECIAL),
    ("cows_milk_mozzarella_cow", SPECIAL),
])
def test_tier_of_id(iid, tier):
    assert tier_of_id(iid) == tier


def test_role_demotes_unknown_ingredient():
    """Un ingrédient inconnu hérite du niveau de son rôle (épice, graisse…)."""
    w = recipe_weights([_ing("sambar_powder", "spice"), _ing("mystery_fat", "fat")])
    assert w["sambar_powder"][1] == ACCENT
    assert w["mystery_fat"][1] == STAPLE


# ── Poids ────────────────────────────────────────────────────────────────────

def test_main_ingredient_outweighs_staples_and_commons():
    w = recipe_weights(GRATIN["composition"])
    squash = w["butternut_squash_raw"][0]
    assert squash > w["egg_raw"][0] > w["butter_sup80pct"][0]
    assert squash > 5 * w["table_salt_unenriched"][0]


def test_egg_weighs_more_when_it_carries_the_recipe():
    in_omelette = recipe_weights(OMELETTE["composition"])["egg_raw"][0]
    in_gratin = recipe_weights(GRATIN["composition"])["egg_raw"][0]
    assert in_omelette > in_gratin


def test_optional_item_weighs_less():
    w = recipe_weights([
        _ing("tofu_plain", "protein"),
        _ing("lime_zest", "ingredient", optional=True),
        _ing("lime_zest_b", "ingredient"),
    ])
    assert w["lime_zest"][0] < w["lime_zest_b"][0]


def test_relevance_caps_common_products():
    """Œufs + lait + beurre ne saturent pas la pertinence d'une recette."""
    w = recipe_weights([
        _ing("egg_raw", "protein", 200),
        _ing("milk_liquid_uht", "liquid", 300, "ml"),
        _ing("cream_heavy", "fat", 100),
    ])
    _, _, use = relevance(w, {"egg_raw", "milk_liquid_uht", "cream_heavy"})
    assert use <= 0.5


def test_has_substance():
    w = recipe_weights(SOUP_WITH_GARLIC["composition"])
    assert not has_substance(w, {"garlic_raw", "water", "table_salt_unenriched"})
    assert has_substance(recipe_weights(OMELETTE["composition"]), {"egg_raw"})


# ── Route ────────────────────────────────────────────────────────────────────

def test_gratin_beats_omelette_when_fridge_has_squash_and_eggs(client):
    ids = [r["id"] for r in _suggest(client, ["egg", "butternut"])]
    assert ids.index("gratin_courge") < ids.index("omelette")


def test_omelette_still_suggested_with_eggs_alone(client):
    results = _suggest(client, ["egg"])
    assert results[0]["id"] == "omelette"


def test_staples_are_assumed_not_missing(client):
    by_id = {r["id"]: r for r in _suggest(client, ["egg", "butternut"], max_missing=0)}
    gratin = by_id["gratin_courge"]
    assert gratin["n_missing"] == 0
    assert gratin["completeness"] == 1.0
    assert {a["id"] for a in gratin["assumed"]} == {
        "butter_sup80pct", "table_salt_unenriched", "black_pepper_spice",
    }


def test_recipe_matching_only_an_aromatic_is_dropped(client):
    """Avec du tofu au frigo, une recette qui n'utilise que l'ail n'est pas proposée."""
    ids = [r["id"] for r in _suggest(client, ["tofu", "garlic", "egg"])]
    assert "soupe_ail" not in ids


def test_fridge_of_staples_only_does_not_empty_the_results(client):
    """Frigo sans rien de discriminant : on ne filtre pas sur le fond."""
    results = _suggest(client, ["garlic"])
    assert [r["id"] for r in results] == ["soupe_ail"]


# ── Français ─────────────────────────────────────────────────────────────────

def _post(client, ingredients, max_missing=3):
    r = client.post("/frigo/suggestions", json={"ingredients": ingredients, "max_missing": max_missing})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("typed", ["poireau", "poireaux", "Poireaux", "leek"])
def test_leek_in_french_and_english(client, typed):
    data = _post(client, [typed])
    assert [r["id"] for r in data["results"]] == ["soupe_poireau"]
    assert data["unrecognized"] == []


@pytest.mark.parametrize("typed", ["épinards", "Épinards", "epinards", "spinach"])
def test_accents_and_plurals_are_ignored(client, typed):
    assert "soupe_poireau" in [r["id"] for r in _post(client, [typed])["results"]]


def test_multiword_french_name_with_underscores(client):
    """La page frigo envoie « pommes de terre » sous la forme pommes_de_terre."""
    data = _post(client, ["pommes_de_terre"])
    assert "soupe_poireau" in [r["id"] for r in data["results"]]
    understood = data["resolved"]["pommes_de_terre"]
    assert "potato_raw_flesh" in [x["id"] for x in understood]
    assert {x["name_fr"] for x in understood} == {"pomme de terre"}


def test_oeufs_french_spelling(client):
    for typed in ("œufs", "oeufs", "oeuf"):
        assert _post(client, [typed])["results"][0]["id"] == "omelette", typed


def test_unknown_name_is_reported_not_silent(client):
    data = _post(client, ["poireaux", "xylophone"])
    assert data["unrecognized"] == ["xylophone"]
    assert data["results"]          # le reste du frigo est quand même exploité


def test_french_and_english_keys_give_the_same_ranking(client):
    fr = [r["id"] for r in _post(client, ["œufs", "courge butternut"])["results"]]
    en = [r["id"] for r in _post(client, ["egg", "butternut"])["results"]]
    assert fr == en


def test_coverage_accepts_french(client):
    r = client.get("/frigo/coverage", params={"keys": "poireaux,leek,xylophone"})
    assert r.json() == {"covered": ["poireaux", "leek"], "uncovered": ["xylophone"]}


def test_catalog_search_ignores_accents_and_plurals():
    from backend.services.ingredient_catalog import search
    for q in ("epinards", "épinards", "Épinard"):
        assert any(e["id"].startswith("spinach") for e in search(q)), q
    assert any(e["id"] == "leeks_raw" for e in search("poireaux"))
    assert any(e["id"] == "egg_raw" for e in search("oeuf"))
