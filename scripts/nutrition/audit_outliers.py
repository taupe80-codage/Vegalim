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
        c = max(c - (_num(v.get("fiber_g")) or 0.0), 0.0)
    # Les glucides comprennent souvent les polyols (CIQUAL, étiquettes UE :
    # abricot sec 59,1 g dont 22,6 g de sorbitol) ; ils sont comptés à part
    # (2,4 kcal/g) dans le contrôle d'énergie.
    pol = _num(v.get("polyols_g")) or 0.0
    if pol:
        rest = (_num(v.get("sugar_g")) or 0.0) + (_num(v.get("starch_g")) or 0.0)
        if rest + pol <= c * 1.05 + 1.0:
            c = max(c - pol, 0.0)
    return c


# Écarts d'énergie vérifiés à la source : la valeur publiée est conservée.
ENERGY_EXCEPTIONS = {
    # Farine de caroube : 222 kcal pour 88,9 g de glucides totaux dont 39,8 g
    # de fibres, mêmes chiffres que la fiche USDA ; énergie publiée avec des
    # coefficients propres à l'aliment, pas une erreur de saisie.
    "carob/flour": "CNF 3278, valeur officielle conservée",
}

# Écarts à la fratrie relus le 2026-11-24 : le groupe réunit des aliments
# différents sous le même premier mot (haricot vert / sec / de mer, chou kale /
# rouge, crème / crème de tartre, pamplemousse rose / blanc…) ou l'aliment est
# réellement atypique. Valeur source conservée ; les vraies erreurs sont dans
# reference/source_value_corrections.json.
_GROUPE = "aliment différent de son groupe"
SIBLING_EXCEPTIONS: dict[tuple[str, str], str] = {
    ("button_mushroom_canned/canned", "manganese_mg"): "champignon frais en conserve vs champignons séchés",
    ("wood_ear_mushroom/default", "manganese_mg"): "champignon séché (CNF 4884)",
    ("jews_ear_mushroom_raw/raw", "vitamin_b3_mg"): "CNF 2101, pas de source contraire",
    ("kale_boiled_canned/boiled_canned", "beta_carotene_ug"): "kale vs chou blanc/rouge",
    ("kale_boiled_salted/boiled_salted", "beta_carotene_ug"): "kale vs chou blanc/rouge",
    ("spaghetti_squash_baked_canned/baked_canned", "beta_carotene_ug"): "courge spaghetti, chair pâle",
    ("cream/default", "iron_mg"): _GROUPE + " (crème de tartre)",
    ("cream_sour/fermented", "iron_mg"): _GROUPE + " (crème de tartre)",
    ("cream_of_tartar/default", "potassium_mg"): "bitartrate de potassium",
    ("cream_of_tartar/default", "iron_mg"): "crème de tartre vs crème laitière",
    ("black_eyed_peas_cowpeas_immature_boiled_canned/boiled_canned", "beta_carotene_ug"): "graines immatures (vertes)",
    ("yardlong_boiled/boiled", "beta_carotene_ug"): "haricot kilomètre : gousse verte",
    ("adzuki_bean_sweetened_canned/sweetened_canned", "beta_carotene_ug"): _GROUPE,
    ("french_bean/boiled", "beta_carotene_ug"): "haricot vert vs haricots secs",
    ("green_flageolet_bean/dried", "beta_carotene_ug"): _GROUPE + " (haricot de mer = algue)",
    ("italian_bean_green_or_yellow_boiled_canned/boiled_canned", "beta_carotene_ug"): "haricot vert vs haricots secs",
    ("light_red_kidney_bean_raw/raw", "beta_carotene_ug"): _GROUPE,
    ("lima_bean_boiled_canned/boiled_canned", "beta_carotene_ug"): "fève de Lima immature (verte)",
    ("lima_bean_boiled_salted/boiled_salted", "beta_carotene_ug"): "fève de Lima immature (verte)",
    ("mung_bean_sprouted_dried_canned/sprouted_dried_canned", "beta_carotene_ug"): "germes en conserve, pas un haricot sec",
    ("mung_bean_sprouted_dried_canned/sprouted_dried_canned", "potassium_mg"): "germes en conserve égouttés (USDA : 27 mg)",
    ("sea_bean/dried", "beta_carotene_ug"): "haricot de mer = algue Himanthalia séchée",
    ("sea_bean/dried", "vitamin_k1_ug"): "haricot de mer = algue Himanthalia séchée",
    ("cantaloupe_melon_charentais/raw", "beta_carotene_ug"): "melon à chair orange vs melon miel",
    ("honeydew_melon/raw", "beta_carotene_ug"): "melon miel à chair verte",
    ("brazilnut/unbleached_dried_plain", "selenium_ug"): "noix du Brésil, très riche en sélénium",
    ("grapefruit/juice_plain", "beta_carotene_ug"): "pamplemousse rose vs blanc",
    ("grapefruit_raw/raw", "beta_carotene_ug"): "pamplemousse rose vs blanc",
    ("pink_grapefruit/raw", "beta_carotene_ug"): "pamplemousse rose vs blanc",
    ("white_grapefruit/raw", "beta_carotene_ug"): "pamplemousse blanc vs rose",
    ("white_grapefruit_raw/raw", "beta_carotene_ug"): "pamplemousse blanc vs rose",
    ("snow_peas_boiled/boiled", "beta_carotene_ug"): "pois mange-tout (gousse verte) vs pois secs",
    ("snow_peas_boiled_canned/boiled_canned", "beta_carotene_ug"): "pois mange-tout (gousse verte) vs pois secs",
    ("snow_peas_boiled_salted/boiled_salted", "beta_carotene_ug"): "pois mange-tout (gousse verte) vs pois secs",
    ("split_peas_boiled_salted/boiled_salted", "vitamin_c_mg"): "pois cassés secs vs petits pois frais",
    ("grey_sea_salt/unenriched", "magnesium_mg"): "sel gris non raffiné",
    ("corn_bran/raw", "vitamin_b1_mg"): "son de maïs vs germe/son de blé (USDA)",
    ("corn_bran/raw", "manganese_mg"): "son de maïs vs germe/son de blé (USDA)",
    ("corn_bran/raw", "potassium_mg"): "son de maïs vs germe/son de blé (USDA)",
    ("vanilla_sugar/default", "potassium_mg"): "sucre raffiné",
    ("vanilla_aqueous_extract/extract_in_water", "manganese_mg"): "extrait aqueux vs gousse",
    ("white_vinegar/liquid_distilled", "potassium_mg"): "vinaigre distillé vs vinaigres de fruit",
}


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
        if f"{base}/{vk}" in ENERGY_EXCEPTIONS:
            continue
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
                if (k, field) in SIBLING_EXCEPTIONS:
                    continue
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
