"""
_diagnose_v2.py
═══════════════════════════════════════════════════════════════════════════
FUSION de _diagnose_ontology.py + _diagnose_ontology_full.py

Changements v2 :
  ✦ Lit nutrition_v2.json (schema hiérarchique base/variant) au lieu de
      nutrition_clean.json (v1 plat — obsolète)
  ✦ Lit ontology_v6.json en priorité, fallback ontology_v4_0.json
  ✦ Sections fusionnées :
      1. Rapport ontologie + outliers
      2. Couverture champs par ingrédient (nutrition_v2)
      3. No-match détaillés avec candidats proches
      4. Stats auto-correct (corrections_log.json)

AMÉLIORATIONS v2.2 :
  ✦ BUGFIX : resolve_source() cherche maintenant nutrition_patched_v8.json
      (plus v7)
  ✦ Section 5 — PIPELINE : état de tous les fichiers clés (date, taille,
      version) — aperçu immédiat de ce qui est à jour
  ✦ Section 6 — PATCH ACTIF : résumé live des URGENT_FIXES + BLOCKED_PROPOSALS
      en vigueur dans patch_nutrition_v8.py (parsé à la volée)
  ✦ Section 7 — MANQUANTS : alias manquants + ingrédients NC sans données
      dans les raws (P3) — liste de travail pour enrichir la base
  ✦ Coverage v2.2 : score global par catégorie + highlight champs à zéro
  ✦ Outliers dynamiques : calcul sur tous les ingrédients, pas 7 fixes
  ✦ --section choices : onto | coverage | nomatch | log | pipeline | patch
      | missing

Usage :
  python _diagnose_v2.py                           # rapport complet condensé
  python _diagnose_v2.py --full                    # détail no-match + outliers
  python _diagnose_v2.py --section pipeline        # état des fichiers
  python _diagnose_v2.py --section patch           # URGENT_FIXES actifs
  python _diagnose_v2.py --section missing         # ingrédients manquants
  python _diagnose_v2.py --section onto
  python _diagnose_v2.py --section coverage
  python _diagnose_v2.py --section nomatch
  python _diagnose_v2.py --section log
  python _diagnose_v2.py --input nutrition_patched_v8.json
═══════════════════════════════════════════════════════════════════════════
"""

import json
import sys
import re
import unicodedata
import argparse
from datetime import datetime, timezone
from pathlib import Path

# ── Encodage console Windows ──────────────────────────────────────────────────
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ══════════════════════════════════════════════════════════════════════════════
# CHEMINS
# ══════════════════════════════════════════════════════════════════════════════

BASE     = Path(__file__).resolve().parents[2] / "backend" / "data"
BASE_DIR = Path(__file__).resolve().parents[2]

_ONTO_V6       = BASE / "nutrition/reference/ontology_v6.json"
_ONTO_FALLBACK = BASE / "nutrition/reference/ontology_v4_0.json"

if _ONTO_V6.exists():
    ONTO_FILE = _ONTO_V6
else:
    ONTO_FILE = _ONTO_FALLBACK
    print("⚠  ontology_v6.json introuvable — fallback ontology_v4_0.json (résultats partiels)")
    print("   → Lancer d'abord : python scripts/nutrition/build_ontology_v6.py")

REPORT_FILE  = (
    BASE / "nutrition/reference/ontology_v6_report.json"
    if (BASE / "nutrition/reference/ontology_v6_report.json").exists()
    else BASE / "nutrition/reference/ontology_v4_0_report.json"
)
MAPPING_FILE = BASE / "ingredients/fr_to_en_mapping.json"
LOG_FILE     = BASE / "logs/corrections_log.json"

# Localisation de patch_nutrition_v8.py pour section_patch
_PATCH_V8_FILE = Path(__file__).resolve().parent / "patch_nutrition_v8.py"

_REF  = BASE / "nutrition/reference"
_PROC = BASE / "nutrition/processed"

# Fichiers pipeline dans l'ordre de priorité
_NC_PATCHED_V8_REF = _REF  / "nutrition_patched_v8.json"
_NC_PATCHED_OUT    = BASE_DIR / "outputs" / "nutrition_patched_v8.json"
_NC_CORRECTED      = _REF  / "nutrition_corrected.json"
_NC_V2             = _PROC / "nutrition_v2.json"


def _first_existing(*paths: Path) -> Path | None:
    return next((p for p in paths if p.exists()), None)


