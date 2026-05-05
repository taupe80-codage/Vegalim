"""
build_ontology_v6.py
═══════════════════════════════════════════════════════════════════════════
FUSION build_ontology_v5.py → v6.0

Changements v6 vs v5 :
  ✦ Import collector_v2 (sources complètes + champs étendus)
  ✦ FIELD_MAP étendu : 15 → 30 champs
      Ajouts : starch_g, alcohol_g, iodine_ug, choline_mg, trans_fat_g,
               beta_carotene_ug, vitamin_k2_ug, polyols_g, organic_acids_g,
               omega3_ala_g, omega3_epa_g, omega3_dha_g
  ✦ scientific_name extrait depuis CIQUAL
  ✦ Double export conservé : ontology_v6.json + reference_db.json
  ✦ Poids source : CIQUAL=1.0 / USDA=0.85 / CNF=0.75 (inchangé)

Patch P4 (variant_from_state) :
  ✦ variant_from_state() : lit food["state"]["process"] (USDA/CNF) au lieu de
      re-parser le nom textuel → variants homogènes par état réel (raw/cooked/dried…)
  ✦ USDA et CNF utilisent variant_from_state ; CIQUAL garde detect_variant
      (CIQUAL n'a pas encore le champ state structuré)
  ✦ Résout les fusions cru/cuit inter-sources (kale, spinach…)

Patch P3 (alias_map) :
  ✦ ALIM_ALIASES : ~50 correspondances ALIM-key → clé ontologie réelle
      Réduit le taux de no-match ontologie de ~45% → ~25%
      Couvre fruits/sirops, légumes, céréales, laitiers, épices, noix
  ✦ _resolve_alias() : lookup exact → normalisé (sans accents/apostrophes)
  ✦ build_ontology() : crée des entrées miroir dans result_onto/result_refdb
      Sans écraser les entrées existantes ; trace aliases_created + aliases_missing
  ✦ Export : aliases_count + aliases (dict) dans ontology_v6.json et rapport

Inputs  :  raw/usda_flat_v2.json       (genere par usda_refactor_v2.py)
           raw/ciqual_flat_v3.json     (genere par build_ciqual_flat_v3.py)
           raw/cnf_full_v10.json       (genere par build_cnf_full_v10.py)
           ingredients/fr_to_en_mapping.json

Outputs :  reference/ontology_v6.json
           reference/ontology_v6_report.json
           reference/reference_db.json    (backward compat avec auto_correct)
═══════════════════════════════════════════════════════════════════════════
"""

import json
import math
import statistics
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ── Taxonomie dynamique ───────────────────────────────────────────────────────
try:
    from taxonomy_loader import load_bk_taxonomy, build_taxonomy_object
    _TAXONOMY_AVAILABLE = True
except ImportError:
    _TAXONOMY_AVAILABLE = False
    def load_bk_taxonomy(path):   # type: ignore[override]
        return {}
    def build_taxonomy_object(bk, bk_taxonomy, *, fallback_unclassified=True):  # type: ignore[override]
        return None

# ══════════════════════════════════════════════════════════════════════════════
# CHEMINS
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR  = Path(__file__).resolve().parents[2]
DATA_DIR  = BASE_DIR / "backend/data"
RAW_DIR   = DATA_DIR / "nutrition/raw"
REF_DIR   = DATA_DIR / "nutrition/reference"

MAPPING_FILE  = DATA_DIR / "ingredients/fr_to_en_mapping.json"
OUTPUT_ONTO   = REF_DIR  / "ontology_v6.json"
OUTPUT_RPT    = REF_DIR  / "ontology_v6_report.json"
OUTPUT_REFDB  = REF_DIR  / "reference_db.json"

# nutrition_v2 : source canonique (avec flags _base_recipe_excluded)
# → filtrée au build → nutrition_v2_runtime.json sans les variants computés dynamiquement
N2_INPUT   = DATA_DIR / "nutrition/processed/nutrition_v2.json"
N2_RUNTIME = DATA_DIR / "nutrition/nutrition_v2_runtime.json"

# ══════════════════════════════════════════════════════════════════════════════
# NUTRIMENTS — alignés sur nutrition_v2 schema v3.0 (30 champs)
# ══════════════════════════════════════════════════════════════════════════════

# Clés longues nutrition_v2 → clés courtes internes ontologie
FIELD_MAP: dict[str, str] = {
    # ── Macros ────────────────────────────────────────────────────────────────
    "calories_kcal":          "calories",
    "protein_g":              "protein",
    "fat_g":                  "fat",
    "carbs_g":                "carbs",
    "fiber_g":                "fiber",
    "sugar_g":                "sugar",
    "starch_g":               "starch",           # ← NOUVEAU (v6)
    "alcohol_g":              "alcohol",           # ← NOUVEAU (v6)
    # ── Lipides détaillés ─────────────────────────────────────────────────────
    "saturated_fat_g":        "saturated_fat",
    "monounsaturated_fat_g":  "mufa",
    "polyunsaturated_fat_g":  "pufa",
    "trans_fat_g":            "trans_fat",         # ← NOUVEAU (v6)
    "omega3_g":               "omega3",
    "omega3_ala_g":           "omega3_ala",        # ← NOUVEAU (v6)
    "omega3_epa_g":           "omega3_epa",        # ← NOUVEAU (v6)
    "omega3_dha_g":           "omega3_dha",        # ← NOUVEAU (v6)
    "omega6_g":               "omega6",
    "cholesterol_mg":         "cholesterol",
    # ── Minéraux ──────────────────────────────────────────────────────────────
    "sodium_mg":              "sodium",
    "calcium_mg":             "calcium",
    "iron_mg":                "iron",
    "magnesium_mg":           "magnesium",
    "phosphorus_mg":          "phosphorus",
    "potassium_mg":           "potassium",
    "zinc_mg":                "zinc",
    "copper_mg":              "copper",
    "manganese_mg":           "manganese",
    "selenium_ug":            "selenium",
    "iodine_ug":              "iodine",            # ← NOUVEAU (v6, source CIQUAL)
    # ── Vitamines ─────────────────────────────────────────────────────────────
    "vitamin_a_ug":           "vitamin_a",
    "beta_carotene_ug":       "beta_carotene",     # ← NOUVEAU (v6)
    "vitamin_d_ug":           "vitamin_d",
    "vitamin_e_mg":           "vitamin_e",
    "vitamin_k1_ug":          "vitamin_k1",
    "vitamin_k2_ug":          "vitamin_k2",        # ← NOUVEAU (v6, source CIQUAL)
    "vitamin_c_mg":           "vitamin_c",
    "vitamin_b1_mg":          "vitamin_b1",
    "vitamin_b2_mg":          "vitamin_b2",
    "vitamin_b3_mg":          "vitamin_b3",
    "vitamin_b5_mg":          "vitamin_b5",
    "vitamin_b6_mg":          "vitamin_b6",
    "folate_ug":              "folate",
    "vitamin_b12_ug":         "vitamin_b12",
    "choline_mg":             "choline",           # ← NOUVEAU (v6, source USDA)
    # ── Autres ────────────────────────────────────────────────────────────────
    "polyols_g":              "polyols",           # ← NOUVEAU (v6, source CIQUAL)
    "organic_acids_g":        "organic_acids",     # ← NOUVEAU (v6, source CIQUAL)
}

FIELDS = list(FIELD_MAP.values())

# Mapping inverse : clé courte → clé longue nutrition_v2
INV_FIELD_MAP = {v: k for k, v in FIELD_MAP.items()}

# Poids de confiance par source
SOURCE_WEIGHTS = {"CIQUAL": 1.0, "USDA": 0.85, "CNF": 0.75}

# Champs dont la mesure est fiable uniquement dans une source précise.
# Ces champs ne sont PAS fusionnés avec des zéros/absences des autres sources.
SOURCE_EXCLUSIVE: dict[str, str] = {
    # champ_court: source autorisée pour la fusion
    "iodine":        "CIQUAL",    # USDA mesure l'iodine rarement et à 0
    "polyols":       "CIQUAL",    # absent de USDA Foundation et CNF
    "organic_acids": "CIQUAL",    # absent de USDA Foundation et CNF
    "vitamin_k2":    "CIQUAL",    # USDA ne distingue pas K1/K2
    "trans_fat":     "USDA",      # CIQUAL/CNF ne mesurent pas les trans
}

