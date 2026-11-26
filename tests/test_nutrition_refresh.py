"""
tests/test_nutrition_refresh.py — Recalcul ciblé après la correction d'un ingrédient.

Travaille sur des copies des fichiers de données (graphes, registre des
sous-recettes, recipes.json) : les vrais fichiers ne sont jamais réécrits.
"""
from __future__ import annotations

import json
import shutil

import pytest

from backend.core.data_io import load_catalogue_recipes
from backend.db.culinary_repositories import _derived_registry
from backend.engine import derived_registry
from backend.engine.config import DATA_ROOT
from backend.services import ingredient_sheet as S
from backend.services import nutrition_refresh as R

CURRY = "curry_aubergine_sri_lanka_bf8bcd"


@pytest.fixture
def copies(tmp_path, monkeypatch):
    graphs = tmp_path / "graphs"
    graphs.mkdir()
    for name in ("recipe_nutrition_graph_v1.json", "recipe_scoring_graph_v1.json"):
        shutil.copy(DATA_ROOT / "graphs" / name, graphs / name)
    shutil.copy(DATA_ROOT / "recipes" / "recipes.json", tmp_path / "recipes.json")
    shutil.copy(derived_registry.REGISTRY, tmp_path / "registry.json")
    monkeypatch.setattr(R, "GRAPH_DIR", graphs)
    monkeypatch.setattr(R, "RECIPES_PATH", tmp_path / "recipes.json")
    monkeypatch.setattr(derived_registry, "REGISTRY", tmp_path / "registry.json")
    monkeypatch.setattr(S, "CORRECTIONS_PATH", tmp_path / "corrections.json")
    S._corr_cache.update(sig=None, data={})
    yield tmp_path
    S._corr_cache.update(sig=None, data={})
    _derived_registry.cache_clear()          # le registre en cache a été modifié en place
    from backend.core.data_io import load_nutrition_graph
    load_nutrition_graph.cache_clear()


def _correct(iid: str, field: str, value: float) -> None:
    n = S.raw_nutrition(iid)
    S.write_corrections([{"id": "t", "ingredient_id": iid, "field": field, "source_id": str(n["_source_id"]),
                          "proposed_value": value, "current_value": n[field], "source_ref": "test",
                          "source_url": None, "reviewed_at": "2026-11-26"}])


def _graph(tmp, name="recipe_nutrition_graph_v1.json"):
    return json.loads((tmp / "graphs" / name).read_text(encoding="utf-8"))


def test_sans_correction_rien_ne_change(copies):
    stats = R.refresh_for_ingredients(["eggplant_raw"])
    assert stats["recipes"] >= 30 and stats["nutrition_updated"] == 0 and stats["tokens_updated"] == 0


def test_correction_recalcule_les_recettes_concernees(copies):
    before = _graph(copies)
    _correct("eggplant_raw", "protein_g", 5.0)
    stats = R.refresh_for_ingredients(["eggplant_raw"])
    after = _graph(copies)
    assert stats["nutrition_updated"] >= 30
    assert after[CURRY]["protein"] == pytest.approx(before[CURRY]["protein"] + (5.0 - 0.98) * 5 / 4, abs=0.2)
    # une recette sans aubergine ne bouge pas
    other = next(r["id"] for r in load_catalogue_recipes()
                 if "eggplant_raw" not in {c.get("ingredient") for c in r.get("composition") or []})
    assert after[other] == before[other]
    # score et mots-clés suivent la nouvelle nutrition
    assert _graph(copies, "recipe_scoring_graph_v1.json")[CURRY]["protein"] == after[CURRY]["protein"]


def test_les_sous_recettes_suivent(copies):
    bases, recs = R.affected(["milk_liquid_uht_3_5pct"])
    assert "base_bechamel_7db18f" in bases
    reg0 = json.loads(derived_registry.REGISTRY.read_text(encoding="utf-8"))["recipes"]
    _correct("milk_liquid_uht_3_5pct", "calcium_mg", 300.0)
    stats = R.refresh_for_ingredients(["milk_liquid_uht_3_5pct"], tokens=False)
    reg1 = json.loads(derived_registry.REGISTRY.read_text(encoding="utf-8"))["recipes"]
    assert stats["registry_updated"] >= 1
    assert reg1["base_bechamel_7db18f"]["nutrition_per_100g"]["calcium"] > \
        reg0["base_bechamel_7db18f"]["nutrition_per_100g"]["calcium"]
    # une recette qui n'utilise la béchamel que comme sous-recette est recalculée aussi
    users = [r["id"] for r in load_catalogue_recipes()
             if "base_bechamel_7db18f" in {c.get("ingredient") for c in r.get("composition") or []}
             and "milk_liquid_uht_3_5pct" not in {c.get("ingredient") for c in r.get("composition") or []}]
    assert users and set(users) <= set(recs)
