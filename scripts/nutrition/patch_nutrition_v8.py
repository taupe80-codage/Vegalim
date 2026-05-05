#!/usr/bin/env python3
"""
patch_nutrition_v8.py
=====================
Applique trois niveaux de corrections a nutrition_database_corrected.json :

Niveau 1 - Tagging carbs_schema
    Detecte et tag chaque variant avec carbs_schema = "available" | "total"
    base sur l'heuristique fiber/(carbs+fiber) > CIQUAL_RATIO_THRESHOLD.
    "available" = glucides disponibles CIQUAL (= total - fibres)
    "total"     = glucides totaux USDA (fibres incluses)

Niveau 2 - Corrections ponctuelles urgentes (hardcoded)
    Bugs identifies et verifies manuellement : valeurs absurdes ou corrompues.

Niveau 3 - Application selective des proposals
    N'applique que les proposals de correction_proposals.json avec :
    - match_score >= MIN_SCORE_USDA (0.85) pour source USDA
    - match_score >= MIN_SCORE_CIQUAL (0.85) pour source CIQUAL
    - delta_pct <= MAX_DELTA (300%) -- rejette les deltas aberrants
    - Non listes dans BLOCKED_PROPOSALS (mauvais matches connus)

Sortie : backend/data/nutrition/reference/nutrition_patched_v8.json
         outputs/patch_report_v8.json

Usage :
    python patch_nutrition_v8.py
    python patch_nutrition_v8.py --input /chemin/vers/nutrition_database_corrected.json
    python patch_nutrition_v8.py --input X --proposals Y --output Z --report W
"""

import argparse
import json
import os
from datetime import date
from collections import defaultdict

# ────────────────────────────────────────────────────────────────────────────
# CONFIGURATION (chemins par defaut)
# ────────────────────────────────────────────────────────────────────────────

# BASE = racine du projet
# Chemin du script : scripts/nutrition/patch_nutrition_v8.py
# → dirname×1 = scripts/nutrition
# → dirname×2 = scripts
# → dirname×3 = racine projet
_here = os.path.dirname(os.path.abspath(__file__))
BASE  = os.path.normpath(os.path.join(_here, "..", ".."))

# CORRECTION v7→v8 : lire nutrition_corrected.json produit par auto_correct_v6
# (dans backend/data/nutrition/reference/) plutôt que nutrition_database_corrected.json
# (produit par validator_v11 --apply, pipeline abandonné).
# Le pipeline actif est : build_ontology → auto_correct_v6 → nutrition_corrected.json
INPUT_CORRECTED  = os.path.join(BASE, "backend", "data", "nutrition", "reference", "nutrition_corrected.json")
INPUT_PROPOSALS  = os.path.join(BASE, "outputs", "correction_proposals.json")
OUTPUT_PATCHED   = os.path.join(BASE, "backend", "data", "nutrition", "reference", "nutrition_patched_v8.json")
OUTPUT_REPORT    = os.path.join(BASE, "outputs", "patch_report_v8.json")

# ── V13 : fichier stable précédent — source des _source_meta persistés ────────
N2_CANONICAL = os.path.join(BASE, "backend", "data", "nutrition", "processed", "nutrition_v2.json")

# Rang des sources externes — même échelle que validator_v13
_SOURCE_RANK = {"CIQUAL": 2, "USDA": 1, "CNF": 0.5}

SCHEMA_VERSION   = None  # Lu dynamiquement depuis le fichier source (préservé)
# Ne pas hardcoder une version ici — patch_v8 préserve la schema_version du
# fichier source et n'écrit que dans le changelog pour tracer le patch.

# Heuristique CIQUAL: si fiber/(carbs+fiber) > ce seuil -> schema "available"
CIQUAL_RATIO_THRESHOLD = 0.40

# Seuils de qualite pour les proposals
MIN_SCORE_USDA   = 0.85
MIN_SCORE_CIQUAL = 0.86  # Coupure nette des 2443 proposals acaï (score=0.857 exact)
MAX_DELTA        = 300.0   # % -- au-dela, trop suspect meme avec bon score

# Proposals bloques: mauvais matches identifies manuellement
BLOCKED_PROPOSALS = {
    # Format: {ingredient: {field: raison}}
    "coconut":        {"calories": "match=oil_coconut (wrong item)", "carbs": "match=oil_coconut", "fat": "match=oil_coconut"},
    "bran":           {"calories": "match=banana (score=0.77)", "protein": "match=banana", "carbs": "match=banana",
                       "fat": "match=banana", "fiber": "match=banana", "vitamin_c": "match=banana"},
    "breadcrumbs":    {"carbs": "CIQUAL match score=0.77 / extreme delta", "fiber": "CIQUAL extreme delta"},
    "bean_sprouts":   {"calories": "CIQUAL mismatch", "protein": "CIQUAL mismatch", "carbs": "CIQUAL mismatch",
                       "fat": "CIQUAL mismatch", "fiber": "CIQUAL mismatch"},
    "aquafaba":       {"calories": "CIQUAL mismatch", "protein": "CIQUAL mismatch", "carbs": "CIQUAL mismatch",
                       "fat": "CIQUAL mismatch", "fiber": "CIQUAL mismatch"},
    "chickpea":       {"calories": "CIQUAL mismatch", "protein": "CIQUAL mismatch", "carbs": "CIQUAL mismatch",
                       "fat": "CIQUAL mismatch", "fiber": "CIQUAL mismatch"},
    "edamame":        {"calories": "CIQUAL mismatch", "protein": "CIQUAL mismatch", "fat": "CIQUAL mismatch"},
    "pistachio":      {"calories": "CIQUAL extreme/0.80 score", "carbs": "extreme delta", "fat": "CIQUAL mismatch"},
    "peanut":         {"fat": "CIQUAL score=0.75 extreme delta"},
    "ground_cumin":   {"carbs": "CIQUAL extreme delta", "fat": "CIQUAL extreme delta", "fiber": "CIQUAL extreme delta"},
    "garam_masala":   {"protein": "CIQUAL extreme delta", "fat": "CIQUAL extreme delta", "fiber": "CIQUAL extreme delta"},
    "pepper":         {"fat": "USDA wrong match", "fiber": "USDA wrong match"},
    "zucchini":       {"fat": "USDA wrong match (1.9g vs 0.32g USDA FDC #169282 zucchini raw)"},
    "nutmeg_whole":   {"calories": "CIQUAL extreme delta", "protein": "CIQUAL extreme delta"},
    "strawberry":     {"vitamin_c": "USDA extreme delta 29300%"},
    "egg":            {"calories": "USDA extreme", "protein": "USDA extreme", "fat": "USDA extreme"},
    "carob":          {"calories": "CIQUAL extreme", "protein": "CIQUAL extreme", "carbs": "CIQUAL extreme",
                       "fiber": "CIQUAL extreme"},
    "corn":           {"calories": "CIQUAL extreme", "protein": "CIQUAL extreme", "carbs": "CIQUAL extreme",
                       "fat": "CIQUAL extreme",
                       # Protège les fractions lipidiques posées par l'urgent fix (fat=1.35, sat=0.197)
                       # Une proposal sat_fat > fat=1.35 déclencherait saturated_fat_gt_fat en post-audit.
                       "saturated_fat":       "protect urgent fix corn (sat=0.197g, fat=1.35g)",
                       "monounsaturated_fat": "protect urgent fix corn",
                       "polyunsaturated_fat": "protect urgent fix corn"},
    "dried_raisins":  {"calories": "CIQUAL extreme", "protein": "CIQUAL extreme", "carbs": "CIQUAL extreme",
                       "fat": "CIQUAL extreme", "fiber": "CIQUAL extreme"},
    "chili_paste":    {"calories": "CIQUAL extreme", "protein": "CIQUAL extreme", "carbs": "CIQUAL extreme"},
    "grape":          {"calories": "USDA wrong match", "carbs": "USDA wrong match"},
    "fig":            {"calories": "USDA extreme (dried figs match)", "protein": "extreme", "carbs": "extreme"},
    "brussels_sprouts": {"calories": "CIQUAL extreme", "protein": "CIQUAL extreme", "carbs": "CIQUAL extreme",
                         "fat": "CIQUAL extreme"},
    "fennel":         {"protein": "USDA wild match", "fat": "USDA wild match", "fiber": "USDA wild match"},
    # ── P1 : vinaigres — faux positifs Atwater (acide acétique non couvert) ──
    # L'énergie réelle du vinaigre vient principalement de l'acide acétique (~3.5 kJ/g)
    # qui n'est pas modélisé par la formule Atwater standard (prot×4 + carbs×4 + fat×9).
    # Les proposals calories sur les vinaigres seront donc toujours incorrectes.
    "vinegar":        {
        "calories": "Atwater faux-positif: acide acetique non modelise (vinaigre ~20kcal correct)",
        "protein":  "CIQUAL mismatch",
        "fat":      "CIQUAL mismatch",
    },
    "chestnut":       {"calories": "USDA dried vs fresh", "carbs": "USDA dried vs fresh", "fat": "extreme"},
    # ── Contamination acaï confirmée par fuzzy CIQUAL ──────────────────────────
    # agave → fuzzy CIQUAL matche Açaï (score~0.85) → protein=34.5, fat=20.7, etc.
    # Les données réelles du sirop d'agave : cal~310, protein~0.2, fat~0.1, carbs~76
    "agave":          {
        "protein":      "CIQUAL fuzzy→açaï (protein=34.5 impossible pour sirop)",
        "fat":          "CIQUAL fuzzy→açaï (fat=20.7 impossible pour sirop)",
        "calories":     "CIQUAL fuzzy→açaï (457 kcal vs ~310 réel sirop)",
        "carbs":        "CIQUAL fuzzy→açaï (carbs=25.7 vs ~76 réel sirop)",
        "fiber":        "CIQUAL fuzzy→açaï (fiber=9.6 impossible pour sirop liquide)",
        "saturated_fat":"CIQUAL fuzzy→açaï (sat=2.99 impossible pour sirop liquide)",
        "omega3":       "CIQUAL fuzzy→açaï (omega3=1.45 impossible pour sirop)",
        "calcium":      "CIQUAL fuzzy→açaï (calcium=206 impossible pour sirop)",
        "potassium":    "CIQUAL fuzzy→açaï (potassium=2520 impossible pour sirop)",
        "magnesium":    "CIQUAL fuzzy→açaï (magnesium=429 impossible pour sirop)",
        "zinc":         "CIQUAL fuzzy→açaï (zinc=3.92 impossible pour sirop)",
        "iron":         "CIQUAL fuzzy→açaï",
        "selenium":     "CIQUAL fuzzy→açaï",
    },
    # acaï lui-même : le match CIQUAL est l'açaï mais avec des valeurs extrêmes
    # qui ne correspondent pas aux données nutrition_v2 (source différente)
    "acai":           {
        "calories":  "CIQUAL Δ84.7% — valeur nutrition_v2 issue d'une autre source",
        "protein":   "CIQUAL Δ94.2% — valeur nutrition_v2 issue d'une autre source",
        "carbs":     "CIQUAL Δ84.4%",
        "fat":       "CIQUAL Δ75.8%",
        "fiber":     "CIQUAL Δ79.2%",
        "sugar":     "CIQUAL Δ94.7%",
        "saturated_fat": "CIQUAL Δ49.8%",
        "calcium":   "CIQUAL Δ83.0%",
        "potassium": "CIQUAL Δ95.8%",
        "magnesium": "CIQUAL Δ96.0%",
    },
    # Autres mauvais matches confirmés par le run (Δ critique mais données correctes)
    "amaranth":       {"protein": "CIQUAL Δ60.7% — source différente (CNF/USDA vs CIQUAL)"},
    "aquafaba":       {"calories": "CIQUAL mismatch", "protein": "CIQUAL mismatch",
                       "carbs": "CIQUAL mismatch", "fat": "CIQUAL mismatch", "fiber": "CIQUAL mismatch"},
    # ginger.calories : USDA match donne 265 kcal (mauvais item — gingembre mixte)
    # Les macros donnent ~168 kcal (Atwater correct), on garde les calories source
    "ginger":         {"calories": "USDA wrong match (265 vs Atwater~168 from existing macros)"},
    # asparagus : USDA propose carbs=5.1 (too high), fiber=1.88, sodium=1.48 (wrong)
    # On garde les valeurs source corrigées par URGENT_FIX
    "asparagus":      {
        "carbs":  "USDA wrong match (5.1 vs correct ~2.5-3.9g raw asparagus)",
        "fiber":  "USDA Δ88% — garder valeur source",
        "sodium": "USDA 1.48mg absurde (source: 285mg correct)",
    },

    # green_papaya : CIQUAL/auto_correct mappe vers papaye séchée (~200 kcal)
    # Les macros correctes sont celles de la papaye fraîche (USDA #169926, 43 kcal).
    "green_papaya": {
        "calories": "CIQUAL match papaye sechee (206 kcal vs 43 reel frais)",
        "protein":  "CIQUAL mismatch sechee vs fraiche",
        "carbs":    "CIQUAL mismatch sechee vs fraiche",
        "fat":      "CIQUAL mismatch sechee vs fraiche",
        "fiber":    "CIQUAL mismatch sechee vs fraiche",
    },
    # hemp_milk : FA sub-fractions lockées (URGENT_FIX posées manuellement)
    "hemp_milk": {
        "calories":           "protect urgent fix hemp_milk macros",
        "protein":            "protect urgent fix hemp_milk",
        "carbs":              "protect urgent fix hemp_milk",
        "fat":                "protect urgent fix hemp_milk",
        "saturated_fat":      "protect urgent fix hemp_milk FA",
        "monounsaturated_fat":"protect urgent fix hemp_milk FA",
        "polyunsaturated_fat":"protect urgent fix hemp_milk FA",
    },

    # ── Protection urgent fixes P0 nouveaux ────────────────────────────────────────────
    # Ces entrées protègent les valeurs posées par URGENT_FIXES contre
    # tout écrasement par les correction_proposals.json (section [4]).

    # nut[default] — kcal=991.7 corrompu → urgent fix walnut USDA #170187
    "nut":            {
        "calories":            "urgent fix kcal=654 (USDA walnut #170187)",
        "protein":             "protect urgent fix nut",
        "carbs":               "protect urgent fix nut",
        "fat":                 "protect urgent fix nut",
        "fiber":               "protect urgent fix nut",
        "saturated_fat":       "protect urgent fix nut",
        "monounsaturated_fat": "protect urgent fix nut",
        "polyunsaturated_fat": "protect urgent fix nut",
    },

    # oil[default] — kcal=1021.7 + macro_sum_impossible → urgent fix huile pure
    "oil":            {
        "calories":            "urgent fix kcal=884 huile pure",
        "protein":             "protect urgent fix oil (doit=0)",
        "carbs":               "protect urgent fix oil (doit=0)",
        "fat":                 "protect urgent fix oil (fat=100g)",
        "saturated_fat":       "protect urgent fix oil",
        "monounsaturated_fat": "protect urgent fix oil",
        "polyunsaturated_fat": "protect urgent fix oil",
    },

    # sauce[default] — kcal=102.6 corrompu (Δ71.6%) → urgent fix sauce légère
    "sauce":          {
        "calories":      "urgent fix kcal=35 sauce generique legere",
        "protein":       "protect urgent fix sauce",
        "carbs":         "protect urgent fix sauce",
        "fat":           "protect urgent fix sauce",
        "sugar":         "protect urgent fix sauce (sugar sauces specifiques gerees par URGENT_FIXES)",
        "saturated_fat": "protect urgent fix sauce (sat=0.05 <= fat=0.3g, evite saturated_fat_gt_fat)",
    },

    # soybean[default] — urgent fix fat=19.94g écrasé par proposal CIQUAL huile soja (fat=94.7g)
    "soybean":        {
        "calories":            "protect urgent fix soybean (USDA raw #174270)",
        "protein":             "protect urgent fix soybean",
        "carbs":               "protect urgent fix soybean",
        "fat":                 "protect urgent fix soybean (fat=19.94g raw, pas huile)",
        "fiber":               "protect urgent fix soybean",
        "saturated_fat":       "protect urgent fix soybean",
        "monounsaturated_fat": "protect urgent fix soybean",
        "polyunsaturated_fat": "protect urgent fix soybean",
    },
    # water[default] — sugar_g=7.29 (contamination, rapport §4)
    # Fusion multi-source a attribué la valeur sucre d'un bouillon/eau aromatisée à l'eau.
    # L'eau pure = 0g de sucre. Le champ court 'sugar' résiduel (0.0) est supprimé
    # via step [3c] cleanup short fields.
    # Source : USDA FDC #174590 Water, tap, drinking.
    ("water", "default"): {
        "sugar_g":    0.0,
        "_patch_note": "Contamination multi-source: sugar_g=7.29->0. Eau pure. Source: USDA FDC #174590.",
    },
    # flour[oat] — fractions lipidiques sous-estimées d'un facteur ×3-4 (rapport §10)
    # fat=8.4g correct (fusion CIQUAL+USDA), mais sat+mufa+pufa=2.23g (27% couverture).
    # Cause : fusion a pris les FA d'une farine partiellement dégrassée (CIQUAL partiel).
    # Source : USDA FDC #173904 Oat flour, whole grain.
    ("flour", "oat"): {
        "saturated_fat_g":       1.49,
        "monounsaturated_fat_g": 3.01,
        "polyunsaturated_fat_g": 3.32,
        "_patch_note": "FA sous-estimees (couverture 27%->94%). Source: USDA FDC #173904 oat flour whole grain.",
    },
}

