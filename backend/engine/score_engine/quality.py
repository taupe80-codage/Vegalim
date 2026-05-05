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
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

from backend.core.data_io import (
    load_score_graph, load_prices, load_availability_graph,
    load_carbon_footprint, load_flavor_graph,
    load_global_cuisine_graph, load_ingredients_dict,
    load_nutrition_graph,
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

@lru_cache(maxsize=1)
def _load_data() -> dict:
    """
    Charge les 8 sources de données nécessaires au scoring.

    @lru_cache(maxsize=1) : les loaders sous-jacents sont eux-mêmes mis en
    cache (lru_cache ou _MtimeCache dans data_io). Ce cache évite de
    reconstruire le dict à chaque appel score_recipe() — soit 300+ fois
    lors d'un pipeline batch.

    Invalider avec _load_data.cache_clear() si nécessaire (admin, tests).
    """
    return {
        "score_g": load_score_graph(),
        "prices":  load_prices(),
        "avail":   load_availability_graph(),
        "carbon":  load_carbon_footprint(),
        "flavor":  load_flavor_graph(),
        "cuisine": load_global_cuisine_graph(),
        "ings":    load_ingredients_dict(),
        "nutr_g":  load_nutrition_graph(),   # consolidé ici — évite un 2e appel dans score_recipe
    }

def _d_nutrition(r, d):
    sg = d["score_g"].get(str(r.get("id", "")), {})
    return round(max(0.0, min(10.0, float(sg.get("nutrition_score", sg.get("overall_score", sg.get("score", 5.0)))))), 2)

def _d_authenticity(r, d):
    iconic   = float(r.get("scoring", {}).get("iconic", {}).get("score", 50) or 50) / 100.0
    cid      = (r.get("iconic_status") or {}).get("cuisine_origin", "")
    prestige = float(d["cuisine"].get(cid, {}).get("prestige_score", 5.0)) / 10.0
    return round(min(10.0, (iconic * 0.6 + prestige * 0.4) * 10.0), 2)

def _get_ings(r):
    ings = r.get("ingredients", [])
    if not ings and r.get("composition"):
        ings = [c["ingredient"] for c in r.get("composition", [])]
    return ings

def _d_accessibility(r, d):
    ings = _get_ings(r)
    if not ings: return 7.0
    m = {"True": 10.0, True: 10.0, "partial": 6.0, "False": 2.0, False: 2.0}
    scores = [m.get(d["avail"].get(i, {}).get("available_in_france"), 7.0) for i in ings]
    return round(sum(scores) / len(scores), 2)

def _d_cost(r, d):
    ings = _get_ings(r)
    total    = sum(float(d["prices"].get(i, 0.25)) for i in ings)
    servings = max(1, int(r.get("servings", 4) or 4))
    return round(max(0.0, min(10.0, 10.0 - (total / servings) * 1.2)), 2)

def _d_ease(r, d):
    diff = r.get("difficulty") or 0
    if diff == 1: return 9.0
    if diff == 3: return 3.0
    if diff == 2: return 6.0
    n_t = len(r.get("technique", []) or [])
    n_i = len(_get_ings(r))
    if n_t <= 1 and n_i <= 6:  return 9.0
    if n_t >= 4 or n_i >= 10: return 3.0
    return 6.0

def _d_carbon(r, d):
    ings = _get_ings(r)
    if not ings: return 7.0
    def _co2(v): return float(v) if isinstance(v, (int, float)) else float(v.get("co2_per_100g", 0.3)) if isinstance(v, dict) else 0.3
    avg = sum(_co2(d["carbon"].get(i, 0.3)) for i in ings) / len(ings)
    return round(max(1.0, min(10.0, 10.0 - avg * 6.0)), 2)

def _d_flavor(r, d):
    ings = _get_ings(r)
    if not ings: return 5.0
    profiles = [str(d["ings"].get(i, {}).get("flavor_profile", "")) for i in ings]
    profiles = [p for p in profiles if p]
    
    base_score = 5.0 + (len(set(profiles)) / max(1, len(profiles))) * 3.0
    
    pairs = 0
    flavor_g = d["flavor"]
    for i in ings:
        match_list = flavor_g.get(i, [])
        for j in ings:
            if i != j and j in match_list:
                pairs += 1
                
    pairing_bonus = min(2.0, pairs * 0.5)
    return round(min(10.0, base_score + pairing_bonus), 2)


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
