"""
scripts/tag_allergens.py
=========================
Re-tagging complet des 14 allergènes EU (Règlement 1169/2011) sur les 791 recettes ALIM v6.

Corrections vs version précédente :
  - Adapté au schéma v6 : composition[].ingredient (non ingredients[].ingredient_id)
  - Écrit dans tags.allergens (non recipe.allergens)
  - Mapping étendu (soy_sauce, comte, cream_cheese, sesame_seed, gochujang…)
  - Décision validée : tahini → sesame UNIQUEMENT (pas fruits_a_coque)
  - sesame_free : flag distinct de nut_free (à implémenter séparément)

Usage :
  python scripts/tag_allergens.py            (applique)
  python scripts/tag_allergens.py --dry-run  (prévisualise)
  python scripts/tag_allergens.py --stats    (statistiques uniquement)
"""
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

# Fix encodage Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT      = Path(__file__).resolve().parent.parent.parent
RECIPES_F = ROOT / "backend/data/recipes/recipes.json"

# ── Mapping ingrédient → allergènes EU (14 allergènes réglementaires) ────────
# Format : "ingredient_id" → ["allergene1", "allergene2"]
#
# Règles :
#   - Basé sur la clé `ingredient` dans composition[]
#   - Les clés sont en minuscules
#   - tahini → sesame UNIQUEMENT (décision 2026-04-08)
#   - gochujang → gluten (contient blé dans version standard)

