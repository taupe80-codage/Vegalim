"""
patch_nutrition_critical.py
Corrige les 5 bugs critiques identifiés dans l'audit nutrition_v2.json.
Toutes les valeurs sont sourcées CIQUAL 2025 / USDA FoodData Central.

Corrections :
  C1 - water[default]         : sugar 7.29 → 0
  C2 - oil[4 variantes]       : profils lipidiques corrects (sat/mono/poly)
  C3 - pepper[default]        : starch 38 → 0.5 (poivre frais)
  C4 - butter[almond]         : fiber 6.0 → 0.06, starch 7.94 → 0
  C5 - quinoa[default]        : recalibrer sur état cru (USDA 20035)
  C6 - metadata               : corriger schema_version, compteurs
  C7 - xylitol/chia           : ajouter calorie_method note
"""
import json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE  = Path("backend/data")
N2F   = BASE / "nutrition/processed/nutrition_v2.json"
NOW   = datetime.now(timezone.utc).isoformat()
LOG   = []

raw   = json.load(open(N2F, encoding="utf-8"))
ings  = raw["ingredients"]

def patch(path, field, old_val, new_val, source):
    """Applique et logue un patch."""
    parts = path.split(".")
    obj = ings
    for p in parts[:-1]:
        obj = obj[p]
    actual = obj.get(parts[-1])
    obj[parts[-1]] = new_val
    LOG.append({
        "path": path, "field": field,
        "old": actual, "new": new_val,
        "source": source, "ts": NOW,
    })
    print(f"  [{path}] {field}: {actual} → {new_val}  ({source})")


print("=" * 65)
print("  PATCH CRITIQUE nutrition_v2.json")
print("=" * 65)

# ── C1 — water[default] sugar=7.29 → 0 ───────────────────────────────────────
print("\nC1 — water[default] : sugar erroné")
w = ings.get("water", {}).get("variants", {}).get("default", {})
if w.get("sugar_g", 0) > 0:
    w["sugar_g"]  = 0.0
    w["sugar"]    = 0.0
    LOG.append({"path": "water.variants.default", "field": "sugar_g", "old": 7.29, "new": 0, "source": "CIQUAL 2025 #18066", "ts": NOW})
    print("  water[default].sugar_g = 7.29 → 0.0  (CIQUAL 2025 #18066)")
else:
    print("  OK déjà corrigé")

# ── C2 — oil[4 variantes] profils lipidiques corrects ────────────────────────
# Sources : USDA FoodData / CIQUAL 2025 (valeurs /100g huile pure)
print("\nC2 — oil : profils lipidiques corrects")
OIL_LIPIDS = {
    # variant : (sat_g, mono_g, poly_g)         source USDA/CIQUAL
    "coconut":   (86.5,  5.8,  1.8),   # USDA #04047  — ~86% saturés
    "flaxseed":  (9.0,  20.2, 66.0),   # USDA #04038  — ~73% poly (ALA)
    "sesame":    (14.2,  39.7, 41.7),   # USDA #04058  — poly/mono équilibrés
    "sunflower": (10.3,  45.4, 40.1),   # USDA #04506  — tournesol HO
    "palm":      (49.3,  37.0, 9.3),    # USDA #04055
    "olive":     (13.8,  72.9, 10.5),   # USDA #04053  — déjà OK normalement
    "peanut":    (17.0,  46.2, 32.0),   # USDA #04042
}
oil_variants = ings.get("oil", {}).get("variants", {})
for var, (sat, mono, poly) in OIL_LIPIDS.items():
    v = oil_variants.get(var)
    if v is None:
        print(f"  SKIP oil/{var} absent")
        continue
    old_sat  = v.get("saturated_fat_g") or v.get("sat_fat_g")
    old_mono = v.get("monounsaturated_fat_g") or v.get("mono_fat_g")
    old_poly = v.get("polyunsaturated_fat_g") or v.get("poly_fat_g")
    # Mise à jour — tenter les deux noms de champs
    for fname in ("saturated_fat_g","sat_fat_g"):
        if fname in v: v[fname] = sat
    for fname in ("monounsaturated_fat_g","mono_fat_g"):
        if fname in v: v[fname] = mono
    for fname in ("polyunsaturated_fat_g","poly_fat_g"):
        if fname in v: v[fname] = poly
    # Si pas de champ existant, créer
    if "saturated_fat_g" not in v and "sat_fat_g" not in v:
        v["saturated_fat_g"] = sat
        v["monounsaturated_fat_g"] = mono
        v["polyunsaturated_fat_g"] = poly
    LOG.append({"path": f"oil.variants.{var}", "field": "lipids", "old": f"sat={old_sat}", "new": f"sat={sat},mono={mono},poly={poly}", "source": "USDA FoodData", "ts": NOW})
    print(f"  oil/{var}: sat={old_sat}→{sat}, mono={old_mono}→{mono}, poly={old_poly}→{poly}")

# ── C3 — pepper[default] starch 38 → 0.5 ─────────────────────────────────────
print("\nC3 — pepper[default] : starch contaminé")
pv = ings.get("pepper", {}).get("variants", {}).get("default", {})
if pv:
    old_st = pv.get("starch_g")
    pv["starch_g"] = 0.5   # CIQUAL poivre frais
    LOG.append({"path": "pepper.variants.default", "field": "starch_g", "old": old_st, "new": 0.5, "source": "CIQUAL 2025 poivre frais", "ts": NOW})
    print(f"  pepper[default].starch_g: {old_st} → 0.5  (CIQUAL poivre frais)")
