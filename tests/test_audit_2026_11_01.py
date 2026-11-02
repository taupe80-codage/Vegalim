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


# ── Variante vegan : ne remplaçait rien mais se déclarait vegan ───────────────

def test_variante_substituts_existent_et_sont_vegan():
    from backend.engine.rule_engine.variants import VEGAN_SUBS_CIQUAL, _is_vegan_id
    recipes = load_recipes()
    ids = {c["ingredient"] for r in recipes for c in r["composition"]} | {r["id"] for r in recipes}
    subs = set(VEGAN_SUBS_CIQUAL.values())
    assert subs <= ids
    assert all(_is_vegan_id(s) is True for s in subs)


def _recette_avec(iid):
    return next(r for r in load_recipes() if any(c["ingredient"] == iid for c in r["composition"])
                and not (r.get("diet_flags") or {}).get("vegan"))


def test_variante_remplace_les_ingredients_non_vegan():
    from backend.engine.rule_engine.variants import vegan_variant, _is_vegan_id
    r = _recette_avec("butter_sup80pct")
    res = vegan_variant(r)
    if res["source"] == "partial":
        pytest.skip("recette avec un ingrédient sans substitut")
    assert res["source"] == "generated"
    comp = [c["ingredient"] for c in res["recipe"]["composition"]]
    assert "butter_sup80pct" not in comp and "vegan_butter" in comp
    assert not [i for i in comp if _is_vegan_id(i) is False]
    sub = next(s for s in res["substitutions"] if s["original"] == "butter_sup80pct")
    assert sub["original_name"] and sub["substitute_name"]
    assert res["recipe"]["ingredients_meta"]["vegan_butter"]["name_fr"]
    assert res["recipe"]["diet_flags"]["vegan"] is True


def test_variante_partielle_ne_se_dit_pas_vegan():
    from backend.engine.rule_engine.variants import vegan_variant
    r = _recette_avec("shortcrust_pastry_all_butter_raw_paste_pre_packaged")
    res = vegan_variant(r)
    assert res["source"] == "partial"
    assert any(u["id"] == "shortcrust_pastry_all_butter_raw_paste_pre_packaged" for u in res["unresolved"])
    assert not res["recipe"].get("diet_flags", {}).get("vegan")
    assert "vegan" not in res["recipe"]["tags"].get("diet", [])


def test_route_variante_recette_de_l_ancien_index():
    # L'index pré-calculé faisait renvoyer l'original inchangé
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.core.auth_deps import get_user
    app.dependency_overrides[get_user] = lambda: {"email": "test@exemple.com"}
    try:
        res = TestClient(app).post("/recettes/rice_biryani_classic_k82x7b/variante")
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["substitutions"], data.get("source")
        assert data["source"] in ("generated", "partial")
        vegan = next(r for r in load_recipes() if (r.get("diet_flags") or {}).get("vegan"))
        data = TestClient(app).post(f"/recettes/{vegan['id']}/variante").json()
        assert data["source"] == "already_vegan" and data["substitutions"] == []
    finally:
        app.dependency_overrides.pop(get_user, None)


# ── Saisonnalité : table toujours vide, puis ids CIQUAL non reconnus ──────────

def test_saisonnalite_chargee_et_sans_ingredients_annee_entiere():
    from backend.engine.rule_engine.seasonality import seasonal_ingredients
    ete = seasonal_ingredients(7)
    hiver = seasonal_ingredients(1)
    assert "zucchini" in ete and "tomato" in ete
    assert "water" not in ete and "salt" not in ete
    assert "zucchini" not in hiver and "tomato" not in hiver


def test_saisonnalite_donnees_corrigees():
    # Corrigé le 2026-11-01 : pois chiches « printemps », cannelle « hiver »,
    # graines de courge « automne », tomate 12 mois, potiron et poivrons
    # rouge / vert « toute l'année » alors que squash / bell_pepper ont une saison
    from backend.core.data_io import load_seasonality
    from backend.engine.rule_engine.seasonality import _is_seasonal
    d = load_seasonality()
    for k in ("chickpea_cooked", "cinnamon", "pumpkin_seeds", "ginger"):
        assert not _is_seasonal(d[k]), k
    assert d["tomato"]["months"] == [6, 7, 8, 9]
    assert d["pumpkin"]["months"] == d["squash"]["months"]
    assert d["red_bell_pepper"]["months"] == d["green_bell_pepper"]["months"] == d["bell_pepper"]["months"]


