"""
report_builder.py
Rapport consolidé : corrections, drift, règles adaptatives.

Corrections vs version originale :
  - open() remplacé par context manager
  - REPORT.parent.mkdir() ajouté
  - ensure_ascii=False à l'écriture
  - Intègre drift_log.json et adaptive_rules_v2.json
  - Statistiques enrichies : top ingrédients, distribution deltas, taux de match
  - Timestamp dans le rapport
"""

import json
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

LOG_FILE    = BASE_DIR / "data" / "logs" / "corrections_log.json"
DRIFT_FILE  = BASE_DIR / "data" / "logs" / "drift_log.json"
RULES_FILE  = BASE_DIR / "data" / "logs" / "adaptive_rules_v2.json"
REPORT_FILE = BASE_DIR / "outputs" / "final_report.json"

# =====================================================
# UTILS
# =====================================================

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# =====================================================
# ANALYSE DES CORRECTIONS
# =====================================================

def analyze_corrections(logs: list[dict]) -> dict:
    """
    Produit des statistiques détaillées depuis les entrées de log.
    """
    if not logs:
        return {}

    field_counts:      Counter = Counter()
    field_deltas:      dict    = {}
    ingredient_counts: Counter = Counter()
    mode_counts:       Counter = Counter()
    delta_buckets             = {"<0.1": 0, "0.1-0.2": 0, "0.2-0.5": 0, ">0.5": 0}

    for log in logs:
        field  = log["field"]
        delta  = log.get("delta", 0)
        ing    = log["ingredient"]
        mode   = log.get("mode", "auto")

        field_counts[field]      += 1
        ingredient_counts[ing]   += 1
        mode_counts[mode]        += 1
        field_deltas.setdefault(field, []).append(delta)

        if delta < 0.1:
            delta_buckets["<0.1"] += 1
        elif delta < 0.2:
            delta_buckets["0.1-0.2"] += 1
        elif delta < 0.5:
            delta_buckets["0.2-0.5"] += 1
        else:
            delta_buckets[">0.5"] += 1

    # Statistiques par champ
    field_stats = {}
    for field, deltas in field_deltas.items():
        field_stats[field] = {
            "count":  len(deltas),
            "mean":   round(statistics.mean(deltas), 4),
            "median": round(statistics.median(deltas), 4),
            "max":    round(max(deltas), 4),
            "stdev":  round(statistics.stdev(deltas), 4) if len(deltas) > 1 else 0,
        }

    return {
        "by_field":           dict(field_counts.most_common()),
        "field_stats":        field_stats,
        "top_ingredients":    ingredient_counts.most_common(20),
        "by_mode":            dict(mode_counts),
        "delta_distribution": delta_buckets,
    }

# =====================================================
# ANALYSE DES RÈGLES
# =====================================================

def analyze_rules(rules: dict) -> dict:
    """Résumé des règles adaptatives générées."""
    if not rules:
        return {}

    mode_counts: Counter = Counter()
    total_fields = 0

    for fields in rules.values():
        for rule in fields.values():
            mode_counts[rule.get("mode", "auto")] += 1
            total_fields += 1

    return {
        "total_ingredients": len(rules),
        "total_rules":       total_fields,
        "by_mode":           dict(mode_counts),
    }

# =====================================================
# MAIN
# =====================================================

def run() -> dict:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Chargement des sources
    log_data  = load_json(LOG_FILE)
    drift_data = load_json(DRIFT_FILE)
    rules_data = load_json(RULES_FILE)

    logs  = log_data.get("logs", [])
    stats = log_data.get("stats", {})

    # Taux de match
    total   = stats.get("total", 0)
    no_match = stats.get("skipped_no_match", 0)
    match_rate = round((total - no_match) / total * 100, 1) if total else 0

    report = {
        "generated_at":   datetime.now().isoformat(),
        "summary":        stats,
        "match_rate_pct": match_rate,
        "corrections":    analyze_corrections(logs),
        "drift":  {
            "count": drift_data.get("count", 0),
            "top":   drift_data.get("drift", [])[:10],
        },
        "rules":          analyze_rules(rules_data),
        "total_logs":     len(logs),
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Affichage console
    print("\n════════════════════════════════════")
    print("  PIPELINE REPORT")
    print(f"  {report['generated_at'][:19]}")
    print("════════════════════════════════════")
    print(f"  Total ingrédients  : {total}")
    print(f"  Match rate         : {match_rate}%")
    print(f"  Corrections        : {stats.get('corrected', 0)}")
    print(f"  En révision        : {stats.get('review', 0)}")
    print(f"  Ignorés            : {stats.get('ignored', 0)}")
    print(f"  Drift détectés     : {drift_data.get('count', 0)}")
    if report["corrections"]:
        print(f"  Champ le + corrigé : {next(iter(report['corrections']['by_field']))}")
        top3 = report["corrections"]["top_ingredients"][:3]
        print(f"  Top 3 ingrédients  : {[i for i,_ in top3]}")
    print(f"  Rapport            : {REPORT_FILE}")
    print("════════════════════════════════════")

    return report


if __name__ == "__main__":
    run()
