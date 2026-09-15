"""Les corrections manuelles recette par recette (scripts/recipes/recipe_patches) sont appliquées."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "recipes" / "apply_recipe_patches.py"


def _module():
    spec = importlib.util.spec_from_file_location("apply_recipe_patches", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_corrections_manuelles_appliquees_et_idempotentes():
    mod = _module()
    raw = json.loads(Path(mod.RECIPES_PATH).read_text(encoding="utf-8"))
    restant = mod.apply_all(raw["recipes"], mod.load_patches())
    assert not restant, (
        "corrections non appliquées à recipes.json : lancer "
        f"scripts/recipes/apply_recipe_patches.py : {restant[:10]}"
    )
