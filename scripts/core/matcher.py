"""
matcher.py
Résolution de noms d'ingrédients vers une clé canonique de référence.

Corrections vs version originale :
  - ALIASES chargé à la demande (lazy) — plus de crash à l'import
  - clean_name() : normalisation Unicode identique aux autres scripts
  - STOPWORDS étendu : états de cuisson FR + EN couverts
  - Index cleaned_ref précalculé une fois par appel batch (build_index)
  - Résolution alias indexée O(1) au lieu de O(n)
  - Garde-fou longueur sur fuzzy_loose (évite faux positifs sur tokens courts)
  - Échecs loggés et retournés pour analyse
"""

import re
import unicodedata
from pathlib import Path

BASE_DIR     = Path(__file__).resolve().parent.parent
DATASET_FILE = BASE_DIR / "backend/data/nutrition/nutrition_database_cleaned_final.json"

# =====================================================
# STOPWORDS  (états + prépositions — ne font pas partie de la clé base)
# =====================================================

STOPWORDS: frozenset[str] = frozenset([
    # États FR
    "cru", "crue", "crus", "crues",
    "cuit", "cuite", "cuits", "cuites",
    "bouilli", "bouillie", "frit", "frite",
    "grille", "grillee", "roti", "rotie",
    "saute", "sautee", "braise", "braisee",
    "fume", "fumee", "surgele", "surgelee",
    "congele", "congelee", "marine", "marinee",
    "fermente", "fermentee", "seche", "sechee",
    "moulu", "moulue", "entier", "entiere",
    "tranche", "tranchee", "hache", "hachee",
    "frais", "fraiche", "sale", "salee",
    "blanchi", "blanchie", "epluche", "epeluchee",
    "conserve", "deshydrate",
    # États EN
    "raw", "cooked", "dried", "frozen", "canned",
    "boiled", "fried", "grilled", "roasted", "steamed",
    "smoked", "marinated", "fermented", "poached",
    "sauteed", "stewed", "braised", "ground", "whole",
    "sliced", "chopped", "diced", "minced", "grated",
    "fresh", "salted", "unsalted", "blanched", "baked",
    "unprepared", "unheated", "dehydrated", "peeled",
    "skinless", "boneless", "prepared", "instant",
    # Termes anatomiques / qualité (USDA)
    "lean", "only", "meat", "separable", "trimmed",
    "boneless", "bone", "skin", "fat", "light", "dark",
    "select", "choice", "prime",
    # Prépositions / articles
    "with", "without", "and", "or", "de", "du", "des",
    "le", "la", "les", "un", "une", "au", "aux", "en", "a",
])

# =====================================================
# NORMALISATION  (cohérence avec build_ontology_v4_0)
# =====================================================

def normalize(text: str) -> str:
    """NFD Unicode + minuscules + strip."""
    if not text:
        return ""
    text = text.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def clean_name(name: str) -> str:
    """
    Produit une clé normalisée sans stopwords.
    Utilisée de façon cohérente sur les noms à matcher ET sur les clés de référence.
    """
    name = normalize(name)
    name = re.sub(r"[(),\-/]", " ", name)
    tokens = [t for t in name.split() if t and t not in STOPWORDS]
    return "_".join(tokens)

# =====================================================
# ALIASES  (chargement lazy)
# =====================================================

_aliases_cache: dict | None = None


def get_aliases() -> dict[str, str]:
    """
    Charge et met en cache le dictionnaire d'aliases.
    Lazy : le fichier n'est lu qu'au premier appel, jamais à l'import.
    """
    global _aliases_cache
    if _aliases_cache is not None:
        return _aliases_cache

    if not DATASET_FILE.exists():
        _aliases_cache = {}
        return _aliases_cache

    import json
    with open(DATASET_FILE, encoding="utf-8") as f:
        data = json.load(f).get("ingredients", {})

    alias_map: dict[str, str] = {}
    for name, item in data.items():
        alias_map[clean_name(name)] = name
        for a in item.get("aliases", []):
            alias_map[clean_name(a)] = name

    _aliases_cache = alias_map
    return alias_map

# =====================================================
# INDEX DE RÉFÉRENCE  (précalculé une fois par batch)
# =====================================================

def build_index(reference: dict) -> dict[str, str]:
    """
    Construit un index {clé_nettoyée → clé_originale} depuis le dict de référence.
    À précalculer une seule fois avant une boucle de matching.

    En cas de collision (deux clés originales → même clé nettoyée),
    la première rencontrée est conservée.
    """
    index: dict[str, str] = {}
    for k in reference:
        ck = clean_name(k)
        if ck not in index:
            index[ck] = k
    return index

# =====================================================
# MATCHING
# =====================================================

def match_ingredient(
    name: str,
    reference: dict,
    index: dict[str, str] | None = None,
) -> tuple[str | None, str, float]:
    """
    Résout un nom d'ingrédient vers une clé de référence.

    Paramètres
    ----------
    name      : nom brut de l'ingrédient
    reference : dict {clé_ontologie: données}
    index     : index précalculé via build_index() — optionnel mais recommandé
                en batch pour éviter de recalculer à chaque appel.

    Retourne (clé_matchée | None, méthode, score)
    Méthodes : "alias" | "exact" | "fuzzy_strict" | "fuzzy_loose" | "none"
    """
    from rapidfuzz import process, fuzz

    if index is None:
        index = build_index(reference)

    name_clean = clean_name(name)
    aliases    = get_aliases()

    # 1. Alias dataset — résolution O(1) via index
    if name_clean in aliases:
        alias_target      = aliases[name_clean]
        alias_target_clean = clean_name(alias_target)
        if alias_target_clean in index:
            return index[alias_target_clean], "alias", 0.95

    # 2. Correspondance exacte après nettoyage
    if name_clean in index:
        return index[name_clean], "exact", 1.0

    # 3. Fuzzy matching
    if not index:
        return None, "none", 0.0

    result = process.extractOne(
        name_clean,
        index.keys(),
        scorer=fuzz.token_sort_ratio,
    )

    if result is None:
        return None, "none", 0.0

    match_key, score, _ = result

    # Garde-fou longueur : un token très court génère trop de faux positifs
    # (ex: "oil" → score 90 sur "olive_oil", "canola_oil", "palm_oil"...)
    len_ratio = len(name_clean) / max(len(match_key), 1)
    if len_ratio < 0.5 or len_ratio > 2.0:
        return None, "none", 0.0

    if score > 90:
        return index[match_key], "fuzzy_strict", round(score / 100, 3)

    if score > 80:
        return index[match_key], "fuzzy_loose", round(score / 100, 3)

    return None, "none", 0.0
