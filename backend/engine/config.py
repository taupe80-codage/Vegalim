"""
Configuration centralisée des chemins — ALIM_PROJECT_UNIFIED.
Tous les engines importent DATA_ROOT depuis ce fichier.
Fonctionne quel que soit le répertoire de lancement.
"""
from pathlib import Path

# Racine du projet = dossier parent de backend/
_ENGINE_DIR  = Path(__file__).resolve().parent          # backend/engine/
_BACKEND_DIR = _ENGINE_DIR.parent                       # backend/
PROJECT_ROOT = _BACKEND_DIR.parent                      # ALIM_PROJECT_UNIFIED/

DATA_ROOT = Path(__file__).resolve().parents[2] / "backend/data"

# Chemins fréquemment utilisés
RECIPES_PATH       = DATA_ROOT / "recipes"     / "recipes.json"
DICT_PATH          = DATA_ROOT / "ingredients" / "ingredients_dictionary.json"
NUTRITION_PATH     = DATA_ROOT / "nutrition"   / "processed" / "nutrition_v2.json"   # source CIQUAL/USDA nettoyée
NUTRITION_RAW_PATH = DATA_ROOT / "nutrition"   / "raw"       # sources brutes — ne pas charger au runtime
FR_TO_EN_PATH      = DATA_ROOT / "ingredients" / "fr_to_en_mapping.json"
PHYSICAL_PATH      = DATA_ROOT / "ingredients" / "ingredient_physical.json"
GRAPHS_PATH        = DATA_ROOT / "graphs"
MODULES_PATH       = DATA_ROOT / "modules"
INDEXES_PATH       = DATA_ROOT / "indexes"
USER_PROFILES_PATH = DATA_ROOT / "user_profiles"
PRODUCT_PATH       = DATA_ROOT / "product"    # runtime : users, api_keys, quotas, analytics


# ── Constantes métier centralisées ────────────────────────────────────────────
# Ces valeurs sont importées par les engines concernés.
# Ne pas les redéfinir localement — modifier uniquement ici.

# Friture (nutrition_engine)
FRYING_CAP_G = 20          # Huile absorbée max en friture (grammes)

# Pondération scoring CDC_03c (recommendation_engine)
W_QUALITY    = 0.65        # Poids score qualité 7 dimensions
W_RELEVANCE  = 0.35        # Poids pertinence recherche

# Learning engine
MIN_LIKES_TO_ACTIVATE = 5  # Likes minimum pour activer la personnalisation
MAX_LEARNING_BONUS    = 2.0 # Bonus/malus max learning (±)

# Score reliability (score_reliability_engine)
RELIABILITY_HIGH   = 0.80  # ≥80% ingrédients avec données CIQUAL → 🟢
RELIABILITY_MEDIUM = 0.50  # 50-79% → 🟡   <50% → 🔴

# Servings (servings_engine)
SERVINGS_DEFAULT = 4
SERVINGS_MIN     = 1
SERVINGS_MAX     = 20
# Seuils explainer CDC_03c (score_engine/explainer.py)
# hi : seuil au-dessus duquel le label positif est affiché
# lo : seuil en-dessous duquel le label négatif est affiché
# Si les poids ou l'échelle du scoring changent, ajuster ici uniquement.
EXPLAINER_HI_NUTRITION     = 7.5
EXPLAINER_LO_NUTRITION     = 4.0
EXPLAINER_HI_AUTHENTICITY  = 7.0
EXPLAINER_HI_ACCESSIBILITY = 7.5
EXPLAINER_LO_ACCESSIBILITY = 4.0
EXPLAINER_HI_COST          = 7.5
EXPLAINER_LO_COST          = 4.0
EXPLAINER_HI_EASE          = 7.5
EXPLAINER_LO_EASE          = 4.0
EXPLAINER_HI_CARBON        = 7.5
EXPLAINER_LO_CARBON        = 4.0
EXPLAINER_HI_FLAVOR        = 7.0
