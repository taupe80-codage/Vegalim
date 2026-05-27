"""
cleanup_nutrition_backups.py — Nettoie les backups nutrition_v2_backup_*.json

Usage :
    python backend/scripts/cleanup_nutrition_backups.py [--dry-run] [--keep N]

Options :
    --dry-run   Affiche ce qui serait supprimé sans supprimer
    --keep N    Nombre de backups récents à conserver (défaut : 3)

Les fichiers conservés :
    - nutrition_v2.json              (fichier actif)
    - nutrition_v2.zip               (archive)
    - nutrition_v2_rebuilt.json      (reconstruction)
    - nutrition_v2_groupA_merged.json / nutrition_v2_groupB_cleaned.json
    - nutrition_v2_base_recipe_backup.json
    - Les N backups les plus récents (par date dans le nom)
"""
import argparse
import re
import sys
from pathlib import Path


PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "nutrition" / "processed"

PROTECTED = {
    "nutrition_v2.json",
    "nutrition_v2.zip",
    "nutrition_v2_rebuilt.json",
    "nutrition_v2_groupA_merged.json",
    "nutrition_v2_groupB_cleaned.json",
    "nutrition_v2_base_recipe_backup.json",
}

BACKUP_PATTERN = re.compile(r"^nutrition_v2_backup_(\d{8}_\d{6})\.json$")


def main():
    parser = argparse.ArgumentParser(description="Nettoyage des backups nutrition_v2")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans suppression")
    parser.add_argument("--keep", type=int, default=3, help="Nombre de backups récents à conserver")
    args = parser.parse_args()

    # Lister les backups
    backups = []
    for f in PROCESSED_DIR.iterdir():
        if f.name in PROTECTED:
            continue
        m = BACKUP_PATTERN.match(f.name)
        if m:
            backups.append((m.group(1), f))  # (timestamp_str, path)

    backups.sort(key=lambda x: x[0], reverse=True)  # Plus récents en premier

    to_keep   = {f for _, f in backups[: args.keep]}
    to_delete = [f for _, f in backups if f not in to_keep]

    print(f"Dossier    : {PROCESSED_DIR}")
    print(f"Backups    : {len(backups)} trouvés")
    print(f"À conserver: {len(to_keep)} (les {args.keep} plus récents)")
    print(f"À supprimer: {len(to_delete)}")
    print()

    if not to_delete:
        print("Rien à supprimer.")
        return

    total_mb = sum(f.stat().st_size for f in to_delete) / 1_048_576
    print(f"Espace libéré : ~{total_mb:.1f} MB")
    print()

    for f in sorted(to_delete):
        size_mb = f.stat().st_size / 1_048_576
        if args.dry_run:
            print(f"  [DRY-RUN] Suppression : {f.name} ({size_mb:.1f} MB)")
        else:
            f.unlink()
            print(f"  Supprimé  : {f.name} ({size_mb:.1f} MB)")

    if args.dry_run:
        print("\n[DRY-RUN] Aucun fichier supprime. Relancer sans --dry-run pour supprimer.")
    else:
        print(f"\nOK : {len(to_delete)} backups supprimes — {total_mb:.1f} MB liberes.")


if __name__ == "__main__":
    main()
