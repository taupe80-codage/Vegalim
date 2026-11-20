"""Liste de courses : rayons du magasin, une ligne par produit acheté, pas d'eau du robinet
(2026-11-20 : 56 articles sur 60 d'une semaine tombaient dans « Autre »)."""
import pytest

from backend.engine.planning_engine.shopping import AISLES, aisle_of, shopping_list_from_recipes

SEMAINE = ["soup_potage_oseille_0f7d29", "side_gratin_celeri_rave_noix_7a19e6", "curry_matar_paneer_4a7c19",
           "protein_halloumi_pois_chiches_rotis_7c40e2", "pasta_fave_piselli_pecorino_7d3e52",
           "stew_pot_au_feu_legumes_4f80d7", "rice_kimchi_fried_rice_1f3e90"]


@pytest.mark.parametrize("iid, rayon", [
    # pièges de sous-chaînes : aubergine ≠ œuf, butternut ≠ noix, garam masala ≠ masa,
    # chapelure ≠ rhum, vinaigre de vin ≠ vin, huile de sésame ≠ graines
    ("eggplant_raw", "Fruits & légumes"), ("egg_yolk_raw", "Frais : crèmerie, œufs, tofu"),
    ("butternut_squash_raw", "Fruits & légumes"), ("walnut_shelled_dried", "Fruits secs, noix & graines"),
    ("garam_masala", "Épices & aromates séchés"), ("breadcrumbs_dried", "Féculents & boulangerie"),
    ("red_wine_vinegar_liquid", "Condiments & sauces"), ("white_wine_liquid", "Boissons & laits végétaux"),
    ("sesame_oil_plant", "Huiles & matières grasses"), ("coconut_milk_plant", "Conserves & bocaux"),
    ("tofu_plain_pre_packaged", "Frais : crèmerie, œufs, tofu"), ("parsley_fresh_herb", "Herbes fraîches"),
    ("chickpea_boiled", "Légumineuses"), ("green_peas_raw", "Fruits & légumes"),
    ("base_paneer_04e1db", "Préparations maison"), ("table_salt_unenriched", "Épicerie salée"),
])
def test_rayon(iid, rayon):
    assert aisle_of(iid) == rayon


def test_presque_rien_dans_autre():
    from collections import Counter
    from backend.core.data_io import load_recipes
    use = Counter(c["ingredient"] for r in load_recipes() for c in r["composition"] if c["ingredient"] != "water")
    autre = sum(n for i, n in use.items() if aisle_of(i) == "Autre")
    assert autre / sum(use.values()) < 0.01


def test_liste_par_rayon_sans_eau_ni_doublon_d_achat():
    s = shopping_list_from_recipes(SEMAINE)
    rayons = list(s["by_category"])
    assert rayons == sorted(rayons, key=AISLES.index)          # ordre du magasin
    assert "Autre" not in rayons
    ids = {i["ingredient"] for i in s["items"]}
    assert "water" not in ids
    oeuf = next(i for i in s["items"] if i["ingredient"] == "egg_raw")
    assert [m["ingredient"] for m in oeuf["merged"]] == ["egg_yolk_raw"] and "egg_yolk_raw" not in ids
    assert oeuf["n_packages"] == 1                              # une boîte d'œufs, pas deux
