#!/usr/bin/env python3
"""
audit_outliers.py — Valeurs nutritionnelles aberrantes dans nutrition_v2.json.

Trois contrôles par variante :
  1. énergie : calories_kcal comparée à 4·protéines + 4·glucides + 9·lipides
     + 2·fibres + 7·alcool (écart > 25 % et > 40 kcal) ;
     NB : CNF et USDA publient des glucides TOTAUX (fibres comprises), CIQUAL
     des glucides disponibles — les fibres sont retirées des premiers avant
     les contrôles 1 et 2 ;
  2. masse : protéines + glucides + lipides + fibres + eau + alcool ≤ 105 g ;
  3. fratrie : chaque nutriment comparé à la médiane des fiches du même aliment
     (même premier mot du nom FR, même forme : cuisson, séchage, huile/farine…,
     partie) ; valeurs nulles ignorées (souvent « non mesuré ») ; un rapport
     ≥ 30 ou ≤ 1/30 avec au moins deux autres fiches signale une erreur
     d'unité (mg/µg, facteur 100 ou 1000) ou de saisie.

Lecture seule : écrit le rapport backend/data/nutrition/logs/audit_outliers.json.

    python scripts/nutrition/audit_outliers.py            # résumé
    python scripts/nutrition/audit_outliers.py --details   # toutes les alertes
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
N2 = ROOT / "backend" / "data" / "nutrition" / "processed" / "nutrition_v2.json"
REPORT = ROOT / "backend" / "data" / "nutrition" / "logs" / "audit_outliers.json"

# Nutriments comparés entre fiches d'un même aliment (les macros varient trop
# selon la recette ou la cuisson pour un rapport fixe ; les minéraux et
# vitamines d'un même aliment cru restent du même ordre de grandeur).
SIBLING_FIELDS = (
    "calcium_mg", "iron_mg", "magnesium_mg", "phosphorus_mg", "potassium_mg",
    "zinc_mg", "copper_mg", "manganese_mg", "selenium_ug",
    "vitamin_c_mg", "vitamin_b1_mg", "vitamin_b2_mg", "vitamin_b3_mg", "vitamin_b6_mg",
    "folate_dfe_ug", "vitamin_k1_ug", "beta_carotene_ug",
)
RATIO = 30.0
# en dessous, le nutriment est à l'état de traces : un rapport n'a pas de sens
FLOOR = {"_mg": 0.05, "_ug": 0.5}


def _floor(field: str) -> float:
    return FLOOR["_ug"] if field.endswith("_ug") else FLOOR["_mg"]


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _available_carbs(v: dict) -> float | None:
    """Glucides hors fibres, quelle que soit la convention de la source."""
    c = _num(v.get("carbs_g"))
    if c is None:
        return None
    if v.get("_source") in ("CNF", "USDA"):
        return max(c - (_num(v.get("fiber_g")) or 0.0), 0.0)
    return c


_FORM_AXES = ("cooking_state", "thermal_state", "form", "part", "fat_content")


def _form(var: dict) -> tuple:
    """Forme de l'aliment : cuisson, séchage, forme (huile, farine…), partie."""
    ax = var.get("axes") or {}
    return tuple((k, str(ax.get(k))) for k in _FORM_AXES if ax.get(k))


def load() -> dict:
    return json.loads(N2.read_text(encoding="utf-8"))["ingredients"]


def variants(ings: dict):
    for base, b in ings.items():
        name = (b.get("taxonomy") or {}).get("name_fr") or base
        for vk, var in (b.get("variants") or {}).items():
            yield base, vk, name, var


def energy_alerts(ings: dict) -> list[dict]:
    out = []
    for base, vk, name, v in variants(ings):
        kcal = _num(v.get("calories_kcal"))
        p, f = _num(v.get("protein_g")), _num(v.get("fat_g"))
        c = _available_carbs(v)
        if kcal is None or None in (p, c, f):
            continue
        fib = _num(v.get("fiber_g")) or 0.0
        alc = _num(v.get("alcohol_g")) or 0.0
        pol = _num(v.get("polyols_g")) or 0.0
        org = _num(v.get("organic_acids_g")) or 0.0
        est = 4 * p + 4 * c + 9 * f + 2 * fib + 7 * alc + 2.4 * pol + 3 * org
        if abs(kcal - est) > max(40.0, 0.25 * max(kcal, est)):
            out.append({"key": f"{base}/{vk}", "name": name, "source": v.get("_source"),
                        "source_id": v.get("_source_id"), "kcal": kcal, "kcal_from_macros": round(est, 1),
                        "protein_g": p, "carbs_g": c, "fat_g": f, "fiber_g": fib, "alcohol_g": alc})
    return out


def mass_alerts(ings: dict) -> list[dict]:
    out = []
    for base, vk, name, v in variants(ings):
        parts = [_num(v.get("protein_g")), _available_carbs(v)] +                 [_num(v.get(k)) for k in ("fat_g", "fiber_g", "water_g", "alcohol_g")]
        if parts[4] is None:
            continue
        total = sum(x for x in parts if x is not None)
        if total > 105:
            out.append({"key": f"{base}/{vk}", "name": name, "source": v.get("_source"),
                        "source_id": v.get("_source_id"), "total_g": round(total, 1)})
    return out


def sibling_alerts(ings: dict) -> list[dict]:
    groups: dict[tuple, list] = defaultdict(list)
    for base, vk, name, v in variants(ings):
        if v.get("_source") in ("COMPOSITE",):
            continue
        words = name.split("(")[0].strip().lower().split()
        if not words:
            continue
        # « oignon », « oignon jaune », « oignon rouge » : même aliment de base
        groups[(words[0], _form(v))].append((f"{base}/{vk}", v))
    out = []
    for (canon, form), members in groups.items():
        if len(members) < 3:
            continue
        for field in SIBLING_FIELDS:
            vals = [(k, _num(v.get(field)), v) for k, v in members]
            # 0 vaut souvent « non mesuré » : seules les valeurs renseignées sont comparées
            vals = [(k, x, v) for k, x, v in vals if x is not None and x > 0]
            if len(vals) < 3:
                continue
            for k, x, v in vals:
                others = [y for kk, y, _ in vals if kk != k]
                med = statistics.median(others)
                if max(med, x) < _floor(field):
                    continue
                lo, hi = max(x, 1e-9), max(med, 1e-9)
                ratio = hi / lo if hi >= lo else lo / hi
                if ratio >= RATIO and max(x, med) >= _floor(field) * 4:
                    out.append({"key": k, "name": canon, "form": dict(form), "field": field, "value": x,
                                "siblings_median": round(med, 4), "n_siblings": len(others),
                                "ratio": round(ratio, 1), "direction": "trop bas" if x < med else "trop haut",
                                "source": v.get("_source"), "source_id": v.get("_source_id")})
    return sorted(out, key=lambda a: -a["ratio"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--details", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ings = load()
    report = {
        "energy": energy_alerts(ings),
        "mass": mass_alerts(ings),
        "siblings": sibling_alerts(ings),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Énergie incohérente : {len(report['energy'])}")
    print(f"Masse > 105 g       : {len(report['mass'])}")
    print(f"Écart à la fratrie  : {len(report['siblings'])}")
    if args.details:
        for kind, items in report.items():
            print(f"\n── {kind} ──")
            for a in items:
                print("  ", json.dumps(a, ensure_ascii=False))
    print(f"Rapport → {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