def resolve_source(cli_input: str | None = None) -> Path:
    """
    Résout le fichier nutrition à utiliser, par ordre de priorité :
      1. --input=<path>
      2. nutrition_patched_v8.json (reference/ en priorité, sinon outputs/)
      3. nutrition_corrected.json
      4. nutrition_v2.json
    """
    if cli_input:
        p = Path(cli_input)
        if not p.is_absolute():
            candidate = BASE_DIR / p
            if not candidate.exists():
                candidate = Path.cwd() / p
            p = candidate
        if p.exists():
            return p
        raise FileNotFoundError(f"--input : fichier introuvable : {p}")

    result = _first_existing(
        _NC_PATCHED_V8_REF,
        _NC_PATCHED_OUT,
        _NC_CORRECTED,
        _NC_V2,
    )
    if result is None:
        raise FileNotFoundError(
            "Aucun fichier nutrition trouvé. "
            "Lancer d'abord : patch_nutrition_v8.py ou auto_correct_v6.py"
        )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

_SHORT_TO_LONG: dict[str, str] = {
    "calories":      "calories_kcal",
    "protein":       "protein_g",
    "carbs":         "carbs_g",
    "fat":           "fat_g",
    "fiber":         "fiber_g",
    "sugar":         "sugar_g",
    "saturated_fat": "saturated_fat_g",
    "mufa":          "monounsaturated_fat_g",
    "pufa":          "polyunsaturated_fat_g",
    "trans_fat":     "trans_fat_g",
    "omega3":        "omega3_g",
    "omega3_ala":    "omega3_ala_g",
    "omega6":        "omega6_g",
    "cholesterol":   "cholesterol_mg",
    "calcium":       "calcium_mg",
    "iron":          "iron_mg",
    "potassium":     "potassium_mg",
    "magnesium":     "magnesium_mg",
    "sodium":        "sodium_mg",
    "zinc":          "zinc_mg",
    "selenium":      "selenium_ug",
    "iodine":        "iodine_ug",
    "vitamin_c":     "vitamin_c_mg",
    "vitamin_a":     "vitamin_a_ug",
    "vitamin_d":     "vitamin_d_ug",
    "vitamin_b12":   "vitamin_b12_ug",
    "vitamin_k2":    "vitamin_k2_ug",
    "choline":       "choline_mg",
    "folate":        "folate_ug",
    "polyols":       "polyols_g",
    "organic_acids": "organic_acids_g",
}


def _fused_val(nutrients: dict, field: str):
    v = nutrients.get(field)
    if v is not None:
        return v
    long_key = _SHORT_TO_LONG.get(field)
    if long_key:
        return nutrients.get(long_key, "?")
    return "?"


def load_mapping() -> dict:
    if not MAPPING_FILE.exists():
        return {}
    raw = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
    return {normalize(k): v for k, v in raw.get("mapping", {}).items()}


VARIANT_MAP = {
    "cru": "raw", "crue": "raw", "cuit": "cooked", "cuite": "cooked",
    "raw": "raw", "cooked": "cooked", "dried": "dried", "fresh": "fresh",
    "frozen": "frozen", "roasted": "roasted", "ground": "ground",
}
STOPWORDS = {
    "et", "or", "with", "without", "de", "du", "des", "le", "la", "les",
    "un", "une", "and", "au", "aux", "en", "a", "the", "of",
}


def extract_base(name: str, mapping: dict) -> str:
    name = name.split(",")[0].split(" ou ")[0].strip()
    snake = normalize(name).replace(" ", "_").replace("-", "_")
    if snake in mapping:
        return mapping[snake]
    tokens = snake.split("_")
    out, skip = [], False
    for i, tok in enumerate(tokens):
        if skip:
            skip = False
            continue
        if i + 1 < len(tokens):
            bigram = f"{tok}_{tokens[i+1]}"
            if bigram in mapping:
                out.append(mapping[bigram])
                skip = True
                continue
        if tok in mapping:
            out.append(mapping[tok])
        elif tok not in VARIANT_MAP and tok not in STOPWORDS:
            out.append(tok)
    return "_".join(t.strip("_") for t in out if t) or snake


def _file_info(path: Path) -> str:
    """Retourne une ligne de statut pour un fichier."""
    if not path.exists():
        return "✗ ABSENT"
    stat = path.stat()
    age  = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
    kb   = stat.st_size // 1024
    days = age.days
    hours = age.seconds // 3600
    age_str = f"{days}j" if days > 0 else f"{hours}h"
    return f"✓ {kb:6d} KB  modifié il y a {age_str}"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 : ONTOLOGIE