ALLERGEN_MAP: dict[str, list[str]] = {

    # ── GLUTEN ─────────────────────────────────────────────────────────────────
    "flour":              ["gluten"],
    "farine":             ["gluten"],
    "wheat_flour":        ["gluten"],
    "whole_wheat_flour":  ["gluten"],
    "rye_flour":          ["gluten"],
    "spelt_flour":        ["gluten"],
    "chickpea_flour":     ["gluten"],  # farine de pois chiche = sans gluten en réalité
    # note: chickpea_flour est sans gluten — on le retire
    "bread":              ["gluten"],
    "baguette":           ["gluten"],
    "pain_pita":          ["gluten"],
    "pita":               ["gluten"],
    "sourdough_bread":    ["gluten"],
    "breadcrumbs":        ["gluten"],
    "panko_breadcrumbs":  ["gluten"],
    "pasta":              ["gluten"],
    "noodles":            ["gluten"],
    "rice_noodles":       [],          # sans gluten
    "glass_noodles":      [],          # sans gluten
    "udon":               ["gluten"],
    "soba_noodles":       ["gluten"],  # si pur sarrasin: sans gluten — convention: gluten par défaut
    "ramen":              ["gluten"],
    "couscous":           ["gluten"],
    "bulgur":             ["gluten"],
    "boulgour":           ["gluten"],
    "semolina":           ["gluten"],
    "semoule":            ["gluten"],
    "seitan":             ["gluten"],
    "wheat_gluten":       ["gluten"],
    "oats":               ["gluten"],
    "rolled_oats":        ["gluten"],
    "oat":                ["gluten"],
    "barley":             ["gluten"],
    "wonton_wrapper":     ["gluten"],
    "gyoza_wrapper":      ["gluten"],
    "empanada_dough":     ["gluten"],
    "filo_pastry":        ["gluten"],
    "puff_pastry":        ["gluten"],
    "pie_dough":          ["gluten"],
    "shortcrust_pastry":  ["gluten"],
    "ladyfinger":         ["gluten", "oeufs"],
    "digestive_biscuit":  ["gluten"],
    "reshteh_noodles":    ["gluten"],
    "galette":            ["gluten"],   # galette froment (sarrasin = sans gluten)
    # Sauce soja contient du blé dans version standard
    "soy_sauce":          ["gluten", "soja"],
    "sauce_soja":         ["gluten", "soja"],
    "dark_soy_sauce":     ["gluten", "soja"],
    "light_soy_sauce":    ["gluten", "soja"],
    # Gochujang: version standard contient du blé
    "gochujang":          ["gluten"],
    # Miso: contient soja (parfois orge/blé)
    "miso":               ["soja", "gluten"],
    # Sarrasin: sans gluten par nature
    "buckwheat_flour":    [],
    "buckwheat":          [],
    # Farine de pois chiche: sans gluten
    "chickpea_flour":     [],
    "gram_flour":         [],

    # ── OEUFS ──────────────────────────────────────────────────────────────────
    "egg":                ["oeufs"],
    "oeuf":               ["oeufs"],
    "oeufs":              ["oeufs"],
    "eggs":               ["oeufs"],
    "egg_white":          ["oeufs"],
    "egg_yolk":           ["oeufs"],
    "mayonnaise":         ["oeufs"],
    # mayonnaise_vegan → pas d'œufs
    "dijon_mustard":      ["moutarde"],  # aussi moutarde

    # ── LAIT ───────────────────────────────────────────────────────────────────
    "milk":               ["lait"],
    "lait":               ["lait"],
    "butter":             ["lait"],
    "beurre":             ["lait"],
    "salted_butter":      ["lait"],
    "clarified_butter":   ["lait"],
    "cream":              ["lait"],
    "creme":              ["lait"],
    "creme_fraiche":      ["lait"],
    "heavy_cream":        ["lait"],
    "whipping_cream":     ["lait"],
    "sour_cream":         ["lait"],
    "yogurt":             ["lait"],
    "yaourt":             ["lait"],
    "yoghurt":            ["lait"],
    "plant_yogurt":       [],          # sans lait animal
    "ghee":               ["lait"],
    "fromage":            ["lait"],
    "cheese":             ["lait"],
    "parmesan":           ["lait"],
    "pecorino_romano":    ["lait"],
    "mozzarella":         ["lait"],
    "ricotta":            ["lait"],
    "ricotta_salata":     ["lait"],
    "feta":               ["lait"],
    "brie":               ["lait"],
    "camembert":          ["lait"],
    "comte":              ["lait"],
    "gruyere":            ["lait"],
    "gruyere_cheese":     ["lait"],
    "manchego":           ["lait"],
    "cheddar":            ["lait"],
    "emmental":           ["lait"],
    "cream_cheese":       ["lait"],
    "fromage_blanc":      ["lait"],
    "fromage_frais":      ["lait"],
    "paneer":             ["lait"],
    "mascarpone":         ["lait"],
    "kashk":              ["lait"],
    "queijo":             ["lait"],
    "fresh_tome_cheese":  ["lait"],
    "whey":               ["lait"],
    "condensed_milk":     ["lait"],
    "roquefort":          ["lait"],
    "blue_cheese":        ["lait"],
    "goat_cheese":        ["lait"],
    "chevre":             ["lait"],
    "labneh":             ["lait"],
    "kefir":              ["lait"],
    "creme_chantilly":    ["lait"],
    "lait_concentre":     ["lait"],
    "creme_anglaise":     ["lait", "oeufs"],
    "custard":            ["lait", "oeufs"],

    # ── SOJA ───────────────────────────────────────────────────────────────────
    "tofu":               ["soja"],
    "tofu_soyeux":        ["soja"],
    "tempeh":             ["soja"],
    "edamame":            ["soja"],
    "soybean":            ["soja"],
    "lait_soja":          ["soja"],
    "soy_milk":           ["soja"],
    # miso et sauce_soja déjà listés au-dessus

    # ── SÉSAME ─────────────────────────────────────────────────────────────────
    # Décision validée 2026-04-08: tahini → sesame UNIQUEMENT (pas fruits_a_coque)
    "sesame":             ["sesame"],
    "sesame_seed":        ["sesame"],
    "black_sesame_seeds": ["sesame"],
    "sesame_oil":         ["sesame"],
    "huile_sesame":       ["sesame"],
    "tahini":             ["sesame"],   # sésame broyé → sesame UNIQUEMENT

    # ── ARACHIDES ──────────────────────────────────────────────────────────────
    "peanut":             ["arachides"],
    "cacahuete":          ["arachides"],
    "peanut_butter":      ["arachides"],
    "pate_d_arachide":    ["arachides"],

    # ── FRUITS À COQUE ─────────────────────────────────────────────────────────
    # Amandes, noix, noix de cajou, pistaches, noix de pécan, noisettes, noix du Brésil, macadamia
    "almond":             ["fruits_a_coque"],
    "amande":             ["fruits_a_coque"],
    "almonds":            ["fruits_a_coque"],
    "almond_butter":      ["fruits_a_coque"],
    "walnut":             ["fruits_a_coque"],
    "noix":               ["fruits_a_coque"],
    "walnuts":            ["fruits_a_coque"],
    "cashew":             ["fruits_a_coque"],
    "cashews":            ["fruits_a_coque"],
    "noix_de_cajou":      ["fruits_a_coque"],
    "cashew_cream":       ["fruits_a_coque"],
    "pistachio":          ["fruits_a_coque"],
    "pistache":           ["fruits_a_coque"],
    "pistachios":         ["fruits_a_coque"],
    "hazelnut":           ["fruits_a_coque"],
    "noisette":           ["fruits_a_coque"],
    "hazelnuts":          ["fruits_a_coque"],
    "pecan":              ["fruits_a_coque"],
    "pecans":             ["fruits_a_coque"],
    "pine_nut":           ["fruits_a_coque"],
    "pine_nuts":          ["fruits_a_coque"],
    "pignon":             ["fruits_a_coque"],
    "macadamia":          ["fruits_a_coque"],
    "brazil_nut":         ["fruits_a_coque"],

    # ── CÉLERI ─────────────────────────────────────────────────────────────────    # Céleri
    "celery":             ["celeri"],
    "celeri":             ["celeri"],
    "celeriac":           ["celeri"],
    "celery_root":        ["celeri"],
    "celery_salt":        ["celeri"],
    "celeri_rave":        ["celeri"],

    # Moutarde
    "moutarde":           ["moutarde"],
    "mustard":            ["moutarde"],
    "mustard_seeds":      ["moutarde"],
    "dijon_mustard":      ["moutarde"],
    "whole_grain_mustard":["moutarde"],
    "moutarde_en_grains": ["moutarde"],

    # Sulfites (>10mg/kg)
    # Uniquement si concentration significative
    "wine":               ["sulfites"],
    "red_wine":           ["sulfites"],
    "white_wine":         ["sulfites"],
    "wine_vinegar":       ["sulfites"],
    "sherry_vinegar":     ["sulfites"],
    "balsamic_vinegar":   ["sulfites"],
    "vinaigre_balsamique":["sulfites"],
    "dried_fruit":        ["sulfites"],
    "dried_apricot":      ["sulfites"],
    "dried_fig":          ["sulfites"],
    # vinegar blanc/cidre: concentration négligeable → pas déclaré
    # walnut_oil: huile de noix → fruits_a_coque
    "walnut_oil":         ["fruits_a_coque"],
    "almond_oil":         ["fruits_a_coque"],
    "hazelnut_oil":       ["fruits_a_coque"],
    # Ingrédients composites fréquents
    "button_mushroom":    [],   # champignon de Paris, sans allergène
    "small_eggplant":     [],   # aubergine
    "sesame_seed":        ["sesame"],
    "black_sesame_seeds": ["sesame"],
    "sesame_paste":       ["sesame"],

    # ── LUPIN ──────────────────────────────────────────────────────────────────
    "lupin_flour":        ["lupin"],
    "lupin":              ["lupin"],

    # ── POISSON (végétarien uniquement si sauce de poisson) ───────────────────
    "fish_sauce":         ["poisson"],
    "worcestershire_sauce": ["poisson"],

    # ── MOLLUSQUES / CRUSTACÉS ────────────────────────────────────────────────
    # (projet végétarien → normalement absents, mais au cas où)
}

