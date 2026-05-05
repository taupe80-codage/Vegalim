#!/usr/bin/env python3
"""
sync_ingredients.py  v2.0
--------------------------
Synchronise ingredients_dictionary.json ↔ nutrition_v2.json ↔ ingredient_physical.json

Principe : nutrition est la source de vérité.
  Chaque variant nutrition = nutrition distincte = entrée dict autonome.

── Étape 1a : IDs standalone (is_standalone=True) dans nutrition, absents du dict
     → ajout auto dans le dict

── Étape 1b : IDs agrégats (is_standalone=False) dans nutrition, absents du dict
     → EXPAND : chaque variant → entrée dict autonome
     → nutrition_key = "parent_id/variant_name"
     → dict_id = "{parent}_{variant}" si le variant name est générique ou déjà pris

── Étape 2 : IDs dans le dict sans entrée nutrition
     → squelette nutrition généré → review_dict_missing_nutrition.json

── Étape 3 : IDs dans le dict sans entrée physical
     → squelette physical généré → review_dict_missing_physical.json

── Scoring
     nutri→dict  : score de priorité (confidence, aliases, nova, validation, standalone)
     dict→physical : score de criticité (catégorie, richesse nutrition, health_score, restrictions diet)
     Les fichiers review sont triés par score décroissant.

Sorties :
  ingredients_dictionary_synced.json
  nutrition_v2_synced.json
  ingredient_physical_synced.json
  review_dict_missing_nutrition.json   ← triés par score décroissant
  review_dict_missing_physical.json    ← triés par score décroissant
  sync_report.txt
"""

import json
import copy
import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════

