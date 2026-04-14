import json
from pathlib import Path

recipes = json.loads(Path("backend/data/recipes/recipes.json").read_text("utf-8"))["recipes"]
recipe_map = {r["id"]: r for r in recipes}

SUSPECTS = [
    "entry_celeri_remoulade_d5d1b9",
    "main_tarte_a_la_tomate_a1d175",
    "salad_salade_mache_aux_noix_081567",
    "main_galettes_sarrasin_ce9f40",
]

for rid in SUSPECTS:
    r = recipe_map.get(rid)
    if not r:
        continue
    title = r.get("titles", {}).get("fr", "?")
    current = r.get("tags", {}).get("allergens", [])
    print(f"\n{rid}")
    print(f"  Titre : {title}")
    print(f"  Allergenes actuels : {current}")
    print("  Composition:")
    for item in r.get("composition", []):
        if isinstance(item, dict):
            print(f"    - {item.get('ingredient','?')}")
