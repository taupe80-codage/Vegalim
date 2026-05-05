"""
food_schema_v2.py  v3.2
========================
Module commun unifié — schéma food_variant_v3.
Source unique de vérité partagée par build_ciqual_flat_v3, usda_refactor_v2,
build_cnf_full_v9.

Changements v3.1 → v3.2 (réduction unknown_rate USDA/CNF) :
    Trois nouvelles règles lexicales EN dans parse_state_v2, appliquées
    quand level1 est encore "unknown" après toutes les règles existantes :
    - R_fermented_lexical : yogurt, kefir, buttermilk, vinegar → fermented
      (conf 0.80). Précède la règle manufactured pour éviter la collision.
    - R_manufactured_lexical : flour, oil, butter, cream, cheese, milk,
      bread, pasta, margarine, shortening, sugar, syrup, jam, coffee →
      manufactured (conf 0.68). Couvre la majorité des produits laitiers,
      corps gras, farines, céréales transformées non détectés lexicalement.
    - R_category_manufactured_default : catégories USDA/CNF ("Dairy and
      Egg Products", "Fats and Oils", "Baked Products", "Beverages",
      "Sweets", "Snacks") → manufactured (conf 0.65).
    Impact attendu : USDA 27% → ~1.5% unknown, CNF 17% → ~2% unknown.
    Résidus incompressibles : oats, buckwheat, millet (grains entiers sans
    mot-clé d'état).

Exports principaux :
    slugify, compute_variant_id, state_variant_key
    parse_state_v2          -> state dict complet (R2-R8 + R_DRIED + R_FERMENTED)
    fix_unknown_state       -> reclassification post-parse des unknowns → dried/manufactured/fermented
    classify_ou / expand_ou -> parsing des items "A ou B" CIQUAL
    build_nutrients_object  -> structure imbriquee unifiee
    build_diet_profile      -> 38 flags AJR EU
    validate_food_item      -> liste d'erreurs schema

Changements v3.0 → v3.1 (réduction unknowns 22% → ~0%) :
    - _LEVEL2_RE / cooked_generic : negative lookbehind (?<!non ) pour éviter
      que "non cuite" soit classifié cooked (audit 3 — 28 fromages à pâte pressée).
    - _LEVEL2_RE : ajout mots-clés œufs cuisinés (dur, coque, omelette, brouille,
      au plat) → level2 boiled/pan_fried pour les 11 items du sous-groupe 0410.
    - _CATEGORY_LEVEL1_MAP : +20 sous-groupes CIQUAL non couverts →
      0503 (fromages), 0601 (eaux→raw), 0801/02/03 (glaces), 1005 (épices→dried),
      0501 (laits), 0504 (crèmes), 1003 (aides culinaires), 1006 (herbes→raw),
      1002 (condiments), 0603 (alcools), 0303 (biscuits), 1009/1010 (soja),
      1004 (sels), 0905 (graisses), 1103 (infantile), 1008 (régime), 0704
      (confitures), 1104 (céréales infantiles), 0305 (pâtes à tarte).
      Gain : ~449 unknowns résolus. unknown_rate 22% → ~0.05%.

Changements v3.0 vs v2.1 (audit Q1-Q15) :
    - process.level1 : 6 valeurs (raw, cooked, dried, manufactured, fermented, unknown)
      * dried     : séchage sans cuisson (herbes, légumineuses sèches, noix, fruits secs)
      * manufactured : produit transformé industriellement (huiles, alcools, confitures…)
      * fermented : fermenté sans cuisson explicite
    - R_DRIED_LEVEL1 : level2=dried/dehydrated → level1=dried (plus level1=cooked)
    - R_FERMENTED_LEVEL1 : level2=fermented → level1=fermented
    - fix_unknown_state() : 4 passes (regex manufactured, regex dried, cat manufactured, cat dried)
    - extensions dict (Q11:c) : fat_level, fat_pct, maturity, pack_medium, dairy_process,
      variety, cooking_fat, species, cocoa_pct migrés dans state["extensions"] (non-null seulement)
    - classify_ou / expand_ou : expansion "A ou B" → N food_obj avec nutrients partagés,
      canonical = dernier terme (Q5:b)
    - get_dim_value : transparent vis-à-vis de extensions (cherche aussi dans state["extensions"])
    - LEVEL1_VALUES : constante frozenset exportée
    - validate_food_item : valide les 6 level1 + extensions
"""

import hashlib
import json
import re
from typing import Optional

# ============================================================================
# 1. UTILITAIRES
# ============================================================================

_ACCENT_TABLE = str.maketrans(
    "aaaaeeeeiiooouuucnAAAAEEEEIIOOOUUUCN",
    "aaaaeeeeiiooouuucnAAAAEEEEIIOOOUUUCN",
)

# str.maketrans source/dest doivent avoir meme longueur — on construit proprement
_SRC = "àâäéèêëîïôöùûüçñÀÂÄÉÈÊËÎÏÔÖÙÛÜÇÑ"
_DST = "aaaeeeeiioouuucnAAAEEEEIIOOUUUCN"
# Padding pour alignement (les majuscules ont moins de variantes ici)
_ACCENT_TABLE = str.maketrans(_SRC, _DST + "A" * (len(_SRC) - len(_DST)))

# Version robuste : on construit char par char
_ACCENT_MAP_STR = [
    ("à","a"),("â","a"),("ä","a"),("é","e"),("è","e"),("ê","e"),("ë","e"),
    ("î","i"),("ï","i"),("ô","o"),("ö","o"),("ù","u"),("û","u"),("ü","u"),
    ("ç","c"),("ñ","n"),
    ("À","A"),("Â","A"),("Ä","A"),("É","E"),("È","E"),("Ê","E"),("Ë","E"),
    ("Î","I"),("Ï","I"),("Ô","O"),("Ö","O"),("Ù","U"),("Û","U"),("Ü","U"),
    ("Ç","C"),("Ñ","N"),
]
_SRC2 = "".join(s for s, _ in _ACCENT_MAP_STR)
_DST2 = "".join(d for _, d in _ACCENT_MAP_STR)
_ACCENT_TABLE = str.maketrans(_SRC2, _DST2)
_LIGATURES = [("\u0153","oe"),("\u0152","OE"),("\u00e6","ae"),("\u00c6","AE")]


def _deaccent(text: str) -> str:
    t = text.translate(_ACCENT_TABLE)
    for src, dst in _LIGATURES:
        t = t.replace(src, dst)
    return t


def slugify(text: str) -> str:
    """Slug robuste pour group_key. Gere les accents FR/EN."""
    t = _deaccent(text.lower())
    t = re.sub(r"[,;()\[\]'\".:/\\%]", " ", t)
    t = re.sub(r"[^a-z0-9\s_-]", "", t)
    t = re.sub(r"[\s_-]+", "_", t).strip("_")
    return t[:80]


def compute_variant_id(food_id: str, state: dict) -> str:
    """SHA-1 deterministe. Ne pas modifier — identique dans les 3 builds."""
    state_clean = {k: v for k, v in state.items() if not k.startswith("_")}
    canon = json.dumps(
        {"food_id": food_id, "state": state_clean},
        sort_keys=True, ensure_ascii=True,
    )
    return "v_" + hashlib.sha1(canon.encode("utf-8")).hexdigest()[:12]


def state_variant_key(state: dict) -> str:
    """Cle lisible retrocompat. Ex: 'raw', 'cooked.boiled', 'dried', 'manufactured', 'unknown'."""
    l1 = state["process"]["level1"]
    l2 = state["process"]["level2"]
    if l1 == "raw":
        return "raw"
    if l1 == "cooked" and l2:
        return f"cooked.{l2}"
    if l1 in ("dried", "manufactured", "fermented"):
        return l1
    return "unknown"


# ============================================================================
# 2. PATTERNS — FR + EN fusionnes, pre-compiles au chargement du module
# ============================================================================

# ── Level 2 : mega-regex avec groupes nommes ──────────────────────────────────
# Un seul scan au lieu de 20+ appels .search() sequentiels (~5x plus rapide).
# Ordre : plus specifique EN PREMIER (deep_fried avant fried, etc.).
# sauteed/stir_fried : "saute a la poele/wok" -> stir_fried ; "saute" seul -> pan_fried.
_LEVEL2_RE = re.compile(
    # Cuissons aqueuses
    r"\b(?P<steamed>steamed|a la vapeur|vapeur)\b|"
    # Œufs cuisinés (0410) — mots-clés absents du qualificatif CIQUAL (v3.1)
    r"\b(?P<boiled>boiled|bouilli[e]?s?|simmered|mijote[e]?|cuit a l.eau|dur\b|a la coque)\b|"
    r"\b(?P<poached>poached|poche[e]?)\b|"
    r"\b(?P<pressure_cooked>pressure[- ]cooked|auto.?cuiseur|cocotte[- ]minute)\b|"
    r"\b(?P<braised>braised|braise[e]?)\b|"
    # Cuissons seches
    r"\b(?P<baked>oven[- ]cooked|baked|au four|cuit[e]? au four|gratine[e]?)\b|"
    r"\b(?P<roasted>roasted|roti[e]?)\b|"
    r"\b(?P<grilled>grilled|grille[e]?|broiled)\b|"
    r"\b(?P<toasted>toasted|toaste[e]?)\b|"
    r"\b(?P<barbecue>barbecue[d]?|bbq)\b|"
    r"\b(?P<microwaved>microwaved|micro[- ]?ondes?)\b|"
    # Cuissons avec matiere grasse — du plus specifique au moins
    r"\b(?P<deep_fried>deep[- ]?fried|frit[e]? en friteuse|grande friture)\b|"
    r"\b(?P<pan_fried>pan[- ]?fried|pan[- ]?broiled|poele[e]?|blondi[e]?|omelette|brouille[e]?|au plat)\b|"
    r"\b(?P<stir_fried>stir[- ]?fried|saute[e]? a la poele|saute[e]? au wok|wok)\b|"
    r"\b(?P<sauteed>sauteed|saute[e]?)\b|"
    r"\b(?P<fried>fried|frit[e]?)\b(?!\s+rice)|"
    # Transformations non-thermiques
    r"\b(?P<dehydrated>dehydrated|deshydrate[e]?|powdered|en poudre)\b|"
    r"\b(?P<dried>dried|seche[e]?s?|sec)\b(?!\s+(?:matter|weight|de\s|d['\u2019]))|"
    r"\b(?P<fermented>fermented|fermente[e]?)\b|"
    r"\b(?P<smoked>smoked|fume[e]?)\b|"
    r"\b(?P<sprouted>sprouted|germe[e]?)\b|"
    # Fallback — "non cuit(e)(s)" exclu via lookbehind (audit 3 : "fromage à pâte pressée non cuite")
    r"(?<!non )(?<!non\s)\b(?P<cooked_generic>cooked|cuit[e]?s?|prepared|prepare[e]?s?)\b",
    re.I,
)

_LEVEL2_CONF: dict[str, float] = {
    "steamed": 0.97, "boiled": 0.97, "poached": 0.95, "pressure_cooked": 0.95,
    "braised": 0.95, "baked": 0.95, "roasted": 0.95, "grilled": 0.93,
    "toasted": 0.93, "barbecue": 0.93, "microwaved": 0.95, "deep_fried": 0.97, "pan_fried": 0.95,
    "stir_fried": 0.93, "sauteed": 0.93, "fried": 0.90,
    "dehydrated": 0.95, "dried": 0.90, "fermented": 0.95, "smoked": 0.95,
    "sprouted": 0.93, "cooked_generic": 0.70,
}

# ── Preservation ──────────────────────────────────────────────────────────────
# Note : "raw/cru" est RETIRE — gere exclusivement via level1="raw".
_PRESERVATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(canned|en conserve|appertise[e]?|au naturel)\b", re.I), "canned"),
    (re.compile(r"\bin\s+(?:olive\s+)?oil\b", re.I), "canned"),
    (re.compile(r"\b(frozen|congele[e]?|surgele[e]?)\b", re.I), "frozen"),
    (re.compile(r"\b(pasteurized|pasteurise[e]?|uht)\b", re.I), "pasteurized"),
    (re.compile(r"\b(refrigerated|refrigere[e]?)\b", re.I), "refrigerated"),
    (re.compile(r"\b(shelf[- ]stable|longue conservation)\b", re.I), "shelf_stable"),
    (re.compile(r"\b(pickled|saumure[e]?|marine[e]?)\b", re.I), "pickled"),
    (re.compile(r"\bmarinated\b", re.I), "marinated"),
    (re.compile(r"\b(fresh|frais|fraiche?)\b", re.I), "fresh"),
]

# ── Physical form ─────────────────────────────────────────────────────────────
_PHYSICAL_FORM_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(drained|egoutter|egoutte[e]?)\b", re.I), "drained"),
    (re.compile(r"\b(with liquid|avec liquide|solids and liquid)\b", re.I), "with_liquid"),
    (re.compile(r"\b(mashed|ecrase[e]?)\b", re.I), "mashed"),
    (re.compile(r"\b(pureed|en puree)\b", re.I), "pureed"),
    (re.compile(r"\b(sliced|tranche[e]?)\b", re.I), "sliced"),
    (re.compile(r"\b(chopped|hache[e]?|concasse[e]?)\b", re.I), "chopped"),
    (re.compile(r"\b(grated|rape[e]?)\b", re.I), "grated"),
    (re.compile(r"\b(crushed|broye[e]?)\b", re.I), "crushed"),
    (re.compile(r"\b(juice|jus)\b", re.I), "juice"),
    (re.compile(r"\b(powder|poudre)\b", re.I), "powder"),
    (re.compile(r"\b(flour|farine)\b", re.I), "flour"),
    (re.compile(r"\b(flakes?|flocons?)\b", re.I), "flakes"),
    (re.compile(r"\b(paste|pate|concentre[e]?)\b", re.I), "paste"),
    (re.compile(r"\b(extract|extrait)\b", re.I), "extract"),
    (re.compile(r"\b(granulated|granule[e]?)\b", re.I), "granulated"),
    (re.compile(r"\bdry(?!\s+(?:matter|weight|wine|red|white))\b", re.I), "dry"),
    (re.compile(r"\b(fluid|liquide)\b", re.I), "fluid"),
    (re.compile(r"\b(concentrate[d]?|concentre[e]?)\b", re.I), "concentrate"),
    (re.compile(r"\b(undiluted|non dilue)\b", re.I), "undiluted"),
    (re.compile(r"\b(defatted|degraisser|degraisse[e]?)\b", re.I), "defatted"),
    (re.compile(r"\b(whole|entier[e]?)\b(?!\s+(?:grain|wheat|milk))", re.I), "whole"),
]

