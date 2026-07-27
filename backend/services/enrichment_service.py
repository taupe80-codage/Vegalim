"""
enrichment_service.py — Enrichissement des recettes avec données dérivées.

Extrait de recipes.py pour respecter le principe de responsabilité unique.

Expose deux interfaces :
  enrich_one(recipe)           → dict   # données calculées pour une fiche recette
  enrich_why(recipes, filters) → list   # résumé nutritionnel pour une liste

Architecture :
  enrich_one()  → calcul complet  : nutrition, scores, saisonnalité, CO₂, prix, validation
  enrich_why()  → calcul léger    : résumé AJR + tag contextuel (_why)
  enrich_batch()→ enrich_why en batch : version optimisée liste (charge les graphes 1× seul)
"""
from __future__ import annotations

import datetime
import logging

logger = logging.getLogger(__name__)


# ── AJR ──────────────────────────────────────────────────────────────────────

from backend.engine.score_engine.ajr import AJR as _AJR_FULL

_AJR_DISPLAY_KEYS = (
    "protein", "fiber", "iron", "calcium",
    "magnesium", "potassium", "vitamin_c", "zinc",
)
_AJR = {k: _AJR_FULL[k] for k in _AJR_DISPLAY_KEYS if k in _AJR_FULL}

_AJR_LABELS = {
    "protein":   "Protéines", "fiber":     "Fibres",
    "iron":      "Fer",       "calcium":   "Calcium",
    "magnesium": "Magnésium", "potassium": "Potassium",
    "vitamin_c": "Vitamine C","zinc":      "Zinc",
}

_CYCLE_PRIORITY = {
    "menstrual":  ["iron",    "magnesium", "vitamin_c"],
    "follicular": ["protein", "fiber",     "magnesium"],
    "ovulatory":  ["vitamin_c","zinc",     "fiber"],
    "luteal":     ["magnesium","fiber",    "potassium"],
}


# ── enrich_why (calcul léger — liste) ────────────────────────────────────────