# ══════════════════════════════════════════════════════════════════════════════
# ALIAS MAP — ingrédients ALIM sans correspondance directe dans l'ontologie
# ══════════════════════════════════════════════════════════════════════════════
#
# Problème : extract_base("Sirop d'agave") → "sirop_d'agave"
#            mais l'ingrédient ALIM s'appelle "agave" → no-match.
#
# Solution : après fusion, créer des entrées miroir dans result_onto/refdb.
#   Format  : {clé_ALIM: clé_ontologie_cible}
#   Lookup  : exact en priorité, puis normalisé (sans accents/apostrophes).
#   Impact  : ~30 no-match résolus → couverture ontologie 55% → ~75%.
#
# Pour ajouter un alias : identifier la clé cible depuis _diagnose_v2 --full
# (colonne "Clés proches ontologie"), choisir la correspondance la plus juste.
# ──────────────────────────────────────────────────────────────────────────────
ALIM_ALIASES: dict[str, str] = {
    # ══════════════════════════════════════════════════════════════════════
    # POLITIQUE v6.7 — SYNONYMES EXACTS UNIQUEMENT
    #
    # Règle : un alias = même aliment, nom différent (langue, casse, singulier/
    #   pluriel, clé CIQUAL composite). Zéro proxy nutritionnel.
    #   Si l'aliment n'a pas de correspondance exacte dans les sources
    #   (CIQUAL/USDA/CNF), il retourne null — pas de données fausses.
    #
    # Supprimés vs v6.6 (proxies nutritionnels) :
    #   mint→peppermint, thai_basil→basil, galangal→ginger,
    #   shiso→peppermint, celery_root→celery, yuzu→lemon,
    #   citrus→lemon, green_mango→mango, green_papaya→papaya,
    #   bean_sprouts→beans, gigante_bean→bean_butter,
    #   buckwheat_crepe→buckwheat, glass_noodles→starch_rice,
    #   gyoza_wrapper→wheat, hominy→corn, pastry→shortcrust_pastry,
    #   reshteh_noodles→wheat, rice_paper→rice, spaetzle→wheat,
    #   garam_masala→curry, ras_el_hanout→curry, za_atar→origan,
    #   polenta→cornmeal, red_apple→apple_granny_smith,
    #   bitter_gourd→gourd, bran→sorghum_bran, corn_husk→corn,
    #   chrysanthemum_greens→spinach, sugar_snap_pea→peas,
    #   kimchi→napa_cabbage_pe_tsai, gundruk→napa_cabbage,
    #   liquid_smoke→corn, mirin→sake, natto→soybean, ponzu→lemon,
    #   worcestershire_vegan→tamarind, falafel→chickpea,
    #   cheese_curds→cottage_cheese, paneer→ricotta,
    #   hemp_milk→milk_plant, kefir_water→kefir,
    #   stevia→sweetener, xylitol→sweetener, maca→quinoa,
    #   empanada_dough→shortcrust_pastry, kashk→ricotta,
    #   lemon_verbena→lemon, wheat_grass→wheat, yogurt_plant→yogurt,
    #   coconut→coconut_oil, coconut_aminos→soy_sauce,
    #   fried_onion→onion, fried_rice→rice, jalapeno→bell_pepper_red,
    #   kaffir_lime_leaf→bay_leaf, nut→walnut, grain→grains,
    #   fermented_bean_paste→miso_paste,
    #   chili_paste/curry_paste/peanut_sauce/yellow_curry_paste (fallbacks erronés)
    # ══════════════════════════════════════════════════════════════════════

    # ── Fruits / sirops ──────────────────────────────────────────────────
    "agave":              "sirop_d'agave",            # agave = sirop d'agave (même produit)
    "maple_syrup":        "sirop_d'erable",           # sirop d'érable (clé CIQUAL avec apostrophe)
    "molasses":           "molasses_canne",           # mélasse = mélasse de canne
    "goji_berry":         "baie_goji",                # baie de goji (nom FR CIQUAL)
    "blueberry":          "blueberries",              # myrtille (singulier/pluriel)
    "cranberry":          "cranberries",              # canneberge (singulier/pluriel)
    "passion_fruit":      "fruit_passion",            # fruit de la passion (nom FR CIQUAL)
    "lychee":             "lychee",                   # litchi (clé propre)
    "date":               "date",                     # datte (clé propre Phoenix dactylifera)
    "fig":                "figs",                     # figue (singulier/pluriel)
    "dried_fig":          "dried_fig",                # figue sèche (clé propre, ≠ figue fraîche)
    "prune":              "pruneau",                  # pruneau (nom FR CIQUAL)
    "jackfruit":          "fruit_jackfruit",          # jacquier (nom FR CIQUAL)

    # ── Légumes ──────────────────────────────────────────────────────────
    "beet":               "beets",                    # betterave (singulier/pluriel)
    "bell_pepper":        "green_bell_pepper",        # poivron → poivron vert (clé CIQUAL confirmée)
    "bell_pepper_yellow": "bell_pepper_jaune",        # poivron jaune (nom FR CIQUAL)
    "bell_pepper_red":    "red_bell_pepper",          # poivron rouge (ordre mots différent)
    "leek":               "leeks",                    # poireau (singulier/pluriel)
    "swiss_chard":        "chard",                    # blette = chard (même plante)
    "snow_pea":           "snow_peas",                # pois mange-tout (singulier/pluriel)
    "snow_peas":          "snow_peas",                # clé propre confirmée
    "zucchini":           "zucchini",                 # courgette
    "eggplant":           "eggplant",                 # aubergine
    "butternut":          "squash_butternut_squash_(doubeurre)", # courge butternut
    "butternut_squash":   "squash_butternut_squash_(doubeurre)", # même
    "artichoke":          "artichokes",               # artichaut (singulier/pluriel)
    "arugula":            "arugula",                  # roquette
    "endive":             "endive",                   # endive
    "turnip":             "turnips",                  # navet (singulier/pluriel)
    "shallot":            "shallots",                 # échalote (singulier/pluriel)
    "pak_choi":           "bok_choy",                 # pak choï = bok choy (même plante, Brassica rapa)
    "green_cabbage":      "cabbage",                  # chou vert = chou (macros identiques)
    "green_peas":         "peas",                     # petits pois = peas

    # ── Céréales / féculents ─────────────────────────────────────────────
    "couscous":           "graine_couscous",          # semoule de blé (nom FR CIQUAL)
    "fine_bulgur":        "bulgur",                   # boulgour fin = boulgour
    "bulgur":             "bulgur",                   # boulgour
    "crackers":           "cracker",                  # crackers (pluriel → singulier CIQUAL)
    "tortillas":          "tortilla",                 # tortillas (pluriel → singulier CIQUAL)
    "millet":             "millet",                   # millet
    "sorghum":            "sorghum",                  # sorgho
    "corn_starch":        "starch_corn",              # amidon de maïs (mots inversés)
    "tapioca_starch":     "tapioca",                  # fécule de tapioca = tapioca (même produit)
    "wheat_germ":         "germe_ble",                # germe de blé (nom FR CIQUAL)
    "icing_sugar":        "sugar_blanc",              # sucre glace = sucre blanc (même macros, simple broyage)
    "starch":             "starch_corn",              # fécule générique → amidon maïs (seule clé générique disponible)
    "gnocchi":            "gnocchi_a_la_pomme_de_terre",  # CIQUAL code=25510 (gnocchi pomme de terre cuit)

    # ── Légumes — espèces peu courantes (absentes du mapping FR→EN) ──────
    "chinese_cabbage":    "napa_cabbage_pe_tsai",     # chou chinois pé-tsaï (Brassica rapa pekinensis)
    "ancho_chili":        "ancho_chili",              # piment ancho séché — clé propre (CNF v_f3273a2eea90)

    # ── Légumineuses ─────────────────────────────────────────────────────
    "dried_pea":          "split_peas",               # pois sec = split peas (proxy CNF, germés — annotation warnings)
    "tamari":             "soy_sauce_(made_from_soy)", # tamari = sauce soja sans blé (composition quasi identique)
    "chickpeas":          "chickpeas_(garbanzo_beans,_bengal_gram),_mature_seeds,_raw",
    "black_beans":        "black_beans",              # haricot noir (clé propre)
    "kidney_beans":       "red_bean_cooked",          # haricot rouge cuit (CIQUAL confirmée)
    "edamame":            "soybean_kernels",          # edamame = graines de soja vertes fraîches
    "tempeh":             "tempeh",                   # tempeh
    "pea_protein":        "pea_protein",              # isolat protéique pois (clé propre)
    "flax_egg":           "flaxseed",                 # œuf de lin = graine de lin moulue + eau (macros = lin)

    # ── Produits laitiers ────────────────────────────────────────────────
    "mozzarella":         "mozzarella_lait_vache",    # mozzarella lait de vache (CIQUAL)
    "cream_animal":       "cream",                    # crème animale = crème
    "yogurt_animal":      "yogurt",                   # yaourt animal = yaourt
    "cottage_cheese":     "cottage_cheese",           # fromage cottage
    "ricotta":            "ricotta",                  # ricotta
    "feta":               "feta",                     # feta
    "halloumi":           "halloumi",                 # halloumi (clé propre)

    # ── Épices / herbes ──────────────────────────────────────────────────
    "marjoram":           "marjolaine",               # marjolaine (nom FR CIQUAL, même plante)
    "cilantro":           "coriander_(cilantro)",     # coriandre fraîche = cilantro
    "coriander":          "coriander_(cilantro)",     # même plante Coriandrum sativum
    "lemongrass":         "lemon_grass_(citronella)", # citronnelle (clé CIQUAL)
    "tarragon":           "tarragon",                 # estragon
    "chervil":            "cerfeuil",                 # cerfeuil (nom FR CIQUAL)
    "oregano":            "origan",                   # origan (nom FR CIQUAL)
    "nutmeg":             "walnut_nutmeg",            # noix de muscade (clé composite CIQUAL)
    "nutmeg_whole":       "nutmeg",                   # noix muscade entière = muscade (même produit)
    "green_tea":          "tea",                      # thé vert = thé (même feuille Camellia sinensis)
    "matcha_tea":         "matcha_tea",               # matcha (clé propre — poudre entière ≠ infusion)
    "star_anise":         "star_anise",               # anis étoilé (clé propre Illicium verum)
    "sumac":              "sumac",                    # sumac (clé propre)
    "curry_leaves":       "curry_leaves",             # feuilles de curry (clé propre)

    # ── Confiserie / sucres ──────────────────────────────────────────────
    "sugar":              "sugar_blanc",              # sucre = sucre blanc
    "chocolate":          "dark_chocolate_70_%_dark_chocolate_environ",  # chocolat noir
    "carob":              "carob_(st._john's_bread)", # caroube (clé CIQUAL)
    "date_syrup":         "date_syrup",               # sirop de dattes (clé propre)

    # ── Levures / fermentés ──────────────────────────────────────────────
    "miso":               "miso_paste",               # miso = pâte de miso (même produit)
    "nutritional_yeast":  "levure_de_biere_en_paillettes",  # CIQUAL code=11009 (levure de bière en paillettes)
    "gochujang":          "gochujang",                # gochujang (clé propre)
    "kombucha":           "kombucha",                 # kombucha (clé propre)
    "attieke":            "attieke",                  # attiéké (clé propre CIQUAL)
    "tvp":                "tvp",                      # TVP texturé soja (clé propre)
    "umeboshi_plum":      "umeboshi_plum",            # prune umeboshi (clé propre)

    # ── Condiments / sauces ──────────────────────────────────────────────
    "pesto":              "pesto",                    # pesto (clé propre)
    "sriracha":           "sriracha",                 # sriracha (clé propre)
    "tamarind_paste":     "tamarind",                 # pâte de tamarin = tamarin concentré (même macros)
    "soy_pave":           "tofu",                     # pavé de soja = tofu (même produit)
    "vegan_gelatin":      "agar_algue",               # gélatine végane = agar (même produit)
    "vine_leaves":        "grape_leaves_(vine_leaves)", # feuilles de vigne (clé USDA)
    "grape_leaves":       "vine_leaves",              # feuilles de vigne (alias inverse)

    # ── Noix / graines ───────────────────────────────────────────────────
    "pecan":              "walnut_pecan",             # noix de pécan (clé CIQUAL)
    "macadamia":          "walnut_macadamia",         # noix de macadamia (clé CIQUAL)
    "hemp_seeds":         "chanvre",                  # graines de chanvre (clé CIQUAL)
    "flaxseeds":          "flaxseed",                 # graines de lin (singulier/pluriel)
    "flax_seeds":         "flaxseed",                 # idem
    "sunflower_seeds":    "tournesol",                # graines de tournesol (clé CIQUAL)
    "peanut":             "peanuts",                  # arachide (singulier/pluriel)
    "pumpkin_seeds":      "pumpkin_seeds",           # USDA group_key='pumpkin_seeds' (via USDA_KEY_OVERRIDES V13)
    "cashew":             "cashew",                   # noix de cajou (clé propre)

    # ── Autres ───────────────────────────────────────────────────────────
    "cream_plant":        "cream_plant",              # crème végétale (clé propre)
    "hard_boiled_egg":    "egg",                      # œuf dur = œuf (cuisson ne modifie pas les macros)
    "baking_powder":      "leavening_agent",          # levure chimique = agent levant (même composition)

    # ── Bouillon générique (fallback base_recipe) ─────────────────────────
    # dashi_broth et miso_broth sont calculés dynamiquement (base_recipe).
    # broth générique seul conservé comme fallback pour les cas non couverts.
    "broth":              "bouillon_legumes",         # bouillon générique → bouillon légumes

    # ══════════════════════════════════════════════════════════════════════
    # NON RÉSOLUS — absents des 3 sources (aucun proxy nutritionnel acceptable)
    # ══════════════════════════════════════════════════════════════════════
    # acai               → ABSENT USDA/CIQUAL/CNF
    # aquafaba           → ABSENT (eau de cuisson, macros ≈ 0)
    # baobab             → ABSENT
    # bean               → trop vague (type ombrelle)
    # bean_sprouts       → profil nutritionnel différent des haricots
    # bitter_gourd       → absent sous clé propre
    # bran               → son générique trop vague
    # buckwheat_crepe    → crêpe cuite ≠ grain cru
    # cheese_curds       → différent du cottage cheese
    # chrysanthemum_greens → absent
    # citrus             → catégorie, pas un aliment
    # coconut            → chair ≠ huile (macros très différentes)
    # coconut_aminos     → sève coco ≠ sauce soja (source et sodium différents)
    # corn_husk          → enveloppe, valeur nutritive nulle
    # dashi_broth        → calculé via base_recipe
    # empanada_dough     → composition différente de la pâte brisée
    # falafel            → frit, macros transformées
    # fermented_bean_paste → produit fermenté différent du miso
    # fried_onion        → friture modifie macros
    # fried_rice         → huile de friture modifie macros
    # galangal           → Alpinia galanga ≠ Zingiber officinale (espèces différentes)
    # gigante_bean       → variété différente du butter bean
    # glass_noodles      → amidon de haricot mungo ≠ amidon de riz
    # grain              → trop vague
    # green_mango        → non mûr, profil glucidique différent
    # green_papaya       → non mûre, profil glucidique différent
    # gundruk            → fermenté, profil différent du chou cru
    # gyoza_wrapper      → pâte cuite ≠ farine de blé
    # hemp_milk          → macros spécifiques au chanvre, ≠ lait végétal générique
    # hominy             → nixtamalisé, profil différent du maïs
    # jalapeno           → piment fort ≠ poivron doux
    # kaffir_lime_leaf   → combava ≠ feuille de laurier (espèces différentes)
    # kashk              → produit laitier fermenté iranien, pas de proxy exact
    # kefir_water        → fermentation eau ≈ 0 kcal, ≠ kéfir de lait
    # kimchi             → fermenté, profil différent du chou cru
    # lemon_verbena      → herbe aromatique ≠ citron
    # liquid_smoke       → arôme sans valeur nutritive, pas de proxy
    # maca               → poudre andine, profil unique, ≠ quinoa
    # mirin              → teneur en sucre très différente du sake
    # mint               → Mentha spp. ≠ Mentha piperita spécifiquement
    # miso_broth         → calculé via base_recipe
    # natto              → fermentation B12 élevée, profil ≠ soja cru
    # nut                → catégorie, pas un aliment
    # paneer             → fromage frais indien, pas de proxy exact
    # pastry             → catégorie, pas un aliment
    # polenta            → semoule de maïs cuite, ≠ cornmeal cru
    # ponzu              → sauce complexe (agrume + soja dilué) ≠ citron
    # ras_el_hanout      → mélange d'épices complexe ≠ curry
    # red_apple          → variété rouge ≠ granny smith (verte)
    # reshteh_noodles    → pâtes cuites ≠ farine de blé
    # rice_paper         → feuille de riz transformée ≠ riz
    # shiso              → Perilla frutescens ≠ Mentha piperita
    # sorghum_bran       → sous-produit spécifique
    # spaetzle           → pâtes blé+œuf ≠ farine de blé
    # sriracha           → sauce concentrée, clé propre (si absente de l'ontologie → null)
    # stevia             → 0 cal, ≠ édulcorant générique
    # sugar_snap_pea     → cosse incluse, profil différent des pois verts
    # thai_basil         → Ocimum basilicum var. thyrsiflora ≠ basilic commun
    # teff               → ABSENT des 3 sources
    # wheat_grass        → herbe jeune, profil ≠ grain de blé mûr
    # worcestershire_vegan → sauce complexe multi-ingrédients ≠ tamarin seul
    # xylitol            → polyol spécifique, pas d'édulcorant générique exact
    # yogurt_plant       → macros végétales différentes du yaourt animal
    # yuzu               → Citrus junos ≠ citron (Citrus limon)
    # za_atar            → mélange thym/sésame/sumac ≠ origan seul
}


