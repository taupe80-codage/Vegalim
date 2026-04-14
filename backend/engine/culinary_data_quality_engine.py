"""
Culinary Data Quality Engine
==============================
Audit de qualité du dataset en production.
Route : GET /data_quality_audit

Contrôles :
  1. Doublons de titres
  2. Recettes sans ingrédients
  3. Incohérences nutrition (calories, sodium)
  4. Diet flags vegan incorrects
  5. Variantes vegan sans données nutritionnelles
  6. Résumé global avec score de qualité
"""

import json
from backend.engine.config import DATA_ROOT

def _safe_json(path, encoding="utf-8"):
    """Chargement JSON sécurisé avec context manager."""
    with open(path, encoding=encoding) as _f:
        return json.load(_f)


NON_VEGAN = {
    'oeuf','oeufs_dur','lait','butter','ghee','creme','creme_fraiche',
    'fromage_blanc','yogurt','parmesan','feta','mozzarella','cheese',
    'cheddar','fresh_cheese','gruyere_cheese','ricotta','salted_ricotta',
    'fromage_en_grain','paneer','kashk',
}


def _load():
    recipes   = _safe_json(DATA_ROOT / "recipes" / "recipes.json")["recipes"]
    nutr_g    = _safe_json(DATA_ROOT / "graphs" / "recipe_nutrition_graph_v1.json")
    score_g   = _safe_json(DATA_ROOT / "graphs" / "recipe_scoring_graph_v1.json")
    return recipes, nutr_g, score_g


def detect_duplicate_titles(recipes: list) -> list:
    seen, duplicates = {}, []
    for r in recipes:
        title = (r.get("titles", {}).get("fr") or r.get("titles", {}).get("original") or "").lower().strip()
        if not title:
            continue
        if title in seen:
            duplicates.append({"id": r["id"], "title": r.get("titles", {}).get("fr"), "duplicate_of": seen[title]})
        else:
            seen[title] = r["id"]
    return duplicates


def detect_missing_ingredients(recipes: list) -> list:
    return [
        {"id": r["id"], "title": r.get("titles", {}).get("fr"), "issue": "missing_ingredients"}
        for r in recipes if not r.get("composition")
    ]


def detect_short_instructions(recipes: list, min_steps: int = 3) -> list:
    return [
        {"id": r["id"], "title": r.get("titles", {}).get("fr"), "steps": len(r.get("instructions", []))}
        for r in recipes
        if not r.get("auto_generated") and len(r.get("instructions", [])) < min_steps
    ]


def nutrition_sanity_check(recipes: list, nutr_g: dict) -> list:
    issues = []
    for r in recipes:
        rid  = str(r["id"])
        nutr = nutr_g.get(rid, {})
        if not nutr:
            if not r.get("auto_generated"):
                issues.append({"id": r["id"], "title": r.get("titles", {}).get("fr"), "issue": "missing_nutrition"})
            continue
        cal    = nutr.get("calories", 0) or 0
        sodium = nutr.get("sodium",   0) or 0
        # Calories aberrantes (hors range végétarien raisonnable)
        if cal > 1200 and not nutr.get("high_sodium_note"):
            issues.append({"id": r["id"], "title": r.get("titles", {}).get("fr"), "issue": "calories_very_high", "value": cal})
        # Sodium > 2000mg sans note explicative
        if sodium > 2000 and not nutr.get("high_sodium_note"):
            issues.append({"id": r["id"], "title": r.get("titles", {}).get("fr"), "issue": "sodium_very_high", "value": sodium})
    return issues


def detect_vegan_flag_issues(recipes: list) -> list:
    issues = []
    for r in recipes:
        if r.get("auto_generated"):
            continue
        is_vegan = (r.get("diet_flags") or {}).get("vegan", False)
        # In v6, composition is a list of dicts with an "ingredient" key
        ings = [(i.get("ingredient") if isinstance(i, dict) else str(i)) for i in r.get("composition", [])]
        non_vegan_ings = [i for i in ings if i in NON_VEGAN]
        if is_vegan and non_vegan_ings:
            issues.append({
                "id":       r["id"],
                "title":    r.get("titles", {}).get("fr"),
                "issue":    "vegan_flag_incorrect",
                "non_vegan_ingredients": non_vegan_ings,
            })
    return issues


def run_quality_audit() -> dict:
    """
    Lance tous les contrôles qualité et retourne un rapport structuré.
    """
    try:
        recipes, nutr_g, score_g = _load()
    except Exception as e:
        return {"error": f"Impossible de charger les données : {e}"}

    total = len(recipes)
    auto  = sum(1 for r in recipes if r.get("auto_generated"))
    vegan = sum(1 for r in recipes if (r.get("diet_flags") or {}).get("vegan"))

    dup       = detect_duplicate_titles(recipes)
    missing   = detect_missing_ingredients(recipes)
    short_ins = detect_short_instructions(recipes)
    nutr_iss  = nutrition_sanity_check(recipes, nutr_g)
    vegan_iss = detect_vegan_flag_issues(recipes)

    # Score qualité global (100 = parfait)
    total_issues = len(dup) + len(missing) + len(short_ins) + len(nutr_iss) + len(vegan_iss)
    quality_score = max(0, round(100 - (total_issues / max(total, 1)) * 100))

    return {
        "summary": {
            "total_recipes":     total,
            "auto_generated":    auto,
            "vegan_recipes":     vegan,
            "total_issues":      total_issues,
            "quality_score":     quality_score,
        },
        "issues": {
            "duplicate_titles":       dup,
            "missing_ingredients":    missing,
            "short_instructions":     short_ins,
            "nutrition_anomalies":    nutr_iss,
            "vegan_flag_errors":      vegan_iss,
        },
    }