def enrich_why(recipes: list[dict], filters: dict | None = None) -> list[dict]:
    """
    Enrichit chaque recette avec :
      - `_why`       : explication contextuelle aux filtres actifs
      - `_nutrition` : dict nutriments + %AJR (8 clés)

    Charge le graphe nutritionnel une seule fois pour toute la liste.
    Ne modifie pas les recettes originales (copie superficielle).
    """
    from backend.core.data_io import load_nutrition_graph, load_ingredients_dict
    from backend.engine.planning_engine.servings import validate_servings
    filters = filters or {}
    ng = load_nutrition_graph()
    ings_dict = load_ingredients_dict()
    cycle_phase  = filters.get("cycle_phase")
    priority_keys = _CYCLE_PRIORITY.get(cycle_phase, [])

    from backend.services.filter_service import _hs

    result = []
    for r in recipes:
        r = dict(r)   # copie superficielle — on ne mute pas l'original
        rid      = str(r.get("id", ""))
        nutr     = ng.get(rid, {})
        servings = validate_servings(r.get("servings", 4))
        # Attacher health_scores depuis le cache filter_service
        # (contient booléens + valeurs brutes vitamin_c_mg, iron_mg, etc.)
        r["health_scores"] = _hs(r)

        if not nutr:
            r["_why"]       = None
            r["_nutrition"] = {}
            result.append(r)
            continue

        # CORRECTIF DOUBLE-DIVISION : le nutrition graph stocke des valeurs
        # DÉJÀ par portion (compute_nutrition() divise par srv avant de retourner).
        # On ne divise plus par servings ici — les valeurs sont directement utilisables.
        nutri_summary: dict = {}
        all_highlights: dict = {}

        for key, ajr in _AJR.items():
            val = nutr.get(key, 0) or 0          # déjà par portion
            pct = round((val / ajr) * 100) if val > 0 and ajr > 0 else 0
            nutri_summary[key] = {"value": round(val, 1), "pct_ajr": pct}
            if pct >= 10:
                all_highlights[key] = (pct, _AJR_LABELS[key])

        kcal = round(nutr.get("calories") or 0)  # déjà par portion
        nutri_summary["calories"] = {"value": kcal, "pct_ajr": 0}
        nutri_summary["_servings"] = servings        # info côté client
        r["_nutrition"] = nutri_summary

        why_parts: list[str] = []
        if filters.get("high_protein") and "protein" in all_highlights:
            why_parts.append(f"💪 {nutri_summary['protein']['value']}g")
        if filters.get("low_calorie") and kcal:
            why_parts.append(f"📉 {kcal} kcal")
        if filters.get("high_fiber") and "fiber" in all_highlights:
            why_parts.append(f"🌾✨ {nutri_summary['fiber']['value']}g")
        if filters.get("diet") == "vegan":
            why_parts.append("🌿 Végétal")
        if filters.get("low_ig") and (
            r.get("health_scores", {}).get("diabetes_friendly") or
            r.get("health_scores", {}).get("low_ig")
        ):
            why_parts.append("🩸 IG Bas")

        if not why_parts:
            ordered: list = []
            for pk in priority_keys:
                if pk in all_highlights:
                    ordered.append(all_highlights.pop(pk))
            remaining = sorted(all_highlights.values(), reverse=True)
            ordered.extend(remaining)
            top = ordered[:2]
            if top:
                why_parts = [f"{label} {pct}% AJR" for pct, label in top]
                if kcal:
                    why_parts.append(f"{kcal} kcal/pers.")
            elif kcal:
                why_parts.append(f"{kcal} kcal/pers.")

        r["_why"] = " · ".join(why_parts) if why_parts else None

        # ── Flags enrichis (agrégés depuis ingrédients) ───────────────────────
        composition = r.get("composition", r.get("ingredients", []))
        agg_diet = {"egg_free": True, "dairy_free": True, "soy_free": True, "fermented_free": True}
        agg_nutr = {"vitamins": False, "minerals": False, "omega3": False, "antioxidant": False, "low_sugar": False, "low_sodium": False}
        for ing in composition:
            iid = (ing.get("ingredient") or ing.get("ingredient_id") if isinstance(ing, dict) else str(ing))
            if not iid:
                continue
            ing_data = ings_dict.get(iid, {})
            dp = ing_data.get("diet_profile", {})
            af = ing_data.get("allergens_eu", [])
            nf = ing_data.get("nutrition_flags", {})
            if dp.get("egg_free") is False or dp.get("sans_oeuf") is False or "eggs" in af:
                agg_diet["egg_free"] = False
            if dp.get("dairy_free") is False or "milk" in af:
                agg_diet["dairy_free"] = False
            if dp.get("soy_free") is False or dp.get("sans_soja") is False or "soybeans" in af:
                agg_diet["soy_free"] = False
            if dp.get("fermented") is True:
                agg_diet["fermented_free"] = False
            if nf.get("high_vitamin_c") or nf.get("source_vitamin_c") or nf.get("high_folate") or nf.get("source_folate") or nf.get("high_vitamin_d") or nf.get("source_vitamin_d"):
                agg_nutr["vitamins"] = True
            if nf.get("high_calcium") or nf.get("good_source_calcium") or nf.get("high_iron") or nf.get("good_source_iron") or nf.get("high_magnesium") or nf.get("source_magnesium") or nf.get("high_potassium") or nf.get("good_source_potassium") or nf.get("high_zinc") or nf.get("source_zinc"):
                agg_nutr["minerals"] = True
            if nf.get("high_omega3") or nf.get("source_omega3"):
                agg_nutr["omega3"] = True
            if nf.get("antioxidant_rich"):
                agg_nutr["antioxidant"] = True
            if nf.get("low_sugar"):
                agg_nutr["low_sugar"] = True
            if nf.get("low_sodium"):
                agg_nutr["low_sodium"] = True
        r["diet_flags_enriched"]  = agg_diet
        r["nutrition_highlights"] = agg_nutr

        result.append(r)

    return result


