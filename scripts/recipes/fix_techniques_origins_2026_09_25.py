#!/usr/bin/env python3
"""fix_techniques_origins_2026_09_25.py — suite de l'audit du 2026-09-25 (docs/audit_coherence_2026-09-25.md).

1. tags.technique : normalise le vocabulaire (66 valeurs hétérogènes → 18 techniques canoniques)
   puis déduit les techniques manquantes des verbes des étapes (269 recettes sans technique).
2. origin : rattache à une cuisine réelle les recettes en cuisine « international » qui en ont
   une ; celles qui sont réellement sans origine (bowls, energy balls, wraps) restent telles
   quelles.
3. Deux corrections ponctuelles : la tapenade passe en condiment (37,5 g de matière grasse par
   « portion » d'entrée) et trois étapes de plus de 400 caractères sont découpées.

Idempotent. Relancer ensuite rebuild_graphs.py, build_index.py, extract_recipe_list.py.

Usage :
    python scripts/recipes/fix_techniques_origins_2026_09_25.py --dry-run
    python scripts/recipes/fix_techniques_origins_2026_09_25.py
"""
import argparse, json, logging, re, sys, unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
logging.disable(logging.WARNING)

from backend.engine.config import RECIPES_PATH

# ------------------------------------------------------- 1. techniques canoniques
# 18 valeurs : une par geste de cuisine, du plus structurant au plus accessoire
CANON = ("raw", "assembly", "kneading", "blending", "marinating", "fermenting", "chilling",
         "boiling", "simmering", "steaming", "sauteing", "deep_frying", "baking",
         "gratinating", "grilling", "toasting", "caramelizing", "sauce_making")

TECH_MAP = {
    # cuissons à l'eau
    "boiling": "boiling", "boil": "boiling", "water_cooking": "boiling", "absorption": "boiling",
    # cuissons douces et réductions
    "simmer": "simmering", "braising": "simmering", "braise": "simmering",
    "reduction": "simmering", "poaching": "simmering", "bain_marie": "simmering",
    "infuse": "simmering", "infusion": "simmering", "confit": "simmering",
    # vapeur
    "steaming": "steaming", "steam": "steaming",
    # sauté / wok / poêle
    "sauteed": "sauteing", "wok": "sauteing", "stir_fry": "sauteing", "stir_frying": "sauteing",
    "pan_frying": "sauteing", "griddle": "sauteing",
    # friture
    "frying": "deep_frying", "fry": "deep_frying",
    # four
    "oven_cooking": "baking", "bake": "baking", "baking": "baking", "roasting": "baking",
    "roast": "baking", "waffle_iron": "baking", "choux_pastry": "baking",
    "au_gratin": "gratinating", "gratinate": "gratinating",
    # gril et torréfaction
    "grilling": "grilling", "grill": "grilling", "blowtorch": "grilling",
    "toasting": "toasting", "toast": "toasting",
    # sucre et matières grasses travaillées
    "caramel": "caramelizing", "caramelize": "caramelizing", "syrup": "caramelizing",
    "brown_butter": "caramelizing",
    # sauces et crèmes
    "bechamel": "sauce_making", "pastry_cream": "sauce_making", "creme_anglaise": "sauce_making",
    "emulsion": "sauce_making",
    # gestes à froid
    "blending": "blending", "whisking": "blending", "meringue": "blending",
    "assembly": "assembly", "shaping": "assembly", "stuffing": "assembly", "mash": "assembly",
    "grating": "assembly", "mandoline_slicing": "assembly", "pressing": "assembly",
    "knead": "kneading",
    "marinating": "marinating", "marinate": "marinating", "maceration": "marinating",
    "soaking": "marinating",
    "fermentation": "fermenting",
    "refrigeration": "chilling", "freezing": "chilling", "gelling": "chilling",
    "ice_cream_churning": "chilling",
    "raw": "raw",
}