# ── Part ─────────────────────────────────────────────────────────────────────
_PART_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(white|blanc[he]?|albumen)\b", re.I), "white"),
    (re.compile(r"\byolk\b|\bjaune\b(?!\s+d.oeuf\s+de)", re.I), "yolk"),
    (re.compile(r"\b(flesh|chair|pulpe)\b", re.I), "flesh"),
    (re.compile(r"\b(skin|peau|zeste|rind|ecorce)\b", re.I), "skin"),
    (re.compile(r"\bseeds?\b|\bgraines?\b|\bpepins?\b", re.I), "seed"),
    (re.compile(r"\bleaves?\b|\bfeuilles?\b", re.I), "leaf"),
    (re.compile(r"\b(bulb|bulbe)\b", re.I), "bulb"),
    (re.compile(r"\b(root|racine)\b", re.I), "root"),
    (re.compile(r"\b(halves?|halved)\b", re.I), "halves"),
    (re.compile(r"\bcloves?\b|\bgousses?\b(?=\s+d.ail)", re.I), "clove"),
    (re.compile(r"\bkernels?\b", re.I), "kernel"),
    (re.compile(r"\bpods?\b", re.I), "pod"),
    (re.compile(r"\b(peeled|pele[e]?|sans peau|epluch[e][e]?)\b", re.I), "peeled"),
    (re.compile(r"\b(seeded|egrene[e]?|sans pepins)\b", re.I), "seeded"),
    (re.compile(r"\b(destemmed|equete[e]?)\b", re.I), "destemmed"),
]

# ── Additives ─────────────────────────────────────────────────────────────────
_ADDITIVES_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(no salt|unsalted|sans sel|non sale[e]?|without salt)\b", re.I), "no_salt"),
    (re.compile(r"\b(with salt|salted|avec sel|sale[e]?|sodium added)\b", re.I), "salt"),
    (re.compile(r"\b(no sugar|unsweetened|sans sucre|non sucre[e]?)\b", re.I), "no_sugar"),
    (re.compile(r"\b(sweetened|sucre[e]?|avec sucre)\b", re.I), "sugar"),
    (re.compile(r"\bin syrup\b|\bau sirop\b", re.I), "syrup"),
    (re.compile(r"\bin oil\b|\ba l.huile\b|\ben huile\b|\bpacked in oil\b", re.I), "oil"),
    (re.compile(r"\bin brine\b|\ben saumure\b|\bbrined?\b", re.I), "brine"),
    # unenriched avant enriched
    (re.compile(r"\b(unenriched|non enrichi[e]?)\b", re.I), "unenriched"),
    (re.compile(r"\b(enriched|enrichi[e]?|fortified|fortifie[e]?)\b", re.I), "enriched"),
    (re.compile(r"\bvitamins?\s+added\b|\benrichi en vitamines\b", re.I), "vitamins_added"),
    (re.compile(r"\bminerals?\s+added\b|\benrichi en mineraux\b", re.I), "minerals_added"),
    (re.compile(r"\bomega[- ]3\s+added\b", re.I), "omega3_added"),
    (re.compile(r"\b(reduced sodium|low sodium|faible en sodium)\b", re.I), "reduced_sodium"),
    (re.compile(r"\b(sulphured|sulphited)\b", re.I), "sulphured"),
]

# ── Fat level ─────────────────────────────────────────────────────────────────
_FAT_LEVEL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(skim(?:med)?|ecreme[e]?|nonfat|fat[- ]free|0\s*%)\b", re.I), "skim"),
    (re.compile(r"\b(semi[- ]skim(?:med)?|demi[- ]ecreme[e]?|1\s*%\s*milkfat)\b", re.I), "semi_skim"),
    (re.compile(r"\b(low[- ]fat|allege[e]?|reduced[- ]fat|2\s*%)\b", re.I), "low_fat"),
    (re.compile(r"\b(whole(?=\s+milk)|full[- ]fat|entier[e]?(?=\s+(?:lait|,))|3\.25\s*%)\b", re.I), "whole"),
]
# Bug corrige : "mg" (milligrams) retire du groupe
# Accepte : MG (abrev CIQUAL), mf, m.g., matiere(s) grasse(s), milkfat
_FAT_PCT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*(?:mf\b|m\.g\.|matieres?\s+grasses?|milkfat|\bMG\b)",
    re.I,
)

# ── Maturity ──────────────────────────────────────────────────────────────────
_MATURITY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(mature seeds?|graines?\s+matures?|graines?\s+seches?)\b", re.I), "mature_seeds"),
    (re.compile(r"\b(ripe[d]?|mur[e]?)\b", re.I), "ripe"),
    (re.compile(r"\b(unripe|immature)\b", re.I), "unripe"),
    (re.compile(r"\b(young pods?|jeunes?\s+gousses?)\b", re.I), "young_pods"),
]

# ── Pack medium ───────────────────────────────────────────────────────────────
_PACK_MEDIUM_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(light syrup|sirop leger)\b", re.I), "syrup_light"),
    (re.compile(r"\b(heavy syrup|sirop lourd|in syrup|au sirop)\b", re.I), "syrup_heavy"),
    (re.compile(r"\b(packed in oil|in oil|a l.huile)\b", re.I), "oil"),
    (re.compile(r"\b(packed in water|in water|au naturel|dans l.eau)\b", re.I), "water"),
    (re.compile(r"\b(packed in juice|in juice|dans le jus)\b", re.I), "juice"),
    (re.compile(r"\b(in brine|en saumure)\b", re.I), "brine"),
]

# ── Dairy process ─────────────────────────────────────────────────────────────
_DAIRY_PROCESS_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(homogenized|homogeneise[e]?)\b", re.I), "homogenized"),
    (re.compile(r"\b(evaporated|evapore[e]?)\b", re.I), "evaporated"),
    (re.compile(r"\b(condensed|condense[e]?)\b", re.I), "condensed"),
    (re.compile(r"\b(pasteurized|pasteurise[e]?)\b", re.I), "pasteurized"),
]

# ── Color / variety ───────────────────────────────────────────────────────────
_COLOR_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:dark\s+)?(?:red|rouge)\b", re.I), "red"),
    (re.compile(r"\b(green|vert[e]?)\b", re.I), "green"),
    (re.compile(r"\b(yellow|jaune)\b", re.I), "yellow"),
    (re.compile(r"\b(black|noir[e]?)\b", re.I), "black"),
    (re.compile(r"\b(purple|violet[te]?|pink|rose)\b", re.I), "purple"),
    (re.compile(r"\b(white|blanc[he]?)\b", re.I), "white"),
]
_CULTIVAR_RE = re.compile(
    r"\b(fuji|gala|golden|granny\s+smith|pink\s+lady|crimson|bintje|charlotte)\b",
    re.I,
)

# ── Cooking fat ───────────────────────────────────────────────────────────────
_COOKING_FAT_LEVEL2: frozenset[str] = frozenset({
    "fried", "deep_fried", "pan_fried", "stir_fried", "sauteed",
})
_COOKING_FAT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(butter|beurre)\b", re.I), "butter"),
    (re.compile(r"\b(olive oil|huile d.olive)\b", re.I), "oil_olive"),
    (re.compile(r"\b(sunflower oil|huile de tournesol)\b", re.I), "oil_sunflower"),
    (re.compile(r"\b(oil|huile)\b", re.I), "oil_generic"),
    (re.compile(r"\b(lard|graisse|saindoux)\b", re.I), "lard"),
]

DAIRY_CATEGORIES: frozenset[str] = frozenset({"Dairy and Egg Products"})

# Valeurs autorisées pour process.level1 (6 valeurs, Q12:c)
# raw        : brut / non transformé
# cooked     : cuit thermiquement (toujours accompagné de level2)
# dried      : séché / déshydraté sans cuisson (herbes, légumineuses sèches, noix, fruits secs)
# manufactured : produit fini transformé industriellement (huiles, confitures, alcools, jus…)
# fermented  : fermenté sans cuisson explicite (fromages non précisés, vinegar…)
# unknown    : fallback résiduel
LEVEL1_VALUES: frozenset[str] = frozenset({
    "raw", "cooked", "dried", "manufactured", "fermented", "unknown"
})

# Champs qui migrent dans state["extensions"] (Q11:c — purge des 7 quasi-vides)
_EXTENSION_FIELDS: frozenset[str] = frozenset({
    "fat_level", "fat_pct", "maturity", "pack_medium",
    "dairy_process", "variety", "cooking_fat", "species", "cocoa_pct",
})


# ============================================================================
# 3. parse_state_v2 — assembleur complet
#
# Parametres :
#   description          : texte source brut (nom complet)
#   category             : categorie source pour R7 dairy_process
#   search_in_qualifier  : True -> cherche l'etat APRES la 1ere virgule
#                          (CIQUAL : "Epinards, cuits, egouttés")
#                          False (defaut) -> cherche dans tout le texte
#   lang                 : "en" (USDA/CNF) | "" (defaut, CIQUAL/FR)
#                          Active les règles lexicales anglaises (v3.2) :
#                          R_fermented_lexical, R_manufactured_lexical,
#                          R_category_manufactured_default.
#                          Ne PAS passer pour les sources françaises (CIQUAL).
#
# Retourne le dict state + "_rules_fired" (a .pop() avant compute_variant_id).
# PAS de @lru_cache : dict mutable, le caller fait .pop() dessus.
# ============================================================================

