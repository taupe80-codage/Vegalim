"""
tests/test_composites.py — Ingrédients composites calculés depuis leurs composants.

Avant (2026-11-23) : garam masala, fruits rouges mélangés… n'avaient que 4-5
macros saisies à la main, et des zéros fictifs (0 g d'eau, 0 mg de vitamine C
pour des fruits rouges). Leur nutrition vient désormais de
composite_ingredients.json, appliqué par build_n2_direct.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "nutrition"))
import composites as C  # noqa: E402

N2 = json.loads((ROOT / "backend/data/nutrition/processed/nutrition_v2.json").read_text(encoding="utf-8"))["ingredients"]
SPECS = C.load_composites()


def test_les_composants_existent():
    missing = [f"{k}: {c['ingredient']}/{c['variant']}" for k, s in SPECS.items() for c in s["components"]
               if c["variant"] not in N2.get(c["ingredient"], {}).get("variants", {})]
    assert not missing


@pytest.mark.parametrize("key", sorted(SPECS))
def test_nutrition_v2_synchro_avec_les_formules(key):
    """Formule modifiée sans rebuild → lancer build_n2_direct.py --promote puis build_indexes.py."""
    variant = N2[key]["variants"]["default"]
    assert variant["_source"] == "COMPOSITE"
    expected, _ = C.compute(SPECS[key], N2)
    got = {k: v for k, v in variant.items() if k in expected}
    assert got == pytest.approx(expected, rel=1e-6)


def test_plus_de_zeros_fictifs():
    berries = N2["mixed_berries"]["variants"]["default"]
    assert berries["water_g"] > 80 and berries["vitamin_c_mg"] > 20
    garam = N2["garam_masala"]["variants"]["default"]
    assert garam["iron_mg"] > 10 and garam["calcium_mg"] > 300
    # le chili CNF (mélange américain salé) ne doit pas revenir dans le berbéré
    assert N2["berbere"]["variants"]["default"]["sodium_mg"] < 200


def test_extrapolation_bornee():
    """Un nutriment connu pour moins de la moitié du lot reste inconnu."""
    ings = {
        "a": {"variants": {"x": {"_source": "CIQUAL", "calories_kcal": 100.0, "iron_mg": 10.0}}},
        "b": {"variants": {"x": {"_source": "MANUAL", "calories_kcal": 300.0}}},
    }
    out, trace = C.compute({"components": [{"ingredient": "a", "variant": "x", "g": 40},
                                           {"ingredient": "b", "variant": "x", "g": 60}]}, ings)
    assert out["calories_kcal"] == pytest.approx(220.0)
    assert "iron_mg" not in out and trace["_official_share"] == 0.4
    out, trace = C.compute({"components": [{"ingredient": "a", "variant": "x", "g": 60},
                                           {"ingredient": "b", "variant": "x", "g": 40}]}, ings)
    assert out["iron_mg"] == pytest.approx(10.0) and "iron_mg" in trace["_estimated_fields"]


def test_evaporation():
    ings = {"f": {"variants": {"x": {"_source": "CIQUAL", "calories_kcal": 50.0, "water_g": 90.0}}}}
    out, _ = C.compute({"yield_g": 50, "components": [{"ingredient": "f", "variant": "x", "g": 100}]}, ings)
    assert out["calories_kcal"] == pytest.approx(100.0)        # concentré deux fois
    assert out["water_g"] == pytest.approx(80.0)               # (90 - 50) / 50 × 100


def test_fiches_manuelles_hors_arbre_gardent_leur_taxonomie():
    """Un rebuild laissait une taxonomie vide à tteok et à la papaye verte."""
    for key in ("tteok", "green_papaya"):
        assert N2[key]["taxonomy"].get("name_fr"), key