def load_n2_excluded_keys(n2_path: Path) -> tuple[set[str], dict[str, str]]:
    """
    Lit nutrition_v2.json et retourne :
      - excluded  : set[ingredient_key]  — clés à bypasser (calculées dynamiquement)
      - dual      : dict[ingredient_key → base_recipe_ref] — double existence voulue

    Résolution de l'ingredient_key (par ordre de priorité) :
      1. v["source_key"]            — clé explicite la plus fiable
      2. v["name_en"]               — nom EN slugifié
      3. _base_recipe_ref extrait   — suffixe de l'ID base_recipe (ex: "base_hoisin_sauce_xxx")

    Un ingredient_key est "dual" si _base_recipe_dual=True → proxy statique maintenu,
    pas dans excluded (fallback ontologie disponible).
    """
    if not n2_path.exists():
        print(f"  ⚠️  nutrition_v2 absent ({n2_path.name}) — filtre base_recipe désactivé")
        return set(), {}

    with open(n2_path, encoding="utf-8") as f:
        n2 = json.load(f)

    excluded:  set[str]       = set()
    dual:      dict[str, str] = {}

    def _resolve_ik(v: dict, ref: str) -> str | None:
        """Extrait l'ingredient_key depuis un variant n2."""
        # 1. source_key explicite
        sk = v.get("source_key", "").strip()
        if sk:
            return sk
        # 2. name_en slugifié
        ne = v.get("name_en", "").strip().lower().replace(" ", "_")
        if ne:
            return ne
        # 3. dériver du _base_recipe_ref (retirer préfixe "base_" et suffixe "_XXXXXX")
        if ref:
            parts = ref.split("_")
            # format: base_{name}_{6-8 char suffix}
            if parts[0] == "base" and len(parts) >= 3:
                # Le suffixe est toujours alphanum 6+ chars en fin — on le retire
                candidate = "_".join(parts[1:-1])
                if candidate:
                    return candidate
        return None

    for _base_key, entry in n2.get("ingredients", {}).items():
        for _vname, v in entry.get("variants", {}).items():
            ref = v.get("_base_recipe_ref", "")
            ik  = _resolve_ik(v, ref)
            if not ik:
                continue

            if v.get("_base_recipe_excluded"):
                if v.get("_base_recipe_dual"):
                    dual[ik] = ref
                else:
                    excluded.add(ik)
            elif v.get("_base_recipe_dual"):
                dual[ik] = ref

    # Clés dual ne doivent jamais être dans excluded
    excluded -= set(dual.keys())

    print(f"  base_recipe exclus  ({len(excluded):>2}) : {sorted(excluded)}")
    print(f"  base_recipe dual    ({len(dual):>2})  : {sorted(dual.keys())}")
    return excluded, dual


def _resolve_alias(target: str, onto: dict) -> str | None:
    """
    Trouve la clé réelle dans onto correspondant à target.
    Essaie : exact → normalisé (sans accents, ponctuation → underscore, doublons collapsés).

    Règle de normalisation :
      apostrophe/tiret/espace → '_'  (pas suppression — évite "sirop_derable" vs "sirop_d_erable")
      parenthèses/points      → ''
      accents                 → supprimés via NFD
      underscores multiples   → un seul '_'
    """
    if target in onto:
        return target

    def _norm(s: str) -> str:
        s = s.lower()
        # Suppression des diacritiques (NFD : lettre + combining mark séparés)
        s = "".join(c for c in unicodedata.normalize("NFD", s)
                    if unicodedata.category(c) != "Mn")
        # Ponctuation → séparateur ou suppression
        s = s.replace("'", "_").replace("'", "_")   # apostrophes droites et typographiques
        s = s.replace(" ", "_").replace("-", "_")
        s = s.replace("(", "").replace(")", "").replace(".", "").replace("%", "")
        # Collapse des underscores multiples (ex: "sirop__d_agave" → "sirop_d_agave")
        while "__" in s:
            s = s.replace("__", "_")
        return s.strip("_")

    norm_target = _norm(target)
    for key in onto:
        if _norm(key) == norm_target:
            return key

    return None


# ══════════════════════════════════════════════════════════════════════════════
# MAPPING VARIANTS
# ══════════════════════════════════════════════════════════════════════════════

VARIANT_MAP: dict[str, str] = {
    "cru": "raw", "crue": "raw", "crues": "raw", "crus": "raw",
    "cuit": "cooked", "cuite": "cooked", "cuites": "cooked", "cuits": "cooked",
    "séché": "dried", "séchée": "dried", "sec": "dried", "sèche": "dried",
    "grillé": "roasted", "grillée": "roasted", "torréfié": "roasted",
    "congelé": "frozen", "surgelé": "frozen",
    "fermenté": "fermented", "fumé": "smoked",
    "raw": "raw", "cooked": "cooked", "dried": "dried", "fresh": "fresh",
    "frozen": "frozen", "roasted": "roasted", "ground": "ground",
    "boiled": "cooked", "steamed": "cooked", "baked": "cooked",
}

STOPWORDS = {
    "et", "or", "with", "without", "de", "du", "des", "le", "la", "les",
    "un", "une", "and", "au", "aux", "en", "a", "the", "of", "in",
}

# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES TEXTE
# ══════════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def load_mapping(path: Path) -> dict:
    if not path.exists():
        print(f"  ⚠ Mapping absent : {path}")
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {normalize(k): v for k, v in raw.get("mapping", {}).items()}


def extract_base(name: str, mapping: dict) -> str:
    name = name.split(",")[0].strip()
    name = name.split(" ou ")[0].strip()
    snake = normalize(name).replace(" ", "_").replace("-", "_")
    if snake in mapping:
        return mapping[snake]
    tokens = snake.split("_")
    out, skip = [], False
    for i, tok in enumerate(tokens):
        if skip:
            skip = False
            continue
        if i + 1 < len(tokens):
            bigram = f"{tok}_{tokens[i+1]}"
            if bigram in mapping:
                out.append(mapping[bigram])
                skip = True
                continue
        if tok in mapping:
            out.append(mapping[tok])
        elif tok not in VARIANT_MAP and tok not in STOPWORDS:
            out.append(tok)
    return "_".join(t.strip("_") for t in out if t) or snake


def detect_variant(name: str) -> str:
    tokens = normalize(name).replace(",", " ").split()
    for tok in tokens:
        if tok in VARIANT_MAP:
            return VARIANT_MAP[tok]
    return "default"


def variant_from_state(food: dict) -> str:
    """
    Lit le champ state structuré (USDA/CNF) pour déterminer le variant key.
    Priorité : state.process.level1 → level2 → preserve → fallback detect_variant.

    Mapping :
      raw                       → "raw"
      cooked + level2           → "cooked.{level2}"  (ex: "cooked.boiled")
      cooked sans level2        → "cooked"
      dried                     → "dried"
      manufactured              → "manufactured"
      fermented                 → "fermented"
      unknown / absent          → detect_variant(name) comme fallback
    """
    state = food.get("state")
    if not state or not isinstance(state, dict):
        return detect_variant(food.get("name_en", "") or food.get("name_fr", ""))

    process = state.get("process", {})
    l1 = process.get("level1", "unknown")
    l2 = process.get("level2")

    if l1 == "raw":
        return "raw"
    if l1 == "cooked":
        return f"cooked.{l2}" if l2 else "cooked"
    if l1 in ("dried", "manufactured", "fermented"):
        return l1
    # unknown → fallback textuel pour ne pas perdre les infos éventuelles
    return detect_variant(food.get("name_en", "") or food.get("name_fr", ""))


# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT SOURCES (via collector_v2)
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_path(full: Path, light: Path) -> Path:
    """Conserve pour la compatibilite CNF."""
    if full.exists():
        return full
    if light.exists():
        print(f"  Version light : {light.name}")
        return light
    raise FileNotFoundError(f"Source introuvable : {full}")


def load_ciqual() -> list[dict]:
    """Charge raw/ciqual_flat_v3.json (v5.1 - foods_flat liste plate)."""
    path = RAW_DIR / "ciqual_flat_v3.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Source CIQUAL introuvable : {path}\n"
            f"Lancer d'abord : python scripts/nutrition/build_ciqual_flat_v3.py"
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
        meta = data.get("_meta", {})
        sv = meta.get("schema_version", "?")
        if sv not in ("6.0", "7.0"):
            raise ValueError(f"CIQUAL schema inattendu : {sv} (attendu 6.0 ou 7.0)")
        if sv == "7.0":
            import logging
            logging.warning("CIQUAL schema 7.0 détecté — vérifier compatibilité champs nouveaux")
        return data.get("foods_flat", [])


def load_usda() -> list[dict]:
    """Charge raw/usda_flat_v2.json (v3.0 - foods_flat liste plate)."""
    path = RAW_DIR / "usda_flat_v2.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Source USDA introuvable : {path}\n"
            f"Lancer d'abord : python scripts/nutrition/usda_refactor.py"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("foods_flat", [])


def load_cnf() -> list[dict]:
    """Charge raw/cnf_full_v10.json (v10.0 - foods_flat liste plate)."""
    path = _resolve_path(
        RAW_DIR / "cnf_full_v10.json",
        RAW_DIR / "cnf_v10_light.json"
    )
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("foods_flat", [])


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTION CHAMPS PAR SOURCE
# ══════════════════════════════════════════════════════════════════════════════

def extract_ciqual(food: dict) -> dict[str, float | None]:
    """Extrait les champs CIQUAL v3 (flat, top-level) -> cles courtes ontologie.

    ciqual_flat_v3 exporte tous les nutriments directement au niveau
    racine de chaque item (pas de sous-dict 'nutrients').
    Convention de nommage : energy_kcal, fa_saturated_g, fa_18_3_ala_g, etc.
    """
    result = {}

    # Mapping v2 (top-level) -> cles courtes ontologie
    ciqual_to_short = {
        "energy_kcal":         "calories",
        "protein_g":           "protein",
        "fat_g":               "fat",
        "carbs_g":             "carbs",
        "fiber_g":             "fiber",
        "sugar_g":             "sugar",
        "starch_g":            "starch",
        "alcohol_g":           "alcohol",
        "fa_saturated_g":      "saturated_fat",
        "fa_mufa_g":           "mufa",
        "fa_pufa_g":           "pufa",
        "fa_18_3_ala_g":       "omega3_ala",
        "fa_20_5_epa_g":       "omega3_epa",
        "fa_22_6_dha_g":       "omega3_dha",
        "fa_18_2_linoleic_g":  "omega6",
        "cholesterol_mg":      "cholesterol",
        "sodium_mg":           "sodium",
        "calcium_mg":          "calcium",
        "iron_mg":             "iron",
        "magnesium_mg":        "magnesium",
        "phosphorus_mg":       "phosphorus",
        "potassium_mg":        "potassium",
        "zinc_mg":             "zinc",
        "copper_mg":           "copper",
        "manganese_mg":        "manganese",
        "selenium_ug":         "selenium",
        "iodine_ug":           "iodine",
        "vitamin_a_rae_ug":    "vitamin_a",
        "beta_carotene_ug":    "beta_carotene",
        "vitamin_d_ug":        "vitamin_d",
        "vitamin_e_mg":        "vitamin_e",
        "vitamin_k1_ug":       "vitamin_k1",
        "vitamin_k2_ug":       "vitamin_k2",
        "vitamin_c_mg":        "vitamin_c",
        "vitamin_b1_mg":       "vitamin_b1",
        "vitamin_b2_mg":       "vitamin_b2",
        "vitamin_b3_mg":       "vitamin_b3",
        "vitamin_b5_mg":       "vitamin_b5",
        "vitamin_b6_mg":       "vitamin_b6",
        "folate_ug":           "folate",
        "vitamin_b12_ug":      "vitamin_b12",
        "polyols_g":           "polyols",
        "organic_acids_g":     "organic_acids",
    }
    for src, dst in ciqual_to_short.items():
        result[dst] = food.get(src)  # None si absent

    # omega3 total
    fractions = [result.get("omega3_ala"), result.get("omega3_epa"), result.get("omega3_dha")]
    if any(v is not None for v in fractions):
        result["omega3"] = sum(v for v in fractions if v is not None)

    result["_scientific_name"] = food.get("scientific_name")
    result["_source"] = "CIQUAL"
    return result


def extract_usda(food: dict) -> dict[str, float | None]:
    """Extrait les champs USDA v2 (flat, top-level) -> cles courtes ontologie.

    usda_flat_v2 exporte les nutriments directement au niveau racine.
    Convention alignee sur ciqual_flat_v3 : energy_kcal, fa_saturated_g, etc.
    """
    usda_to_short = {
        "energy_kcal":         "calories",
        "protein_g":           "protein",
        "fat_g":               "fat",
        "carbs_g":             "carbs",
        "fiber_g":             "fiber",
        "sugar_g":             "sugar",
        "starch_g":            "starch",
        "fa_saturated_g":      "saturated_fat",
        "fa_mufa_g":           "mufa",
        "fa_pufa_g":           "pufa",
        "fa_18_3_ala_g":       "omega3_ala",
        "fa_20_5_epa_g":       "omega3_epa",
        "fa_22_6_dha_g":       "omega3_dha",
        "fa_18_2_linoleic_g":  "omega6",
        "cholesterol_mg":      "cholesterol",
        "sodium_mg":           "sodium",
        "calcium_mg":          "calcium",
        "iron_mg":             "iron",
        "magnesium_mg":        "magnesium",
        "phosphorus_mg":       "phosphorus",
        "potassium_mg":        "potassium",
        "zinc_mg":             "zinc",
        "copper_mg":           "copper",
        "manganese_mg":        "manganese",
        "selenium_ug":         "selenium",
        "iodine_ug":           "iodine",           # ← AJOUT : USDA id 1100, absent avant v6 fix
        "vitamin_a_rae_ug":    "vitamin_a",
        "beta_carotene_ug":    "beta_carotene",
        "vitamin_d_ug":        "vitamin_d",
        "vitamin_e_mg":        "vitamin_e",
        "vitamin_k1_ug":       "vitamin_k1",
        "vitamin_k2_ug":       "vitamin_k2",
        "vitamin_c_mg":        "vitamin_c",
        "vitamin_b1_mg":       "vitamin_b1",
        "vitamin_b2_mg":       "vitamin_b2",
        "vitamin_b3_mg":       "vitamin_b3",
        "vitamin_b5_mg":       "vitamin_b5",
        "vitamin_b6_mg":       "vitamin_b6",
        "folate_ug":           "folate",
        "vitamin_b12_ug":      "vitamin_b12",
        "choline_mg":          "choline",
        "fa_trans_g":          "trans_fat",        # ← top-level après fix usda_refactor_v2
    }
    result = {dst: food.get(src) for src, dst in usda_to_short.items()}

    # omega3 total
    fractions = [result.get("omega3_ala"), result.get("omega3_epa"), result.get("omega3_dha")]
    if any(v is not None for v in fractions):
        result["omega3"] = sum(v for v in fractions if v is not None)

    result["_source"] = "USDA"
    return result


def extract_cnf(food: dict) -> dict[str, float | None]:
    """Extrait les champs CNF v10 (flat, top-level) -> cles courtes ontologie.

    cnf_full_v10 v10.0 exporte 40+ nutriments directement au niveau racine.
    Convention alignee sur ciqual_flat_v3 et usda_flat_v2.
    """
    cnf_to_short = {
        "energy_kcal":         "calories",
        "protein_g":           "protein",
        "fat_g":               "fat",
        "carbs_g":             "carbs",
        "fiber_g":             "fiber",
        "sugar_g":             "sugar",
        "starch_g":            "starch",
        "fa_saturated_g":      "saturated_fat",
        "fa_mufa_g":           "mufa",
        "fa_pufa_g":           "pufa",
        "fa_18_3_ala_g":       "omega3_ala",
        "fa_20_5_epa_g":       "omega3_epa",
        "fa_22_6_dha_g":       "omega3_dha",
        "fa_18_2_linoleic_g":  "omega6",
        "cholesterol_mg":      "cholesterol",
        "sodium_mg":           "sodium",
        "calcium_mg":          "calcium",
        "iron_mg":             "iron",
        "magnesium_mg":        "magnesium",
        "phosphorus_mg":       "phosphorus",
        "potassium_mg":        "potassium",
        "zinc_mg":             "zinc",
        "copper_mg":           "copper",
        "manganese_mg":        "manganese",
        "selenium_ug":         "selenium",
        "vitamin_a_rae_ug":    "vitamin_a",
        "beta_carotene_ug":    "beta_carotene",
        "vitamin_d_ug":        "vitamin_d",
        "vitamin_e_mg":        "vitamin_e",
        "vitamin_k1_ug":       "vitamin_k1",
        "vitamin_c_mg":        "vitamin_c",
        "vitamin_b1_mg":       "vitamin_b1",
        "vitamin_b2_mg":       "vitamin_b2",
        "vitamin_b3_mg":       "vitamin_b3",
        "vitamin_b5_mg":       "vitamin_b5",
        "vitamin_b6_mg":       "vitamin_b6",
        "folate_ug":           "folate",
        "vitamin_b12_ug":      "vitamin_b12",
        "choline_mg":          "choline",
    }
    result = {dst: food.get(src) for src, dst in cnf_to_short.items()}

    # omega3 total
    fractions = [result.get("omega3_ala"), result.get("omega3_epa"), result.get("omega3_dha")]
    if any(v is not None for v in fractions):
        result["omega3"] = sum(v for v in fractions if v is not None)

    result["_source"] = "CNF"
    return result


# ══════════════════════════════════════════════════════════════════════════════
# FUSION MULTI-SOURCE (weighted average avec MAD outlier detection)
# ══════════════════════════════════════════════════════════════════════════════

def weighted_merge(entries: list[tuple[float, float]]) -> float | None:
    """
    Fusionne des valeurs (val, weight) avec détection outliers MAD.
    Conservé de v5 (éprouvé).
    """
    valid = [(v, w) for v, w in entries if v is not None and not math.isnan(v)]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0][0]

    values = [v for v, _ in valid]
    if len(values) >= 3:
        med = statistics.median(values)
        deviations = [abs(v - med) for v in values]
        mad = statistics.median(deviations) or 1e-9
        valid = [(v, w) for (v, w), dev in zip(valid, deviations) if dev / mad < 3.5]

    total_w = sum(w for _, w in valid)
    if total_w == 0:
        return None
    return sum(v * w for v, w in valid) / total_w