def parse_state_v2(
    description: str,
    category: str = "",
    search_in_qualifier: bool = False,
    lang: str = "",
) -> dict:
    """
    Construit l'objet state complet depuis une description texte.
    Valide pour USDA, CNF et CIQUAL (patterns FR+EN fusionnes).
    Passer lang='en' pour activer les règles lexicales anglaises (USDA/CNF).
    """
    if search_in_qualifier:
        # CIQUAL : etat dans le segment apres la 1ere virgule hors parentheses
        depth, split_at = 0, -1
        for i, ch in enumerate(description):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif ch == "," and depth == 0:
                split_at = i
                break
        search_src = description[split_at + 1:].strip() if split_at >= 0 else description
    else:
        search_src = description

    # Les patterns travaillent sur des chaines desaccentuees en minuscules
    desc = _deaccent(search_src.lower())
    full = _deaccent(description.lower())   # fat_level, cultivar cherchent le nom complet
    rules: list[str] = []

    # ── level1 + level2 ───────────────────────────────────────────────────
    level1 = "unknown"
    level2 = None
    confidence = 0.50
    raw_label_fragment = None

    if re.search(r"\b(raw|uncooked|cru[e]?s?|sans\s+cuisson)\b", desc, re.I):
        level1 = "raw"
        confidence = 0.95
        rules.append("regex_raw")
    else:
        m = _LEVEL2_RE.search(desc)
        if m:
            for gname, gval in m.groupdict().items():
                if gval is not None:
                    level1 = "cooked"
                    level2 = gname
                    confidence = _LEVEL2_CONF.get(gname, 0.90)
                    raw_label_fragment = gval
                    rules.append(f"regex_level2_{gname}")
                    break

    # ── preservation (R2 : dried dans level2 -> preservation null) ────────
    preservation = None
    for pat, pval in _PRESERVATION_PATTERNS:
        if pat.search(desc):
            if level2 in ("dried", "dehydrated") and pval in ("fresh", "dried"):
                rules.append("R2_dried_exclusive")
            else:
                preservation = pval
                rules.append(f"regex_pres_{pval}")
            break

    # ── physical_form ─────────────────────────────────────────────────────
    physical_form = None
    for pat, pval in _PHYSICAL_FORM_PATTERNS:
        if pat.search(desc):
            physical_form = pval
            rules.append(f"regex_phys_{pval}")
            break

    # ── part ─────────────────────────────────────────────────────────────
    part = None
    for pat, pval in _PART_PATTERNS:
        if pat.search(desc):
            part = pval
            rules.append(f"regex_part_{pval}")
            break
    if part is None and level2 not in ("juice", "extract", "powder", "flour", "paste"):
        part = "whole"

    # ── additives (multi-valeur) ───────────────────────────────────────────
    additives: list[str] = []
    for pat, aval in _ADDITIVES_PATTERNS:
        if pat.search(desc):
            additives.append(aval)
            rules.append(f"regex_add_{aval}")
    if not additives:
        additives = ["none"]   # R4

    # ── fat_level + fat_pct ───────────────────────────────────────────────
    fat_level = None
    fat_pct = None
    for pat, fval in _FAT_LEVEL_PATTERNS:
        if pat.search(full):   # cherche dans le nom complet ("lait entier")
            fat_level = fval
            rules.append(f"regex_fat_{fval}")
            break
    m_pct = _FAT_PCT_RE.search(full)
    if m_pct:
        try:
            fat_pct = float(m_pct.group(1).replace(",", "."))
            rules.append("regex_fat_pct")
        except ValueError:
            pass

    # ── maturity ─────────────────────────────────────────────────────────
    maturity = None
    for pat, mval in _MATURITY_PATTERNS:
        if pat.search(desc):
            maturity = mval
            rules.append(f"regex_mat_{mval}")
            break

    # ── pack_medium (R6) ─────────────────────────────────────────────────
    pack_medium = None
    if preservation == "canned" or physical_form in ("drained", "with_liquid"):
        for pat, pmval in _PACK_MEDIUM_PATTERNS:
            if pat.search(desc):
                pack_medium = pmval
                rules.append(f"regex_pack_{pmval}")
                break
        if pack_medium is None and preservation == "canned":
            pack_medium = "water"

    # ── dairy_process (R7) ────────────────────────────────────────────────
    dairy_process = None
    if category in DAIRY_CATEGORIES:
        for pat, dpval in _DAIRY_PROCESS_PATTERNS:
            if pat.search(full):
                dairy_process = dpval
                rules.append(f"regex_dairy_{dpval}")
                break

    # ── variety ──────────────────────────────────────────────────────────
    variety = None
    color = None
    for pat, cval in _COLOR_PATTERNS:
        if pat.search(desc):
            color = cval
            rules.append(f"regex_color_{cval}")
            break
    cm = _CULTIVAR_RE.search(full)
    if color or cm:
        variety = {
            "color":    color,
            "cultivar": cm.group(1).title() if cm else None,
        }

    # ── cooking_fat (R8) ─────────────────────────────────────────────────
    cooking_fat = None
    if level2 in _COOKING_FAT_LEVEL2:
        fat_type = None
        for pat, ftype in _COOKING_FAT_PATTERNS:
            if pat.search(full):
                fat_type = ftype
                break
        cooking_fat = {"type": fat_type, "amount_g_per_100g": None}

    # ── R_DRIED_LEVEL1 : level2=dried/dehydrated → level1="dried" (Q12:c) ──────
    # Le séchage n'est PAS une cuisson thermique ; c'est un état primaire.
    # "Herbes séchées", "Légumineuses sèches", "Noix" : level1=dried, level2=null.
    # Conf conservée : 0.90 (dried) ou 0.95 (dehydrated).
    if level2 in ("dried", "dehydrated"):
        level1 = "dried"
        level2 = None
        rules.append("R_dried_level1_promotion")

    # ── R_FERMENTED_LEVEL1 : level2=fermented → level1="fermented" (Q12:c) ────
    # La fermentation n'est pas une cuisson ; c'est un état de transformation distinct.
    if level2 == "fermented":
        level1 = "fermented"
        level2 = None
        rules.append("R_fermented_level1_promotion")

    # ── R_DRY_DEHYDRATED : "dry" en physical_form sans level2 → dried ──────────
    # "Milk, dry whole", "Cheese, parmesan, dry grated" : dried (pas cooked).
    # Conf 0.80 : "dry" peut signifier "non hydraté" sans déshydratation explicite.
    if physical_form == "dry" and level1 == "unknown":
        level1 = "dried"
        confidence = 0.80
        rules.append("R_dry_dehydrated_fallback")

    # ── R_CANNED_FALLBACK : conservation canned → process de cuisson implicite ──
    # Les conserves alimentaires sont systématiquement cuites avant mise en boîte.
    # Conf 0.65 : cooked_generic (méthode inconnue).
    if preservation == "canned" and level1 == "unknown":
        level1 = "cooked"
        level2 = "cooked_generic"
        confidence = 0.65
        rules.append("R_canned_fallback")

    # ── R_CATEGORY_RAW_DEFAULT : catégories CNF sans mention d'état → raw ─────
    # "Lettuce, butterhead", "Raisin, golden seedless" : aucun mot-clé d'état.
    # Ne s'applique QUE si level1 est encore unknown après toutes les règles.
    # Conf 0.60 : inférence catégorielle, moins fiable qu'une règle lexicale.
    _RAW_DEFAULT_CATEGORIES: frozenset = frozenset({
        "Vegetables and Vegetable Products",
        "Fruits and Fruit Juices",
        "Fruits and fruit juices",          # variante de casse CNF
        "Nut and Seed Products",
        "Spices and Herbs",
    })
    if level1 == "unknown" and category in _RAW_DEFAULT_CATEGORIES:
        level1 = "raw"
        confidence = 0.60
        rules.append("R_category_raw_default")

    # ── Règles EN uniquement (lang="en") ─────────────────────────────────────
    # Ces règles sont réservées aux sources anglaises (USDA, CNF).
    # Elles NE doivent PAS s'appliquer aux sources françaises (CIQUAL) pour
    # éviter des faux positifs sur les noms français.
    if lang == "en" and level1 == "unknown":

        # R_FERMENTED_LEXICAL : yaourts, kéfir, babeurre, vinaigre EN ─────────
        # Précède la règle manufactured (yaourt = fermenté > manufactured).
        # Conf 0.80 : mots-clés spécifiques au procédé fermentatif.
        _FERMENTED_LEXICAL_EN_RE = re.compile(
            r"\b(yogurt|yoghurt|yogourt|kefir|kephir|buttermilk|"
            r"vinegar|cider\s+vinegar|wine\s+vinegar|"
            r"tempeh|miso|natto|kombucha|kimchi)\b",
            re.I,
        )
        if _FERMENTED_LEXICAL_EN_RE.search(full):
            level1 = "fermented"
            confidence = 0.80
            rules.append("R_fermented_lexical")

        # R_MANUFACTURED_LEXICAL : produits transformés EN ────────────────────
        # Farines, huiles, beurres, crèmes, fromages, laits, pains, pâtes,
        # margarines, shortenings, sucres, sirops, confitures, café,
        # tofu, sauce soja, okara, substituts végétaux, gluten.
        # Conf 0.68 : lexical anglais, fiabilité intermédiaire.
        elif level1 == "unknown":
            _MANUFACTURED_LEXICAL_EN_RE = re.compile(
                r"\b(flour|oil\b|butter|cream|cheese|"
                r"milk(?!\s+chocolate)\b|"
                r"bread\b|pasta\b|noodles?|"
                r"margarine|shortening|"
                r"sugar|syrup|jam\b|honey|"
                r"coffee|cocoa\b|chocolate\b|"
                r"tofu|soy\s+sauce|tamari|shoyu|okara|"
                r"meatless|seitan|gluten\b|papad|papadum|"
                r"glazed)\b",
                re.I,
            )
            if _MANUFACTURED_LEXICAL_EN_RE.search(full):
                level1 = "manufactured"
                confidence = 0.68
                rules.append("R_manufactured_lexical")

        # R_CATEGORY_MANUFACTURED_DEFAULT : catégories USDA/CNF ──────────────
        # Filet catégoriel pour les produits non détectés lexicalement.
        # "Cereal Grains and Pasta" : grains entiers (oats, buckwheat, millet)
        # sont minimalement transformés → manufactured acceptable.
        # "Legumes and Legume Products" : tofu, okara, farines légumineuses.
        # Conf 0.65 : inférence catégorielle, moins fiable.
        if level1 == "unknown":
            _MANUFACTURED_DEFAULT_CATEGORIES: frozenset = frozenset({
                "Dairy and Egg Products",
                "Fats and Oils",
                "Baked Products",
                "Beverages",
                "Sweets",
                "Snacks",
                "Cereal Grains and Pasta",
                "Breakfast Cereals",
                "Legumes and Legume Products",
            })
            if category in _MANUFACTURED_DEFAULT_CATEGORIES:
                level1 = "manufactured"
                confidence = 0.65
                rules.append("R_category_manufactured_default")

    # ── Assemblage extensions (Q11:c — champs quasi-vides en sous-dict) ────────
    # Seuls les champs non-null sont inclus dans extensions.
    _ext_raw = {
        "fat_level":     fat_level,
        "fat_pct":       fat_pct,
        "maturity":      maturity,
        "pack_medium":   pack_medium,
        "dairy_process": dairy_process,
        "variety":       variety,
        "cooking_fat":   cooking_fat,
        "species":       None,    # injecté via BASE_INGREDIENT_MAP.extra_dims
        "cocoa_pct":     None,    # injecté via BASE_INGREDIENT_MAP.extra_dims
    }
    extensions = {k: v for k, v in _ext_raw.items() if v is not None} or None

    return {
        "process": {
            "level1":             level1,
            "level2":             level2,
            "confidence":         round(confidence, 3),
            "raw_label_fragment": raw_label_fragment,
        },
        "preservation":  preservation,
        "physical_form": physical_form,
        "part":          part,
        "additives":     additives,
        "extensions":    extensions,   # None si tous les champs quasi-vides sont null
        "_rules_fired":  rules,
    }



# ============================================================================
# 3b. fix_unknown_state — reclassification post-parse des unknowns (Q3:a / Q12:c)
#
# Récupère ~230 des 506 unknowns CIQUAL en 3 passes lexicales + catégorielle.
# Appelé APRÈS parse_state_v2. Ne touche PAS aux états déjà déterminés.
# ============================================================================

# Produits transformés industriellement → manufactured
_MANUFACTURED_RE = re.compile(
    r"\b("
    r"jus\b|nectar|sirop|smoothie|"                      # boissons non-alcool
    r"biere|cidre|ale\b|lager|porter\b|stout\b|"         # alcools fermentés
    r"vin\b|vins\b|champagne|porto|madere|"
    r"spiritueux|whisky|vodka|rhum|gin\b|calvados|kirsch|cointreau|pastis|"
    r"liqueur|aperitif|digestif|anisette|"
    r"huile|margarine|"                                   # corps gras
    r"confiture|marmelade|compote|gelee\b|pate de fruit|"# sucres/confits
    r"beurre de cacahuete|pate a tartiner|"
    r"sauce\b|ketchup|mayonnaise|moutarde\b|vinaigrette|condiment|"
    r"cafe\b|expresso|cappuccino|"                        # boissons chaudes préparées
    r"the\b(?!\s+blanc)|infusion|tisane|"
    r"sucre\s+(?:blanc|roux|glace|complet|de\s+canne)|"  # sucres raffinés
    r"miel|sirop\s+d.agave|"
    r"lait\s+(?:concentre|en\s+poudre|infantile)|"
    r"chocolat\s+(?:noir|lait|blanc|poudre)|cacao\b|"
    r"farine\b(?!\s+de\s+(?:pois|chataigne|ma[ïi]s)\s+crue)|" # farines (déjà processed)
    r"amidon|fecule|"
    r"conserve\b|plat\s+(?:cuisiné|cuisine|prepare)|soupe\b|"
    r"biscuit\b|gâteau|gateau|viennoiserie|pain\b(?!\s+(?:complet|de\s+mie\s+sans|grille))|"
    r"preparation\s+pour\s+gateau"
    r")\b",
    re.I,
)

# Séchés sans cuisson → dried (herbes, noix, légumineuses, champignons, algues, fruits secs)
_DRIED_FALLBACK_RE = re.compile(
    r"\b("
    r"herbe[s]?\b|epice[s]?\b|"                          # herbes/épices
    r"noix\b|noisette|amande|pistache|cajou|macadamia|"  # noix
    r"raisin\s+sec|abricot\s+sec|figue\s+seche|pruneau|datte|"  # fruits secs
    r"champignon\s+(?:seche|sec)|algue[s]?\s+(?:seche|sec)e?s?|"
    r"legume[s]?\s+secs?|graine[s]?\s+seches?|"          # légumineuses/graines sèches
    r"seche[e]?s?\b|sec\b(?!\s+(?:vin|vins|cidre))"      # "sec" / "sèche" standalone (hors vins)
    r")\b",
    re.I,
)

# Catégories CIQUAL mappées à un level1 par défaut quand état = unknown
# (utilisé comme fallback catégoriel après les regex)
_CATEGORY_LEVEL1_MAP: dict[str, str] = {
    # ── Boissons alcoolisées ────────────────────────────────────────────────
    "0201": "manufactured",   # bières
    "0202": "manufactured",   # cidres
    "0203": "manufactured",   # vins
    "0204": "manufactured",   # spiritueux / liqueurs
    "0205": "manufactured",   # champagnes/mousseux
    "0206": "manufactured",   # vins rosés
    "0207": "manufactured",   # vins doux
    "0603": "manufactured",   # alcools divers (eaux-de-vie, saké, sangria…)
    # ── Corps gras ──────────────────────────────────────────────────────────
    "0701": "manufactured",   # huiles végétales
    "0702": "manufactured",   # graisses animales
    "0703": "manufactured",   # margarines
    "0905": "manufactured",   # autres matières grasses (saindoux, graisses volaille)
    # ── Boissons sucrées / non-alcoolisées ─────────────────────────────────
    "0602": "manufactured",   # boissons sucrées industrielles
    # ── Produits laitiers et dérivés ────────────────────────────────────────
    "0501": "manufactured",   # laits (pasteurisés, UHT…)
    "0503": "manufactured",   # fromages et alternatives végétales
    "0504": "manufactured",   # crèmes et spécialités à base de crème
    # ── Sucres, confitures, glaces ──────────────────────────────────────────
    "0801": "manufactured",   # glaces
    "0802": "manufactured",   # sorbets
    "0803": "manufactured",   # desserts glacés
    "0901": "manufactured",   # confitures / marmelades
    "0902": "manufactured",   # compotes / coulis
    "0903": "manufactured",   # sucres et sirops
    "0704": "manufactured",   # confitures et assimilés (crème de pruneaux…)
    # ── Plats cuisinés / soupes ─────────────────────────────────────────────
    "1201": "manufactured",   # plats cuisinés
    "1202": "manufactured",   # soupes industrielles
    # ── Aides culinaires / condiments / sels ───────────────────────────────
    "1002": "manufactured",   # condiments (vinaigres, olives, cornichons…)
    "1003": "manufactured",   # aides culinaires (sons, levures, vanille…)
    "1004": "manufactured",   # sels alimentaires
    # ── Produits végétariens / soja ─────────────────────────────────────────
    "1009": "manufactured",   # ingrédients végétariens (tofu, seitan, tempeh…)
    "1010": "manufactured",   # tartinables végétariens (houmous, guacamole…)
    # ── Biscuits / snacks ───────────────────────────────────────────────────
    "0303": "manufactured",   # biscuits apéritifs (chips, pop-corn, gressins…)
    # ── Pâtes à tarte ───────────────────────────────────────────────────────
    "0305": "manufactured",   # pâtes à tarte (brick, khatfa…)
    # ── Alimentation infantile ──────────────────────────────────────────────
    "1103": "manufactured",   # desserts infantiles
    "1104": "manufactured",   # céréales et biscuits infantiles
    "1008": "manufactured",   # substituts de repas hypocaloriques
    # ── Eaux ────────────────────────────────────────────────────────────────
    "0601": "raw",            # eaux minérales et de source — état brut
    # ── Épices et herbes ────────────────────────────────────────────────────
    "1005": "dried",          # épices en poudre — séchées avant broyage
    "1006": "raw",            # herbes aromatiques fraîches — état brut
}

# Catégories CIQUAL où l'unknown → dried par défaut (herbes sèches, noix, légumineuses sèches)
_DRIED_DEFAULT_SUBGROUPS: frozenset[str] = frozenset({
    "0301", "0302",           # herbes aromatiques sèches, épices sèches
    "1701", "1702",           # fruits à coque
    "1703", "1704",           # graines oléagineuses
})

