"""
tests/test_search_tokens_nutrition.py — Mots-clés nutritionnels cohérents avec la nutrition.

Avant (2026-11-23) : le générateur divisait par le nombre de portions des valeurs
déjà par portion : 1 093 recettes « léger » (un curry à 748 kcal compris), 2 seulement
« riche en protéines ». Et les mots-clés étaient générés avant le graphe : un nouveau
lot ne les recevait qu'à la reconstruction suivante.
"""
from __future__ import annotations

from backend.core.data_io import load_catalogue_recipes, load_nutrition_graph


def test_mots_cles_conformes_a_la_nutrition_par_portion():
    ng = load_nutrition_graph()
    wrong = []
    for r in load_catalogue_recipes():
        n = ng.get(str(r["id"]))
        if not n:
            continue
        toks = set(r.get("search_tokens") or [])
        kcal, prot = n.get("calories") or 0, n.get("protein") or 0
        if ("leger" in toks) != (0 < kcal <= 300):
            wrong.append((r["id"], "leger", kcal))
        if ("riche en proteines" in toks) != (prot >= 15):
            wrong.append((r["id"], "riche en proteines", prot))
    assert not wrong, wrong[:10]


def test_mots_cles_generes_apres_le_graphe():
    src = open("scripts/recipes/rebuild_graphs.py", encoding="utf-8").read()
    assert src.index("batch_generate(recipes") > src.index("recipe_nutrition_graph_v1.json")
