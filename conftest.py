"""
conftest.py — Racine du projet ALIM.

Ajoute la racine au sys.path pour que `import backend.*` fonctionne
sans `pip install -e .` ni variable d'environnement spéciale.

Pytest charge ce fichier automatiquement avant toute collecte de tests.
"""
import sys
import pytest
from pathlib import Path

# Racine du projet (répertoire contenant ce fichier)
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True, scope="module")
def _isolate_sys_modules():
    """
    Isole sys.modules entre les modules de test.

    Problème : certaines fixtures injectent des mocks dans sys.modules
    via sys.modules.setdefault() sans les nettoyer (backend, backend.core…).
    Ces mocks persistent et corrompent les imports des modules de test
    suivants, produisant des erreurs '(unknown location)'.

    Solution : snapshot de sys.modules avant chaque module de test,
    restauration complète après. Les fixtures qui utilisent patch.dict
    sont déjà correctes — ce fixture corrige uniquement les setdefault nus.
    """
    # Snapshot avant le module de test
    saved_keys   = set(sys.modules.keys())
    saved_values = {k: v for k, v in sys.modules.items()}

    yield

    # Nettoyer les modules ajoutés pendant ce module de test
    for key in list(sys.modules.keys()):
        if key not in saved_keys:
            del sys.modules[key]

    # Restaurer les modules dont la valeur a changé
    for key, val in saved_values.items():
        if sys.modules.get(key) is not val:
            sys.modules[key] = val