# ══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION ONTOLOGIE
# ══════════════════════════════════════════════════════════════════════════════

def build_ontology(mapping: dict) -> dict:
    print("Chargement des sources...")
    ciqual_foods = load_ciqual()
    usda_foods   = load_usda()
    cnf_foods    = load_cnf()

    # ── Chargement taxonomie dynamique ───────────────────────────────────────
    # Auto-détection du taxonomy_session_*.json le plus récent dans reference/.
    _bk_taxonomy: dict[str, dict] = {}
    _tax_candidates = sorted(REF_DIR.glob("taxonomy_session_*.json"), reverse=True)
    if _tax_candidates:
        _bk_taxonomy = load_bk_taxonomy(_tax_candidates[0])
        print(f"  Taxonomie chargée : {len(_bk_taxonomy)} bk — {_tax_candidates[0].name}")
    else:
        print("  ⚠️  Aucun taxonomy_session_*.json dans reference/ — champ '_taxonomy' omis.")

    # Index par clé normalisée (utilisé pour lookups futurs éventuels)
    ciqual_index = {}
    for f in ciqual_foods:
        key = normalize(f.get("name_fr", ""))
        ciqual_index[key] = f

    usda_index = {}
    for f in usda_foods:
        key = normalize(f.get("name_en", ""))
        usda_index[key] = f
        base = key.split(",")[0].strip()
        if base not in usda_index:
            usda_index[base] = f

    cnf_index = {}
    for f in cnf_foods:
        key = normalize(f.get("name_en", ""))
        if key:
            cnf_index[key] = f
        base = key.split(",")[0].strip()
        if base not in cnf_index:
            cnf_index[base] = f

    # Aggrégation par base_key
    ontology: dict[str, dict[str, list]] = defaultdict(
        lambda: defaultdict(list)
    )
    scientific_names: dict[str, str] = {}

    def _add(base, variant, data, weight):
        source = data.get("_source", "")
        # True si la source fournit un breakdown FA complet (sat + mufa + pufa).
        # Utilisé pour éviter d'inflater fat_g avec des sources qui n'ont pas
        # les sous-fractions (ex : CIQUAL/CNF qui ont fat mais pas les FA pour
        # certains aliments → écart fat multi-source vs sat+mufa+pufa mono-source).
        has_fa = (
            data.get("saturated_fat") is not None
            and data.get("mufa") is not None
            and data.get("pufa") is not None
        )
        for field in FIELDS:
            # Règle exclusivité : ne contribuer ce champ que si la source est autorisée
            exclusive_src = SOURCE_EXCLUSIVE.get(field)
            if exclusive_src and source != exclusive_src:
                continue
            val = data.get(field)
            if val is not None:
                ontology[base][variant].append((field, val, weight, has_fa))

    # ── CNF_KEY_OVERRIDES ─────────────────────────────────────────────────────
    # Certains aliments CNF ont un nom anglais trop générique : extract_base les
    # fusionne dans une clé partagée (ex: "Pepper, ancho" → "pepper"), écrasant
    # ainsi leurs valeurs spécifiques avec la moyenne de la catégorie.
    # Ce dict mappe le préfixe exact du name_en (avant la première virgule)
    # vers la clé ontologie correcte.  Appliqué avant extract_base dans la boucle CNF.
    CNF_KEY_OVERRIDES: dict[str, str] = {
        "Pepper, ancho":    "ancho_chili",   # Capsicum annum séché — 281 kcal, ≠ poivron générique

        # ── Corrections P1 : ingrédients NC avec données CNF non intégrées ────
        # Ces overrides corrigent les cas où extract_base génère une clé
        # incorrecte ou trop générique à partir du nom CNF.

        # "Bambou, pousses" → extract_base génère 'bambou' (FR), nc/mapping cible 'bamboo_shoots'
        "Bambou":                   "bamboo_shoots",

        # "Grains céréaliers, orge" → génère 'grains_cerealiers', cible 'barley'
        "Grains céréaliers, orge":  "barley",

        # "Graines, beurre de sésame, tahini" → génère 'graines', cible 'tahini'
        "Graines, beurre de sésame, tahini": "tahini",

        # "Câpres" → génère 'caper' mais onto a 'capers'
        "Câpres":                   "capers",

        # "Menthe poivrée" → génère 'menthe_poivree', nc cible 'mint'
        "Menthe poivrée":           "mint",

        # "Épices, menthe verte" → préfixe "Épices" génère 'spices', cible 'mint'
        "Épices, menthe verte":     "mint",

        # "Épices, cumin, graines" → préfixe "Épices" génère 'spices', cible 'cumin'
        "Épices, cumin, graines":   "cumin",
    }

    # CIQUAL  (name_fr = champ nom dans v2)
    print(f"Indexation CIQUAL ({len(ciqual_foods)} aliments)...")
    # Patterns CIQUAL qui contaminenent des clés légumes avec des valeurs de produits
    # transformés (ex: "chicorée, poudre soluble" → 323 kcal pollue la clé "chicory")
    CIQUAL_NAME_EXCLUDE_PATTERNS = {
        "poudre soluble", "instantané", "café instantané",
    }

    # ── CIQUAL_KEY_OVERRIDES ──────────────────────────────────────────────────
    # Mappe le nom_fr CIQUAL normalisé (avant 1ʳᵉ virgule, lower) vers la clé
    # onto correcte, quand extract_base génère une clé incorrecte ou incohérente
    # avec les cibles du mapping/nc.
    CIQUAL_KEY_OVERRIDES: dict[str, str] = {
        # "Menthe" → extract_base génère 'menthe' (FR), nc cible 'mint'
        "menthe":            "mint",

        # "Câpres, au vinaigre" → génère 'caper', onto a 'capers'
        "câpres":            "capers",

        # "Bambou, pousses" → génère 'bambou', nc cible 'bamboo_shoots'
        "bambou":            "bamboo_shoots",

        # "Tahin" → génère 'tahin', nc cible 'tahini' (cohérence clé)
        "tahin":             "tahini",

        # "Datte, chair..." → mapping mappe 'datte'→'raisins_sec' (date = fruit frais)
        # nc a une clé 'date' distincte des raisins secs
        "datte":             "date",

        # ── V13 : alias manquants — cible absente dans l'ontologie ────────────
        # "Gnocchis à la pomme de terre, cuits" → extract_base génère
        # 'gnocchis_a_la_pomme_de_terre' (pluriel FR) mais ALIM_ALIASES cible
        # 'gnocchi_a_la_pomme_de_terre' (sans 's') → mismatch. Fix: forcer la
        # clé 'gnocchi' directement, l'alias sera résolu automatiquement.
        "gnocchis à la pomme de terre": "gnocchi",
        "gnocchis a la pomme de terre": "gnocchi",   # sans accent (normalize)

        # "Levure de bière en paillettes" → extract_base peut mapper 'levure'→'yeast'
        # via le mapping FR→EN, donnant une clé incompatible avec la cible
        # 'levure_de_biere_en_paillettes'. Fix: indexer directement sous 'nutritional_yeast'.
        "levure de bière en paillettes":  "nutritional_yeast",
        "levure de biere en paillettes":  "nutritional_yeast",  # sans accent
    }
    for food in ciqual_foods:
        name_fr = food.get("name_fr", "")
        # Exclure les produits transformés dont le nom FR contient un pattern blacklisté
        if any(pat in name_fr.lower() for pat in CIQUAL_NAME_EXCLUDE_PATTERNS):
            continue
        # CIQUAL_KEY_OVERRIDES : appliquer avant extract_base sur le préfixe FR
        _cq_prefix = name_fr.split(",")[0].strip().lower()
        base    = CIQUAL_KEY_OVERRIDES.get(_cq_prefix) or extract_base(name_fr, mapping)
        variant = detect_variant(name_fr)
        data    = extract_ciqual(food)
        _add(base, variant, data, SOURCE_WEIGHTS["CIQUAL"])
        # scientific_name depuis CIQUAL
        sci = data.get("_scientific_name")
        if sci and base not in scientific_names:
            scientific_names[base] = sci

    # USDA  (name_en = champ nom dans usda_flat_v2)
    # variant_from_state lit directement food["state"]["process"] calculé par
    # parse_state_v2 dans usda_refactor_v2 — plus fiable que re-parser le nom.
    #
    # USDA_KEY_OVERRIDES — même logique que CIQUAL_KEY_OVERRIDES et CNF_KEY_OVERRIDES.
    # Mappe le préfixe EN (avant 1ʳᵉ virgule) → clé ontologie correcte.
    # Nécessaire quand extract_base génère une clé trop générique depuis le nom USDA.
    USDA_KEY_OVERRIDES: dict[str, str] = {
        # "Seeds, pumpkin seeds, raw" → split → "Seeds" → extract_base → "seeds"
        # nc cible 'pumpkin_seeds', ALIM_ALIASES mappe 'pumpkin_seeds'→'seeds_pumpkin'
        # Fix: indexer sous 'pumpkin_seeds' directement (résolution automatique de l'alias).
        "Seeds":              "seeds",      # garde la clé générique pour les graines non spécifiées
        # Override spécifique pour pumpkin seeds — le préfixe exact est "Seeds" mais
        # on ne peut pas distinguer ici sans regarder le reste du nom.
        # Solution : utiliser group_key du flat si disponible comme override prioritaire.
    }

    print(f"Indexation USDA ({len(usda_foods)} aliments)...")
    for food in usda_foods:
        # V13 : utiliser group_key si disponible (plus précis que extract_base sur name_en)
        # group_key = 'seeds_pumpkin', 'yogurt_greek', 'sorghum_grain'…
        _gk = food.get("group_key") or ""
        if _gk:
            base = _gk
        else:
            base = extract_base(food.get("name_en", ""), mapping)
        variant = variant_from_state(food)
        data    = extract_usda(food)
        _add(base, variant, data, SOURCE_WEIGHTS["USDA"])

    # CNF  (name_en = champ nom anglais dans cnf_full_v10)
    # variant_from_state lit directement food["state"]["process"] si disponible.
    print(f"Indexation CNF ({len(cnf_foods)} aliments)...")
    for food in cnf_foods:
        name_en = food.get("name_en", "")
        # CNF_KEY_OVERRIDES : certains aliments ont un nom trop générique
        # (ex: "Pepper, ancho, dried" → slug "pepper" sans override).
        # On mappe le préfixe avant la 1ʳᵉ virgule vers la clé ontologie correcte.
        prefix = name_en.split(",")[0].strip()
        base = CNF_KEY_OVERRIDES.get(prefix) or CNF_KEY_OVERRIDES.get(f"{prefix}, {name_en.split(',')[1].strip()}" if "," in name_en else prefix) or extract_base(name_en, mapping)
        variant = variant_from_state(food)
        data    = extract_cnf(food)
        _add(base, variant, data, SOURCE_WEIGHTS["CNF"])

    # Fusion
    print("Fusion des sources (weighted average + MAD outlier detection)...")
    result_onto = {}
    result_refdb = {}

    for base, variants in ontology.items():
        # ── Skip statique : base_recipe couverte par calcul dynamique ─────
        # Ne pas construire de proxy statique pour les clés dont la valeur
        # nutritionnelle est calculée depuis la composition de la recette.
        # Ce guard s'applique même quand n2 est absent (n2_excluded désactivé).
        if base in STATIC_BASE_RECIPE_KEYS:
            continue

        result_onto[base] = {}
        result_refdb[base] = {}

        # ── Taxonomie au niveau base_key ──────────────────────────────────
        # Recherche directe par base_key (déjà slugifié par extract_base).
        # Le champ _taxonomy est stocké en tête de l'entrée pour être
        # immédiatement visible dans les outils de debug.
        _tax = build_taxonomy_object(base, _bk_taxonomy, fallback_unclassified=False)
        if _tax is not None:
            result_onto[base]["_taxonomy"] = _tax

        for variant, entries in variants.items():
            # Group by field — tuples sont (field, val, weight, has_fa)
            by_field: dict[str, list] = defaultdict(list)
            for field, val, w, hf in entries:
                by_field[field].append((val, w, hf))

            merged = {}
            stats  = {}
            for field, pairs in by_field.items():
                if field == "fat":
                    # Préférer les sources avec FA breakdown complet pour fat_g.
                    # Évite d'inflater fat via des sources sans sat/mufa/pufa
                    # (ex : CIQUAL fat=15g sans FA → gonfle la moyenne alors que
                    # USDA seul a sat+mufa+pufa → incohérence fat vs sous-fractions).
                    fa_pairs = [(v, w) for v, w, hf in pairs if hf]
                    use_pairs = fa_pairs if fa_pairs else [(v, w) for v, w, hf in pairs]
                    merged_val = weighted_merge(use_pairs)
                else:
                    use_pairs = [(v, w) for v, w, *_ in pairs]
                    merged_val = weighted_merge(use_pairs)
                merged[field] = round(merged_val, 4) if merged_val is not None else None
                if len(pairs) > 1 and merged_val is not None:
                    vals = [v for v, w, *_ in pairs if v is not None]
                    stats[field] = {
                        "n_sources": len(pairs),
                        "min": min(vals),
                        "max": max(vals),
                        "std": statistics.stdev(vals) if len(vals) > 1 else 0,
                    }

            # Clés longues pour ontologie riche
            merged_long = {INV_FIELD_MAP.get(k, k): v for k, v in merged.items()}
            merged_long["scientific_name"] = scientific_names.get(base)

            result_onto[base][variant] = {
                "nutrients": merged_long,
                "stats": stats,
                "n_sources": len(set(e[2] for e in entries)),  # e[2] = weight → proxy source
            }
            result_refdb[base][variant] = merged  # clés courtes pour backward compat

    # ── Application des alias ALIM → ontologie ─────────────────────────────
    # Crée des entrées miroir pour les ingrédients ALIM sans correspondance
    # directe. N'écrase pas une entrée existante.
    # Les clés marquées _base_recipe_excluded dans n2 sont SKIPPÉES : leur
    # valeur nutritionnelle est désormais calculée dynamiquement par
    # _compute_nutrition_from_recipe — pas de proxy statique dans l'ontologie.
    aliases_created:   dict[str, str] = {}
    aliases_missing:   list[str]      = []
    aliases_skipped:   list[str]      = []

    n2_excluded, n2_dual = load_n2_excluded_keys(N2_INPUT)

    for alim_key, onto_target in ALIM_ALIASES.items():
        if alim_key in result_onto:
            continue  # déjà résolu — pas besoin d'alias

        if alim_key in n2_excluded or alim_key in STATIC_BASE_RECIPE_KEYS:
            aliases_skipped.append(alim_key)
            continue  # base_recipe couvre cet ingrédient — pas de miroir statique

        real_key = _resolve_alias(onto_target, result_onto)
        if real_key:
            result_onto[alim_key]  = result_onto[real_key]
            result_refdb[alim_key] = result_refdb[real_key]
            aliases_created[alim_key] = real_key
        else:
            aliases_missing.append(f"{alim_key} → {onto_target} (cible absente)")

    if aliases_created:
        print(f"  Alias résolus  : {len(aliases_created)}")
        for k, v in aliases_created.items():
            print(f"    {k:<25} → {v}")
    if aliases_skipped:
        print(f"  Alias skippés (base_recipe) : {len(aliases_skipped)}")
        for k in aliases_skipped:
            print(f"    ⊘ {k}")
    if aliases_missing:
        print(f"  Alias manquants (cible introuvable) : {len(aliases_missing)}")
        for m in aliases_missing:
            print(f"    ⚠ {m}")

    # ── Corrections post-fusion ───────────────────────────────────────────────
    print("Corrections post-fusion (sanity fixes)...")
    _apply_sanity_fixes(result_onto, result_refdb)

    return result_onto, result_refdb, scientific_names, aliases_created, n2_excluded, n2_dual


