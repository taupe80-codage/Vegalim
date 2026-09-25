#!/usr/bin/env python3
"""fix_coherence_2026_09_25.py — corrige les incohérences trouvées par l'audit des 1 000 recettes.

Audit : docs/audit_coherence_2026-09-25.md. Ce script ne traite que les cas mécaniques ou
tranchés ; les constats qui demandent un arbitrage (mains pauvres en protéines, part lipidique,
métadonnées absentes) restent dans le rapport.

Règles générales :
  1. tags.diet : retire 'kid_friendly' / 'raw' quand le flag correspondant est False
  2. instructions : renumérote « Étape N : … » les recettes qui n'ont pas la numérotation
  3. composition : fusionne deux lignes du même ingrédient (même unité, même rôle)

Corrections ciblées : kid_friendly avec piment, spice_level, cook_min manquant, unités
'pinch'/'leaf', titres anglais restés en français, quantités du texte ≠ composition,
formulations fautives, ingrédients jamais cités.

Idempotent. Relancer ensuite rebuild_graphs.py, build_index.py, extract_recipe_list.py.

Usage :
    python scripts/recipes/fix_coherence_2026_09_25.py --dry-run
    python scripts/recipes/fix_coherence_2026_09_25.py
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

# ---------------------------------------------------------------- correctifs ciblés
# kid_friendly=True alors que la recette contient au moins 10 g de piment / harissa
KID_FRIENDLY_FALSE = (
    "brkf_ojja_vegan_dbbad8",                 # 12 g de harissa
    "dal_ragout_de_pois_chiches_moulus_f64412",  # 20 g de berbéré
    "egg_ojja_5bdbea",                        # 10 g de harissa
    "main_mexican_enfrijoladas_vega_d6a9a8",  # 30 g de piment
    "snack_brik_oeuf_2a7e64",                 # 15 g de harissa
)

# spice_level absent alors que la recette est piquante, ou annoncé sans ingrédient piquant
SPICE_LEVEL = {
    "bread_mexican_enfrijoladas_578ae7": 2,
    "main_mexican_enfrijoladas_vega_d6a9a8": 3,
    "main_pav_bhaji_vegan_c1437e": 2,
    "pasta_lagman_aaae70": 2,
    "rice_kimchi_bokkeumbap_2cbfe6": 2,
    "rice_kimchi_fried_rice_1f3e90": 2,
    "rice_riz_saute_au_kimchi_vegan_af038b": 2,
    "salad_gadogado_indonesien_vegan_e4cd75": 2,
    "salad_grillee_tunisienne_dcb033": 3,
    "sauce_pommes_de_terre_sauce_hua_3304de": 2,
    "snack_crepe_coreenne_aux_oignon_a45536": 2,
    "stew_peruvian_quinoa_stew_1180bf": 2,
    "wrap_quesadillas_au_fromage_511e1a": 2,
    "side_gomen_ethiopien_4d10a7": 1,
    "egg_sundubu_jjigae_bc21e0": 0,           # « baek » = version douce, sans piment
    "rice_biryani_classic_k82x7b": 1,
    "soup_persian_ash_reshteh_vegan_968f7d": 1,
}

# cook_min = 0 alors que les étapes décrivent une cuisson chiffrée
COOK_MIN = {
    "base_samosa_77fac4": 5,            # « frire 4 à 5 minutes »
    "base_pastry_wrappers_a56ee0": 22,  # « cuire au four 20 à 25 minutes »
    "base_yaourt_coco_552a95": 5,       # « cuire 2 minutes » + mise à température
    "base_halloumi_293d5e": 20,         # « cuire dans le petit-lait 20 minutes »
    "entry_chana_chaat_5f27b3": 20,     # « cuire 250 g de pommes de terre 20 minutes »
    "entry_houmous_betterave_51b3e7": 2,  # « griller le cumin à sec »
}

# unités hors g/ml du reste du dataset
UNITS = {
    ("base_bechamel_7db18f", "nutmeg_spice"): (1, "g"),
    ("base_bechamel_vegane_7a210c", "nutmeg_spice"): (1, "g"),
    ("base_gnocchi_8f01d0", "nutmeg_spice"): (1, "g"),
    ("red_curry_paste_3ee8f5", "kaffir_lime_leaf"): (1, "g"),
}

# titres anglais restés en français
TITLES_EN = {
    "base_creme_fraiche_b536c1": "Crème Fraîche, Cultured Cream",
    "bread_acorda_a_lail_et_coriandr_048494": "Açorda, Portuguese Garlic and Coriander Bread Soup",
    "dessert_creme_brulee_a19dfa": "Crème Brûlée, Burnt Sugar Custard",
    "sauce_tofu_croustillant_sauce_a_b8be56": "Crispy Tofu with Garlic Sauce",
    "soup_ramen_au_miso_f69c22": "Miso Ramen",
    "soup_soupe_thai_coco_citronnelle_375c23": "Thai Coconut and Lemongrass Soup",
    "soup_vegetable_laksa_ab0112": "Vegetable Laksa",
}

# titres trop génériques, indistinguables d'une autre recette
RENAME = {
    "salad_de_quinoa_e74dea": {
        "fr": "Taboulé de quinoa au persil et au citron",
        "en": "Quinoa Tabbouleh with Parsley and Lemon",
        "desc": "Salade de quinoa façon taboulé, sans blé : beaucoup de persil, concombre et tomate "
                "en dés fins, vinaigrette très citronnée, servie bien fraîche.",
        "cuisine": "mediterranean",
    },
}

# remplacements de texte : (id, ancien, nouveau)
TEXT = [
    # quantité citée ≠ composition
    ("soup_tofu_frit_au_bouillon_1bad0a", "Chauffer 100ml d'huile végétale", "Chauffer 40 ml d'huile végétale"),
    ("base_fried_onion_217e6a", "Chauffer 60ml d'huile de tournesol", "Chauffer 40 ml d'huile de tournesol"),
    ("main_gozleme_aux_epinards_66eccf", "200 g de farine avec 5 g de sel", "200 g de farine avec 2 g de sel"),
    # « saisir » employé pour « prendre » / « piler »
    ("dip_guacamole_970186", "Saisir 400 g d'avocats mûrs", "Couper 400 g d'avocats mûrs"),
    ("main_papaya_salad_918f58", "Saisir 9g d'ail et 15g de piment rouge dans un mortier",
     "Piler 9 g d'ail et 15 g de piment rouge dans un mortier"),
    # ingrédient de la composition jamais cité dans les étapes
    ("brkf_granola_maison_0d3e52", "faire fondre 60 ml d'huile de coco avec 80 ml de sirop d'érable",
     "faire fondre 60 ml d'huile de coco avec 80 ml de sirop d'érable et 3 g d'extrait de vanille"),
    ("soup_soup_k3d2p1", "Faire fondre 30 g de beurre dans une cocotte.",
     "Faire fondre 30 g de beurre avec 15 ml d'huile d'olive dans une cocotte."),
    # description commençant en minuscule
    ("bread_acorda_a_lail_et_coriandr_048494", None, None),
]

DIET_TAGS_CONDITIONAL = ("kid_friendly", "raw")


def fix_tags_diet(r, stats):
    flags = r.get("diet_flags") or {}
    diet = (r.get("tags") or {}).get("diet")
    if not isinstance(diet, list):
        return
    for f in DIET_TAGS_CONDITIONAL:
        if f in diet and not flags.get(f):
            diet.remove(f)
            stats["tags.diet nettoyé"] += 1


def fix_numbering(r, stats):
    steps = r.get("instructions") or []
    if not steps or steps[0].startswith("Étape 1"):
        return
    r["instructions"] = [f"Étape {i} : {s.strip()}" for i, s in enumerate(steps, 1)]
    stats["étapes renumérotées"] += 1


def fix_duplicate_lines(r, stats):
    comp = r.get("composition") or []
    seen = {}
    out = []
    for c in comp:
        m = c.get("meta") or {}
        key = (c["ingredient"], c.get("unit"), m.get("role"), m.get("state"))
        if m.get("role") == "serving_suggestion" or c.get("quantity") is None:
            out.append(c)
            continue
        if key in seen:
            seen[key]["quantity"] = round((seen[key]["quantity"] or 0) + (c["quantity"] or 0), 2)
            stats["lignes en double fusionnées"] += 1
            continue
        seen[key] = c
        out.append(c)
    r["composition"] = out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))
    recipes = raw["recipes"]
    by_id = {r["id"]: r for r in recipes}
    stats = Counter()

    for r in recipes:
        fix_tags_diet(r, stats)
        fix_numbering(r, stats)
        fix_duplicate_lines(r, stats)

    for rid in KID_FRIENDLY_FALSE:
        r = by_id[rid]
        if r.setdefault("diet_flags", {}).get("kid_friendly") is not False:
            r["diet_flags"]["kid_friendly"] = False
            stats["kid_friendly → False"] += 1
        diet = (r.get("tags") or {}).get("diet") or []
        if "kid_friendly" in diet:
            diet.remove("kid_friendly")
            stats["tags.diet nettoyé"] += 1

    for rid, lvl in SPICE_LEVEL.items():
        sc = by_id[rid].setdefault("scoring", {})
        if sc.get("spice_level") != lvl:
            sc["spice_level"] = lvl
            stats["spice_level ajusté"] += 1

    for rid, ck in COOK_MIN.items():
        t = by_id[rid].setdefault("timing", {})
        if t.get("cook_min") != ck:
            t["cook_min"] = ck
            t["total_min"] = sum(t.get(k) or 0 for k in ("prep_active_min", "prep_passive_min", "cook_min"))
            stats["cook_min corrigé"] += 1

    for (rid, iid), (q, u) in UNITS.items():
        for c in by_id[rid].get("composition") or []:
            if c["ingredient"] == iid and (c.get("unit") != u or c.get("quantity") != q):
                c["quantity"], c["unit"] = q, u
                stats["unité normalisée"] += 1

    for rid, en in TITLES_EN.items():
        t = by_id[rid]["titles"]
        if t.get("en") != en:
            t["en"] = t["original"] = en
            stats["titre anglais traduit"] += 1

    for rid, old, new in TEXT:
        if old is None:
            continue
        steps = by_id[rid].get("instructions") or []
        if any(new in s for s in steps):
            continue  # déjà appliqué (le nouveau passage contient parfois l'ancien)
        hits = [i for i, s in enumerate(steps) if old in s]
        if not hits:
            if not any(new in s for s in steps):
                print(f"ATTENTION {rid} : passage introuvable {old[:50]!r}")
            continue
        for i in hits:
            steps[i] = steps[i].replace(old, new)
        stats["texte corrigé"] += 1

    for rid, spec in RENAME.items():
        r = by_id[rid]
        t = r["titles"]
        if t.get("fr") != spec["fr"]:
            t["fr"] = spec["fr"]
            t["en"] = t["original"] = spec["en"]
            r["description"] = spec["desc"]
            r.setdefault("origin", {})["cuisine"] = spec["cuisine"]
            stats["titre générique renommé"] += 1

    # description commençant en minuscule
    r = by_id["bread_acorda_a_lail_et_coriandr_048494"]
    if r["description"][:1].islower():
        r["description"] = r["description"][0].upper() + r["description"][1:]
        stats["description capitalisée"] += 1

    for k, v in sorted(stats.items()):
        print(f"  {v:4d}  {k}")
    total = sum(stats.values())
    print(f"{total} correction(s)" + (" (dry-run)" if args.dry_run else ""))
    if total and not args.dry_run:
        RECIPES_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2),
                                encoding="utf-8", newline="\n")
        print("écrit :", RECIPES_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