# Catégories CIQUAL où l'unknown → dried via _CATEGORY_LEVEL1_MAP["1005"]
# et raw pour herbes fraîches (1006) — géré dans _CATEGORY_LEVEL1_MAP directement.

# Sous-groupes épices/herbes à ajouter au mapping catégoriel (v3.1)
# 1005 = épices en poudre → dried ; 1006 = herbes fraîches → raw
# Ces deux cas sont désormais dans _CATEGORY_LEVEL1_MAP ci-dessus.


def fix_unknown_state(
    state: dict,
    name_fr: str,
    subgroup_code: str = "",
    rules_fired: list | None = None,
) -> dict:
    """
    Reclassifie les state.process.level1 == "unknown" vers dried / manufactured / fermented.
    Appelé après parse_state_v2 dans le pipeline build.

    Modifie state IN PLACE et retourne state.
    Ajoute les règles déclenchées à rules_fired (si fourni).
    """
    if state.get("process", {}).get("level1") != "unknown":
        return state   # déjà déterminé — ne pas écraser

    rules = rules_fired if rules_fired is not None else []
    desc = _deaccent(name_fr.lower())

    # Passe 1 — regex manufactured
    if _MANUFACTURED_RE.search(desc):
        state["process"]["level1"] = "manufactured"
        state["process"]["confidence"] = 0.72
        rules.append("fix_manufactured_regex")
        return state

    # Passe 2 — regex dried
    if _DRIED_FALLBACK_RE.search(desc):
        state["process"]["level1"] = "dried"
        state["process"]["confidence"] = 0.68
        rules.append("fix_dried_regex")
        return state

    # Passe 3 — mapping catégoriel manufactured
    if subgroup_code in _CATEGORY_LEVEL1_MAP:
        state["process"]["level1"] = _CATEGORY_LEVEL1_MAP[subgroup_code]
        state["process"]["confidence"] = 0.65
        rules.append(f"fix_cat_{_CATEGORY_LEVEL1_MAP[subgroup_code]}_{subgroup_code}")
        return state

    # Passe 4 — mapping catégoriel dried
    if subgroup_code in _DRIED_DEFAULT_SUBGROUPS:
        state["process"]["level1"] = "dried"
        state["process"]["confidence"] = 0.60
        rules.append(f"fix_cat_dried_{subgroup_code}")
        return state

    # Reste unknown
    return state


# ============================================================================
# 3c. classify_ou / expand_ou — parsing des items "A ou B" (Q4:a / Q5:b)
#
# CIQUAL utilise "ou" pour deux cas :
#   Type-1 (noms alternatifs) : "Farine de blé tendre ou froment, T45"
#     → deux food_obj distincts, nutrients PARTAGÉS (copiés), _ou_expansion=True
#     → canonical = deuxième terme (B), d'après Q5:b
#   Type-2 (variétés interchangeables) : "Haricot vert ou haricot jaune"
#     → traité comme Type-1 par défaut ; BASE_INGREDIENT_MAP gère le regroupement
# ============================================================================

_OU_SPLIT_RE = re.compile(
    r"\s+ou\s+(?![^(]*\))",   # "ou" hors parenthèses
    re.I,
)


def classify_ou(name_fr: str) -> bool:
    """True si le nom contient un 'ou' hors parenthèses."""
    return bool(_OU_SPLIT_RE.search(name_fr))


def _split_ou_terms(name_fr: str) -> list[str]:
    """
    Découpe 'A, B ou C, D' en termes complets.
    Ex: "Farine de blé tendre ou froment, T45"
        → ["Farine de blé tendre, T45", "froment, T45"]
    Le qualificatif après la 1ère virgule du nom complet est propagé à chaque terme.
    """
    # Séparer la partie base de la partie qualificatif
    depth = 0
    first_comma = -1
    for i, ch in enumerate(name_fr):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            first_comma = i
            break

    if first_comma > 0:
        base_part = name_fr[:first_comma].strip()
        qualifier  = name_fr[first_comma + 1:].strip()   # "T45", "cuit, égoutté"…
    else:
        base_part = name_fr
        qualifier  = ""

    # Découper le base_part sur "ou"
    raw_terms = _OU_SPLIT_RE.split(base_part)
    terms = []
    for t in raw_terms:
        t = t.strip()
        if qualifier:
            terms.append(f"{t}, {qualifier}")
        else:
            terms.append(t)
    return terms


def expand_ou(food_obj: dict) -> list[dict]:
    """
    Expanse un food_obj contenant "ou" en N food_obj distincts.
    Le premier item est l'original (source_id conservé, _ou_expansion=False).
    Les suivants sont synthétiques (nutrients copiés, _ou_expansion=True).
    Canonical = dernier terme (Q5:b : le terme le plus précis/usuel est en 2e position).
    Si < 2 termes : retourne [food_obj] sans modification.
    """
    import copy

    name_fr = food_obj.get("name_fr", "")
    terms = _split_ou_terms(name_fr)

    if len(terms) < 2:
        return [food_obj]

    result: list[dict] = []
    canonical_name = terms[-1]   # Q5:b — le dernier terme est le canonique

    for i, term in enumerate(terms):
        obj = copy.deepcopy(food_obj)
        is_expansion = (i > 0)

        obj["name_fr"]   = term
        obj["base_name"] = term.split(",")[0].strip()
        obj["name"]["fr"] = term
        obj["name"]["canonical"] = canonical_name if is_expansion else food_obj["name"].get("canonical", name_fr)

        # group_key recalculé depuis le nouveau base_name
        obj["group_key"] = slugify(obj["base_name"])

        # Traçabilité
        obj["_ou_expansion"]   = is_expansion
        obj["_ou_source_name"] = name_fr   # nom d'origine complet

        if is_expansion:
            # ID synthétique : suffixe _ou{i}
            obj["id"]      = f"{food_obj['id']}_ou{i}"
            obj["food_id"] = obj["id"]
            # variant_id recalculé (state potentiellement différent après re-slugify)
            obj["variant_id"] = compute_variant_id(obj["id"], food_obj["state"])
            # Pas de source_id original — tracé via _ou_source_name
            obj["sources"] = [{
                "db":        food_obj["sources"][0]["db"] if food_obj.get("sources") else "CIQUAL",
                "source_id": f"{food_obj['source_id']}_ou{i}",
                "raw_label": term,
                "version":   food_obj["sources"][0].get("version", "2025") if food_obj.get("sources") else "2025",
                "_ou_expansion": True,
                "_ou_source_label": name_fr,
            }]

        result.append(obj)

    return result
#
# Parametres :
#   flat               : dict plat des nutriments (cles standard)
#   extra              : dict USDA supplementaire (amino acids, lycopene...)
#                        None pour CIQUAL/CNF
#   level1             : "raw"|"cooked"|"unknown" pour _nutrient_meta.basis
#   completeness_fields: cles pour missing_fields (defaut : 14 communs)
#   detection_limits   : dict CIQUAL {field: seuil} — None pour USDA/CNF
# ============================================================================

_DEFAULT_COMPLETENESS: list[str] = [
    "energy_kcal", "protein_g", "carbs_g",  "fat_g",
    "fiber_g",     "water_g",   "sodium_mg", "calcium_mg",
    "iron_mg",     "vitamin_c_mg", "folate_ug", "vitamin_d_ug",
    "fa_saturated_g", "fa_18_3_ala_g",
]


def build_nutrients_object(
    flat: dict,
    *,
    extra: Optional[dict] = None,
    level1: str = "unknown",
    completeness_fields: Optional[list] = None,
    detection_limits: Optional[dict] = None,
) -> dict:
    """
    Structure nutrients imbriquee conforme au schema v2.
    Parametres keyword-only pour eviter les confusions de position.
    """
    ex = extra or {}
    dl = detection_limits or {}
    cf = completeness_fields or _DEFAULT_COMPLETENESS

    def g(f):
        return flat.get(f)

    def e(f):
        return ex.get(f)

    def _sum_none(*args):
        vals = [v for v in args if v is not None]
        return round(sum(vals), 6) if vals else None

    def aa_mg(f):
        """Convertit amino acids USDA de g en mg."""
        v = e(f)
        return round(v * 1000, 3) if v is not None else None

    # missing_fields : vraiment absent (pas juste sous seuil de detection)
    missing = [f for f in cf if flat.get(f) is None and f not in dl]

    nutrient_meta = {
        "basis":                   "as_prepared" if level1 == "cooked" else "as_purchased",
        "serving_g":               None,
        "missing_fields":          missing,
        "imputed_fields":          [],
        "source_method":           "laboratory",
        "retention_factors_applied": False,
    }
    if dl:
        nutrient_meta["detection_limits"] = dl   # CIQUAL uniquement

    return {
        "energy": {
            "kcal": g("energy_kcal"),
            "kj":   g("energy_kj"),
        },
        "macros": {
            "water_g":   g("water_g"),
            "protein_g": g("protein_g"),
            "fat_g":     g("fat_g"),
            "carbs_g":   g("carbs_g"),
            "fiber_g":   g("fiber_g"),
            "alcohol_g": g("alcohol_g"),
            "ash_g":     g("ash_g"),
        },
        "lipids": {
            "saturated_g":       g("fa_saturated_g"),
            "monounsaturated_g": g("fa_mufa_g"),
            "polyunsaturated_g": g("fa_pufa_g"),
            "omega3_g":  _sum_none(g("fa_18_3_ala_g"), g("fa_20_5_epa_g"), g("fa_22_6_dha_g")),
            "omega6_g":  _sum_none(g("fa_18_2_linoleic_g"), g("fa_20_4_ara_g")),
            "trans_g":           e("fa_trans_g"),        # USDA seulement
            "cholesterol_mg":    g("cholesterol_mg"),
            "fa_4_0_g":          g("fa_4_0_g"),
            "fa_6_0_g":          g("fa_6_0_g"),
            "fa_8_0_g":          g("fa_8_0_g"),
            "fa_10_0_g":         g("fa_10_0_g"),
            "fa_12_0_g":         g("fa_12_0_g"),
            "fa_14_0_g":         g("fa_14_0_g"),
            "fa_16_0_g":         g("fa_16_0_g"),
            "fa_18_0_g":         g("fa_18_0_g"),
            "fa_18_1_oleic_g":   g("fa_18_1_oleic_g"),
            "fa_18_2_linoleic_g":g("fa_18_2_linoleic_g"),
            "fa_18_3_ala_g":     g("fa_18_3_ala_g"),
            "fa_20_4_ara_g":     g("fa_20_4_ara_g"),
            "fa_20_5_epa_g":     g("fa_20_5_epa_g"),
            "fa_22_6_dha_g":     g("fa_22_6_dha_g"),
        },
        "carbohydrates": {
            "sugars_g":          g("sugar_g"),
            "added_sugars_g":    None,
            "starch_g":          g("starch_g"),
            "polyols_g":         g("polyols_g"),
            "fiber_soluble_g":   e("fiber_soluble_g"),   # USDA seulement
            "fiber_insoluble_g": e("fiber_insoluble_g"), # USDA seulement
            "fructose_g":        g("fructose_g"),
            "galactose_g":       g("galactose_g"),
            "glucose_g":         g("glucose_g"),
            "lactose_g":         g("lactose_g"),
            "maltose_g":         g("maltose_g"),
            "saccharose_g":      g("saccharose_g"),
        },
        # amino acids : USDA Foundation uniquement, null sinon (CNF/CIQUAL)
        "proteins_detail": {
            "histidine_mg":     aa_mg("aa_histidine_g"),
            "isoleucine_mg":    aa_mg("aa_isoleucine_g"),
            "leucine_mg":       aa_mg("aa_leucine_g"),
            "lysine_mg":        aa_mg("aa_lysine_g"),
            "methionine_mg":    aa_mg("aa_methionine_g"),
            "phenylalanine_mg": aa_mg("aa_phenylalanine_g"),
            "threonine_mg":     aa_mg("aa_threonine_g"),
            "tryptophan_mg":    aa_mg("aa_tryptophan_g"),
            "valine_mg":        aa_mg("aa_valine_g"),
        },
        "vitamins": {
            "a_rae_mcg":             g("vitamin_a_rae_ug"),
            "retinol_mcg":           g("retinol_ug"),
            "beta_carotene_mcg":     g("beta_carotene_ug"),
            "b1_mg":                 g("vitamin_b1_mg"),
            "b2_mg":                 g("vitamin_b2_mg"),
            "b3_mg":                 g("vitamin_b3_mg"),
            "b5_mg":                 g("vitamin_b5_mg"),
            "b6_mg":                 g("vitamin_b6_mg"),
            "b9_mcg":                g("folate_ug"),
            "b9_dfe_mcg":            g("folate_dfe_ug"),
            "b9_intrinsic_mcg":      g("folate_intrinsic_ug"),
            "b9_folic_mcg":          g("folic_acid_ug"),
            "b12_mcg":               g("vitamin_b12_ug"),
            "c_mg":                  g("vitamin_c_mg"),
            "d_mcg":                 g("vitamin_d_ug"),
            "d2_mcg":                g("vitamin_d2_ug"),
            "d3_mcg":                g("vitamin_d3_ug"),
            "e_mg":                  g("vitamin_e_mg"),
            "e_alpha_tocopherol_mg": g("alpha_tocopherol_mg"),
            "k1_mcg":                g("vitamin_k1_ug"),
            "k2_mcg":                g("vitamin_k2_ug"),
            "choline_mg":            g("choline_mg"),
            "betaine_mg":            None,
            "biotin_mcg":            e("biotin_ug"),     # USDA seulement
        },
        "minerals": {
            "calcium_mg":    g("calcium_mg"),
            "phosphorus_mg": g("phosphorus_mg"),
            "potassium_mg":  g("potassium_mg"),
            "sodium_mg":     g("sodium_mg"),
            "magnesium_mg":  g("magnesium_mg"),
            "iron_mg":       g("iron_mg"),
            "zinc_mg":       g("zinc_mg"),
            "copper_mg":     g("copper_mg"),
            "manganese_mg":  g("manganese_mg"),
            "selenium_mcg":  g("selenium_ug"),
            "iodine_mcg":    g("iodine_ug"),
            "chloride_mg":   g("chloride_mg"),
            "fluoride_mg":   None,
            "chromium_mcg":  None,
            "molybdenum_mcg":None,
        },
        "bioactives": {
            "lycopene_mcg":      e("lycopene_ug"),           # USDA
            "lutein_mcg":        e("lutein_zeaxanthin_ug"),  # USDA
            "beta_carotene_mcg": g("beta_carotene_ug"),
            "polyphenols_mg":    None,
            "caffeine_mg":       None,
            "taurine_mg":        None,
            "phytosterols_mg": _sum_none(
                e("phytosterol_beta_sitosterol_mg"),
                e("phytosterol_stigmasterol_mg"),
                e("phytosterol_campesterol_mg"),
            ),
            "nitrates_mg":       None,
            "organic_acids_g":   g("organic_acids_g"),      # CIQUAL
        },
        "_nutrient_meta": nutrient_meta,
    }