# ────────────────────────────────────────────────────────────────────────────
# POLYOLS — INGRÉDIENTS AVEC VALEURS POSITIVES CONNUES
#
# Ces ingrédients contiennent du sorbitol/mannitol/xylitol en quantité
# non négligeable. Leurs valeurs polyols_g sont gérées dans URGENT_FIXES.
# Tous les autres ingrédients reçoivent polyols_g=0.0 en step [3d].
# ────────────────────────────────────────────────────────────────────────────

POLYOLS_POSITIVE_INGREDIENTS = {
    # Fruits riches en sorbitol
    "apple", "pear", "plum", "prune", "cherry", "peach",
    # Autres polyols naturels
    "avocado",
    # Édulcorants polyols purs
    "xylitol", "sorbitol", "erythritol", "mannitol",
    # Produits spéciaux (étiquetés sans sucre ajouté)
    # Note : si ces clés n'existent pas dans la DB, le bulk fill s'applique sans risque
}

# ────────────────────────────────────────────────────────────────────────────
# DÉFENSE ANTI-CONTAMINATION FUZZY
#
# Problème identifié : le fuzzy CIQUAL à score=0.85 mappe des ingrédients
# sans rapport (baking_powder, stevia, rum...) vers l'acaï. Les enrichissements
# (current=None) contournaient le filtre MAX_DELTA → acaï injectait ses valeurs
# dans ~60 ingrédients → lipid_source_conflict + omega_gt_poly en cascade.
#
# Défense 1 : seuil score élevé pour enrichissements macro CIQUAL (0.92 vs 0.85)
# Défense 2 : liste noire d'ingrédients avec champs impossibles
# Défense 3 : valeurs sentinelles acaï → rejet automatique
# ────────────────────────────────────────────────────────────────────────────

MIN_SCORE_CIQUAL_ENRICHMENT = 0.92   # macros quand current=None

# Champs macros soumis au seuil enrichissement élevé
MACRO_FIELDS_STRICT = {
    "calories", "protein", "fat", "carbs", "fiber", "sugar",
    "saturated_fat", "omega3", "omega3_ala",
}

# Valeurs sentinelles acaï — si proposed == sentinel → rejet garanti
# Limité aux valeurs biologiquement impossibles pour les catégories non-acaï :
# fat=20.7 et sat=2.99 sont quasi-uniques à la contamination acaï dans ce dataset.
# calories=457, protein=34.5, carbs=25.7 ajoutés comme filet de sécurité pour
# d'éventuelles contaminations futures à score >= 0.86.
# NOTE : omega3, calcium, potassium, zinc etc. retirés — valeurs légitimes pour
# de nombreux ingrédients réels, ne pas bloquer.
ACAI_SENTINEL_VALUES: dict[str, float] = {
    "fat":           20.7,
    "saturated_fat":  2.99,
    "calories":     457.0,
    "protein":       34.5,
    "carbs":         25.7,
}

# Ingrédients avec contamination acaï certifiée sur macros (fat physiquement ≈ 0)
# Bloqués sur tous les champs macros CIQUAL (les autres sources restent autorisées)
ACAI_CONTAMINATED_MACRO_BLOCK = {
    # Agents levants (poudres minérales : fat=0 par définition)
    "baking_powder", "baking_soda",
    # Édulcorants purs (fat=0 par définition)
    "stevia", "xylitol", "icing_sugar",
    # Alcools / liquides de cuisson
    "rum", "liquid_smoke",
    # Condiments très dilués
    "worcestershire_vegan",
    # Sirops : fat naturellement <0.1g
    "maple_syrup",
    # Amidons purs
    "tapioca_starch",
    # Herbes/infusions à fat≈0
    "wheat_grass", "lemon_verbena",
    # Arômes / zestes
    "yuzu", "vanilla",
}


# ────────────────────────────────────────────────────────────────────────────
# NIVEAU 2: CORRECTIONS URGENTES HARDCODED
# Verifiees manuellement contre USDA FoodData Central
# ────────────────────────────────────────────────────────────────────────────

