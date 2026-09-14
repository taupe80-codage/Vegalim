"""
quality.py — Score qualité 7 dimensions CDC_03c + profils adaptatifs.

Fusionne : global_score_engine + adaptive_score_engine_v4

API :
    score_recipe(recipe, profile, context) → dict
    score_batch(recipes, profile, context) → list[dict]
    PROFILES                               → dict profils disponibles
"""
from __future__ import annotations
import logging
from backend.core.data_cache import data_cached
from typing import Any

logger = logging.getLogger(__name__)

from backend.core.data_io import (
    load_score_graph, load_prices_catalog, load_availability_graph,
    load_flavor_graph, load_ingredients_dict, load_nutrition_graph,
    load_recipes, resolve_catalog_key,
)

# ── Profils ──────────────────────────────────────────────────────────────────

PROFILES: dict[str, dict[str, Any]] = {
    "default":      {"weights": {"nutrition": 0.40, "authenticity": 0.20, "accessibility": 0.15, "cost": 0.15, "ease": 0.05, "carbon": 0.03, "flavor": 0.02}, "bonus_rules": [], "description": "Équilibre CDC_03c standard"},
    "health_focus": {"weights": {"nutrition": 0.55, "authenticity": 0.15, "accessibility": 0.10, "cost": 0.10, "ease": 0.05, "carbon": 0.03, "flavor": 0.02}, "bonus_rules": [{"field": "protein", "op": ">=", "value": 15, "bonus": 0.5, "label": "riche en protéines"}, {"field": "fiber", "op": ">=", "value": 8, "bonus": 0.4, "label": "riche en fibres"}], "description": "Priorité santé / nutrition"},
    "budget":       {"weights": {"nutrition": 0.30, "authenticity": 0.15, "accessibility": 0.20, "cost": 0.28, "ease": 0.04, "carbon": 0.02, "flavor": 0.01}, "bonus_rules": [], "description": "Priorité coût / accessibilité"},
    "eco":          {"weights": {"nutrition": 0.35, "authenticity": 0.15, "accessibility": 0.15, "cost": 0.10, "ease": 0.05, "carbon": 0.18, "flavor": 0.02}, "bonus_rules": [], "description": "Priorité empreinte carbone"},
    "quick":        {"weights": {"nutrition": 0.30, "authenticity": 0.15, "accessibility": 0.20, "cost": 0.15, "ease": 0.18, "carbon": 0.01, "flavor": 0.01}, "bonus_rules": [], "description": "Priorité facilité / rapidité"},
    "diabetic":     {"weights": {"nutrition": 0.55, "authenticity": 0.10, "accessibility": 0.15, "cost": 0.10, "ease": 0.05, "carbon": 0.03, "flavor": 0.02}, "bonus_rules": [{"field": "glycemic_index", "op": "<=", "value": 55, "bonus": 1.0, "label": "IG bas"}, {"field": "fiber", "op": ">=", "value": 6, "bonus": 0.3, "label": "fibres (contrôle glycémique)"}], "description": "Adapté diabète / IG bas"},
    "anemia":       {"weights": {"nutrition": 0.55, "authenticity": 0.15, "accessibility": 0.15, "cost": 0.10, "ease": 0.03, "carbon": 0.01, "flavor": 0.01}, "bonus_rules": [{"field": "iron", "op": ">=", "value": 3, "bonus": 1.0, "label": "riche en fer"}, {"field": "vitamin_c", "op": ">=", "value": 20, "bonus": 0.3, "label": "vitamine C"}, {"field": "vitamin_b12", "op": ">=", "value": 1, "bonus": 0.5, "label": "vitamine B12"}], "description": "Adapté anémie / carence fer"},
    "athlete":      {"weights": {"nutrition": 0.50, "authenticity": 0.15, "accessibility": 0.15, "cost": 0.10, "ease": 0.05, "carbon": 0.03, "flavor": 0.02}, "bonus_rules": [{"field": "protein", "op": ">=", "value": 20, "bonus": 1.0, "label": "haute protéine"}, {"field": "calories", "op": ">=", "value": 400, "bonus": 0.3, "label": "dense en calories"}], "description": "Adapté sport / haute protéine"},
}

for _n, _c in PROFILES.items():
    _s = sum(_c["weights"].values())
    assert abs(_s - 1.0) < 1e-9, f"Profil '{_n}': poids={_s:.4f} ≠ 1.0"


# ── Dimensions ────────────────────────────────────────────────────────────────
#
# Revu le 2026-09-14 : 4 dimensions sur 7 étaient mortes ou quasi constantes
# (flavor = 5.0 pour 820/820, prestige cuisine = 5 faute de fichier, ease sur
# des champs absents, cost/carbon via des référentiels couvrant 5 % des ids).
# Chaque dimension lit désormais un champ réel des recettes ou un référentiel
# générique résolu par resolve_catalog_key.