# ============================================================================
# 5. SEUILS DIET PROFILE — AJR EU (Reglement 1169/2011)
#    Source unique. Chaque build importe ces constantes, ne les redefinit pas.
# ============================================================================

HIGH_PROT_G    = 20.0
HIGH_FIBER_G   =  6.0
LOW_FAT_G      =  3.0
LOW_SUGAR_G    =  5.0
LOW_SODIUM_MG  = 120.0
LOW_CAL_KCAL   =  40.0
HIGH_CA_MG     = 300.0
HIGH_FE_MG     =   4.2
HIGH_MG_MG     = 112.5
HIGH_P_MG      = 210.0
HIGH_K_MG      = 600.0
HIGH_ZN_MG     =   3.0
HIGH_SE_UG     =  16.5
HIGH_IODINE_UG =  45.0
HIGH_MN_MG     =   0.6
HIGH_CU_MG     =   0.3
HIGH_B12_UG    =  0.75
HIGH_VD_UG     =   1.5
HIGH_VC_MG     =  24.0
HIGH_FOL_UG    =  60.0
HIGH_VE_MG     =   3.6
HIGH_VK1_UG    =  22.5
HIGH_ALA_G     =   1.1
HIGH_OMEGA3_G  =   0.3

ANTIOXIDANT_THRESHOLDS: list[tuple[str, float]] = [
    ("vitamin_c_mg",      30.0),
    ("beta_carotene_ug", 300.0),
    ("vitamin_e_mg",       3.0),
    ("selenium_ug",       16.5),
]


# ============================================================================
# 6. build_diet_profile — 38 flags communs
# ============================================================================

_DAIRY_KW    = ["milk", "cream", "cheese", "butter", "yogurt", "yoghurt",
                "ghee", "whey", "casein", "kefir", "buttermilk", "lactose",
                "lait", "fromage", "creme", "yaourt", "beurre", "lacto"]
_DAIRY_PLANT = ["almond milk", "soy milk", "oat milk", "coconut milk",
                "plant milk", "plant-based", "lait d amande", "lait de soja",
                "lait d avoine", "lait vegetal"]
_EGG_KW      = ["egg", "eggs", " yolk", "albumen", "meringue", "mayonnaise",
                "oeuf", "jaune d oeuf", "blanc d oeuf"]
_GLUTEN_KW   = ["wheat", "rye", "barley", "spelt", "kamut", "semolina",
                "bulgur", "farro", "flour", "pasta", "bread", "couscous", "seitan",
                "ble", "seigle", "orge", "epeautre", "farine", "pates", "pain"]
_NUT_KW      = ["almond", "cashew", "walnut", "pecan", "pistachio", "hazelnut",
                "macadamia", "brazil nut", "chestnut", "pine nut",
                "amande", "noix de cajou", "noix", "pistache", "noisette"]
_SOY_KW      = ["soy", "soya", "tofu", "tempeh", "edamame", "miso", "natto",
                "soja", "proteines de soja"]
_FERMENT_KW  = ["yogurt", "yoghurt", "kefir", "miso", "tempeh", "natto",
                "kombucha", "vinegar", "fermented", "fermente",
                "yaourt", "vinaigre", "choucroute", "kimchi", "levain"]


def build_diet_profile(
    name: str,
    nutrients: dict,
    category: str = "",
    detection_limits: Optional[dict] = None,
) -> dict:
    """38 flags dietetiques. Identique USDA v2 / CNF v9 / CIQUAL."""
    dl = detection_limits or {}
    nl = _deaccent(name.lower())

    is_plant_dairy = any(k in nl for k in _DAIRY_PLANT)
    has_dairy  = not is_plant_dairy and any(k in nl for k in _DAIRY_KW)
    has_egg    = any(k in nl for k in _EGG_KW)
    has_gluten = any(k in nl for k in _GLUTEN_KW)
    has_nut    = any(k in nl for k in _NUT_KW)
    has_soy    = any(k in nl for k in _SOY_KW)
    is_ferment = any(k in nl for k in _FERMENT_KW)
    vegan      = not has_dairy and not has_egg
    is_wf      = not has_gluten and not has_dairy and not has_soy

    def g(k):
        return nutrients.get(k)

    def hi(field, thr):
        val = g(field)
        if val is not None:
            return val >= thr
        return False if field in dl else None

    def lo(field, thr):
        val = g(field)
        return (val <= thr) if val is not None else None

    ala = g("fa_18_3_ala_g")
    epa = g("fa_20_5_epa_g") or 0.0
    dha = g("fa_22_6_dha_g") or 0.0
    epa_dha = epa + dha
    if ala is not None:
        high_omega3 = (ala >= HIGH_ALA_G) or (epa_dha >= HIGH_OMEGA3_G)
    elif "fa_18_3_ala_g" in dl:
        high_omega3 = epa_dha >= HIGH_OMEGA3_G
    elif g("fa_20_5_epa_g") is not None or g("fa_22_6_dha_g") is not None:
        high_omega3 = epa_dha >= HIGH_OMEGA3_G
    else:
        high_omega3 = None

    ant_hit = False; ant_all_none = True
    for _f, _thr in ANTIOXIDANT_THRESHOLDS:
        _v = g(_f)
        if _v is not None:
            ant_all_none = False
            if _v >= _thr:
                ant_hit = True; break
        elif _f in dl:
            ant_all_none = False
    high_antioxidant = True if ant_hit else (None if ant_all_none else False)

    sugar = g("sugar_g"); carbs = g("carbs_g"); fiber = g("fiber_g") or 0.0
    if sugar is not None and carbs is not None:
        diabetic = sugar <= LOW_SUGAR_G and (carbs - fiber) <= 15.0
    elif "sugar_g" in dl and carbs is not None:
        diabetic = (carbs - fiber) <= 15.0
    else:
        diabetic = None

    alc = g("alcohol_g")
    if alc is None:
        alcohol_free = True if "alcohol_g" in dl else None
    else:
        alcohol_free = alc < 0.5

    lac = g("lactose_g")
    if lac is not None:
        lactose_free = lac < 0.5
    elif "lactose_g" in dl:
        lactose_free = True
    else:
        lactose_free = not has_dairy

    return {
        "vegetarian":      True,
        "vegan":           vegan,
        "egg_free":        not has_egg,
        "dairy_free":      not has_dairy,
        "lactose_free":    lactose_free,
        "gluten_free":     not has_gluten,
        "nuts_free":       not has_nut,
        "soja_free":       not has_soy,
        "gelatin_risk":    False,
        "diabetic_friendly": diabetic,
        "high_protein":    hi("protein_g",    HIGH_PROT_G),
        "high_fiber":      hi("fiber_g",       HIGH_FIBER_G),
        "low_fat":         lo("fat_g",         LOW_FAT_G),
        "low_sugar":       lo("sugar_g",       LOW_SUGAR_G),
        "low_sodium":      lo("sodium_mg",     LOW_SODIUM_MG),
        "low_calorie":     lo("energy_kcal",   LOW_CAL_KCAL),
        "high_calcium":    hi("calcium_mg",    HIGH_CA_MG),
        "high_iron":       hi("iron_mg",       HIGH_FE_MG),
        "high_magnesium":  hi("magnesium_mg",  HIGH_MG_MG),
        "high_phosphorus": hi("phosphorus_mg", HIGH_P_MG),
        "high_potassium":  hi("potassium_mg",  HIGH_K_MG),
        "high_zinc":       hi("zinc_mg",       HIGH_ZN_MG),
        "high_selenium":   hi("selenium_ug",   HIGH_SE_UG),
        "high_iodine":     hi("iodine_ug",     HIGH_IODINE_UG),
        "high_manganese":  hi("manganese_mg",  HIGH_MN_MG),
        "high_copper":     hi("copper_mg",     HIGH_CU_MG),
        "high_vit_b12":    hi("vitamin_b12_ug", HIGH_B12_UG),
        "high_vit_d":      hi("vitamin_d_ug",   HIGH_VD_UG),
        "high_vit_c":      hi("vitamin_c_mg",   HIGH_VC_MG),
        "high_folate":     hi("folate_ug",      HIGH_FOL_UG),
        "high_vit_e":      hi("vitamin_e_mg",   HIGH_VE_MG),
        "high_vit_k1":     hi("vitamin_k1_ug",  HIGH_VK1_UG),
        "high_omega3_ala": hi("fa_18_3_ala_g",  HIGH_ALA_G),
        "high_omega3":     high_omega3,
        "alcohol_free":    alcohol_free,
        "whole_food":      is_wf,
        "fermented":       is_ferment,
        "high_antioxidant": high_antioxidant,
    }


# ============================================================================
# 7. validate_food_item
# ============================================================================

def validate_food_item(item: dict) -> list[str]:
    """
    Valide la conformite d'un item au schema v2.
    Retourne une liste d'erreurs (vide = valide).
    """
    errors: list[str] = []

    if not str(item.get("variant_id", "")).startswith("v_"):
        errors.append("variant_id manquant ou format invalide (attendu 'v_...')")

    name = item.get("name")
    if not isinstance(name, dict) or not name.get("canonical"):
        errors.append("name doit etre {fr, en, canonical} avec canonical non vide")

    state = item.get("state", {})
    proc  = state.get("process", {})
    l1    = proc.get("level1")
    l2    = proc.get("level2")
    if l1 not in LEVEL1_VALUES:
        errors.append(f"state.process.level1 invalide : {l1!r} (valeurs: {sorted(LEVEL1_VALUES)})")
    if l1 == "raw" and l2 is not None:
        errors.append("R3 : level1=raw => level2 doit etre null")
    if l1 == "cooked" and l2 is None:
        errors.append("R3 : level1=cooked => level2 requis")
    if l1 in ("dried", "manufactured", "fermented") and l2 is not None:
        errors.append(f"R3b : level1={l1!r} => level2 doit etre null (niveau primaire)")

    additives = state.get("additives", [])
    if "none" in additives and len(additives) > 1:
        errors.append("R4 : 'none' doit etre exclusif dans additives")

    pack = (state.get("extensions") or {}).get("pack_medium")
    pres = state.get("preservation")
    pf   = state.get("physical_form")
    if pack is not None and pres != "canned" and pf not in ("drained", "with_liquid"):
        errors.append("R6 : pack_medium non null => preservation=canned OU physical_form drained/with_liquid")

    cf = (state.get("extensions") or {}).get("cooking_fat")
    if cf is not None and l2 not in _COOKING_FAT_LEVEL2:
        errors.append(f"R8 : cooking_fat non null => level2 dans {set(_COOKING_FAT_LEVEL2)}")

    sources = item.get("sources", [])
    if not sources:
        errors.append("sources vide (R10 : >= 1 source requise)")
    for src in sources:
        if not src.get("db") or not src.get("source_id") or not src.get("raw_label"):
            errors.append(f"source incomplete (db/source_id/raw_label requis) : {src}")

    meta = item.get("nutrients", {}).get("_nutrient_meta", {})
    if meta.get("basis") not in ("as_prepared", "as_purchased", "dry_weight", None):
        errors.append(f"_nutrient_meta.basis invalide : {meta.get('basis')!r}")

    return errors


# ============================================================================
# 8. EXPORTS
# ============================================================================

__all__ = [
    # Utilitaires
    "slugify",
    "compute_variant_id",
    "state_variant_key",
    # State
    "parse_state_v2",
    "fix_unknown_state",
    "classify_ou",
    "expand_ou",
    "LEVEL1_VALUES",
    "_EXTENSION_FIELDS",
    "DAIRY_CATEGORIES",
    # Nutriments
    "build_nutrients_object",
    # Diet profile
    "build_diet_profile",
    "ANTIOXIDANT_THRESHOLDS",
    "HIGH_PROT_G",   "HIGH_FIBER_G",  "LOW_FAT_G",     "LOW_SUGAR_G",
    "LOW_SODIUM_MG", "LOW_CAL_KCAL",  "HIGH_CA_MG",    "HIGH_FE_MG",
    "HIGH_MG_MG",    "HIGH_P_MG",     "HIGH_K_MG",     "HIGH_ZN_MG",
    "HIGH_SE_UG",    "HIGH_IODINE_UG","HIGH_MN_MG",    "HIGH_CU_MG",
    "HIGH_B12_UG",   "HIGH_VD_UG",    "HIGH_VC_MG",    "HIGH_FOL_UG",
    "HIGH_VE_MG",    "HIGH_VK1_UG",   "HIGH_ALA_G",    "HIGH_OMEGA3_G",
    # Validation
    "validate_food_item",
    # Variant tree (v7)
    "BASE_INGREDIENT_MAP",
    "NUTRIENT_PRECISION",
    "round_nutrients",
    "detect_extra_dimensions",
    "DIM_PRIORITY",
    "get_dim_value",
    "build_variant_tree",
]


# ============================================================================
# 9. BASE_INGREDIENT_MAP — table d'appartenance group_key → base_key
# ============================================================================