# détection dans le texte des étapes ; ordre = priorité (la technique structurante d'abord)
INFER = [
    ("deep_frying", r"\bfrire\b|friture|bain d'huile|\bfrit(?:e|s|es)? dans|"
                    r"chauffer l'huile a \d|huile a 1[5-9]0|plonger.{0,25}huile"),
    ("baking", r"enfourner|enfournez|au four|\bfour\b|cuire \d+ minutes? a \d+\s?°?c"),
    ("gratinating", r"gratiner|gratin\b|sous le gril"),
    ("grilling", r"griller|grillez|barbecue|plancha|poele-gril|chalumeau"),
    ("sauteing", r"faire revenir|faites revenir|faire sauter|\bsaut(?:er|ez|ees?|es)\b|au wok|"
                 r"dans une poele|poelee|faire blondir|faire suer|saisir|"
                 r"(?:les|le|la) dorer|faire dorer|dorer \d"),
    ("simmering", r"mijoter|mijotez|fremissement|a couvert \d+ minutes|laisser reduire|"
                  r"pocher|braiser|etuvee|a l'etouffee|feu tres doux"),
    ("boiling", r"eau bouillante|porter.{0,40}a ebullition|bouillir|cuire.{0,25}dans l'eau|"
                r"cuire.{0,20}a l'eau|cuire.{0,30}\d+ ml d'eau|blanchir"),
    ("steaming", r"\bvapeur\b|cuit-vapeur|panier vapeur"),
    ("toasting", r"griller a sec|torrefier|toaster|a sec \d+ minutes?"),
    ("blending", r"mixer|mixez|au blender|fouetter|fouettez|monter (?:les|en) (?:blancs|neige)|"
                 r"passer au tamis"),
    ("kneading", r"petrir|petrissez"),
    ("caramelizing", r"carameliser|caramelis|beurre noisette"),
    ("marinating", r"mariner|marinade|laisser tremper|faire tremper"),
    ("fermenting", r"fermenter|fermentation|levain"),
    ("chilling", r"refrigerer|au refrigerateur|au frais|congeler|prise au froid|au congelateur"),
    ("sauce_making", r"bechamel|roux\b|creme patissiere|creme anglaise|emulsionner"),
    ("assembly", r"dresser|monter les bols|garnir|rouler serre|assembler|tartiner"),
]
MAX_TECH = 3
# techniques de cuisson : une recette qui en a une n'a pas besoin de « assembly »
COOKING = {"boiling", "simmering", "steaming", "sauteing", "deep_frying", "baking",
           "gratinating", "grilling", "toasting", "caramelizing"}


def norm(s):
    s = (s or "").replace("œ", "oe").replace("Œ", "oe")
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def infer_techniques(r):
    text = norm(" ".join(r.get("instructions") or []))
    found = [t for t, pat in INFER if re.search(pat, text)]
    if (r.get("diet_flags") or {}).get("raw"):
        found = ["raw"] + [t for t in found if t not in COOKING]
    if any(t in COOKING for t in found):
        found = [t for t in found if t != "assembly"]
    if not found:
        # repli : le mode de cuisson se devine du matériel cité, sinon montage à froid
        ck = (r.get("timing") or {}).get("cook_min") or 0
        if ck > 0:
            if re.search(r"poele|sauteuse|\bwok\b|plaque chaude|crepiere", text):
                found = ["sauteing"]
            elif re.search(r"\bfour\b|plaque de cuisson", text):
                found = ["baking"]
            elif re.search(r"huile.{0,20}chaude|\bfrire|friture", text):
                found = ["deep_frying"]
            else:
                found = ["simmering"]
        else:
            found = ["assembly"]
        if re.search(r"mixer|mixez|fouetter|au blender", text) and len(found) < MAX_TECH:
            found.append("blending")
    return found[:MAX_TECH]


