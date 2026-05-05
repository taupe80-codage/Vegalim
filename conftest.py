"""
conftest.py — Racine du projet ALIM.

Ajoute la racine au sys.path pour que `import backend.*` fonctionne
sans `pip install -e .` ni variable d'environnement spéciale.

Pytest charge ce fichier automatiquement avant toute collecte de tests.
"""
import sys
from pathlib import Path

# Racine du projet (répertoire contenant ce fichier)
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