# ══════════════════════════════════════════════════════════════════════════════
# STATIC BASE RECIPE EXCLUSIONS (audit 2026-04-28)
# ──────────────────────────────────────────────────────────────────────────────
# Ces ingredient_keys correspondent à des base_recipes dont la valeur
# nutritionnelle est CALCULÉE dynamiquement depuis leur composition (recette).
# Ils ne doivent JAMAIS être construits comme variants dans l'ontologie, même
# lorsque nutrition_v2.json est absent (le filtre dynamique n2_excluded serait
# alors désactivé et laisserait passer ces clés).
#
# Maintenance : mettre à jour quand un ingredient_key est ajouté/retiré de
# recipes.json (is_base_recipe=True). Source : recipes_final_9plus_final_v4.json
# ══════════════════════════════════════════════════════════════════════════════
STATIC_BASE_RECIPE_KEYS: frozenset[str] = frozenset({
    "bechamel",
    "cheddar_vegane",
    "chili_paste",
    "coconut_cream",
    "cream_cheese",
    "creme_fraiche",
    "dashi_broth",
    "empanada_dough",
    "ghee",
    "gnocchi_vegan",
    "gochujang",
    "green_curry_paste",
    "harissa",
    "hoisin_sauce",
    "japanese_curry_roux",
    "mala_broth",
    "mayonnaise",
    "miso_broth",
    "miso_paste",
    "mole_sauce",
    "mozzarella_vegane",
    "natto",
    "okonomiyaki_sauce",
    "peanut_butter",
    "pesto",
    "pistou",
    "pizza_dough",
    "puff_pastry",
    "red_curry_paste",
    "salted_butter_caramel",
    "salted_ricotta",
    "samosa_dough",
    "sauce_tomate",       # ← cause de sauce/energy_mismatch — recette calculable
    "seitan",
    "shortcrust_pastry",
    "spring_roll_wrappers",
    "strawberry_coulis",
    "strawberry_jam",
    "tahini",
    "tamarind_paste",
    "teriyaki_sauce",
    "tomato_paste",
    "vegetable_broth",
    "vegetarian_brown_sauce",
    "vegetarian_fish_sauce",
    "vegetarian_oyster_sauce",
    "yellow_curry_paste",
    "falafel",              # recette composée (chickpeas+herbes) — 3 recettes dans recipes.json
})


# ══════════════════════════════════════════════════════════════════════════════
# CORRECTIONS POST-FUSION — cas particuliers biologiquement incorrects
# ══════════════════════════════════════════════════════════════════════════════
#
# Chaque bloc est autonome et documenté. Toutes les valeurs sont vérifiées
# contre USDA FDC / CIQUAL. L'ordre d'application est sans importance
# (chaque correction cible des champs distincts sur des variants distincts).
#
# Règle de non-régression :
#   - Ne modifier que les champs explicitement listés dans le bloc.
#   - Toujours vérifier que fat >= sat+mono+poly après correction FA.
#   - Toujours vérifier que poly >= omega3+omega6 après correction omega.
#   - Ne jamais toucher aux stats (calculées sur sources brutes, pas corrigées).
#
# ══════════════════════════════════════════════════════════════════════════════

def _patch_variant(
    result_onto: dict,
    result_refdb: dict,
    base: str,
    variant: str,
    long_updates: dict,   # clés longues (nutrition_v2 schema) → nouvelles valeurs
    label: str = "",
) -> bool:
    """
    Applique long_updates sur nutrients (result_onto) et traduit en clés courtes
    pour result_refdb. Ne touche qu'aux champs listés. Retourne True si trouvé.
    """
    if base not in result_onto or variant not in result_onto[base]:
        print(f"  ⚠ _patch_variant : {base}[{variant}] introuvable — ignoré ({label})")
        return False

    nutrients = result_onto[base][variant]["nutrients"]
    merged    = result_refdb[base][variant]

    for long_key, val in long_updates.items():
        nutrients[long_key] = val
        short_key = FIELD_MAP.get(long_key)
        if short_key:
            merged[short_key] = val

    if label:
        print(f"  ✓ {base}[{variant}] — {label}")
    return True


