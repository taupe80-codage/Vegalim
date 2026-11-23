"""
tests/test_fodmap_portions.py — Portions Monash des légumes et fruits courants.

Avant (2026-11-23) : courgette, poivron rouge, haricots verts, tomates et fraises
n'avaient pas de seuil — une soupe à 175 g de courgette par bol était « low ».
Poivron vert et concentré de tomate ajoutés le même jour.
"""
from __future__ import annotations

import pytest

from backend.engine.rule_engine.diet import compute_fodmap


def _recipe(iid: str, grams_per_portion: float) -> dict:
    return {"servings": 4, "composition": [
        {"ingredient": iid, "quantity": grams_per_portion * 4, "unit": "g", "meta": {}},
        {"ingredient": "potato_raw_flesh", "quantity": 400, "unit": "g", "meta": {}},
    ]}


@pytest.mark.parametrize("iid, safe, over", [
    ("green_zucchini_squash_raw", 65, 175),
    ("red_bell_pepper_raw", 40, 90),
    ("french_bean_raw", 75, 140),
    ("tomato_raw_ripe", 65, 180),
    ("cherry_tomato_raw", 75, 160),
    ("tomato_crushed_canned", 100, 220),
    ("strawberry_raw", 65, 160),
    ("green_bell_pepper_raw", 75, 160),
    ("tomato_paste_unsalted_canned", 28, 90),
])
def test_portion_sure_low_et_portion_excessive_non_low(iid, safe, over):
    assert compute_fodmap(_recipe(iid, safe))["fodmap_level"] == "low"
    assert compute_fodmap(_recipe(iid, over))["fodmap_level"] != "low"