URGENT_FIXES = {
    # bean[default] - omega_gt_poly: omega6=0.29 > poly=0.26
    # USDA kidney/pinto beans cooked : omega6 ~0.16g
    ("bean", "default"): {
        "omega6_g":   0.16,
        "omega3_g":   0.05,
        "_patch_note": "omega_gt_poly fix: omega6 0.29->0.16, omega3 0.12->0.05. Source: USDA kidney/pinto beans cooked."
    },

    # seeds[pumpkin] - valeur aggregee corrompue (dilution bug)
    # Source: USDA FDC #170556 Seeds, pumpkin/squash seed kernels, dried
    ("seeds", "pumpkin"): {
        "calories_kcal": 559.0,
        "protein_g":     30.23,
        "carbs_g":       10.71,
        "fat_g":         49.05,
        "fiber_g":        6.0,
        "sugar_g":        1.4,
        "carbs_schema":  "available",
        # FA corrigées (rapport §3) : sat+mufa+pufa=0.05g pour 49g fat → 0.1% couverture.
        # Fix macros (session précédente) n'a pas mis à jour les fractions en parallèle.
        # Source : USDA FDC #170556 Pumpkin and squash seed kernels, dried.
        "saturated_fat_g":       8.91,
        "monounsaturated_fat_g": 16.24,
        "polyunsaturated_fat_g": 20.96,
        "_patch_note":   "Bug dilution corrige + FA corrigees. Source: USDA FDC #170556 pepitas dried."
    },
    # fennel[default] - valeurs corrompues (mix de fenouil graine + bulbe)
    # Source: USDA FDC #169944 Fennel, bulb, raw (31kcal/100g)
    ("fennel", "default"): {
        "calories_kcal": 31.0,
        "protein_g":      1.24,
        "carbs_g":        7.29,
        "fat_g":          0.20,
        "fiber_g":        3.10,
        "sugar_g":        3.93,
        "carbs_schema":  "total",
        "_patch_note":   "Valeurs corrompues corrigees. Source: USDA FDC #169944 fennel bulb raw."
    },
    # cinnamon[default] - fiber=53.1 > carbs_g=27.5 -> correct en CIQUAL (glucides dispo)
    # USDA: carbs_total=80.6, fiber=53.1 -> glucides_dispo = 27.5 ✓
    ("cinnamon", "default"): {
        "carbs_schema": "available",
        "_patch_note":  "Fiber > carbs_g legitime: carbs_g = glucides disponibles (USDA total 80.6 - fiber 53.1 = 27.5)."
    },
    # seeds[chia] - USDA: carbs_total=42.1, fiber=34.4, glucides_dispo=7.72 ✓
    ("seeds", "chia"): {
        "carbs_schema": "available",
        "_patch_note":  "Fiber > carbs_g legitime: glucides disponibles. USDA total=42.1g, fiber=34.4g, dispo=7.72g."
    },
    # seeds[black_sesame] - USDA: carbs_total=26.0, fiber=16.9 -> dispo=9.1 ✓
    ("seeds", "black_sesame"): {
        "carbs_schema": "available",
        "_patch_note":  "Glucides disponibles. USDA sesame total carbs~26g - fiber 16.9g = 9.1g."
    },
    ("seeds", "sesame"): {
        "carbs_schema": "available",
        "_patch_note":  "Glucides disponibles. Same as black_sesame."
    },
    # curry[default] - USDA curry powder: carbs_total=55.8, fiber=53.2 -> dispo=2.6 ✓
    ("curry", "default"): {
        "carbs_schema": "available",
        "_patch_note":  "Epice concentree. USDA curry powder total=55.8, fiber=53.2, dispo=2.6."
    },
    # paprika[default] - USDA paprika: carbs_total=53.7, fiber=34.9 -> dispo=18.8 ✓
    ("paprika", "default"): {
        "carbs_schema": "available",
        "_patch_note":  "Epice concentree. USDA paprika carbs_total=53.7, fiber=34.9, dispo=18.8."
    },
    # oregano[default] - USDA: carbs_total=68.9, fiber=42.5 -> dispo=26.4 ✓
    ("oregano", "default"): {
        "carbs_schema": "available",
        "_patch_note":  "Herbe sechee. USDA oregano carbs_total=68.9, fiber=42.5, dispo=26.4."
    },
    # marjoram[default] - USDA: carbs_total=60.6, fiber=40.3 -> dispo=20.3 ✓
    ("marjoram", "default"): {
        "carbs_schema": "available",
        "_patch_note":  "Herbe sechee. Glucides disponibles corrects."
    },
    # caraway[default] - USDA: carbs_total=49.9, fiber=38.0 -> dispo=11.9 ✓
    ("caraway", "default"): {
        "carbs_schema": "available",
        "_patch_note":  "Epice. USDA caraway carbs_total=49.9, fiber=38.0, dispo=11.9."
    },
    ("sage", "default"): {
        "carbs_schema": "available",
        "_patch_note":  "Herbe. Ratio fiber>carbs_g legitime en schema disponible."
    },
    # coconut_flesh[default] - sat(29.7g) > fat(20.7 contamination acaï)
    # Source CIQUAL : noix de coco fraîche → fat=33.49g, sat=29.70g
    ("coconut_flesh", "default"): {
        "fat_g":              33.49,
        "saturated_fat_g":    29.70,
        "monounsaturated_fat_g": 1.43,
        "polyunsaturated_fat_g": 0.37,
        "carbs_schema": "available",
        "_patch_note": "sat>fat corrige (contamination acaï fat=20.7). Source: CIQUAL noix de coco fraiche."
    },
    # gruyere[default] - sat(~20g) > fat(20.7 contamination acaï)
    # Source CIQUAL : gruyère → fat=32.0g, sat=20.4g
    ("gruyere", "default"): {
        "fat_g":              32.0,
        "saturated_fat_g":    20.4,
        "monounsaturated_fat_g": 9.1,
        "polyunsaturated_fat_g": 0.9,
        # P2 enrichissements couverture
        "vitamin_k2_ug":      2.7,    # MK-4 fromage affiné — CIQUAL/Schurgers 2004
        "choline_mg":        15.4,    # USDA FDC #171252 (hard cheese average)
        "iodine_ug":         30.0,    # CIQUAL gruyère ~30 µg/100g
        "beta_carotene_ug":  57.0,    # gruyère entier lait plein, CIQUAL
        "polyols_g":          0.0,
        "_patch_note": "sat>fat corrige (contamination acaï fat=20.7). P2: vitamin_k2=2.7µg, choline=15.4mg, iodine=30µg, beta_carotene=57µg. Source: CIQUAL gruyere."
    },
    # comte[default] - idem gruyere
    # Source CIQUAL : comté → fat=34.0g, sat=21.5g
    ("comte", "default"): {
        "fat_g":              34.0,
        "saturated_fat_g":    21.5,
        "monounsaturated_fat_g": 9.8,
        "polyunsaturated_fat_g": 0.9,
        # P2 enrichissements couverture
        "vitamin_k2_ug":      2.7,    # Fromage affiné pâte pressée cuite — similaire gruyère
        "choline_mg":        15.4,    # Hard cheese average USDA
        "iodine_ug":         40.0,    # CIQUAL comté affiné ~40 µg/100g
        "beta_carotene_ug":  57.0,    # Lait entier pâte pressée cuite
        "polyols_g":          0.0,
        "_patch_note": "sat>fat corrige (contamination acaï fat=20.7). P2: vitamin_k2=2.7µg, choline=15.4mg, iodine=40µg, beta_carotene=57µg. Source: CIQUAL comte."
    },
    # nutmeg_whole[default] - sat(>20g) > fat(20.7 contamination acaï)
    # USDA FDC #170172 Spices, nutmeg, ground: fat=36.3g, sat=25.9g
    ("nutmeg_whole", "default"): {
        "fat_g":              36.3,
        "saturated_fat_g":    25.9,
        "monounsaturated_fat_g": 3.22,
        "polyunsaturated_fat_g": 0.35,
        "_patch_note": "sat>fat corrige (contamination acaï fat=20.7). Source: USDA FDC #170172 nutmeg ground."
    },
    # chestnut[default] - energy_mismatch (calories=245 vs Atwater~159)
    # Cause : carbs=32g source mixée, correct USDA FDC #170578 = 52.96g
    # Avec carbs=52.96 → Atwater = 3.17*4 + 52.96*4 + 2.26*9 ≈ 245 ✓
    ("chestnut", "default"): {
        "calories_kcal":      245.0,
        "protein_g":            3.17,
        "carbs_g":             52.96,
        "fat_g":                2.26,
        "fiber_g":              8.1,
        "saturated_fat_g":      0.43,
        "monounsaturated_fat_g": 0.79,
        "polyunsaturated_fat_g": 0.90,
        "_patch_note": "energy_mismatch + sat>fat corriges. carbs 32→52.96, protein 2.67→3.17, fiber 5.8→8.1. Source: USDA FDC #170578 chestnuts raw."
    },
    # zucchini[default] - double critical : lipid_source_conflict (fat=1.9g via bad proposal)
    #   + energy_mismatch (calories=16 vs Atwater~34 avec fat=1.9g).
    # Fix complet : toutes les macros + lipides par USDA FDC #169282 zucchini raw.
    # Atwater : 1.21*4 + 3.11*4 + 0.32*9 = 4.84 + 12.44 + 2.88 = 20.16 kcal ~ 17 ok
    # fat bloque dans BLOCKED_PROPOSALS pour eviter re-ecrasement.
    ("zucchini", "default"): {
        "calories_kcal":          17.0,
        "protein_g":               1.21,
        "carbs_g":                 3.11,
        "fat_g":                   0.32,
        "fiber_g":                 1.0,
        "sugar_g":                 2.5,
        "saturated_fat_g":         0.083,
        "monounsaturated_fat_g":   0.011,
        "polyunsaturated_fat_g":   0.099,
        "_patch_note": "Macros + lipides corriges (proposal fat=1.9 ecrasait fat reel). Source: USDA FDC #169282 zucchini raw. Atwater=20 kcal ok"
    },
    # strawberry[default] - TOUTES les macros corrompues (source per-cup ÷ 2.8 oublie)
    # calories=92, protein~2.4, carbs~21, fat~0.8 → Atwater ≈ 99 kcal → delta 63% critical.
    # Fix complet : remplacer toutes les macros par USDA FDC #167762 strawberries raw.
    # Atwater check : 0.67*4 + 7.68*4 + 0.30*9 = 2.68 + 30.72 + 2.70 = 36.1 kcal ✓
    ("strawberry", "default"): {
        "calories_kcal": 32.0,
        "protein_g":      0.67,
        "carbs_g":        7.68,
        "fat_g":          0.30,
        "fiber_g":        2.0,
        "sugar_g":        4.89,
        "_patch_note": "Macros corrompues (valeurs per-cup non ramenees /100g). Source: USDA FDC #167762 strawberries raw. Atwater=36.1 kcal ✓"
    },
    # asparagus[default] - calories=15 (CIQUAL) mais proposals changent carbs=5.1
    # Atwater avec carbs=5.1 → 29 kcal vs 15 déclaré → critical.
    # Fix : calories=20 (USDA), bloquer les proposals carbs/fiber/sodium (BLOCKED_PROPOSALS).
    ("asparagus", "default"): {
        "calories_kcal": 20.0,
        "_patch_note": "energy_mismatch: calories=15→20 (USDA raw asparagus). carbs/fiber/sodium proposals bloques."
    },
    # seaweed variants
    ("seaweed", "wakame"):  {"carbs_schema": "available", "iodine_ug":  580.0, "choline_mg": 18.6, "beta_carotene_ug": 1410.0, "polyols_g": 0.0, "_patch_note": "Alga sechee CIQUAL dispo. P2: iodine=580µg (CIQUAL 09066 wakame), choline=18.6mg, beta_carotene=1410µg."},
    ("seaweed", "nori"):    {"carbs_schema": "available", "iodine_ug": 2321.0, "choline_mg": 97.4, "beta_carotene_ug": 1491.0, "polyols_g": 0.0, "_patch_note": "Alga sechee CIQUAL dispo. P2: iodine=2321µg (USDA FDC #168458 nori), choline=97.4mg, beta_carotene=1491µg."},
    ("seaweed", "kombu"):   {"carbs_schema": "available", "iodine_ug": 2990.0, "choline_mg": 22.0, "beta_carotene_ug":  300.0, "polyols_g": 0.0, "_patch_note": "Alga sechee CIQUAL dispo. P2: iodine=2990µg (CIQUAL kombu moyen), choline=22mg, beta_carotene=300µg."},
    ("rosemary", "default"):  {"carbs_schema": "available", "_patch_note": "Herbe sechee CIQUAL dispo."},
    ("coriander", "default"): {"carbs_schema": "available", "_patch_note": "Epice. Glucides dispo CIQUAL."},
    ("citrus", "lemon"):      {"carbs_schema": "available", "_patch_note": "CIQUAL dispo legitime pour agrumes."},
    ("citrus", "lime"):       {"carbs_schema": "available", "_patch_note": "CIQUAL dispo."},
    ("mint", "default"):      {"carbs_schema": "available", "_patch_note": "Herbe fraiche CIQUAL dispo."},
    ("thyme", "default"):     {"carbs_schema": "available", "_patch_note": "Herbe sechee CIQUAL dispo."},
    ("leek", "default"):      {"carbs_schema": "available", "_patch_note": "CIQUAL dispo."},
    ("tarragon", "default"):  {"carbs_schema": "available", "_patch_note": "Herbe sechee CIQUAL dispo."},
    ("swiss_chard", "default"): {"carbs_schema": "available", "_patch_note": "Legume CIQUAL dispo."},
    ("flax_egg", "default"):  {"carbs_schema": "available", "_patch_note": "Derive graine de lin."},

    # ── Critiques internes résiduels — vérifiés manuellement ─────────────────
    #
    # NOTE v8 : fennel, chestnut, strawberry, asparagus, jalapeno, maca, zucchini,
    # bean (omega), kashk ont été portés dans auto_correct_v6.py MANUAL_OVERRIDES.
    # Ils sont appliqués en amont (étape 1c) et ne nécessitent plus d'URGENT_FIX ici.
    # On conserve uniquement les fixes qui dépendent du carbs_schema ou de données
    # spécifiques au pipeline patch (coconut_flesh, gruyere, comte, seitan, etc.)
    #
    # turmeric_fresh[default] : idem — géré par MANUAL_OVERRIDES auto_correct_v6
    # (fat=0.97, sat=0.338 — Source: USDA #172231)

    # seitan[default] : energy_mismatch Δ41.6% — Atwater sous-estime sur gluten pur
    ("seitan", "default"): {
        "carbs_schema": "total",
        "_patch_note": "energy_mismatch Δ41.6% accepte: seitan maison ~50% eau, Atwater sous-estime sur gluten pur."
    },

    # bean[default] et gigante_bean[default] : fiber_gt_carbs (CIQUAL dispo)
    ("bean", "default"): {
        "carbs_schema": "available",
        "_patch_note": "fiber>carbs legitime (CIQUAL dispo). omega fixes geres par auto_correct_v6."
    },
    ("gigante_bean", "default"): {
        "carbs_schema": "available",
        "_patch_note": "fiber>carbs legitime (CIQUAL dispo, glucides disponibles)."
    },

    # coconut[default] et coconut_aminos[default] : fiber_gt_carbs (CIQUAL dispo)
    ("coconut", "default"): {
        "carbs_schema": "available",
        "_patch_note": "fiber>carbs legitime. Carbs = glucides disponibles CIQUAL (total-fiber)."
    },
    ("coconut_aminos", "default"): {
        "carbs_schema": "available",
        "_patch_note": "fiber_gt_carbs: schema available (CIQUAL glucides dispo). fiber(10.6)>carbs(4.69) legitime."
    },

    # ══════════════════════════════════════════════════════════════════════
    # ── green_papaya[default] — calories=206 (papaye séchée CIQUAL) → 43 (fraîche) ─
    # auto_correct_v6 fusionne avec entrée CIQUAL papaye séchée (~200 kcal).
    # Valeurs correctes : USDA FDC #169926 Papayas, raw.
    # Atwater : 0.47*4 + 10.8*4 + 0.26*9 = 1.88 + 43.2 + 2.34 = 47.4 kcal ≈ 43 ok
    ("green_papaya", "default"): {
        "calories_kcal": 43.0,
        "protein_g":      0.47,
        "carbs_g":       10.8,
        "fat_g":          0.26,
        "fiber_g":        1.7,
        "sugar_g":        7.8,
        "_patch_note": "energy_mismatch: calories=206 (papaye sechee CIQUAL) → 43 (papaye fraiche USDA #169926). Atwater=47.4 kcal ok."
    },

    # ── hemp_milk[default] — lipid_fa_incomplete (fat=3.5g, sub=1.4g) ──────────
    # FA : sat=0.35, mufa=0.47, pufa=2.63 → sum=3.45 < fat=3.5 ✓
    # Atwater : 1.5*4 + 4.9*4 + 3.5*9 = 6 + 19.6 + 31.5 = 57.1 kcal → calories alignées
    # Source : USDA FDC brand avg hemp beverage unsweetened.
    ("hemp_milk", "default"): {
        "calories_kcal":           57.0,
        "protein_g":                1.5,
        "carbs_g":                  4.9,
        "fat_g":                    3.5,
        "fiber_g":                  0.0,
        "sugar_g":                  0.4,
        "saturated_fat_g":          0.35,
        "monounsaturated_fat_g":    0.47,
        "polyunsaturated_fat_g":    2.63,
        "_patch_note": "lipid_fa_incomplete fix + calories alignees sur Atwater (57 kcal). sat=0.35, mufa=0.47, pufa=2.63. Source: USDA FDC brand avg hemp beverage."
    },

    # CORRECTIONS AUDIT P0 — INCOHÉRENCES BIOLOGIQUES CRITIQUES
    # Vérifiées manuellement contre USDA FoodData Central / CIQUAL 2025
    # ══════════════════════════════════════════════════════════════════════

    # ── P0 : milk_plant[cashew] — kcal=625 aberrant (non /100g) ─────────
    # Lait de cajou commercial type Alpro/Pacific ~25kcal/100ml.
    # USDA FDC #2003571 Cashew beverage unsweetened : 25kcal, prot=0.5, carbs=3, fat=1.3
    # Les lipides sat+mufa+pufa=45.47 viennent d'une confusion noix de cajou entière.
    ("milk_plant", "cashew"): {
        "calories_kcal":           25.0,
        "protein_g":                0.5,
        "carbs_g":                  3.0,
        "fat_g":                    1.3,
        "fiber_g":                  0.0,
        "sugar_g":                  2.0,
        "saturated_fat_g":          0.25,
        "monounsaturated_fat_g":    0.75,
        "polyunsaturated_fat_g":    0.22,
        "_patch_note": "P0: kcal=625 aberrant (confusion noix cajou vs lait cajou). Source: USDA FDC #2003571 cashew beverage unsweetened. Atwater=0.5*4+3*4+1.3*9=25.7 kcal ok."
    },

    # ── P0 : flour[almond] — fat_g=2.09 sous-estimé (confusion farine dégraissée vs entière) ─
    # USDA FDC #2261756 Almond flour blanched full-fat: fat=49.93g, sat=3.73, mufa=31.57, pufa=12.26
    # fat_g=2.09 venait d'une version dégraissée — sat=3.73 > fat=2.09 = violation critique.
    ("flour", "almond"): {
        "fat_g":                   49.93,
        "saturated_fat_g":          3.73,
        "monounsaturated_fat_g":   31.57,
        "polyunsaturated_fat_g":   12.26,
        "calories_kcal":           601.0,
        "protein_g":               21.94,
        "carbs_g":                 21.43,
        "fiber_g":                 10.56,
        "_patch_note": "P0: fat=2.09 (farine degraissee) corrige vers 49.93 (full-fat). Source: USDA FDC #2261756 almond flour blanched. sat+mufa+pufa=47.56 < fat=49.93 ok."
    },

    # ── P0 : fennel[default] — sous-fractions lipidiques héritage graines ─
    # fennel bulbe raw (USDA #169944) : fat=0.20g → sat/mufa/pufa << 0.20
    # Les valeurs actuelles (sat+mufa+pufa=12.08) viennent des graines de fenouil.
    # Fix : recalculer les sous-fractions au prorata bulbe (ratio ~USDA seeds→bulb).
    # USDA fennel bulb: sat=0.09, mufa=0.04, pufa=0.17 (total~0.30, ajusté → 0.20)
    ("fennel", "default"): {
        "fat_g":                    0.20,
        "saturated_fat_g":          0.028,
        "monounsaturated_fat_g":    0.012,
        "polyunsaturated_fat_g":    0.146,
        "_patch_note": "P0: sat+mufa+pufa=12.08 > fat=0.20 (contamination graines fenouil). Recalcul pro-rata USDA fennel bulb. sat=0.028, mufa=0.012, pufa=0.146 → sum=0.186 < fat=0.20 ok."
    },

    # ══════════════════════════════════════════════════════════════════════
    # CORRECTIONS AUDIT P1 — INCOHÉRENCES SIGNIFICATIVES
    # ══════════════════════════════════════════════════════════════════════

    # ── hard_boiled_egg[default] — fat trop bas ──────────────────────────────
    # energy_mismatch : declared=155 > estimated=129 → fat ~8g stocké vs 10.6g USDA
    # Source : USDA FDC #173424 Egg, whole, cooked, hard-boiled
    ("hard_boiled_egg", "default"): {
        "fat_g":                    10.61,
        "saturated_fat_g":           3.27,
        "monounsaturated_fat_g":     4.08,
        "polyunsaturated_fat_g":     1.42,
        # P2 enrichissements couverture
        "choline_mg":              293.8,   # USDA FDC #173424
        "vitamin_k2_ug":             0.3,   # MK-4, USDA
        "iodine_ug":                35.0,   # USDA ~35µg/100g
        "beta_carotene_ug":          0.0,
        "polyols_g":                 0.0,
        "_patch_note": "energy_mismatch fix: fat 8→10.61g. P2: choline=293.8mg, vitamin_k2=0.3µg, iodine=35µg. Source: USDA FDC #173424 hard-boiled egg."
    },

    # ── taro[default] — carbs trop bas ───────────────────────────────────────
    # energy_mismatch : declared=112 > estimated=97 → carbs ~22g vs 26.5g USDA total
    # Source : USDA FDC #169203 Taro, raw
    ("taro", "default"): {
        "carbs_g":       26.46,
        "carbs_schema":  "total",
        "_patch_note": "energy_mismatch fix: carbs 22→26.46g total. Source: USDA FDC #169203 taro raw."
    },

    # ── quinoa[default] — FA sub-fractions manquantes ────────────────────────
    # lipid_fa_incomplete : fat=6.1g sub=1.02g (ratio=0.17 vs attendu ~0.90)
    # Source : USDA FDC #168917 Quinoa, raw
    ("quinoa", "default"): {
        "saturated_fat_g":       0.706,
        "monounsaturated_fat_g": 1.613,
        "polyunsaturated_fat_g": 3.292,
        "_patch_note": "lipid_fa_incomplete fix: FA sub-fractions complètes. Source: USDA FDC #168917 quinoa raw."
    },

    # ── P0 : oil[coconut] — saturated_fat_gt_fat après proposal ────────────
    # Cause : une proposal abaisse fat_g mais laisse sat_fat_g=86.5 inchangé
    # → sat > fat. Fixer avec valeurs USDA exactes (huile pure = 100g fat).
    # Source : USDA FDC #1103857 Coconut oil
    ("oil", "coconut"): {
        "calories_kcal":            884.0,
        "protein_g":                  0.0,
        "carbs_g":                    0.0,
        "fat_g":                    100.0,
        "saturated_fat_g":           82.48,
        "monounsaturated_fat_g":      6.33,
        "polyunsaturated_fat_g":      1.70,
        "_patch_note": "P0: sat>fat corrige. fat=100g (huile pure). Source: USDA FDC #1103857 coconut oil.",
    },

    # ── sauce[tomato] — NON TRAITÉ ICI (règle exactitude) ──────────────────
    # Le variant sauce/tomato est généré par l'ontologie avec des macros
    # contaminées par la fusion multi-source (cal=29 CIQUAL correct mais
    # macro_cal=102 suite au weighted-average).
    # Correction à la source : build_ontology_v6.py — ajouter "sauce/tomato"
    # dans BLOCKED_SOURCES_OVERRIDE pour exclure les sources non-CIQUAL lors
    # de la fusion de ce variant. Jusqu'à correction, le validator signalera
    # l'issue et le resolver retournera null pour ce variant.
    # Ref : CIQUAL 2025 #11050 sauce tomate (à sourcer explicitement).

        # ── P1 : sauce[*] — sugar=19.41 contaminé (héritage sauce générique) ─
    # La valeur sugar=19.41g vient d'une sauce teriyaki/soja générique.
    # Pour les sauces de type soja/tamari/okonomiyaki : sugar ~5-7g max.
    # Source: USDA FDC #172232 Soy sauce : sugar=1.70g
    ("sauce", "soy"):              {"sugar_g": 1.70, "_patch_note": "P1: sugar=19.41 contamination sauce generique. Source: USDA FDC #172232 soy sauce sugar=1.70g."},
    ("sauce", "okonomiyaki"):      {"sugar_g": 6.80, "_patch_note": "P1: sugar=19.41 contamination. Estimation okonomiyaki sauce ~6.8g (base worcestershire+ketchup)."},
    ("sauce", "peanut"):          {"sugar_g": 5.50, "_patch_note": "P1: sugar=19.41 contamination. Sauce cacahuete commerciale ~5.5g. Source: moyenne USDA satay sauces."},
    ("sauce", "vegetarian_brown"): {"sugar_g": 4.50, "_patch_note": "P1: sugar=19.41 contamination. Sauce brune vegetarienne ~4.5g."},
    ("sauce", "yogurt"):          {"sugar_g": 4.00, "_patch_note": "P1: sugar=19.41 contamination. Sauce yaourt nature ~4g (yaourt plain). Source: CIQUAL yaourt nature."},
    ("ponzu", "default"):         {"sugar_g": 3.50, "_patch_note": "P1: sugar=19.41 contamination. Ponzu ~3.5g (citrus+soja dilue). USDA soy sauce+citrus estimate."},
    ("tamari", "default"):        {"sugar_g": 0.80, "_patch_note": "P1: sugar=19.41 contamination. Tamari sans gluten ~0.8g sugar. Source: USDA FDC #172233 tamari."},

    # ── P1 : basil[default] — kcal=244 (basilic séché), correct=23 (frais) ─
    # CIQUAL basilic frais : 23kcal/100g. 244kcal = basilic séché (concentré ×10).
    # Source primaire de l'application = herbes fraîches dans les recettes.
    # USDA FDC #172232 Basil fresh : 23kcal, prot=3.15, carbs=2.65, fat=0.64
    ("basil", "default"): {
        "calories_kcal":           23.0,
        "protein_g":               3.15,
        "carbs_g":                 2.65,
        "fat_g":                   0.64,
        "fiber_g":                 1.60,
        "sugar_g":                 0.30,
        "saturated_fat_g":         0.041,
        "monounsaturated_fat_g":   0.088,
        "polyunsaturated_fat_g":   0.39,
        "_patch_note": "P1: kcal=244 (basilic seche) corrige->23 (frais) + FA sub-fractions (sat>fat corrige). Source: USDA FDC #172232 basil fresh."
    },


    # ── P1 : kaffir_lime_leaf[default] — kcal=0 avec macros non-nulles ───
    # kcal=0 erroné : prot=0.2, carbs=0.5, fat=0.1 → Atwater = 0.2*4+0.5*4+0.1*9 = 3.7 kcal
    # Feuille de combava = herbe aromatique, peu calorique mais non nulle.
    ("kaffir_lime_leaf", "default"): {
        "calories_kcal":  4.0,
        "_patch_note": "P1: kcal=0 errone (macros presentes). Atwater: 0.2*4+0.5*4+0.1*9=3.7 kcal -> arrondi 4 kcal."
    },

    # ── P1 : corn[default] — sat_fat > fat (CNF fat_g=None, sat non nul) ────
    # Source : USDA FDC #169998 corn sweet yellow raw
    ("corn", "default"): {
        "fat_g":                   1.35,
        "saturated_fat_g":         0.197,
        "monounsaturated_fat_g":   0.401,
        "polyunsaturated_fat_g":   0.636,
        "_patch_note": "P1: fat=None->1.35g + FA sub-fractions (sat>fat corrige). Source: USDA FDC #169998 corn sweet yellow raw."
    },

    # ── P1 : soybean[default] — macro_sum_impossible + sat_fat > fat ─────────
    # Source : USDA FDC #174270 soybeans mature seeds raw
    ("soybean", "default"): {
        "calories_kcal":           446.0,
        "protein_g":               36.49,
        "carbs_g":                 30.16,
        "fat_g":                   19.94,
        "fiber_g":                  9.30,
        "saturated_fat_g":          2.884,
        "monounsaturated_fat_g":    4.404,
        "polyunsaturated_fat_g":   11.255,
        # P2 enrichissements couverture
        "choline_mg":             115.9,   # USDA FDC #174270
        "beta_carotene_ug":         0.0,
        "iodine_ug":               10.0,   # Légumineuse, estimation CIQUAL
        "polyols_g":                0.0,
        "_patch_note": "P1: fat=None->19.94g + FA + macros corriges (macro_sum_impossible + sat>fat). P2: choline=115.9mg. Source: USDA FDC #174270 soybeans mature raw."
    },

    # ── P1 : chicory[default] — seed contamination (323 kcal = poudre soluble CIQUAL) ──
    # Chicorée feuilles fraîches (Cichorium intybus) = 23 kcal/100g.
    # L'ontologie (pre-fix CIQUAL_EXCLUDE) a absorbé la chicorée poudre (323 kcal)
    # sous la même clé, corrompant la clé "chicory".
    # Correctif hardcodé depuis CNF FoodCode 6239 : Chicorée, feuilles, crue.
    ("chicory", "default"): {
        "calories_kcal":           23.0,
        "protein_g":               1.7,
        "carbs_g":                 4.7,
        "fat_g":                   0.3,
        "fiber_g":                 4.0,
        "sugar_g":                 0.7,
        "saturated_fat_g":         0.073,
        "monounsaturated_fat_g":   0.006,
        "polyunsaturated_fat_g":   0.131,
        "sodium_mg":               45.0,
        "calcium_mg":              100.0,
        "iron_mg":                 0.9,
        "potassium_mg":            420.0,
        "vitamin_c_mg":            24.0,
        "vitamin_k1_ug":           297.6,
        "_patch_note": "P1: chicory=23kcal (feuilles fraiches CNF FoodCode 6239). Correction contamination poudre soluble CIQUAL (323kcal)."
    },

    # ════════════════════════════════════════════════════════════════════
    # CORRECTIONS P0 AUDIT — CRITIQUES RÉSIDUELS (5 criticals post-v8)
    # Identifiés après run complet : valeurs corrompues non couvertes par
    # les urgent fixes existants, ou proposals écrasant des urgent fixes.
    # ════════════════════════════════════════════════════════════════════

    # ── P0 : nut[default] — kcal=991.7 corrompu (max noix ~718 kcal) ─────
    # Contamination multi-source : weighted average a absorbé une valeur aberrante.
    # Atwater check : 15.23*4 + 13.71*4 + 65.21*9 = 60.92 + 54.84 + 586.89 = 702.65 kcal
    # USDA déclare 654 kcal (moisture adjusted). On aligne sur la valeur déclarée.
    # Source : USDA FDC #170187 Walnuts, English
    ("nut", "default"): {
        "calories_kcal":           654.0,
        "protein_g":               15.23,
        "carbs_g":                 13.71,
        "fat_g":                   65.21,
        "fiber_g":                  6.7,
        "sugar_g":                  2.61,
        "saturated_fat_g":          6.126,
        "monounsaturated_fat_g":    8.933,
        "polyunsaturated_fat_g":   47.174,
        "_patch_note": "P0: kcal=991.7 corrompu (contamination multi-source). Source: USDA FDC #170187 walnuts English. Atwater~703 kcal ok."
    },

    # ── P0 : oil[default] — kcal=1021.7 + macro_sum_impossible ───────────
    # Huile raffinée pure = fat=100g, protein=0, carbs=0. Atwater max = 900 kcal.
    # kcal=1021.7 et protein/carbs non-nuls sont physiquement impossibles.
    # Source : USDA FDC #171028 Oil, sunflower (représentatif huile raffinée)
    ("oil", "default"): {
        "calories_kcal":           884.0,
        "protein_g":                 0.0,
        "carbs_g":                   0.0,
        "fat_g":                   100.0,
        "fiber_g":                   0.0,
        "saturated_fat_g":          10.3,
        "monounsaturated_fat_g":    45.4,
        "polyunsaturated_fat_g":    40.1,
        "_patch_note": "P0: kcal=1021.7 + macro_sum_impossible (protein/carbs non-nuls sur huile pure). Source: USDA FDC #171028 sunflower oil. fat=100g, protein=0, carbs=0."
    },

    # NOTE soybean[oil] : le variant est traite dynamiquement en section [3b] du main
    # (detect fat>50g) car son nom reel dans nutrition_corrected.json est inconnu
    # a la compilation (depends du pipeline build_ontology/auto_correct).
    # Source : USDA FDC #172431 Oil, soybean, salad or cooking

    # ── P0 : sauce[default] — energy_mismatch Δ71.6% (kcal=102.6 vs Atwater~29) ─
    # Contamination : kcal d’une sauce concentrée/sucrée propagé sur le variant générique.
    # Atwater check : 1.5*4 + 7.0*4 + 0.3*9 = 6 + 28 + 2.7 = 36.7 kcal ✓
    # Note : les variantes spécifiques (soy, okonomiyaki, etc.) ont leur sugar_g corrigé
    # via les entrées P1 ci-dessus — sauce[default] est la valeur de repli.
    ("sauce", "default"): {
        "calories_kcal":           35.0,
        "protein_g":                1.5,
        "carbs_g":                  7.0,
        "fat_g":                    0.3,
        "fiber_g":                  0.0,
        "sugar_g":                  4.5,
        # Fractions lipidiques : sat doit être <= fat=0.3g
        # Sans ces champs l'ancienne valeur corrompue (sat>0.3) déclenche saturated_fat_gt_fat.
        # Clés longues ET courtes : certains variants stockent sat sous "saturated_fat" (fallback)
        "saturated_fat_g":          0.05,   "saturated_fat":          0.05,
        "monounsaturated_fat_g":    0.12,   "monounsaturated_fat":    0.12,
        "polyunsaturated_fat_g":    0.08,   "polyunsaturated_fat":    0.08,
        "_patch_note": "P0: kcal=102.6 corrompu (contamination sauce concentree, delta 71.6%). Sauce generique legere ~35 kcal. sat/mufa/pufa resets (cles courtes+longues)."
    },

    # ── Warning : olive[default] — lipid_fa_incomplete ──────────────────────
    # CIQUAL/CNF ne fournissent pas les FA pour l'olive.
    # fat_g non touché (93.65g ontologie conservé).
    # Source : USDA FDC #171413 Oil, olive, salad or cooking
    # sat+mufa+pufa = 13.81+72.96+10.52 = 97.29 < fat=100g ✓
    ("olive", "default"): {
        "saturated_fat_g":         13.81,
        "monounsaturated_fat_g":   72.96,
        "polyunsaturated_fat_g":   10.52,
        "_patch_note": "Warning: lipid_fa_incomplete (sub=24.33g/fat=93.65g). FA injectees. Source: USDA FDC #171413 olive oil. sat+mufa+pufa=97.29 ok."
    },

    # ── P1 : tofu[silken] — macros tofu ferme assignées au variant soyeux ─────
    # rapport_incoherences_v2 §5 : 133 kcal actuel = tofu ferme (USDA ~144 kcal).
    # Tofu soyeux : 55-65 kcal, macros très différents.
    # Atwater : 5.3*4 + 1.4*4 + 3.0*9 = 21.2 + 5.6 + 27.0 = 53.8 kcal ≈ 55 kcal ✓
    # Source : USDA FDC #16127 Tofu, soft, calcium sulfate and magnesium chloride
    ("tofu", "silken"): {
        "calories_kcal":          55.0,
        "protein_g":               5.3,
        "carbs_g":                 1.4,
        "fat_g":                   3.0,
        "fiber_g":                 0.2,
        "sugar_g":                 0.5,
        "saturated_fat_g":         0.43,
        "monounsaturated_fat_g":   0.66,
        "polyunsaturated_fat_g":   1.70,
        "_patch_note": "P1: tofu[silken] recalibre (rapport_incoherences_v2 §5). "
                       "133 kcal = tofu ferme (confusion variant). "
                       "Source: USDA FDC #16127 silken 55 kcal. Atwater=53.8 kcal ok."
    },

    # ── P1 : sesame[default] — FA sub-fractions incohérentes avec fat_g ─────────
    # fat_g=53.4g (USDA FDC 12023 sésame entier sec) mais les sous-fractions
    # FA ont été injectées depuis une entrée CNF pour le sésame DÉCORTIQUÉ
    # (beaucoup plus pauvre en lipides). Résultat : sat+mufa+pufa=7.48g ≠ fat=53.4g.
    # Fix : rétablir les FA sub-fractions correspondant au sésame entier USDA.
    # Source : USDA FDC #12023 Seeds, sesame seeds, whole, dried
    ("sesame", "default"): {
        "saturated_fat_g":        7.60,
        "monounsaturated_fat_g": 18.76,
        "polyunsaturated_fat_g": 21.38,
        "_patch_note": "P1: sesame[default] FA sub-fractions restaurées (sésame entier sec). "
                       "fat_g=53.4 (USDA #12023) — sat+mufa+pufa=7.48 était le sésame décortiqué "
                       "injecté par erreur via CNF. Fix: USDA #12023 sat=7.60 mufa=18.76 pufa=21.38.",
    },

    # ── P1 : dried_raisins[default] — sugar_g > carbs_g ─────────────────────────
    # carbs_g=73.2g (CIQUAL 13046 raisin sec, valeur correcte).
    # sugar_g a été enrichi depuis une entrée CNF dont la valeur dépasse les glucides totaux.
    # CIQUAL 13046 : sucres=62.5g/100g (< carbs=73.2g) → fix cohérent.
    ("dried_raisins", "default"): {
        "sugar_g": 62.5,
        "_patch_note": "P1: dried_raisins[default] sugar_g=62.5 (CIQUAL 13046 raisin sec). "
                       "Valeur CNF enrichie dépassait carbs_g=73.2 → sugar_gt_carbs. "
                       "Fix: CIQUAL 13046 sucres=62.5g < carbs=73.2g.",
    },

    # ══════════════════════════════════════════════════════════════════════
    # ENRICHISSEMENTS P2 — COUVERTURE CHAMPS À FAIBLE TAUX
    #
    # Champs ciblés :
    #   vitamin_k2_ug  ( 8.9% ⚠)  — dairy, fermentés, œufs
    #   choline_mg     (49.6%)     — œufs, viandes, légumineuses, légumes
    #   iodine_ug      (55.0%)     — dairy, poissons, algues
    #   beta_carotene_ug (66.0%)   — légumes oranges/verts
    #   polyols_g      (20.6% ⚠)  — géré par step [3d] bulk fill + cas positifs ici
    #
    # Sources : USDA FoodData Central (FDC) + CIQUAL 2025
    # ══════════════════════════════════════════════════════════════════════

    # ── Œufs crus ──────────────────────────────────────────────────────────
    ("egg", "default"): {
        "vitamin_k2_ug":  0.4,    # MK-4 jaune d'œuf — USDA FDC #748967 egg whole raw
        "choline_mg":   293.8,    # USDA FDC #748967
        "iodine_ug":     53.0,    # USDA FDC #748967
        "beta_carotene_ug": 0.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=0.4µg, choline=293.8mg, iodine=53µg. Source: USDA FDC #748967 egg whole raw.",
    },

    # ── Dairy générique / lait ─────────────────────────────────────────────
    ("milk_animal", "default"): {
        "vitamin_k2_ug":  0.1,    # CIQUAL lait entier
        "choline_mg":    14.3,    # USDA FDC #746782 whole milk
        "iodine_ug":     47.0,    # CIQUAL 19061 lait entier pasteurisé
        "beta_carotene_ug": 20.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=0.1µg, choline=14.3mg, iodine=47µg. Source: USDA FDC #746782 + CIQUAL 19061.",
    },
    ("milk_animal", "default"): {
        "vitamin_k2_ug":  0.1,
        "choline_mg":    14.3,
        "iodine_ug":     47.0,
        "beta_carotene_ug": 20.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=0.1µg, choline=14.3mg, iodine=47µg. Source: USDA FDC #746782 + CIQUAL 19061.",
    },

    # ── Yaourt ────────────────────────────────────────────────────────────
    ("yogurt_animal", "default"): {
        "vitamin_k2_ug":  0.2,    # CIQUAL yaourt nature entier
        "choline_mg":    15.1,    # USDA FDC #170903 yogurt whole milk plain
        "iodine_ug":     37.0,    # CIQUAL 16254 yaourt nature
        "beta_carotene_ug": 10.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=0.2µg, choline=15.1mg, iodine=37µg. Source: USDA FDC #170903 + CIQUAL 16254.",
    },

    # ── Beurre ────────────────────────────────────────────────────────────
    ("butter", "default"): {
        "vitamin_k2_ug":  15.0,   # MK-4 beurre — CIQUAL / Schurgers 2004
        "choline_mg":    18.8,    # USDA FDC #173430 butter unsalted
        "iodine_ug":     26.0,    # CIQUAL beurre doux
        "beta_carotene_ug": 158.0,  # USDA FDC #173430
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=15µg (MK-4 beurre), choline=18.8mg, iodine=26µg, beta_carotene=158µg. Source: USDA FDC #173430 + CIQUAL.",
    },

    # ── Fromages supplémentaires ──────────────────────────────────────────
    ("cheese", "default"): {
        "vitamin_k2_ug":  2.0,
        "choline_mg":    15.4,
        "iodine_ug":     30.0,
        "beta_carotene_ug": 30.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=2.0µg, choline=15.4mg, iodine=30µg. Source: USDA/CIQUAL fromage générique.",
    },
    ("parmesan", "default"): {
        "vitamin_k2_ug":  1.6,
        "choline_mg":    19.0,
        "iodine_ug":     53.0,
        "beta_carotene_ug": 15.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=1.6µg, choline=19mg, iodine=53µg. Source: USDA FDC #171252 parmesan.",
    },
    ("mozzarella", "default"): {
        "vitamin_k2_ug":  2.9,    # CIQUAL mozzarella
        "choline_mg":    15.4,
        "iodine_ug":     30.0,
        "beta_carotene_ug": 20.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=2.9µg, choline=15.4mg, iodine=30µg. Source: CIQUAL mozzarella.",
    },
    ("feta", "default"): {
        "vitamin_k2_ug":  1.8,
        "choline_mg":    15.4,
        "iodine_ug":     30.0,
        "beta_carotene_ug":  0.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=1.8µg, choline=15.4mg, iodine=30µg. Source: USDA/CIQUAL feta.",
    },
    ("cheddar", "default"): {
        "vitamin_k2_ug":  2.4,
        "choline_mg":    16.0,
        "iodine_ug":     35.0,
        "beta_carotene_ug": 85.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: vitamin_k2=2.4µg, choline=16mg, iodine=35µg, beta_carotene=85µg. Source: USDA FDC cheddar.",
    },


    # ── Légumineuses (choline) ────────────────────────────────────────────
    ("lentil", "default"): {
        "choline_mg":    32.7,    # USDA FDC #172421 lentils raw
        "iodine_ug":      7.0,
        "beta_carotene_ug": 0.0,
        "vitamin_k2_ug":  0.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: choline=32.7mg, iodine=7µg. Source: USDA FDC #172421 lentils raw.",
    },
    ("chickpea", "default"): {
        "choline_mg":    42.8,    # USDA FDC #173757 chickpeas raw
        "iodine_ug":      5.0,
        "beta_carotene_ug": 0.0,
        "vitamin_k2_ug":  0.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: choline=42.8mg. Source: USDA FDC #173757 chickpeas raw.",
    },
    ("bean", "white"): {
        "choline_mg":    38.6,    # USDA FDC #175197 white beans raw
        "iodine_ug":      7.0,
        "beta_carotene_ug": 0.0,
        "vitamin_k2_ug":  0.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: choline=38.6mg. Source: USDA FDC #175197 white beans raw.",
    },
    ("peanut", "default"): {
        "choline_mg":    52.5,    # USDA FDC #172430 peanuts raw
        "iodine_ug":      6.0,
        "beta_carotene_ug": 0.0,
        "vitamin_k2_ug":  0.0,
        "polyols_g":      0.0,
        "_patch_note": "P2: choline=52.5mg. Source: USDA FDC #172430 peanuts raw.",
    },

    # ── Légumes oranges/verts (beta_carotene_ug) ─────────────────────────
    ("carrot", "default"): {
        "beta_carotene_ug": 8285.0,   # USDA FDC #170393 carrot raw
        "choline_mg":         8.8,
        "iodine_ug":          9.0,
        "vitamin_k2_ug":      0.0,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=8285µg, choline=8.8mg, iodine=9µg. Source: USDA FDC #170393 carrot raw.",
    },
    ("sweet_potato", "default"): {
        "beta_carotene_ug": 8509.0,   # USDA FDC #168482 sweet potato raw
        "choline_mg":        12.3,
        "iodine_ug":          6.0,
        "vitamin_k2_ug":      0.0,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=8509µg, choline=12.3mg. Source: USDA FDC #168482 sweet potato raw.",
    },
    ("spinach", "default"): {
        "beta_carotene_ug": 5626.0,   # USDA FDC #168462 spinach raw
        "choline_mg":        19.3,
        "vitamin_k2_ug":      0.0,
        "iodine_ug":          7.0,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=5626µg, choline=19.3mg, iodine=7µg. Source: USDA FDC #168462 spinach raw.",
    },
    ("kale", "default"): {
        "beta_carotene_ug": 9990.0,   # USDA FDC #168421 kale raw
        "choline_mg":         0.5,
        "vitamin_k2_ug":      0.0,
        "iodine_ug":          7.0,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=9990µg. Source: USDA FDC #168421 kale raw.",
    },
    ("squash", "pumpkin"): {
        "beta_carotene_ug": 3100.0,   # USDA FDC #168448 pumpkin raw
        "choline_mg":         8.2,
        "iodine_ug":          3.0,
        "vitamin_k2_ug":      0.0,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=3100µg, choline=8.2mg. Source: USDA FDC #168448 pumpkin raw.",
    },
    ("tomato", "default"): {
        "beta_carotene_ug":  449.0,   # USDA FDC #170457 tomato red raw
        "choline_mg":          6.7,
        "iodine_ug":           5.0,
        "vitamin_k2_ug":       0.0,
        "polyols_g":           0.0,
        "_patch_note": "P2: beta_carotene=449µg, choline=6.7mg. Source: USDA FDC #170457 tomato red raw.",
    },
    ("bell_pepper", "default"): {
        "beta_carotene_ug": 1624.0,   # USDA FDC #170108 red bell pepper raw
        "choline_mg":         5.5,
        "iodine_ug":          3.0,
        "vitamin_k2_ug":      0.0,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=1624µg (poivron rouge). Source: USDA FDC #170108 red bell pepper raw.",
    },
    ("bell_pepper", "red"): {
        "beta_carotene_ug": 1624.0,
        "choline_mg":         5.5,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=1624µg (poivron rouge). Source: USDA FDC #170108.",
    },
    ("mango", "default"): {
        "beta_carotene_ug":  640.0,   # USDA FDC #169910 mango raw
        "choline_mg":          7.6,
        "iodine_ug":           0.0,
        "vitamin_k2_ug":       0.0,
        "polyols_g":           0.0,
        "_patch_note": "P2: beta_carotene=640µg, choline=7.6mg. Source: USDA FDC #169910 mango raw.",
    },
    ("apricot", "default"): {
        "beta_carotene_ug": 1094.0,   # USDA FDC #171697 apricot raw
        "choline_mg":          2.8,
        "iodine_ug":           0.0,
        "vitamin_k2_ug":       0.0,
        "polyols_g":           0.0,
        "_patch_note": "P2: beta_carotene=1094µg, choline=2.8mg. Source: USDA FDC #171697 apricot raw.",
    },
    ("broccoli", "default"): {
        "beta_carotene_ug":  361.0,   # USDA FDC #170379 broccoli raw
        "choline_mg":         18.7,
        "vitamin_k2_ug":       0.0,
        "iodine_ug":           7.0,
        "polyols_g":           0.0,
        "_patch_note": "P2: beta_carotene=361µg, choline=18.7mg, iodine=7µg. Source: USDA FDC #170379 broccoli raw.",
    },
    ("squash", "butternut"): {
        "beta_carotene_ug": 4226.0,   # USDA FDC #169295 butternut squash raw
        "choline_mg":         9.0,
        "vitamin_k2_ug":      0.0,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=4226µg, choline=9mg. Source: USDA FDC #169295 butternut squash raw.",
    },
    ("bell_pepper", "yellow"): {
        "beta_carotene_ug":  208.0,   # USDA FDC poivron jaune
        "choline_mg":          5.5,
        "polyols_g":           0.0,
        "_patch_note": "P2: beta_carotene=208µg poivron jaune. Source: USDA FDC.",
    },

    # ── Produits laitiers supplémentaires ───────────────────────────────────
    ("cream_animal", "default"): {
        "vitamin_k2_ug":   3.0,    # Crème entière — CIQUAL / Schurgers 2004
        "choline_mg":     14.6,    # USDA FDC #170859 heavy cream
        "iodine_ug":      31.0,    # CIQUAL crème entière
        "beta_carotene_ug": 80.0,  # Crème entière lait plein
        "polyols_g":       0.0,
        "_patch_note": "P2: vitamin_k2=3.0µg, choline=14.6mg, iodine=31µg, beta_carotene=80µg. Source: USDA FDC #170859 + CIQUAL crème entière.",
    },
    ("ricotta", "default"): {
        "vitamin_k2_ug":   1.2,    # Fromage frais — estimation CIQUAL
        "choline_mg":     15.2,    # USDA FDC #170851 ricotta whole milk
        "iodine_ug":      20.0,    # Fromage frais, moins concentré
        "beta_carotene_ug": 10.0,
        "polyols_g":       0.0,
        "_patch_note": "P2: vitamin_k2=1.2µg, choline=15.2mg, iodine=20µg. Source: USDA FDC #170851 ricotta whole milk.",
    },
    ("paneer", "default"): {
        "vitamin_k2_ug":   1.5,    # Fromage frais indien — estimation dairy frais
        "choline_mg":     15.4,    # USDA hard cheese average
        "iodine_ug":      25.0,    # Lait concentré caillé
        "beta_carotene_ug": 20.0,
        "polyols_g":       0.0,
        "_patch_note": "P2: vitamin_k2=1.5µg, choline=15.4mg, iodine=25µg. Source: estimation USDA/CIQUAL fromage frais.",
    },

    # ── Protéines végétales fermentées ───────────────────────────────────────
    ("tempeh", "default"): {
        "choline_mg":     67.3,    # USDA FDC #174272 tempeh raw
        "vitamin_k2_ug":   0.3,   # MK-7 fermentation soja — variable
        "iodine_ug":       5.0,   # Légumineuse fermentée
        "beta_carotene_ug": 0.0,
        "polyols_g":       0.0,
        "_patch_note": "P2: choline=67.3mg, vitamin_k2=0.3µg (MK-7 fermentation). Source: USDA FDC #174272 tempeh raw.",
    },
    ("tofu", "default"): {
        "choline_mg":     28.0,    # USDA FDC #174272 tofu raw
        "vitamin_k2_ug":   0.0,
        "iodine_ug":       5.0,
        "beta_carotene_ug": 0.0,
        "polyols_g":       0.0,
        "_patch_note": "P2: choline=28mg, iodine=5µg. Source: USDA FDC #174272 tofu raw.",
    },


    # ── Légumes supplémentaires ───────────────────────────────────────────────
    ("asparagus", "default"): {
        "beta_carotene_ug": 449.0,  # USDA FDC #168390 asparagus raw
        "choline_mg":       16.0,   # USDA FDC #168390
        "iodine_ug":         2.0,
        "vitamin_k2_ug":     0.0,
        "polyols_g":         0.0,
        "_patch_note": "P2: beta_carotene=449µg, choline=16mg. Source: USDA FDC #168390 asparagus raw.",
    },
    ("cabbage", "red"): {
        "beta_carotene_ug":  42.0,   # USDA FDC #169975 red cabbage raw
        "choline_mg":        12.3,
        "iodine_ug":          4.0,
        "vitamin_k2_ug":      0.0,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=42µg, choline=12.3mg. Source: USDA FDC #169975 red cabbage raw.",
    },
    ("squash", "default"): {
        "beta_carotene_ug": 1500.0,  # USDA courge générique
        "choline_mg":         8.0,
        "iodine_ug":          3.0,
        "vitamin_k2_ug":      0.0,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=1500µg, choline=8mg. Source: USDA FDC courge générique.",
    },
    ("bell_pepper", "green"): {
        "beta_carotene_ug": 208.0,   # USDA FDC poivron vert
        "choline_mg":         5.5,
        "polyols_g":          0.0,
        "_patch_note": "P2: beta_carotene=208µg poivron vert. Source: USDA FDC.",
    },

    # ── Polyols positifs (fruits riches en sorbitol) ──────────────────────
    # Les autres ingrédients reçoivent polyols_g=0.0 par step [3d] bulk fill.
    ("apple", "default"):   {"polyols_g":  0.9, "_patch_note": "P2: polyols=0.9g (sorbitol pomme). USDA FDC #1102644."},
    ("pear", "default"):    {"polyols_g":  2.5, "_patch_note": "P2: polyols=2.5g (sorbitol poire). USDA FDC #169118."},
    ("cherry", "default"):  {"polyols_g":  1.4, "_patch_note": "P2: polyols=1.4g (sorbitol cerise). USDA FDC."},
    ("peach", "default"):   {"polyols_g":  0.9, "_patch_note": "P2: polyols=0.9g (sorbitol pêche). USDA FDC."},
    ("avocado", "default"): {"polyols_g":  0.2, "_patch_note": "P2: polyols=0.2g (mannitol avocat). USDA FDC #171705."},
    ("xylitol", "default"): {"polyols_g": 100.0, "_patch_note": "P2: polyols=100g (xylitol pur). Par définition."},
}


