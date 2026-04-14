"""
promote_nutrition.py
════════════════════
Promeut nutrition_corrected.json → nutrition_v2.json après validation.

Workflow :
  1. Vérifie que nutrition_corrected.json existe et est plus récent que nutrition_v2.json
  2. Lit le numéro de version actuel dans nutrition_v2.json (_meta.schema_version)
  3. Archive nutrition_v2.json → archive/nutrition_v{N}.json
  4. Copie nutrition_corrected.json → nutrition_v2.json
  5. Met à jour _meta.schema_version + _meta.promoted_date dans le nouveau nutrition_v2.json
  6. (Optionnel) supprime nutrition_corrected.json si --clean

Usage :
  python scripts/nutrition/promote_nutrition.py            # dry-run (affiche ce qui sera fait)
  python scripts/nutrition/promote_nutrition.py --confirm  # exécute la promotion
  python scripts/nutrition/promote_nutrition.py --confirm --clean  # + supprime corrected
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parents[2]

NUTRITION_DIR  = BASE_DIR / "backend" / "data" / "nutrition"
PROCESSED_DIR  = NUTRITION_DIR / "processed"
REFERENCE_DIR  = NUTRITION_DIR / "reference"
ARCHIVE_DIR    = PROCESSED_DIR / "archive"

CANONICAL_FILE  = PROCESSED_DIR / "nutrition_v2.json"
CORRECTED_FILE  = REFERENCE_DIR / "nutrition_corrected.json"

TODAY = datetime.now().strftime("%Y-%m-%d")


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_meta(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        db = json.load(f)
    return db.get("_meta", {})


def read_schema_version(meta: dict, filepath: Path) -> str:
    """
    Lit schema_version depuis _meta (champ canonique).
    Accepte aussi 'version' pour la rétro-compatibilité.
    Lève ValueError si aucun champ n'est présent — refus de deviner depuis le nom de fichier.
    """
    version = meta.get("schema_version") or meta.get("version")
    if not version:
        raise ValueError(
            f"Impossible de déterminer la version de {filepath.name} : "
            f"_meta.schema_version absent. Vérifier le fichier avant promotion."
        )
    return str(version)


def next_archive_path(version_str: str) -> Path:
    """
    Détermine le chemin d'archive : archive/nutrition_v{N}.json
    Si version_str = "2.1", archive = nutrition_v2.1.json
    Si déjà pris, incrémente le suffixe : nutrition_v2.1.1.json
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    base_name = f"nutrition_v{version_str}.json"
    candidate = ARCHIVE_DIR / base_name
    counter = 1
    while candidate.exists():
        candidate = ARCHIVE_DIR / f"nutrition_v{version_str}.{counter}.json"
        counter += 1
    return candidate


def bump_version(version_str: str) -> str:
    """
    Incrémente la version mineure : "2" → "2.1", "2.1" → "2.2", "2.9" → "2.10"
    """
    parts = str(version_str).split(".")
    if len(parts) == 1:
        return f"{parts[0]}.1"
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except ValueError:
        parts.append("1")
    return ".".join(parts)


# ── Main ──────────────────────────────────────────────────────────────────────

def promote(dry_run: bool = True, clean_corrected: bool = False):
    confirm = not dry_run

    print("══════════════════════════════════════════════════════")
    print(f"  PROMOTE NUTRITION {'[DRY-RUN]' if dry_run else '[EXÉCUTION]'}")
    print("══════════════════════════════════════════════════════")

    # ── Vérifications préalables ─────────────────────────────────────────────
    if not CORRECTED_FILE.exists():
        print(f"  ❌ Fichier source introuvable :\n     {CORRECTED_FILE}")
        print("     Lancer d'abord : python scripts/nutrition/auto_correct_v6.py")
        return 1

    if not CANONICAL_FILE.exists():
        print(f"  ⚠  nutrition_v2.json absent — création directe sans archivage.")
        archive_path = None
        current_version = "1"
    else:
        # Fraîcheur relative
        corrected_mtime = CORRECTED_FILE.stat().st_mtime
        canonical_mtime = CANONICAL_FILE.stat().st_mtime
        if corrected_mtime <= canonical_mtime:
            print("  ⚠  nutrition_corrected.json n'est pas plus récent que nutrition_v2.json.")
            print("     Relancer auto_correct_v6.py pour regénérer, ou utiliser --force.")

        meta = read_meta(CANONICAL_FILE)
        try:
            current_version = read_schema_version(meta, CANONICAL_FILE)
        except ValueError as e:
            print(f"  ❌ {e}")
            return 1
        archive_path = next_archive_path(current_version)

    new_version = bump_version(current_version)

    # ── Résumé des opérations ─────────────────────────────────────────────────
    print(f"\n  Version actuelle : {current_version}")
    print(f"  Nouvelle version : {new_version}")
    if archive_path:
        print(f"  Archive          : {archive_path.relative_to(BASE_DIR)}")
    print(f"  Cible            : {CANONICAL_FILE.relative_to(BASE_DIR)}")
    print(f"  Source           : {CORRECTED_FILE.relative_to(BASE_DIR)}")
    if clean_corrected:
        print(f"  Nettoyage        : suppression de nutrition_corrected.json après promotion")

    if dry_run:
        print("\n  ──────────────────────────────────────────────────")
        print("  Dry-run : aucune modification. Ajouter --confirm pour exécuter.")
        print("  ══════════════════════════════════════════════════\n")
        return 0

    # ── Exécution ────────────────────────────────────────────────────────────
    print()

    # 1. Archiver l'ancien canonical
    if archive_path and CANONICAL_FILE.exists():
        shutil.copy2(CANONICAL_FILE, archive_path)
        print(f"  💾 Archivé  → {archive_path.name}")

    # 2. Charger corrected, mettre à jour _meta, écrire canonical
    with open(CORRECTED_FILE, encoding="utf-8") as f:
        db = json.load(f)

    db.setdefault("_meta", {})
    db["_meta"]["schema_version"]   = new_version
    db["_meta"]["promoted_date"]    = TODAY
    db["_meta"]["promoted_from"]    = CORRECTED_FILE.name
    db["_meta"]["previous_version"] = current_version

    with open(CANONICAL_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    ing_count = len(db.get("ingredients", {}))
    print(f"  ✔  Promu    → {CANONICAL_FILE.name}  (v{new_version}, {ing_count} ingrédients)")

    # 3. Optionnel : supprimer nutrition_corrected.json
    if clean_corrected:
        CORRECTED_FILE.unlink()
        print(f"  🗑  Supprimé → {CORRECTED_FILE.name}")

    print(f"\n  ══════════════════════════════════════════════════")
    print(f"  Promotion v{current_version} → v{new_version} terminée.")
    print(f"  Archive : {ARCHIVE_DIR.relative_to(BASE_DIR)}/\n")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    confirm      = "--confirm" in args
    clean        = "--clean"   in args
    sys.exit(promote(dry_run=not confirm, clean_corrected=clean))