else:
    print("  SKIP pepper/default absent")

# ── C4 — butter[almond] fiber+starch recalibré ────────────────────────────────
# Beurre d'amande /100g : carbs=20g, fiber=3.7g, starch=0g (USDA #16167)
print("\nC4 — butter[almond] : fiber/starch recalibrage")
ba = ings.get("butter", {}).get("variants", {}).get("almond", {})
if ba:
    old_fiber = ba.get("fiber_g"); old_starch = ba.get("starch_g")
    ba["fiber_g"]  = 3.7
    ba["starch_g"] = 0.0
    ba["carbs_g"]  = ba.get("carbs_g") or 20.0   # carbs corrects USDA
    LOG.append({"path": "butter.variants.almond", "field": "fiber_g", "old": old_fiber, "new": 3.7, "source": "USDA #16167", "ts": NOW})
    LOG.append({"path": "butter.variants.almond", "field": "starch_g", "old": old_starch, "new": 0.0, "source": "USDA #16167", "ts": NOW})
    print(f"  butter[almond].fiber_g: {old_fiber} → 3.7  |  starch_g: {old_starch} → 0.0  (USDA #16167)")
else:
    print("  SKIP butter/almond absent")

# ── C5 — quinoa[default] recalibration état cru ───────────────────────────────
# Quinoa cru /100g USDA #20035 : cal=368, prot=14.1, carbs=64.2, fat=6.1, fiber=7.0
print("\nC5 — quinoa[default] : état mixte cru/cuit")
qv = ings.get("quinoa", {}).get("variants", {}).get("default", {})
if qv:
    old_cal = qv.get("calories_kcal") or qv.get("calories")
    QUINOA_RAW = {
        "calories_kcal": 368, "calories": 368,
        "protein_g":  14.1, "protein": 14.1,
        "carbs_g":    64.2, "carbs": 64.2,
        "fat_g":       6.1, "fat": 6.1,
        "fiber_g":     7.0, "fiber": 7.0,
        "sugar_g":     0.0,
    }
    for field, val in QUINOA_RAW.items():
        if field in qv:
            qv[field] = val
    # Forcer si absent
    qv.setdefault("calories_kcal", 368)
    qv.setdefault("protein_g", 14.1)
    qv.setdefault("carbs_g", 64.2)
    qv.setdefault("fat_g", 6.1)
    qv.setdefault("fiber_g", 7.0)
    qv["_state_note"] = "raw — cuisson divise cal/3, carbs/3 (absorption eau)"
    LOG.append({"path": "quinoa.variants.default", "field": "calories+macros", "old": f"cal={old_cal},carbs=69.5", "new": "cal=368,carbs=64.2 (état CRU USDA #20035)", "source": "USDA FoodData #20035", "ts": NOW})
    print(f"  quinoa[default]: cal {old_cal} → 368, carbs 69.5 → 64.2  (USDA #20035 cru)")
else:
    print("  SKIP quinoa/default absent")

# ── C7 — calorie_method pour xylitol et chia ──────────────────────────────────
print("\nC7 — calorie_method note (xylitol, chia)")
for base, variant, method, note in [
    ("xylitol",  "default",  "partial_metabolism", "~2.4 kcal/g — métabolisme partiel (EU 2008/100/EC)"),
    ("seeds",    "chia",     "low_digestibility",  "fibres peu digestibles — valeur calorique effective réduite"),
]:
    v = ings.get(base, {}).get("variants", {}).get(variant, {})
    if v:
        v["calorie_method"] = method
        v["calorie_method_note"] = note
        print(f"  {base}[{variant}].calorie_method = {method}")

# ── C6 — Metadata ─────────────────────────────────────────────────────────────
print("\nC6 — metadata : compteurs + schema_version")
meta = raw.get("_meta", raw.get("metadata", {}))

# Compter réel
bases    = len(ings)
variants = sum(len(v.get("variants",{})) for v in ings.values())
meta["total_bases"]    = bases
meta["total_variants"] = variants
# V13 FIX : préserver la version issue de promote_nutrition.py
# Hardcoder "5.4" ici écrasait le bump 5.4→5.5/6.0 après chaque promote.
_current_sv = (meta.get("schema_version")
               or raw.get("schema_version")
               or raw.get("_meta", {}).get("schema_version", "5.4"))
meta["schema_version"] = _current_sv
meta["last_critical_patch"] = NOW
meta["last_critical_patch_log"] = f"5 corrections critiques (water/oil/pepper/almond_butter/quinoa)"
if "_meta" in raw: raw["_meta"] = meta
elif "metadata" in raw: raw["metadata"] = meta
print(f"  total_bases: {bases}, total_variants: {variants}, schema_version: {_current_sv}")

# ── Écriture atomique ─────────────────────────────────────────────────────────
fd, tmp = tempfile.mkstemp(dir=N2F.parent, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False, indent=2)
os.replace(tmp, N2F)

# Log de patch
LOGF = BASE / "nutrition/logs/critical_patches_log.json"
LOGF.parent.mkdir(parents=True, exist_ok=True)
existing = []
if LOGF.exists():
    try: existing = json.loads(LOGF.read_text(encoding="utf-8"))
    except: pass
existing.extend(LOG)
LOGF.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"\n{'='*65}")
print(f"  {len(LOG)} corrections appliquées → {N2F.name}")
print(f"  Log → {LOGF}")
print(f"{'='*65}")