BASE_INGREDIENT_MAP: dict[str, dict] = {

    # =========================================================================
    # LÉGUMINEUSES
    # =========================================================================

    # ── Haricots ──────────────────────────────────────────────────────────────
    "haricot_rouge":     {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "rouge"}},
    "haricot_blanc":     {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "blanc"}},
    "haricot_vert":      {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "vert"}},
    "haricots_verts":    {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "vert"}},
    "haricot_flageolet": {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "flageolet"}},
    "haricot_mungo":     {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "mungo"}},
    "haricot_beurre":    {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "beurre"}},
    "haricot_plat":      {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "plat"}},
    "haricot_coco":      {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "coco"}},
    "graine_germee_de_haricot_mungo_ou_pousse_de_soja":
                         {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "mungo"}},
    "haricot_de_lima_ou_pois_savon_ou_pois_du_cap_ou_pois_souche":
                         {"base_key": "haricot_de_lima", "name_fr": "Haricot de Lima",
                          "name_en": "Lima bean", "extra_dims": {}},

    # ── Lentilles ─────────────────────────────────────────────────────────────
    "lentille_corail":   {"base_key": "lentille", "name_fr": "Lentille", "name_en": "Lentil",
                          "extra_dims": {"variety": "corail"}},
    "lentille_verte":    {"base_key": "lentille", "name_fr": "Lentille", "name_en": "Lentil",
                          "extra_dims": {"variety": "verte"}},
    "lentille_blonde":   {"base_key": "lentille", "name_fr": "Lentille", "name_en": "Lentil",
                          "extra_dims": {"variety": "blonde"}},
    "graine_germee_de_lentille":
                         {"base_key": "lentille", "name_fr": "Lentille", "name_en": "Lentil",
                          "extra_dims": {"variety": "germee"}},
    "pates_de_lentilles_corail":
                         {"base_key": "pates_de_lentilles", "name_fr": "Pâtes de lentilles",
                          "name_en": "Lentil pasta", "extra_dims": {"variety": "corail"}},

    # ── Pois ──────────────────────────────────────────────────────────────────
    "pois_mange_tout_ou_pois_gourmand":
                         {"base_key": "pois", "name_fr": "Pois", "name_en": "Peas",
                          "extra_dims": {"variety": "mange_tout"}},
    "pois_mange_tout_ou_pois_gourmands":
                         {"base_key": "pois", "name_fr": "Pois", "name_en": "Peas",
                          "extra_dims": {"variety": "mange_tout"}},
    "pois_casse":        {"base_key": "pois", "name_fr": "Pois", "name_en": "Peas",
                          "extra_dims": {"variety": "casse"}},
    "pois_chiche":       {"base_key": "pois_chiche", "name_fr": "Pois chiche",
                          "name_en": "Chickpea", "extra_dims": {}},
    "pois_d_angole_vert":{"base_key": "pois_d_angole", "name_fr": "Pois d'Angole",
                          "name_en": "Pigeon pea", "extra_dims": {}},

    # =========================================================================
    # CÉRÉALES ET FARINES
    # =========================================================================

    # ── Riz ───────────────────────────────────────────────────────────────────
    "riz_blanc":                {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                                 "extra_dims": {"variety": "blanc"}},
    "riz_complet":              {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                                 "extra_dims": {"variety": "complet"}},
    "riz_sauvage":              {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                                 "extra_dims": {"variety": "sauvage"}},
    "riz_rouge":                {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                                 "extra_dims": {"variety": "rouge"}},
    "riz_semi_complet":         {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                                 "extra_dims": {"variety": "semi_complet"}},
    "riz_thai_ou_riz_basmati":  {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                                 "extra_dims": {"variety": "thai_basmati"}},
    "riz_thai":                 {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                                 "extra_dims": {"variety": "thai"}},
    "riz_basmati":              {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                                 "extra_dims": {"variety": "basmati"}},

    # ── Blé ───────────────────────────────────────────────────────────────────
    "ble_dur":          {"base_key": "ble", "name_fr": "Blé", "name_en": "Wheat",
                         "extra_dims": {"variety": "dur"}},
    "ble_dur_complet":  {"base_key": "ble", "name_fr": "Blé", "name_en": "Wheat",
                         "extra_dims": {"variety": "dur_complet"}},
    "ble_de_khorasan":  {"base_key": "ble", "name_fr": "Blé", "name_en": "Wheat",
                         "extra_dims": {"variety": "khorasan"}},

    # ── Farine de blé tendre ──────────────────────────────────────────────────
    "farine_de_ble_tendre_ou_froment_t45":  {"base_key": "farine_de_ble", "name_fr": "Farine de blé",
                                              "name_en": "Wheat flour", "extra_dims": {"variety": "t45"}},
    "farine_de_ble_tendre_ou_froment_t55":  {"base_key": "farine_de_ble", "name_fr": "Farine de blé",
                                              "name_en": "Wheat flour", "extra_dims": {"variety": "t55"}},
    "farine_de_ble_tendre_ou_froment_t65":  {"base_key": "farine_de_ble", "name_fr": "Farine de blé",
                                              "name_en": "Wheat flour", "extra_dims": {"variety": "t65"}},
    "farine_de_ble_tendre_ou_froment_t80":  {"base_key": "farine_de_ble", "name_fr": "Farine de blé",
                                              "name_en": "Wheat flour", "extra_dims": {"variety": "t80"}},
    "farine_de_ble_tendre_ou_froment_t110": {"base_key": "farine_de_ble", "name_fr": "Farine de blé",
                                              "name_en": "Wheat flour", "extra_dims": {"variety": "t110"}},
    "farine_de_ble_tendre_ou_froment_t150": {"base_key": "farine_de_ble", "name_fr": "Farine de blé",
                                              "name_en": "Wheat flour", "extra_dims": {"variety": "t150"}},

    # ── Farine de seigle ──────────────────────────────────────────────────────
    "farine_de_seigle_t85":  {"base_key": "farine_de_seigle", "name_fr": "Farine de seigle",
                               "name_en": "Rye flour", "extra_dims": {"variety": "t85"}},
    "farine_de_seigle_t130": {"base_key": "farine_de_seigle", "name_fr": "Farine de seigle",
                               "name_en": "Rye flour", "extra_dims": {"variety": "t130"}},
    "farine_de_seigle_t170": {"base_key": "farine_de_seigle", "name_fr": "Farine de seigle",
                               "name_en": "Rye flour", "extra_dims": {"variety": "t170"}},

    # ── Semoule / Couscous ────────────────────────────────────────────────────
    "semoule_de_ble_dur":                          {"base_key": "semoule", "name_fr": "Semoule", "name_en": "Semolina",
                                                    "extra_dims": {"variety": "ble_dur"}},
    "semoule_ou_graine_de_couscous":               {"base_key": "semoule", "name_fr": "Semoule", "name_en": "Semolina",
                                                    "extra_dims": {"variety": "couscous"}},
    "semoule_ou_graine_de_couscous_complete":      {"base_key": "semoule", "name_fr": "Semoule", "name_en": "Semolina",
                                                    "extra_dims": {"variety": "couscous_complet"}},
    "semoule_ou_graine_de_couscous_semi_complete": {"base_key": "semoule", "name_fr": "Semoule", "name_en": "Semolina",
                                                    "extra_dims": {"variety": "couscous_semi_complet"}},
    "graine_de_couscous":                          {"base_key": "semoule", "name_fr": "Semoule", "name_en": "Semolina",
                                                    "extra_dims": {"variety": "couscous"}},

    # ── Son ───────────────────────────────────────────────────────────────────
    "son_de_ble":    {"base_key": "son", "name_fr": "Son", "name_en": "Bran",
                      "extra_dims": {"variety": "ble"}},
    "son_d_avoine":  {"base_key": "son", "name_fr": "Son", "name_en": "Bran",
                      "extra_dims": {"variety": "avoine"}},
    "son_de_mais":   {"base_key": "son", "name_fr": "Son", "name_en": "Bran",
                      "extra_dims": {"variety": "mais"}},
    "son_de_riz":    {"base_key": "son", "name_fr": "Son", "name_en": "Bran",
                      "extra_dims": {"variety": "riz"}},

    # ── Galettes soufflées ────────────────────────────────────────────────────
    "galette_de_riz_complet_souffle":   {"base_key": "galette_souffle", "name_fr": "Galette soufflée",
                                         "name_en": "Puffed cake", "extra_dims": {"variety": "riz_complet"}},
    "galette_de_cereales_soufflees":    {"base_key": "galette_souffle", "name_fr": "Galette soufflée",
                                         "name_en": "Puffed cake", "extra_dims": {"variety": "cereales"}},
    "galette_de_mais_souffle":          {"base_key": "galette_souffle", "name_fr": "Galette soufflée",
                                         "name_en": "Puffed cake", "extra_dims": {"variety": "mais"}},

    # =========================================================================
    # ŒUFS
    # =========================================================================
    "oeuf_cru":          {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "poule", "part": "whole"}},
    "oeuf_dur":          {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "poule", "part": "whole"}},
    "oeuf_poche":        {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "poule", "part": "whole"}},
    "oeuf_a_la_coque":   {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "poule", "part": "whole"}},
    "oeuf_brouille":     {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "poule", "part": "whole"}},
    "oeuf_au_plat":      {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "poule", "part": "whole"}},
    "blanc_d_oeuf_cru":  {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "poule", "part": "white"}},
    "blanc_d_oeuf":      {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "poule", "part": "white"}},
    "jaune_d_oeuf":      {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "poule", "part": "yolk"}},
    "oeuf_de_caille":    {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "caille", "part": "whole"}},
    "oeuf_de_cane":      {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "cane", "part": "whole"}},
    "oeuf_d_oie":        {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "oie", "part": "whole"}},
    "oeuf_de_dinde":     {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                          "extra_dims": {"species": "dinde", "part": "whole"}},

    # =========================================================================
    # FROMAGES DE CHÈVRE
    # =========================================================================
    "fromage_de_chevre_frais_ou_palet_frais_ou_crottin_frais_ou_buchette_frais":
                         {"base_key": "fromage_de_chevre", "name_fr": "Fromage de chèvre",
                          "name_en": "Goat cheese", "extra_dims": {"dairy_process": "frais"}},
    "fromage_de_chevre_demi_sec":
                         {"base_key": "fromage_de_chevre", "name_fr": "Fromage de chèvre",
                          "name_en": "Goat cheese", "extra_dims": {"dairy_process": "demi_sec"}},
    "fromage_de_chevre_sec":
                         {"base_key": "fromage_de_chevre", "name_fr": "Fromage de chèvre",
                          "name_en": "Goat cheese", "extra_dims": {"dairy_process": "sec"}},
    "fromage_de_chevre_affine_ou_palet_affine_ou_crottin_affine_ou_buchette_affine":
                         {"base_key": "fromage_de_chevre", "name_fr": "Fromage de chèvre",
                          "name_en": "Goat cheese", "extra_dims": {"dairy_process": "affine"}},
    "fromage_de_chevre_buche":
                         {"base_key": "fromage_de_chevre", "name_fr": "Fromage de chèvre",
                          "name_en": "Goat cheese", "extra_dims": {"dairy_process": "buche"}},
    "crottin_de_chevre": {"base_key": "fromage_de_chevre", "name_fr": "Fromage de chèvre",
                          "name_en": "Goat cheese", "extra_dims": {"dairy_process": "affine"}},

    # =========================================================================
    # CHOCOLAT ET CONFISERIE
    # =========================================================================
    "chocolat_noir_40_de_cacao": {"base_key": "chocolat", "name_fr": "Chocolat",
                                  "name_en": "Chocolate",
                                  "extra_dims": {"variety": "noir", "cocoa_pct": "40"}},
    "chocolat_noir_50_de_cacao": {"base_key": "chocolat", "name_fr": "Chocolat",
                                  "name_en": "Chocolate",
                                  "extra_dims": {"variety": "noir", "cocoa_pct": "50"}},
    "chocolat_noir_70_de_cacao": {"base_key": "chocolat", "name_fr": "Chocolat",
                                  "name_en": "Chocolate",
                                  "extra_dims": {"variety": "noir", "cocoa_pct": "70"}},
    "chocolat_au_lait":          {"base_key": "chocolat", "name_fr": "Chocolat",
                                  "name_en": "Chocolate",
                                  "extra_dims": {"variety": "lait"}},
    "chocolat_blanc":            {"base_key": "chocolat", "name_fr": "Chocolat",
                                  "name_en": "Chocolate",
                                  "extra_dims": {"variety": "blanc"}},

    # =========================================================================
    # PROTÉINES VÉGÉTALES / SOJA
    # =========================================================================
    "tofu_nature":   {"base_key": "tofu", "name_fr": "Tofu", "name_en": "Tofu",
                      "extra_dims": {"physical_form": "firm"}},
    "tofu_soyeux":   {"base_key": "tofu", "name_fr": "Tofu", "name_en": "Tofu",
                      "extra_dims": {"physical_form": "silken"}},
    "tofu_fume":     {"base_key": "tofu", "name_fr": "Tofu", "name_en": "Tofu",
                      "extra_dims": {"physical_form": "smoked"}},

    # =========================================================================
    # LÉGUMES
    # =========================================================================

    # ── Asperge ───────────────────────────────────────────────────────────────
    "asperge_blanche":                     {"base_key": "asperge", "name_fr": "Asperge",
                                            "name_en": "Asparagus", "extra_dims": {"variety": "blanche"}},
    "asperge_blanche_ou_asperge_violette": {"base_key": "asperge", "name_fr": "Asperge",
                                            "name_en": "Asparagus", "extra_dims": {"variety": "blanche_violette"}},
    "asperge_verte":                       {"base_key": "asperge", "name_fr": "Asperge",
                                            "name_en": "Asparagus", "extra_dims": {"variety": "verte"}},

    # ── Champignon ────────────────────────────────────────────────────────────
    "champignon_de_paris":   {"base_key": "champignon", "name_fr": "Champignon", "name_en": "Mushroom",
                              "extra_dims": {"variety": "paris"}},
    "champignon_noir":       {"base_key": "champignon", "name_fr": "Champignon", "name_en": "Mushroom",
                              "extra_dims": {"variety": "noir"}},
    "champignon_lentin_ou_shiitake":
                             {"base_key": "champignon", "name_fr": "Champignon", "name_en": "Mushroom",
                              "extra_dims": {"variety": "shiitake"}},
    "champignon_lentin_comestible_ou_shiitake":
                             {"base_key": "champignon", "name_fr": "Champignon", "name_en": "Mushroom",
                              "extra_dims": {"variety": "shiitake"}},

    # =========================================================================
    # NOIX ET GRAINES
    # =========================================================================
    "noix":                          {"base_key": "noix", "name_fr": "Noix", "name_en": "Walnut", "extra_dims": {}},
    "noix_du_bresil_ou_noix_d_amazonie":
                                     {"base_key": "noix_du_bresil", "name_fr": "Noix du Brésil",
                                      "name_en": "Brazil nut", "extra_dims": {}},
    "noix_de_cajou":                 {"base_key": "noix_de_cajou", "name_fr": "Noix de cajou",
                                      "name_en": "Cashew", "extra_dims": {}},
    "noix_de_pecan":                 {"base_key": "noix_de_pecan", "name_fr": "Noix de pécan",
                                      "name_en": "Pecan", "extra_dims": {}},
    "noix_de_macadamia":             {"base_key": "noix_de_macadamia", "name_fr": "Noix de macadamia",
                                      "name_en": "Macadamia", "extra_dims": {}},
    "noisette":        {"base_key": "noisette", "name_fr": "Noisette", "name_en": "Hazelnut", "extra_dims": {}},
    "noisette_grille": {"base_key": "noisette", "name_fr": "Noisette", "name_en": "Hazelnut",
                        "extra_dims": {"variety": "grille"}},

    # =========================================================================
    # CONDIMENTS ET ASSAISONNEMENTS
    # =========================================================================

    # ── Moutarde ──────────────────────────────────────────────────────────────
    "moutarde":              {"base_key": "moutarde", "name_fr": "Moutarde", "name_en": "Mustard",
                              "extra_dims": {}},
    "moutarde_a_l_ancienne": {"base_key": "moutarde", "name_fr": "Moutarde", "name_en": "Mustard",
                              "extra_dims": {"variety": "ancienne"}},

    # ── Vinaigre ──────────────────────────────────────────────────────────────
    "vinaigre_de_cidre":      {"base_key": "vinaigre", "name_fr": "Vinaigre", "name_en": "Vinegar",
                               "extra_dims": {"variety": "cidre"}},
    "vinaigre_balsamique":    {"base_key": "vinaigre", "name_fr": "Vinaigre", "name_en": "Vinegar",
                               "extra_dims": {"variety": "balsamique"}},
    "vinaigre_de_vin_rouge":  {"base_key": "vinaigre", "name_fr": "Vinaigre", "name_en": "Vinegar",
                               "extra_dims": {"variety": "vin_rouge"}},

    # ── Sel ───────────────────────────────────────────────────────────────────
    "sel_blanc_alimentaire":  {"base_key": "sel", "name_fr": "Sel", "name_en": "Salt",
                               "extra_dims": {"variety": "blanc"}},
    "sel_marin_gris":         {"base_key": "sel", "name_fr": "Sel", "name_en": "Salt",
                               "extra_dims": {"variety": "marin_gris"}},
    "sel_au_celeri":          {"base_key": "sel", "name_fr": "Sel", "name_en": "Salt",
                               "extra_dims": {"variety": "celeri"}},

    # ── Poivre ────────────────────────────────────────────────────────────────
    "poivre_noir":    {"base_key": "poivre", "name_fr": "Poivre", "name_en": "Pepper",
                       "extra_dims": {"variety": "noir"}},
    "poivre_blanc":   {"base_key": "poivre", "name_fr": "Poivre", "name_en": "Pepper",
                       "extra_dims": {"variety": "blanc"}},

    # ── Levure ────────────────────────────────────────────────────────────────
    "levure_de_biere":     {"base_key": "levure", "name_fr": "Levure", "name_en": "Yeast",
                            "extra_dims": {"variety": "biere"}},
    "levure_de_boulanger": {"base_key": "levure", "name_fr": "Levure", "name_en": "Yeast",
                            "extra_dims": {"variety": "boulanger"}},

    # =========================================================================
    # ALGUES
    # =========================================================================
    "kombu_royal":             {"base_key": "kombu", "name_fr": "Kombu", "name_en": "Kombu",
                                "extra_dims": {"variety": "royal"}},
    "kombu_ou_kombu_japonais": {"base_key": "kombu", "name_fr": "Kombu", "name_en": "Kombu",
                                "extra_dims": {"variety": "japonais"}},
    "kombu_breton":            {"base_key": "kombu", "name_fr": "Kombu", "name_en": "Kombu",
                                "extra_dims": {"variety": "breton"}},

    # =========================================================================
    # GERMES
    # =========================================================================
    "graine_germee_de_luzerne": {"base_key": "graine_germee", "name_fr": "Graine germée",
                                 "name_en": "Sprout", "extra_dims": {"variety": "luzerne"}},
    "graine_germee_de_radis":   {"base_key": "graine_germee", "name_fr": "Graine germée",
                                 "name_en": "Sprout", "extra_dims": {"variety": "radis"}},

    # =========================================================================
    # BISCOTTES
    # =========================================================================
    "biscotte_au_germe_de_ble":   {"base_key": "biscotte", "name_fr": "Biscotte",
                                   "name_en": "Rusk", "extra_dims": {"variety": "germe_de_ble"}},
    "biscotte_au_ble_complet":    {"base_key": "biscotte", "name_fr": "Biscotte",
                                   "name_en": "Rusk", "extra_dims": {"variety": "ble_complet"}},
    "biscotte_aux_cereales":      {"base_key": "biscotte", "name_fr": "Biscotte",
                                   "name_en": "Rusk", "extra_dims": {"variety": "cereales"}},
    "biscotte_briochee":          {"base_key": "biscotte", "name_fr": "Biscotte",
                                   "name_en": "Rusk", "extra_dims": {"variety": "briochee"}},

    # =========================================================================
    # USDA — BEANS
    # =========================================================================
    "beans_red":         {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "rouge"}},
    "beans_black":       {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "noir"}},
    "beans_navy":        {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "blanc"}},
    "beans_pinto":       {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "pinto"}},
    "beans_snap":        {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "vert"}},
    "beans_lima":        {"base_key": "haricot_de_lima", "name_fr": "Haricot de Lima",
                          "name_en": "Lima bean", "extra_dims": {}},
    "beans_mung":        {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                          "extra_dims": {"variety": "mungo"}},

    # =========================================================================
    # USDA — RICE
    # =========================================================================
    "rice_white": {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                   "extra_dims": {"variety": "blanc"}},
    "rice_brown": {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                   "extra_dims": {"variety": "complet"}},
    "rice_black": {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                   "extra_dims": {"variety": "noir"}},
    "rice_red":   {"base_key": "riz", "name_fr": "Riz", "name_en": "Rice",
                   "extra_dims": {"variety": "rouge"}},

    # =========================================================================
    # USDA — EGGS
    # =========================================================================
    "egg_whole": {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                  "extra_dims": {"species": "poule", "part": "whole"}},
    "egg_white": {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                  "extra_dims": {"species": "poule", "part": "white"}},
    "egg_yolk":  {"base_key": "oeuf", "name_fr": "Œuf", "name_en": "Egg",
                  "extra_dims": {"species": "poule", "part": "yolk"}},

    # =========================================================================
    # USDA — POTATOES
    # =========================================================================
    "potatoes_russet": {"base_key": "pomme_de_terre", "name_fr": "Pomme de terre",
                        "name_en": "Potato", "extra_dims": {"variety": "russet"}},
    "potatoes_red":    {"base_key": "pomme_de_terre", "name_fr": "Pomme de terre",
                        "name_en": "Potato", "extra_dims": {"variety": "rouge"}},
    "potatoes_gold":   {"base_key": "pomme_de_terre", "name_fr": "Pomme de terre",
                        "name_en": "Potato", "extra_dims": {"variety": "gold"}},

    # =========================================================================
    # USDA — APPLES
    # =========================================================================
    "apples_red":    {"base_key": "pomme", "name_fr": "Pomme", "name_en": "Apple",
                      "extra_dims": {"variety": "rouge"}},
    "apples_fuji":   {"base_key": "pomme", "name_fr": "Pomme", "name_en": "Apple",
                      "extra_dims": {"variety": "fuji"}},
    "apples_gala":   {"base_key": "pomme", "name_fr": "Pomme", "name_en": "Apple",
                      "extra_dims": {"variety": "gala"}},
    "apples_granny": {"base_key": "pomme", "name_fr": "Pomme", "name_en": "Apple",
                      "extra_dims": {"variety": "granny_smith"}},

    # =========================================================================
    # USDA — MILK
    # =========================================================================
    "milk_3_25":  {"base_key": "lait_vache", "name_fr": "Lait de vache",
                   "name_en": "Cow milk", "extra_dims": {"fat_level": "whole"}},
    "milk_2":     {"base_key": "lait_vache", "name_fr": "Lait de vache",
                   "name_en": "Cow milk", "extra_dims": {"fat_level": "semi"}},
    "milk_lowfat":{"base_key": "lait_vache", "name_fr": "Lait de vache",
                   "name_en": "Cow milk", "extra_dims": {"fat_level": "low_fat"}},

    # =========================================================================
    # USDA — FLOUR
    # =========================================================================
    "flour_wheat": {"base_key": "farine_de_ble", "name_fr": "Farine de blé",
                    "name_en": "Wheat flour", "extra_dims": {}},
    "flour_whole": {"base_key": "farine_de_ble", "name_fr": "Farine de blé",
                    "name_en": "Wheat flour", "extra_dims": {"variety": "complet"}},
    "flour_rice":  {"base_key": "farine_de_riz", "name_fr": "Farine de riz",
                    "name_en": "Rice flour", "extra_dims": {}},

    # =========================================================================
    # USDA — TOMATOES / PEPPERS / ONIONS / MUSHROOMS
    # =========================================================================
    "tomatoes_grape": {"base_key": "tomate", "name_fr": "Tomate", "name_en": "Tomato",
                       "extra_dims": {"variety": "cerise"}},
    "tomatoes_red":   {"base_key": "tomate", "name_fr": "Tomate", "name_en": "Tomato",
                       "extra_dims": {"variety": "rouge"}},
    "peppers_bell":     {"base_key": "poivron", "name_fr": "Poivron", "name_en": "Bell pepper",
                         "extra_dims": {}},
    "peppers_banana":   {"base_key": "poivron", "name_fr": "Poivron", "name_en": "Bell pepper",
                         "extra_dims": {"variety": "banane"}},
    "peppers_jalapeno": {"base_key": "piment", "name_fr": "Piment", "name_en": "Chili pepper",
                         "extra_dims": {"variety": "jalapeno"}},
    "peppers_poblano":  {"base_key": "piment", "name_fr": "Piment", "name_en": "Chili pepper",
                         "extra_dims": {"variety": "poblano"}},
    "onions_red":    {"base_key": "oignon", "name_fr": "Oignon", "name_en": "Onion",
                      "extra_dims": {"variety": "rouge"}},
    "onions_yellow": {"base_key": "oignon", "name_fr": "Oignon", "name_en": "Onion",
                      "extra_dims": {"variety": "jaune"}},
    "onions_white":  {"base_key": "oignon", "name_fr": "Oignon", "name_en": "Onion",
                      "extra_dims": {"variety": "blanc"}},
    "mushroom_portabella": {"base_key": "champignon", "name_fr": "Champignon",
                            "name_en": "Mushroom", "extra_dims": {"variety": "portobello"}},
    "mushroom_oyster":     {"base_key": "champignon", "name_fr": "Champignon",
                            "name_en": "Mushroom", "extra_dims": {"variety": "pleurote"}},
    "mushroom_shiitake":   {"base_key": "champignon", "name_fr": "Champignon",
                            "name_en": "Mushroom", "extra_dims": {"variety": "shiitake"}},
    "mushrooms_shiitake":  {"base_key": "champignon", "name_fr": "Champignon",
                            "name_en": "Mushroom", "extra_dims": {"variety": "shiitake"}},
    "mushrooms_white":     {"base_key": "champignon", "name_fr": "Champignon",
                            "name_en": "Mushroom", "extra_dims": {"variety": "blanc"}},

    # =========================================================================
    # CNF — BEANS
    # =========================================================================
    "beans_kidney": {"base_key": "haricot", "name_fr": "Haricot", "name_en": "Bean",
                     "extra_dims": {"variety": "rouge"}},
    # beans_navy / beans_mung / beans_lima already defined above (USDA)

    # =========================================================================
    # CNF — POTATO
    # =========================================================================
    "potato_boiled": {"base_key": "pomme_de_terre", "name_fr": "Pomme de terre",
                      "name_en": "Potato", "extra_dims": {}},
    "potato_mashed": {"base_key": "pomme_de_terre", "name_fr": "Pomme de terre",
                      "name_en": "Potato", "extra_dims": {"physical_form": "mashed"}},

    # =========================================================================
    # CNF — CABBAGE / LETTUCE / ONION / BUTTER / CREAM
    # =========================================================================
    "cabbage_red":     {"base_key": "chou", "name_fr": "Chou", "name_en": "Cabbage",
                        "extra_dims": {"variety": "rouge"}},
    "cabbage_savoy":   {"base_key": "chou", "name_fr": "Chou", "name_en": "Cabbage",
                        "extra_dims": {"variety": "savoie"}},
    "cabbage_chinese": {"base_key": "chou_chinois", "name_fr": "Chou chinois",
                        "name_en": "Chinese cabbage", "extra_dims": {}},
    "lettuce_butterhead": {"base_key": "laitue", "name_fr": "Laitue", "name_en": "Lettuce",
                           "extra_dims": {"variety": "beurre"}},
    "lettuce_cos":         {"base_key": "laitue", "name_fr": "Laitue", "name_en": "Lettuce",
                            "extra_dims": {"variety": "romaine"}},
    "lettuce_looseleaf":   {"base_key": "laitue", "name_fr": "Laitue", "name_en": "Lettuce",
                            "extra_dims": {"variety": "feuilles"}},
    "lettuce_iceberg":     {"base_key": "laitue", "name_fr": "Laitue", "name_en": "Lettuce",
                            "extra_dims": {"variety": "iceberg"}},
    "onion_spring": {"base_key": "oignon", "name_fr": "Oignon", "name_en": "Onion",
                     "extra_dims": {"variety": "nouveau"}},
    "butter_unsalted": {"base_key": "beurre", "name_fr": "Beurre", "name_en": "Butter",
                        "extra_dims": {"variety": "non_sale"}},
    "butter_regular":  {"base_key": "beurre", "name_fr": "Beurre", "name_en": "Butter",
                        "extra_dims": {}},
    "butter_light":    {"base_key": "beurre", "name_fr": "Beurre", "name_en": "Butter",
                        "extra_dims": {"fat_level": "light"}},
    "butter_whipped":  {"base_key": "beurre", "name_fr": "Beurre", "name_en": "Butter",
                        "extra_dims": {"physical_form": "whipped"}},
    "cream_table":    {"base_key": "creme", "name_fr": "Crème", "name_en": "Cream",
                       "extra_dims": {"fat_level": "table"}},
    "cream_whipping": {"base_key": "creme", "name_fr": "Crème", "name_en": "Cream",
                       "extra_dims": {"fat_level": "whipping"}},
    "cream_sour":     {"base_key": "creme", "name_fr": "Crème", "name_en": "Cream",
                       "extra_dims": {"variety": "sour"}},
}


