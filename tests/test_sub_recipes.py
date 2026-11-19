"""Sous-recettes (base_*) dans les calculs : le dictionnaire d'ingrédients ne
les connaît pas, chaque calcul qui le lit ligne à ligne doit les déplier
(audit du 2026-11-19 : coût, badges « sans X », cycle, astro, ménopause,
liste de courses, frigo)."""
import pytest

from backend.core.data_io import (
    expand_sub_recipes, load_recipes, sub_recipe_core_name, sub_recipe_label,
)

IDX = {r["id"]: r for r in load_recipes()}
HALLOUMI = "protein_halloumi_pois_chiches_rotis_7c40e2"   # 250 g de base_halloumi


def _line(rid, iid):
    return next(c for c in IDX[rid]["composition"] if c["ingredient"] == iid)


def test_depliage_au_poids_brut_et_au_poids_servi():
    line = _line(HALLOUMI, "base_halloumi_293d5e")
    brut = expand_sub_recipes([line])
    servi = expand_sub_recipes([line], as_eaten=True)
    assert {c["ingredient"] for c in brut} >= {"milk_liquid_uht_3_5pct", "lemon_juice"}
    assert all(c["_from_sub_recipe"] == "base_halloumi_293d5e" for c in brut)
    # 2 L de lait pour 250 g de halloumi (rendement) ; au poids servi : 250 g
    assert sum(c["quantity"] for c in brut) > 1500
    assert sum(c["quantity"] for c in servi) == pytest.approx(line["quantity"], rel=0.02)


def test_suggestion_de_service_reste_suggestion():
    line = {"ingredient": "base_soy_cream_4dc027", "quantity": 15, "unit": "g",
            "meta": {"role": "serving_suggestion"}}
    assert all(c["meta"]["role"] == "serving_suggestion" for c in expand_sub_recipes([line]))


def test_libelles():
    assert sub_recipe_label("base_halloumi_293d5e") == "Halloumi"
    assert "base" not in sub_recipe_label("base_kimchi_61791a").lower()
    assert sub_recipe_label("tofu") is None
    assert sub_recipe_core_name("base_vegetarian_fish_sauce_536a33") == "vegetarian_fish_sauce"


def test_cycle_voit_le_gingembre_d_une_sous_recette():
    # le gingembre du teriyaki maison n'était pas compté
    from backend.engine.cycle_engine import cycle_score
    assert "ginger" in cycle_score(IDX["protein_tofu_teriyaki_ffcb47"], "menstrual_phase")["recommended"]


def test_astro_compte_les_sous_recettes():
    from backend.engine.rule_engine.astro import astro_shares
    seul = {"composition": [{"ingredient": "base_paneer_04e1db", "quantity": 200, "unit": "g"}]}
    elements, _ = astro_shares(seul)
    assert elements and sum(elements.values()) == pytest.approx(1.0)


def test_liste_de_courses_nomme_et_chiffre_la_sous_recette():
    from backend.engine.planning_engine.shopping import recipe_cost, shopping_list_from_recipes
    items = shopping_list_from_recipes([HALLOUMI])["items"]
    h = next(i for i in items if i["ingredient"] == "base_halloumi_293d5e")
    assert h["name_fr"] == "Halloumi"
    # même prix au gramme que le coût de la fiche (rendement compris) : ~2,9 € les 250 g
    cost = next(d["cost_eur"] for d in recipe_cost(IDX[HALLOUMI])["details"]
                if d["ingredient"] == "base_halloumi_293d5e")
    assert h["price_eur"] == pytest.approx(cost, rel=0.05)


def test_categorie_preparations_maison():
    from backend.core.data_io import load_ingredients_dict
    from backend.engine.planning_engine.shopping import _make_resolvers
    _, cat = _make_resolvers(load_ingredients_dict())
    assert cat("base_kimchi_61791a") == "Préparations maison"