# Alias pour la compat ascendante avec recipes.py
enrich_batch = enrich_why


# ── enrich_one (calcul complet — fiche recette) ───────────────────────────────

def enrich_one(recipe: dict) -> dict:
    """
    Calcule les données dérivées d'une recette (fiche complète).

    Ne modifie JAMAIS la recette originale.
    Retourne uniquement les champs calculés, prêts à être fusionnés :
      nutrition, score_data, score_reliability, score_coverage,
      seasonal_tag, seasonal_ratio,
      final_score, quality_score, relevance_score, nutrition_score, score_reasons,
      ingredients_availability, ingredients_meta,
      culinary_score, culinary_violations,
      carbon_data, price_data
    """
    from backend.core.data_io import (
        load_nutrition_graph, load_score_graph,
        load_availability_graph, load_ingredients_dict,
    )
    from backend.engine.planning_engine.servings  import validate_servings
    from backend.engine.score_engine.reliability  import reliability
    from backend.engine.score_engine.explainer    import explain
    from backend.engine.rule_engine.seasonality   import seasonal_ingredients
    from backend.engine.rule_engine.validation    import validate_recipe
    from backend.engine.rule_engine.carbon        import carbon_score
    from backend.engine.rule_engine.variants      import vegan_variant  # noqa — gardé pour cohérence
    from backend.engine.planning_engine.budget    import estimate_price
    from backend.services.scoring_service         import score_recipe as _score_recipe

    rid       = str(recipe.get("id", ""))
    ng        = load_nutrition_graph()
    sg        = load_score_graph()
    av        = load_availability_graph()
    ings_dict = load_ingredients_dict()
    out: dict = {}

    # ── Nutrition par portion ─────────────────────────────────────────────────
    # IMPORTANT : le nutrition graph stocke des valeurs DÉJÀ par portion
    # (compute_nutrition() divise par srv avant de retourner).
    # On ne divise donc PAS à nouveau — ancienne division /servings = double bug.
    #
    # On recalcule toujours via compute_nutrition() pour :
    #   1. Corriger la double-division (graph → valeurs correctes)
    #   2. Obtenir les nutriments étendus (vitamine A/D/E/K, folates, oméga-3…)
    #      absents de l'ancien graph pré-calculé
    #   3. Fresh prime (alias fix fiable), graph en fallback pour clés absentes/nulles
    from backend.engine.nutrition_engine import compute_nutrition as _compute_nutr
    servings    = validate_servings(recipe.get("servings", 4))
    ng_graph    = ng.get(rid, {})                          # déjà par portion
    fresh       = _compute_nutr(recipe)                    # déjà par portion
    _skip = {"servings_used", "source", "_per_serving", "_source"}

    merged = dict(fresh)
    for k, v in ng_graph.items():
        if k not in _skip and (k not in merged or (not merged.get(k) and v)):
            merged[k] = v

    merged = {k: round(v, 2) if isinstance(v, (int, float)) else v
              for k, v in merged.items()}
    # Sel dérivé du sodium fusionné (1 mg sodium = 0.00254 g sel — UE 1169/2011)
    sodium_merged = merged.get("sodium", 0) or 0
    if sodium_merged > 0:
        merged["salt"] = round(float(sodium_merged) * 0.00254, 2)
    out["nutrition"] = merged
    out["nutrition"]["_per_serving"] = servings
    out["score_data"] = sg.get(rid, {})

    # ── _nutrition : résumé AJR depuis le graphe (source validée) ────────────
    # Le graphe nutritionnel contient des valeurs par portion pré-calculées et
    # validées (audit CIQUAL). On les préfère aux valeurs fraîches de
    # compute_nutrition() qui peuvent être biaisées par des incohérences
    # servings/quantités. Ce champ est utilisé par le frontend pour le scoring
    # (buildNutrPctMap path 1 → computeNRFScore / computeAlimScore).
    nutri_summary: dict = {}
    _src = ng_graph if ng_graph else merged   # graphe d'abord, merged en fallback
    for key, ajr in _AJR.items():
        val = _src.get(key, 0) or 0
        pct = round((val / ajr) * 100) if val > 0 and ajr > 0 else 0
        nutri_summary[key] = {"value": round(val, 1), "pct_ajr": pct}
    kcal_ng = round(_src.get("calories") or 0)
    nutri_summary["calories"] = {"value": kcal_ng, "pct_ajr": 0}
    nutri_summary["_servings"] = servings
    out["_nutrition"] = nutri_summary

    # ── health_scores enrichis (mêmes données que la page liste) ─────────────
    # Sans cet appel la fiche détail reçoit les health_scores bruts de la DB
    # (structure ancienne, sans protein_g / fiber_g / kcal / glycemic_category)
    # → computeAlimScore donne un score différent entre liste et détail.
    from backend.services.filter_service import _hs as _filter_hs
    out["health_scores"] = _filter_hs(recipe)

    # ── Fiabilité nutritionnelle ──────────────────────────────────────────────
    _rel = reliability(recipe)
    out["score_reliability"] = _rel.get("status")
    out["score_coverage"]    = _rel.get("coverage")

    # ── Saisonnalité dynamique ────────────────────────────────────────────────
    current_month = datetime.date.today().month
    _comp_for_season = recipe.get("composition", recipe.get("ingredients", []))
    recipe_ings   = {
        (i.get("ingredient") or i.get("ingredient_id", "") if isinstance(i, dict) else str(i)).lower()
        for i in _comp_for_season
    }
    in_season = set(seasonal_ingredients(current_month))
    strict    = recipe_ings - {"salt", "pepper", "oil", "olive_oil", "water", "bouillon"}
    if strict:
        ratio = len(strict & in_season) / len(strict)
        out["seasonal_tag"]   = (
            "de_saison"      if ratio >= 0.7 else
            "presque_saison" if ratio >= 0.4 else
            "hors_saison"
        )
        out["seasonal_ratio"] = round(ratio, 2)
    else:
        out["seasonal_tag"]   = "année_entière"
        out["seasonal_ratio"] = 1.0

    # ── Scoring CDC_03c ───────────────────────────────────────────────────────
    _scored = _score_recipe(recipe)
    out["final_score"]     = round(_scored.get("final_score",    _scored.get("adaptive_score", 0)), 2)
    out["quality_score"]   = round(_scored.get("global_score",   0), 2)
    out["relevance_score"] = round(_scored.get("adaptive_score", 0), 2)
    out["nutrition_score"] = round(sg.get(rid, {}).get("nutrition_score", 0), 2)
    out["score_reasons"]   = explain(_scored)

    # ── Helpers ID ingrédient ─────────────────────────────────────────────────
    def _ing_id(ing: dict | str) -> str:
        """Extrait l'identifiant d'un ingrédient (clé 'ingredient' ou 'ingredient_id')."""
        if isinstance(ing, dict):
            return ing.get("ingredient") or ing.get("ingredient_id") or ""
        return str(ing)

    def _resolve_ing(iid: str) -> dict:
        """Cherche un ingrédient dans le dictionnaire en normalisant les IDs slash.
        mushroom/button → essaie : exact → mushroom_button → mushroom → {}
        """
        if not iid:
            return {}
        d = ings_dict.get(iid)
        if d:
            return d
        if "/" in iid:
            und = iid.replace("/", "_")
            d = ings_dict.get(und)
            if d:
                return d
            first = iid.split("/")[0]
            d = ings_dict.get(first)
            if d:
                return d
        return {}

    # ── Disponibilité des ingrédients ─────────────────────────────────────────
    composition_ings = recipe.get("composition", recipe.get("ingredients", []))
    ing_avail: dict = {}
    for ing in composition_ings:
        iid = _ing_id(ing)
        ing_avail[iid] = av.get(iid, {}).get("available_in_france", True)
    out["ingredients_availability"] = ing_avail

    # ── Métadonnées ingrédients ───────────────────────────────────────────────
    ings_meta: dict = {}
    for ing in composition_ings:
        iid = _ing_id(ing)
        if iid and iid not in ings_meta:
            d = _resolve_ing(iid)
            name_fr = d.get("canonical_name_fr") or iid.replace("/", " ").replace("_", " ").title()
            ings_meta[iid] = {
                "name_fr":        name_fr,
                "substitutions":  d.get("substitutions", []),
                "flavor_profile": d.get("flavor_profile", []),
            }
    out["ingredients_meta"] = ings_meta

    # ── Validation culinaire ──────────────────────────────────────────────────
    _result = validate_recipe(recipe)
    out["culinary_score"]      = _result.get("score", 10)
    out["culinary_violations"] = [
        v for v in _result.get("violations", [])
        if v.get("severity") in ("critical", "warning")
    ]

    # ── Durabilité (CO₂) et prix ──────────────────────────────────────────────
    out["carbon_data"] = carbon_score(recipe)
    out["price_data"]  = estimate_price(recipe)

    # ── Flags diététiques enrichis (agrégés depuis les ingrédients) ───────────
    # "sans X" = True si AUCUN ingrédient ne contient X
    # flag nutritionnel = True si AU MOINS UN ingrédient le porte
    composition = recipe.get("composition", recipe.get("ingredients", []))

    agg_diet = {
        "egg_free":       True,
        "dairy_free":     True,
        "soy_free":       True,
        "fermented_free": True,
    }
    agg_nutr = {
        "vitamins":    False,
        "minerals":    False,
        "omega3":      False,
        "antioxidant": False,
        "low_sugar":   False,
        "low_sodium":  False,
    }

    for ing in composition:
        iid = (
            ing.get("ingredient") or ing.get("ingredient_id")
            if isinstance(ing, dict) else str(ing)
        )
        if not iid:
            continue
        ing_data = ings_dict.get(iid, {})
        dp = ing_data.get("diet_profile", {})
        af = ing_data.get("allergens_eu", [])
        nf = ing_data.get("nutrition_flags", {})

        if dp.get("egg_free") is False or dp.get("sans_oeuf") is False or "eggs" in af:
            agg_diet["egg_free"] = False
        if dp.get("dairy_free") is False or "milk" in af:
            agg_diet["dairy_free"] = False
        if dp.get("soy_free") is False or dp.get("sans_soja") is False or "soybeans" in af:
            agg_diet["soy_free"] = False
        if dp.get("fermented") is True:
            agg_diet["fermented_free"] = False

        if nf.get("high_vitamin_c") or nf.get("source_vitamin_c") \
                or nf.get("high_folate") or nf.get("source_folate") \
                or nf.get("high_vitamin_d") or nf.get("source_vitamin_d"):
            agg_nutr["vitamins"] = True
        if nf.get("high_calcium") or nf.get("good_source_calcium") \
                or nf.get("high_iron") or nf.get("good_source_iron") \
                or nf.get("high_magnesium") or nf.get("source_magnesium") \
                or nf.get("high_potassium") or nf.get("good_source_potassium") \
                or nf.get("high_zinc") or nf.get("source_zinc"):
            agg_nutr["minerals"] = True
        if nf.get("high_omega3") or nf.get("source_omega3"):
            agg_nutr["omega3"] = True
        if nf.get("antioxidant_rich"):
            agg_nutr["antioxidant"] = True
        if nf.get("low_sugar"):
            agg_nutr["low_sugar"] = True
        if nf.get("low_sodium"):
            agg_nutr["low_sodium"] = True

    out["diet_flags_enriched"]  = agg_diet
    out["nutrition_highlights"] = agg_nutr

    return out


__all__ = ["enrich_one", "enrich_why", "enrich_batch"]