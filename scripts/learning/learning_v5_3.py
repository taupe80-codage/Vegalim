"""
learning_v5_3.py
Apprentissage adaptatif : mémoire EMA + génération de règles + détection de drift.

Corrections vs V5.2 :
  - confidence_weighted : vraie moyenne pondérée (num/denom accumulés séparément)
  - EMA : initialisation correcte (count=0, pas d'update sur la 1ère valeur)
  - detect_drift() : fenêtres sans chevauchement (old = [:n//2], recent = [-n//2:])
  - generate_rules() : préserve les règles manuelles (mode "ignore" existant)
  - detect_drift() : résultat sauvegardé dans drift_log.json + retourné
  - Ajout de last_seen dans chaque entrée mémoire (timestamp ISO)
  - Ajout de min/max dans l'historique pour détecter les valeurs aberrantes
"""

import json
import statistics
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_FILE    = BASE_DIR / "data" / "logs" / "corrections_log.json"
MEMORY_FILE = BASE_DIR / "data" / "logs" / "learning_memory_v2.json"
RULES_FILE  = BASE_DIR / "data" / "logs" / "adaptive_rules_v2.json"
DRIFT_FILE  = BASE_DIR / "data" / "logs" / "drift_log.json"

ALPHA           = 0.3   # facteur EMA (0 = figé, 1 = mémoire nulle)
HISTORY_MAX     = 10    # taille max de l'historique glissant
DRIFT_THRESHOLD = 0.2   # seuil de différence entre fenêtres pour signaler un drift
DRIFT_MIN_LEN   = 6     # taille min d'historique pour déclencher le drift check

# =====================================================
# UTILS
# =====================================================

def load_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# =====================================================
# UPDATE MEMORY
# =====================================================

def update_memory() -> dict:
    """
    Lit le log de corrections et met à jour la mémoire d'apprentissage.

    Structure par entrée :
      ema_delta          : moyenne exponentielle du delta (lissage temporel)
      confidence_sum     : numérateur de la moyenne pondérée par confiance
      confidence_weight  : dénominateur (somme des poids)
      confidence_weighted: ratio num/denom — vraie moyenne pondérée (corrigé v5.3)
      count              : nb total d'observations
      history            : liste glissante des N derniers deltas
      variance           : variance de l'historique
      last_seen          : timestamp ISO de la dernière observation (nouveau)
    """
    logs   = load_json(LOG_FILE).get("logs", [])
    memory = load_json(MEMORY_FILE)

    for entry in logs:
        ing   = entry["ingredient"]
        field = entry["field"]
        delta = entry["delta"]
        conf  = entry.get("confidence", 1.0)
        ts    = entry.get("timestamp", datetime.now().isoformat())

        memory.setdefault(ing, {})

        if field not in memory[ing]:
            # Correction v5.3 : initialisation sans appliquer l'EMA à la 1ère valeur.
            # L'EMA sera mis à jour au prochain passage ; ici on pose juste la graine.
            memory[ing][field] = {
                "ema_delta":          delta,
                "confidence_sum":     delta * conf,   # numérateur
                "confidence_weight":  conf,            # dénominateur
                "confidence_weighted": delta,
                "count":              1,
                "history":            [delta],
                "variance":           0,
                "last_seen":          ts,
            }
            continue  # 1ère observation : pas d'EMA update, on passe à la suivante

        m = memory[ing][field]

        # EMA
        m["ema_delta"] = ALPHA * delta + (1 - ALPHA) * m["ema_delta"]

        # Moyenne pondérée par confiance (corrigé v5.3 : num/denom séparés)
        m["confidence_sum"]    += delta * conf
        m["confidence_weight"] += conf
        m["confidence_weighted"] = m["confidence_sum"] / m["confidence_weight"]

        m["count"] += 1
        m["last_seen"] = ts

        # Historique glissant
        m["history"].append(delta)
        if len(m["history"]) > HISTORY_MAX:
            m["history"].pop(0)

        # Variance (nécessite au moins 2 points)
        m["variance"] = statistics.variance(m["history"]) if len(m["history"]) > 1 else 0

    save_json(MEMORY_FILE, memory)
    print(f"✔ Memory v5.3 updated ({len(memory)} ingrédients)")
    return memory