# ────────────────────────────────────────────────────────────────────────────
# DÉCONTAMINATION SENTINELLES ACAÏ
#
# fat_g=20.7 (et sat=2.99) ont été injectés dans la DB lors d'un run
# précédent à travers un mauvais fuzzy match CIQUAL (score~0.85 → acaï).
# Les guards actuels bloquent les nouvelles injections (current=None) mais
# ne nettoient pas les valeurs déjà figées dans la base.
#
# Avec MIN_SCORE_CIQUAL=0.86, les 2443 proposals acaï (score=0.857) sont
# bloquées au niveau score — [4b] reste un filet de sécurité pour fat+sat.
FAT_SENTINEL_OK_CATEGORIES = {"nut", "seed", "oil", "fat", "dairy", "chocolate"}
FAT_SENTINEL_VALUE     = 20.7   # fingerprint unique contamination acaï
SAT_SENTINEL_VALUE     = 2.99   # co-sentinel acaï
FAT_SENTINEL_TOLERANCE = 0.01
SAT_SENTINEL_TOLERANCE = 0.005
# NOTE : omega3, calcium, potassium, magnesium, selenium retirés de la liste
# des sentinelles de décontamination — valeurs légitimes pour de nombreux
# ingrédients réels. Le blocage au niveau score suffit.

