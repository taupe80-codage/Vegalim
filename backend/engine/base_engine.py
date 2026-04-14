"""
base_engine.py — Contrat de base pour les engines de scoring.

Tous les engines de scoring implémentent (ou héritent de) cette interface.
Garantit qu'un engine peut toujours : scorer + expliquer.

Usage :
    class MonEngine(BaseEngine):
        def score(self, recipe, context=None):
            ...
            return {"score": 7.5, "dims": {...}}
"""
from abc import ABC, abstractmethod


class BaseEngine(ABC):
    """Interface minimale commune à tous les engines de scoring."""

    @abstractmethod
    def score(self, recipe: dict, context: dict | None = None) -> dict:
        """
        Calcule un score pour la recette.

        Args:
            recipe  : dict recette avec au minimum 'id' et 'ingredients'
            context : dict optionnel (profil utilisateur, flags contextuels…)

        Returns:
            dict avec au moins {"score": float}  où score ∈ [0.0, 10.0]
        """
        raise NotImplementedError

    def explain(self, score_result: dict) -> list[str]:
        """
        Traduit un résultat de scoring en labels lisibles.

        Implémentation par défaut via score_engine.explainer (migré).
        Les engines peuvent surcharger pour des explications spécifiques.
        """
        from backend.engine.score_engine.explainer import explain  # ✅ migré
        return explain(score_result)

    def score_and_explain(self, recipe: dict,
                          context: dict | None = None) -> dict:
        """
        Raccourci : score + reasons en un appel.

        Returns:
            dict score_result enrichi avec 'score_reasons'.
        """
        result = self.score(recipe, context)
        result["score_reasons"] = self.explain(result)
        return result
