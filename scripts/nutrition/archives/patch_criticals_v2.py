"""
patch_criticals_v2.py
══════════════════════════════════════════════════════════════════════════════
Corrige les 54 erreurs CRITICAL du validator_v11 dans nutrition_patched_v7.json.

Stratégie :
  A. Proposals validées       → champs CIQUAL/USDA corrects (whitelist explicite)
  B. Proposals REJETÉES       → form raw/cooked/dried confondue (blacklist explicite)
  C. Fixes hardcodés          → valeurs connues incontestables
  D. bio_plant_cholesterol    → cholesterol_mg = 0 pour végétaux
  E. energy_mismatch          → recalcul Atwater
  F. lipid_sub_incoherence    → correction fat_g + mise à l'échelle subs OU l'inverse
  G. macro_sum_impossible     → maca fat_g corrigé

Input  : nutrition_patched_v7.json
Outputs: nutrition_patched_v7.json (in-place, backup auto)
         patch_criticals_v2_log.json
══════════════════════════════════════════════════════════════════════════════
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR        = Path(__file__).resolve().parent
NUTRITION_FILE  = BASE_DIR / "nutrition_patched_v7.json"
PROPOSALS_FILE  = BASE_DIR / "correction_proposals.json"
LOG_FILE        = BASE_DIR / "patch_criticals_v2_log.json"

FIELD_MAP = {
    "calories":  "calories_kcal",
    "protein":   "protein_g",
    "fat":       "fat_g",
    "carbs":     "carbs_g",
    "fiber":     "fiber_g",
    "sugar":     "sugar_g",
    "vitamin_c": "vitamin_c_mg",
    "vitamin_a": "vitamin_a_ug",
    "vitamin_d": "vitamin_d_ug",
}

LIPID_SUB_FIELDS = ["saturated_fat_g", "monounsaturated_fat_g", "polyunsaturated_fat_g"]

# ── A. Proposals validées : whitelisted par ingrédient ─────────────────────
# Seuls ces champs sont appliqués depuis correction_proposals.json.
# Raison des rejets dans PROPOSAL_BLACKLIST ci-dessous.
PROPOSAL_WHITELIST: dict[str, list[str]] = {
    "apple":           ["fiber"],
    "bean":            ["fat"],
    "blueberry":       ["calories", "protein", "carbs", "fat"],
    "bulgur":          ["carbs"],
    "carrot":          ["carbs"],
    "cashew":          ["carbs", "fat", "fiber"],
    "cauliflower":     ["calories", "protein", "fat", "fiber", "vitamin_c"],
    "chili_paste":     ["calories", "protein", "carbs"],
    "dried_raisins":   ["calories", "protein", "carbs", "fat", "fiber"],
    "fennel":          ["carbs"],          # fiber rejected (3.1 correct pour fenouil)
    "hazelnut":        ["carbs", "fiber"],
    "lettuce":         ["vitamin_c"],
    "parmesan":        ["carbs"],
    "peach":           ["calories", "carbs"],
    "ricotta":         ["carbs"],
    "zucchini":        ["fat"],
}

# ── B. Raisons des rejets (documentation) ──────────────────────────────────
# egg         : raw egg correct (143 kcal), USDA match = dried egg → reject all
# strawberry  : fiber 3.8 et vitamin_c 58.8 sont CORRECTS, USDA match erroné
# pepper      : poivre noir moulu (251 kcal), USDA match = poivron frais → reject
# pistachio   : 560 kcal correct pour pistache crue, USDA match absurde (15 kcal)
# nutmeg_whole: 525 kcal correct pour noix de muscade, match erroné (20.6 kcal)
# honey       : 304 kcal correct pour miel, match erroné (54 kcal)
# corn        : 72.9 kcal correct maïs frais, CIQUAL match erroné (13.1 kcal)
# grape       : 69 kcal correct raisin frais, match erroné (27 kcal)
# coconut     : 354 kcal correct noix de coco fraîche, match = huile (833 kcal)
# edamame     : 83.3 kcal correct (cuit), match = soja sec (320 kcal)
# chestnut    : 167 kcal correct châtaigne fraîche, match = séchée (385 kcal)
# chickpea    : 164 kcal correct pois chiche cuit, match = sec (350 kcal)
# fig         : 74 kcal correct figue fraîche, match = séchée (249 kcal)
# millet      : 116 kcal correct millet cuit, match = cru sec (381 kcal)
# quinoa      : 168 kcal correct quinoa cuit, match = cru sec (358 kcal)
# mustard     : condiment préparé (61 kcal correct), proposals = moutarde en poudre
# barley      : orge cru hulled OK (354 kcal, fiber 17g), CIQUAL = orge perlée différente
# brussels_sprouts: proposals toutes fausses (19→142 et 19→8 inverses) → hardcoded
# breadcrumbs.fiber: 5.4→0.056 absurde
# cherry.protein: 1.06→0.147 absurde
# grapefruit.fiber: 1.6→0.2 absurde (vrai ~1.6g)
# kale.carbs  : 4.3→0.32 absurde
# maca.carbs  : 71.4 CORRECT pour poudre de maca, proposal 24.1 erroné

# ── C. Fixes hardcodés (valeurs incontestables, source USDA/CIQUAL direct) ──
HARDCODED_FIXES: dict[str, dict] = {
    # strawberry: macros complètement faux dans pv7 (83 kcal, 8g protein!)
    # Source USDA: strawberries raw → 32 kcal, 0.67g prot, 7.68g carbs, 0.3g fat
    # fiber=3.8 et vitamin_c=58.8 déjà corrects dans pv7
    "strawberry": {
        "calories_kcal": 32,
        "protein_g": 0.67,
        "carbs_g": 7.68,
        "fat_g": 0.3,
    },
    # brussels_sprouts: pv7 a 19 kcal (trop bas), proposals avaient 142 (trop haut)
    # Source USDA: brussels sprouts raw → 43 kcal, 3.38g prot, 8.95g carbs, 0.3g fat
    "brussels_sprouts": {
        "calories_kcal": 43.0,
        "protein_g": 3.38,
        "carbs_g": 8.95,
        "fat_g": 0.3,
        "fiber_g": 3.8,
        "vitamin_c_mg": 85.0,
    },
    # maca: fat=64.9 impossible (macro sum=144g), real maca powder fat ~2.2g
    # carbs=71.4 CORRECT (garder), recalc calories après fix fat
    "maca": {
        "fat_g": 2.2,
        # calories recalculées ensuite via Atwater
    },
    # mustard processed (condiment): cholesterol_mg = 0.35 → 0 (végétal)
    "mustard": {
        "cholesterol_mg": 0.0,
    },
}

# ── D. Aliments végétaux avec cholesterol_mg != 0 à forcer à 0 ─────────────
BIO_PLANT_CHOL = {"avocado", "breadcrumbs", "carrot", "hemp_milk",
                  "polenta", "semolina", "mustard"}

# ── E. energy_mismatch → recalc calories Atwater ───────────────────────────
ENERGY_RECALC = {"ginger", "tamari", "maca"}   # maca aussi après fix fat_g

# ── F. Lipid sub incoherence : ratio subs/fat < 0.15 ───────────────────────
# Pour chaque cas : action = "fix_fat" (fat_g wrong, subs corrects)
#                             "fix_subs" (fat_g correct, subs zeros/wrong)
# fat_target = valeur correcte connue (source USDA/CIQUAL)
LIPID_FIX: dict[str, dict] = {
    # fat_g wrong (subs corrects, petites valeurs absolues)
    "bulgur":       {"action": "fix_fat",  "fat_target": 0.24},   # USDA bulgur cuit
    "capers":       {"action": "fix_fat",  "fat_target": 0.86},   # USDA capers raw
    "couscous":     {"action": "fix_fat",  "fat_target": 0.58},   # USDA couscous cuit
    "rice_paper":   {"action": "fix_fat",  "fat_target": 0.17},   # USDA rice paper dry
    "snow_pea":     {"action": "fix_fat",  "fat_target": 0.20},   # USDA snow peas raw
    "snow_peas":    {"action": "fix_fat",  "fat_target": 0.20},
    # fat_g correct, subs ont été mis à ~0 par erreur → rescale vers fat
    "curry_leaves": {"action": "fix_subs"},   # fat=4g plausible (feuilles aromatiques)
    "matcha_tea":   {"action": "fix_subs"},   # fat=5.3g correct (matcha USDA ~5.5g)
    "vine_leaves":  {"action": "fix_subs"},   # fat=2g correct (feuilles de vigne)
    # blueberry, cauliflower, dried_raisins, maca : fat corrigé par proposals/hardcoded
    # → leur rescale subs est géré dans la section "rescale after fat change"
}

# Profils lipidiques typiques (sat:mono:poly) pour fix_subs
LIPID_PROFILES: dict[str, tuple[float,float,float]] = {
    "curry_leaves": (0.15, 0.25, 0.60),  # feuilles riches en poly
    "matcha_tea":   (0.24, 0.20, 0.56),  # matcha : fort ratio poly (USDA)
    "vine_leaves":  (0.30, 0.33, 0.37),  # feuilles de vigne (USDA)
}
DEFAULT_LIPID_PROFILE = (0.33, 0.33, 0.34)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def get_variant(data: dict, key: str) -> dict | None:
    return data["ingredients"].get(key, {}).get("variants", {}).get("default")


def recalc_calories(v: dict) -> float:
    return round(
        (v.get("protein_g") or 0) * 4 +
        (v.get("carbs_g") or 0) * 4 +
        (v.get("fat_g") or 0) * 9 +
        (v.get("alcohol_g") or 0) * 7,
        2
    )


def scale_subs(v: dict, new_fat: float, profile: tuple[float,float,float]) -> list[str]:
    """Set sat/mono/poly so they sum to ~0.95 * new_fat using the given profile."""
    s, m, p = profile
    target = new_fat * 0.95
    v["saturated_fat_g"]       = round(target * s, 4)
    v["monounsaturated_fat_g"] = round(target * m, 4)
    v["polyunsaturated_fat_g"] = round(target * p, 4)
    return LIPID_SUB_FIELDS[:]


def proportional_scale_subs(v: dict, old_fat: float, new_fat: float) -> list[str]:
    """Scale existing subs proportionally when fat_g changes."""
    if old_fat <= 0:
        return []
    ratio = new_fat / old_fat
    changed = []
    for f in LIPID_SUB_FIELDS:
        val = v.get(f)
        if val is not None and val > 0:
            v[f] = round(val * ratio, 4)
            changed.append(f)
    return changed


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("══════════════════════════════════════════════════════════════════")
    print("  PATCH CRITICALS v2  →  nutrition_patched_v7.json")
    print("══════════════════════════════════════════════════════════════════")

    backup = NUTRITION_FILE.with_suffix(
        f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    shutil.copy2(NUTRITION_FILE, backup)
    print(f"  Backup → {backup.name}")

    with open(NUTRITION_FILE, encoding="utf-8") as f:
        data = json.load(f)
    with open(PROPOSALS_FILE, encoding="utf-8") as f:
        proposals_doc = json.load(f)

    proposals = proposals_doc["proposals"]
    log = {"generated": datetime.now().isoformat(), "corrections": [], "stats": {}}
    stats = dict(proposals_applied=0, proposals_skipped=0, hardcoded=0,
                 cholesterol_zeroed=0, energy_recalculated=0,
                 lipid_fat_fixed=0, lipid_subs_scaled=0)

    # ── A. Proposals (whitelist) ────────────────────────────────────────────
    print("\n[A] Application proposals (whitelist)...")
    for ing_key, allowed_fields in PROPOSAL_WHITELIST.items():
        v = get_variant(data, ing_key)
        if v is None:
            print(f"    ⚠ {ing_key} introuvable → skip")
            continue
        prop = proposals.get(ing_key, {})
        changes = []
        for pf in allowed_fields:
            jf = FIELD_MAP.get(pf)
            if not jf or pf not in prop:
                continue
            proposed = prop[pf].get("proposed")
            if proposed is None:
                continue
            old = v.get(jf)
            old_fat = v.get("fat_g") if jf == "fat_g" else None
            v[jf] = round(proposed, 4)
            stats["proposals_applied"] += 1
            changes.append({"field": jf, "old": old, "new": round(proposed, 4),
                             "source": prop[pf].get("source", "?")})
            # Scale subs if fat changed
            if old_fat is not None and old_fat > 0:
                scaled = proportional_scale_subs(v, old_fat, proposed)
                if scaled:
                    stats["lipid_subs_scaled"] += len(scaled)
                    changes.append({"field": "lipid_subs_proportional_scale",
                                    "fields": scaled, "ratio": round(proposed/old_fat, 4)})
        if changes:
            log["corrections"].append({"ingredient": ing_key, "step": "A_proposal", "changes": changes})
            print(f"    ✔ {ing_key}: {[c['field'] for c in changes if 'field' in c]}")

    # ── C. Fixes hardcodés ──────────────────────────────────────────────────
    print("\n[C] Fixes hardcodés...")
    for ing_key, fixes in HARDCODED_FIXES.items():
        v = get_variant(data, ing_key)
        if v is None:
            continue
        changes = []
        for jf, new_val in fixes.items():
            old = v.get(jf)
            old_fat = v.get("fat_g") if jf == "fat_g" else None
            v[jf] = new_val
            stats["hardcoded"] += 1
            changes.append({"field": jf, "old": old, "new": new_val, "source": "hardcoded_reference"})
            if old_fat is not None and old_fat > 0:
                scaled = proportional_scale_subs(v, old_fat, new_val)
                if scaled:
                    stats["lipid_subs_scaled"] += len(scaled)
                    changes.append({"field": "lipid_subs_proportional_scale",
                                    "fields": scaled, "ratio": round(new_val/old_fat, 4)})
        if changes:
            log["corrections"].append({"ingredient": ing_key, "step": "C_hardcoded", "changes": changes})
            print(f"    ✔ {ing_key}: {[c['field'] for c in changes if 'field' in c]}")

    # ── D. bio_plant_cholesterol ────────────────────────────────────────────
    print("\n[D] bio_plant_cholesterol → 0...")
    for ing_key in BIO_PLANT_CHOL:
        v = get_variant(data, ing_key)
        if v is None:
            continue
        old = v.get("cholesterol_mg")
        if old and old != 0:
            v["cholesterol_mg"] = 0
            stats["cholesterol_zeroed"] += 1
            log["corrections"].append({"ingredient": ing_key, "step": "D_cholesterol",
                                       "changes": [{"field": "cholesterol_mg",
                                                    "old": old, "new": 0}]})
            print(f"    ✔ {ing_key}: cholesterol_mg {old} → 0")
        else:
            print(f"    · {ing_key}: déjà 0")

    # ── E. Energy recalc (Atwater) ──────────────────────────────────────────
    print("\n[E] Recalcul énergie (Atwater)...")
    for ing_key in ENERGY_RECALC:
        v = get_variant(data, ing_key)
        if v is None:
            continue
        old_cal = v.get("calories_kcal")
        new_cal = recalc_calories(v)
        v["calories_kcal"] = new_cal
        stats["energy_recalculated"] += 1
        log["corrections"].append({"ingredient": ing_key, "step": "E_energy_recalc",
                                   "changes": [{"field": "calories_kcal",
                                                "old": old_cal, "new": new_cal}]})
        print(f"    ✔ {ing_key}: {old_cal} → {new_cal} kcal")

    # ── F. Lipid sub incoherence ────────────────────────────────────────────
    print("\n[F] Lipid sub incoherence...")
    for ing_key, cfg in LIPID_FIX.items():
        v = get_variant(data, ing_key)
        if v is None:
            continue
        fat = v.get("fat_g") or 0
        changes = []

        if cfg["action"] == "fix_fat":
            # fat_g is wrong; subs are from correct reference
            new_fat = cfg["fat_target"]
            old_fat = fat
            v["fat_g"] = new_fat
            stats["lipid_fat_fixed"] += 1
            changes.append({"field": "fat_g", "old": old_fat, "new": new_fat,
                             "source": "lipid_sub_coherence_fix"})
            # Recalc calories after fat change
            old_cal = v.get("calories_kcal")
            new_cal = recalc_calories(v)
            v["calories_kcal"] = new_cal
            changes.append({"field": "calories_kcal", "old": old_cal, "new": new_cal,
                             "source": "atwater_recalc"})

        elif cfg["action"] == "fix_subs":
            # fat_g is correct; scale subs to fat using known profile
            if fat <= 0:
                print(f"    ⚠ {ing_key}: fat_g=0, skip")
                continue
            profile = LIPID_PROFILES.get(ing_key, DEFAULT_LIPID_PROFILE)
            old_subs = {f: v.get(f) for f in LIPID_SUB_FIELDS}
            scaled_fields = scale_subs(v, fat, profile)
            stats["lipid_subs_scaled"] += len(scaled_fields)
            changes.append({"field": "lipid_subs_rescaled",
                             "fields": scaled_fields,
                             "old_subs": old_subs,
                             "fat_g": fat,
                             "profile": profile})

        if changes:
            log["corrections"].append({"ingredient": ing_key, "step": "F_lipid_sub",
                                       "changes": changes})
            action_label = cfg["action"]
            print(f"    ✔ {ing_key} [{action_label}]: {[c.get('field') for c in changes]}")

    # ── Mise à jour metadata ────────────────────────────────────────────────
    now = datetime.now().isoformat()
    data["generated_at"] = now
    if "changelog" not in data:
        data["changelog"] = {}
    schema = data.get("schema_version", "3.8")
    # bump minor version
    parts = str(schema).split(".")
    new_ver = f"{parts[0]}.{int(parts[1])+1 if len(parts)>1 else 9}" if len(parts)>1 else f"{schema}.1"
    data["schema_version"] = new_ver
    data["changelog"][new_ver] = {
        "date": now[:10],
        "author": "patch_criticals_v2.py",
        "summary": "Fix 54 criticals: proposals (whitelist), hardcoded, cholesterol, Atwater, lipid_sub",
        "stats": stats
    }

    with open(NUTRITION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ {NUTRITION_FILE.name} mis à jour (schema {new_ver})")

    log["stats"] = stats
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Log → {LOG_FILE.name}")

    print(f"""
  ┌────────────────────────────────────────────────────┐
  │  Résumé                                            │
  │  Proposals appliquées    : {stats['proposals_applied']:<5}                    │
  │  Fixes hardcodés         : {stats['hardcoded']:<5}                    │
  │  Cholesterol zéroté      : {stats['cholesterol_zeroed']:<5}                    │
  │  Énergie recalculée      : {stats['energy_recalculated']:<5}                    │
  │  fat_g corrigé (lipids)  : {stats['lipid_fat_fixed']:<5}                    │
  │  Subs lipides rescalés   : {stats['lipid_subs_scaled']:<5}                    │
  └────────────────────────────────────────────────────┘
""")
    print("══════════════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