@data_cached
def _load_data() -> dict:
    """
    Charge les sources de données nécessaires au scoring.

    @lru_cache(maxsize=1) : les loaders sous-jacents sont eux-mêmes mis en
    cache (lru_cache ou _MtimeCache dans data_io). Ce cache évite de
    reconstruire le dict à chaque appel score_recipe() — soit 300+ fois
    lors d'un pipeline batch.

    Invalider avec _load_data.cache_clear() si nécessaire (admin, tests).
    """
    return {
        "score_g": load_score_graph(),
        "catalog": load_prices_catalog(),
        "avail":   load_availability_graph(),
        "flavor":  load_flavor_graph(),
        "ings":    load_ingredients_dict(),
        "nutr_g":  load_nutrition_graph(),   # consolidé ici — évite un 2e appel dans score_recipe
        "recipes": {str(r.get("id")): r for r in load_recipes()},
    }

def _d_nutrition(r, d):
    sg = d["score_g"].get(str(r.get("id", "")), {})
    return round(max(0.0, min(10.0, float(sg.get("nutrition_score", sg.get("overall_score", sg.get("score", 5.0)))))), 2)

def _d_authenticity(r, d):
    # scoring.iconic.score est sur 10 (6, 5.2…) — l'ancienne division par 100
    # l'écrasait à ~0.05. Pas de référentiel de prestige par cuisine
    # (global_cuisine_graph_v1.json n'a jamais existé) : neutre 5 si absent.
    iconic = (r.get("scoring") or {}).get("iconic") or {}
    score = iconic.get("score") if isinstance(iconic, dict) else None
    if not isinstance(score, (int, float)):
        return 5.0
    return round(max(0.0, min(10.0, float(score))), 2)

def _get_ings(r):
    ings = r.get("ingredients", [])
    if not ings and r.get("composition"):
        ings = [c["ingredient"] for c in r.get("composition", [])
                if (c.get("meta") or {}).get("role") != "serving_suggestion"]
    return ings

def _d_accessibility(r, d):
    ings = _get_ings(r)
    if not ings: return 7.0
    m = {"True": 10.0, True: 10.0, "partial": 6.0, "False": 2.0, False: 2.0}
    scores = []
    for i in ings:
        v = d["avail"].get(i, {}).get("available_in_france")
        if v in m:
            scores.append(m[v])
        elif i.startswith("base_"):
            scores.append(8.0)       # préparation maison
        else:
            # Disponibilité non documentée (~96 % du graphe) : présent au
            # catalogue de prix grande surface → courant ; sinon incertain.
            scores.append(8.0 if resolve_catalog_key(i, d["catalog"]) else 5.0)
    return round(sum(scores) / len(scores), 2)

def _d_cost(r, d):
    # Coût réellement consommé (prices_catalog), pas un forfait par ingrédient.
    # Médiane du dataset ≈ 1,3 €/portion → ~6,7 ; 4 €/portion → 0.
    from backend.engine.planning_engine.shopping import recipe_cost
    cost = recipe_cost(r, d["catalog"], d["recipes"])
    if cost["n_priced"] == 0:
        return 5.0
    return round(max(0.0, min(10.0, 10.0 - cost["per_portion_eur"] * 2.5)), 2)

_DIFFICULTY_EASE = {"easy": 9.0, "medium": 6.0, "hard": 3.0}

def _d_ease(r, d):
    ease = _DIFFICULTY_EASE.get(str(r.get("difficulty_level") or "").lower())
    if ease is None:
        n_t = len((r.get("tags") or {}).get("technique") or [])
        n_i = len(_get_ings(r))
        ease = 9.0 if (n_t <= 1 and n_i <= 6) else 3.0 if (n_t >= 4 or n_i >= 10) else 6.0
    # temps actif (hors repos/marinade) : pénalité au-delà d'1 h 30
    timing = r.get("timing") or {}
    active = (timing.get("prep_active_min") or 0) + (timing.get("cook_min") or 0)
    if active > 90:
        ease -= 1.0
    return round(max(0.0, min(10.0, ease)), 2)

def _d_carbon(r, d):
    from backend.engine.rule_engine.carbon import carbon_score
    res = carbon_score(r)
    return 7.0 if res["coverage"] == 0 else res["score"]

_BASIC_TASTES = {"sweet", "sour", "salty", "bitter", "umami", "spicy"}

def _d_flavor(r, d):
    # flavor_graph.json : profils gustatifs par ingrédient générique. Score =
    # couverture des saveurs de base (équilibre) + diversité aromatique.
    tastes: set[str] = set()
    n_mapped = 0
    for i in _get_ings(r):
        key = resolve_catalog_key(i, d["flavor"])
        if key:
            n_mapped += 1
            tastes.update(d["flavor"][key])
    if n_mapped == 0:
        return 5.0
    basic = len(tastes & _BASIC_TASTES)
    aromatic = len(tastes - _BASIC_TASTES - {"neutral"})
    return round(min(10.0, 3.0 + basic * 1.0 + min(aromatic, 4) * 0.25), 2)