# ══════════════════════════════════════════════════════════════════════════════

_ONTO_REPORT_SKIP = {"ingredients", "aliases", "reference", "ontology",
                     "scientific_names", "fields", "source_weights"}


def section_ontology(onto: dict, full: bool = False):
    print("═" * 68)
    print("1. RAPPORT ONTOLOGIE")
    print("═" * 68)

    if REPORT_FILE.exists():
        r = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        for k, v in r.items():
            if k in _ONTO_REPORT_SKIP:
                continue
            if k == "aliases_count":
                print(f"  {k}: {v}  (alias ALIM → ontologie)")
            else:
                print(f"  {k}: {v}")
    else:
        total_variants = sum(len(v) for v in onto.values())
        print(f"  Bases    : {len(onto)}")
        print(f"  Variants : {total_variants}")

    if full:
        # Outliers dynamiques : top 15 variants avec le plus grand écart-type
        print("\n  Outliers (std > 10 kcal/g, tous ingrédients) :")
        outlier_rows = []
        for base_key, base_data in onto.items():
            if not isinstance(base_data, dict):
                continue
            for var, vdata in base_data.items():
                if not isinstance(vdata, dict):
                    continue
                stats = vdata.get("stats", {})
                nutrients = vdata.get("nutrients", {})
                for field, s in stats.items():
                    if isinstance(s, dict) and s.get("std", 0) > 10:
                        outlier_rows.append((
                            s["std"], base_key, var, field,
                            s.get("min", "?"), s.get("max", "?"),
                            _fused_val(nutrients, field)
                        ))
        outlier_rows.sort(reverse=True)
        if outlier_rows:
            print(f"  {'Ingrédient/variant':<30} {'Champ':<22} {'min':>7} {'max':>7} "
                  f"{'std':>7} {'fused':>7}")
            print("  " + "-" * 78)
            for std, base, var, field, mn, mx, fused in outlier_rows[:20]:
                label = f"{base}/{var}"
                print(f"  {label:<30} {field:<22} {mn:>7.1f} {mx:>7.1f} "
                      f"{std:>7.1f} {str(fused):>7}")
        else:
            print("  Aucun outlier détecté (std > 10).")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 : COUVERTURE
# ══════════════════════════════════════════════════════════════════════════════

def section_coverage(ings: dict):
    print("\n" + "═" * 68)
    print("2. COUVERTURE CHAMPS — nutrition")
    print("═" * 68)

    ALL_FIELDS = [
        # Macros
        "calories_kcal", "protein_g", "fat_g", "carbs_g", "fiber_g", "sugar_g",
        "starch_g", "alcohol_g",
        # Lipides
        "saturated_fat_g", "monounsaturated_fat_g", "polyunsaturated_fat_g",
        "trans_fat_g", "omega3_g", "omega3_ala_g", "omega3_epa_g", "omega3_dha_g",
        "omega6_g", "cholesterol_mg",
        # Minéraux
        "calcium_mg", "iron_mg", "magnesium_mg", "phosphorus_mg", "potassium_mg",
        "sodium_mg", "zinc_mg", "copper_mg", "manganese_mg", "selenium_ug",
        "iodine_ug",
        # Vitamines
        "vitamin_a_ug", "beta_carotene_ug", "vitamin_d_ug", "vitamin_e_mg",
        "vitamin_k1_ug", "vitamin_k2_ug", "vitamin_c_mg",
        "vitamin_b1_mg", "vitamin_b2_mg", "vitamin_b3_mg", "vitamin_b5_mg",
        "vitamin_b6_mg", "folate_ug", "vitamin_b12_ug", "choline_mg",
        # Autres
        "polyols_g", "organic_acids_g",
    ]

    total = len(ings)

    def get_val(data, field):
        default = data.get("variants", {}).get("default", {})
        v = default.get(field)
        if v is not None:
            return v
        return data.get(field)

    GROUPS = {
        "Macros (8)":    ALL_FIELDS[:8],
        "Lipides (10)":  ALL_FIELDS[8:18],
        "Minéraux (11)": ALL_FIELDS[18:29],
        "Vitamines (15)":ALL_FIELDS[29:44],
        "Autres (2)":    ALL_FIELDS[44:],
    }

    group_scores = {}
    for group_name, fields in GROUPS.items():
        group_total = 0
        group_max   = len(fields) * total
        print(f"\n  ── {group_name} ──")
        for field in fields:
            count = sum(1 for d in ings.values() if get_val(d, field) is not None)
            pct   = count / total * 100 if total else 0
            bar   = "█" * int(pct / 5)
            if pct == 0:
                flag = " ✗ ZÉRO"
            elif pct < 30:
                flag = " ⚠"
            elif pct < 60:
                flag = " ·"
            else:
                flag = ""
            print(f"  {field:<28} {count:4d}/{total} ({pct:5.1f}%)  {bar}{flag}")
            group_total += count
        group_scores[group_name] = group_total / group_max * 100 if group_max else 0

    print("\n  ── Score global par catégorie ──")
    overall = sum(group_scores.values()) / len(group_scores)
    for grp, score in group_scores.items():
        bar = "█" * int(score / 5)
        print(f"  {grp:<18} {score:5.1f}%  {bar}")
    print(f"\n  Score global : {overall:.1f}%")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 : NO-MATCH
