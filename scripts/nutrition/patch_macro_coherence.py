"""
patch_macro_coherence.py
Corrige les 131 incohérences macro dans nutrition_v2.json :

  A) fiber > carbs  (36 cas)
     Cause : fibres CIQUAL sur matière sèche, glucides sur frais.
     Fix   : ajouter flag carbs_basis="dry" — ne PAS modifier les valeurs
             (elles sont correctes dans leur référentiel).

  B) starch + sugar > carbs  (45 cas)
     Cause : starch hérité d'une forme concentrée/séchée non recalculée.
     Fix   : cap starch = max(0, carbs - sugar). Loggué.

  C) Schema contradiction _meta vs racine
     Fix   : forcer schema_version=5.4 partout.
"""
import json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path("backend/data")
N2F  = BASE / "nutrition/processed/nutrition_v2.json"
LOGF = BASE / "nutrition/logs/macro_coherence_log.json"
NOW  = datetime.now(timezone.utc).isoformat()

raw  = json.load(open(N2F, encoding="utf-8"))
ings = raw["ingredients"]

flagged_dry   = []  # fiber > carbs → carbs_basis=dry
fixed_starch  = []  # starch+sugar > carbs → starch capped

EPSILON = 0.01  # tolérance flottant

for base_key, base in ings.items():
    for var_key, v in base.get("variants", {}).items():
        if not isinstance(v, dict):
            continue
        path = f"{base_key}[{var_key}]"

        # Lire champs (double nommage historique)
        carbs  = v.get("carbs_g")  or v.get("carbs")  or 0.0
        fiber  = v.get("fiber_g")  or v.get("fiber")  or 0.0
        starch = v.get("starch_g") or 0.0
        sugar  = v.get("sugar_g")  or v.get("sugar")  or 0.0

        try:
            carbs  = float(carbs)
            fiber  = float(fiber)
            starch = float(starch)
            sugar  = float(sugar)
        except (TypeError, ValueError):
            continue

        # ── A) fiber > carbs ───────────────────────────────────────────────────
        # Exclure les variants schema "available" (glucides disponibles) :
        # fiber > carbs_available est biologiquement attendu pour graines séchées
        # (ex: sesame, chia, black_sesame) — pas un bug, pas de flag carbs_basis=dry.
        if fiber > carbs + EPSILON and carbs > 0:
            if v.get("carbs_basis") != "dry" and v.get("carbs_schema") != "available":
                v["carbs_basis"] = "dry"
                v["carbs_basis_note"] = (
                    "Glucides exprimés sur poids frais, fibres sur matière sèche "
                    "(CIQUAL convention). Incohérence apparente — valeurs correctes."
                )
                flagged_dry.append({
                    "path": path, "fiber": fiber, "carbs": carbs,
                    "ratio_dry_est": round(fiber / carbs, 2),
                })

        # ── B) starch + sugar > carbs ─────────────────────────────────────────
        if starch > 0 and (starch + sugar) > carbs + EPSILON:
            # Cap starch
            new_starch = max(0.0, round(carbs - sugar, 3))
            old_starch = starch

            # Mettre à jour les deux noms de champ si présents
            if "starch_g" in v: v["starch_g"] = new_starch
            if "starch" in v:   v["starch"]   = new_starch

            fixed_starch.append({
                "path":       path,
                "carbs":      carbs,
                "sugar":      sugar,
                "old_starch": old_starch,
                "new_starch": new_starch,
                "delta":      round(old_starch - new_starch, 3),
            })

# ── C) Schema version ─────────────────────────────────────────────────────────
# V13 FIX : préserver la version issue de promote_nutrition.py
# Hardcoder "5.4" ici écrasait silencieusement le bump 5.4→5.5/6.0.
_sv = (raw.get("schema_version")
       or raw.get("_meta", {}).get("schema_version")
       or raw.get("metadata", {}).get("schema_version", "5.4"))
for key in ("_meta", "metadata"):
    if key in raw:
        raw[key]["schema_version"] = _sv
if "schema_version" in raw:
    raw["schema_version"] = _sv

# ── Écriture atomique ─────────────────────────────────────────────────────────
fd, tmp = tempfile.mkstemp(dir=N2F.parent, suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False, indent=2)
os.replace(tmp, N2F)

# ── Log ───────────────────────────────────────────────────────────────────────
LOGF.parent.mkdir(parents=True, exist_ok=True)
log_entry = {
    "ts": NOW,
    "script": "patch_macro_coherence.py",
    "flagged_dry_basis": len(flagged_dry),
    "fixed_starch_overflow": len(fixed_starch),
    "details_dry":    flagged_dry,
    "details_starch": fixed_starch,
}
existing = []
if LOGF.exists():
    try: existing = json.loads(LOGF.read_text(encoding="utf-8"))
    except: pass
existing.append(log_entry)
LOGF.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

# ── Rapport ───────────────────────────────────────────────────────────────────
print(f"{'='*65}")
print(f"  PATCH MACRO COHÉRENCE — nutrition_v2.json")
print(f"{'='*65}")
print(f"\n  A) fiber>carbs flaggés  carbs_basis=dry : {len(flagged_dry)}")
for e in flagged_dry[:12]:
    print(f"     {e['path']:35s}  fiber={e['fiber']:.1f}  carbs={e['carbs']:.2f}  ratio≈{e['ratio_dry_est']}x")
if len(flagged_dry) > 12:
    print(f"     ... et {len(flagged_dry)-12} autres")

print(f"\n  B) starch+sugar>carbs corrigés          : {len(fixed_starch)}")
for e in fixed_starch[:12]:
    print(f"     {e['path']:35s}  starch {e['old_starch']:.2f}→{e['new_starch']:.3f}  (Δ={e['delta']:.2f})")
if len(fixed_starch) > 12:
    print(f"     ... et {len(fixed_starch)-12} autres")

print(f"\n  C) schema_version préservée : {_sv}")
print(f"\n  Log : {LOGF}")
print(f"{'='*65}")