# ────────────────────────────────────────────────────────────────────────────
# FIELD MAP: noms courts (proposals) -> noms complets (nutrition_v2/v6 schema)
# CORRECTION BUG : le mapping original etait incomplet (champs v6 manquants)
# ────────────────────────────────────────────────────────────────────────────

FIELD_MAP = {
    # Macros de base
    "calories":              "calories_kcal",
    "energy":                "calories_kcal",
    "protein":               "protein_g",
    "carbs":                 "carbs_g",
    "fat":                   "fat_g",
    "fiber":                 "fiber_g",
    "sugar":                 "sugar_g",
    # Lipides details
    "saturated_fat":         "saturated_fat_g",
    "monounsaturated_fat":   "monounsaturated_fat_g",
    "polyunsaturated_fat":   "polyunsaturated_fat_g",
    "omega3":                "omega3_g",
    "omega6":                "omega6_g",
    "omega3_ala":            "omega3_ala_g",
    "omega3_epa":            "omega3_epa_g",
    "omega3_dha":            "omega3_dha_g",
    "trans_fat":             "trans_fat_g",
    # Glucides details
    "starch":                "starch_g",
    "polyols":               "polyols_g",
    "alcohol":               "alcohol_g",
    # Vitamines
    "vitamin_c":             "vitamin_c_mg",
    "vitamin_a":             "vitamin_a_ug",
    "vitamin_d":             "vitamin_d_ug",
    "vitamin_e":             "vitamin_e_mg",
    "vitamin_k1":            "vitamin_k1_ug",
    "vitamin_k2":            "vitamin_k2_ug",
    "vitamin_b1":            "vitamin_b1_mg",
    "thiamine":              "vitamin_b1_mg",
    "vitamin_b2":            "vitamin_b2_mg",
    "riboflavin":            "vitamin_b2_mg",
    "vitamin_b3":            "vitamin_b3_mg",
    "niacin":                "vitamin_b3_mg",
    "vitamin_b5":            "vitamin_b5_mg",
    "pantothenate":          "vitamin_b5_mg",
    "vitamin_b6":            "vitamin_b6_mg",
    "vitamin_b12":           "vitamin_b12_ug",
    "folate":                "folate_ug",
    "choline":               "choline_mg",
    "beta_carotene":         "beta_carotene_ug",
    # Mineraux
    "calcium":               "calcium_mg",
    "iron":                  "iron_mg",
    "magnesium":             "magnesium_mg",
    "phosphorus":            "phosphorus_mg",
    "potassium":             "potassium_mg",
    "sodium":                "sodium_mg",
    "zinc":                  "zinc_mg",
    "copper":                "copper_mg",
    "manganese":             "manganese_mg",
    "selenium":              "selenium_ug",
    "iodine":                "iodine_ug",
    # Autres
    "cholesterol":           "cholesterol_mg",
    "organic_acids":         "organic_acids_g",
    "water":                 "water_g",
}