# ══════════════════════════════════════════════════════════════════════════════

def section_nomatch(ings: dict, onto: dict, aliases: dict, mapping: dict,
                    full: bool = False):
    print("\n" + "═" * 68)
    print("3. NO-MATCH ONTOLOGIE")
    print("═" * 68)

    onto_keys    = set(onto.keys())
    alias_keys   = set(aliases.keys())
    no_match     = []
    alias_resolved = []

    for name in ings:
        base = extract_base(name, mapping)
        if base in onto_keys:
            continue
        if name in alias_keys or base in alias_keys:
            alias_resolved.append(name)
            continue
        if full:
            candidates = [
                k for k in onto_keys
                if (base[:4] in k or k[:4] in base or
                    (base.split("_") and base.split("_")[0] in k))
            ][:3]
        else:
            candidates = []
        no_match.append((name, base, candidates))

    print(f"  No-match : {len(no_match)} / {len(ings)}")
    if alias_resolved:
        print(f"  Résolus via alias : {len(alias_resolved)}"
              f"  ({', '.join(sorted(alias_resolved)[:8])}"
              f"{'…' if len(alias_resolved) > 8 else ''})")

    limit = len(no_match) if full else min(40, len(no_match))
    if full and no_match:
        print(f"\n  {'Ingrédient':<30} {'Base calculée':<35} {'Clés proches ontologie'}")
        print("  " + "-" * 90)
    for name, base, cands in sorted(no_match)[:limit]:
        if full:
            print(f"  {name:<30} {base:<35} {cands}")
        else:
            print(f"  '{name}'  =>  '{base}'")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 : LOG AUTO-CORRECT
# ══════════════════════════════════════════════════════════════════════════════

def section_log():
    print("\n" + "═" * 68)
    print("4. STATS AUTO-CORRECT")
    print("═" * 68)
    if not LOG_FILE.exists():
        print("  Log absent — lancer auto_correct_v6.py d'abord")
        return
    log   = json.loads(LOG_FILE.read_text(encoding="utf-8"))
    stats = log.get("stats", {})
    for k, v in stats.items():
        if k != "by_field":
            print(f"  {k}: {v}")
    bf = stats.get("by_field", {})
    if bf:
        print(f"\n  Corrections par champ :")
        for field, count in sorted(bf.items(), key=lambda x: -x[1]):
            if count:
                bar = "▪" * min(count, 20)
                print(f"    {field:<28} {count:3d}  {bar}")

    # Enrichissements détaillés (v2.2)
    enrichissements = log.get("enrichissements", [])
    if enrichissements:
        print(f"\n  Enrichissements ({len(enrichissements)}) :")
        for e in enrichissements[:15]:
            ing  = e.get("ingredient", "?")
            flds = e.get("fields", [])
            src  = e.get("source", "")
            print(f"    {ing:<30} +{len(flds)} champs  {src}")
        if len(enrichissements) > 15:
            print(f"    … et {len(enrichissements)-15} autres")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 : ÉTAT DU PIPELINE (nouveau v2.2)
# ══════════════════════════════════════════════════════════════════════════════

