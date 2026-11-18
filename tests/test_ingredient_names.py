"""Noms d'ingrédients affichés (fiche recette, avertissement de prix, frigo) :
pas de libellé de table nutritionnelle faux ou québécois."""
import pytest

from backend.core.data_io import load_ingredients_dict
from backend.services.ingredient_catalog import _DISPLAY_NAME_FR, full_name_fr, names_of


def test_surcharges_designent_des_entrees_du_dictionnaire():
    d = load_ingredients_dict()
    assert sorted(set(_DISPLAY_NAME_FR) - set(d)) == []


@pytest.mark.parametrize("iid,attendu", [
    ("drumstick_horseradish_tree_raw_pod", "pilon de moringa"),
    ("blueberry_raw", "myrtille"),
    ("tofu_smoked_pre_packaged", "tofu fumé"),
    ("apricot_pitted_dried", "abricot sec"),
    ("indian_bread_naan", "pain naan"),
])
def test_nom_affiche(iid, attendu):
    assert names_of([iid])[iid] == attendu


def test_entree_sans_surcharge_inchangee():
    d = load_ingredients_dict()
    assert full_name_fr(d["olive_oil_plant"], "olive_oil_plant") == "huile d'olive"