def test_saisonnalite_table_valide():
    from backend.core.data_io import load_seasonality
    from backend.engine.rule_engine.seasonality import SEASON_ID_ALIASES
    ids = {c["ingredient"] for r in load_recipes() for c in r["composition"]}
    assert set(SEASON_ID_ALIASES) <= ids
    assert set(SEASON_ID_ALIASES.values()) <= set(load_seasonality())


@pytest.mark.parametrize("iid", ["tomato_paste_unsalted_canned", "pumpkin_squash_raw_seed",
                                 "fennel_spice_seed", "corn_flour_seed", "pomegranate_juice_plain",
                                 "shiitake_mushroom_dried"])
def test_saisonnalite_produits_transformes_hors_saison(iid):
    from backend.engine.rule_engine.seasonality import season_key
    assert season_key(iid) is None


def test_saisonnalite_ratio_recette():
    from backend.engine.rule_engine.seasonality import season_ratio, season_bonus
    r = {"composition": [{"ingredient": "green_zucchini_squash_raw"},
                         {"ingredient": "eggplant_raw"},
                         {"ingredient": "olive_oil_plant"},
                         {"ingredient": "table_salt_unenriched"}]}
    assert season_ratio(r, 7) == 1.0 and season_bonus(r, 7) == 2.0
    assert season_ratio(r, 1) == 0.0 and season_bonus(r, 1) == 0.0
    assert season_ratio({"composition": [{"ingredient": "table_salt_unenriched"}]}, 7) is None


def test_route_seasonal_mois_valide():
    from fastapi.testclient import TestClient
    from backend.api.main import app
    c = TestClient(app)
    assert c.get("/planning/seasonal?month=13").status_code == 422
    res = c.get("/planning/seasonal?month=7")
    assert res.status_code == 200 and "zucchini" in res.json()["ingredients"]


# ── Astro : 58/593 ids reconnus, filtre « au moins un ingrédient » ────────────

def test_astro_couverture_et_table_valide():
    from collections import Counter
    from backend.core.data_io import load_astro_nutrition
    from backend.engine.rule_engine.astro import ASTRO_ID_ALIASES, astro_key
    data = load_astro_nutrition()
    cnt = Counter(c["ingredient"] for r in load_recipes() for c in r["composition"])
    assert set(ASTRO_ID_ALIASES) <= set(cnt)
    assert set(ASTRO_ID_ALIASES.values()) <= set(data)
    covered = sum(n for iid, n in cnt.items() if astro_key(iid, data))
    assert covered / sum(cnt.values()) > 0.9


@pytest.mark.parametrize("iid,key", [
    ("egg_raw", "oeuf"), ("soy_sauce_shoyu_reduced_sodium", "sauce_soja"),
    ("tomato_raw_ripe", "tomato"), ("almond_raw_skinless_unsalted", "almond"),
    ("cashew_butter_plain_plant", "noix_de_cajou"),   # table des prix : « butter »
    ("capers_canned_in_vinegar", "capre"),            # table des prix : « vinegar »
    ("rose_water", None), ("orange_blossom_water", None),
])
def test_astro_correspondances(iid, key):
    from backend.engine.rule_engine.astro import astro_key
    assert astro_key(iid) == key


@pytest.mark.parametrize("element", ["feu", "Terre", "air", "eau"])
def test_filtre_astro_element_dominant(element):
    from backend.engine.rule_engine.astro import dominant_element
    recipes = load_recipes()
    page, total = apply_filters(recipes, astro_element=element, limit=len(recipes))
    assert 0 < total < len(recipes) * 0.9   # « au moins un ingrédient » : 990/1000 en feu
    assert all(dominant_element(r) == element.lower() for r in page)