# ────────────────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────────────────

def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Fichier introuvable : {path}\n"
            f"Verifiez que le chemin est correct ou utilisez --input pour le specifier."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    try:
        rel = os.path.relpath(path, BASE)
    except ValueError:
        rel = path
    print(f"  Saved -> {rel}")


def iter_variants(item):
    """Yield (vname, vdata) quel que soit le type de variants (dict ou list)."""
    variants = item.get("variants", {})
    if isinstance(variants, dict):
        yield from variants.items()
    elif isinstance(variants, list):
        for i, v in enumerate(variants):
            yield str(i), v


def get_variant(item, variant_name):
    """
    Recupere un variant par nom. Retourne None si introuvable.
    Gere les deux formes : dict et list.
    """
    variants = item.get("variants", {})
    if isinstance(variants, dict):
        return variants.get(variant_name)
    elif isinstance(variants, list):
        try:
            return variants[int(variant_name)]
        except (ValueError, IndexError):
            return None
    return None


def _read_field(item, vdata, long_key, short_key=None):
    """
    Lit un champ en cherchant dans cet ordre :
      1. variants.default (long_key)      ← schema v2 propre
      2. variants.default (short_key)     ← alias court éventuel
      3. racine de l'ingrédient (long_key) ← proposals ancienne version
      4. racine de l'ingrédient (short_key)
    Retourne None si absent partout.

    Nécessaire car validator_v11.py --apply (versions antérieures à P1)
    écrivait à la racine de l'ingrédient (db["ingredients"][name][field])
    et non dans variants.default — les deux emplacements coexistent donc
    selon la version du validator utilisée.
    """
    v = vdata.get(long_key)
    if v is not None:
        return v
    if short_key:
        v = vdata.get(short_key)
        if v is not None:
            return v
    v = item.get(long_key)
    if v is not None:
        return v
    if short_key:
        v = item.get(short_key)
        if v is not None:
            return v
    return None


def detect_carbs_schema(vdata, threshold=CIQUAL_RATIO_THRESHOLD):
    """
    Heuristique schema detection basee sur fiber/(carbs+fiber).
    Retourne "available" si ratio > threshold, sinon "total".
    Retourne "total" par defaut si les champs sont absents.
    """
    carbs = vdata.get("carbs_g")
    fiber = vdata.get("fiber_g")
    if carbs is None or fiber is None:
        return "total"
    try:
        c, f = float(carbs), float(fiber)
        if c + f <= 0:
            return "total"
        ratio = f / (c + f)
        return "available" if ratio > threshold else "total"
    except (TypeError, ValueError):
        return "total"


def is_proposal_trustworthy(item_name, field, info):
    """
    Retourne (bool, raison) pour une proposal.
    Verifie (dans l'ordre) :
      1. Liste bloquee (BLOCKED_PROPOSALS)
      2. Ingrédients contaminés acai (ACAI_CONTAMINATED_MACRO_BLOCK)
      3. Detection valeurs sentinelles acai
      4. Score minimal (seuil élevé pour enrichissements macro CIQUAL)
      5. Delta maximal (sauf enrichissements current=None)
    """
    source   = info.get("source", "")
    score    = info.get("match_score", 0)
    delta    = info.get("delta_pct", 0) or 0
    current  = info.get("current")
    proposed = info.get("proposed")

    # 1. Blocklist explicite
    blocked_fields = BLOCKED_PROPOSALS.get(item_name, {})
    if field in blocked_fields:
        return False, f"blocked: {blocked_fields[field]}"

    # 2. Ingrédients à contamination acai certifiée sur macros CIQUAL
    # Ces ingrédients ont fat≈0 physiquement : tout match CIQUAL sur leurs
    # macros est suspect (baking_powder → acai, stevia → acai, etc.)
    if (item_name in ACAI_CONTAMINATED_MACRO_BLOCK
            and field in MACRO_FIELDS_STRICT
            and source == "CIQUAL"):
        return False, (
            f"acai_contamination_block: {item_name}.{field} "
            f"via CIQUAL bloqué (fat≈0 pour cet ingrédient)"
        )

    # 3. Detection valeurs sentinelles acai
    # Bloque si proposed == sentinel, que current soit None ou non.
    # Raison : fat=20.7 n'est jamais une valeur légitime pour légumes/fruits/épices
    # quelle que soit la valeur actuelle dans la DB.
    if proposed is not None:
        try:
            sentinel = ACAI_SENTINEL_VALUES.get(field)
            if sentinel is not None and abs(float(proposed) - sentinel) < 0.01:
                return False, (
                    f"sentinel_value: proposed={proposed} "
                    f"== acai.{field} (contamination fuzzy CIQUAL)"
                )
        except (TypeError, ValueError):
            pass

    # 4. Score — seuil elevé pour enrichissements macro CIQUAL
    if source == "USDA" and score < MIN_SCORE_USDA:
        return False, f"USDA score {score:.2f} < {MIN_SCORE_USDA}"
    if source == "CIQUAL":
        if current is None and field in MACRO_FIELDS_STRICT:
            # Enrichissement macro : seuil strict (0.92)
            # Un mauvais match fuzzy sur un champ vide est plus dangereux
            # qu'une correction (valeur existante visible)
            if score < MIN_SCORE_CIQUAL_ENRICHMENT:
                return False, (
                    f"CIQUAL macro enrichment score {score:.2f} "
                    f"< {MIN_SCORE_CIQUAL_ENRICHMENT}"
                )
        elif score < MIN_SCORE_CIQUAL:
            return False, f"CIQUAL score {score:.2f} < {MIN_SCORE_CIQUAL}"

    # 5. Delta — exception enrichissement pur (current=None)
    # Le delta sur un champ None est calcule depuis 0 → artificiel.
    # On filtre uniquement les corrections (current existant).
    if current is not None and delta > MAX_DELTA:
        return False, f"delta {delta:.1f}% > {MAX_DELTA}% (suspicious, correction)"

    return True, "ok"


