"""
restructure_nutrition_v2.py
═══════════════════════════
Refonte structurelle de nutrition_v2.json + extension depuis ontology_v6.json
+ corrections qualité intégrées (ex patch_quality_v1.py — supprimé).

Trois problèmes résolus en une passe :
  1. STRUCTURE  — nodes/ombelles = conteneurs vides, plus de variant "default"
                  porteur de données. Leaves : variant renommé selon état réel.
  2. COUVERTURE — extension depuis l'ontologie (cultivars pomme, variantes légumes,
                  haricots additionnels, fromages, etc.) sans importer les plats
                  préparés, ultra-transformés, doublons source.
  3. QUALITÉ    — §10 : carbs_schema, energy_kj, cohérence sugar/carbs,
                  vitamines None, corrections cross-source (fig, shallot).

Intégration dans le pipeline :
  → Copier _restructure_nodes() et les constantes dans promote_nutrition.py
  → Appeler _restructure_nodes(CANONICAL_FILE, ONTOLOGY_FILE) en step 10
     (après _recompute_meta_counters, idempotent)

Usage autonome (une seule fois ou pour test) :
  python restructure_nutrition_v2.py --confirm
  python restructure_nutrition_v2.py             # dry-run, affiche le plan

IMPORTANT : lire les commentaires de chaque section avant de modifier les maps.

Changelog :
  v2.0 (2026-05-11) — fusion avec patch_quality_v1.py (§10 qualité globale)
                      + carbs_schema et energy_kj inline dans _build_variant_from_onto
"""

import copy
import json
import sys
from pathlib import Path
from datetime import datetime

# ── Chemins (mode autonome) ───────────────────────────────────────────────────
HERE          = Path(__file__).resolve()
BASE_DIR      = HERE.parents[2]           # racine du projet ALIM
NUTRITION_V2  = BASE_DIR / "backend/data/nutrition/processed/nutrition_v2.json"
ONTOLOGY_FILE = BASE_DIR / "backend/data/nutrition/reference/ontology_v6.json"
TODAY         = datetime.now().strftime("%Y-%m-%d")


# ══════════════════════════════════════════════════════════════════════════════
# §1 — PURGES DÉFINITIVES
# Entrées à supprimer de nutrition_v2 (fantômes, non-comestibles, hors-scope).
# ══════════════════════════════════════════════════════════════════════════════
PURGE_KEYS: frozenset[str] = frozenset({
    "corn_husk",      # emballage non-comestible
    "grain",          # fantôme trop générique — aucune recette ne l'utilise tel quel
    "spices",         # idem
    "starch",         # doublon de corn_starch / tapioca_starch / arrowroot
    "dried_fig",      # alias orphelin — fig/dried existe déjà
})


# ══════════════════════════════════════════════════════════════════════════════
# §2 — DÉPLACEMENTS leaf → variant d'un node EXISTANT
#
# Format : leaf_id → (node_id, variant_key)
# La leaf est supprimée après copie de ses données dans le variant cible.
# Si le variant cible existe déjà → on conserve les données existantes (idempotent).
# ══════════════════════════════════════════════════════════════════════════════
LEAF_TO_VARIANT: dict[str, tuple[str, str]] = {
    # ── bell_pepper ───────────────────────────────────────────────────────────
    "bell_pepper_yellow": ("bell_pepper",   "yellow"),   # variant déjà existant

    # ── cabbage ───────────────────────────────────────────────────────────────
    "green_cabbage":      ("cabbage",       "green"),    # variant déjà existant

    # ── bean ──────────────────────────────────────────────────────────────────
    "black_beans":        ("bean",          "black"),    # variant déjà existant
    "lupine":             ("bean",          "lupine"),   # variant déjà existant
    "gigante_bean":       ("bean",          "giant_white"), # variant déjà existant

    # ── chili ─────────────────────────────────────────────────────────────────
    "ancho_chili":        ("chili",         "ancho"),

    # ── sauce ─────────────────────────────────────────────────────────────────
    "bechamel":           ("sauce",         "bechamel"),
    "mole_sauce":         ("sauce",         "mole"),

    # ── seeds ─────────────────────────────────────────────────────────────────
    "pumpkin_seeds":      ("seeds",         "pumpkin"),  # variant déjà existant

    # ── sesame ────────────────────────────────────────────────────────────────
    # tahini (leaf manufactured) fusionne avec sesame/tahini_raw → renommé tahini
    "tahini":             ("sesame",        "tahini"),

    # ── yogurt_animal ─────────────────────────────────────────────────────────
    "greek_yogurt":       ("yogurt_animal", "greek"),    # variant déjà existant
    "fromage_blanc":      ("yogurt_animal", "fromage_blanc"),
    "kashk":              ("yogurt_animal", "kashk"),
}