# Retirer chickpea_flour du gluten — sans gluten par nature
ALLERGEN_MAP["chickpea_flour"] = []


def detect_allergens_v6(recipe: dict) -> list[str]:
    """Détecte les allergènes présents dans une recette v6 (champ composition)."""
    found: set[str] = set()
    for item in recipe.get("composition", []):
        if not isinstance(item, dict):
            continue
        ing = item.get("ingredient", "").lower().strip()
        if not ing:
            continue
        if ing in ALLERGEN_MAP:
            found.update(ALLERGEN_MAP[ing])
    return sorted(found - {""})


def main():
    parser = argparse.ArgumentParser(description="Tag allergènes EU sur toutes les recettes ALIM v6")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Affiche sans modifier")
    parser.add_argument("--stats",   "-s", action="store_true",
                        help="Statistiques uniquement (implique dry-run)")
    args = parser.parse_args()
    dry = args.dry_run or args.stats

    print("\n" + "="*60)
    print("  ALIM v6 — Re-tagging Allergènes EU (14 allergènes)")
    mode = "DRY-RUN" if dry else "APPLICATION"
    print(f"  Mode : {mode}")
    print("="*60 + "\n")

    raw = json.loads(RECIPES_F.read_text(encoding="utf-8"))
    recipes = raw.get("recipes", []) if isinstance(raw, dict) else raw

    stats_before: dict[str, int] = defaultdict(int)
    stats_after:  dict[str, int] = defaultdict(int)
    changed = 0

    for recipe in recipes:
        rid    = recipe.get("id", "?")
        # Allergènes actuels dans tags.allergens
        old_allergens = sorted(set(
            t.lower() for t in recipe.get("tags", {}).get("allergens", [])
        ))
        # Nouveaux allergènes détectés depuis la composition
        new_allergens = detect_allergens_v6(recipe)

        for a in old_allergens:
            stats_before[a] += 1
        for a in new_allergens:
            stats_after[a] += 1

        if set(old_allergens) != set(new_allergens):
            changed += 1
            added   = sorted(set(new_allergens) - set(old_allergens))
            removed = sorted(set(old_allergens) - set(new_allergens))
            if not args.stats:
                print(f"  {rid}")
                if added:
                    print(f"    ++ {added}")
                if removed:
                    print(f"    -- {removed}")

        if not dry:
            recipe.setdefault("tags", {})["allergens"] = new_allergens

    # Patch history
    if not dry:
        import datetime
        raw.setdefault("metadata", {}).setdefault("patch_history", []).append({
            "date": datetime.date.today().isoformat(),
            "action": "retag_allergens_eu_v6",
            "changed": changed,
            "description": (
                "Re-tagging complet allergènes EU 14 allergènes. "
                "Schéma v6 (composition[].ingredient). "
                "Tahini → sesame uniquement. soy_sauce → gluten+soja."
            ),
        })
        RECIPES_F.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # Récapitulatif
    print(f"\n{'─'*60}")
    print(f"  Recettes analysées : {len(recipes)}")
    print(f"  Recettes modifiées : {changed}")
    print(f"\n  Distribution AVANT → APRÈS (top allergènes) :")
    all_keys = sorted(
        set(stats_before.keys()) | set(stats_after.keys()),
        key=lambda k: -stats_after.get(k, 0)
    )
    print(f"  {'Allergène':<22} {'Avant':>8} {'Après':>8} {'Δ':>6}")
    print(f"  {'─'*22} {'─'*8} {'─'*8} {'─'*6}")
    for a in all_keys:
        b = stats_before.get(a, 0)
        af = stats_after.get(a, 0)
        delta = af - b
        sign = "+" if delta > 0 else ""
        print(f"  {a:<22} {b:>8} {af:>8} {sign+str(delta):>6}")

    if dry:
        print(f"\n  Mode DRY-RUN — aucun fichier modifié")
        print(f"  Relancer sans --dry-run pour appliquer.")
    else:
        print(f"\n  ✅ Fichier sauvegardé : {RECIPES_F}")

    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
