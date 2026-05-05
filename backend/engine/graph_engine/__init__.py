"""
graph_engine/__init__.py — Sous-package graphe d'ingrédients.

Migré depuis engine/graph_engine.py (module plat) → engine/graph_engine/ (sous-package).

Compatibilité ascendante totale :
    from backend.engine.graph_engine import analyze_recipe      # ✅ inchangé
    from backend.engine.graph_engine import get_cycle_ingredients
    from backend.engine.graph_engine import _load_graph
    from backend.engine.graph_engine import compute_graph_score
    from backend.engine.graph_engine import get_substitutes
"""
from backend.engine.graph_engine.core import (
    _load_graph,
    compute_graph_score,
    analyze_recipe,
    get_substitutes,
    get_cycle_ingredients,
)

__all__ = [
    "_load_graph",
    "compute_graph_score",
    "analyze_recipe",
    "get_substitutes",
    "get_cycle_ingredients",
]