def _apply_sanity_fixes(result_onto: dict, result_refdb: dict) -> None:
    """
    Corrections post-fusion sur des variants spécifiques.
    Chaque bloc corrige un problème identifié lors de la validation croisée.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # 1. OMEGA > POLY : les omega3+omega6 dépassent la PUFA totale.
    #    Cause : sources multiples avec poly trop bas ou omega trop haut.
    #    Fix   : ajuster poly = max(poly_actuel, omega3+omega6) arrondi à 4 déc.
    #    Règle : on ne touche qu'à poly et fat si FA_sum > fat après ajustement.
    #    Ne pas toucher à omega3/omega6 (valeurs sources fiables).
    # ──────────────────────────────────────────────────────────────────────────
    OMEGA_POLY_FIXES: list[tuple[str, str]] = [
        # (base, variant)          Cause
        # milk_plant[cashew] : oméga6 hérité du cajou pur non dilué.
        #   Le lait de cajou est dilué ~1:8 → omega6 doit être recalculé.
        #   Fix spécifique : corriger omega6 + fat/FA vers profil lait dilué.
        #   (NE PAS relever poly comme pour les autres cas — fat=1.3g est correct)
        ("oil",         "coconut"), # om3+om6=12.01 > poly=1.8  (omega6 héritage huile erronée)
        ("fennel",      "default"), # om3+om6=1.69  > poly=0.05 (profil fenouil CIQUAL)
        ("tofu",        "silken"),  # om3+om6=7.03  > poly=5.18 (FA abaissé en fix précédent)
        ("tofu",        "firm"),    # om3+om6=7.03  > poly=5.18 (idem)
    ]
    for base, variant in OMEGA_POLY_FIXES:
        if base not in result_onto or variant not in result_onto[base]:
            continue
        nutrients = result_onto[base][variant]["nutrients"]
        merged    = result_refdb[base][variant]

        om3  = nutrients.get("omega3_g")  or 0
        om6  = nutrients.get("omega6_g")  or 0
        poly = nutrients.get("polyunsaturated_fat_g") or 0
        fat  = nutrients.get("fat_g") or 0
        sat  = nutrients.get("saturated_fat_g") or 0
        mono = nutrients.get("monounsaturated_fat_g") or 0

        new_poly = round(max(poly, om3 + om6), 4)
        # Si ajuster poly dépasse fat, relever fat au minimum
        new_fat = round(max(fat, sat + mono + new_poly), 4)

        nutrients["polyunsaturated_fat_g"] = new_poly
        merged["pufa"] = new_poly
        if new_fat != fat:
            nutrients["fat_g"] = new_fat
            merged["fat"] = new_fat

        print(f"  ✓ omega>poly fix  {base}[{variant}]: poly {poly}→{new_poly}"
              + (f", fat {fat}→{new_fat}" if new_fat != fat else ""))

    # ──────────────────────────────────────────────────────────────────────────
    # 2. NULL SUR CHAMPS REQUIS : remplacer par la valeur biologique correcte.
    #
    #    Règle générale :
    #      - omega3/omega6 null sur végétaux non gras → 0.0
    #      - omega3/omega6 null sur œuf dur → valeurs USDA œuf entier
    #      - phosphorus null sur huile → 0 (huile raffinée = pas de phosphore)
    #      - sugar null sur huile de lin → 0 (huile = pas de sucres)
    #      - mono/poly/omega null sur champignon → valeurs USDA shiitake
    # ──────────────────────────────────────────────────────────────────────────

    # oil[flaxseed] : sugar=null → 0, phosphorus=null → 0
    _patch_variant(result_onto, result_refdb, "oil", "default", {
        "sugar_g":      0.0,
        "phosphorus_mg": 0.0,
    }, "oil[flaxseed] null→0 (huile raffinée)")

    # hard_boiled_egg : omega3=null, omega6=null → valeurs USDA FDC 173424
    # Œuf dur entier : omega3=0.109g, omega6=1.07g
    _patch_variant(result_onto, result_refdb, "hard_boiled_egg", "raw", {
        "omega3_g": 0.109,
        "omega6_g": 1.07,
    }, "hard_boiled_egg omega3/6 (USDA FDC 173424)")

    # mushroom[shiitake] : mono=null, poly=null, omega3=null, omega6=null, phosphorus=null
    # USDA FDC 168436 shiitake raw: mono=0.016, poly=0.109, phosphorus=112mg
    # omega3=0.002g, omega6=0.107g
    _patch_variant(result_onto, result_refdb, "mushroom", "raw", {
        "monounsaturated_fat_g":  0.016,
        "polyunsaturated_fat_g":  0.109,
        "omega3_g":               0.002,
        "omega6_g":               0.107,
        "phosphorus_mg":          112.0,
    }, "mushroom[shiitake] null→USDA FDC 168436")

    # reshteh_noodles : omega3=null, omega6=null → valeurs proxy (pâtes de blé)
    # USDA pâtes sèches : omega3≈0.03g, omega6≈0.37g pour 100g
    _patch_variant(result_onto, result_refdb, "reshteh_noodles", "default", {
        "omega3_g": 0.03,
        "omega6_g": 0.37,
    }, "reshteh_noodles omega3/6 proxy blé (USDA)")

    # ──────────────────────────────────────────────────────────────────────────
    # 3. flax_egg cholesterol=474 : héritage d'un œuf entier non dilué.
    #    Le flax egg (1 cs graines lin + 3 cs eau) est vegan et ne contient
    #    pas de cholestérol. La valeur 474 vient d'un œuf de poule non pondéré.
    #    Fix : cholesterol = 0, allergen eggs = False.
    #    Note : on ne touche pas aux autres champs (protéines, lipides) ici —
    #    ils font l'objet d'un audit séparé.
    # ──────────────────────────────────────────────────────────────────────────
    _patch_variant(result_onto, result_refdb, "flax_egg", "raw", {
        "cholesterol_mg": 0.0,
    }, "flax_egg cholesterol=474→0 (préparation végane, pas d'œuf)")

    # ──────────────────────────────────────────────────────────────────────────
    # 4. butter[almond] profil lipidique erroné.
    #    fat=81.85g et sat=44.6g sont ceux d'un corps gras saturé (karité/coco),
    #    pas du beurre d'amande. USDA FDC 168588 (almond butter, plain) :
    #      fat=55.53, sat=5.19, mono=35.11, poly=12.27, prot=20.96
    #    Les carbs/fiber/sugar corrigés en session précédente sont conservés.
    #    On corrige uniquement fat + FA (protein déjà vu, hors scope ici).
    # ──────────────────────────────────────────────────────────────────────────
    # butter[almond] : clé introuvable dans l'ontologie (almond butter indexé
    # sous butter[default] = beurre laitier, incompatible). Correction déjà
    # appliquée sur la DB ALIM via patch_nutrition_v8.py URGENT_FIXES.
    # _patch_variant(result_onto, result_refdb, "butter", "almond", {...})  # désactivé

    # ──────────────────────────────────────────────────────────────────────────
    # 5. CAL_MISMATCH — catégories et corrections ciblées.
    #
    #    5a. Épices/herbes/algues avec fiber>carbs (CIQUAL sec vs frais) :
    #        Les calories CIQUAL sont exprimées sur matière sèche, cohérentes
    #        avec les vraies valeurs. L'écart Atwater est un artefact du mix
    #        sec/frais, PAS une erreur de calories. → Ne pas corriger les cal.
    #        Ces cas sont documentés dans _validation.known_issues et ignorés.
    #
    #    5b. Légumineuses (bean, chickpea) :
    #        cal=127 (cuit) mais carbs=12.15 (cuit) et fiber>carbs → même cause
    #        que 5a. Calories CIQUAL cuites, fibres sèches. → Ignorer.
    #
    #    5c. Noix (almond, cashew) :
    #        cal USDA = 579/533. Atwater sur amandes donne trop haut car
    #        les fibres d'amandes ont une digestibilité réduite (~25% des
    #        lipides indigestibles). USDA utilise la méthode "Modified Atwater"
    #        (facteur lipides amandes ≈ 8.0 kcal/g au lieu de 9).
    #        → Les calories déclarées sont correctes. Ignorer.
    #
    #    5d. Produits biologiquement justifiés :
    #        xylitol (2.4 kcal/g), chia (fibres insolubles), carob, chlorella.
    #        → Ignorer.
    #
    #    5e. seitan : cal=134 avec prot≈20g, carbs≈20g, fat≈7g → est=230.
    #        Valeur déclarée 134 est manifestement celle du seitan CUIT dilué
    #        (≈140 kcal) mais macros de seitan CONCENTRÉ. Corriger calories.
    #
    #    5f. chocolate[powder] : 228 kcal vs est 433.
    #        228 kcal correspond au cacao en poudre NON SUCRÉ dégraissé
    #        (USDA id 19165 : cal=229, fat=13.7g, carbs=57.9g, prot=19.6g).
    #        Mais fat=43.5g dans le fichier → profil de cacao GRAS (non dégraissé).
    #        Les cal et macros proviennent de deux produits différents.
    #        Corriger fat/carbs/prot vers profil cacao non sucré non dégraissé.
    #
    #    5g. mirin : decl=241, est=312. Mirin contient alcool~14% non comptabilisé.
    #        alcohol_g manquant → Atwater sous-estime. Corriger alcohol_g.
    #
    # ──────────────────────────────────────────────────────────────────────────

    # 5e. seitan : macros concentré, calories cuites → corriger calories
    # USDA FDC 174804 seitan cuit : cal=142, prot=25.9, carbs=5.0, fat=2.37
    _patch_variant(result_onto, result_refdb, "seitan", "default", {
        "calories_kcal": 142.0,
        "protein_g":     25.9,
        "carbs_g":        5.0,
        "fat_g":          2.37,
    }, "seitan cal+macros (USDA FDC 174804 seitan cuit)")

    # 5f. chocolate[powder] : unifier sur profil cacao poudre non sucré non dégraissé
    # USDA FDC 19165 cocoa powder unsweetened : cal=229, fat=13.7, carbs=57.9, prot=19.6
    # fiber=33.2, sugar=1.75
    _patch_variant(result_onto, result_refdb, "dark_chocolate", "default", {
        "calories_kcal": 229.0,
        "fat_g":          13.7,
        "carbs_g":        57.9,
        "protein_g":      19.6,
        "fiber_g":        33.2,
        "sugar_g":         1.75,
        "saturated_fat_g":  8.07,
        "monounsaturated_fat_g": 4.57,
        "polyunsaturated_fat_g": 0.44,
    }, "chocolate[powder] → cacao poudre non sucré (USDA FDC 19165)")

    # 5g. mirin : ajouter alcohol_g manquant
    # Mirin hon-mirin : ~14% alcool → 14g/100g. cal=241 cohérent avec alcohol inclus.
    _patch_variant(result_onto, result_refdb, "mirin", "default", {
        "alcohol_g": 14.0,
    }, "mirin alcohol_g=14 (hon-mirin ~14% ABV)")

    # ──────────────────────────────────────────────────────────────────────────
    # 6. butter[dairy] : calories 626.48 vs Atwater 733.
    #    Beurre 82% MG : USDA FDC 173410 → cal=717, fat=81.1, prot=0.85, carbs=0.06
    #    La valeur 626 provient d'un beurre allégé (fat~70g), pas d'un beurre
    #    standard 82% MG. Corriger calories vers USDA.
    # ──────────────────────────────────────────────────────────────────────────
    _patch_variant(result_onto, result_refdb, "butter", "default", {
        "calories_kcal": 717.0,
    }, "butter[dairy] cal 626→717 (USDA FDC 173410, beurre 82% MG)")

    # ──────────────────────────────────────────────────────────────────────────
    # 7. milk_plant[cashew] : omega6 hérité du cajou PUR (non dilué).
    #    Le lait de cajou est une dilution ~1:8 cajou:eau.
    #    Le fix omega>poly (bloc 1) aurait remonté poly à 8.57g sur fat=1.3g,
    #    ce qui est incohérent. On corrige ici l'omega6 à la valeur réelle du
    #    lait dilué, et on rétablit le profil lipidique complet.
    # ──────────────────────────────────────────────────────────────────────────
    # milk_plant[cashew] : seul variant disponible milk_plant[default] = lait végétal
    # générique. Appliquer les valeurs spécifiques cajou écraserait tous les laits
    # végétaux. Correction déjà gérée via patch_nutrition_v8.py URGENT_FIXES.
    # _patch_variant(result_onto, result_refdb, "milk_plant", "cashew", {...})  # désactivé

    # ──────────────────────────────────────────────────────────────────────────
    # 8. flour[oat] : fat=2.09g incorrect (farine allégée) vs USDA farine complète.
    #    USDA FDC 173948 whole oat flour : fat=8.4g, prot=14.7g, cal=404kcal.
    # ──────────────────────────────────────────────────────────────────────────
    # flour[oat] : seul variant flour[default] existe. Appliquer fat=8.4g
    # (avoine) écraserait la farine de blé standard (fat~1.5g) — incompatible.
    # La farine d'avoine est indexée séparément sous oats_d'avoine dans l'ontologie.
    # _patch_variant(result_onto, result_refdb, "flour", "oat", {...})  # désactivé

    # ──────────────────────────────────────────────────────────────────────────
    # 9. chocolate[powder] : ecart Atwater justifié (Atwater modifié USDA pour cacao).
    #    cal=229 = valeur USDA directe. Atwater standard sur carbs bruts donne 433
    #    car les fibres de cacao (~33g) ne sont digestibles qu'à ~50%.
    #    Aucune correction de données — documenté comme cas justifié dans le rapport.
    # ──────────────────────────────────────────────────────────────────────────
    # (pas de _patch_variant nécessaire — valeurs déjà correctes)

    # ══════════════════════════════════════════════════════════════════════════════
    # PATCH 2026-05 : AJOUT DES 19 ENTRÉES MANQUANTES (seitan + 18)
    # ══════════════════════════════════════════════════════════════════════════════
    print("  Ajout des entrées manquantes (seitan + 18)...")

    new_entries = {
        "seitan": {
            "default": {
                "nutrients": {
                    "calories_kcal": 142.0,
                    "protein_g": 25.9,
                    "fat_g": 2.37,
                    "carbs_g": 5.0,
                    "fiber_g": 0.6,
                    "sugar_g": 0.0,
                    "starch_g": 3.8,
                    "saturated_fat_g": 0.27,
                    "monounsaturated_fat_g": 0.27,
                    "polyunsaturated_fat_g": 0.91,
                    "omega3_g": 0.13,
                    "omega6_g": 0.77,
                    "cholesterol_mg": 0.0,
                    "sodium_mg": 360.0,
                    "potassium_mg": 51.0,
                    "iron_mg": 2.7,
                    "calcium_mg": 14.0,
                    "magnesium_mg": 14.0,
                    "phosphorus_mg": 117.0,
                    "zinc_mg": 0.8,
                    "selenium_ug": 29.0,
                    "vitamin_b12_ug": 0.0
                },
                "stats": {"n_sources": 1, "data_quality": "high", "source": "USDA FDC 174804"}
            }
        },
        "dried_fig": {
            "dried": {
                "nutrients": {
                    "calories_kcal": 249.0, "protein_g": 3.3, "fat_g": 0.9,
                    "carbs_g": 63.9, "fiber_g": 9.8, "sugar_g": 47.9,
                    "potassium_mg": 680.0, "calcium_mg": 162.0
                }
            }
        },
        "black_beans": {
            "cooked": {
                "nutrients": {
                    "calories_kcal": 132.0, "protein_g": 8.9, "fat_g": 0.5,
                    "carbs_g": 23.7, "fiber_g": 8.7, "iron_mg": 2.1,
                    "folate_ug": 149.0
                }
            }
        },
        "pumpkin_seeds": {
            "raw": {
                "nutrients": {
                    "calories_kcal": 559.0, "protein_g": 30.2, "fat_g": 49.1,
                    "carbs_g": 10.7, "fiber_g": 6.0, "magnesium_mg": 592.0,
                    "zinc_mg": 7.6, "iron_mg": 8.8
                }
            }
        },
        "gnocchi": {
            "cooked": {
                "nutrients": {
                    "calories_kcal": 176.0, "protein_g": 4.0, "carbs_g": 38.0,
                    "fat_g": 1.2
                }
            }
        },
        "pea_protein": {
            "default": {
                "nutrients": {
                    "calories_kcal": 370.0, "protein_g": 75.0, "fat_g": 8.0,
                    "carbs_g": 8.0, "fiber_g": 6.0
                }
            }
        },
        "halloumi": {
            "raw": {
                "nutrients": {
                    "calories_kcal": 320.0, "protein_g": 20.0, "fat_g": 25.0,
                    "calcium_mg": 612.0, "sodium_mg": 1100.0
                }
            }
        },
        "matcha_tea": {
            "default": {
                "nutrients": {
                    "calories_kcal": 3.0, "vitamin_k1_ug": 2130.0
                }
            }
        },
        "star_anise": {
            "default": {
                "nutrients": {
                    "calories_kcal": 337.0, "iron_mg": 36.9
                }
            }
        },
        "sumac": {
            "default": {
                "nutrients": {
                    "calories_kcal": 270.0, "calcium_mg": 500.0
                }
            }
        },
        "curry_leaves": {
            "raw": {
                "nutrients": {
                    "calories_kcal": 108.0, "calcium_mg": 830.0
                }
            }
        },
        "date_syrup": {
            "default": {
                "nutrients": {
                    "calories_kcal": 290.0, "potassium_mg": 550.0, "sugar_g": 65.0
                }
            }
        },
        "kombucha": {
            "fermented": {
                "nutrients": {
                    "calories_kcal": 19.0, "alcohol_g": 0.5
                }
            }
        },
        "attieke": {
            "cooked": {
                "nutrients": {
                    "calories_kcal": 170.0, "carbs_g": 38.0
                }
            }
        },
        "tvp": {
            "default": {
                "nutrients": {
                    "calories_kcal": 330.0, "protein_g": 52.0, "iron_mg": 15.0
                }
            }
        },
        "umeboshi_plum": {
            "fermented": {
                "nutrients": {
                    "calories_kcal": 35.0, "sodium_mg": 8700.0
                }
            }
        },
        "sriracha": {
            "default": {
                "nutrients": {
                    "calories_kcal": 93.0, "sodium_mg": 2200.0
                }
            }
        },
        "cream_plant": {
            "default": {
                "nutrients": {
                    "calories_kcal": 180.0, "fat_g": 18.0, "vitamin_b12_ug": 0.5
                }
            }
        }
    }

    for base_key, variants in new_entries.items():
        if base_key not in result_onto:
            result_onto[base_key] = {}
            result_refdb[base_key] = {}
        for variant_name, data in variants.items():
            result_onto[base_key][variant_name] = data
            # Mise à jour reference_db
            result_refdb[base_key][variant_name] = {
                FIELD_MAP.get(k, k): v 
                for k, v in data.get("nutrients", {}).items()
            }
            print(f"    ✓ Ajouté : {base_key}[{variant_name}]")

    print(f"  Sanity fixes appliqués.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 70)
    print("BUILD ONTOLOGY v6")
    print("═" * 70)

    REF_DIR.mkdir(parents=True, exist_ok=True)
    mapping = load_mapping(MAPPING_FILE)
    print(f"  Mapping chargé : {len(mapping)} entrées")

    onto, refdb, sci_names, aliases, n2_excluded, n2_dual = build_ontology(mapping)

    # Export ontologie riche
    # Comptage réel des variants (hors clés _meta comme _taxonomy)
    _total_variants_onto = sum(
        sum(1 for vk in variants if not vk.startswith("_"))
        for variants in onto.values()
    )
    onto_output = {
        "schema_version": "6.0",
        "generated_at": datetime.now().isoformat(),
        "source_weights": SOURCE_WEIGHTS,
        "fields": list(FIELD_MAP.keys()),
        "total_bases": len(onto),
        "total_variants": _total_variants_onto,
        "aliases": aliases,          # clé ALIM → clé ontologie réelle
        "aliases_count": len(aliases),
        "taxonomy_coverage": sum(1 for v in onto.values() if "_taxonomy" in v),
        # Clés dont la nutrition est calculée dynamiquement via _compute_nutrition_from_recipe.
        # Le resolver doit bypasser l'ontologie statique pour ces clés.
        "base_recipe_computed_keys": sorted(n2_excluded),
        "base_recipe_dual_keys":     {k: v for k, v in sorted(n2_dual.items())},
        "ingredients": onto,
        "scientific_names": sci_names,
    }
    with open(OUTPUT_ONTO, "w", encoding="utf-8") as f:
        json.dump(onto_output, f, ensure_ascii=False, indent=2)
    print(f"OK Ontologie v6 -> {OUTPUT_ONTO}")

    # Rapport
    field_coverage = defaultdict(int)
    for base, variants in onto.items():
        for variant, data in variants.items():
            # _taxonomy est une clé de métadonnée au niveau base, pas un variant
            if variant.startswith("_"):
                continue
            for field, val in data["nutrients"].items():
                if val is not None:
                    field_coverage[field] += 1

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_bases": len(onto),
        "total_variants": _total_variants_onto,
        "aliases_count": len(aliases),
        "aliases": aliases,
        "taxonomy_coverage": sum(1 for v in onto.values() if "_taxonomy" in v),
        "base_recipe_computed_keys": sorted(n2_excluded),
        "base_recipe_dual_keys":     {k: v for k, v in sorted(n2_dual.items())},
        "field_coverage": {
            f: f"{100 * c // _total_variants_onto}%" if _total_variants_onto else "0%"
            for f, c in sorted(field_coverage.items())
        },
        "new_fields_v6": [
            "starch_g", "alcohol_g", "iodine_ug", "choline_mg", "trans_fat_g",
            "beta_carotene_ug", "vitamin_k2_ug", "polyols_g", "organic_acids_g",
            "omega3_ala_g", "omega3_epa_g", "omega3_dha_g", "scientific_name"
        ]
    }
    with open(OUTPUT_RPT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"OK Rapport       -> {OUTPUT_RPT}")

    # Export reference_db (backward compat auto_correct_v5/v6)
    refdb_output = {
        "schema_version": "6.0",
        "generated_at": datetime.now().isoformat(),
        "source_weights": SOURCE_WEIGHTS,
        "reference": refdb,
    }
    with open(OUTPUT_REFDB, "w", encoding="utf-8") as f:
        json.dump(refdb_output, f, ensure_ascii=False, indent=2)
    print(f"OK Reference DB  -> {OUTPUT_REFDB}")

    # ── Écriture nutrition_v2_runtime.json — n2 purgé des variants _base_recipe_excluded ──
    # Le moteur charge ce fichier au runtime. Les variants exclus sont absents :
    # le resolver tombera sur KeyError/None et basculera vers _compute_nutrition_from_recipe.
    if N2_INPUT.exists():
        with open(N2_INPUT, encoding="utf-8") as f:
            n2_raw = json.load(f)

        n2_runtime_ing: dict = {}
        removed_variants = 0
        for base_key, entry in n2_raw.get("ingredients", {}).items():
            variants_in  = entry.get("variants", {})
            variants_out = {
                vname: v for vname, v in variants_in.items()
                if not v.get("_base_recipe_excluded")
            }
            removed_variants += len(variants_in) - len(variants_out)
            if variants_out:
                n2_runtime_ing[base_key] = {**entry, "variants": variants_out}
            # Si tous les variants sont exclus → entrée entière retirée

        n2_runtime = {
            **{k: v for k, v in n2_raw.items() if k != "ingredients"},
            "generated_at":              datetime.now().isoformat(),
            "base_recipe_computed_keys": sorted(n2_excluded),
            "ingredients":               n2_runtime_ing,
        }
        with open(N2_RUNTIME, "w", encoding="utf-8") as f:
            json.dump(n2_runtime, f, ensure_ascii=False, indent=2)
        print(f"OK n2 runtime    -> {N2_RUNTIME}  "
              f"({len(n2_runtime_ing)} bases | {removed_variants} variants supprimés)")
    else:
        print(f"  ⚠️  nutrition_v2 absent — n2_runtime non généré")
    tax_cov = sum(1 for v in onto.values() if "_taxonomy" in v)
    print(f"\nTotal bases : {len(onto)} | Variants : {_total_variants_onto} | Alias : {len(aliases)} | Taxonomy : {tax_cov}/{len(onto)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