# ============================================================================
# 10. NUTRIENT_PRECISION + round_nutrients
# ============================================================================

NUTRIENT_PRECISION: dict[str, int] = {
    # Énergie
    "kcal":                  1,
    "kj":                    0,
    # Macros (g/100g)
    "water_g":               1,
    "protein_g":             2,
    "fat_g":                 2,
    "carbs_g":               2,
    "fiber_g":               1,
    "alcohol_g":             2,
    "ash_g":                 2,
    # Lipides (g)
    "saturated_g":           2,
    "monounsaturated_g":     2,
    "polyunsaturated_g":     2,
    "omega3_g":              3,
    "omega6_g":              3,
    "trans_g":               3,
    "cholesterol_mg":        1,
    # Acides gras détaillés (g)
    "fa_4_0_g":              3,
    "fa_6_0_g":              3,
    "fa_8_0_g":              3,
    "fa_10_0_g":             3,
    "fa_12_0_g":             3,
    "fa_14_0_g":             3,
    "fa_16_0_g":             3,
    "fa_18_0_g":             3,
    "fa_18_1_oleic_g":       3,
    "fa_18_2_linoleic_g":    3,
    "fa_18_3_ala_g":         3,
    "fa_20_4_ara_g":         3,
    "fa_20_5_epa_g":         3,
    "fa_22_6_dha_g":         3,
    # Glucides détail (g)
    "sugars_g":              2,
    "starch_g":              2,
    "polyols_g":             2,
    "fructose_g":            2,
    "galactose_g":           2,
    "glucose_g":             2,
    "lactose_g":             2,
    "maltose_g":             2,
    "saccharose_g":          2,
    # Acides aminés (mg)
    "histidine_mg":          1,
    "isoleucine_mg":         1,
    "leucine_mg":            1,
    "lysine_mg":             1,
    "methionine_mg":         1,
    "phenylalanine_mg":      1,
    "threonine_mg":          1,
    "tryptophan_mg":         1,
    "valine_mg":             1,
    # Vitamines liposolubles (mcg)
    "a_rae_mcg":             1,
    "retinol_mcg":           1,
    "beta_carotene_mcg":     1,
    "d_mcg":                 2,
    "d2_mcg":                2,
    "d3_mcg":                2,
    "e_mg":                  2,
    "e_alpha_tocopherol_mg": 2,
    "k1_mcg":                2,
    "k2_mcg":                2,
    # Vitamines hydrosolubles (mg)
    "c_mg":                  1,
    "b1_mg":                 3,
    "b2_mg":                 3,
    "b3_mg":                 2,
    "b5_mg":                 3,
    "b6_mg":                 3,
    "b9_mcg":                1,
    "b9_dfe_mcg":            1,
    "b9_intrinsic_mcg":      1,
    "b9_folic_mcg":          1,
    "b12_mcg":               3,
    "choline_mg":            1,
    "biotin_mcg":            2,
    # Minéraux majeurs (mg)
    "calcium_mg":            1,
    "phosphorus_mg":         1,
    "potassium_mg":          1,
    "sodium_mg":             1,
    "magnesium_mg":          1,
    "chloride_mg":           1,
    # Oligo-éléments (mg)
    "iron_mg":               2,
    "zinc_mg":               2,
    "copper_mg":             3,
    "manganese_mg":          3,
    # Oligo-éléments (mcg)
    "selenium_mcg":          1,
    "iodine_mcg":            1,
    "chromium_mcg":          1,
    "molybdenum_mcg":        1,
    # Bioactifs
    "lycopene_mcg":          1,
    "lutein_mcg":            1,
    "phytosterols_mg":       1,
    "organic_acids_g":       2,
}


