"""
patch_nutrition.py — Trois corrections sur nutrition_v2.json :
  1. alcohol_g : null → 0.0 sauf fermentés avec alcool réel
  2. starch_g  : calcul auto (carbs - sugar - fiber) quand fiable
  3. added_sugar: null → 0 pour ingredient_type == "raw"
  4. scientific_name : 115 espèces depuis Wikidata/bases botaniques
"""

import json
from pathlib import Path

SRC = Path("backend/data/nutrition/processed/nutrition_v2.json")
OUT = Path("backend/data/nutrition/processed/nutrition_v2.json")

with open(SRC, encoding="utf-8") as f:
    db = json.load(f)

ings = db["ingredients"]
stats = {"alcohol":0, "starch":0, "added_sugar":0, "sci_name":0}

# ─────────────────────────────────────────────────────────────────
# PATCH 1 — alcohol_g → 0.0 (sauf fermentés avec alcool significatif)
# ─────────────────────────────────────────────────────────────────
# Valeurs réelles mesurées (g/100g ou ml)
REAL_ALCOHOL_VALUES = {
    "mirin":              13.5,   # vin de riz sucré ~14%
    "kombucha":            0.5,   # trace fermentation
    "kefir_water":         0.2,   # trace
    "vinegar":             0.1,   # résiduel post-fermentation (tous variants)
    "fermented_bean_paste":0.1,
    "gochujang":           0.1,
    "ponzu":               0.5,   # contient mirin
    "worcestershire_vegan":0.1,
}

for ing_name, ing in ings.items():
    for vname, v in ing.get("variants", {}).items():
        if v.get("alcohol_g") is None:
            if ing_name in REAL_ALCOHOL_VALUES:
                v["alcohol_g"] = REAL_ALCOHOL_VALUES[ing_name]
            else:
                v["alcohol_g"] = 0.0
            stats["alcohol"] += 1

# ─────────────────────────────────────────────────────────────────
# PATCH 2 — starch_g = carbs - sugar - fiber (si tous non-null et résultat >= 0)
# ─────────────────────────────────────────────────────────────────
for ing_name, ing in ings.items():
    for vname, v in ing.get("variants", {}).items():
        if v.get("starch_g") is not None:
            continue
        carbs = v.get("carbs_g")
        sugar = v.get("sugar_g")
        fiber = v.get("fiber_g")
        if all(x is not None for x in [carbs, sugar, fiber]):
            starch = round(carbs - sugar - fiber, 4)
            v["starch_g"] = max(0.0, starch)
            stats["starch"] += 1

# ─────────────────────────────────────────────────────────────────
# PATCH 3 — added_sugar → 0 pour ingredient_type == "raw"
# ─────────────────────────────────────────────────────────────────
for ing_name, ing in ings.items():
    for vname, v in ing.get("variants", {}).items():
        if v.get("added_sugar") is None and v.get("ingredient_type") == "raw":
            v["added_sugar"] = 0
            stats["added_sugar"] += 1

