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
    assert estimate_price(IDX["soup_gaspacho_provencal_f69228"])["estimated_ingredients"] == []