# ══════════════════════════════════════════════════════════════════════════════
# §3 — NOUVEAUX NODES (leaf → node + absorption d'autres leaves)
#
# Format : new_node_id → {
#   "_meta": {...},
#   "absorbs": {variant_key: leaf_id_source, ...},
#              leaf_id_source = None → données à peupler depuis ontologie (§5)
# }
#
# Les leaves listées dans "absorbs" sont supprimées après migration.
# ══════════════════════════════════════════════════════════════════════════════
NEW_NODES: dict[str, dict] = {

    # ── apple : leaf → node ──────────────────────────────────────────────────
    # Variétés CIQUAL confirmées dans ontology_v6. generic = données de apple/raw.
    "apple": {
        "_meta": {
            "category": "fruit",
            "name_fr": "pomme",
            "scientific_name": "Malus domestica",
            "is_standalone": False,
        },
        "absorbs": {
            "generic":      None,          # ← données de apple/raw dans ontologie
            "golden":       None,          # ← apple_golden/raw
            "gala":         None,          # ← apple_gala/raw
            "granny_smith": None,          # ← apple_granny_smith/raw
            "pink_lady":    None,          # ← apple_pink_lady/raw
            "chantecler":   None,          # ← apple_chantecler/raw
            "canada":       None,          # ← apple_canada/raw
            "cooked":       None,          # ← apple/cooked.cooked_generic
            "dried":        None,          # ← apple/dried
        },
        "delete_leaves": ["green_apple", "red_apple"],  # doublons génériques
    },

    # ── coconut : leaf → node ────────────────────────────────────────────────
    # coconut_flesh → coconut/fresh
    # Note : huile → oil/coconut, lait → milk_plant/coconut, sucre → sugar/coconut
    #        crème → cream_plant/coconut (déjà présent)
    "coconut": {
        "_meta": {
            "category": "fruit",
            "name_fr": "noix de coco",
            "scientific_name": "Cocos nucifera",
            "is_standalone": False,
        },
        "absorbs": {
            "fresh":      "coconut_flesh",   # données de coconut_flesh/default
            "desiccated": None,              # ← flour_coconut ou coconut_flesh desiccated
            "toasted":    None,              # données manuelles ou ontologie
        },
        "delete_leaves": ["coconut_flesh"],
    },

    # ── baking : 2 leaves → node ─────────────────────────────────────────────
    "baking": {
        "_meta": {
            "category": "leavening",
            "name_fr": "levure / poudre à lever",
            "scientific_name": None,
            "is_standalone": False,
        },
        "absorbs": {
            "powder": "baking_powder",
            "soda":   "baking_soda",
        },
        "delete_leaves": ["baking_powder", "baking_soda"],
    },

    # ── cheese : leaf générique → ombelle ────────────────────────────────────
    # Tous les fromages animaux fusionnés sous un seul node.
    "cheese": {
        "_meta": {
            "category": "dairy",
            "name_fr": "fromage",
            "scientific_name": None,
            "is_standalone": False,
        },
        "absorbs": {
            "cheddar":   "cheddar",
            "feta":      "feta",
            "mozzarella":"mozzarella",
            "parmesan":  "parmesan",
            "gruyere":   "gruyere",
            "comte":     "comte",
            "halloumi":  "halloumi",
            "ricotta":   "ricotta",
            "paneer":    "paneer",
            "curds":     "cheese_curds",
            "fresh":     "fresh_cheese",
        },
        # cheese (leaf générique) était déjà dans n2 — ses données deviennent
        # cheese/generic si elles ne dupliquent rien
        "delete_leaves": [
            "cheddar","feta","mozzarella","parmesan","gruyere","comte",
            "halloumi","ricotta","paneer","cheese_curds","fresh_cheese",
        ],
    },

    # ── mango : leaf → node ──────────────────────────────────────────────────
    "mango": {
        "_meta": {
            "category": "fruit",
            "name_fr": "mangue",
            "scientific_name": "Mangifera indica",
            "is_standalone": False,
        },
        "absorbs": {
            "fresh": "mango",       # données actuelles de mango/default
            "green": "green_mango", # données de green_mango/default
            "dried": None,          # ontologie si disponible
        },
        "delete_leaves": ["green_mango"],
    },

    # ── grape : leaf → node ──────────────────────────────────────────────────
    "grape": {
        "_meta": {
            "category": "fruit",
            "name_fr": "raisin",
            "scientific_name": "Vitis vinifera",
            "is_standalone": False,
        },
        "absorbs": {
            "white":  "grape",         # données actuelles de grape/default
            "dried":  "dried_raisins", # données de dried_raisins/default
            "red":    None,            # ontologie
            "black":  None,            # ontologie
        },
        "delete_leaves": ["dried_raisins"],
    },

    # ── pea : 4 leaves → node ────────────────────────────────────────────────
    # Retirer aussi snow_pea du node bean/ après création.
    "pea": {
        "_meta": {
            "category": "legume",
            "name_fr": "pois",
            "scientific_name": "Pisum sativum",
            "is_standalone": False,
        },
        "absorbs": {
            "green":       "green_peas",
            "snow":        "snow_pea",
            "sugar_snap":  "sugar_snap_pea",
            "dried":       "dried_pea",
        },
        "delete_leaves": ["green_peas","snow_pea","sugar_snap_pea","dried_pea"],
        "remove_from_bean": ["snow_pea"],   # retirer aussi de bean/snow_pea
    },

    # ── celery : 2 leaves → node ─────────────────────────────────────────────
    "celery": {
        "_meta": {
            "category": "vegetable",
            "name_fr": "céleri",
            "scientific_name": "Apium graveolens",
            "is_standalone": False,
        },
        "absorbs": {
            "stalk": "celery",
            "root":  "celery_root",
        },
        "delete_leaves": ["celery_root"],
        # celery leaf elle-même est réutilisée comme node
        "_self_becomes_node": True,
    },

    # ── paprika : 2 leaves → node ────────────────────────────────────────────
    "paprika": {
        "_meta": {
            "category": "herb_spice",
            "name_fr": "paprika",
            "scientific_name": "Capsicum annuum",
            "is_standalone": False,
        },
        "absorbs": {
            "sweet":  "paprika",
            "smoked": "smoked_paprika",
            "hot":    None,
        },
        "delete_leaves": ["smoked_paprika"],
        "_self_becomes_node": True,
    },

    # ── basil : 2 leaves → node ──────────────────────────────────────────────
    "basil": {
        "_meta": {
            "category": "herb_spice",
            "name_fr": "basilic",
            "scientific_name": "Ocimum basilicum",
            "is_standalone": False,
        },
        "absorbs": {
            "fresh": "basil",
            "dried": None,
            "thai":  "thai_basil",
        },
        "delete_leaves": ["thai_basil"],
        "_self_becomes_node": True,
    },

    # ── turmeric : 2 leaves → node ───────────────────────────────────────────
    "turmeric": {
        "_meta": {
            "category": "herb_spice",
            "name_fr": "curcuma",
            "scientific_name": "Curcuma longa",
            "is_standalone": False,
        },
        "absorbs": {
            "fresh": "turmeric_fresh",
            "ground": "turmeric",
        },
        "delete_leaves": ["turmeric_fresh"],
        "_self_becomes_node": True,
    },

    # ── coriander : 3 leaves → node ──────────────────────────────────────────
    "coriander": {
        "_meta": {
            "category": "herb_spice",
            "name_fr": "coriandre",
            "scientific_name": "Coriandrum sativum",
            "is_standalone": False,
        },
        "absorbs": {
            "fresh":  "fresh_coriander",
            "ground": "ground_coriander",
            "seeds":  "coriander",
        },
        "delete_leaves": ["fresh_coriander","ground_coriander"],
        "_self_becomes_node": True,
    },

    # ── cumin : 2 leaves → node ──────────────────────────────────────────────
    "cumin": {
        "_meta": {
            "category": "herb_spice",
            "name_fr": "cumin",
            "scientific_name": "Cuminum cyminum",
            "is_standalone": False,
        },
        "absorbs": {
            "seeds":  "cumin",
            "ground": "ground_cumin",
        },
        "delete_leaves": ["ground_cumin"],
        "_self_becomes_node": True,
    },

    # ── lemongrass : 2 leaves → node ─────────────────────────────────────────
    "lemongrass": {
        "_meta": {
            "category": "herb_spice",
            "name_fr": "citronnelle",
            "scientific_name": "Cymbopogon citratus",
            "is_standalone": False,
        },
        "absorbs": {
            "stalk": "lemongrass_stalk",
            "fresh": "lemongrass",
            "paste": None,
        },
        "delete_leaves": ["lemongrass_stalk"],
        "_self_becomes_node": True,
    },

    # ── ginger : leaf → node ─────────────────────────────────────────────────
    "ginger": {
        "_meta": {
            "category": "herb_spice",
            "name_fr": "gingembre",
            "scientific_name": "Zingiber officinale",
            "is_standalone": False,
        },
        "absorbs": {
            "fresh":   "ginger",
            "ground":  None,
            "pickled": None,
        },
        "_self_becomes_node": True,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# §4 — EXPANSION DE NODES EXISTANTS
#
# Ajouter de nouvelles leaves dans un node existant.
# format : node_id → {variant_key: leaf_id_à_absorber_ou_None}
# ══════════════════════════════════════════════════════════════════════════════
EXPAND_NODES: dict[str, dict[str, str | None]] = {
    # ── nut : node(3) → ombelle(9) ───────────────────────────────────────────
    # Absorbe 6 leaves indépendantes. almond reste son propre node (slivered/toasted).
    "nut": {
        "walnut":    "walnut",
        "hazelnut":  "hazelnut",
        "pecan":     "pecan",
        "macadamia": "macadamia",
        "cashew":    "cashew",
        "pistachio": "pistachio",
    },

    # ── tropical_fruit : node(1) → ombelle ───────────────────────────────────
    # jackfruit reste une leaf autonome (usage culinaire spécifique).
    "tropical_fruit": {
        "dragon_fruit":  "dragon_fruit",
        "lychee":        "lychee",
        "passion_fruit": "passion_fruit",
    },
}

# Leaves à supprimer après absorption dans EXPAND_NODES
EXPAND_DELETE_LEAVES: dict[str, list[str]] = {
    "nut":            ["walnut","hazelnut","pecan","macadamia","cashew","pistachio"],
    "tropical_fruit": ["dragon_fruit","lychee","passion_fruit"],
}


# ══════════════════════════════════════════════════════════════════════════════
# §5 — EXTENSION DEPUIS L'ONTOLOGIE
#
# Variantes supplémentaires à importer de ontology_v6.json vers des nodes n2.
# Format : (n2_base, variant_key) → (onto_key, onto_state, name_fr, name_en, ing_type)
# ingredient_type doit être un état réel : raw|cooked|dried|processed|fermented|refined
#
# Ces données ne sont importées QUE si le variant n'existe pas déjà dans n2.
# ══════════════════════════════════════════════════════════════════════════════
ONTOLOGY_PROMOTE_MAP: dict[tuple[str,str], tuple[str,str,str,str,str]] = {

    # ── apple cultivars (CIQUAL) ──────────────────────────────────────────────
    ("apple", "generic"):      ("apple",             "raw",                  "Pomme",            "apple",          "raw"),
    ("apple", "golden"):       ("apple_golden",      "raw",                  "Pomme golden",     "golden apple",   "raw"),
    ("apple", "gala"):         ("apple_gala",        "raw",                  "Pomme gala",       "gala apple",     "raw"),
    ("apple", "granny_smith"): ("apple_granny_smith","raw",                  "Pomme granny smith","granny smith",  "raw"),
    ("apple", "pink_lady"):    ("apple_pink_lady",   "raw",                  "Pomme pink lady",  "pink lady apple","raw"),
    ("apple", "chantecler"):   ("apple_chantecler",  "raw",                  "Pomme chantecler", "chantecler apple","raw"),
    ("apple", "canada"):       ("apple_canada",      "raw",                  "Pomme canada",     "canada apple",   "raw"),
    ("apple", "cooked"):       ("apple",             "cooked.cooked_generic","Pomme cuite",      "cooked apple",   "cooked"),
    ("apple", "dried"):        ("apple",             "dried",                "Pomme séchée",     "dried apple",    "dried"),

    # ── asparagus : blanche / verte / cuite ─────────────────────────────────
    ("asparagus", "white"):    ("asparagus_blanche", "default",              "Asperge blanche",  "white asparagus","raw"),
    ("asparagus", "green"):    ("asparagus_verte",   "default",              "Asperge verte",    "green asparagus","raw"),
    ("asparagus", "cooked"):   ("asparagus",         "cooked.boiled",        "Asperge cuite",    "cooked asparagus","cooked"),

    # ── barley : entier / perlé ───────────────────────────────────────────────
    ("barley", "whole"):       ("barley_complete",   "raw",                  "Orge entière",     "whole barley",   "raw"),
    ("barley", "pearled"):     ("barley_perlee",     "raw",                  "Orge perlée",      "pearled barley", "processed"),

    # ── beet : cru / cuit ────────────────────────────────────────────────────
    ("beet", "raw"):           ("beet",              "raw",                  "Betterave crue",   "raw beet",       "raw"),
    ("beet", "cooked"):        ("beet_rouge",        "cooked",               "Betterave cuite",  "cooked beet",    "cooked"),

    # ── bean : haricots supplémentaires ──────────────────────────────────────
    ("bean", "flageolet"):     ("bean_flageolet",    "default",              "Flageolet",        "flageolet bean", "raw"),
    ("bean", "mung"):          ("bean_mungo",        "dried",                "Haricot mungo",    "mung bean",      "raw"),
    ("bean", "lima"):          ("bean_lima",         "raw",                  "Haricot de Lima",  "lima bean",      "raw"),
    ("bean", "cannellini"):    ("beans_cannellini",  "dried",                "Haricot cannellini","cannellini bean","raw"),

    # ── chickpea : cuit (en plus du raw existant) ────────────────────────────
    ("chickpea", "cooked"):    ("chickpea",          "cooked.boiled",        "Pois chiche cuit", "cooked chickpea","cooked"),

    # ── lentil : variante supplémentaire ─────────────────────────────────────
    ("lentil", "french"):      ("lentil",            "raw",                  "Lentille verte du Puy","French lentil","raw"),

    # ── carrot : crue / cuite ────────────────────────────────────────────────
    ("carrot", "raw"):         ("carrot",            "raw",                  "Carotte crue",     "raw carrot",     "raw"),
    ("carrot", "cooked"):      ("carrot",            "cooked.boiled",        "Carotte cuite",    "cooked carrot",  "cooked"),

    # ── potato : états de cuisson ────────────────────────────────────────────
    ("potato", "raw"):         ("potato",            "raw",                  "Pomme de terre crue","raw potato",   "raw"),
    ("potato", "cooked"):      ("potato",            "cooked.boiled",        "Pomme de terre cuite","boiled potato","cooked"),

    # ── eggplant : cru / cuit ────────────────────────────────────────────────
    ("eggplant", "raw"):       ("eggplant",          "raw",                  "Aubergine crue",   "raw eggplant",   "raw"),
    ("eggplant", "cooked"):    ("eggplant",          "cooked.boiled",        "Aubergine cuite",  "cooked eggplant","cooked"),

    # ── zucchini : cru / cuit ────────────────────────────────────────────────
    ("zucchini", "raw"):       ("zucchini",          "raw",                  "Courgette crue",   "raw zucchini",   "raw"),
    ("zucchini", "cooked"):    ("zucchini",          "cooked.boiled",        "Courgette cuite",  "cooked zucchini","cooked"),

    # ── spinach : cru / cuit ─────────────────────────────────────────────────
    ("spinach", "raw"):        ("spinach",           "raw",                  "Épinards crus",    "raw spinach",    "raw"),
    ("spinach", "cooked"):     ("spinach",           "cooked.boiled",        "Épinards cuits",   "cooked spinach", "cooked"),

    # ── broccoli : cru / cuit ────────────────────────────────────────────────
    ("broccoli", "raw"):       ("broccoli",          "raw",                  "Brocoli cru",      "raw broccoli",   "raw"),
    ("broccoli", "cooked"):    ("broccoli",          "cooked.boiled",        "Brocoli cuit",     "cooked broccoli","cooked"),

    # ── cauliflower : cru / cuit ──────────────────────────────────────────────
    ("cauliflower", "raw"):    ("cauliflower",       "raw",                  "Chou-fleur cru",   "raw cauliflower","raw"),
    ("cauliflower", "cooked"): ("cauliflower",       "cooked.boiled",        "Chou-fleur cuit",  "cooked cauliflower","cooked"),

    # ── leek : cru / cuit ────────────────────────────────────────────────────
    ("leek", "raw"):           ("leek",              "raw",                  "Poireau cru",      "raw leek",       "raw"),
    ("leek", "cooked"):        ("leek",              "cooked.boiled",        "Poireau cuit",     "cooked leek",    "cooked"),

    # ── quinoa : cru / cuit ──────────────────────────────────────────────────
    ("quinoa", "raw"):         ("quinoa",            "raw",                  "Quinoa cru",       "raw quinoa",     "raw"),
    ("quinoa", "cooked"):      ("quinoa",            "cooked.cooked_generic","Quinoa cuit",      "cooked quinoa",  "cooked"),

    # ── oats : flocons / entiers ──────────────────────────────────────────────
    ("oats", "rolled"):        ("oats",              "raw",                  "Flocons d'avoine", "rolled oats",    "processed"),
    ("oats", "steel_cut"):     ("oats",              "raw",                  "Avoine steel cut", "steel cut oats", "raw"),

    # ── sweet_potato : cru / cuit ─────────────────────────────────────────────
    ("sweet_potato", "raw"):   ("sweet_potato",      "raw",                  "Patate douce crue","raw sweet potato","raw"),
    ("sweet_potato", "cooked"):("sweet_potato",      "cooked.baked",         "Patate douce cuite","baked sweet potato","cooked"),
}


# ══════════════════════════════════════════════════════════════════════════════
# §6 — DISPOSITION DES VARIANTS "default" SUR LES NODES EXISTANTS
#
# Pour chaque node : que faire du variant "default" porteur de données ?
#   "rename:X"  → renommer la clé en X (données conservées)
#   "drop"      → supprimer (données déjà couvertes par un variant nommé)
#   "keep"      → conserver tel quel (cas exceptionnel justifié)
# ══════════════════════════════════════════════════════════════════════════════
NODE_DEFAULT_DISPOSITION: dict[str, str] = {
    # ── nodes où default = données uniques à renommer ─────────────────────────
    "almond":       "rename:whole",      # amande entière (vs slivered/toasted)
    "chestnut":     "rename:raw",        # châtaigne crue (vs cooked)
    "peanut":       "rename:raw",        # cacahuète brute (vs paste)
    "tempeh":       "rename:plain",      # tempeh nature (vs smoked)
    "sesame":       "rename:raw",        # sésame brut (vs tahini)
    "yeast":        "rename:dried",      # levure sèche (vs fresh)
    "cream_animal": "rename:light",      # crème légère (vs heavy)
    "milk_animal":  "rename:semi_skimmed", # lait demi-écrémé (vs whole)
    "flour":        "rename:all_purpose", # farine de blé standard (vs spelt/rye/etc.)
    "hard_boiled_egg": "rename:hard_boiled",  # œuf dur (le raw est le variant brut)
    "pepper":       "rename:ground",     # poivre moulu — + passer is_standalone=True

    # ── nodes où default est redondant avec un variant nommé → drop ───────────
    "bean":         "drop",    # white/black/red… couvrent tout
    "bell_pepper":  "drop",    # green/red/yellow
    "bread":        "drop",    # baguette/pita/white
    "broth":        "drop",    # vegetable/dashi/miso
    "butter":       "drop",    # peanut/vegan/almond/dairy
    "cabbage":      "drop",    # red/savoy/green
    "chili":        "drop",    # amarillo/green/korean/red + ancho ajouté §2
    "chocolate":    "drop",    # nibs/powder/dark
    "citrus":       "drop",    # lemon/lime/orange
    "cream_plant":  "drop",    # coconut/oat/soy
    "curry_paste":  "drop",    # green/red/yellow
    "fig":          "drop",    # fresh/dried
    "lentil":       "drop",    # black/brown/green/red/split_pea/common
    "milk_plant":   "drop",    # almond/cashew/coconut/oat/rice/soy
    "miso":         "drop",    # red/white
    "mushroom":     "drop",    # shiitake/button/porcini/oyster/chanterelle/wood_ear/morel
    "nut":          "drop",    # brazil/pine + walnut/hazelnut/pecan/macadamia/cashew/pistachio
    "oil":          "drop",    # neutral/olive/coconut/flaxseed…
    "onion":        "drop",    # red/shallot/spring/white/yellow
    "pasta":        "drop",    # noodles/orzo/rice_noodles/soba/udon/ziti/wheat
    "pastry":       "drop",    # wrappers/phyllo/pizza/puff/samosa/shortcrust
    "rice":         "drop",    # arborio/basmati/brown/jasmine/cooked…
    "sauce":        "drop",    # hoisin/soy/teriyaki/peanut… + bechamel/mole §2
    "seaweed":      "drop",    # kombu/nori/wakame/ogonori/irish_moss
    "seeds":        "drop",    # black_sesame/chia/hemp/mustard/poppy/pumpkin/sesame/sunflower
    "squash":       "drop",    # butternut/kabocha/muscat/pumpkin/generic
    "sugar":        "drop",    # cane/coconut/white
    "tofu":         "drop",    # silken/smoked/firm
    "tomato":       "drop",    # cherry/crushed/dried/peeled/paste/sauce/fresh
    "tropical_fruit": "drop",  # cherimoya + dragon_fruit/lychee/passion_fruit §4
    "vinegar":      "drop",    # apple_cider/balsamic/rice/white_wine/white
    "yogurt_animal":"drop",    # plain/greek + fromage_blanc/kashk §2
    "yogurt_plant": "drop",    # coconut/soy

    # ── herbs avec default/dried/fresh → default redondant ───────────────────
    "oregano":      "drop",
    "parsley":      "drop",
    "rosemary":     "drop",
    "sage":         "drop",
    "tarragon":     "drop",
    "thyme":        "drop",
}


# ══════════════════════════════════════════════════════════════════════════════
# §7 — CORRECTIONS ingredient_type sur des variants existants
# Format : (base_id, variant_key) → new_ingredient_type
# ══════════════════════════════════════════════════════════════════════════════
INGREDIENT_TYPE_FIXES: dict[tuple[str,str], str] = {
    # invalides
    ("dried_pea",     "default"):  "raw",        # sera migré vers pea/dried ensuite
    ("vanilla",       "default"):  "raw",
    ("vanilla",       "powder"):   "processed",
    # sémantiquement incorrects
    ("kimchi",        "default"):  "fermented",
    ("sauerkraut",    "default"):  "fermented",
    ("tamari",        "default"):  "fermented",
    ("curry",         "default"):  "processed",
    ("curry_paste",   "default"):  "processed",
    ("icing_sugar",   "default"):  "refined",
    ("smoked_paprika","default"):  "processed",  # sera absorbé dans paprika/smoked
    ("ancho_chili",   "default"):  "dried",      # sera absorbé dans chili/ancho
    ("miso",          "red"):      "fermented",
    ("miso",          "white"):    "fermented",
}


# ══════════════════════════════════════════════════════════════════════════════
# §8 — METADATA CORRECTIONS
# ══════════════════════════════════════════════════════════════════════════════
META_FIXES: dict[str, dict] = {
    "pepper":         {"is_standalone": True},    # 1 seul variant → leaf
    "tropical_fruit": {"category": "fruit"},      # était "other"
    "sesame":         {"category": "fat"},         # était "other"
}


# ══════════════════════════════════════════════════════════════════════════════
# §9 — RENOMMAGE de variants existants dans des nodes
# Format : (base_id, old_variant_key) → new_variant_key
# ══════════════════════════════════════════════════════════════════════════════
VARIANT_RENAMES: dict[tuple[str,str], str] = {
    ("sesame", "tahini_raw"): "tahini",  # fusion avec leaf tahini absorbée
}


# ══════════════════════════════════════════════════════════════════════════════
# §10 — CORRECTIONS QUALITÉ (ex patch_quality_v1.py)
#
# Données ponctuelles sourcées — modifier ici si une source est mise à jour.
# Références : cross_source_corrected_v4.json + resume_calculs_sources_matching.md
# ══════════════════════════════════════════════════════════════════════════════

# Q3 — Incohérences sugar > carbs
# Format : (ing_key, var_key) → {field: corrected_value, ...}
# Condition de déclenchement : sugar > carbs (guard dans _apply_quality_fixes)
Q3_SUGAR_CARBS_FIXES: dict[tuple[str,str], dict] = {
    # sugar[cane] : carbs arrondi défavorable — saccharose pur = 99.8g/100g
    # Source : CIQUAL #31021
    ("sugar",  "cane"):    {"carbs_g": 99.8},
    # fennel[default] : valeurs brutes importées incorrectes
    # Source : CIQUAL #20016 Fenouil cru (carbs_dispo=3.65, sugar=3.4)
    ("fennel", "default"): {"sugar_g": 3.4, "carbs_g": 3.65},
}

# Q5 — Données suspectes identifiées par cross_source_corrected_v4.json
# Appliquées inconditionnellement (valeurs plus fiables que l'état actuel)
Q5_CROSS_SOURCE_FIXES: dict[tuple[str,str], dict] = {
    # fig[fresh] : protein CNF=0.75 sous-estimé — USDA FDC #169910 = 1.3g
    ("fig",   "fresh"):   {
        "protein_g": 1.3,
        # Sources absentes sur cette entrée — ajoutées ici
        "_sources_add": [
            {"name": "USDA FDC", "version": "2023",
             "url": "https://fdc.nal.usda.gov", "confidence": 0.85},
            {"name": "CNF",      "version": "2015",
             "url": "https://food-nutrition.canada.ca", "confidence": 0.75},
        ],
    },
    # fig[dried] : USDA FDC #168191 = 3.6g
    ("fig",   "dried"):   {
        "protein_g": 3.6,
        "_sources_add": [
            {"name": "USDA FDC", "version": "2023",
             "url": "https://fdc.nal.usda.gov", "confidence": 0.85},
            {"name": "CNF",      "version": "2015",
             "url": "https://food-nutrition.canada.ca", "confidence": 0.75},
        ],
    },
    # onion[shallot] : sugar divergent CIQUAL=7.87 vs CNF=3.3 (SUSPECT 58%)
    # Moyenne pondérée CIQUAL×0.6 + CNF×0.4 = 6.0g
    # Note : écart probable entre variétés (échalote grise vs rose)
    ("onion", "shallot"): {"sugar_g": 6.0},
}


# ══════════════════════════════════════════════════════════════════════════════
# MOTEUR D'APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

def _carbs_schema_from_ratio(carbs: float, fiber: float) -> str:
    """
    Détermine carbs_schema selon la règle CIQUAL documentée dans
    resume_calculs_sources_matching.md §1 :
      fiber / (carbs + fiber) > 0.40 → "available" (glucides sans fibres, CIQUAL)
      sinon                           → "total"     (fibres incluses, USDA/CNF)
    """
    ratio = fiber / (carbs + fiber) if (carbs + fiber) > 0 else 0
    return "available" if ratio > 0.40 else "total"


def _get_onto_nutrients(onto_ings: dict, onto_key: str, state: str) -> dict | None:
    """Extrait le dict nutrients d'une entrée ontologie."""
    entry = onto_ings.get(onto_key, {})
    v = entry.get(state)
    if isinstance(v, dict) and "nutrients" in v:
        return v["nutrients"]
    return None


def _build_variant_from_onto(
    onto_ings: dict,
    onto_key: str,
    state: str,
    name_fr: str,
    name_en: str,
    ing_type: str,
) -> dict | None:
    """
    Construit un variant nutrition_v2 depuis les données ontologie.
    Inclut carbs_schema (Q1) et energy_kj (Q2) dès la construction
    pour éviter d'avoir à les patcher a posteriori.
    """
    n = _get_onto_nutrients(onto_ings, onto_key, state)
    if not n:
        return None

    CIQUAL_SRC = {"name": "CIQUAL/USDA", "version": "2020-2023",
                  "url": "https://ciqual.anses.fr", "confidence": 0.90}

    kcal  = round(float(n.get("calories_kcal", 0) or 0), 2)
    carbs = round(float(n.get("carbs_g",       0) or 0), 3)
    fiber = round(float(n.get("fiber_g",        0) or 0), 3)

    return {
        "name_fr":                 name_fr,
        "name_en":                 name_en,
        "source_key":              onto_key,
        "ingredient_type":         ing_type,
        # ── énergie ──────────────────────────────────────────────────────────
        "calories_kcal":           kcal,
        "energy_kj":               round(kcal * 4.184, 1),   # Q2 — inline
        # ── macros ───────────────────────────────────────────────────────────
        "protein_g":               round(float(n.get("protein_g",   0) or 0), 3),
        "carbs_g":                 carbs,
        "fat_g":                   round(float(n.get("fat_g",        0) or 0), 3),
        "fiber_g":                 fiber,
        "sugar_g":                 round(float(n.get("sugar_g",      0) or 0), 3),
        "starch_g":                round(float(n.get("starch_g",     0) or 0), 3),
        "carbs_schema":            _carbs_schema_from_ratio(carbs, fiber),  # Q1 — inline
        "added_sugar":             0,
        "alcohol_g":               0.0,
        # ── lipides ──────────────────────────────────────────────────────────
        "saturated_fat_g":         round(float(n.get("saturated_fat_g",       0) or 0), 3),
        "monounsaturated_fat_g":   round(float(n.get("monounsaturated_fat_g", 0) or 0), 3),
        "polyunsaturated_fat_g":   round(float(n.get("polyunsaturated_fat_g", 0) or 0), 3),
        "omega3_g":                round(float(n.get("omega3_g",  0) or 0), 4),
        "omega6_g":                round(float(n.get("omega6_g",  0) or 0), 4),
        "cholesterol_mg":          round(float(n.get("cholesterol_mg", 0) or 0), 1),
        # ── minéraux ─────────────────────────────────────────────────────────
        "sodium_mg":               round(float(n.get("sodium_mg",     0) or 0), 1),
        "calcium_mg":              round(float(n.get("calcium_mg",    0) or 0), 1),
        "iron_mg":                 round(float(n.get("iron_mg",       0) or 0), 3),
        "magnesium_mg":            round(float(n.get("magnesium_mg",  0) or 0), 1),
        "phosphorus_mg":           round(float(n.get("phosphorus_mg", 0) or 0), 1),
        "potassium_mg":            round(float(n.get("potassium_mg",  0) or 0), 1),
        "zinc_mg":                 round(float(n.get("zinc_mg",       0) or 0), 3),
        "copper_mg":               round(float(n.get("copper_mg",     0) or 0), 4),
        "manganese_mg":            round(float(n.get("manganese_mg",  0) or 0), 4),
        "selenium_ug":             round(float(n.get("selenium_ug",   0) or 0), 2),
        # ── vitamines ────────────────────────────────────────────────────────
        "vitamin_a_ug":            round(float(n.get("vitamin_a_ug",  0) or 0), 2),
        "vitamin_c_mg":            round(float(n.get("vitamin_c_mg",  0) or 0), 2),
        "vitamin_d_ug":            round(float(n.get("vitamin_d_ug",  0) or 0), 3),
        "vitamin_e_mg":            round(float(n.get("vitamin_e_mg",  0) or 0), 3),  # Q4 — 0.0 si absent
        "vitamin_k1_ug":           round(float(n.get("vitamin_k1_ug", 0) or 0), 2),
        "vitamin_b1_mg":           round(float(n.get("vitamin_b1_mg", 0) or 0), 4),
        "vitamin_b2_mg":           round(float(n.get("vitamin_b2_mg", 0) or 0), 4),
        "vitamin_b3_mg":           round(float(n.get("vitamin_b3_mg", 0) or 0), 3),
        "vitamin_b5_mg":           round(float(n.get("vitamin_b5_mg", 0) or 0), 4),
        "vitamin_b6_mg":           round(float(n.get("vitamin_b6_mg", 0) or 0), 4),
        "folate_ug":               round(float(n.get("folate_ug",     0) or 0), 2),
        "vitamin_b12_ug":          0.0,   # Q4 — 0.0 convention (non mesuré végétaux)
        # ── métadonnées ──────────────────────────────────────────────────────
        "nova_group":              1,
        "allergens":               [],
        "confidence":              0.88,
        "sources":                 [CIQUAL_SRC],
        "last_updated":            TODAY,
        "version":                 1,
        "data_quality":            "high",
    }


def _copy_leaf_as_variant(leaf_data: dict, new_ing_type: str | None = None) -> dict:
    """Copie les données d'une leaf pour en faire un variant de node."""
    variants = leaf_data.get("variants", {})
    src = variants.get("default") or next(iter(variants.values()), {})
    v = copy.deepcopy(src)
    if new_ing_type and new_ing_type not in ("default", "MISSING"):
        v["ingredient_type"] = new_ing_type
    return v


def _apply_quality_fixes(ings: dict, stats: dict) -> None:
    """
    §10 — Corrections qualité globales (idempotentes).

    Q1 — carbs_schema résiduel : variants non issus de l'ontologie
         (ceux de l'ontologie le reçoivent inline dans _build_variant_from_onto)
    Q2 — energy_kj résiduel : même périmètre
    Q3 — sugar > carbs : corrections ponctuelles sourcées (Q3_SUGAR_CARBS_FIXES)
    Q4 — vitamines None → 0.0 (convention pipeline)
    Q5 — données suspectes cross-source (Q5_CROSS_SOURCE_FIXES)
    """
    q = {"q1": 0, "q2": 0, "q3": 0, "q4": 0, "q5": 0}

    for ing_key, ing in ings.items():
        for var_key, var in ing.get("variants", {}).items():

            # Q1 — carbs_schema manquant sur variants hors-ontologie
            if "carbs_schema" not in var:
                var["carbs_schema"] = _carbs_schema_from_ratio(
                    var.get("carbs_g") or 0,
                    var.get("fiber_g") or 0,
                )
                q["q1"] += 1

            # Q2 — energy_kj manquant ou nul
            kcal = var.get("calories_kcal") or 0
            if kcal > 0 and not (var.get("energy_kj") or 0):
                var["energy_kj"] = round(kcal * 4.184, 1)
                q["q2"] += 1

            # Q4 — vitamines None → 0.0
            for vit in ("vitamin_e_mg", "vitamin_b12_ug"):
                if var.get(vit) is None:
                    var[vit] = 0.0
                    q["q4"] += 1

    # Q3 — incohérences sugar > carbs (corrections hardcodées + sourcées)
    for (ing_key, var_key), fixes in Q3_SUGAR_CARBS_FIXES.items():
        var = ings.get(ing_key, {}).get("variants", {}).get(var_key, {})
        if var and (var.get("sugar_g") or 0) > (var.get("carbs_g") or 0):
            var.update(fixes)
            q["q3"] += 1

    # Q5 — données suspectes cross-source
    for (ing_key, var_key), fixes in Q5_CROSS_SOURCE_FIXES.items():
        var = ings.get(ing_key, {}).get("variants", {}).get(var_key, {})
        if not var:
            continue
        sources_to_add = fixes.pop("_sources_add", None)
        var.update(fixes)
        if sources_to_add is not None and not var.get("sources"):
            var["sources"] = sources_to_add
        # Remettre la clé pour idempotence (le dict constant ne doit pas être muté)
        if sources_to_add is not None:
            fixes["_sources_add"] = sources_to_add
        q["q5"] += 1

    stats["quality"] = q


def _restructure_nodes(n2_path: Path, onto_path: Path | None = None) -> None:
    """
    Applique toutes les transformations structurelles + qualité sur nutrition_v2.json.
    Idempotent : sans effet si déjà appliqué.
    """
    n2   = json.load(open(n2_path, encoding="utf-8"))
    ings = n2["ingredients"]

    onto_ings: dict = {}
    if onto_path and onto_path.exists():
        onto_ings = json.load(open(onto_path, encoding="utf-8")).get("ingredients", {})
    else:
        print("  ⚠  ontology_v6.json absent — extension ontologie désactivée")

    stats = {
        "purged": [], "moved": [], "nodes_created": [], "nodes_expanded": [],
        "defaults_renamed": [], "defaults_dropped": [],
        "type_fixes": [], "meta_fixes": [], "renames": [],
        "onto_injected": [], "onto_skipped": [],
        "quality": {},
    }

    # ── §1 Purges ─────────────────────────────────────────────────────────────
    for key in PURGE_KEYS:
        if key in ings:
            del ings[key]
            stats["purged"].append(key)

    # ── §7 Corrections ingredient_type (avant déplacements) ──────────────────
    for (base, vk), new_type in INGREDIENT_TYPE_FIXES.items():
        entry = ings.get(base)
        if entry and vk in entry.get("variants", {}):
            old = entry["variants"][vk].get("ingredient_type", "?")
            if old != new_type:
                entry["variants"][vk]["ingredient_type"] = new_type
                stats["type_fixes"].append(f"{base}/{vk}: {old}→{new_type}")

    # ── §8 Metadata fixes ─────────────────────────────────────────────────────
    for base, fixes in META_FIXES.items():
        entry = ings.get(base)
        if entry:
            meta = entry.setdefault("_meta", {})
            for k, v in fixes.items():
                if meta.get(k) != v:
                    meta[k] = v
                    stats["meta_fixes"].append(f"{base}._meta.{k}={v}")

    # ── §2 Déplacements leaf → variant node existant ──────────────────────────
    for leaf_id, (node_id, vk) in LEAF_TO_VARIANT.items():
        leaf = ings.get(leaf_id)
        node = ings.get(node_id)
        if not leaf or not node:
            continue
        node_variants = node.setdefault("variants", {})
        if vk in node_variants:
            if leaf_id in ings:
                del ings[leaf_id]
                stats["moved"].append(f"{leaf_id} → {node_id}/{vk} [existant]")
            continue
        v_data = _copy_leaf_as_variant(leaf)
        node_variants[vk] = v_data
        del ings[leaf_id]
        stats["moved"].append(f"{leaf_id} → {node_id}/{vk}")

    # ── §3 Nouveaux nodes ─────────────────────────────────────────────────────
    for node_id, cfg in NEW_NODES.items():
        for leaf_id in cfg.get("delete_leaves", []):
            if leaf_id in ings:
                del ings[leaf_id]

        for vk_to_remove in cfg.get("remove_from_bean", []):
            bean = ings.get("bean")
            if bean and vk_to_remove in bean.get("variants", {}):
                del bean["variants"][vk_to_remove]

        new_variants: dict = {}
        for vk, leaf_src in cfg.get("absorbs", {}).items():
            if leaf_src is None:
                continue
            src_entry = ings.get(leaf_src)
            if not src_entry:
                continue
            v_data = _copy_leaf_as_variant(src_entry)
            new_variants[vk] = v_data

        if cfg.get("_self_becomes_node"):
            existing = ings.get(node_id)
            if existing and existing.get("_meta", {}).get("is_standalone", True):
                existing["_meta"] = cfg["_meta"]
                existing_variants = existing.get("variants", {})
                if "default" in existing_variants:
                    self_vk = next(
                        (vk for vk, src in cfg["absorbs"].items() if src == node_id),
                        None
                    )
                    if self_vk:
                        existing_variants[self_vk] = existing_variants.pop("default")
                        new_variants[self_vk] = existing_variants[self_vk]
                for vk, vdata in new_variants.items():
                    if vk not in existing_variants:
                        existing_variants[vk] = vdata
                existing["variants"] = existing_variants
                stats["nodes_created"].append(f"{node_id} [self→node]")
            continue

        if node_id not in ings:
            ings[node_id] = {
                "_meta": cfg["_meta"],
                "variants": new_variants,
                "substitution": [],
            }
        else:
            existing = ings[node_id]
            existing["_meta"] = cfg["_meta"]
            existing_variants = existing.setdefault("variants", {})
            for vk, vdata in new_variants.items():
                if vk not in existing_variants:
                    existing_variants[vk] = vdata
            if "default" in existing_variants and node_id == "cheese":
                existing_variants["generic"] = existing_variants.pop("default")

        stats["nodes_created"].append(node_id)

    # ── §4 Expansion de nodes existants ───────────────────────────────────────
    for node_id, absorb_map in EXPAND_NODES.items():
        node = ings.get(node_id)
        if not node:
            continue
        node_variants = node.setdefault("variants", {})
        for vk, leaf_src in absorb_map.items():
            if vk in node_variants:
                continue
            leaf = ings.get(leaf_src) if leaf_src else None
            if leaf:
                vdata = _copy_leaf_as_variant(leaf)
                node_variants[vk] = vdata
        for leaf_id in EXPAND_DELETE_LEAVES.get(node_id, []):
            if leaf_id in ings:
                del ings[leaf_id]
                stats["nodes_expanded"].append(f"{leaf_id}→{node_id}/{leaf_id}")

    # ── §6 Disposition des variants "default" sur nodes ──────────────────────
    for base_id, disposition in NODE_DEFAULT_DISPOSITION.items():
        entry = ings.get(base_id)
        if not entry:
            continue
        variants = entry.get("variants", {})
        if "default" not in variants:
            continue

        if disposition.startswith("rename:"):
            new_key = disposition.split(":", 1)[1]
            if new_key not in variants:
                variants[new_key] = variants.pop("default")
                vdata = variants[new_key]
                if vdata.get("ingredient_type") in ("default", "MISSING", None):
                    vdata["ingredient_type"] = _infer_type_from_key(new_key)
                stats["defaults_renamed"].append(f"{base_id}/default→{new_key}")
            else:
                del variants["default"]
                stats["defaults_dropped"].append(f"{base_id}/default [doublé par {new_key}]")

        elif disposition == "drop":
            del variants["default"]
            stats["defaults_dropped"].append(f"{base_id}/default")

        if base_id == "pepper":
            entry["_meta"]["is_standalone"] = True

    # ── §9 Renommages de variants existants ───────────────────────────────────
    for (base_id, old_vk), new_vk in VARIANT_RENAMES.items():
        entry = ings.get(base_id)
        if not entry:
            continue
        variants = entry.get("variants", {})
        if old_vk in variants and new_vk not in variants:
            variants[new_vk] = variants.pop(old_vk)
            stats["renames"].append(f"{base_id}/{old_vk}→{new_vk}")

    # ── §5 Extension depuis l'ontologie ───────────────────────────────────────
    for (n2_base, vk), (onto_key, onto_state, name_fr, name_en, ing_type) in ONTOLOGY_PROMOTE_MAP.items():
        if not onto_ings:
            break

        if n2_base not in ings:
            ings[n2_base] = {
                "_meta": {"category": "unknown", "name_fr": name_fr,
                           "is_standalone": False},
                "variants": {},
                "substitution": [],
            }

        base_entry = ings[n2_base]
        variants   = base_entry.setdefault("variants", {})

        if base_entry.get("_meta", {}).get("is_standalone", True):
            base_entry["_meta"]["is_standalone"] = False

        if vk in variants:
            stats["onto_skipped"].append(f"{n2_base}/{vk}")
            continue

        vdata = _build_variant_from_onto(onto_ings, onto_key, onto_state,
                                          name_fr, name_en, ing_type)
        if vdata:
            variants[vk] = vdata
            stats["onto_injected"].append(f"{n2_base}/{vk} ← {onto_key}/{onto_state}")
        else:
            stats["onto_skipped"].append(f"{n2_base}/{vk} [no data in onto]")

    # ── §10 Corrections qualité globales ──────────────────────────────────────
    _apply_quality_fixes(ings, stats)

    # ── Écriture ──────────────────────────────────────────────────────────────
    n2["_meta"]["restructured_date"] = TODAY
    n2["_meta"]["restructure_version"] = "2.0"
    with open(n2_path, "w", encoding="utf-8") as fh:
        json.dump(n2, fh, ensure_ascii=False, indent=2)

    # ── Rapport ───────────────────────────────────────────────────────────────
    def _pr(label, items):
        if items:
            print(f"  {label} ({len(items)}) :")
            for x in items:
                print(f"    · {x}")

    q = stats["quality"]
    print(f"\n  ✅ Restructuration terminée — {len(ings)} bases")
    _pr("Purgés", stats["purged"])
    _pr("Déplacés leaf→variant", stats["moved"])
    _pr("Nodes créés/convertis", stats["nodes_created"])
    _pr("Nodes étendus", stats["nodes_expanded"])
    _pr("Defaults renommés", stats["defaults_renamed"])
    _pr("Defaults supprimés (redondants)", stats["defaults_dropped"])
    _pr("ingredient_type corrigés", stats["type_fixes"])
    _pr("Variants injectés depuis ontologie", stats["onto_injected"])
    if stats["onto_skipped"]:
        print(f"  ℹ  Skipped (déjà présents ou sans data) : {len(stats['onto_skipped'])}")
    print(f"  §10 Qualité : carbs_schema={q.get('q1',0)} energy_kj={q.get('q2',0)} "
          f"sugar/carbs={q.get('q3',0)} vitamines={q.get('q4',0)} cross-source={q.get('q5',0)}")


def _infer_type_from_key(key: str) -> str:
    """Infère ingredient_type depuis le nom de variant."""
    table = {
        "raw": "raw", "whole": "raw", "fresh": "raw", "seeds": "raw",
        "cooked": "cooked", "boiled": "cooked", "baked": "cooked",
        "dried": "dried",
        "ground": "processed", "smoked": "processed", "toasted": "processed",
        "slivered": "processed", "paste": "processed", "powder": "processed",
        "pearled": "processed", "all_purpose": "refined",
        "refined": "refined",
        "fermented": "fermented",
        "plain": "raw", "light": "processed", "semi_skimmed": "processed",
        "hard_boiled": "cooked",
        "thai": "raw", "stalk": "raw", "white": "raw", "green": "raw",
        "red": "raw", "golden": "raw", "gala": "raw", "granny_smith": "raw",
        "pink_lady": "raw", "chantecler": "raw", "canada": "raw",
        "generic": "raw",
    }
    return table.get(key, "raw")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRÉE PRINCIPALE (mode autonome)
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    confirm = "--confirm" in sys.argv

    if not NUTRITION_V2.exists():
        print(f"❌  nutrition_v2.json introuvable : {NUTRITION_V2}")
        sys.exit(1)

    onto_path = ONTOLOGY_FILE if ONTOLOGY_FILE.exists() else None
    if not onto_path:
        print(f"⚠   ontology_v6.json introuvable : {ONTOLOGY_FILE}")
        print("    Extension ontologie désactivée.")

    print("══════════════════════════════════════════════════════")
    print(f"  RESTRUCTURE NUTRITION_V2 v2.0  {'[DRY-RUN]' if not confirm else '[EXÉCUTION]'}")
    print("══════════════════════════════════════════════════════")
    print(f"  Source : {NUTRITION_V2.relative_to(BASE_DIR)}")
    if onto_path:
        print(f"  Onto   : {onto_path.relative_to(BASE_DIR)}")

    if not confirm:
        print("\n  Dry-run : analyser les maps §1–§10 ci-dessus.")
        print("  Ajouter --confirm pour appliquer.\n")
        sys.exit(0)

    _restructure_nodes(NUTRITION_V2, onto_path)
    sys.exit(0)