def section_pipeline():
    print("\n" + "═" * 68)
    print("5. ÉTAT DU PIPELINE")
    print("═" * 68)

    # Fichiers sources (raws)
    raws = [
        ("CIQUAL flat v3",   BASE / "nutrition/reference/ciqual_flat_v3.json"),
        ("USDA flat v2",     BASE / "nutrition/reference/usda_flat_v2.json"),
        ("CNF full v10",     BASE / "nutrition/reference/cnf_full_v10.json"),
        ("Taxonomy",         BASE / "taxonomy/taxonomy_session_*.json"),
        ("Mapping FR→EN",    MAPPING_FILE),
    ]
    # Fichiers pipeline
    pipeline_files = [
        ("── ONTOLOGIE ──",       None),
        ("ontology_v6.json",      _ONTO_V6),
        ("ontology_v6_report",    REPORT_FILE),
        ("reference_db.json",     BASE / "nutrition/reference/reference_db.json"),
        ("── AUTO-CORRECT ──",    None),
        ("nutrition_corrected",   _NC_CORRECTED),
        ("corrections_log",       LOG_FILE),
        ("── PATCH ──",           None),
        ("nutrition_patched_v8",  _NC_PATCHED_V8_REF),
        ("patch_report_v8",       BASE_DIR / "outputs/patch_report_v8.json"),
        ("── PROMU ──",           None),
        ("nutrition_v2.json",     _NC_V2),
        ("nutrition_aliases_v6",  BASE / "nutrition/reference/nutrition_aliases_v6.json"),
        ("── SCRIPTS ──",         None),
        ("build_ontology_v6.py",  Path(__file__).parent / "build_ontology_v6.py"),
        ("auto_correct_v6.py",    Path(__file__).parent / "auto_correct_v6.py"),
        ("patch_nutrition_v8.py", _PATCH_V8_FILE),
        ("promote_nutrition.py",  Path(__file__).parent / "promote_nutrition.py"),
        ("validator_v12.py",      Path(__file__).parent / "validator_v12.py"),
    ]

    for label, path in pipeline_files:
        if path is None:
            print(f"\n  {label}")
            continue
        # Glob pour les fichiers avec wildcard
        if "*" in str(path):
            matches = sorted(Path(path.parent).glob(path.name))
            path = matches[-1] if matches else path
        info = _file_info(path)
        # Extraire la version si possible
        version_tag = ""
        if path.exists() and path.suffix == ".json":
            try:
                d = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
                v = (d.get("schema_version") or d.get("version") or
                     d.get("_meta", {}).get("version") if isinstance(d, dict) else None)
                if v:
                    version_tag = f"  [v{v}]"
            except Exception:
                pass
        print(f"  {label:<30} {info}{version_tag}")

    # Version nutrition_v2
    if _NC_V2.exists():
        try:
            d = json.loads(_NC_V2.read_text(encoding="utf-8"))
            n_ings = len(d.get("ingredients", {}))
            total_vars = sum(
                len(ing.get("variants", {}))
                for ing in d.get("ingredients", {}).values()
            )
            print(f"\n  Contenu nutrition_v2 : {n_ings} ingrédients, {total_vars} variants")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 : PATCH ACTIF (nouveau v2.2)
# ══════════════════════════════════════════════════════════════════════════════

def _parse_patch_v8():
    """
    Parse patch_nutrition_v8.py pour extraire URGENT_FIXES et BLOCKED_PROPOSALS
    sans l'importer (évite les side-effects du script).
    Retourne (urgent_keys, blocked_keys) sous forme de listes de strings.
    """
    if not _PATCH_V8_FILE.exists():
        return [], {}

    src = _PATCH_V8_FILE.read_text(encoding="utf-8", errors="replace")

    # URGENT_FIXES : extraire les clés ("base", "variant")
    urgent_keys = re.findall(r'^\s+\("(\w+)",\s*"(\w+)"\)\s*:', src, re.MULTILINE)

    # BLOCKED_PROPOSALS : extraire les clés de premier niveau du dict
    bp_match = re.search(
        r'BLOCKED_PROPOSALS\s*:\s*dict\[.*?\]\s*=\s*\{(.*?)\n\}',
        src, re.DOTALL
    )
    blocked = {}
    if bp_match:
        block_src = bp_match.group(1)
        # Le dict contient des commentaires # entre entrées — itérer sur les
        # lignes en sautant les commentaires avant d'appliquer le regex.
        # Stratégie : supprimer les lignes de commentaires purs, puis matcher.
        clean_lines = []
        for line in block_src.split('\n'):
            stripped = line.strip()
            if stripped.startswith('#') or stripped == '':
                continue
            clean_lines.append(line)
        clean_src = '\n'.join(clean_lines)
        for m in re.finditer(
            r'"(\w+)"\s*:\s*\{([^}]+)\}',
            clean_src, re.DOTALL
        ):
            ing = m.group(1)
            fields = re.findall(r'"(\w+)"\s*:', m.group(2))
            blocked[ing] = [f for f in fields if not f.startswith('_')]

    return urgent_keys, blocked