# ------------------------------------------------------- 2. cuisines à rattacher
ORIGIN = {
    # petits-déjeuners et desserts nord-américains
    "brkf_bowl_quinoa_fruits_du_mat_2a615c": ("american", "united_states"),
    "brkf_chia_pudding_framboise_e8a8fd": ("american", "united_states"),
    "brkf_granola_bowl_yaourt_fruit_980183": ("american", "united_states"),
    "brkf_granola_maison_0d3e52": ("american", "united_states"),
    "brkf_overnight_oats_vegan_a1e7b5": ("american", "united_states"),
    "brkf_pancakes_ricotta_citron_847c9a": ("american", "united_states"),
    "brkf_smoothie_vert_epinards_ba_eb4142": ("american", "united_states"),
    "brkf_tofu_brouille_aux_herbes_eb117c": ("american", "united_states"),
    "dessert_brownie_vegan_d4c6bd": ("american", "united_states"),
    "dessert_cheesecake_fruits_rouges_3460f6": ("american", "united_states"),
    "dessert_gateau_carottes_vegan_9d8a84": ("american", "united_states"),
    "rice_poke_bowl_ee65ef": ("american", "united_states"),
    # îles britanniques
    "brkf_porridge_pomme_cannelle_9af096": ("british", "united_kingdom"),
    "main_haricots_blancs_au_four_000c13": ("british", "united_kingdom"),
    # France
    "brkf_tartines_beurre_amande_ba_9f16cc": ("french", "france"),
    "brkf_tartines_ricotta_figue_mi_6f7590": ("french", "france"),
    "dessert_mousse_au_chocolat_vegan_b5d48f": ("french", "france"),
    "dessert_sorbet_mangue_passion_583687": ("french", "france"),
    "entry_rillettes_lentilles_corai_40d7dc": ("french", "france"),
    "entry_verrines_avocat_mangue_c5f8c6": ("french", "france"),
    "main_caviar_d_aubergine_0e824d": ("french_provencal", "france"),
    "main_poelee_de_legumes_f74508": ("french", "france"),
    "main_soup_k3d2p1": ("french", "france"),
    "rice_salad_k3d2p1": ("french", "france"),
    "side_orge_perle_aux_champignon_2824cb": ("french", "france"),
    "soup_au_chou_4be090": ("french", "france"),
    "soup_potage_de_patate_douce_e4b521": ("french", "france"),
    "soup_tomato_k2d1p1": ("french", "france"),
    # Méditerranée et Moyen-Orient
    "dal_revithia_922f79": ("greek", "greece"),
    "dal_salade_de_pois_chiches_2e32de": ("mediterranean", "international"),
    "entry_white_bean_dip_ail_roti_e61590": ("mediterranean", "international"),
    "rice_poivrons_farcis_au_riz_be3ddc": ("mediterranean", "international"),
    "salad_de_poivrons_et_tomates_d5f4ec": ("mediterranean", "international"),
    "main_manakish_zaatar_580150": ("levantine", "lebanon"),
    "main_ribollita_toscane_4cae34": ("italian", "italy"),
    "dessert_panna_cotta_coco_vegan_16d6b5": ("italian", "italy"),
    "main_pico_de_gallo_31e006": ("mexican", "mexico"),
    # Asie
    "dal_khichdi_23f932": ("indian", "india"),
    "main_rasam_34dc5a": ("indian", "india"),
    "soup_tom_yum_8001c0": ("thai", "thailand"),
    "pasta_nouilles_satay_864b31": ("malaysian", "malaysia"),
    "pasta_soupe_de_nouilles_thukpa_9c3ce8": ("nepali", "nepal"),
    "egg_galettes_aux_oignons_verts_ff5328": ("chinese", "china"),
    "protein_tofu_braise_aux_champigno_c515dd": ("chinese", "china"),
    "sauce_tofu_croustillant_sauce_a_b8be56": ("chinese", "china"),
    "wok_tofu_saute_aux_legumes_1f3ac2": ("chinese", "china"),
    "wok_tofu_saute_gingembre_soja_6e901c": ("chinese", "china"),
    "salad_asiatique_sesame_948f03": ("asian", ""),
    # Afrique et Amérique du Sud
    "salad_dattieke_7824bf": ("west_african", "ivory_coast"),
    "soup_de_quinoa_2df148": ("peruvian", "peru"),
}

# ------------------------------------------------------- 3. corrections ponctuelles
DISH_TYPE = {"entry_tapenade_d_olives_noires_ed6d5d": "condiment"}