def round_nutrients(nutrients: dict) -> dict:
    """
    Applique les arrondis NUTRIENT_PRECISION sur l'objet nutrients imbriqué.
    Traverse récursivement toutes les clés.
    Les valeurs None restent None. Les clés inconnues restent inchangées.
    """
    def _round_value(key: str, val):
        if val is None:
            return None
        if not isinstance(val, (int, float)):
            return val
        precision = NUTRIENT_PRECISION.get(key)
        if precision is None:
            return val
        return round(float(val), precision)

    def _round_dict(d: dict) -> dict:
        result = {}
        for k, v in d.items():
            if isinstance(v, dict):
                result[k] = _round_dict(v)
            elif k.startswith("_"):
                result[k] = v  # _nutrient_meta etc. : ne pas toucher
            else:
                result[k] = _round_value(k, v)
        return result

    return _round_dict(nutrients)


# ============================================================================
# 11. detect_extra_dimensions
# ============================================================================

def detect_extra_dimensions(group_key: str) -> dict:
    """
    Retourne les extra_dims associées à ce group_key depuis BASE_INGREDIENT_MAP.
    Si absent : retourne {}.
    Ces dimensions sont injectées dans le state de chaque food AVANT construction
    de l'arbre, pour que build_variant_tree puisse les utiliser comme axes.
    """
    entry = BASE_INGREDIENT_MAP.get(group_key, {})
    return entry.get("extra_dims", {})


# ============================================================================
# 12. build_variant_tree + helpers
# ============================================================================

DIM_PRIORITY: list[str] = [
    "species", "variety", "cocoa_pct", "part",
    "dairy_process", "fat_level",
    "process.level1", "process.level2",
    "physical_form", "preservation",
]


def get_dim_value(state: dict, dim: str):
    """Extrait la valeur d'une dimension depuis le state.
    Cherche d'abord dans les champs core, puis dans state['extensions'] (Q11:c).
    """
    if dim == "process.level1":
        return state.get("process", {}).get("level1")
    elif dim == "process.level2":
        return state.get("process", {}).get("level2")
    elif dim in _EXTENSION_FIELDS:
        # Champ migré dans extensions
        ext = state.get("extensions") or {}
        val = ext.get(dim)
        if dim == "variety" and isinstance(val, dict):
            return val.get("color") or val.get("cultivar") or None
        return val
    else:
        val = state.get(dim)
        if dim == "variety" and isinstance(val, dict):
            return val.get("color") or val.get("cultivar") or None
        return val


def _leaf_key(food: dict) -> str:
    """Clé d'un leaf dans children : process.level2 > process.level1 > 'base'."""
    proc = food.get("state", {}).get("process", {})
    l2 = proc.get("level2")
    l1 = proc.get("level1")
    return l2 or l1 or "base"


def _make_leaf(food: dict, dimension: str) -> dict:
    """Construit un nœud leaf depuis un food dict."""
    return {
        "type":         "leaf",
        "dimension":    dimension,
        "value":        _leaf_key(food),
        "state":        food["state"],
        "source_id":    food.get("id") or food.get("food_id"),
        "source_label": food.get("name_fr") or food.get("name_en"),
        "nutrients":    round_nutrients(food["nutrients"]),
        "diet_profile": food.get("diet_profile", {}),
        "_quality":     food.get("_quality"),
        "children":     {},
    }


def remaining_dims_after(dim: str, priority: list[str]) -> list[str]:
    """Retourne la liste des dimensions après `dim` dans la priorité."""
    try:
        idx = priority.index(dim)
    except ValueError:
        return []
    # process.level2 ne peut venir qu'après process.level1
    remaining = priority[idx + 1:]
    if dim == "process.level2":
        # rien après level2 dans l'ordre process
        remaining = [d for d in remaining if d != "process.level1"]
    return remaining


def _build_tree_recursive(
    foods: list[dict],
    priority: list[str],
    depth: int,
) -> dict:
    """Construction récursive de l'arbre node/leaf."""
    if not foods:
        return {}

    # Trouver la première dimension discriminante (≥ 2 valeurs distinctes non-null)
    for dim in priority:
        values_all     = [get_dim_value(f["state"], dim) for f in foods]
        values_notnull = {v for v in values_all if v is not None}

        if len(values_notnull) < 2:
            # Dimension non discriminante — passer à la suivante
            continue

        # Ce niveau est discriminant → créer des enfants
        children: dict = {}
        rem = remaining_dims_after(dim, priority)

        for val in sorted(values_notnull, key=str):
            group = [f for f in foods if get_dim_value(f["state"], dim) == val]
            sub = _build_tree_recursive(group, rem, depth + 1)

            # Règle cardinalité : node avec 1 seul enfant leaf → aplatir
            # Le leaf qui remonte hérite de la dimension de CE niveau
            if len(sub) == 1 and list(sub.values())[0]["type"] == "leaf":
                leaf = dict(list(sub.values())[0])   # copie peu profonde
                leaf["dimension"] = dim               # dimension du parent
                children[str(val)] = leaf
            elif sub:
                children[str(val)] = {
                    "type":         "node",
                    "dimension":    dim,
                    "value":        str(val),
                    "nutrients":    None,
                    "diet_profile": None,
                    "source_id":    None,
                    "source_label": None,
                    "_quality":     None,
                    "children":     sub,
                }
            # sub vide → ne rien ajouter

        # Foods avec valeur null pour cette dim → sous-arbre indépendant
        nulls = [f for f in foods if get_dim_value(f["state"], dim) is None]
        if nulls:
            sub_null = _build_tree_recursive(nulls, rem, depth + 1)
            children.update(sub_null)

        return children

    # Aucune dimension discriminante → tous les foods sont des leaves
    # dimension = "base" (aucune facette n'a discriminé à ce niveau)
    if len(foods) == 1:
        f = foods[0]
        return {_leaf_key(f): _make_leaf(f, "base")}

    # Cas conflit : plusieurs foods, aucune dimension ne les distingue
    # → leaves avec suffixe _2, _3… pour rétrocompat
    result: dict = {}
    for f in foods:
        key = _leaf_key(f)
        if key in result:
            j = 2
            while f"{key}_{j}" in result:
                j += 1
            key = f"{key}_{j}"
        result[key] = _make_leaf(f, "base")
    return result


def _count_leaves(variants: dict) -> int:
    """Compte récursivement les leaves dans l'arbre."""
    count = 0
    for node in variants.values():
        if node.get("type") == "leaf":
            count += 1
        elif node.get("type") == "node":
            count += _count_leaves(node.get("children", {}))
    return count


def _count_nodes(variants: dict) -> int:
    """Compte récursivement les nodes dans l'arbre."""
    count = 0
    for node in variants.values():
        if node.get("type") == "node":
            count += 1 + _count_nodes(node.get("children", {}))
    return count


def _collect_dims_used(variants: dict, acc: list | None = None) -> list[str]:
    """Collecte les dimensions effectivement utilisées dans l'arbre."""
    if acc is None:
        acc = []
    for node in variants.values():
        if node.get("type") == "node":
            dim = node.get("dimension")
            if dim and dim not in acc:
                acc.append(dim)
            _collect_dims_used(node.get("children", {}), acc)
        elif node.get("type") == "leaf":
            dim = node.get("dimension")
            if dim and dim not in acc and dim != "base":
                acc.append(dim)
    return acc


def build_variant_tree(
    foods: list[dict],
    base_key: str,
    name_fr: str | None,
    name_en: str | None,
    category: dict,
    source_name: str,
    extra_fields: dict | None = None,
) -> dict:
    """
    Construit le groupe complet (arbre node/leaf) depuis une liste de food dicts.

    Params :
        foods        : liste des food dicts partageant le même base_key
        base_key     : slug de l'ingrédient de base
        name_fr      : nom FR usuel (sans état)
        name_en      : nom EN usuel ou None
        category     : dict categorie unifié
        source_name  : "ciqual" | "usda" | "cnf"
        extra_fields : champs additionnels source-spécifiques (ex: taxonomy CNF)

    Retourne le dict groupe complet incluant "variants" (arbre), "_meta", etc.
    """
    # 1. Injecter les extra_dims dans le state de chaque food (merge non-destructif)
    for food in foods:
        extra_dims = detect_extra_dimensions(food.get("group_key", ""))
        for dim, val in extra_dims.items():
            if dim in ("process.level1", "process.level2"):
                continue  # jamais overrider le process
            if dim in _EXTENSION_FIELDS:
                # Champ migré dans extensions (Q11:c)
                ext = food["state"].setdefault("extensions", {}) or {}
                food["state"]["extensions"] = food["state"].get("extensions") or {}
                if food["state"]["extensions"].get(dim) is None:
                    food["state"]["extensions"][dim] = val
            else:
                if food["state"].get(dim) is None:
                    food["state"][dim] = val

    # 2. Construire l'arbre récursivement
    variants = _build_tree_recursive(foods, DIM_PRIORITY, depth=0)

    # 3. Calculer _meta
    leaf_count  = _count_leaves(variants)
    node_count  = _count_nodes(variants)
    dims_used   = _collect_dims_used(variants)
    source_gks  = sorted(set(f.get("group_key", base_key) for f in foods))

    # 4. Construire le groupe
    group: dict = {
        "base_key": base_key,
        "name_fr":  name_fr,
        "name_en":  name_en,
        "category": category,
        "sources":  [source_name],
    }
    if extra_fields:
        group.update(extra_fields)
    group["_meta"] = {
        "leaf_count":        leaf_count,
        "node_count":        node_count,
        "dimensions_used":   dims_used,
        "source_group_keys": source_gks,
    }
    group["variants"] = variants

    return group
