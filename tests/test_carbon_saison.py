"""Empreinte carbone selon le mois : Agribalyse 3.2 distingue la tomate et la fraise de
saison et hors saison (carbon_footprint_sources.json, « saisonnier »)."""
from backend.core.data_io import load_recipes
from backend.engine.rule_engine.carbon import carbon_score, _seasonal_co2_per_100g

IDX = {r["id"]: r for r in load_recipes()}
GASPACHO = "soup_gaspacho_provencal_f69228"


def test_gaspacho_plus_lourd_en_hiver():
    r = IDX[GASPACHO]
    hiver, ete, annuel = (carbon_score(r, m)["per_portion_kg"] for m in (1, 7, None))
    assert ete < annuel < hiver
    assert hiver > 2 * ete          # tomate hors saison 2,11 contre 0,63 kg CO₂e/kg


def test_sans_mois_moyenne_annuelle():
    r = IDX[GASPACHO]
    assert carbon_score(r)["per_portion_kg"] == carbon_score(r, None)["per_portion_kg"]
    assert carbon_score(r)["month"] is None


def test_seuls_les_produits_frais_du_calendrier():
    assert _seasonal_co2_per_100g("tomato_raw_ripe", "tomato", 1) > _seasonal_co2_per_100g(
        "tomato_raw_ripe", "tomato", 7)
    # le ketchup partage la clé « tomato » mais ne suit pas la saison
    assert _seasonal_co2_per_100g("tomato_ketchup_catsup_pre_packaged_normal", "tomato", 1) is None
    assert _seasonal_co2_per_100g("strawberry_raw", "strawberry", 5) is not None
    assert _seasonal_co2_per_100g("tomato_raw_ripe", "tomato", None) is None


def test_plat_sans_tomate_ni_fraise_insensible_au_mois():
    r = next(r for r in IDX.values() if r["composition"]
             and not any(c["ingredient"] in ("tomato_raw_ripe", "strawberry_raw")
                         for c in r["composition"]))
    assert carbon_score(r, 1)["per_portion_kg"] == carbon_score(r, 7)["per_portion_kg"]


def test_cartes_et_fiche_portent_la_saison_du_mois():
    # badge « De saison » des cartes (enrich_why) = même calcul que la fiche (enrich_one)
    from backend.services.enrichment_service import enrich_one, enrich_why, seasonal_tag
    r = IDX["side_gratin_celeri_rave_noix_7a19e6"]
    assert seasonal_tag(r, 1)[0] == "de_saison" and seasonal_tag(r, 7)[0] == "hors_saison"
    carte = enrich_why([r])[0]
    fiche = enrich_one(r)
    assert carte["seasonal_tag"] == fiche["seasonal_tag"]
    assert fiche["season_month"] == fiche["carbon_data"]["month"]


def test_prix_estimes_signales():
    from backend.engine.planning_engine.budget import estimate_price
    noms = [e["name_fr"] for e in estimate_price(IDX["soup_potage_oseille_0f7d29"])["estimated_ingredients"]]
    assert noms == ["oseille"]
    # le vinaigre de vin rouge a son prix propre, relevé le 2026-11-20 : plus rien d'estimé
    assert estimate_price(IDX["soup_gaspacho_provencal_f69228"])["estimated_ingredients"] == []


def test_route_de_saison():
    from fastapi.testclient import TestClient
    from backend.api.main import app
    c = TestClient(app)
    nov = c.get("/recettes/de-saison?month=11&limit=3").json()
    assert nov["month"] == 11 and len(nov["results"]) == 3 and nov["total"] == len(nov["ids"])
    assert "side_gratin_celeri_rave_noix_7a19e6" in nov["ids"]
    assert "soup_gaspacho_provencal_f69228" not in nov["ids"]
    assert all(r["seasonal_tag"] == "de_saison" for r in nov["results"])
    assert c.get("/recettes/de-saison?month=13").status_code == 422


def test_route_de_saison_regime():
    """Profil vegan : la rubrique de l'accueil ne propose que des plats vegan, mais
    le badge « De saison » (ids) couvre toujours tout le catalogue."""
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.services.filter_service import match_diet
    c = TestClient(app)
    tous = c.get("/recettes/de-saison?month=11&limit=50").json()
    veg = c.get("/recettes/de-saison?month=11&limit=50&diet=vegan").json()
    assert veg["ids"] == tous["ids"]
    assert 6 <= veg["total"] < tous["total"]
    assert veg["results"] and all(match_diet(IDX[r["id"]], "vegan") for r in veg["results"])
    assert any(not match_diet(IDX[r["id"]], "vegan") for r in tous["results"])


def test_ketchup_n_est_plus_une_tomate():
    from backend.core.data_io import load_prices_catalog, load_carbon_footprint, resolve_catalog_key
    iid = "tomato_ketchup_catsup_pre_packaged_normal"
    assert resolve_catalog_key(iid, load_prices_catalog()) == "ketchup"
    assert resolve_catalog_key(iid, load_carbon_footprint()) == "ketchup"


def test_prix_estime_nomme_la_sous_recette():
    """« prix estimé : Paneer », pas l'identifiant « base paneer 04e1db »."""
    from backend.engine.planning_engine.budget import estimate_price
    est = estimate_price(IDX["base_mala_broth_1ab129"])["estimated_ingredients"]
    assert {"id": "base_doubanjiang_paste_340399", "name_fr": "Pâte Doubanjiang"} in est
    for r in IDX.values():
        if r.get("composition"):
            p = estimate_price(r)
            assert all(not e["name_fr"].startswith("base ")
                       for e in p["estimated_ingredients"] + p["unknown_ingredients"]), r["id"]


def test_plus_aucun_prix_inconnu():
    """Feuilles de maïs, moringa, tomatilles et roselle ont leur prix (estimé)."""
    from backend.engine.planning_engine.budget import estimate_price
    sans_prix = [r["id"] for r in IDX.values() if r.get("composition") and not estimate_price(r)["complete"]]
    assert sans_prix == []
    p = estimate_price(IDX["dal_sambar_581de8"])
    assert "drumstick_horseradish_tree_raw_pod" in [e["id"] for e in p["estimated_ingredients"]]