INPUT_DIR  = Path("/mnt/user-data/uploads")
OUTPUT_DIR = Path("/mnt/user-data/outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

DICT_FILE  = INPUT_DIR / "ingredients_dictionary.json"
NUT_FILE   = INPUT_DIR / "nutrition_v2.json"
PHYS_FILE  = INPUT_DIR / "ingredient_physical.json"

# Noms de variants trop génériques pour être utilisés comme ID seul → préfixés avec le parent
GENERIC_VARIANT_NAMES = {
    "default", "common", "red", "green", "black", "brown", "white",
    "plain", "heavy", "whole", "dark", "powder", "nibs", "wrappers",
    "puff", "pizza", "oat", "soy", "coconut", "almond", "cashew", "rice",
    "vegetable", "amarillo", "korean", "peanut", "yogurt",
}

VALID_DICT_CATEGORIES = {
    "vegetable", "fruit", "fat", "herb_spice", "liquid", "grain",
    "protein_plant", "condiment", "nut_seed", "legume", "leavening",
    "dairy", "sweetener", "superfood", "dairy_alternative",
    "egg", "fermented", "additive", "alcohol",
}

DIET_DEFAULTS = {
    "vegetable":         dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "fruit":             dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "grain":             dict(vegan=True,  vegetarian=True,  sans_gluten=False, sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "legume":            dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=True,  diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=True),
    "fat":               dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "herb_spice":        dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "condiment":         dict(vegan=False, vegetarian=False, sans_gluten=False, sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=False, sans_oeuf=False, riche_en_fibres=False),
    "dairy":             dict(vegan=False, vegetarian=True,  sans_gluten=True,  sans_lactose=False, sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "dairy_alternative": dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=False, hyper_proteine=False, diabet_free=False, sans_soja=False, sans_oeuf=True,  riche_en_fibres=False),
    "sweetener":         dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "protein_plant":     dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=True,  diabet_free=True,  sans_soja=False, sans_oeuf=True,  riche_en_fibres=True),
    "nut_seed":          dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=False, hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=True),
    "superfood":         dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=True),
    "leavening":         dict(vegan=True,  vegetarian=True,  sans_gluten=False, sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "liquid":            dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "egg":               dict(vegan=False, vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=True,  diabet_free=True,  sans_soja=True,  sans_oeuf=False, riche_en_fibres=False),
    "fermented":         dict(vegan=False, vegetarian=False, sans_gluten=False, sans_lactose=False, sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=False, sans_oeuf=True,  riche_en_fibres=False),
    "additive":          dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "alcohol":           dict(vegan=True,  vegetarian=True,  sans_gluten=False, sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
}

CULINARY_PROPS_BY_CATEGORY = {
    "vegetable": ["fresh", "fiber"],     "fruit": ["fresh", "sweet"],
    "grain": ["starchy"],                "legume": ["protein", "fiber", "starchy"],
    "fat": ["fat"],                      "herb_spice": ["aromatic"],
    "condiment": ["aromatic", "acid"],   "dairy": ["creamy", "protein"],
    "dairy_alternative": ["creamy"],     "sweetener": ["sweet"],
    "protein_plant": ["protein"],        "nut_seed": ["fat", "protein"],
    "superfood": ["fresh"],              "leavening": ["leavening"],
    "liquid": ["neutral"],               "egg": ["protein", "creamy"],
    "fermented": ["fermented", "umami"], "additive": ["neutral"],
    "alcohol": ["neutral"],
}

FLAVOR_BY_CATEGORY = {
    "vegetable": ["neutral"],      "fruit": ["sweet"],       "grain": ["neutral"],
    "legume": ["earthy"],          "fat": ["neutral"],        "herb_spice": ["aromatic"],
    "condiment": ["savory"],       "dairy": ["creamy"],       "dairy_alternative": ["neutral"],
    "sweetener": ["sweet"],        "protein_plant": ["neutral"], "nut_seed": ["nutty"],
    "superfood": ["neutral"],      "leavening": ["neutral"],  "liquid": ["neutral"],
    "egg": ["neutral"],            "fermented": ["umami"],    "additive": ["neutral"],
    "alcohol": ["neutral"],
}

DEFAULT_UNIT_BY_CATEGORY = {
    "vegetable": "piece",  "fruit": "piece",    "grain": "g",
    "legume": "g",         "fat": "ml",          "herb_spice": "g",
    "condiment": "ml",     "dairy": "ml",        "dairy_alternative": "ml",
    "sweetener": "g",      "protein_plant": "g", "nut_seed": "g",
    "superfood": "g",      "leavening": "g",     "liquid": "ml",
    "egg": "piece",        "fermented": "g",     "additive": "g",
    "alcohol": "ml",
}

# Priorité de la catégorie pour le scoring physical (max 10 pts)
CAT_PHYSICAL_PRIORITY = {
    "vegetable": 10, "fruit": 10, "egg": 10,
    "legume": 8,     "grain": 7,  "nut_seed": 7,
    "dairy": 6,      "dairy_alternative": 6,
    "herb_spice": 5, "protein_plant": 5,
    "fat": 4,        "condiment": 3, "sweetener": 3,
    "liquid": 2,     "fermented": 2, "superfood": 2,
    "leavening": 1,  "additive": 1,  "alcohol": 1,
}


# ══════════════════════════════════════════════════════════════════
# SCORING
# ══════════════════════════════════════════════════════════════════

def score_nut_to_dict(nut_id, nut_entry):
    """
    Score de priorité pour intégrer un ingrédient nutrition dans le dictionnaire.
    Max théorique : 100 pts

    Critères :
      Confiance nutritionnelle  (0–30) : avg confidence des variants
      Richesse aliases          (0–25) : nb max d'aliases → fréquence d'usage estimée
      Qualité alimentaire NOVA  (0–15) : NOVA 1 (brut) = prioritaire, NOVA 4 = moins urgent
      Score de validation       (0–20) : avg validation_score des variants
      Standalone                (+10)  : ingrédient autonome vs agrégat (ajout bonus)
    """
    variants = nut_entry.get("variants", {})
    meta     = nut_entry.get("_meta", {})
    details  = {}
    score    = 0

    # 1. Confiance nutritionnelle (0–30)
    confs    = [v.get("confidence", 0) for v in variants.values()]
    avg_conf = sum(confs) / len(confs) if confs else 0
    conf_pts = round(avg_conf * 30)
    score   += conf_pts
    details["confidence"] = {"value": round(avg_conf, 2), "pts": conf_pts, "max": 30,
                              "note": "avg confidence des variants"}

    # 2. Richesse aliases (0–25) — proxy de fréquence dans les recettes
    alias_counts = [len(v.get("aliases") or []) for v in variants.values()]
    max_aliases  = max(alias_counts) if alias_counts else 0
    alias_pts    = min(max_aliases * 2, 25)
    score       += alias_pts
    details["aliases"] = {"value": max_aliases, "pts": alias_pts, "max": 25,
                          "note": "nb max aliases → proxy usage recettes"}

    # 3. Qualité alimentaire NOVA (0–15) — NOVA 1 brut = prioritaire
    nova_vals = [v.get("nova_group") for v in variants.values() if v.get("nova_group")]
    avg_nova  = sum(nova_vals) / len(nova_vals) if nova_vals else 3
    nova_pts  = max(0, round((4 - avg_nova) / 3 * 15))
    score    += nova_pts
    details["nova_group"] = {"value": round(avg_nova, 1), "pts": nova_pts, "max": 15,
                             "note": "NOVA 1=aliment brut (+15), NOVA 4=ultra-transformé (0)"}

    # 4. Score de validation (0–20)
    val_scores = [v.get("validation_score", 0.9) for v in variants.values()]
    avg_val    = sum(val_scores) / len(val_scores) if val_scores else 0.9
    val_pts    = round(avg_val * 20)
    score     += val_pts
    details["validation_score"] = {"value": round(avg_val, 2), "pts": val_pts, "max": 20,
                                   "note": "avg validation_score des variants"}

    # 5. Standalone bonus (+10)
    is_standalone = meta.get("is_standalone", True)
    if is_standalone:
        score += 10
    details["standalone"] = {"value": is_standalone, "pts": 10 if is_standalone else 0, "max": 10,
                             "note": "ingrédient autonome vs agrégat"}

    label = "haute" if score >= 75 else "moyenne" if score >= 50 else "faible"
    return score, label, details


def score_physical(dict_id, dict_entry, nut_entry=None):
    """
    Score de criticité pour remplir l'entrée physical d'un ingrédient.
    Max théorique : 55 pts

    Critères :
      Priorité catégorie   (0–10) : légumes/fruits/œufs critiques (unités pièce)
      Confiance nutrition  (0–20) : si nutrition fiable, physical devient bloquant
      Health score moyen   (0–15) : ingrédients sains souvent recommandés → physical utile
      Restrictions diet    (0–10) : bcp de restrictions → usage fréquent en filtrage
    """
    variants = nut_entry.get("variants", {}) if nut_entry else {}
    cat      = dict_entry.get("category", "condiment")
    details  = {}
    score    = 0

    # 1. Priorité catégorie (0–10)
    cat_pts = CAT_PHYSICAL_PRIORITY.get(cat, 3)
    score  += cat_pts
    details["category"] = {"value": cat, "pts": cat_pts, "max": 10,
                           "note": "catégories piece/volumétriques = critique"}

    # 2. Confiance nutrition (0–20)
    if variants:
        confs    = [v.get("confidence", 0) for v in variants.values()]
        avg_conf = sum(confs) / len(confs) if confs else 0
        nut_pts  = round(avg_conf * 20)
    else:
        avg_conf = 0
        nut_pts  = 0
    score += nut_pts
    details["nut_confidence"] = {"value": round(avg_conf, 2), "pts": nut_pts, "max": 20,
                                 "note": "nutrition fiable → physical devient bloquant"}

    # 3. Health score moyen (0–15)
    if variants:
        hs_vals = [v.get("health_score", 50) for v in variants.values() if v.get("health_score")]
        avg_hs  = sum(hs_vals) / len(hs_vals) if hs_vals else 50
        hs_pts  = round(avg_hs / 100 * 15)
    else:
        avg_hs = 0
        hs_pts = 0
    score += hs_pts
    details["health_score"] = {"value": round(avg_hs, 1), "pts": hs_pts, "max": 15,
                               "note": "ingrédients sains souvent recommandés → physical utile"}

    # 4. Restrictions diet (0–10)
    diet         = dict_entry.get("diet_profile", {})
    restrictions = sum(1 for v in diet.values() if v is False)
    restr_pts    = min(restrictions * 2, 10)
    score       += restr_pts
    details["diet_restrictions"] = {"value": restrictions, "pts": restr_pts, "max": 10,
                                    "note": "bcp de restrictions → filtrage fréquent"}

    label = "critique" if score >= 35 else "important" if score >= 20 else "faible"
    return score, label, details


# ══════════════════════════════════════════════════════════════════
# CONSTRUCTEURS D'ENTRÉES
# ══════════════════════════════════════════════════════════════════

def _resolve_category(raw_cat):
    if raw_cat in VALID_DICT_CATEGORIES:
        return raw_cat
    return "condiment"  # fallback sûr

def _base_dict_entry(dict_id, category, name_fr, nut_key, source_note):
    cat = _resolve_category(category)
    return {
        "id":                    dict_id,
        "name_fr":               name_fr,
        "category":              cat,
        "substitutions":         [],
        "diet_profile":          copy.deepcopy(DIET_DEFAULTS.get(cat, DIET_DEFAULTS["condiment"])),
        "culinary_properties":   CULINARY_PROPS_BY_CATEGORY.get(cat, ["neutral"]),
        "flavor_profile":        FLAVOR_BY_CATEGORY.get(cat, ["neutral"]),
        "cooking_behavior":      {"time_minutes": None, "__note": "À compléter"},
        "allergens_eu":          [],
        "nutrition_key":         nut_key,
        "bioavailability_protein": 0.7,
        "__auto_generated":      True,
        "__source":              source_note,
    }

def make_dict_entry_standalone(nut_id, nut_entry):
    meta    = nut_entry.get("_meta", {})
    variants = nut_entry.get("variants", {})
    cat     = meta.get("category", "condiment")
    name_fr = meta.get("name_fr") or (next(iter(variants.values())).get("name_fr", nut_id) if variants else nut_id)
    nut_key = f"{nut_id}/default" if "default" in variants else (f"{nut_id}/{next(iter(variants))}" if variants else f"{nut_id}/default")
    return _base_dict_entry(nut_id, cat, name_fr, nut_key, f"standalone:nutrition/{nut_id}")

def make_dict_entry_variant(dict_id, parent_id, variant_name, variant_data, parent_meta):
    cat     = parent_meta.get("category", "condiment")
    name_fr = variant_data.get("name_fr", dict_id)
    nut_key = f"{parent_id}/{variant_name}"
    return _base_dict_entry(dict_id, cat, name_fr, nut_key, f"expanded:nutrition/{parent_id}/{variant_name}")

def make_nutrition_skeleton(dict_id, dict_entry):
    cat = dict_entry.get("category", "vegetable")
    return {
        "_meta": {"category": cat, "name_fr": dict_entry.get("name_fr", dict_id),
                  "is_standalone": True, "__auto_generated": True},
        "variants": {"default": {
            "name_fr": dict_entry.get("name_fr", dict_id), "name_en": dict_id,
            "aliases": [], "source_key": dict_id, "ingredient_type": "raw",
            "calories_kcal": None, "protein_g": None, "carbs_g": None, "fat_g": None,
            "fiber_g": None, "sugar_g": None, "starch_g": None, "added_sugar": 0, "alcohol_g": 0.0,
            "saturated_fat_g": None, "monounsaturated_fat_g": None, "polyunsaturated_fat_g": None,
            "omega3_g": None, "omega6_g": None, "cholesterol_mg": None,
            "sodium_mg": None, "calcium_mg": None, "iron_mg": None, "magnesium_mg": None,
            "phosphorus_mg": None, "potassium_mg": None, "zinc_mg": None,
            "copper_mg": None, "manganese_mg": None, "selenium_ug": None,
            "vitamin_a_ug": None, "vitamin_b1_mg": None, "vitamin_b2_mg": None,
            "vitamin_b3_mg": None, "vitamin_b5_mg": None, "vitamin_b6_mg": None,
            "folate_ug": None, "vitamin_b12_ug": None, "vitamin_c_mg": None,
            "vitamin_d_ug": None, "vitamin_e_mg": None, "vitamin_k1_ug": None,
            "glycemic_index": None, "glycemic_index_source": "estimated",
            "glycemic_load": None, "nova_group": None, "__review_needed": True,
        }}
    }

def make_physical_skeleton(dict_id, dict_entry):
    cat          = dict_entry.get("category", "vegetable")
    default_unit = DEFAULT_UNIT_BY_CATEGORY.get(cat, "g")
    return {
        "default_unit": default_unit,
        "units": {
            default_unit: {"g": None, "note": "À compléter"},
            "g": {"g": 1}, "kg": {"g": 1000},
        },
        "density_g_per_ml": None, "water_content_pct": None,
        "edible_pct": None, "ciqual_id": None,
        "note": "À compléter",
        "__auto_generated": True, "__review_needed": True,
    }

def variant_dict_id(parent_id, variant_name, existing_ids):
    """ID dict pour un variant : préfixe si générique ou collision potentielle."""
    if variant_name in GENERIC_VARIANT_NAMES or variant_name in existing_ids:
        return f"{parent_id}_{variant_name}"
    return variant_name


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("\n🔄 Chargement des fichiers…")
    d_raw  = json.load(open(DICT_FILE,  encoding="utf-8"))
    nut    = json.load(open(NUT_FILE,   encoding="utf-8"))
    phys   = json.load(open(PHYS_FILE,  encoding="utf-8"))

    dict_list  = d_raw["ingredients"]
    dict_map   = {ing["id"]: ing for ing in dict_list}
    nut_items  = nut["ingredients"]

    dict_ids = set(dict_map.keys())
    nut_ids  = set(nut_items.keys())
    phys_ids = set(k for k in phys if not k.startswith("_"))

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    report = [
        f"sync_ingredients v2.0 — {ts}", "=" * 60,
        "Source de vérité : nutrition_v2.json",
        f"  dict     : {len(dict_ids)} ingrédients",
        f"  nutrition: {len(nut_ids)} entrées",
        f"  physical : {len(phys_ids)} ingrédients", "",
    ]

    # ── Étape 1 : nutrition → dict ────────────────────────────────
    print("\n📥 Étape 1 — nutrition → dict…")
    nut_not_in_dict  = sorted(nut_ids - dict_ids)
    added_standalone = []
    added_expanded   = []

    for nut_id in nut_not_in_dict:
        nut_entry = nut_items[nut_id]
        meta      = nut_entry.get("_meta", {})
        variants  = nut_entry.get("variants", {})

        if meta.get("is_standalone", True):
            # 1a — standalone : une entrée dict directe
            entry = make_dict_entry_standalone(nut_id, nut_entry)
            score, label, score_details = score_nut_to_dict(nut_id, nut_entry)
            entry["__priority_score"] = score
            entry["__priority_label"] = label
            entry["__score_details"]  = score_details
            dict_list.append(entry)
            dict_map[nut_id] = entry
            dict_ids.add(nut_id)
            added_standalone.append({"id": nut_id, "score": score, "label": label})

        else:
            # 1b — agrégat : EXPAND → une entrée dict par variant
            for var_name, var_data in variants.items():
                new_id = variant_dict_id(nut_id, var_name, dict_ids)
                if new_id in dict_ids:
                    continue  # collision après préfixage → déjà couvert
                entry = make_dict_entry_variant(new_id, nut_id, var_name, var_data, meta)
                # Score sur le variant seul
                single = {"_meta": meta, "variants": {var_name: var_data}}
                score, label, score_details = score_nut_to_dict(nut_id, single)
                entry["__priority_score"] = score
                entry["__priority_label"] = label
                entry["__score_details"]  = score_details
                dict_list.append(entry)
                dict_map[new_id] = entry
                dict_ids.add(new_id)
                added_expanded.append({
                    "parent": nut_id, "variant": var_name,
                    "dict_id": new_id, "score": score, "label": label,
                })

    n_aggregates = len({e["parent"] for e in added_expanded})
    report += [
        "── Étape 1 : nutrition → dict ──",
        f"  IDs nutrition absents du dict : {len(nut_not_in_dict)}",
        f"  → Standalone ajoutés          : {len(added_standalone)}",
        f"  → Variants expanded           : {len(added_expanded)} (depuis {n_aggregates} agrégats)",
        f"  → Total nouvelles entrées     : {len(added_standalone) + len(added_expanded)}", "",
    ]

    # ── Étape 2 : dict → nutrition (squelettes) ───────────────────
    print("📤 Étape 2 — dict → nutrition (squelettes)…")
    dict_not_in_nut = sorted(dict_ids - nut_ids)
    nut_skeletons   = []

    for dict_id in dict_not_in_nut:
        dict_entry = dict_map[dict_id]
        skeleton   = make_nutrition_skeleton(dict_id, dict_entry)
        nut_items[dict_id] = skeleton

        # Pour les variants expanded, résoudre la nutrition réelle via nutrition_key (parent/variant)
        nut_entry_for_score = None
        nut_key = dict_entry.get("nutrition_key") or ""
        if "/" in nut_key:
            parent_id, var_name = nut_key.split("/", 1)
            parent_entry = nut_items.get(parent_id)
            if parent_entry and var_name in parent_entry.get("variants", {}):
                nut_entry_for_score = {
                    "_meta":    parent_entry.get("_meta", {}),
                    "variants": {var_name: parent_entry["variants"][var_name]},
                }

        score, label, score_details = score_physical(dict_id, dict_entry, nut_entry_for_score)
        nut_skeletons.append({
            "id":             dict_id,
            "name_fr":        dict_entry.get("name_fr", dict_id),
            "category":       dict_entry.get("category"),
            "nutrition_key":  nut_key,
            "priority_score": score,
            "priority_label": label,
            "score_details":  score_details,
            "skeleton":       skeleton,
        })

    nut_skeletons.sort(key=lambda x: -x["priority_score"])
    lbl_count = lambda lbl: sum(1 for s in nut_skeletons if s["priority_label"] == lbl)

    report += [
        "── Étape 2 : dict → nutrition (squelettes) ──",
        f"  IDs dict sans nutrition : {len(dict_not_in_nut)}",
        f"  Top 5 critique          : {[s['id'] for s in nut_skeletons[:5]]}",
        f"  critique={lbl_count('critique')} | important={lbl_count('important')} | faible={lbl_count('faible')}", "",
    ]

    # ── Étape 3 : dict → physical (squelettes) ────────────────────
    print("🏋️  Étape 3 — dict → physical (squelettes)…")
    dict_not_in_phys = sorted(dict_ids - phys_ids)
    phys_skeletons   = []

    for dict_id in dict_not_in_phys:
        dict_entry = dict_map[dict_id]
        skeleton   = make_physical_skeleton(dict_id, dict_entry)
        phys[dict_id] = skeleton

        # Résoudre la nutrition réelle via nutrition_key (parent/variant pour les expanded)
        nut_entry_for_score = nut_items.get(dict_id)
        if not nut_entry_for_score:
            nut_key = dict_entry.get("nutrition_key") or ""
            if "/" in nut_key:
                parent_id, var_name = nut_key.split("/", 1)
                parent_entry = nut_items.get(parent_id)
                if parent_entry and var_name in parent_entry.get("variants", {}):
                    nut_entry_for_score = {
                        "_meta":    parent_entry.get("_meta", {}),
                        "variants": {var_name: parent_entry["variants"][var_name]},
                    }

        score, label, score_details = score_physical(dict_id, dict_entry, nut_entry_for_score)
        phys_skeletons.append({
            "id":             dict_id,
            "name_fr":        dict_entry.get("name_fr", dict_id),
            "category":       dict_entry.get("category"),
            "priority_score": score,
            "priority_label": label,
            "score_details":  score_details,
            "skeleton":       skeleton,
        })

    phys_skeletons.sort(key=lambda x: -x["priority_score"])
    lbl_count_p = lambda lbl: sum(1 for s in phys_skeletons if s["priority_label"] == lbl)

    report += [
        "── Étape 3 : dict → physical (squelettes) ──",
        f"  IDs dict sans physical  : {len(dict_not_in_phys)}",
        f"  Top 5 critique          : {[s['id'] for s in phys_skeletons[:5]]}",
        f"  critique={lbl_count_p('critique')} | important={lbl_count_p('important')} | faible={lbl_count_p('faible')}", "",
    ]

    # ── Mise à jour des compteurs internes ────────────────────────
    d_raw["ingredients"]       = dict_list
    d_raw["total_ingredients"] = len(dict_list)
    nut["total_bases"]         = len(nut_items)
    nut["total_variants"]      = sum(len(v.get("variants", {})) for v in nut_items.values())
    active_phys = len([k for k in phys if not k.startswith("_")])
    phys.setdefault("_meta", {})["coverage"] = (
        f"Active: {active_phys} | synced: {datetime.datetime.now().strftime('%Y-%m-%d')}"
    )

    # ── Sauvegarde ────────────────────────────────────────────────
    print("\n💾 Sauvegarde…")
    def save(data, fname):
        json.dump(data, open(OUTPUT_DIR / fname, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  ✅ {fname}")

    save(d_raw, "ingredients_dictionary_synced.json")
    save(nut,   "nutrition_v2_synced.json")
    save(phys,  "ingredient_physical_synced.json")

    save({
        "generated_at": ts,
        "count": len(nut_skeletons),
        "instruction": "Remplir les valeurs None (source : CIQUAL, USDA…). Trié par priorité décroissante.",
        "scoring": {
            "method": "score_physical() — priorité catégorie + confiance nutrition + health_score + restrictions diet",
            "max_pts": 55,
            "legend": {"critique (≥35)": "nutrition manquante bloquante", "important (≥20)": "utile pour recommandations", "faible (<20)": "ingrédient rare"},
        },
        "items": nut_skeletons,
    }, "review_dict_missing_nutrition.json")

    save({
        "generated_at": ts,
        "count": len(phys_skeletons),
        "instruction": "Remplir poids/unités (source : CIQUAL, références culinaires). Trié par priorité décroissante.",
        "scoring": {
            "method": "score_physical() — priorité catégorie + confiance nutrition + health_score + restrictions diet",
            "max_pts": 55,
            "legend": {"critique (≥35)": "physical manquant bloquant la conversion unité→grammes", "important (≥20)": "ingrédient fréquent", "faible (<20)": "peut attendre"},
        },
        "items": phys_skeletons,
    }, "review_dict_missing_physical.json")

    # ── Rapport final ─────────────────────────────────────────────
    report += [
        "── Résultat final ──",
        f"  dict     : {len(dict_list)} ingrédients  (+{len(added_standalone) + len(added_expanded)})",
        f"  nutrition: {nut['total_bases']} bases / {nut['total_variants']} variants",
        f"  physical : {active_phys} ingrédients",
        "",
        "── Fichiers générés ──",
        "  ingredients_dictionary_synced.json",
        "  nutrition_v2_synced.json",
        "  ingredient_physical_synced.json",
        "  review_dict_missing_nutrition.json  ← triés par score décroissant (critique→faible)",
        "  review_dict_missing_physical.json   ← triés par score décroissant (critique→faible)",
    ]

    report_str = "\n".join(report)
    (OUTPUT_DIR / "sync_report.txt").write_text(report_str, encoding="utf-8")
    print("\n" + report_str)
    print(f"\n✅ Sync terminé — {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
