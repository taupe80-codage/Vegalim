"""
conftest.py — Configuration globale pytest ALIM v6.

Marqueurs automatiques :
  - Les tests dans test_data_integrity.py qui dépendent de l'état du pipeline
    sont marqués @pipeline : ils peuvent échouer si build_indexes.py n'a pas
    été lancé (graphe de disponibilité désynchronisé).
"""
import pytest


def pytest_collection_modifyitems(items):
    """
    Applique automatiquement le marker 'pipeline' aux tests
    de cohérence données qui nécessitent le pipeline complet.
    """
    pipeline_tests = {
        "test_availability_couvre_tous_les_ingredients",
        "test_availability_valeurs_valides",
    }
    for item in items:
        if item.name in pipeline_tests:
            item.add_marker(
                pytest.mark.pipeline,
                append=False,
            )



def pytest_configure(config):
    """
    Les recettes publiées par les utilisateurs (community_recipes.json, généré
    à l'exécution et hors Git) ne doivent pas entrer dans les tests du
    catalogue : on pointe vers un fichier absent, avant la collecte (certains
    modules chargent les recettes à l'import). Les tests des contributions
    redirigent eux-mêmes ce chemin vers leur dossier temporaire.
    """
    import tempfile
    from pathlib import Path
    from backend.core import data_io
    data_io.COMMUNITY_RECIPES_PATH = Path(tempfile.mkdtemp(prefix="alim_communaute_")) / "community_recipes.json"
    data_io.load_recipes.cache_clear()
