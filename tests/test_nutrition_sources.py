"""
tests/test_nutrition_sources.py — Lecture des tables sources et corrections tracées.

Constaté le 2026-11-23 (scripts/nutrition/audit_outliers.py) :
- CIQUAL note « < 20 » une valeur sous le seuil de détection : le pipeline lisait
  20, d'où 20 µg de sélénium pour le vinaigre et 235 fiches CIQUAL à 20 µg ;
- CIQUAL 2025 donne 0,00019 mg de fer pour l'oignon cru (environ 1 000 fois trop
  peu), corrigé par source_value_corrections.json avec sa preuve.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "nutrition"))
from build_n2_direct import ciqual_value  # noqa: E402

N2 = json.loads((ROOT / "backend/data/nutrition/processed/nutrition_v2.json").read_text(encoding="utf-8"))["ingredients"]
CORR = json.loads((ROOT / "backend/data/nutrition/reference/source_value_corrections.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("cell, field, expected", [
    ("< 20", "selenium_ug", 0.0),        # sous le seuil : borne basse
    ("<0,5", "vitamin_c_mg", 0.0),
    ("< 0,5", "fiber_g", 0.5),           # macros : le seuil reste (Atwater)
    ("traces", "sodium_mg", 0.0),
    ("traces", "protein_g", None),
    ("-", "iron_mg", None),
    ("nd", "iron_mg", None),
    ("1,85", "iron_mg", 1.85),
    (None, "iron_mg", None),
])
def test_lecture_des_cellules_ciqual(cell, field, expected):
    assert ciqual_value(cell, field) == expected


def test_plus_de_seuil_lu_comme_mesure():
    se20 = [b for b, v in N2.items() for var in v["variants"].values()
            if var.get("_source") == "CIQUAL" and var.get("selenium_ug") == 20]
    assert len(se20) < 20, se20          # 235 avant la correction
    assert N2["vinegar"]["variants"]["liquid"]["selenium_ug"] < 1


def test_corrections_appliquees_et_documentees():
    for c in CORR["corrections"]:
        assert c["reason"] and c["evidence"] and c["was"] != c["value"]
    assert N2["onion_raw"]["variants"]["raw"]["iron_mg"] == pytest.approx(0.21)


def test_audit_sans_alerte_de_masse():
    """Glucides CNF/USDA totaux (fibres comprises) : l'audit les ramène aux glucides disponibles."""
    import audit_outliers as A
    assert A.mass_alerts(N2) == []


def test_audit_sans_alerte_d_energie():
    """Fiches MANUAL d'herbe de blé (86 kcal), baobab et sumac remplacées par
    des valeurs d'étiquette, alcool du mirin et polyols du xylitol renseignés ;
    polyols CIQUAL (abricot sec) comptés à 2,4 kcal/g (2026-11-23)."""
    import audit_outliers as A
    assert A.energy_alerts(N2) == []
    assert N2["mirin"]["variants"]["default"]["alcohol_g"] == pytest.approx(9.4)
    assert N2["wheatgrass_powder"]["variants"]["default"]["calories_kcal"] == 261


def test_fiches_manuelles_corrigees_documentees():
    supp = json.loads((ROOT / "backend/data/nutrition/reference/nutrition_manual_supplements.json")
                      .read_text(encoding="utf-8"))["supplements"]
    for key in ("wheat_grass", "baobab", "sumac", "mirin", "xylitol"):
        assert supp[key].get("_source_note"), key


def test_audit_sans_ecart_a_la_fratrie():
    """48 écarts relus le 2026-11-24 : 7 erreurs de source corrigées
    (abricot au sirop, chou rouge étuvé, haricot mungo sec), oreille de Judas
    MANUAL reprise de CNF 4884, le reste en exceptions motivées."""
    import audit_outliers as A
    assert A.sibling_alerts(N2) == []
    assert all(reason for reason in A.SIBLING_EXCEPTIONS.values())
    assert N2["wood_ear_mushroom"]["variants"]["default"]["iron_mg"] == pytest.approx(5.88)
    assert N2["mung_bean_dried"]["variants"]["dried"]["vitamin_k1_ug"] == pytest.approx(9.0)
    assert N2["apricot_05865"]["variants"]["canned_in_syrup"]["vitamin_b1_mg"] < 0.05


def _diabetic_flags() -> dict:
    d = json.loads((ROOT / "backend/data/ingredients/ingredients_dictionary.json").read_text(encoding="utf-8"))
    return {k: (g.get("diet_profile") or {}).get("diabetic_friendly")
            for c in d["categories"].values() for s in c.get("subcategories", {}).values()
            for k, g in s.get("ingredient_groups", {}).items()}


@pytest.mark.parametrize("key, expected", [
    ("xylitol_birch_sugar", True),     # polyols, pas de sucre
    ("stevia_extract", True),
    ("egg_poached", True),             # ni sucre ni glucides
    ("comte_cow", True),
    ("avocado_oil_plant", True),
    ("wheat_flour_t55", False),        # amidon sans fibres (critère 10:1)
    ("white_sugar", False),
    ("kirsch", False),                 # alcool
    ("calvados_liquid", False),        # alcool non renseigné dans CIQUAL
])
def test_regle_adapte_au_diabete(key, expected):
    assert _diabetic_flags()[key] is expected
