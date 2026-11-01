"""
tests/test_audit_2026_11_01.py — Régressions relevées par l'audit de cohérence du 2026-11-01.
"""
from __future__ import annotations

import pytest

from backend.core.data_io import load_recipes
from backend.services.filter_service import apply_filters


# ── Filtre difficulté : « Difficile » renvoyait 0 recette ────────────────────

@pytest.mark.parametrize("value", ["hard", "difficile", "advanced"])
def test_filtre_difficile_trouve_les_recettes_hard(value):
    recipes = load_recipes()
    page, total = apply_filters(recipes, difficulty=value, limit=len(recipes))
    expected = sum(1 for r in recipes if r.get("difficulty_level") == "hard")
    assert expected > 0
    assert total == expected
    assert all(r["difficulty_level"] == "hard" for r in page)


# ── Filtre technique : lisait r["technique"], absent des données ──────────────

def test_filtre_technique_lit_tags_technique():
    recipes = load_recipes()
    page, total = apply_filters(recipes, technique="Blending", limit=len(recipes))
    expected = sum(1 for r in recipes if "blending" in r["tags"].get("technique", []))
    assert expected > 0
    assert total == expected