# ── Bonus rules ───────────────────────────────────────────────────────────────

def _check_rule(rule, nutr):
    v, op, rv = float(nutr.get(rule["field"], 0) or 0), rule["op"], rule["value"]
    return (op==">=" and v>=rv) or (op==">" and v>rv) or (op=="<=" and v<=rv) or (op=="<" and v<rv) or (op=="==" and v==rv)

def _apply_bonuses(rules, nutr):
    total, applied = 0.0, []
    for r in rules:
        if _check_rule(r, nutr):
            val = float(r.get("bonus", r.get("malus", 0.0)))
            total += val
            applied.append({"label": r["label"], "value": val})
    return total, applied

def _dynamic_weights(base, ctx):
    if not ctx: return base
    w = dict(base)
    if ctx.get("strict_budget"):
        w["cost"] = min(0.40, w["cost"] + 0.15); w["authenticity"] = max(0.05, w["authenticity"] - 0.10); w["flavor"] = max(0.01, w["flavor"] - 0.05)
    if ctx.get("high_protein"):
        w["nutrition"] = min(0.70, w["nutrition"] + 0.10); w["cost"] = max(0.05, w["cost"] - 0.05); w["flavor"] = max(0.01, w["flavor"] - 0.05)
    total = sum(w.values())
    return {k: round(v / total, 4) for k, v in w.items()}


# ── API publique ──────────────────────────────────────────────────────────────

def score_recipe(recipe: dict, profile: str = "default", context: dict | None = None) -> dict:
    """
    Score complet d'une recette sur 7 dimensions CDC_03c.

    Retourne deux scores distincts :
      global_score   -- score de reference neutre, toujours calcule avec les poids
                        "default" (independant du profil actif). Permet la comparaison
                        inter-profils et le classement absolu. Expose comme quality_score
                        dans les routes API.
      adaptive_score -- score ajuste au profil + contexte (strict_budget, high_protein...).
                        C'est ce score qui est affiche et utilise pour le ranking.
    """
    ctx = context or {}
    d   = _load_data()
    pcfg    = PROFILES.get(profile, PROFILES["default"])
    weights = _dynamic_weights(pcfg["weights"], ctx)

    dims = {
        "nutrition":     _d_nutrition(recipe, d),
        "authenticity":  _d_authenticity(recipe, d),
        "accessibility": _d_accessibility(recipe, d),
        "cost":          _d_cost(recipe, d),
        "ease":          _d_ease(recipe, d),
        "carbon":        _d_carbon(recipe, d),
        "flavor":        _d_flavor(recipe, d),
    }
    # global_s = score de reference neutre (poids "default", sans ajustement contextuel).
    # Intentionnellement fixe : permet de comparer des recettes entre profils differents.
    # NE PAS remplacer par `weights` -- ce serait un score adaptatif duplique, pas une reference.
    global_s = round(sum(dims[k] * PROFILES["default"]["weights"][k] for k in dims), 2)
    base     = sum(dims[k] * weights[k] for k in dims)

    nutr = d["nutr_g"].get(str(recipe.get("id", "")), {}) or {}
    bonus_total, bonuses = _apply_bonuses(pcfg.get("bonus_rules", []), nutr)
    adaptive = round(max(0.0, min(10.0, base + bonus_total)), 2)

    try:
        from backend.engine.score_engine.reliability import reliability as _rel
        rel_status = _rel(recipe)["status"]
    except Exception:
        logger.debug("score_recipe : erreur ignorée (repli)", exc_info=False)
        rel_status = "unknown"

    return {
        "global_score":   global_s,
        "adaptive_score": adaptive,
        "final_score":    adaptive,
        "score":          adaptive,   # compat adaptive_score_engine_v4
        "profile":        profile,
        "dims":           dims,
        "weights":        weights,
        "bonuses":        bonuses,
        "reliability":    rel_status,
        "details":        {**dims, "bonuses": bonuses},
    }


def score_batch(recipes: list[dict], profile: str = "default", context: dict | None = None) -> list[dict]:
    """Score et trie une liste de recettes par final_score décroissant."""
    scored = []
    for recipe in recipes:
        try:
            res = score_recipe(recipe, profile=profile, context=context)
            r = dict(recipe)
            r["_score_detail"]  = res
            r["final_score"]    = res["final_score"]
            r["adaptive_score"] = res["adaptive_score"]
            scored.append(r)
        except Exception as e:
            logger.warning("score_batch erreur id=%s : %s", recipe.get("id"), e)
            scored.append(dict(recipe))
    scored.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return scored