def test_moteur_recherche_carte_astro_chargee():
    from backend.engine.search_engine.core import (_IndexCache, _default_astro_path,
                                                    _astro_element_bonus, _moon_phase_bonus)
    cache = _IndexCache.get()
    cache.load_astro(_default_astro_path())
    assert len(cache._astro) > 300
    r = next(r for r in load_recipes() if r["titles"]["fr"] == "Harissa")
    assert _astro_element_bonus(r, "feu", cache) == _astro_element_bonus(r, "Feu", cache) > 0.5
    assert 0 <= _moon_phase_bonus(r, "pleine_lune", cache) <= 1


# ── Mon frigo : tables synonymes / exclusions sur les ids actuels ─────────────

def test_frigo_tables_sur_ids_reels():
    from backend.api.routes.frigo import _SYNONYMS, _EXCLUSIONS, _get_all_recipe_ingredient_ids
    known = _get_all_recipe_ingredient_ids()
    assert {i for pair in _EXCLUSIONS for i in pair} <= known
    assert set(_SYNONYMS) <= known
    assert {i for v in _SYNONYMS.values() for i in v} <= known


@pytest.mark.parametrize("fridge,recipe,expected", [
    ("rice", "rice_flour", False), ("rice", "rice_vermicelli_raw_dried", False),
    ("lemon", "lemon_grass_fresh_herb", False), ("lemon", "lemon_juice", True),
    ("cream", "vanilla_ice_cream", False), ("cream", "cream_heavy", True),
    ("water", "rose_water", False),
    ("persil", "parsley_fresh_herb", True), ("parsley_fresh_herb", "persil", True),
])
def test_frigo_correspondances(fridge, recipe, expected):
    from backend.api.routes.frigo import _ingredient_matches
    assert _ingredient_matches(fridge, recipe) is expected


def test_frigo_riz_couvre_le_riz_blanc_pas_la_farine():
    from backend.api.routes.frigo import _fridge_coverage
    have, missing = _fridge_coverage({"rice"}, {"white_rice_raw_seed_unenriched",
                                                "basmati_rice_raw_seed", "rice_flour"})
    assert have == {"white_rice_raw_seed_unenriched", "basmati_rice_raw_seed"}
    assert missing == {"rice_flour"}


# ── Catalogue : nom de base + axe « forme » (rice_flour = « riz » + farine) ───

@pytest.mark.parametrize("iid,fr,en", [
    ("rice_flour", "farine de riz", "rice flour"),
    ("olive_oil_plant", "huile d'olive", "olive oil"),
    ("soybean_milk_unsweetened_plant", "lait de soja", "soybean milk"),
    ("orange_juice_plain", "jus d'orange", "orange juice"),
    ("tomato_paste_unsalted_canned", "concentré de tomate", "tomato paste"),
    ("coriander_spice_seed", "graines de coriandre", "coriander seeds"),
    ("bay_leaf_spice", "feuilles de laurier", "bay leaf"),
    ("cream_liquid_uht", "crème", "cream"),                 # « liquide » ne change pas le produit
    ("bread_flour_blanched", "farine à pain", "bread flour"),
])
def test_catalogue_nom_complet(iid, fr, en):
    from backend.core.data_io import load_ingredients_dict
    from backend.services.ingredient_catalog import full_name_fr, full_name_en
    entry = load_ingredients_dict()[iid]
    assert full_name_fr(entry, iid) == fr
    assert full_name_en(entry, iid) == en


@pytest.mark.parametrize("word,expected,forbidden", [
    ("riz", "rice", "rice_flour"),
    ("farine de riz", "rice_flour", None),
    ("olive", "black_olive_canned_in_brine", "olive_oil_plant"),
    ("citron", "lemon", None),
    ("maïs", "sweet_corn_raw_fresh", "cornstarch_flour"),
    ("cannelle", "cinnamon", None),
])
def test_frigo_mots_francais(word, expected, forbidden):
    from backend.services.ingredient_catalog import resolve_names
    ids = resolve_names([word]).get(word, [])
    assert expected in ids
    assert forbidden not in ids


