#!/usr/bin/env python3
"""fix_portions_2026_09_27.py — plats principaux servis sans féculent (suite de l'audit du 2026-09-25).

Le contrôle « portion légère » de audit_coherence.py mesurait la matière sèche par portion : il
signalait surtout des plats aqueux (soupes, polentas) et des féculents pesés secs (pâtes, riz).
Restaient une dizaine de vrais cas, traités ici au cas par cas :

  - teriyaki de tofu et de tempeh, tofu sauté gingembre-soja : les étapes disent « servir sur un
    lit de riz » mais le riz ne figurait pas dans la composition — il est ajouté ;
  - wrap végétarien : 181 g et 214 kcal par portion, des pois chiches sont ajoutés à la garniture ;
  - haricots frits mexicains et migas portugaises : ce sont des accompagnements dans leur cuisine
    d'origine, ils passent en `side`.

Les étapes existantes ne sont pas retouchées (des ops `txt` de recipe_patches s'y accrochent) :
les ajouts se font par une étape supplémentaire.

Idempotent. Relancer ensuite rebuild_graphs.py, build_index.py, extract_recipe_list.py.

Usage :
    python scripts/recipes/fix_portions_2026_09_27.py --dry-run
    python scripts/recipes/fix_portions_2026_09_27.py
"""
import argparse, json, logging, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
logging.disable(logging.WARNING)

from backend.engine.config import RECIPES_PATH

RICE = "white_rice_short_grain_seed_dried"

# id -> (ingrédient, quantité, unité, rôle, état, étape à ajouter)
ADD = {
    "tempeh_tempeh_teriyaki_da1952": [
        (RICE, 250, "g", "base", "dried",
         "Cuire 250 g de riz japonais à l'eau salée, 12 minutes, et le laisser reposer 5 minutes "
         "à couvert : c'est le lit de riz du plat."),
    ],
    "protein_tofu_teriyaki_ffcb47": [
        (RICE, 250, "g", "base", "dried",
         "Cuire 250 g de riz japonais à l'eau salée, 12 minutes, puis le laisser gonfler "
         "5 minutes à couvert avant de dresser le tofu dessus."),
    ],
    "wok_tofu_saute_gingembre_soja_6e901c": [
        (RICE, 250, "g", "base", "dried",
         "Cuire 250 g de riz à l'eau salée pendant la marinade du tofu et servir le sauté "
         "dessus, avec la sauce du wok."),
    ],
    "wrap_veg_k3d2p1": [
        ("chickpea_rinsed_canned", 200, "g", "plant_protein", "cooked",
         "Écraser grossièrement 200 g de pois chiches rincés à la fourchette et les répartir sur "
         "le chèvre frais avant les crudités : le wrap devient un plat complet."),
    ],
}

# plats qui sont des accompagnements dans leur cuisine d'origine
DISH_TYPE = {
    "main_haricots_frits_mexicains_a78841": "side",
    "bread_migas_portugaises_76818b": "side",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in raw["recipes"]}
    stats = Counter()

    for rid, lines in ADD.items():
        r = by_id[rid]
        comp = r.setdefault("composition", [])
        steps = r.setdefault("instructions", [])
        for iid, q, unit, role, state, step in lines:
            if any(c["ingredient"] == iid for c in comp):
                continue
            sugg = [c for c in comp if (c.get("meta") or {}).get("role") == "serving_suggestion"]
            core = [c for c in comp if c not in sugg]
            core.append({"ingredient": iid, "quantity": q, "unit": unit,
                         "meta": {"role": role, "form": "", "state": state, "preparation": ""}})
            r["composition"] = core + sugg
            steps.append(f"Étape {len(steps) + 1} : {step}")
            stats["féculent ou protéine ajouté"] += 1

    for rid, dt in DISH_TYPE.items():
        r = by_id[rid]
        if r.get("dish_type") != dt:
            r["dish_type"] = dt
            meal = (r.get("tags") or {}).get("meal")
            if isinstance(meal, list):
                r["tags"]["meal"] = [dt]
            stats["reclassé en accompagnement"] += 1

    for k, v in sorted(stats.items()):
        print(f"  {v:4d}  {k}")
    total = sum(stats.values())
    print(f"{total} modification(s)" + (" (dry-run)" if args.dry_run else ""))
    if total and not args.dry_run:
        RECIPES_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2),
                                encoding="utf-8", newline="\n")
        print("écrit :", RECIPES_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
