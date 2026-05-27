"""
usda_refactor_v2.py  v5.1
==========================
Transforme FoodData_Central_foundation_food_json_2025-12-18.json
en usda_flat_v2.json — schéma state v2 + nutrients imbriqués.

CHANGEMENTS v5.0 → v5.1 (audit scope recettes maison) :
  EXCL_CODES_HARD — 21 FDC IDs ajoutés :
    Jus enrichis/concentrés non-cuisine (9) : apple juice, grape juice ×2,
    cranberry, grapefruit ×2, prune, pomegranate, tart cherry.
    Eggs Grade A Large ×3 : doublons de egg_whole/white/yolk déjà présents.
    Œufs congelés/pasteurisés ×3 : forme industrielle, inutile pour recettes.
    Watermelon rind (1) : pas un ingrédient recette.
    Almonds dry roasted with salt (1) : snack, raw déjà présent.
    Sunflower kernels dry roasted with salt (1) : idem.
    Beans kidney + peas green avec sugar added (3) : reformulés.
  GROUP_KEY_OVERRIDES — 7 corrections de clés dégénérées :
    milk_with  → milk_nonfat        (lait écrémé,    fdc=746776)
    milk_2     → milk_reduced_fat   (lait demi-écrémé, fdc=746778)
    milk_3_25  → milk_whole         (lait entier,    fdc=746782)
    seeds (sunflower raw) → seeds_sunflower  (fdc=2515381)
    seeds (pumpkin)       → seeds_pumpkin    (fdc=2515380)
    chickpeas_garbanzo_beans_bengal_gram → chickpeas  (dry fdc=2644282,
                                                       canned fdc=2644288)
  extract_nutrients — recalcul Atwater quand nid 1008/2048/2047 absent :
    Foundation Foods récents ne publient pas l'énergie directement.
    Résout 38 items restants sans kcal dans le périmètre végétarien.
    Priorité 1 : fat×9 + protein×4 + carbs×4 (macros complets).
    Priorité 2 : (sat+mono+poly)×9 quand fat_g absent (huiles).
    Après fix : 1 seul item sans kcal = sel de table (correct : 0 kcal).
    Champ _energy_source="atwater_recalc" ajouté pour traçabilité.

CHANGEMENTS v4.x → v5.0 (alignement schéma variant v2) :
  - state : objet imbriqué { process: { level1, level2, ... } }
  - variant_id : hash déterministe SHA-1
  - nutrients : structure imbriquée + champs plats rétrocompat
  - Délégation totale à food_schema_v2 (source unique de vérité)
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ====================== FIX IMPORT food_schema_v2 ======================
# Résout le ModuleNotFoundError quand on lance depuis scripts/nutrition/
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_NUTRITION_DIR = SCRIPT_DIR.parent.parent / "backend" / "data" / "nutrition"

if str(BACKEND_NUTRITION_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_NUTRITION_DIR))
# ======================================================================

from food_schema_v2 import (
    compute_variant_id,
    parse_state_v2,
    build_nutrients_object,
    build_diet_profile,
    state_variant_key,
    slugify,
    build_variant_tree,
    detect_extra_dimensions,
    round_nutrients,
    BASE_INGREDIENT_MAP,
)


# ============================================================================
# 1. NUTRIENT DEFS — alignement CIQUAL
# ============================================================================
NUTRIENT_DEFS: list[tuple[int, str, float]] = [
    (1062, "energy_kj",   1.0),
    (1008, "energy_kcal", 1.0),
    (2048, "energy_kcal", 1.0),
    (2047, "energy_kcal", 1.0),
    (1051, "water_g",     1.0),
    (1003, "protein_g",   1.0),
    (1005, "carbs_g",     1.0),
    (1004, "fat_g",       1.0),
    (1063, "sugar_g",     1.0),
    (2000, "sugar_g",     1.0),
    (1009, "starch_g",    1.0),
    (1079, "fiber_g",     1.0),
    (1007, "ash_g",       1.0),
    (1018, "alcohol_g",   1.0),
    (1012, "fructose_g",   1.0),
    (1075, "galactose_g",  1.0),
    (1011, "glucose_g",    1.0),
    (1013, "lactose_g",    1.0),
    (1014, "maltose_g",    1.0),
    (1010, "saccharose_g", 1.0),
    (1258, "fa_saturated_g", 1.0),
    (1292, "fa_mufa_g",      1.0),
    (1293, "fa_pufa_g",      1.0),
    (1259, "fa_4_0_g",  1.0),
    (1260, "fa_6_0_g",  1.0),
    (1261, "fa_8_0_g",  1.0),
    (1262, "fa_10_0_g", 1.0),
    (1263, "fa_12_0_g", 1.0),
    (1264, "fa_14_0_g", 1.0),
    (1265, "fa_16_0_g", 1.0),
    (1266, "fa_18_0_g", 1.0),
    (1315, "fa_18_1_oleic_g",    1.0),
    (1316, "fa_18_2_linoleic_g", 1.0),
    (1404, "fa_18_3_ala_g",      1.0),
    (1271, "fa_20_4_ara_g",      1.0),
    (1278, "fa_20_5_epa_g",      1.0),
    (1272, "fa_22_6_dha_g",      1.0),
    (1253, "cholesterol_mg",     1.0),
    (1087, "calcium_mg",    1.0),
    (1098, "copper_mg",     1.0),
    (1089, "iron_mg",       1.0),
    (1100, "iodine_ug",     1.0),
    (1090, "magnesium_mg",  1.0),
    (1101, "manganese_mg",  1.0),
    (1091, "phosphorus_mg", 1.0),
    (1092, "potassium_mg",  1.0),
    (1103, "selenium_ug",   1.0),
    (1093, "sodium_mg",     1.0),
    (1095, "zinc_mg",       1.0),
    (1106, "vitamin_a_rae_ug",    1.0),
    (1105, "retinol_ug",          1.0),
    (1107, "beta_carotene_ug",    1.0),
    (1114, "vitamin_d_ug",        1.0),
    (1110, "vitamin_d_ug",        0.025),
    (1111, "vitamin_d2_ug",       1.0),
    (1112, "vitamin_d3_ug",       1.0),
    (1109, "alpha_tocopherol_mg", 1.0),
    (1109, "vitamin_e_mg",        1.0),
    (1185, "vitamin_k1_ug",       1.0),
    (1183, "vitamin_k2_ug",       1.0),
    (1162, "vitamin_c_mg",        1.0),
    (1165, "vitamin_b1_mg",       1.0),
    (1166, "vitamin_b2_mg",       1.0),
    (1167, "vitamin_b3_mg",       1.0),
    (1170, "vitamin_b5_mg",       1.0),
    (1175, "vitamin_b6_mg",       1.0),
    (1177, "folate_ug",           1.0),
    (1178, "vitamin_b12_ug",      1.0),
    (1180, "choline_mg",          1.0),
]

CIQUAL_ABSENT = [
    "energy_kj_jones", "energy_kcal_jones",
    "protein_n625_g", "polyols_g", "organic_acids_g",
    "chloride_mg", "folate_dfe_ug", "folate_intrinsic_ug", "folic_acid_ug",
]

_ALL_NUTRIENT_FIELDS: list[str] = []
_seen_for_list: set[str] = set()
for _id, _field, _conv in NUTRIENT_DEFS:
    if _field not in _seen_for_list:
        _ALL_NUTRIENT_FIELDS.append(_field)
        _seen_for_list.add(_field)
for _field in CIQUAL_ABSENT:
    if _field not in _seen_for_list:
        _ALL_NUTRIENT_FIELDS.append(_field)
        _seen_for_list.add(_field)
_ALL_NUTRIENT_FIELDS.append("salt_g")

SALT_SODIUM_RATIO = 2.542

_COMPLETENESS_FIELDS: list[str] = [
    "energy_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "water_g",
    "sodium_mg", "calcium_mg", "iron_mg",
    "vitamin_c_mg", "folate_ug", "vitamin_d_ug",
    "fa_saturated_g", "fa_18_3_ala_g",
]


# ============================================================================
# 2. USDA EXTRA DEFS
# ============================================================================
USDA_EXTRA_DEFS: list[tuple[int, str, float]] = [
    (1176, "biotin_ug",             1.0),
    (1257, "fa_trans_g",            1.0),
    (1082, "fiber_soluble_g",       1.0),
    (1084, "fiber_insoluble_g",     1.0),
    (1071, "starch_resistant_g",    1.0),
    (1002, "nitrogen_g",            1.0),
    (1122, "lycopene_ug",           1.0),
    (1123, "lutein_zeaxanthin_ug",  1.0),
    (1108, "alpha_carotene_ug",     1.0),
    (1210, "aa_tryptophan_g",    1.0),
    (1211, "aa_threonine_g",     1.0),
    (1212, "aa_isoleucine_g",    1.0),
    (1213, "aa_leucine_g",       1.0),
    (1214, "aa_lysine_g",        1.0),
    (1215, "aa_methionine_g",    1.0),
    (1217, "aa_phenylalanine_g", 1.0),
    (1219, "aa_valine_g",        1.0),
    (1220, "aa_arginine_g",      1.0),
    (1221, "aa_histidine_g",     1.0),
    (1288, "phytosterol_beta_sitosterol_mg", 1.0),
    (1285, "phytosterol_stigmasterol_mg",    1.0),
    (1286, "phytosterol_campesterol_mg",     1.0),
    (1340, "isoflavone_daidzein_mg",  1.0),
    (1341, "isoflavone_genistein_mg", 1.0),
]


# ============================================================================
# 3. RÈGLES D'EXCLUSION
# ============================================================================
EXCL_CATEGORIES_HARD: set[str] = {
    "Beef Products", "Poultry Products", "Pork Products",
    "Finfish and Shellfish Products", "Lamb, Veal, and Game Products",
    "Sausages and Luncheon Meats", "Restaurant Foods",
    "Baked Products", "Soups, Sauces, and Gravies",
}

EXCL_CODES_HARD: set[int] = {
    # ── Jus enrichis/concentrés — pas des ingrédients de cuisine ─────────────
    2003590,  # Apple juice, with added vitamin C, from concentrate
    2003592,  # Grape juice, purple, with added vitamin C, from concentrate
    2003593,  # Grape juice, white, with added vitamin C, from concentrate
    2003594,  # Cranberry juice, not fortified, from concentrate
    325287,   # Grapefruit juice, white, canned or bottled, unsweetened
    2003595,  # Grapefruit juice, red, not fortified, not from concentrate
    2727587,  # Juice, prune, shelf-stable         (group_key dégénéré = "juice")
    2727588,  # Juice, pomegranate, from concentrate  (idem)
    2727589,  # Juice, tart cherry, from concentrate  (idem)
    # ── Eggs, Grade A, Large — doublons de egg_whole/egg_white/egg_yolk ──────
    747997,   # Eggs, Grade A, Large, egg white
    748236,   # Eggs, Grade A, Large, egg yolk
    748967,   # Eggs, Grade A, Large, egg whole
    # ── Œufs congelés/pasteurisés — forme industrielle hors recettes maison ──
    323604,   # Egg, whole, raw, frozen, pasteurized
    323697,   # Egg, white, raw, frozen, pasteurized
    329596,   # Egg, yolk, raw, frozen, pasteurized
    # ── Watermelon rind — pas un ingrédient recette standard ─────────────────
    2747676,  # Watermelon, seedless, rind only, raw
    # ── Noix/graines grillées salées — snacks, forme raw déjà présente ───────
    323294,   # Nuts, almonds, dry roasted, with salt added
    325524,   # Seeds, sunflower seed kernels, dry roasted, with salt added
    # ── Légumineuses avec sucre ajouté — reformulées ──────────────────────────
    2644289,  # Beans, kidney, dark red, canned, sodium added, sugar added
    2644290,  # Beans, kidney, light red, canned, sodium added, sugar added
    2644291,  # Peas, green, sweet, canned, sodium added, sugar added
}

# Corrections de group_keys dégénérés générés par build_usda_group_key.
# Clé : fdc_id → group_key corrigé.
GROUP_KEY_OVERRIDES: dict[int, str] = {
    # Laits (clés trop courtes issues du truncate automatique)
    746776:   "milk_nonfat",         # Milk, nonfat, fluid → était "milk_with"
    746778:   "milk_reduced_fat",    # Milk, reduced fat, 2% milkfat → était "milk_2"
    746782:   "milk_whole",          # Milk, whole, 3.25% milkfat → était "milk_3_25"
    # Graines (3 items partageaient le même group_key "seeds")
    2515381:  "seeds_sunflower",     # Seeds, sunflower seed, kernel, raw
    2515380:  "seeds_pumpkin",       # Seeds, pumpkin seeds (pepitas), raw
    # Légumineuses (group_key trop long généré par slugify)
    2644282:  "chickpeas",           # Chickpeas, dry → était "chickpeas_garbanzo_beans_bengal_gram"
    2644288:  "chickpeas",           # Chickpeas, canned → idem
}

COMPOSITE_NAME_RE: list[re.Pattern] = [re.compile(p, re.I) for p in [
    r"\bcommercially\s+prepared\b", r"\bcommercial\b", r"\bpasteurized\s+process\b",
    r"\brestaurant\b", r"\bwith\s+additives\b", r"\bsweet\s+and\s+sour\b",
    r"\bfried\s+rice\b", r"\btamale\b|\bpupusa\b", r"\bsweetened\b",
    r"\bstrawberry\b|\bchocolate\s+flavor", r"\bbreaded\b",
]]


# ============================================================================
# 4. EXTRACTION NUTRIMENTS (inchangée)
# ============================================================================
def extract_nutrients(food: dict) -> tuple[dict, dict, dict, dict]:
    nut_by_id: dict[int, dict] = {
        n["nutrient"]["id"]: n for n in food.get("foodNutrients", [])
    }

    nutrients: dict = {}
    detection_limits: dict = {}
    seen_fields: set = set()
    total_nuts = 0
    analytical_count = 0
    max_dp = 0
    median_used_count = 0

    for (usda_id, field, conv) in NUTRIENT_DEFS:
        if field in seen_fields:
            continue
        n = nut_by_id.get(usda_id)
        if n is None:
            continue
        dp = n.get("dataPoints", 0) or 0
        median = n.get("median")
        amount = n.get("amount")
        if dp > 1 and median is not None:
            val = median * conv
            median_used_count += 1
        elif amount is not None:
            val = amount * conv
        else:
            continue
        nutrients[field] = round(val, 6) if val else val
        seen_fields.add(field)
        total_nuts += 1
        if dp > max_dp:
            max_dp = dp
        deriv = n.get("foodNutrientDerivation", {}).get("code", "?")
        if deriv in ("A", "AS"):
            analytical_count += 1

    if "sodium_mg" in nutrients and nutrients["sodium_mg"] is not None:
        nutrients["salt_g"] = round(nutrients["sodium_mg"] / 1000 * SALT_SODIUM_RATIO, 4)

    # ── v5.1 : recalcul Atwater quand nid 1008/2048/2047 absent ─────────────
    _atwater_recalc = False
    if nutrients.get("energy_kcal") is None:
        prot  = nutrients.get("protein_g")
        carbs = nutrients.get("carbs_g")
        fat   = nutrients.get("fat_g")
        if fat is None:
            sat  = nutrients.get("fa_saturated_g")
            mufa = nutrients.get("fa_mufa_g")
            pufa = nutrients.get("fa_pufa_g")
            if sat is not None and mufa is not None and pufa is not None:
                fat = round(sat + mufa + pufa, 4)
                nutrients["fat_g"] = fat
        if fat is not None or prot is not None or carbs is not None:
            kcal = round(
                (fat   or 0.0) * 9.0
              + (prot  or 0.0) * 4.0
              + (carbs or 0.0) * 4.0,
                1
            )
            if kcal > 0:
                nutrients["energy_kcal"] = kcal
                nutrients["energy_kj"]   = round(kcal * 4.184, 1)
                _atwater_recalc = True

    for field in CIQUAL_ABSENT:
        if field not in nutrients:
            nutrients[field] = None

    extra: dict = {}
    seen_extra: set = set()
    for (usda_id, field, conv) in USDA_EXTRA_DEFS:
        if field in seen_extra:
            continue
        n = nut_by_id.get(usda_id)
        if n is None:
            continue
        dp = n.get("dataPoints", 0) or 0
        median = n.get("median")
        amount = n.get("amount")
        val = (median * conv if (dp > 1 and median is not None)
               else (amount * conv if amount is not None else None))
        if val is not None:
            extra[field] = round(val, 6) if val else val
            seen_extra.add(field)

    anal_pct = round(analytical_count / total_nuts, 3) if total_nuts else 0.0
    confidence = 0.60
    if anal_pct >= 0.80:
        confidence += 0.15
    elif anal_pct >= 0.50:
        confidence += 0.08
    if max_dp >= 10:
        confidence += 0.15
    elif max_dp >= 5:
        confidence += 0.10
    elif max_dp >= 2:
        confidence += 0.05
    confidence = round(min(confidence, 1.0), 3)

    quality = {
        "source": "usda_foundation_2025",
        "source_id": food.get("fdcId"),
        "data_points_max": max_dp,
        "median_used": median_used_count,
        "total_nutrients": total_nuts,
        "analytical_pct": anal_pct,
        "confidence": confidence,
        "portions_count": None,
    }

    return nutrients, detection_limits, extra, quality


# ============================================================================
# 5. AUDIT (inchangé)
# ============================================================================
ENERGY_FACTORS_KJ = {
    "protein_g": 17, "carbs_g": 17, "fat_g": 37,
    "fiber_g": 8, "alcohol_g": 29, "polyols_g": 10,
}
MASS_BALANCE_WARN_G = 15.0
MASS_BALANCE_ERR_G  = 30.0
ENERGY_TOLERANCE    = 0.20
FA_BALANCE_TOL      = 0.10

SEVERITY_CLASS: dict[str, str] = {
    "negative_values": "physical_error",
    "sugar_vs_carbs": "physical_error",
    "energy_check": "data_quality",
    "fa_balance": "major_quality",
    "sugar_subfractions": "major_quality",
    "salt_sodium": "data_quality",
    "mass_balance": "physical_error",
    "omega_vs_pufa": "data_quality",
    "vit_d_subforms": "data_quality",
    "vit_e_tocopherol": "data_quality",
}

def get_severity_class(check: str, severity: str) -> str:
    if check == "mass_balance":
        return "physical_error" if severity == "error" else "major_quality"
    return SEVERITY_CLASS.get(check, "info")


def run_audit(name_en, fdc_id, food_id, nutrients, by_check, all_issues):
    issues: list[dict] = []
    def flag(check, sev, msg, **kw):
        sev_class = get_severity_class(check, sev)
        issue = {"severity_class": sev_class, "severity": sev, "check": check, "message": msg}
        if kw:
            issue.update(kw)
        issues.append(issue)
        all_issues.append({"id": food_id, "source_id": fdc_id, "name_en": name_en, **issue})
        by_check[check][sev + "s"] = by_check[check].get(sev + "s", 0) + 1

    def g(f):
        return nutrients.get(f)

    for field, val in nutrients.items():
        if val is not None and val < -0.001:
            flag("negative_values", "error", f"Valeur négative : {field} = {val}")

    sug = g("sugar_g"); carbs = g("carbs_g")
    if sug is not None and carbs is not None and sug > carbs + 0.5:
        flag("sugar_vs_carbs", "error", f"sugar_g={sug} > carbs_g={carbs}")

    dry_basis = "(0% moisture)" in name_en or "dry weight basis" in name_en.lower()
    if dry_basis:
        flag("mass_balance", "info", "Base sèche — mass_balance non applicable.")
    else:
        if nutrients.get("carbs_g") is not None:
            components = ["water_g", "protein_g", "fat_g", "carbs_g", "ash_g", "alcohol_g"]
        else:
            components = ["water_g", "protein_g", "fat_g", "fiber_g", "ash_g", "alcohol_g"]
        vals = [g(f) for f in components if g(f) is not None]
        if len(vals) >= 4:
            total = sum(vals)
            delta = abs(100.0 - total)
            if delta > MASS_BALANCE_ERR_G:
                flag("mass_balance", "error", f"Sigma macros={total:.1f} g/100g (écart={delta:.1f}g)", delta_pct=round(delta, 1))
            elif delta > MASS_BALANCE_WARN_G:
                flag("mass_balance", "warning", f"Sigma macros={total:.1f} g/100g (écart={delta:.1f}g)", delta_pct=round(delta, 1))

    e_decl_kj = g("energy_kj")
    e_decl_kcal = g("energy_kcal")
    if not e_decl_kj and e_decl_kcal:
        e_decl_kj = e_decl_kcal * 4.184
    if e_decl_kj and e_decl_kj > 0:
        e_calc = sum((g(f) or 0.0) * factor for f, factor in ENERGY_FACTORS_KJ.items() if g(f) is not None)
        if e_calc > 0:
            delta_pct = abs(e_decl_kj - e_calc) / e_decl_kj
            if delta_pct > ENERGY_TOLERANCE:
                flag("energy_check", "warning",
                     f"Energie déclarée={e_decl_kj:.0f} kJ vs calculée={e_calc:.1f} kJ (delta={delta_pct*100:.1f}%)",
                     delta_pct=round(delta_pct * 100, 1))

    fat = g("fat_g"); sfa = g("fa_saturated_g"); mufa = g("fa_mufa_g"); pufa = g("fa_pufa_g")
    if fat and sfa is not None and mufa is not None and pufa is not None:
        total_fa = sfa + mufa + pufa
        if total_fa > fat * (1 + FA_BALANCE_TOL) + 0.1:
            flag("fa_balance", "warning", f"SFA+MUFA+PUFA={total_fa:.2f} > fat_g={fat:.2f}")

    salt = g("salt_g"); na = g("sodium_mg")
    if salt is not None and na is not None and na > 0:
        expected_salt = na / 1000 * SALT_SODIUM_RATIO
        if expected_salt > 0:
            delta = abs(salt - expected_salt) / expected_salt
            if delta > 0.15:
                flag("salt_sodium", "warning",
                     f"salt_g={salt:.3f} vs Na×2.542={expected_salt:.3f} (delta={delta*100:.1f}%)")

    ala = g("fa_18_3_ala_g") or 0
    epa = g("fa_20_5_epa_g") or 0
    dha = g("fa_22_6_dha_g") or 0
    if pufa and pufa > 0:
        omega3 = ala + epa + dha
        linol = g("fa_18_2_linoleic_g") or 0
        if (omega3 + linol) > pufa * 1.10 + 0.1:
            flag("omega_vs_pufa", "warning", f"Σ oméga3+linol={omega3+linol:.3f} > fa_pufa={pufa:.3f}")

    vd = g("vitamin_d_ug"); vd2 = g("vitamin_d2_ug"); vd3 = g("vitamin_d3_ug")
    if vd and vd2 is not None and vd3 is not None:
        if (vd2 + vd3) > vd * 1.05 + 0.01:
            flag("vit_d_subforms", "warning", f"D2+D3={vd2+vd3:.2f} > vitamin_d_ug={vd:.2f}")

    n_physical = sum(1 for i in issues if i["severity_class"] == "physical_error")
    n_major = sum(1 for i in issues if i["severity_class"] == "major_quality")
    n_dq = sum(1 for i in issues if i["severity_class"] == "data_quality")
    score = {
        "physical_errors": n_physical,
        "major_quality": n_major,
        "data_quality": n_dq,
        "total": len(issues),
        "usable": n_physical == 0,
    }
    return issues, score


def compute_quality_score(quality_meta, audit_score, nutrients):
    anal_pct = quality_meta.get("analytical_pct", 0.0)
    anal_comp = anal_pct * 0.35
    present = sum(1 for f in _COMPLETENESS_FIELDS if nutrients.get(f) is not None)
    comp_score = (present / len(_COMPLETENESS_FIELDS)) * 0.35
    n_physical = audit_score.get("physical_errors", 0)
    n_major = audit_score.get("major_quality", 0)
    n_dq = audit_score.get("data_quality", 0)
    if n_physical > 0:
        audit_comp = 0.0
    else:
        penalty = min(n_major * 0.05 + n_dq * 0.01, 0.30)
        audit_comp = round(0.30 - penalty, 4)
    return round(min(anal_comp + comp_score + audit_comp, 1.0), 3)


# ============================================================================
# 6. EXCLUSION (inchangé)
# ============================================================================
def should_exclude(fdc_id: int, category: str, description: str) -> tuple[bool, str]:
    if category in EXCL_CATEGORIES_HARD:
        return True, f"category:{category}"
    if fdc_id in EXCL_CODES_HARD:
        return True, "code:hard"
    for pat in COMPOSITE_NAME_RE:
        if pat.search(description):
            return True, f"composite_name:{pat.pattern[:40]}"
    return False, ""


# ============================================================================
# 7. CATÉGORIE UNIFIÉE (inchangé)
# ============================================================================
_USDA_CATEGORY_MAP: dict[str, tuple] = {
    "Vegetables and Vegetable Products": ("légumes et produits végétaux", "usda_1.0", None, "usda_1.1"),
    "Fruits and Fruit Juices": ("fruits et jus de fruits", "usda_2.0", None, "usda_2.1"),
    "Nut and Seed Products": ("noix, graines et oléagineux", "usda_3.0", None, "usda_3.1"),
    "Legumes and Legume Products": ("légumineuses et dérivés", "usda_4.0", None, "usda_4.1"),
    "Cereal Grains and Pasta": ("céréales, grains et pâtes", "usda_5.0", None, "usda_5.1"),
    "Dairy and Egg Products": ("produits laitiers et œufs", "usda_6.0", None, "usda_6.1"),
    "Fats and Oils": ("matières grasses et huiles", "usda_7.0", None, "usda_7.1"),
    "Spices and Herbs": ("épices et herbes aromatiques", "usda_8.0", None, "usda_8.1"),
    "Beverages": ("boissons", "usda_9.0", None, "usda_9.1"),
    "Sweets": ("sucreries et confiseries", "usda_10.0", None, "usda_10.1"),
    "Snacks": ("snacks et apéritifs", "usda_11.0", None, "usda_11.1"),
    "Breakfast Cereals": ("céréales petit-déjeuner", "usda_12.0", None, "usda_12.1"),
    "Baby Foods": ("aliments pour bébés", "usda_13.0", None, "usda_13.1"),
    "Meals, Entrees, and Side Dishes": ("plats préparés", "usda_14.0", None, "usda_14.1"),
    "Fast Foods": ("restauration rapide", "usda_15.0", None, "usda_15.1"),
}
_USDA_CATEGORY_DEFAULT = (None, "usda_0.0", None, "usda_0.1")

def build_unified_category(usda_category: str) -> dict:
    l1_fr, l1_code, l2_fr, l2_code = _USDA_CATEGORY_MAP.get(usda_category, _USDA_CATEGORY_DEFAULT)
    return {
        "level1_fr": l1_fr, "level1_en": usda_category, "level1_code": l1_code,
        "level2_fr": l2_fr, "level2_code": l2_code,
        "level3_fr": None, "level3_code": None,
    }


# ============================================================================
# 8. UTILITAIRES (inchangé)
# ============================================================================
_PAREN_RE = re.compile(r"\([^)]*\)")

GENERIC_USDA_PREFIXES: set[str] = {
    "oil", "beans", "bean", "flour", "cheese", "milk", "nuts", "butter",
    "cream", "yogurt", "mushroom", "mushrooms", "pepper", "peppers",
    "squash", "lettuce", "cabbage", "apple", "apples", "tomato", "tomatoes",
    "potato", "potatoes", "onion", "onions", "corn", "spinach", "broccoli",
    "carrot", "carrots", "egg", "eggs", "rice", "wheat", "berries", "berry",
    "beans dry",
}

_STATE_STOP_SLUGS: set[str] = {
    slugify(s) for s in [
        "dry", "dried", "raw", "cooked", "fresh", "frozen", "canned",
        "whole", "plain", "fluid", "unsweetened", "refrigerated",
        "low fat", "nonfat", "full fat", "fat free", "reduced fat",
        "boiled", "steamed", "grilled", "roasted", "fried",
        "uncooked", "unprepared", "pasteurized", "dehydrated",
    ]
}

def _split_usda_parts(description: str) -> list[str]:
    parts: list[str] = []; current: list[str] = []; depth = 0
    for ch in description:
        if ch == "(": depth += 1; current.append(ch)
        elif ch == ")": depth -= 1; current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip()); current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]

def build_usda_group_key(description: str) -> tuple[str, str]:
    parts = _split_usda_parts(description)
    if not parts:
        return slugify(description)[:80], description
    first = parts[0].strip()
    first_lower = first.lower()
    if first_lower in GENERIC_USDA_PREFIXES and len(parts) >= 2:
        for second in parts[1:]:
            second_clean = _PAREN_RE.sub("", second).strip()
            s_slug = slugify(second_clean)
            if s_slug and s_slug not in _STATE_STOP_SLUGS:
                key_part = second_clean.split()[0] if second_clean.split() else second_clean
                base_name = f"{first}, {second_clean}"
                return slugify(f"{first} {key_part}"), base_name
        second_clean = _PAREN_RE.sub("", parts[1]).strip()
        key_part = second_clean.split()[0] if second_clean.split() else second_clean
        base_name = f"{first}, {second_clean}"
        return slugify(f"{first} {key_part}"), base_name
    return slugify(first), first



# ============================================================================
# 9. BUILD PRINCIPAL
# ============================================================================
def build(input_path: Path, output_path: Path,
          audit_path: Path | None = None, excl_path: Path | None = None,
          dry_run: bool = False) -> None:

    ts = datetime.now(timezone.utc).isoformat()
    print(f"\n[1/6] Lecture {input_path}...")

    with open(input_path, encoding="utf-8") as f:
        raw = json.load(f)
    source_foods = raw["FoundationFoods"]
    print(f"    {len(source_foods)} aliments dans la source USDA Foundation.")

    stats: dict = defaultdict(int)
    stats["total_usda"] = len(source_foods)
    excluded: list[dict] = []; all_issues: list[dict] = []
    by_check: dict = defaultdict(lambda: defaultdict(int))

    print("\n[2/6] Filtrage + extraction...")
    foods: list[dict] = []

    for raw_food in source_foods:
        fdc_id = raw_food.get("fdcId", 0)
        desc = raw_food.get("description", "")
        usda_cat = raw_food.get("foodCategory", {}).get("description", "Unknown")

        excl_flag, reason = should_exclude(fdc_id, usda_cat, desc)
        if excl_flag:
            excluded.append({"source_id": fdc_id, "name_en": desc,
                             "usda_category": usda_cat, "reason": reason})
            stats[f"excl_{reason.split(':')[0]}"] += 1
            stats["total_excl"] += 1
            continue

        stats["kept"] += 1

        nutrients, dl, extra, quality = extract_nutrients(raw_food)
        group_key, base_name = build_usda_group_key(desc)
        # ── v5.1 : corrections de group_keys dégénérés ──────────────────────
        if fdc_id in GROUP_KEY_OVERRIDES:
            group_key = GROUP_KEY_OVERRIDES[fdc_id]
        food_id = f"usda_{fdc_id}"
        category = build_unified_category(usda_cat)

        # State v2
        state = parse_state_v2(desc, category=usda_cat, lang="en")
        rules_fired = state.pop("_rules_fired", [])
        variant_key_str = state_variant_key(state)
        variant_id = compute_variant_id(food_id, state)

        # Audit
        issues, audit_score = run_audit(desc, fdc_id, food_id, nutrients, by_check, all_issues)
        quality["quality_score"] = compute_quality_score(quality, audit_score, nutrients)
        quality["state_inference"] = {
            "confidence": state["process"]["confidence"],
            "rules_fired": rules_fired,
            "raw_label": desc,
        }
        quality["created_at"] = ts
        quality["pipeline_version"] = "5.0"

        # Diet profile
        diet = build_diet_profile(desc, nutrients, usda_cat)

        portions = []
        for p in raw_food.get("foodPortions", []):
            mu = p.get("measureUnit", {})
            gw = p.get("gramWeight") or p.get("value")
            if gw:
                portions.append({
                    "unit": mu.get("name", "serving"),
                    "abbr": mu.get("abbreviation", ""),
                    "grams_per_unit": round(gw, 3),
                })
        quality["portions_count"] = len(portions)

        l1 = state["process"]["level1"]
        l2 = state["process"]["level2"]
        stats[f"level1_{l1}"] += 1
        if l2:
            stats[f"level2_{l2}"] += 1

        if audit_score["total"] > 0:
            stats["foods_with_issues"] += 1
        for sc in ("physical_error", "major_quality", "data_quality", "info"):
            stats[f"sevclass_{sc}"] += sum(1 for i in issues if i["severity_class"] == sc)
        for i in issues:
            stats[f"sev_{i['severity']}"] += 1

        # Nutrients structurés (déjà avec kwargs)
        nutrients_obj = build_nutrients_object(
            nutrients,
            extra=extra,
            level1=l1,
            completeness_fields=_COMPLETENESS_FIELDS,
        )

        food_obj = {
            "id": food_id,
            "variant_id": variant_id,
            "food_id": food_id,
            "source": "usda",
            "source_id": fdc_id,
            "name_fr": None,
            "name_en": desc,
            "base_name": base_name,
            "scientific_name": None,
            "group_key": group_key,
            "variant_key": variant_key_str,
            "is_generic": False,
            "category": category,
            "diet_profile": diet,
            "refuse_percent": None,
            "jones_factor": None,
            "detection_limits": dl,
            "portions": portions,
            "nutrients": nutrients_obj,
            **nutrients,
            "_usda_extra": extra if extra else None,
            # ── Dépliage _usda_extra vers le niveau racine (v6) ─────────────
            # CRITIQUE (ISSUE-7) : build_ontology_v6 → extract_usda() lit tous
            # les nutriments directement au top-level (food.get("selenium_ug"),
            # food.get("iodine_ug"), food.get("choline_mg")…).
            # Point 1 : **nutrients ci-dessus spread TOUS les champs NUTRIENT_DEFS,
            #   incluant selenium_ug (id 1103), iodine_ug (id 1100), vitamines B.
            #   → Couverture faible pour ces champs = lacune USDA Foundation Foods,
            #     pas un bug pipeline. La source ne mesure pas tout.
            # Point 2 : les champs USDA_EXTRA_DEFS absents de NUTRIENT_DEFS
            #   (fa_trans_g, fiber_soluble_g, biotin_ug, lycopene_ug…)
            #   ne sont pas dans **nutrients → ce spread secondaire les remonte.
            # Point 3 : guard nutrients.get(k) is None évite double-écriture.
            **{
                k: v for k, v in (extra or {}).items()
                if k in (
                    "choline_mg", "fa_trans_g", "fiber_soluble_g",
                    "fiber_insoluble_g", "biotin_ug", "lycopene_ug",
                    "lutein_zeaxanthin_ug",
                )
                and v is not None
                and nutrients.get(k) is None  # ne pas écraser si déjà présent
            },
            "_flat_schema_version": "5.1",  # sentinel pour vérification par extract_usda
            "quality_score": quality["quality_score"],
            "_quality": quality,
            "_audit_score": audit_score,
            "_audit_issues": issues if issues else None,
            "state": state,
        }
        foods.append(food_obj)

    print(f"    Retenus : {stats['kept']} | Exclus : {stats['total_excl']}")
    print(f"\n[3/6] Construction groupes/variants (arbre multi-level)...")

    base_groups: dict[str, list] = defaultdict(list)
    for food in foods:
        entry = BASE_INGREDIENT_MAP.get(food["group_key"], {})
        base_key = entry.get("base_key", food["group_key"])
        extra_dims = entry.get("extra_dims", {})
        for dim, val in extra_dims.items():
            if dim in ("process.level1", "process.level2"):
                continue
            if food["state"].get(dim) is None:
                food["state"][dim] = val
        base_groups[base_key].append(food)

    groups: dict = {}
    for base_key, base_foods in base_groups.items():
        entry = BASE_INGREDIENT_MAP.get(base_foods[0]["group_key"], {})
        name_fr = entry.get("name_fr")
        name_en = entry.get("name_en") or base_foods[0].get("base_name") or base_key
        category = base_foods[0].get("category", {})

        groups[base_key] = build_variant_tree(
            foods=base_foods,
            base_key=base_key,
            name_fr=name_fr,
            name_en=name_en,
            category=category,
            source_name="usda",
        )

    conflicts: list[dict] = []
    stats["total_groups"] = len(groups)
    stats["multi_variant_groups"] = sum(
        1 for g in groups.values() if g["_meta"]["leaf_count"] > 1
    )
    stats["total_conflicts"] = 0

    print(f"    {stats['total_groups']} groupes | {stats['multi_variant_groups']} multi-variants")

    print("\n[4/6] Rapport...")
    print(f"    Total USDA Foundation   : {stats['total_usda']:>5}")
    print(f"    Total exclus            : {stats['total_excl']:>5}")
    print(f"    Conservés               : {stats['kept']:>5}")
    print(f"\n    --- État process (level1) ---")
    for key in ("level1_raw", "level1_cooked", "level1_unknown"):
        print(f"    {key:<35} : {stats.get(key,0):>5}")
    unknown_rate = stats.get("level1_unknown", 0) / max(stats["kept"], 1) * 100
    print(f"    unknown_rate            : {unknown_rate:.1f}%")
    print(f"\n    --- Top level2 ---")
    l2_counts = sorted(
        ((k.replace("level2_",""), v) for k,v in stats.items() if k.startswith("level2_")),
        key=lambda x: -x[1]
    )
    for l2, cnt in l2_counts[:12]:
        print(f"      {l2:<30} : {cnt:>5}")
    print(f"\n    --- Audit ---")
    print(f"    Avec issues             : {stats['foods_with_issues']:>5}")
    print(f"    physical_error          : {stats.get('sevclass_physical_error',0):>5}")
    print(f"    major_quality           : {stats.get('sevclass_major_quality',0):>5}")

    if dry_run:
        print("\n[DRY-RUN] Aucune écriture.")
        return

    print("\n[5/6] Sérialisation...")

    foods_flat = []
    for food in foods:
        flat = {
            "id":          food["id"],
            "variant_id":  food["variant_id"],
            "source":      "usda",
            "source_id":   food["source_id"],
            "name_fr":     None,
            "name_en":     food["name_en"],
            "base_name":   food["base_name"],
            "scientific_name": None,
            "group_key":   food["group_key"],
            "variant_key": food["variant_key"],
            "is_generic":  False,
            "category":    food["category"],
            "state":       food["state"],
            "diet_profile":food["diet_profile"],
            "refuse_percent":   None,
            "jones_factor":     None,
            "detection_limits": food.get("detection_limits", {}),
            "portions":         food["portions"],
            "nutrients":        food["nutrients"],
            "_usda_extra": food.get("_usda_extra"),
            "quality_score": food["quality_score"],
            "_quality":      food["_quality"],
            "_audit_score":  food["_audit_score"],
            "_audit_issues": food.get("_audit_issues"),
        }
        flat.update({k: v for k, v in food.items()
                     if k in _ALL_NUTRIENT_FIELDS and k not in flat})
                     
        n = food.get("nutrients", {})
        mins = n.get("minerals", {})
        vits = n.get("vitamins", {})
        lps  = n.get("lipids", {})
        carbs = n.get("carbohydrates", {})
        
        flat.update({
            "selenium_ug":       mins.get("selenium_mcg", flat.get("selenium_ug")),
            "iodine_ug":         mins.get("iodine_mcg", flat.get("iodine_ug")),
            "vitamin_a_rae_ug":  vits.get("a_rae_mcg", flat.get("vitamin_a_rae_ug")),
            "vitamin_b12_ug":    vits.get("b12_mcg", flat.get("vitamin_b12_ug")),
            "vitamin_b5_mg":     vits.get("b5_mg", flat.get("vitamin_b5_mg")),
            "vitamin_d_ug":      vits.get("d_mcg", flat.get("vitamin_d_ug")),
            "retinol_ug":        vits.get("retinol_mcg", flat.get("retinol_ug")),
            "beta_carotene_ug":  vits.get("beta_carotene_mcg", flat.get("beta_carotene_ug")),
            "fa_saturated_g":    lps.get("saturated_g", flat.get("fa_saturated_g")),
            "fa_mufa_g":         lps.get("monounsaturated_g", flat.get("fa_mufa_g")),
            "fa_pufa_g":         lps.get("polyunsaturated_g", flat.get("fa_pufa_g")),
            "fa_18_3_ala_g":     lps.get("fa_18_3_ala_g", flat.get("fa_18_3_ala_g")),
            "fa_20_5_epa_g":     lps.get("fa_20_5_epa_g", flat.get("fa_20_5_epa_g")),
            "fa_22_6_dha_g":     lps.get("fa_22_6_dha_g", flat.get("fa_22_6_dha_g")),
            "cholesterol_mg":    lps.get("cholesterol_mg", flat.get("cholesterol_mg")),
            "starch_g":          carbs.get("starch_g", flat.get("starch_g")),
            "sugar_g":           carbs.get("sugars_g", flat.get("sugar_g")),
            "alcohol_g":         n.get("macros", {}).get("alcohol_g", flat.get("alcohol_g")),
        })
        
        for k in list(flat.keys()):
            if flat[k] is None:
                del flat[k]
                
        for f in _ALL_NUTRIENT_FIELDS:
            if f not in flat:
                flat[f] = None
                
        foods_flat.append(flat)

    field_source_coverage = {
        f: ([] if f in CIQUAL_ABSENT else ["usda"])
        for f in _ALL_NUTRIENT_FIELDS
    }
    for _f in ("vitamin_d3_ug", "vitamin_k2_ug", "choline_mg"):
        if _f in field_source_coverage:
            field_source_coverage[_f] = ["usda"]

    document = {
        "_meta": {
            "schema_version": "6.0",
            "schema_family":  "unified_food",
            "generated_at":   ts,
            "sources": {
                "usda": {
                    "title": "USDA FoodData Central — Foundation Foods",
                    "url":   "https://fdc.nal.usda.gov/",
                    "file":  input_path.name,
                    "total_foods_in_source": stats["total_usda"],
                }
            },
            "total_foods": stats["kept"],
            "nutrient_fields": _ALL_NUTRIENT_FIELDS,
            "field_source_coverage": field_source_coverage,
            "stats": {
                "total_kept":          stats["kept"],
                "total_excluded":      stats["total_excl"],
                "total_groups":        stats["total_groups"],
                "multi_variant_groups":stats["multi_variant_groups"],
                "variant_conflicts":   stats["total_conflicts"],
                "foods_with_issues":   stats["foods_with_issues"],
                "by_severity_class": {
                    "physical_error": stats.get("sevclass_physical_error", 0),
                    "major_quality":  stats.get("sevclass_major_quality",  0),
                    "data_quality":   stats.get("sevclass_data_quality",   0),
                },
                "state_stats": {
                    "level1_raw":     stats.get("level1_raw", 0),
                    "level1_cooked":  stats.get("level1_cooked", 0),
                    "level1_unknown": stats.get("level1_unknown", 0),
                    "unknown_rate_pct": round(unknown_rate, 1),
                    "top_level2": dict(l2_counts[:15]),
                },
            },
            "schema_notes": {
                "state_v2": (
                    "state = objet { process{level1,level2,confidence,raw_label_fragment}, "
                    "preservation, physical_form, part, additives[], fat_level, fat_pct, "
                    "maturity, pack_medium, dairy_process, variety, cooking_fat }. "
                    "process.level1 ∈ {raw, cooked, unknown}. "
                    "process.level2 = sous-catégorie de cuisson si level1=cooked."
                ),
                "nutrients_v2": (
                    "nutrients = objet imbriqué { energy, macros, lipids, carbohydrates, "
                    "proteins_detail (acides aminés essentiels), vitamins, minerals, "
                    "bioactives, _nutrient_meta }. "
                    "choline_mg déplacé dans vitamins (aligné CNF). "
                    "Champs plats aussi conservés à la racine pour rétrocompat."
                ),
                "variant_id": (
                    "variant_id = SHA-1(food_id + state canonique sérialisé), tronqué 12 chars."
                ),
                "value_strategy": (
                    "Valeur nutriment = median si dataPoints > 1, sinon amount. "
                    "energy_kcal : ID 1008 > 2048 > 2047."
                ),
                "shared_schema": (
                    "parse_state_v2, build_nutrients_object, build_diet_profile, "
                    "compute_variant_id, state_variant_key, slugify "
                    "importés depuis food_schema_v2 (source unique de vérité v2.1)."
                ),
            },
        },
        "groups":            groups,
        "foods_flat":        foods_flat,
        "variant_conflicts": conflicts,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2)
    print(f"    OK {output_path}  ({output_path.stat().st_size / 1_048_576:.1f} Mo)")

    if audit_path:
        audit_doc = {
            "_meta": {
                "schema_version":    "6.0",
                "generated_at":      ts,
                "total_checked":     stats["kept"],
                "foods_with_issues": stats["foods_with_issues"],
                "by_severity_class": {
                    "physical_error": stats.get("sevclass_physical_error", 0),
                    "major_quality":  stats.get("sevclass_major_quality",  0),
                    "data_quality":   stats.get("sevclass_data_quality",   0),
                    "info":           stats.get("sevclass_info",           0),
                },
                "by_check": {k: dict(v) for k, v in by_check.items()},
            },
            "excluded": excluded,
            "issues":   all_issues,
        }
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_doc, f, ensure_ascii=False, indent=2)
        print(f"    OK {audit_path}  ({len(all_issues)} issues | {len(excluded)} exclus)")

    if excl_path and excluded:
        excl_doc = {
            "_meta": {"generated_at": ts, "total_excluded": len(excluded)},
            "excluded": excluded,
        }
        with open(excl_path, "w", encoding="utf-8") as f:
            json.dump(excl_doc, f, ensure_ascii=False, indent=2)
        print(f"    OK {excl_path}  ({len(excluded)} aliments exclus)")

    print("\n[6/6] Terminé.")


# ============================================================================
# 11. POINT D'ENTRÉE
# ============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Transforme FoodData Central Foundation Foods → usda_flat_v2.json v5.0"
    )
    ap.add_argument("--input",        "-i",
                    default="FoodData_Central_foundation_food_json_2025-12-18.json")
    ap.add_argument("--output",       "-o", default="usda_flat_v2.json")
    ap.add_argument("--audit-report",       default=None, metavar="PATH")
    ap.add_argument("--log-excl",           default=None, metavar="PATH")
    ap.add_argument("--dry-run",            action="store_true")
    args = ap.parse_args()

    # ====================== FORCE OUTPUT TO OUTPUTS FOLDER ======================
    TARGET_DIR = Path(r"C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\backend\data\nutrition\outputs")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Input file (try several possible locations)
    BASE_DIR = Path(__file__).resolve().parents[2]
    default_input = BASE_DIR / "backend" / "data" / "nutrition" / "raw" / "FoodData_Central_foundation_food_json_2025-12-18.json"

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = BASE_DIR / args.input
    if not input_path.exists() and "FoodData_Central" in str(args.input):
        input_path = default_input

    if not input_path.exists():
        sys.exit(f"❌ Fichier introuvable : {args.input}\nVérifiez que le JSON USDA est dans le dossier raw/")

    # Force output paths
    output_path = TARGET_DIR / Path(args.output).name
    audit_path = TARGET_DIR / Path(args.audit_report).name if args.audit_report else None
    excl_path = TARGET_DIR / Path(args.log_excl).name if args.log_excl else None

    print(f"📥 Input  : {input_path}")
    print(f"📤 Output : {output_path}")

    build(
        input_path=input_path,
        output_path=output_path,
        audit_path=audit_path,
        excl_path=excl_path,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