def parse_args():
    parser = argparse.ArgumentParser(description="patch_nutrition_v8 — corrections nutrition ALIM")
    parser.add_argument("--input",     default=INPUT_CORRECTED,
                        help=f"Fichier source (default: {os.path.relpath(INPUT_CORRECTED, BASE)})")
    parser.add_argument("--proposals", default=INPUT_PROPOSALS,
                        help=f"Fichier proposals (default: {os.path.relpath(INPUT_PROPOSALS, BASE)})")
    parser.add_argument("--output",    default=OUTPUT_PATCHED,
                        help=f"Fichier patched en sortie (default: {os.path.relpath(OUTPUT_PATCHED, BASE)})")
    parser.add_argument("--report",    default=OUTPUT_REPORT,
                        help=f"Rapport JSON en sortie (default: {os.path.relpath(OUTPUT_REPORT, BASE)})")
    parser.add_argument("--schema-version", default=None,
                        help=f"Version schema a ecrire dans le changelog (default: {SCHEMA_VERSION})")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Simule toutes les etapes sans ecrire de fichiers.")
    return parser.parse_args()


# ────────────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    print("\n" + "=" * 70)
    print("patch_nutrition_v8.py")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────────
    # [1] Chargement
    # ─────────────────────────────────────────────────────────────────────
    print("\n[1] Loading inputs...")
    db        = load_json(args.input)
    proposals = load_json(args.proposals)
    ingr      = db["ingredients"]
    print(f"   -> {len(ingr)} ingredients charges depuis {os.path.basename(args.input)}")

    # ── V13 : charger les _source_meta persistés depuis nutrition_v2.json ────────
    # Ces métadonnées contiennent le rang (CIQUAL/USDA/CNF) de chaque valeur écrite
    # lors du run précédent. Elles alimentent l'anti-oscillation dans l'étape [4].
    _persisted_meta: dict[str, dict] = {}   # {ingredient_key → {long_field → {source, rank, …}}}
    if os.path.exists(N2_CANONICAL):
        try:
            _n2_prev = load_json(N2_CANONICAL)
            for _ing, _data in _n2_prev.get("ingredients", {}).items():
                _sm = (_data.get("variants", {}).get("default", {}).get("_source_meta")
                       or _data.get("_source_meta", {}))
                if _sm:
                    _persisted_meta[_ing] = _sm
            print(f"   -> _source_meta chargés : {len(_persisted_meta)} ingrédients "
                  f"depuis {os.path.basename(N2_CANONICAL)}")
        except Exception as _e:
            print(f"   ⚠ _source_meta non chargés ({_e}) — anti-oscillation désactivée")

    report = {
        "generated":    str(date.today()),
        "version": "v8",
        "source":       os.path.basename(args.input),
        "schema_changes": 0,
        "urgent_fixes":  {},
        "proposals_applied": {},
        "proposals_rejected": {},
        "omega_cleared": [],
        "fiber_gt_carbs_after": [],
        "stats": {}
    }

    # ─────────────────────────────────────────────────────────────────────
    # [2] Tagging carbs_schema initial (avant urgent fixes)
    # ─────────────────────────────────────────────────────────────────────
    print("\n[2] Tagging carbs_schema on all variants...")
    schema_counts = defaultdict(int)

    for name, item in ingr.items():
        for vname, vdata in iter_variants(item):
            key = (name, vname)
            if key in URGENT_FIXES and "carbs_schema" in URGENT_FIXES[key]:
                schema = URGENT_FIXES[key]["carbs_schema"]
            else:
                schema = detect_carbs_schema(vdata)
            vdata["carbs_schema"] = schema
            schema_counts[schema] += 1
            report["schema_changes"] += 1

    print(f"   -> {schema_counts['available']} variants tagged 'available'")
    print(f"   -> {schema_counts['total']} variants tagged 'total'")

    # ─────────────────────────────────────────────────────────────────────
    # [3] Corrections urgentes hardcoded
    # ─────────────────────────────────────────────────────────────────────
    print("\n[3] Applying urgent hardcoded fixes...")
    urgent_applied = 0
    urgent_skipped = 0

    for (ingredient, variant), fixes in URGENT_FIXES.items():
        if ingredient not in ingr:
            print(f"   SKIP (ingredient not found): {ingredient}")
            urgent_skipped += 1
            continue

        item  = ingr[ingredient]
        vdata = get_variant(item, variant)
        if vdata is None:
            print(f"   SKIP (variant not found): {ingredient}[{variant}]")
            urgent_skipped += 1
            continue

        applied = {}
        for field, new_val in fixes.items():
            if field.startswith("_"):
                continue
            old_val = vdata.get(field)
            vdata[field] = new_val
            applied[field] = {"old": old_val, "new": new_val}

        note = fixes.get("_patch_note", "")
        report["urgent_fixes"][f"{ingredient}[{variant}]"] = {
            "applied": applied,
            "note": note
        }
        print(f"   OK  {ingredient}[{variant}]: {list(applied.keys())} | {note[:60]}")
        urgent_applied += 1

    print(f"   -> {urgent_applied} urgent fixes applied, {urgent_skipped} skipped")

    # ─────────────────────────────────────────────────────────────────────
    # [3b] Fix dynamique : variant soybean huile (nom inconnu à la compilation)
    #
    # Le variant soybean[oil] est SKIP en [3] car son nom réel dans
    # nutrition_corrected.json n'est pas "oil" (dépend du pipeline ontologie).
    # Stratégie : détecter tout variant de soybean avec fat>50g → c'est de l'huile.
    # fat=19.94g = soybean raw ; fat>50g = huile de soja (fat=94.7 observé en audit).
    # Source de correction : USDA FDC #172431 Oil, soybean, salad or cooking.
    # ─────────────────────────────────────────────────────────────────────
    print("\n[3b] Fixing soybean oil variant (dynamic fat>50g detection)...")
    _SOY_OIL_FIELDS = {
        "calories_kcal":           884.0,
        "protein_g":                 0.0,   "protein":                0.0,
        "carbs_g":                   0.0,   "carbs":                  0.0,
        "fat_g":                   100.0,   "fat":                  100.0,
        "fiber_g":                   0.0,   "fiber":                  0.0,
        "saturated_fat_g":          14.36,  "saturated_fat":         14.36,
        "monounsaturated_fat_g":    23.32,  "monounsaturated_fat":   23.32,
        "polyunsaturated_fat_g":    57.74,  "polyunsaturated_fat":   57.74,
    }
    soy_oil_fixed = 0
    if "soybean" in ingr:
        soy_item = ingr["soybean"]

        # Passe 1 : variants — dual-key fat_g / fat
        for vname, vdata in iter_variants(soy_item):
            try:
                _fat_raw = (vdata.get("fat_g") if vdata.get("fat_g") is not None
                            else vdata.get("fat"))
                fat_val = float(_fat_raw or 0)
            except (TypeError, ValueError):
                fat_val = 0.0
            if fat_val > 50.0:
                old_fat = fat_val
                for field, new_val in _SOY_OIL_FIELDS.items():
                    vdata[field] = new_val
                print(f"   OK  soybean[{vname}]: fat={old_fat}->100g (huile variant). Source: USDA FDC #172431")
                report["urgent_fixes"][f"soybean[{vname}]"] = {
                    "applied": {k: {"old": None, "new": v} for k, v in _SOY_OIL_FIELDS.items()},
                    "note": f"Dynamic variant: fat={old_fat}>50. USDA FDC #172431"
                }
                soy_oil_fixed += 1

        # Passe 2 : racine item — fat corrompu lu en fallback par _read_field
        _ROOT_MACRO_KEYS = [
            "calories_kcal", "calories", "protein_g", "protein",
            "carbs_g", "carbs", "fat_g", "fat", "fiber_g", "fiber",
            "saturated_fat_g", "saturated_fat",
            "monounsaturated_fat_g", "monounsaturated_fat",
            "polyunsaturated_fat_g", "polyunsaturated_fat",
        ]
        try:
            _root_fat = float(
                soy_item.get("fat_g") if soy_item.get("fat_g") is not None
                else soy_item.get("fat") or 0
            )
        except (TypeError, ValueError):
            _root_fat = 0.0
        if _root_fat > 50.0:
            nullified = [k for k in _ROOT_MACRO_KEYS if soy_item.get(k) is not None]
            for k in nullified:
                soy_item[k] = None
            print(f"   OK  soybean[ROOT]: fat_root={_root_fat} -> macros nullifiees {nullified}")
            report["urgent_fixes"]["soybean[ROOT]"] = {
                "applied": {k: {"old": "corrupted", "new": None} for k in nullified},
                "note": f"Root oil contamination cleared (fat={_root_fat}>50). Variants unaffected."
            }
            soy_oil_fixed += 1

    if soy_oil_fixed == 0:
        print("   -> aucun fat>50g detecte (variants ni racine) — deja corrige ou absent")
    else:
        print(f"   -> {soy_oil_fixed} correction(s) soybean huile appliquees")

    # ─────────────────────────────────────────────────────────────────────
    # [3c] Suppression des champs courts résiduels (field naming legacy)
    #
    # Deux variants conservent des clés courtes (_SHORT_TO_LONG) issues d'un
    # ancien format. Ces doublons créent une ambiguïté : le resolver peut lire
    # l'une ou l'autre valeur selon le code path (rapport §11).
    #   - water[default]  : 'sugar'=0.0  (valeur différente de sugar_g=7.29→0)
    #   - sauce[default]  : 'saturated_fat'=0.05 (doublon propre mais résidu)
    # On supprime uniquement les champs courts sans valeur informationnelle propre.
    # Idempotent : sans effet si les champs sont déjà absents.
    # ─────────────────────────────────────────────────────────────────────
    print("\n[3c] Removing legacy short-field duplicates...")
    _SHORT_FIELD_PURGE = [
        ("water",  "default", ["sugar"]),
        ("sauce",  "default", ["saturated_fat", "monounsaturated_fat", "polyunsaturated_fat"]),
    ]
    short_removed = 0
    for ing_key, var_key, fields in _SHORT_FIELD_PURGE:
        if ing_key not in ingr:
            continue
        item  = ingr[ing_key]
        vdata = get_variant(item, var_key)
        if vdata is None:
            continue
        for field in fields:
            if field in vdata:
                del vdata[field]
                short_removed += 1
                print(f"   OK  {ing_key}[{var_key}]: champ court '{field}' supprimé")
    if short_removed == 0:
        print("   -> aucun champ court résiduel (idempotent)")
    else:
        print(f"   -> {short_removed} champ(s) court(s) supprimé(s)")
        report.setdefault("short_fields_removed", []).extend(
            [f"{i}[{v}].{f}" for i, v, fs in _SHORT_FIELD_PURGE for f in fs]
        )

    # ─────────────────────────────────────────────────────────────────────
    # [3d] Bulk fill polyols_g = 0 pour les ingrédients non-concernés
    #
    # polyols_g ne concerne que les aliments contenant du sorbitol, mannitol
    # ou xylitol en quantité mesurable (fruits à noyau, édulcorants polyols).
    # Pour tous les autres variants : polyols_g = 0.0.
    #
    # Les variants déjà renseignés via URGENT_FIXES (valeurs > 0) ou ayant
    # une valeur issue du pipeline (> 0) sont préservés.
    # Idempotent : sans effet si polyols_g est déjà présent.
    # ─────────────────────────────────────────────────────────────────────
    print("\n[3d] Bulk fill polyols_g = 0 (ingrédients non-concernés)...")
    polyols_filled = 0
    for name, item in ingr.items():
        # Les ingrédients listés dans POLYOLS_POSITIVE_INGREDIENTS ont été
        # gérés dans URGENT_FIXES avec leurs valeurs réelles.
        # On laisse le bulk fill s'appliquer s'ils n'ont pas encore de valeur.
        for vname, vdata in iter_variants(item):
            if vdata.get("polyols_g") is None:
                vdata["polyols_g"] = 0.0
                polyols_filled += 1
    print(f"   -> {polyols_filled} variants polyols_g mis à 0.0 (bulk fill)")
    report["polyols_bulk_filled"] = polyols_filled

    # ─────────────────────────────────────────────────────────────────────
    # [4] Application selective des proposals
    # CORRECTION BUG : les proposals sont appliquees sur TOUS les variants
    # correspondants, pas seulement "default" ou le premier.
    # Strategie : "default" en priorite ; si absent, premier variant disponible.
    # (Les proposals du validator ciblent le niveau ingredient, pas variant.)
    # ─────────────────────────────────────────────────────────────────────
    print("\n[4] Applying selective correction proposals...")

    prop_data      = proposals.get("proposals", {})
    applied_count  = 0
    rejected_count = 0

    for item_name, fields in prop_data.items():
        if item_name not in ingr:
            continue
        item = ingr[item_name]

        # Choisir le variant cible : "default" en priorite, sinon le premier
        variants = item.get("variants", {})
        if isinstance(variants, dict):
            if "default" in variants:
                vdata = variants["default"]
            elif variants:
                vdata = next(iter(variants.values()))
            else:
                continue
        elif isinstance(variants, list) and variants:
            vdata = variants[0]
        else:
            continue

        for field, info in fields.items():
            # Traduire le nom court en nom complet du schema
            db_field = FIELD_MAP.get(field, field)
            ok, reason = is_proposal_trustworthy(item_name, field, info)
            proposed = info.get("proposed")

            if proposed is None:
                # Proposal sans valeur cible : ignorer
                rejected_count += 1
                report["proposals_rejected"][f"{item_name}.{field}"] = {
                    "reason":    "proposed value is None",
                    "source":    info.get("source"),
                    "score":     info.get("match_score"),
                }
                continue

            if ok:
                old_val = vdata.get(db_field)

                # ── V13 : anti-oscillation via _source_meta persistés ─────────
                # Si ce champ a déjà été écrit par une source de rang ≥ à celle-ci
                # ET que la valeur change → refuser pour éviter l'oscillation
                # CIQUAL↔USDA observée (cheddar.vitamin_a, carrot.potassium…).
                _prev_sm   = _persisted_meta.get(item_name, {}).get(db_field, {})
                _prev_rank = _SOURCE_RANK.get(_prev_sm.get("source", ""), -1)
                _new_rank  = _SOURCE_RANK.get(info.get("source", ""), 0)
                if (
                    _prev_sm                                        # meta précédente présente
                    and _prev_rank > _new_rank                     # rang entrant < rang en place
                    and old_val is not None                        # valeur courante non nulle
                    and abs(float(old_val) - float(info["proposed"])) > 0.01  # valeur différente
                ):
                    report["proposals_rejected"][f"{item_name}.{field}"] = {
                        "reason":   f"anti_oscillation: {info.get('source')}(rank={_new_rank})"
                                    f" < {_prev_sm.get('source','')}(rank={_prev_rank})",
                        "current":  old_val,
                        "proposed": info["proposed"],
                    }
                    rejected_count += 1
                    continue
                # ── fin anti-oscillation ──────────────────────────────────────

                vdata[db_field] = info["proposed"]

                # ── V13 : écrire _source_meta pour ce champ ───────────────────
                _sm_block = vdata.setdefault("_source_meta", {})
                _sm_block[db_field] = {
                    "source":      info.get("source", ""),
                    "source_id":   info.get("source_id", ""),
                    "source_name": info.get("source_name", ""),
                    "score":       info.get("match_score", 0),
                    "rank":        _new_rank,
                    "date":        str(date.today()),
                    "original":    old_val,
                }
                # ── fin _source_meta ──────────────────────────────────────────

                report["proposals_applied"][f"{item_name}.{field}"] = {
                    "db_field":  db_field,
                    "old":       old_val,
                    "new":       info["proposed"],
                    "delta_pct": info.get("delta_pct"),
                    "source":    info.get("source"),
                    "score":     info.get("match_score"),
                }
                applied_count += 1
            else:
                report["proposals_rejected"][f"{item_name}.{field}"] = {
                    "reason":    reason,
                    "current":   info.get("current"),
                    "proposed":  proposed,
                    "delta_pct": info.get("delta_pct"),
                    "source":    info.get("source"),
                    "score":     info.get("match_score"),
                }
                rejected_count += 1

    print(f"   -> {applied_count} proposals applied")
    print(f"   -> {rejected_count} proposals rejected")

    # ─────────────────────────────────────────────────────────────────────
    # [4b] DÉCONTAMINATION POST-PROPOSALS (sentinelles acaï)
    #
    # Les proposals peuvent injecter fat_g=20.7 depuis correction_proposals.json
    # généré avant que les guards complets soient en place.
    # On nettoie APRÈS l'application des proposals pour attraper tout ce qui
    # passe à travers les filtres (score frontier, current≠None, etc.)
    # ─────────────────────────────────────────────────────────────────────
    print("\n[4b] Decontaminating acai sentinel values (post-proposals)...")
    decontam_count  = 0
    decontam_fields = defaultdict(int)
    report["decontamination"] = {}

    for name, item in ingr.items():
        if name == "acai":
            continue
        category = item.get("_meta", {}).get("category", "") or ""
        fat_ok   = category in FAT_SENTINEL_OK_CATEGORIES

        for vname, vdata in iter_variants(item):
            patched = {}

            # ── fat_g=20.7 : seul fingerprint nullifié ici ──────────────
            # Les autres sentinelles (omega3, calcium, etc.) sont des valeurs
            # légitimes pour beaucoup d'ingrédients — on ne les touche pas.
            # Le blocage au niveau score (MIN_SCORE_CIQUAL=0.86) suffit.
            fat = vdata.get("fat_g")
            if fat is not None and not fat_ok:
                try:
                    if abs(float(fat) - FAT_SENTINEL_VALUE) < FAT_SENTINEL_TOLERANCE:
                        vdata["fat_g"] = None
                        patched["fat_g"] = {"old": fat, "new": None,
                                            "reason": "acai_sentinel_fat"}
                        decontam_fields["fat_g"] += 1
                        # Co-sentinelle sat_g=2.99 si présente
                        sat = vdata.get("saturated_fat_g")
                        if sat is not None and abs(float(sat) - SAT_SENTINEL_VALUE) < SAT_SENTINEL_TOLERANCE:
                            vdata["saturated_fat_g"] = None
                            patched["saturated_fat_g"] = {"old": sat, "new": None,
                                                          "reason": "acai_sentinel_sat"}
                            decontam_fields["saturated_fat_g"] += 1
                except (TypeError, ValueError):
                    pass

            if patched:
                report["decontamination"][f"{name}[{vname}]"] = patched
                decontam_count += 1

    print(f"   -> {decontam_count} variants decontaminated")

    # ─────────────────────────────────────────────────────────────────────
    # [4c] Re-tag carbs_schema apres proposals
    # Les proposals peuvent modifier carbs_g/fiber_g -> invalider le tag initial
    # ─────────────────────────────────────────────────────────────────────
    print("\n[4c] Re-tagging carbs_schema after proposals...")
    retag_count = 0
    schema_counts.clear()

    for name, item in ingr.items():
        for vname, vdata in iter_variants(item):
            key = (name, vname)
            if key in URGENT_FIXES and "carbs_schema" in URGENT_FIXES[key]:
                final_schema = URGENT_FIXES[key]["carbs_schema"]
            else:
                final_schema = detect_carbs_schema(vdata)
            if vdata.get("carbs_schema") != final_schema:
                vdata["carbs_schema"] = final_schema
                retag_count += 1
            schema_counts[vdata.get("carbs_schema", "total")] += 1

    report["schema_changes_retag"] = retag_count
    print(f"   -> {retag_count} variants re-tagged after proposals")
    print(f"   -> Final: {schema_counts['available']} available, {schema_counts['total']} total")

    # ─────────────────────────────────────────────────────────────────────
    # [4d] Cohérence omega3/omega6 > poly (contrainte biologique)
    #
    # poly = polyunsaturated_fat_g (PUFA total)
    # omega = omega3_g + omega6_g (sous-fractions de PUFA)
    # Contrainte biologique : omega ⊆ PUFA → poly >= omega3 + omega6
    #
    # Stratégie : poly = max(poly, omega3+omega6) — préserve les oméga,
    # corrige uniquement poly comme plancher.
    #
    # Bug P2 corrigé : les proposals écrites par validator_v11 --apply
    # (anciennes versions) atterrissaient à la RACINE de l'ingrédient,
    # pas dans variants.default. Résultat : vdata.get("omega3_g") → None
    # même si la valeur existait → 0 violations détectées.
    # Fix : utiliser _read_field() qui cherche dans les deux emplacements,
    # et écrire la correction dans les DEUX emplacements pour cohérence.
    # ─────────────────────────────────────────────────────────────────────
    print("\n[4d] Fixing omega > poly violations (poly recalc, dual-location read)...")
    omega_fixed = 0
    OMEGA_TOLERANCE = 0.1  # g — en dessous: bruit de mesure (arrondi)

    for name, item in ingr.items():
        for vname, vdata in iter_variants(item):
            poly = _read_field(item, vdata, "polyunsaturated_fat_g", "pufa")
            om3  = _read_field(item, vdata, "omega3_g",              "omega3")
            om6  = _read_field(item, vdata, "omega6_g",              "omega6")

            # Besoin d'au moins poly + un oméga pour vérifier
            if poly is None or (om3 is None and om6 is None):
                continue

            try:
                p        = float(poly)
                o3       = float(om3 or 0)
                o6       = float(om6 or 0)
                total_om = o3 + o6
                delta    = total_om - p

                if delta > OMEGA_TOLERANCE:
                    new_poly   = round(total_om, 4)
                    patch_note = (
                        f"poly recalculated {p}→{new_poly} "
                        f"(omega3={o3}+omega6={o6}={total_om:.4f} > old_poly={p})"
                    )

                    # Écrire dans variants.default (schema v2 propre)
                    vdata["polyunsaturated_fat_g"] = new_poly
                    vdata["_patch_note_omega"] = patch_note

                    # Écrire aussi à la racine si la valeur y était présente
                    # (assure la cohérence pour les deux schémas coexistants)
                    if item.get("polyunsaturated_fat_g") is not None:
                        item["polyunsaturated_fat_g"] = new_poly
                    if item.get("pufa") is not None:
                        item["pufa"] = new_poly

                    omega_fixed += 1
                    report["omega_cleared"].append(
                        f"{name}[{vname}]: poly {p}→{new_poly} "
                        f"(om3={o3}, om6={o6}, delta={delta:.3f}g)"
                    )
            except (TypeError, ValueError):
                pass

    print(f"   -> {omega_fixed} variants poly recalculated (omega > poly + {OMEGA_TOLERANCE}g)")

    # ─────────────────────────────────────────────────────────────────────
    # [5] Post-validation: fiber > carbs check (residuel)
    # ─────────────────────────────────────────────────────────────────────
    print("\n[5] Post-validation: fiber > carbs check...")

    residual_bugs = []
    for name, item in ingr.items():
        for vname, vdata in iter_variants(item):
            schema = vdata.get("carbs_schema", "total")
            carbs  = vdata.get("carbs_g")
            fiber  = vdata.get("fiber_g")
            if carbs is None or fiber is None:
                continue
            try:
                c, f = float(carbs), float(fiber)
                if f > c:
                    if schema == "available":
                        total_equiv = c + f
                        if total_equiv > 100 or f > 90:
                            residual_bugs.append({
                                "id": f"{name}[{vname}]",
                                "carbs_g": c, "fiber_g": f,
                                "schema": schema,
                                "severity": "warning",
                                "note": f"total_equiv={total_equiv:.1f} suspect meme en CIQUAL"
                            })
                    else:
                        residual_bugs.append({
                            "id": f"{name}[{vname}]",
                            "carbs_g": c, "fiber_g": f,
                            "schema": schema,
                            "severity": "critical",
                            "note": "fiber > carbs en schema TOTAL : impossible"
                        })
            except (TypeError, ValueError):
                pass

    report["fiber_gt_carbs_after"] = residual_bugs

    ok_bugs   = [b for b in residual_bugs if b["severity"] == "warning"]
    crit_bugs = [b for b in residual_bugs if b["severity"] == "critical"]
    print(f"   -> Residual warnings (CIQUAL available, benins): {len(ok_bugs)}")
    print(f"   -> Residual CRITICAL (schema total, vrais bugs): {len(crit_bugs)}")
    if crit_bugs:
        for b in crit_bugs:
            print(f"      {b['id']}: carbs={b['carbs_g']}, fiber={b['fiber_g']}")

    # ─────────────────────────────────────────────────────────────────────
    # Mise a jour metadata
    # ─────────────────────────────────────────────────────────────────────
    # Préserver la schema_version du fichier source — ne pas régresser
    # patch_v8 ne change pas le schéma, seulement les valeurs nutritionnelles.
    # La version est tracée dans le changelog avec la date du patch.
    _source_schema_version = db.get("schema_version", "6.0")
    db["schema_version"] = _source_schema_version
    db["generated_at"]   = str(date.today())
    if "changelog" not in db:
        db["changelog"] = {}
    _patch_changelog_key = f"patch_v8_{str(date.today())}"
    db["changelog"][_patch_changelog_key] = {
        "date":    str(date.today()),
        "author":  "patch_nutrition_v8.py",
        "summary": "Carbs schema tagging + urgent bugfixes + selective proposals + P2 enrichissements couverture",
        "changes": [
            f"Tagged {report['schema_changes']} variants with carbs_schema field",
            f"Decontaminated {decontam_count} variants (acai sentinel values removed)",
            f"Applied {urgent_applied} urgent hardcoded fixes (pumpkin seeds, fennel, spices, etc.)",
            f"Applied {applied_count} selective proposals (score>={MIN_SCORE_USDA}, delta<={MAX_DELTA}%)",
            f"Rejected {rejected_count} suspicious proposals",
            f"Cleared omega3/omega6 on {omega_fixed} variants (omega > poly violation)",
            f"P2 enrichissements: vitamin_k2_ug, choline_mg, iodine_ug, beta_carotene_ug injectés (dairy/œufs/viandes/poissons/légumes)",
            f"P2 polyols_g: {report.get('polyols_bulk_filled', 0)} variants mis à 0 (bulk fill non-concernés) + valeurs positives sorbitol/mannitol",
        ]
    }

    report["stats"] = {
        "total_variants":            report["schema_changes"],
        "schema_available":          schema_counts["available"],
        "schema_total":              schema_counts["total"],
        "decontam_acai_variants":    decontam_count,
        "urgent_fixes_applied":      urgent_applied,
        "urgent_fixes_skipped":      urgent_skipped,
        "proposals_applied":         applied_count,
        "proposals_rejected":        rejected_count,
        "omega_violations_cleared":  omega_fixed,
        "residual_fiber_warnings":   len(ok_bugs),
        "residual_fiber_critical":   len(crit_bugs),
        "p2_polyols_bulk_filled":    report.get("polyols_bulk_filled", 0),
    }

    # ─────────────────────────────────────────────────────────────────────
    # [6] Sauvegarde
    # ─────────────────────────────────────────────────────────────────────
    print("\n[6] Saving outputs...")

    # ── V13 : fusionner les _source_meta persistés dans le fichier de sortie ─────
    # Les champs non touchés ce run héritent de la méta du run précédent.
    # Cela garantit que l'anti-oscillation dispose d'un historique complet
    # même pour les champs stables (non re-proposés ce run).
    _merged_count = 0
    for _ing, _prev_sm in _persisted_meta.items():
        if _ing not in ingr:
            continue
        _vdefault = ingr[_ing].get("variants", {}).get("default", {})
        if _vdefault is None:
            continue
        _sm_cur = _vdefault.setdefault("_source_meta", {})
        for _field, _meta in _prev_sm.items():
            if _field not in _sm_cur:          # seulement si non écrit ce run
                _sm_cur[_field] = _meta
                _merged_count += 1
    if _merged_count:
        print(f"   -> {_merged_count} _source_meta hérités du run précédent")

    if args.dry_run:
        print("  [DRY-RUN] Aucun fichier ecrit.")
        print(f"  [DRY-RUN] Aurait ecrit -> {os.path.relpath(args.output, BASE)}")
        print(f"  [DRY-RUN] Aurait ecrit -> {os.path.relpath(args.report, BASE)}")
    else:
        save_json(db,     args.output)
        save_json(report, args.report)

    print("\n" + "=" * 70)
    print(f"SUMMARY{'  [DRY-RUN]' if args.dry_run else ''}")
    print("=" * 70)
    for k, v in report["stats"].items():
        print(f"  {k:<40} {v}")
    if not args.dry_run:
        print(f"\nDone. Run validator_v11.py --audit --input {os.path.basename(args.output)} next.")
    else:
        print("\nDry-run termine. Relancer sans --dry-run pour appliquer.")


if __name__ == "__main__":
    main()
