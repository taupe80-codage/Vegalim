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


def test_agrumes_en_fruits_entiers():
    """Jus et zeste viennent des mêmes citrons : une ligne de citrons entiers, pas un
    citron de plus pour le zeste ; jus d'orange et oranges sur la même ligne."""
    s = shopping_list_from_recipes(["dessert_tarte_citron_meringuee_7f6440",   # 150 ml + 10 g
                                    "rice_risotto_al_limone_4088e5",           # 30 ml + 6 g
                                    "side_fenouil_braise_a_l_orange_a75916",   # 180 g + 150 ml
                                    "main_feijoada_2f6754",                    # 120 ml de jus
                                    "entry_carpaccio_betterave_agrum_ee8b66"]) # 360 g
    agrumes = [i for i in s["items"] if any(k in i["ingredient"] for k in ("lemon", "orange"))]
    assert len(agrumes) == 2
    citron = next(i for i in agrumes if i["name_fr"] == "Citron")
    # 180 ml de jus = 4,5 citrons ; 16 g de zeste = 2,7 citrons → 5 citrons, un filet
    assert (citron["qty_value"], citron["qty_unit"]) == (5, "piece")
    assert citron["n_packages"] == 1 and citron["price_eur"] == 2.21
    assert {m["name_fr"]: m["qty_str"] for m in citron["merged"]} == {"Jus de citron": "180 ml", "Zeste de citron": "16 g"}
    orange = next(i for i in agrumes if i["name_fr"] == "Oranges")
    # 540 g entiers + 270 ml de jus (0,4 ml/g) = 1 215 g
    assert (orange["qty_value"], orange["qty_unit"]) == (1215, "g")
    assert [(m["name_fr"], m["qty_str"]) for m in orange["merged"]] == [("Jus d'orange", "270 ml")]


def test_jus_seul_inchange():
    """Jus seul : la ligne reste en ml, déjà chiffrée en fruits par le catalogue."""
    s = shopping_list_from_recipes(["main_feijoada_2f6754"])
    jus = next(i for i in s["items"] if "orange" in i["ingredient"])
    assert jus["qty_unit"] == "ml" and jus["package_label"].startswith("1 kg d'oranges")


def _fusion(units_by_ing):
    from backend.core.data_io import load_ingredients_dict, load_prices_catalog
    from backend.engine.planning_engine.shopping import _make_resolvers, _merge_same_product
    get_name_fr, _ = _make_resolvers(load_ingredients_dict())
    data = {k: {"occurrences": 1, "units": u} for k, u in units_by_ing.items()}
    out = _merge_same_product(data, load_prices_catalog(), get_name_fr)
    return {k: (v.get("name_fr") or get_name_fr(k), [m["name_fr"] for m in v.get("merged", [])]) for k, v in out.items()}


def test_ligne_nommee_d_apres_le_produit_achete():
    """Le blanc pèse plus que les œufs entiers : la ligne reste « Œuf », pas « Blanc d'œuf »."""
    assert _fusion({"egg_raw": {"g": 73.3}, "egg_white_raw": {"g": 214.7}, "egg_yolk_raw": {"g": 48}}) == \
        {"egg_raw": ("Œuf", ["Blanc d'œuf", "Jaune d'œuf"])}
    # que des blancs et des jaunes : on achète des œufs
    assert _fusion({"egg_white_raw": {"g": 120}, "egg_yolk_raw": {"g": 40}}) == \
        {"egg_white_raw": ("Œufs", ["Blanc d'œuf", "Jaune d'œuf"])}
    # l'ingrédient au nom du produit l'emporte sur la plus grosse quantité
    assert _fusion({"onion_raw": {"g": 100}, "yellow_onion_raw": {"g": 600}}) == \
        {"onion_raw": ("Oignon", ["Oignon jaune"])}


def test_produits_differents_sur_des_lignes_differentes():
    """Tofu soyeux et tofu fumé n'étaient qu'une ligne « Tofu ferme » ; vinaigre balsamique
    et vinaigre blanc une ligne « Vinaigre » (même entrée du catalogue de prix)."""
    from backend.core.data_io import load_prices_catalog, resolve_catalog_key
    cat = load_prices_catalog()
    cles = {i: resolve_catalog_key(i, cat) for i in (
        "tofu_plain_pre_packaged", "silken_tofu_pre_packaged", "tofu_smoked_pre_packaged",
        "white_vinegar_liquid_distilled", "balsamic_vinegar_liquid", "butter_sup80pct", "vegan_butter",
        "yogurt_plain_3pct", "soybean_yogurt_plain_plant", "anise_spice_seed", "fennel_spice_seed",
        "cream_heavy", "vanilla_ice_cream", "oat_milk_refrigerated_plain_plant", "soybean_milk_unsweetened_plant")}
    assert len(set(cles.values())) == len(cles), cles
    # prix propre : estimé, puis relevé (surveyed_prices_2026_11_20.py) — jamais celui du beurre
    assert cat[cles["vegan_butter"]]["price_source"].startswith(("estimation", "relevé"))
    assert cat[cles["vegan_butter"]]["packages"] != cat[cles["butter_sup80pct"]]["packages"]