# étapes de plus de 400 caractères : (id, index, [nouvelles étapes sans numérotation])
SPLIT_STEPS = {
    ("main_flamiche_aux_poireaux_fa3d0b", 1): [
        "Émincer finement les 800 g de poireaux en rondelles de 0,5 cm en ne conservant que le "
        "blanc et le vert pâle, afin d'obtenir une texture homogène.",
        "Faire fondre le beurre dans une casserole large à feu doux, ajouter les poireaux, saler "
        "légèrement et couvrir. Cuire 20 à 25 minutes à l'étouffée en remuant régulièrement, "
        "jusqu'à ce qu'ils soient très fondants et sans coloration. Laisser tiédir puis égoutter "
        "l'excédent d'eau.",
    ],
    ("stew_ratatouille_k8d2p4", 2): [
        "Dans la même poêle, faites confire l'oignon dans les 20 ml d'huile restants, à feu doux "
        "pendant 10 minutes, jusqu'à ce qu'il soit tendre et parfumé. Ajoutez l'ail et poursuivez "
        "2 minutes.",
        "Ajoutez les tomates concassées, le thym et le laurier, puis cuisez 10 minutes en remuant "
        "occasionnellement, jusqu'à ce que la sauce soit réduite et parfumée.",
    ],
    ("wok_thai_veg_eb92db", 3): [
        "Préparer la sauce tamarin en mélangeant 30 g de pâte de tamarin, 20 ml de sauce soja, "
        "12 g de sucre de coco, 8 g de sucre, 3 g de sel et 60 ml d'eau.",
        "Ajouter les 200 g de vermicelles égouttés, verser la sauce et mélanger vigoureusement à "
        "feu très vif pendant 2 minutes, en soulevant les vermicelles pour les enrober sans les "
        "casser : elles doivent rester tendres mais fermes.",
    ],
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))
    recipes = raw["recipes"]
    by_id = {r["id"]: r for r in recipes}
    stats = Counter()
    unknown = Counter()

    # 1. techniques
    for r in recipes:
        tags = r.setdefault("tags", {})
        old = list(tags.get("technique") or [])
        new = []
        for t in old:
            canon = t if t in CANON else TECH_MAP.get(t)
            if canon is None:
                unknown[t] += 1
                canon = t
            if canon not in new:
                new.append(canon)
        if not new:
            new = infer_techniques(r)
            if new:
                stats["techniques déduites"] += 1
        elif new != old:
            stats["techniques normalisées"] += 1
        tags["technique"] = new

    # 2. cuisines
    for rid, (cuisine, country) in ORIGIN.items():
        o = by_id[rid].setdefault("origin", {})
        if o.get("cuisine") != cuisine:
            o["cuisine"] = cuisine
            o["country"] = country
            stats["cuisine rattachée"] += 1

    # 3. ponctuel
    for rid, dt in DISH_TYPE.items():
        if by_id[rid].get("dish_type") != dt:
            by_id[rid]["dish_type"] = dt
            meal = (by_id[rid].get("tags") or {}).get("meal")
            if isinstance(meal, list) and meal and meal[0] not in (dt,):
                by_id[rid]["tags"]["meal"] = [dt]
            stats["dish_type corrigé"] += 1

    for (rid, idx), parts in SPLIT_STEPS.items():
        steps = by_id[rid]["instructions"]
        if any(parts[-1] in s for s in steps):
            continue  # déjà découpée
        body = re.sub(r"^Étape \d+\s?:\s*", "", steps[idx])
        if len(body) < 300:
            print(f"ATTENTION {rid} étape {idx + 1} déjà courte, découpage ignoré")
            continue
        steps[idx:idx + 1] = parts
        by_id[rid]["instructions"] = [f"Étape {i} : {re.sub(r'^Étape \d+\s?:\s*', '', s)}"
                                      for i, s in enumerate(steps, 1)]
        stats["étape découpée"] += 1

    if unknown:
        print("valeurs de technique non mappées :", dict(unknown))
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