# ── Planning : filtres santé / origines multiples ignorés à la génération ─────

def _plan_ids(data):
    return [data[d][m]["id"] for d in data if d != "meta" for m in data[d]]


@pytest.mark.parametrize("query,check", [
    ("cuisines=italian,japanese",
     lambda r, hs: (r.get("origin") or {}).get("cuisine") in ("italian", "japanese")),
    ("high_protein=true", lambda r, hs: hs.get("high_protein")),
    ("fodmap=low",        lambda r, hs: hs.get("fodmap_level") == "low"),
    ("high_fiber=true",   lambda r, hs: hs.get("high_fiber")),   # aucun plat < 200 mg de sodium
])
def test_mealplan_applique_les_filtres(query, check):
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.services.filter_service import _hs
    by_id = {r["id"]: r for r in load_recipes()}
    res = TestClient(app).get(f"/planning/mealplan?dish_type=main&diversity=0&{query}")
    assert res.status_code == 200, res.text
    ids = _plan_ids(res.json())
    assert ids
    assert all(check(by_id[i], _hs(by_id[i])) for i in ids), query


# ── Liste de courses : portions du créneau transmises ─────────────────────────

def test_liste_de_courses_suit_les_portions_du_creneau():
    from fastapi.testclient import TestClient
    from backend.api.main import app
    r = next(r for r in load_recipes()
             if (r.get("servings") or 0) >= 2 and r.get("composition")
             and all(c.get("unit") == "g" and c.get("quantity") for c in r["composition"]))
    c = TestClient(app)
    def total(servings):
        slot = {"id": r["id"], "title": ""}
        if servings:
            slot["servings"] = servings
        data = c.post("/planning/shopping_list", json={"plan": {"lundi": {"lunch_0": slot}}}).json()
        return sum(float(i.get("qty_value") or 0) for i in data["items"])
    base = total(None)
    assert base > 0
    assert total(r["servings"] * 2) == pytest.approx(base * 2, rel=0.05)


# ── Ménopause : « tags=… » inexistant, la page montrait le top général ───────

def test_recettes_menopause():
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.core.data_io import is_component_recipe
    from backend.services.filter_service import menopause_score, MENOPAUSE_MIN_SCORE
    data = TestClient(app).get("/recettes?menopause=true&limit=500").json()
    assert 50 < data["total"] < 600
    by_id = {r["id"]: r for r in load_recipes()}
    scores = [menopause_score(by_id[r["id"]]) for r in data["results"]]
    assert min(scores) >= MENOPAUSE_MIN_SCORE
    assert scores == sorted(scores, reverse=True)
    assert not any(is_component_recipe(by_id[r["id"]]) for r in data["results"])


# ── planning.py, frigo.py : texte doublement encodé (mojibake) visible ───────

@pytest.mark.parametrize("path", ["backend/api/routes/planning.py",
                                  "backend/api/routes/frigo.py"])
def test_routes_sans_mojibake(path):
    import re
    from pathlib import Path
    src = Path(path).read_text(encoding="utf-8")
    assert not re.search(r"Ã.|â€|â\"|â†|Â", src)


def test_frigo_swagger_lisible():
    from backend.api.main import app
    schema = app.openapi()["components"]["schemas"]["MissingRequest"]
    assert schema["properties"]["fridge"]["description"] == "Ingrédients disponibles"


def test_export_ics_titre_lisible():
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.core.auth_deps import get_user
    app.dependency_overrides[get_user] = lambda: {"email": "test@exemple.com"}
    try:
        res = TestClient(app).post("/planning/mealplan/export_ics",
                                   json={"plan": {"lundi": {"lunch": {"id": "x", "title": "Ratatouille"}}}})
        assert res.status_code == 200, res.text
        assert "SUMMARY:lunch — Ratatouille" in res.json()["ics_content"]
    finally:
        app.dependency_overrides.pop(get_user, None)
