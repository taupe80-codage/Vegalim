"""Filtres de recherche : chaque plat doit être atteignable, et chaque filtre
doit réellement filtrer (analyse d'équilibre du catalogue, 2026-11-19)."""
import re
from pathlib import Path

import pytest

from backend.core.data_io import is_component_recipe, load_recipes, matches_dish_types
from backend.services.filter_service import apply_filters, cuisine_matches

ROOT = Path(__file__).resolve().parent.parent
PLATS = [r for r in load_recipes() if not is_component_recipe(r)]


def _ids(**kw):
    return {r["id"] for r in apply_filters(PLATS, limit=5000, **kw)[0]}


# ── Saison ────────────────────────────────────────────────────────────────────

def test_chaque_saison_filtre_vraiment():
    # l'ancien filtre (marqueurs « tomato », « leek ») renvoyait les 894 plats partout
    counts = {s: len(_ids(season=s)) for s in ("spring", "summer", "autumn", "winter")}
    assert all(0 < n < len(PLATS) for n in counts.values()), counts
    assert len(set(counts.values())) > 1, counts


def test_gaspacho_en_ete_pas_en_hiver():
    assert "soup_gaspacho_provencal_f69228" in _ids(season="summer")
    assert "soup_gaspacho_provencal_f69228" not in _ids(season="winter")


def test_chou_rouge_en_hiver_pas_en_ete():
    assert "side_chou_rouge_pomme_noix_5d7c19" in _ids(season="winter")
    assert "side_chou_rouge_pomme_noix_5d7c19" not in _ids(season="summer")


def test_saison_en_francais():
    assert _ids(season="hiver") == _ids(season="winter")


# ── Cuisine ───────────────────────────────────────────────────────────────────

def _menu_cuisines() -> list[str]:
    jsx = (ROOT / "frontend/src/components/RecipeFiltersShared.jsx").read_text(encoding="utf-8")
    bloc = jsx.split("export const ORIGIN_GROUPS")[1].split("export const ALLERGEN_OPTIONS")[0]
    return re.findall(r"value: '([a-z_]+)'", bloc)


def _origin(r):
    o = r.get("origin") or {}
    return (o.get("cuisine") or "").lower(), (o.get("country") or "").lower()


def test_chaque_plat_est_atteignable_par_le_menu_des_origines():
    menu = _menu_cuisines()
    orphelins = sorted({_origin(r)[0] for r in PLATS
                        if not any(cuisine_matches(m, *_origin(r)) for m in menu)})
    assert not orphelins, f"cuisines sans entrée de menu : {orphelins}"


def test_aucune_entree_du_menu_des_origines_n_est_vide():
    vides = [m for m in _menu_cuisines()
             if not any(cuisine_matches(m, *_origin(r)) for r in PLATS)]
    assert not vides, f"entrées sans recette : {vides}"


@pytest.mark.parametrize("menu, cuisine, attendu", [
    ("french", "french_breton", True),        # région
    ("levantine", "lebanese", True),          # famille
    ("chinese", "sichuan", True),
    ("american", "latin_american", False),    # plus de sous-chaîne
    ("indian", "ocean_indien", False),
    ("african", "west_african", False),
])
def test_correspondance_des_cuisines(menu, cuisine, attendu):
    assert cuisine_matches(menu, cuisine) is attendu


def test_pays_d_origine_accepte():
    assert any(cuisine_matches("france", *_origin(r)) for r in PLATS)


# ── Type de plat ──────────────────────────────────────────────────────────────

def test_chaque_type_de_plat_est_filtrable():
    js = (ROOT / "frontend/src/constants.js").read_text(encoding="utf-8")
    options = set(re.findall(r"value: '([a-z_]+)'", js.split("export const DISH_OPTIONS")[1].split("];")[0]))
    sans_option = sorted({r.get("dish_type") for r in PLATS
                          if not matches_dish_types(r, options)})
    assert not sans_option, f"dish_type sans entrée de filtre : {sans_option}"


def test_viennoiserie_sous_pain():
    assert matches_dish_types({"dish_type": "pastry"}, {"bread"})


# ── Validation culinaire ──────────────────────────────────────────────────────

def _validate(rid):
    from backend.engine.rule_engine.validation import validate_recipe
    return {v["rule"] for v in validate_recipe(next(r for r in PLATS if r["id"] == rid))["violations"]}


def test_validation_lit_la_composition():
    # lisait l'ancien champ « ingredients » : « 0 ingrédient » sur les 1000 recettes
    assert "TOO_FEW_INGREDIENTS" not in _validate("dal_sambar_581de8")
    assert "NO_AROMATIC" not in _validate("dal_sambar_581de8")


def test_substitut_vegan_pas_signale_comme_non_vegan():
    # le beurre végétal a la clé de prix « butter » : ce n'est pas un critère de régime
    from backend.engine.rule_engine.validation import validate_recipe
    vegans = [r for r in PLATS if (r.get("diet_flags") or {}).get("vegan")
              and any(c.get("ingredient") == "vegan_butter" for c in r.get("composition", []))]
    assert vegans
    assert all("VEGAN_FLAG_INCONSISTENT" not in {v["rule"] for v in validate_recipe(r)["violations"]}
               for r in vegans)
