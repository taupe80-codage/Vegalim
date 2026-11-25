"""
tests/test_sur_place.py — « Sur place » (POST /frigo/rapide).

On donne l'aliment qu'on a ; les recettes où il est la vedette viennent en
premier (nommé dans le titre, puis part du plat), sans toucher au frigo
enregistré ; options sans four, sans mixeur, temps.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def _post(**body):
    r = client.post("/frigo/rapide", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_courgette_vedette_d_abord():
    res = _post(ingredients=["courgette"])
    assert res["total"] > 10 and not res["unrecognized"]
    top = res["results"][:5]
    assert all("courgette" in r["title_fr"].lower() for r in top)
    shares = [r["matched"][0]["share_pct"] for r in res["results"]]
    assert all(s >= 15 or r["matched"][0]["in_title"] for s, r in zip(shares, res["results"]))
    # parmi les recettes nommées dans le titre, la part décroît
    titled = [r["matched"][0]["share_pct"] for r in res["results"] if r["matched"][0]["in_title"]]
    assert titled == sorted(titled, reverse=True)


def test_plusieurs_aliments_ceux_qui_utilisent_tout_d_abord():
    res = _post(ingredients=["feta", "tomates"])
    n = [len(r["matched"]) for r in res["results"]]
    assert n == sorted(n, reverse=True)


def test_options_four_mixeur_temps():
    base = _post(ingredients=["pois chiches"], limit=100)["results"]
    no_oven = _post(ingredients=["pois chiches"], no_oven=True, no_blender=True, max_time=30, limit=100)["results"]
    assert len(no_oven) < len(base)
    assert all(not r["needs_oven"] and not r["needs_blender"] for r in no_oven)
    assert all((r["total_time_min"] or 0) <= 30 for r in no_oven)


def test_saisie_inconnue_signalee():
    res = _post(ingredients=["blabla", "poireaux"])
    assert res["unrecognized"] == ["blabla"] and "poireaux" in res["understood"]
    assert res["total"] > 0


def test_frigo_enregistre_intact():
    """La route ne lit ni n'écrit aucun frigo d'utilisateur : réponse identique sans compte."""
    a = _post(ingredients=["courgette"], limit=5)
    b = _post(ingredients=["courgette"], limit=5)
    assert [r["id"] for r in a["results"]] == [r["id"] for r in b["results"]]
