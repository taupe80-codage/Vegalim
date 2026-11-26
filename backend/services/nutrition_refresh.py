"""
nutrition_refresh.py — Recalcul ciblé de la nutrition précalculée (2026-11-26).

Quand la modération accepte (ou annule) la correction d'un ingrédient, la
fiche et le calcul à la volée la prennent en compte tout de suite, mais les
listes, filtres (« riche en fer »), scores et le bilan de la semaine lisent
des valeurs précalculées. Ce module les recalcule pour les seules recettes
concernées, au lieu d'attendre le rebuild complet du pipeline :

  1. sous-recettes (base_*) du registre qui contiennent l'ingrédient, de
     proche en proche (une sous-recette peut en contenir une autre) ;
  2. recettes du catalogue qui contiennent l'ingrédient ou ces sous-recettes :
     graphes nutrition et score (recipe_graphs.graph_entries, comme
     scripts/recipes/rebuild_graphs.py) ;
  3. mots-clés de recherche de ces recettes (« riche en protéines »…).

Écritures atomiques ; un verrou évite deux recalculs simultanés dans le même
processus.
"""
from __future__ import annotations

import json
import logging
import threading
import time

logger = logging.getLogger(__name__)

_lock = threading.Lock()

from backend.engine.config import DATA_ROOT  # noqa: E402

GRAPH_DIR = DATA_ROOT / "graphs"
RECIPES_PATH = DATA_ROOT / "recipes" / "recipes.json"


def _ids(recipe: dict) -> set[str]:
    return {str(c.get("ingredient")) for c in recipe.get("composition") or []
            if isinstance(c, dict) and c.get("ingredient")}


def affected(ingredient_ids: list[str] | set[str]) -> tuple[list[str], list[str]]:
    """(sous-recettes du registre, recettes du catalogue) concernées."""
    from backend.core.data_io import load_catalogue_recipes
    from backend.db.culinary_repositories import _derived_registry
    recipes = {str(r.get("id")): r for r in load_catalogue_recipes()}
    registry = _derived_registry()
    targets = set(ingredient_ids)
    bases: list[str] = []
    changed = True
    while changed:                       # une sous-recette peut en contenir une autre
        changed = False
        for key in registry:
            if key not in bases and key in recipes and _ids(recipes[key]) & targets:
                bases.append(key)
                targets.add(key)
                changed = True
    recs = [rid for rid, r in recipes.items() if _ids(r) & targets]
    return bases, recs


def _refresh_registry(bases: list[str]) -> int:
    from backend.core.data_io import load_catalogue_recipes
    from backend.db.culinary_repositories import _derived_registry
    from backend.engine import derived_registry
    from backend.engine.derived_registry import build_entry
    REGISTRY = derived_registry.REGISTRY
    if not bases:
        return 0
    recipes = {str(r.get("id")): r for r in load_catalogue_recipes()}
    raw = json.loads(REGISTRY.read_text(encoding="utf-8"))
    live = _derived_registry()           # dict en cache, mis à jour à chaque passe
    changed: set[str] = set()
    for _ in range(6):
        new = {k: build_entry(recipes[k]) for k in bases if k in recipes}
        delta = {k for k, v in new.items() if v != live.get(k)}
        live.update(new)
        changed |= {k for k, v in new.items() if v != raw["recipes"].get(k)}
        if not delta:
            break
    if changed:
        for k in changed:
            raw["recipes"][k] = live[k]
        tmp = REGISTRY.with_suffix(".tmp")
        tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        tmp.replace(REGISTRY)
    return len(changed)


def refresh_for_ingredients(ingredient_ids: list[str] | set[str], *, tokens: bool = True) -> dict:
    """Recalcule registre, graphes et mots-clés des recettes concernées."""
    from backend.core.data_cache import invalidate_now
    from backend.core.data_io import load_json, load_nutrition_graph, save_json
    from backend.engine.recipe_graphs import graph_entries

    t0 = time.monotonic()
    with _lock:
        bases, rec_ids = affected(ingredient_ids)
        n_bases = _refresh_registry(bases)
        invalidate_now()

        from backend.core.data_io import load_catalogue_recipes
        index = {str(r.get("id")): r for r in load_catalogue_recipes()}
        recs = [index[i] for i in rec_ids if i in index]
        nutrition, scoring = graph_entries(recs)
        n_path = GRAPH_DIR / "recipe_nutrition_graph_v1.json"
        s_path = GRAPH_DIR / "recipe_scoring_graph_v1.json"
        ng = load_json(n_path, default={}) or {}
        sg = load_json(s_path, default={}) or {}
        n_changed = sum(1 for k, v in nutrition.items() if ng.get(k) != v)
        if n_changed:
            ng.update(nutrition)
            sg.update(scoring)
            save_json(n_path, ng)
            save_json(s_path, sg)
            invalidate_now()
            load_nutrition_graph.cache_clear()

        n_tokens = 0
        if tokens and n_changed:
            from backend.engine.search_token_generator import generate_tokens
            path = RECIPES_PATH
            raw = load_json(path, default={}) or {}
            lst = raw.get("recipes", raw) if isinstance(raw, dict) else raw
            wanted = set(nutrition)
            for r in lst:
                if str(r.get("id")) in wanted:
                    new = generate_tokens(r)
                    if new != r.get("search_tokens"):
                        r["search_tokens"] = new
                        n_tokens += 1
            if n_tokens:
                save_json(path, raw)      # recipes.json seul : jamais les recettes de la communauté
                invalidate_now()
    stats = {"sub_recipes": len(bases), "registry_updated": n_bases, "recipes": len(recs),
             "nutrition_updated": n_changed, "tokens_updated": n_tokens,
             "seconds": round(time.monotonic() - t0, 1)}
    logger.info("nutrition_refresh %s : %s", sorted(ingredient_ids), stats)
    return stats
