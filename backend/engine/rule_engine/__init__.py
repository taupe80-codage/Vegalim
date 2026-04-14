"""
rule_engine/ — Moteur de règles culinaires, régimes et durabilité.

Fusionne 6 engines :
    culinary_rule_engine + diet_flag_engine + diet_flag_auto_engine
    seasonality_engine + sustainability_engine + vegan_variant_engine

API PUBLIQUE :
    from backend.engine.rule_engine import (
        validate_recipe, compute_diet_flags,
        in_season, carbon_score, vegan_variant,
        NON_VEGAN, NON_VEGETARIAN,
    )
"""
from backend.engine.rule_engine.diet        import compute_diet_flags, NON_VEGAN, NON_VEGETARIAN
from backend.engine.rule_engine.validation  import validate_recipe
from backend.engine.rule_engine.seasonality import in_season
from backend.engine.rule_engine.carbon      import carbon_score
from backend.engine.rule_engine.variants    import vegan_variant

__all__ = [
    "validate_recipe",
    "compute_diet_flags", "NON_VEGAN", "NON_VEGETARIAN",
    "in_season", "carbon_score", "vegan_variant",
]