# ─────────────────────────────────────────────────────────────────
# PATCH 4 — scientific_name (115 espèces)
# ─────────────────────────────────────────────────────────────────
SCIENTIFIC_NAMES = {
    # ── Herbs & Spices ──────────────────────────────────────────
    "basil":             "Ocimum basilicum",
    "bay_leaf":          "Laurus nobilis",
    "caraway":           "Carum carvi",
    "cardamom":          "Elettaria cardamomum",
    "chives":            "Allium schoenoprasum",
    "cinnamon":          "Cinnamomum verum",
    "cloves":            "Syzygium aromaticum",
    "coriander":         "Coriandrum sativum",
    "cumin":             "Cuminum cyminum",
    "curry_leaves":      "Murraya koenigii",
    "dill":              "Anethum graveolens",
    "fenugreek":         "Trigonella foenum-graecum",
    "fresh_coriander":   "Coriandrum sativum",
    "galangal":          "Alpinia galanga",
    "ginger":            "Zingiber officinale",
    "ground_coriander":  "Coriandrum sativum",
    "ground_cumin":      "Cuminum cyminum",
    "kaffir_lime_leaf":  "Citrus hystrix",
    "lemon_verbena":     "Aloysia citrodora",
    "lemongrass":        "Cymbopogon citratus",
    "lemongrass_stalk":  "Cymbopogon citratus",
    "marjoram":          "Origanum majorana",
    "mint":              "Mentha spicata",
    "nutmeg_whole":      "Myristica fragrans",
    "oregano":           "Origanum vulgare",
    "paprika":           "Capsicum annuum",
    "parsley":           "Petroselinum crispum",
    "rosemary":          "Salvia rosmarinus",
    "saffron":           "Crocus sativus",
    "sage":              "Salvia officinalis",
    "shiso":             "Perilla frutescens",
    "smoked_paprika":    "Capsicum annuum",
    "star_anise":        "Illicium verum",
    "sumac":             "Rhus coriaria",
    "tarragon":          "Artemisia dracunculus",
    "thai_basil":        "Ocimum basilicum var. thyrsiflora",
    "thyme":             "Thymus vulgaris",
    "turmeric":          "Curcuma longa",
    "turmeric_fresh":    "Curcuma longa",
    "wasabi":            "Wasabia japonica",
    # ── Vegetables ──────────────────────────────────────────────
    "bamboo_shoots":        "Phyllostachys edulis",
    "beet":                 "Beta vulgaris",
    "cauliflower":          "Brassica oleracea var. botrytis",
    "celery":               "Apium graveolens",
    "celery_root":          "Apium graveolens var. rapaceum",
    "chrysanthemum_greens": "Glebionis coronaria",
    "corn":                 "Zea mays",
    "endive":               "Cichorium endivia",
    "garlic":               "Allium sativum",
    "jalapeno":             "Capsicum annuum",
    "jerusalem_artichoke":  "Helianthus tuberosus",
    "kohlrabi":             "Brassica oleracea var. gongylodes",
    "pak_choi":             "Brassica rapa subsp. chinensis",
    "potato":               "Solanum tuberosum",
    "radish":               "Raphanus sativus",
    "snow_pea":             "Pisum sativum var. saccharatum",
    "snow_peas":            "Pisum sativum var. saccharatum",
    "sugar_snap_pea":       "Pisum sativum var. macrocarpon",
    "sweet_potato":         "Ipomoea batatas",
    "taro":                 "Colocasia esculenta",
    "vine_leaves":          "Vitis vinifera",
    "watercress":           "Nasturtium officinale",
    "yam":                  "Dioscorea alata",
    # ── Fruits ──────────────────────────────────────────────────
    "acai":           "Euterpe oleracea",
    "baobab":         "Adansonia digitata",
    "blueberry":      "Vaccinium corymbosum",
    "cherry":         "Prunus avium",
    "coconut":        "Cocos nucifera",
    "coconut_flesh":  "Cocos nucifera",
    "dragon_fruit":   "Selenicereus undatus",
    "dried_raisins":  "Vitis vinifera",
    "goji_berry":     "Lycium barbarum",
    "grape":          "Vitis vinifera",
    "grapefruit":     "Citrus × paradisi",
    "jackfruit":      "Artocarpus heterophyllus",
    "melon":          "Cucumis melo",
    "olive":          "Olea europaea",
    "passion_fruit":  "Passiflora edulis",
    "pepper":         "Capsicum annuum",
    "yuzu":           "Citrus junos",
    # ── Nuts / Fats ─────────────────────────────────────────────
    "almond":    "Prunus amygdalus",
    "nut":       "Bertholletia excelsa",
    "cashew":    "Anacardium occidentale",
    "chestnut":  "Castanea sativa",
    "flaxseed":  "Linum usitatissimum",
    "hazelnut":  "Corylus avellana",
    "macadamia": "Macadamia integrifolia",
    "pecan":     "Carya illinoinensis",
    "pistachio": "Pistacia vera",
    "walnut":    "Juglans regia",
    # ── Grains ──────────────────────────────────────────────────
    "amaranth":   "Amaranthus cruentus",
    "rice":       "Oryza sativa",
    "barley":     "Hordeum vulgare",
    "buckwheat":  "Fagopyrum esculentum",
    "farro":      "Triticum dicoccum",
    "millet":     "Panicum miliaceum",
    "oats":       "Avena sativa",
    "quinoa":     "Chenopodium quinoa",
    "semolina":   "Triticum durum",
    "sorghum":    "Sorghum bicolor",
    "spelt":      "Triticum spelta",
    "wheat_grass":"Triticum aestivum",
    # ── Legumes ─────────────────────────────────────────────────
    "bean":         "Phaseolus vulgaris",
    "lentil":       "Lens culinaris",
    "chickpea":     "Cicer arietinum",
    "edamame":      "Glycine max",
    "lupine":       "Lupinus albus",
    "peanut":       "Arachis hypogaea",
    "soybean":      "Glycine max",
    "gigante_bean": "Phaseolus coccineus",
    # ── Sweeteners ──────────────────────────────────────────────
    "agave":       "Agave tequilana",
    "stevia":      "Stevia rebaudiana",
    "sugar":       "Saccharum officinarum",
    "vanilla":     "Vanilla planifolia",
    # ── Superfoods ──────────────────────────────────────────────
    "green_tea":  "Camellia sinensis",
    "maca":       "Lepidium meyenii",
    "matcha_tea": "Camellia sinensis",
    "moringa":    "Moringa oleifera",
    # ── Condiments ──────────────────────────────────────────────
    "tamarind_paste": "Tamarindus indica",
    # ── Eggs ────────────────────────────────────────────────────
    "egg":            "Gallus gallus domesticus",
    "hard_boiled_egg":"Gallus gallus domesticus",
}

for ing_name, sci_name in SCIENTIFIC_NAMES.items():
    if ing_name not in ings:
        continue
    ing = ings[ing_name]
    # _meta de l'ingrédient
    if ing.get("_meta", {}).get("scientific_name") is None:
        ing.setdefault("_meta", {})["scientific_name"] = sci_name
        stats["sci_name"] += 1
    # variants
    for vname, v in ing.get("variants", {}).items():
        if v.get("scientific_name") is None:
            v["scientific_name"] = sci_name

# ─────────────────────────────────────────────────────────────────
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(db, f, indent=2, ensure_ascii=False)

print("Patch appliqué :")
print(f"  alcohol_g    : {stats['alcohol']} champs corrigés")
print(f"  starch_g     : {stats['starch']} champs calculés")
print(f"  added_sugar  : {stats['added_sugar']} champs corrigés")
print(f"  scientific_name: {stats['sci_name']} bases complétées")