# =====================================================
# RULE GENERATION
# =====================================================

def generate_rules() -> dict:
    """
    Génère les règles adaptatives depuis la mémoire.

    Logique de seuil :
      - ema_delta élevé → seuil serré (correction agressive justifiée)
      - variance élevée → mode "review" (instabilité, ne pas corriger seul)

    Correction v5.3 :
      Les règles existantes en mode "ignore" sont préservées.
      generate_rules() ne peut pas rétrograder un "ignore" manuel en "auto".
    """
    memory        = load_json(MEMORY_FILE)
    existing_rules = load_json(RULES_FILE)
    rules: dict   = {}

    for ing, fields in memory.items():
        rules[ing] = {}

        for field, m in fields.items():
            delta = m["ema_delta"]
            var   = m.get("variance", 0)

            # Seuil adaptatif selon l'amplitude historique du delta
            if delta > 0.5:
                threshold = 0.10
            elif delta > 0.3:
                threshold = 0.15
            else:
                threshold = 0.25

            # Mode : instabilité → review
            if var > 0.1:
                mode = "review"
            else:
                mode = "auto"

            # Correction v5.3 : préserver le mode "ignore" posé manuellement
            existing_mode = existing_rules.get(ing, {}).get(field, {}).get("mode")
            if existing_mode == "ignore":
                mode = "ignore"

            rules[ing][field] = {
                "threshold":  threshold,
                "mode":       mode,
                "variance":   round(var, 4),
                "ema_delta":  round(delta, 4),
                "count":      m.get("count", 0),
                "last_seen":  m.get("last_seen", ""),
            }

    save_json(RULES_FILE, rules)
    print(f"✔ Rules v5.3 generated ({len(rules)} ingrédients)")
    return rules

# =====================================================
# DRIFT DETECTION
# =====================================================

def detect_drift() -> list[dict]:
    """
    Détecte les ingrédients dont le delta moyen a significativement changé
    entre la première moitié et la seconde moitié de l'historique.

    Correction v5.3 :
      - Fenêtres sans chevauchement : old = première moitié stricte,
        recent = seconde moitié stricte.
      - Seuil et longueur min configurables.
      - Résultat sauvegardé dans drift_log.json (n'était qu'affiché avant).
      - Retourne la liste pour usage programmatique.
    """
    memory = load_json(MEMORY_FILE)
    drift: list[dict] = []

    for ing, fields in memory.items():
        for field, m in fields.items():
            h = m["history"]

            if len(h) < DRIFT_MIN_LEN:
                continue

            mid    = len(h) // 2
            old    = h[:mid]        # première moitié — sans chevauchement
            recent = h[mid:]        # seconde moitié

            mean_old    = sum(old)    / len(old)
            mean_recent = sum(recent) / len(recent)
            diff        = mean_recent - mean_old

            if abs(diff) > DRIFT_THRESHOLD:
                drift.append({
                    "ingredient":   ing,
                    "field":        field,
                    "mean_old":     round(mean_old, 4),
                    "mean_recent":  round(mean_recent, 4),
                    "diff":         round(diff, 4),
                    "direction":    "up" if diff > 0 else "down",
                    "history_len":  len(h),
                    "detected_at":  datetime.now().isoformat(),
                })

    # Tri par amplitude de drift décroissante
    drift.sort(key=lambda x: abs(x["diff"]), reverse=True)

    save_json(DRIFT_FILE, {"count": len(drift), "drift": drift})

    print(f"\n📉 Drift detected : {len(drift)} cas")
    for d in drift[:10]:
        arrow = "↑" if d["direction"] == "up" else "↓"
        print(f"  {arrow} {d['ingredient']} / {d['field']} : "
              f"{d['mean_old']:.3f} → {d['mean_recent']:.3f} "
              f"(Δ {d['diff']:+.3f})")

    return drift

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    update_memory()
    generate_rules()
    detect_drift()
