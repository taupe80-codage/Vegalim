from __future__ import annotations

from backend.core.data_loader import DataLoader
from backend.db.culinary_repositories import (
    RecipeRepository,
    NutritionRepository,
    IngredientRepository,
    invalidate_caches,
)
from backend.db.graph_repositories import (
    GraphRepository,
    ScoringGraphRepository,
    SubstitutionGraphRepository,
    FlavorGraphRepository,
    CostGraphRepository,
)


class _DataAccess:
    """
    Conteneur d'instances de repositories.
    Toutes les instances sont créées une seule fois (singleton léger).
    """

    def __init__(self):
        # Loader unique
        self._loader = DataLoader()

        self.recipes       = RecipeRepository()
        self.nutrition     = NutritionRepository()
        self.ingredients   = IngredientRepository()
        self.graphs        = GraphRepository()
        self.scoring       = ScoringGraphRepository()
        self.substitutions = SubstitutionGraphRepository()
        self.flavor        = FlavorGraphRepository()
        self.cost          = CostGraphRepository()

    def invalidate_all_caches(self) -> None:
        """
        Vide tous les caches mémoire (JSON + graphes).
        """
        invalidate_caches()
        self.graphs.invalidate()

        import logging
        logging.getLogger(__name__).info("Tous les caches data invalidés")


# Instance globale — importée directement dans les engines
get_data = _DataAccess()


__all__ = ["get_data"]