def section_patch():
    print("\n" + "═" * 68)
    print("6. PATCH ACTIF — patch_nutrition_v8.py")
    print("═" * 68)

    if not _PATCH_V8_FILE.exists():
        print(f"  ✗ patch_nutrition_v8.py introuvable : {_PATCH_V8_FILE}")
        return

    urgent_keys, blocked = _parse_patch_v8()

    # Grouper les urgent fixes par ingrédient
    from collections import defaultdict
    by_ing = defaultdict(list)
    for base, variant in urgent_keys:
        by_ing[base].append(variant)

    print(f"\n  URGENT_FIXES : {len(urgent_keys)} entrées ({len(by_ing)} ingrédients)")
    print(f"  {'Ingrédient':<25} {'Variants corrigés'}")
    print("  " + "─" * 55)
    for ing in sorted(by_ing.keys()):
        variants = ", ".join(by_ing[ing])
        print(f"  {ing:<25} [{variants}]")

    print(f"\n  BLOCKED_PROPOSALS : {len(blocked)} ingrédients protégés")
    print(f"  (les proposals validator ne peuvent pas écraser ces champs)")
    print(f"  {'Ingrédient':<20} {'Champs bloqués'}")
    print("  " + "─" * 65)
    for ing in sorted(blocked.keys()):
        fields = blocked[ing][:8]
        suffix = "…" if len(blocked[ing]) > 8 else ""
        print(f"  {ing:<20} {', '.join(fields)}{suffix}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 : INGRÉDIENTS MANQUANTS (nouveau v2.2)
# ══════════════════════════════════════════════════════════════════════════════

def section_missing(ings: dict, onto: dict):
    """
    Affiche les ingrédients NC absents de l'onto (P1 + P3).
    P1 = dans NC + absent onto + présent dans raws (données disponibles)
    P3 = dans NC + absent onto + absent raws (données à créer)
    """
    print("\n" + "═" * 68)
    print("7. INGRÉDIENTS MANQUANTS")
    print("═" * 68)

    onto_keys = set(onto.keys())
    nc_keys   = set(ings.keys())

    # NC absents de onto
    missing = sorted(nc_keys - onto_keys)
    print(f"\n  Dans NC mais absents de l'onto : {len(missing)}")

    if not missing:
        print("  ✓ Tous les ingrédients NC ont un correspondant dans l'onto.")
        return

    # Essayer de détecter si des données existent dans les raws
    # en cherchant les fichiers raws disponibles
    raw_names = set()
    for raw_f in [
        BASE / "nutrition/reference/ciqual_flat_v3.json",
        BASE / "nutrition/reference/usda_flat_v2.json",
        BASE / "nutrition/reference/cnf_full_v10.json",
    ]:
        if raw_f.exists():
            try:
                raw_d = json.loads(raw_f.read_text(encoding="utf-8"))
                for food in raw_d.get("foods_flat", []):
                    bn = food.get("base_name", "")
                    if bn:
                        raw_names.add(normalize(bn).replace(" ", "_").replace("-", "_"))
            except Exception:
                pass

    p1, p3 = [], []
    for k in missing:
        # Chercher un match dans les noms raws normalisés
        has_raw = k in raw_names or any(
            k in rn or rn in k
            for rn in raw_names
            if abs(len(k) - len(rn)) < 5 and len(k) > 4
        )
        if has_raw:
            p1.append(k)
        else:
            p3.append(k)

    if p1:
        print(f"\n  P1 — Données raws disponibles ({len(p1)}) :")
        print("  (Ces ingrédients pourraient être intégrés via override dans build_ontology)")
        for k in p1:
            print(f"    · {k}")

    if p3:
        print(f"\n  P3 — Sans données raws ({len(p3)}) :")
        print("  (Données à créer manuellement ou via USDA FDC)")
        for k in p3:
            # Chercher une valeur dans nc pour montrer les kcal disponibles
            nc_entry  = ings.get(k, {})
            default_v = nc_entry.get("variants", {}).get("default", nc_entry)
            kcal      = default_v.get("calories_kcal") or default_v.get("calories")
            kcal_tag  = f"  ({kcal:.0f} kcal dans nc)" if kcal else "  (kcal absent nc)"
            print(f"    · {k:<35}{kcal_tag}")

    # Ingrédients dans onto mais pas dans nc (information bonus)
    onto_not_nc = sorted((onto_keys - nc_keys) & set(k for k in onto_keys
                          if not k.startswith("_")))
    if onto_not_nc:
        sample = onto_not_nc[:8]
        print(f"\n  Dans l'onto mais pas dans NC : {len(onto_not_nc)}")
        print(f"  (Ces ingrédients existent dans les raws mais ne sont pas utilisés dans des recettes)")
        print(f"  Exemples : {', '.join(sample)}{'…' if len(onto_not_nc) > 8 else ''}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="_diagnose_v2 — outil de diagnostic ALIM nutrition pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
sections disponibles :
  onto      Rapport ontologie + outliers (--full pour top 20)
  coverage  Couverture champs nutritionnels par catégorie
  nomatch   Ingrédients NC sans correspondant dans l'onto
  log       Statistiques auto-correct (corrections + enrichissements)
  pipeline  État des fichiers du pipeline (dates, tailles, versions)
  patch     URGENT_FIXES + BLOCKED_PROPOSALS actifs dans patch_v8
  missing   Ingrédients NC absents de l'onto (P1 : raws dispo / P3 : à créer)

exemples :
  python _diagnose_v2.py                          # rapport complet
  python _diagnose_v2.py --section pipeline       # état des fichiers
  python _diagnose_v2.py --section patch          # fixes actifs
  python _diagnose_v2.py --section missing        # ingrédients manquants
  python _diagnose_v2.py --section coverage       # couverture nutritionnelle
  python _diagnose_v2.py --full --section onto    # outliers complets
  python _diagnose_v2.py --input nutrition_patched_v8.json
        """
    )
    parser.add_argument("--full",    action="store_true",
                        help="Détail complet (outliers + no-match)")
    parser.add_argument("--section",
                        choices=["onto", "coverage", "nomatch", "log",
                                 "pipeline", "patch", "missing"],
                        default=None,
                        help="Afficher une section uniquement")
    parser.add_argument("--input",   default=None,
                        help="Fichier nutrition source (ex: nutrition_patched_v8.json)")
    args = parser.parse_args()

    # ── Résolution source nutrition ─────────────────────────────────────────
    try:
        nc_file = resolve_source(args.input)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # ── Chargement ontologie ────────────────────────────────────────────────
    raw_onto = json.loads(ONTO_FILE.read_text(encoding="utf-8")) if ONTO_FILE.exists() else {}
    onto = (raw_onto.get("ingredients")
            or raw_onto.get("ontology")
            or raw_onto.get("reference")
            or raw_onto)
    aliases: dict = raw_onto.get("aliases", {})

    # ── Chargement nutrition ────────────────────────────────────────────────
    nc   = json.loads(nc_file.read_text(encoding="utf-8")) if nc_file.exists() else {}
    ings = nc.get("ingredients", nc)

    mapping = load_mapping()

    # ── Header ──────────────────────────────────────────────────────────────
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n  {'─'*62}")
    print(f"  _diagnose_v2  [{now}]")
    print(f"  {'─'*62}")
    print(f"  Ontologie : {ONTO_FILE.name}  ({len(onto)} bases)")
    print(f"  Nutrition : {nc_file.name}  ({len(ings)} ingrédients)")
    if aliases:
        print(f"  Alias     : {len(aliases)} (ALIM → ontologie)")
    print()

    # ── Dispatch sections ───────────────────────────────────────────────────
    s = args.section
    run_all = s is None

    if run_all or s == "pipeline":
        section_pipeline()
    if run_all or s == "onto":
        section_ontology(onto, full=args.full)
    if run_all or s == "coverage":
        section_coverage(ings)
    if run_all or s == "nomatch":
        section_nomatch(ings, onto, aliases, mapping, full=args.full)
    if run_all or s == "log":
        section_log()
    if run_all or s == "patch":
        section_patch()
    if run_all or s == "missing":
        section_missing(ings, onto)


if __name__ == "__main__":
    main()
