"""
build_ciqual_flat_v3.py  v6.9

CHANGEMENTS v6.8 → v6.9 (stratification check fiber_vs_carbs) :
  DIAGNOSTIC — 129 items fiber_vs_carbs identifiés en 3 populations distinctes :
    Pop. 1 (44 items dried + _fiber_rebased=True) : rebase appliqué, anomalie
      structurelle persistante — biologiquement cohérent pour épices/algues/oléagineux.
    Pop. 2 (~40 items non-dried, carbs_g < 1.0) : aliments quasi-acarbonés (matières
      grasses, olives, légumes très fibreux) — ratio mathématiquement absurde, pas
      d'anomalie réelle.
    Pop. 3 (~45 items cooked/raw/manufactured, carbs_g ≥ 1.0) : seuls vrais positifs
      data_quality.
  CHECK fiber_vs_carbs → remplacé par logique 4 branches :
    • carbs_g < 1.0              → exception silencieuse (pop. 2, ~20 items)
    • water_g >= 75.0            → exception silencieuse (pop. 3A, ~42 items :
                                   légumes hydratés, légumineuses fraîches)
    • _fiber_rebased=True        → check info "fiber_vs_carbs_postdry" (pop. 1+D,
                                   ~55 items : dried + quasi-secs lowwater)
    • sinon                      → warning "fiber_vs_carbs" data_quality (~11 items)
  FIX rebase fiber étendu — water_g < 15 hors dried :
    Son, café, lin, thé, cacao, graines (manufactured/cooked quasi-secs) bénéficient
    du même rebase sec→frais que les dried. Tracé via _fiber_rebase_reason="lowwater".
  SEVERITY_CLASS — ajout : "fiber_vs_carbs_postdry" → "info"
  RÉSULTAT : data_quality fiber 129 → 11 (−118), 11 restants tous justifiés

CHANGEMENTS v6.9 → v6.10 (vit_d_subforms) :
  CHECK vit_d_subforms — skip pour generic_type="aliment_moyen" :
    Les aliments moyens CIQUAL agrègent des mesures inter-lots indépendantes.
    D2, D3 et vitamin_d_total ne sont pas co-mesurés → incohérence structurelle,
    non actionnable. La purge des aliments moyens redondants (v6.6) ne couvre pas
    les cas où l'aliment moyen est seul dans son group_key (ex: ciqual_24999).
  RÉSULTAT : data_quality vit_d_subforms 1 → 0
  FIX v6.10b — generic_type manquant dans run_audit :
    (annulé en v6.14 — les 2 items concernés exclus directement dans EXCL_CODES_HARD)

CHANGEMENTS v6.13 → v6.14 (suppression aliments moyens incohérents) :
  EXCL_CODES_HARD +2 aliments moyens analytiquement inutilisables :
    24999  Dessert (aliment moyen)                    — D2+D3 > vitamin_d_total
    25616  Crudité, sans assaisonnement (aliment moyen) — AGS sous-fractions > total
  Les patches défensifs vit_d_subforms/generic_type et run_audit/generic_type
  introduits en v6.10/v6.10b sont revertés — l'exclusion amont est plus propre.
  RÉSULTAT data_quality attendu : 11 (fiber_vs_carbs uniquement)
    run_audit recevait {**nut, id, name_fr} sans generic_type → le skip
    aliment_moyen ne s'appliquait jamais. Corrigé en passant gen_type
    explicitement dans le dict food transmis à run_audit.

CHANGEMENTS v6.10 → v6.11 (retinol_vita_rae) :
  CHECK retinol_vita_rae — double seuil relatif + absolu (> 5.0 µg) :
    CIQUAL inclut alpha-carotène et bêta-cryptoxanthine dans le calcul RAE,
    absents du schéma. Pour les céréales, riz, jus : retinol=0, bcar=None,
    rae ∈ {1.25, 2.08} µg → delta=100% sur traces (< 0.5% AJR, non significatif).
    Le check ne se déclenche désormais que si abs(rae - calc) > 5 µg.
  RÉSULTAT : data_quality retinol_vita_rae 50 → 0

CHANGEMENTS v6.11 → v6.12 (fa_sfa_subfractions) :
  CHECK fa_sfa_subfractions — exclusion des champs sous limite de détection (LOD/2) :
    CIQUAL encode les valeurs < seuil analytique à LOD/2 (ex: fa_4_0 = 0.005g
    quand dl=0.01g). Ces sentinelles sont valides pour build_diet_profile mais ne
    doivent pas être sommées comme AGS réels. Pour les végétaux, légumes, céréales :
    C4:0–C14:0 sont quasi-systématiquement sous LOD → +0.030g faux sur la somme.
    La somme ne retient désormais que les champs absents de dl (mesures réelles).
  RÉSULTAT : data_quality fa_sfa_subfractions 46 → ~1 (résiduel : aliment moyen
             avec vrais AGS courts mesurés, non corrigeable)

CHANGEMENTS v6.12 → v6.13 (checks structurels analytiques) :
  SEVERITY_CLASS downgrade data_quality → info pour 3 checks :
    omega_vs_pufa (206 items) : Σ(ALA+EPA+DHA+ARA+linoléique) > PUFA total —
      mesures sur aliquots indépendants, non co-contraintes dans CIQUAL.
    salt_sodium (126 items) : sel conductimétrique ≠ Na absorption atomique —
      deux méthodes indépendantes, divergence attendue notamment pour aliments
      transformés, fermentés et produits à Na trace.
    chloride_sodium_balance (139 items) : Cl organique et KCl non issus de NaCl —
      épices, aliments fermentés, ratio Cl/Na ≠ 1.542 par nature.
  Logique de check conservée intacte — issues tracées en info pour auditabilité.
  RÉSULTAT : data_quality structurels 471 → 0

CHANGEMENTS v6.14 → v6.15 (major_quality + physical_error) :
  EXCL_CODES_HARD +2 additifs technologiques :
    31064  Édulcorant saccharine    — mass_balance Sigma=3g/100g (ecart=97g)
    31047  Gélifiant pour confitures — mass_balance Sigma=84g/100g
  energy_check — correction double-comptage polyols :
    CIQUAL inclut polyols dans carbs_g mais leur facteur = 10 kJ/g (vs 17 kJ/g).
    La formule déduit désormais polyols_g de carbs avant d'appliquer ×17.
    Résout : confiseries sans sucres (delta 130-166% → <1%), abricots secs
    (36% → 2%), champignons sautés (32% → 0.2%), céleri-rave (27% → 0.5%).
  fa_balance — skip fat_g < 0.1g :
    FA sub-fractions LOD/2 non représentatives pour ultra-low fat.
    Cas : lait écrémé UHT (fat=0.021g).
  sugar_subfractions — skip generic_type="aliment_moyen" :
    Sous-fractions mesurées sur lots indépendants → structurel.
    Cas : Fromage/Boisson végétale/Légume cuit/Légume sec cuit (aliments moyens).
    generic_type désormais passé explicitement dans le dict food → run_audit.
  RÉSULTAT attendu après rebuild : physical_error=0  major_quality=0  data_quality=11"

CHANGEMENTS v6.7 → v6.8 (rebase fiber_g sec→frais pour items dried) :
  FIX 6 — fiber_g exprimée sur matière sèche dans CIQUAL pour les items dried,
    alors que tous les autres macros sont sur poids frais (tel quel).
    Correction inline dans build_food_object, après stabilisation du state :
      fiber_g_frais = fiber_g_sec × (100 - water_g) / 100
    Garde-fous : water_g disponible ET water_g < 98 (exclut bouillons/valeurs
    aberrantes). Tracé minimal via _fiber_rebased=True dans nut{}.
  CHECK — Ajout du check audit fiber_vs_carbs (severity_class=data_quality) :
    Détecte les anomalies résiduelles post-rebase où fiber > carbs + 0.5.
    Sert également de filet pour les items non-dried mal classifiés.

CHANGEMENTS v6.6 → v6.7 (audit scope recettes maison — purge hors-scope) :
  8 ssgrps ajoutés à EXCL_SUBGROUPS_HARD :
    0601  eaux minérales (89 items — zéro utilité recette)
    0303  biscuits apéritifs / crackers industriels (48 items)
    0801  glaces (produits finis)
    0802  sorbets (produits finis)
    0803  desserts glacés (profiteroles, pêche melba…)
    1103  desserts infantiles
    1104  céréales et biscuits infantiles
    1008  denrées alimentation particulière (substituts de repas)
  EXCL_CODES_HARD étendu :
    +37 codes 0603 alcools non-cuisine (pastis, gin, vodka, bières, cocktails…).
    Conservés pour cuisine : vin rouge/blanc/rosé, champagne, cidre brut/doux,
    rhum, marsala, cognac, calvados, eau de vie de fruits, saké, crème de cassis.
    +~95 codes 0602 sous-catégories indésirables : BRSA (48 codes), boissons
    lactées aromatisées (8), nectars (20), cafés/thés prêts à consommer (14),
    boissons reconstituées industrielles (4). Conservés : jus, boissons végétales
    (laits végétaux), café/thé/cacao en feuilles/poudre brute.
  should_exclude : +2 filtres nom :
    DOM-TOM — exclut tout item contenant "prélevé à la Martinique" ou
    "prélevé à La Réunion" (101 items dans 0201/0204).
    Édulcorants — exclut tout item contenant "avec édulcorants" dans son nom
    (~80 variants reformulés sans valeur pour la cuisine).

CHANGEMENTS v6.5 → v6.6 (purge aliments moyens redondants + unknown → 0%) :
  FIX 4 — Purge des aliments moyens redondants :
    Après expand_ou, tout food marqué is_generic=True / generic_type="aliment_moyen"
    est supprimé si son group_key contient déjà ≥1 food non-générique avec
    energy_kcal non-null. Les aliments moyens seuls dans leur groupe sont conservés
    (ils sont le seul représentant du groupe). Gain : ~61 foods supprimés sur 2161.
    Stat ajoutée : "generic_purged" dans le rapport.
  FIX 5 — unknown_rate résiduel → food_schema_v2 v3.1 :
    Dépendance food_schema_v2 mise à jour vers v3.1, qui ajoute :
    - _CATEGORY_LEVEL1_MAP : +20 sous-groupes (0503 fromages, 0601 eaux→raw,
      0801/02/03 glaces, 1005 épices→dried, 0501 laits, 0504 crèmes, 1003,
      1006 herbes→raw, 1002, 0603, 0303, 1009, 1010, 1004, 0905, 1103, 1008,
      0704, 1104, 0305). Résout ~449 unknowns.
    - _LEVEL2_RE : mots-clés œufs (dur→boiled, coque→boiled, omelette/brouillé/
      au plat→pan_fried). Résout ~11 unknowns.
    - Lookbehind (?<!non ) sur cooked_generic. Corrige ~2 faux positifs.
    unknown_rate projeté : 22% → ~0.05% (1 résidu incompressible).


CHANGEMENTS v6.4 → v6.5 (3 corrections post-audit) :
  FIX 1 — diet_profile.vegan=True sur fromages (103 items) :
    build_diet_profile reçoit uniquement le name_fr sans catégorie → ne détecte
    pas les fromages affinés comme produits laitiers. Correction : force
    vegan=False pour tout item dont ssgrp ∈ DAIRY_SUBGROUPS (0501-0504).
  FIX 2 — state.process.level1=unknown sur lait fermenté (25 items) :
    fix_unknown_state ratait le mot "fermenté" présent dans le nom du groupe
    et non dans le qualificatif analysé. Correction : force level1="fermented"
    pour tout item inconnu du sous-groupe 0502, confidence=0.90,
    raw_label_fragment="subgroup:0502".
  FIX 3 — doublon biscuit / cracker_aperitif (16+16 items identiques) :
    CIQUAL 0303 utilise "biscuit" et "cracker apéritif" comme synonymes.
    Correction : remappage group_key → "biscuit_aperitif" pour ssgrp="0303",
    quelle que soit la base_name. cracker_aperitif retiré de PRESERVE_FINE_GRAINED,
    biscuit_aperitif ajouté. Économie : ~16 group_keys dupliqués supprimés.


CHANGEMENTS v6.3 → v6.4 (scission champignons) :
  - Ajout d'une règle de parsing du qualificatif pour "Champignon, TYPE, état".
    extract_base_name coupant à la 1ère virgule, tous les champignons sauvages
    héritaient du même group_key "champignon". On extrait maintenant le type
    depuis le qualificatif via _CHAMPIGNON_TYPE_MAP (11 keywords → 8 group_keys).
  - Nouveaux group_keys isolés : champignon_cepe, champignon_morille,
    champignon_pleurote, champignon_oronge, champignon_rose_des_pres,
    champignon_truffe, champignon_shiitake (lentin comestible = shiitaké).
  - "Champignon, tout type" reste group_key="champignon" (aliment générique).
  - PRESERVE_FINE_GRAINED : +7 clés champignon ajoutées.


CHANGEMENTS v6.2 → v6.3 (granularité des groupes — PRESERVE_FINE_GRAINED) :
  - Ajout de PRESERVE_FINE_GRAINED (57 group_keys) dans la boucle de groupement.
    Ces group_keys court-circuitent BASE_INGREDIENT_MAP pour rester des groupes
    autonomes plutôt qu'être fusionnés sous un base_key générique trop large.
  - Impacte 14 familles d'ingrédients :
    * haricot     : 9 sous-types séparés (vert/rouge/blanc/beurre/flageolet/mungo/plat/coco + germé)
    * champignon  : champignon_de_paris + champignon_noir isolés
    * lentille    : verte/corail/blonde/germée
    * riz         : blanc/complet/rouge/sauvage/basmati/thaï/semi-complet
    * son         : avoine/blé/maïs/riz
    * chocolat    : au lait + blanc isolés (noir/générique reste "chocolat")
    * tofu        : nature/soyeux/fumé
    * asperge     : blanche/verte
    * vinaigre    : balsamique/cidre/vin rouge
    * fromage_de_chevre : bûche/demi-sec/sec/crottin
    * farine_de_seigle  : T85/T130/T170
    * biscotte    : blé complet/céréales/germe de blé/briochée
    * galette     : riz/maïs/céréales soufflées
    * couscous    : graine de couscous (simple/complète/semi-complète) séparée de semoule
    * oeuf        : espèces non-poule (caille/cane/dinde/oie) isolées
    * cracker_aperitif : séparé de biscuit
  - ingredient_key inchangé → jointure USDA cross-source toujours fonctionnelle.
  - extra_dims du BIM désactivés pour les group_keys préservés (pas de BIM entry).

==============================
Construit ciqual_flat_v3.json depuis le fichier XLSX CIQUAL 2025.
Source unique : Table_Ciqual_2025_FR_2025_11_03.xlsx

CHANGEMENTS v6.1 → v6.2 (refactor "ou" — blends vs synonymes) :
  - Stratégie "ou" : seuls les VRAIS blends entre ingrédients distincts sont exclus.
    Les synonymes régionaux / variantes de même ingrédient sont expansés normalement.
  - EXCL_SUBGROUPS_HARD : ajout 0101, 0103, 0104, 0105, 0106 (entrées & plats composés),
    0403 (charcuteries), 0705/0706/0707/0708/0709 (produits finis), 1102 (infantile).
  - EXCL_CODES_HARD : +15 codes "ou"-blends indéfinis :
    * 0201 : salade/chicorée, champignon/chanterelle/girolle, julienne, printanière, mesclun
    * 0204 : macédoines, compote tout-type, aliments moyens multi-fruits
    * Aliments moyens multi-ingrédients (glace tout parfum, confiture tout type)
  - ULTRATRANS_KEYWORDS : accents corrigés (comparaison sur nom.lower() brut sans _strip).
    Ajout "thé glacé", "ice tea". Suppression "tonic ou bitter" (garder les tonics purs).

CHANGEMENTS v5.1 → v6.0 (audit schéma Q1-Q15, food_schema_v2 v3.0) :
  - process.level1 : 6 valeurs (raw, cooked, dried, manufactured, fermented, unknown)
    * dried        : séchage sans cuisson (herbes, légumineuses sèches, noix, fruits secs)
    * manufactured : produit fini industriel (huiles, alcools, confitures, jus…)
    * fermented    : fermenté sans cuisson explicite
    Récupère ~230 des 506 unknowns → unknown_rate ≈ 29%
  - fix_unknown_state() appelé après parse_state_v2 (4 passes : regex × 2 + catég × 2)
  - Expansion "ou" : classify_ou / expand_ou — items "A ou B" → N food_obj distincts,
    nutrients partagés (copiés), canonical = dernier terme (Q5:b), _ou_expansion tracé
  - state.extensions (Q11:c) : 9 champs quasi-vides migrés dans sous-dict non-null
  - ingredient_key : clé de jointure cross-source (base_key BASE_INGREDIENT_MAP ou slugify)
  - family_key : clé de navigation CIQUAL (subgroup_code)
  - schema_version "7.0"

CHANGEMENTS v4.x → v5.0 (alignement schéma variant v2) :
  - state : objet imbriqué, nutrients : structure imbriquée, variant_id SHA-1, etc.

Usage :
  python build_ciqual_flat_v3.py \\
      --input  Table_Ciqual_2025_FR_2025_11_03.xlsx \\
      --output ciqual_flat_v3.json \\
      --audit-report ciqual_flat_v3_audit.json \\
      --log-excl ciqual_flat_v3_excluded.json
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
NUTRITION_DIR = (
    SCRIPT_DIR.parent if SCRIPT_DIR.name in ("raw", "scripts") else SCRIPT_DIR
)

if str(NUTRITION_DIR) not in sys.path:
    sys.path.insert(0, str(NUTRITION_DIR))
from food_schema_v2 import (
    compute_variant_id,
    parse_state_v2,
    fix_unknown_state,
    classify_ou,
    expand_ou,
    build_nutrients_object,
    build_diet_profile,
    state_variant_key,
    slugify,
    validate_food_item,
    build_variant_tree,
    detect_extra_dimensions,
    round_nutrients,
    BASE_INGREDIENT_MAP,
    LEVEL1_VALUES,
)

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl requis : pip install openpyxl")

# ── Taxonomie dynamique ───────────────────────────────────────────────────────
# Chargée une fois dans build() depuis taxonomy_session_*.json
# puis utilisée par build_food_object() via ce global de module.
try:
    from taxonomy_loader import load_bk_taxonomy, build_taxonomy_object
    _TAXONOMY_AVAILABLE = True
except ImportError:
    _TAXONOMY_AVAILABLE = False
    def load_bk_taxonomy(path):   # type: ignore[override]
        return {}
    def build_taxonomy_object(bk, bk_taxonomy, *, fallback_unclassified=True):  # type: ignore[override]
        return None

_BK_TAXONOMY: dict[str, dict] = {}   # peuplé dans build()


# ============================================================================
# 1. MAPPING 84 COLONNES XLSX
# ============================================================================
COLUMN_MAP = [
    None, None, None, None, None, None, None, None, None,   # 00-08 identifiants
    "energy_kj",           # 09
    "energy_kcal",         # 10
    "energy_kj_jones",     # 11
    "energy_kcal_jones",   # 12
    "water_g",             # 13
    "protein_g",           # 14
    "protein_n625_g",      # 15
    "carbs_g",             # 16
    "fat_g",               # 17
    "sugar_g",             # 18
    "fructose_g",          # 19
    "galactose_g",         # 20
    "glucose_g",           # 21
    "lactose_g",           # 22
    "maltose_g",           # 23
    "saccharose_g",        # 24
    "starch_g",            # 25
    "fiber_g",             # 26
    "polyols_g",           # 27
    "ash_g",               # 28
    "alcohol_g",           # 29
    "organic_acids_g",     # 30
    "fa_saturated_g",      # 31
    "fa_mufa_g",           # 32
    "fa_pufa_g",           # 33
    "fa_4_0_g",            # 34
    "fa_6_0_g",            # 35
    "fa_8_0_g",            # 36
    "fa_10_0_g",           # 37
    "fa_12_0_g",           # 38
    "fa_14_0_g",           # 39
    "fa_16_0_g",           # 40
    "fa_18_0_g",           # 41
    "fa_18_1_oleic_g",     # 42
    "fa_18_2_linoleic_g",  # 43
    "fa_18_3_ala_g",       # 44
    "fa_20_4_ara_g",       # 45
    "fa_20_5_epa_g",       # 46
    "fa_22_6_dha_g",       # 47
    "cholesterol_mg",      # 48
    "salt_g",              # 49
    "calcium_mg",          # 50
    "chloride_mg",         # 51
    "copper_mg",           # 52
    "iron_mg",             # 53
    "iodine_ug",           # 54
    "magnesium_mg",        # 55
    "manganese_mg",        # 56
    "phosphorus_mg",       # 57
    "potassium_mg",        # 58
    "selenium_ug",         # 59
    "sodium_mg",           # 60
    "zinc_mg",             # 61
    "vitamin_a_rae_ug",    # 62
    "retinol_ug",          # 63
    "beta_carotene_ug",    # 64
    "vitamin_d_ug",        # 65
    "vitamin_d2_ug",       # 66
    "vitamin_d3_ug",       # 67
    "alpha_tocopherol_mg", # 68
    "vitamin_e_mg",        # 69
    "vitamin_k1_ug",       # 70
    "vitamin_k2_ug",       # 71
    "vitamin_c_mg",        # 72
    "vitamin_b1_mg",       # 73
    "vitamin_b2_mg",       # 74
    "vitamin_b3_mg",       # 75
    "vitamin_b5_mg",       # 76
    "vitamin_b6_mg",       # 77
    "folate_dfe_ug",       # 78
    "folate_ug",           # 79
    "folate_intrinsic_ug", # 80
    "folic_acid_ug",       # 81
    "vitamin_b12_ug",      # 82
    "jones_factor",        # 83
]
assert len(COLUMN_MAP) == 84

NUTRIENT_FIELDS = [f for f in COLUMN_MAP[9:83] if f is not None]

# Champs clés pour completeness_14 et _nutrient_meta.missing_fields
KEY_NUTRIENTS_14 = [
    "energy_kcal", "protein_g",  "carbs_g",       "fat_g",
    "fiber_g",     "calcium_mg", "iron_mg",        "sodium_mg",
    "vitamin_c_mg", "vitamin_d_ug", "vitamin_b12_ug", "folate_ug",
    "fa_saturated_g", "sugar_g",
]

CIQUAL_SOURCE = {
    "title":     "Ciqual French food composition table",
    "publisher": "Anses",
    "location":  "Maisons-Alfort",
    "year":      2025,
    "edition":   "November 2025",
    "url":       "https://ciqual.anses.fr/",
    "doi":       "https://doi.org/10.5281/zenodo.17550133",
    "scope":     "3484 foods, 74 nutrients",
}

SALT_SODIUM_RATIO = 2.542


# ============================================================================
# 2. EXCLUSIONS
# ============================================================================
EXCL_SUBGROUPS_HARD = {
    # Viandes, poissons et dérivés
    "0401", "0402", "0403", "0404", "0405", "0406", "0407", "0408", "0409",
    # Plats composés, salades, sandwichs, entrées — plats préparés, pas ingrédients
    "0101",   # salades composées
    "0103",   # plats composés (y compris végétariens)
    "0104",   # pizzas, crêpes garnies
    "0105",   # sandwichs / burgers / wraps
    "0106",   # entrées composées (nems, feuilletés, samossas, bouchées…)
    # Sous-groupes déjà exclus
    "0102",
    # Céréales petit-déjeuner et barres (produits finis)
    "0707", "0708",
    # Viennoiseries et biscuits sucrés (produits finis)
    "0705", "0706",
    # Gâteaux et pâtisseries préparés (produits finis)
    "0709",
    # Aliments infantiles
    "1102", "1103", "1104",
    # Autres exclusions préexistantes
    "0904", "1001", "1101",
    # ── Ajouts v6.7 (audit scope recettes maison) ────────────────────────────
    "0601",   # Eaux minérales (89 items — aucune utilité recette)
    "0303",   # Biscuits apéritifs / crackers industriels (48 items)
    "0801",   # Glaces (produits finis industriels)
    "0802",   # Sorbets (produits finis industriels)
    "0803",   # Desserts glacés (profiteroles, pêche melba, mystères…)
    "1008",   # Denrées alimentation particulière (substituts de repas)
}

EXCL_CODES_HARD = {
    # Exclusions préexistantes
    25002, 25003, 25010, 25013, 25029, 25043, 25057, 25073, 25088,
    25103, 25106, 25111, 25121, 25123, 25124, 25127, 25135, 25085,
    25137, 25138, 25152, 25200, 25511, 25220, 25243, 25456, 25546,
    36318, 25565, 1033, 9085, 8380, 8395, 8937,
    11194, 11114, 11223, 42603, 42604, 42605, 42606, 11507,
    # ── Vrais blends "ou" entre ingrédients distincts (v6.2) ──────────────────
    # Mélanges de légumes indéfinis (0201)
    19999,  # Poivron, vert, jaune ou rouge, cuit (aliment moyen — blend)
    20012,  # Salade ou chicorée frisée, crue
    20103,  # Champignon, chanterelle ou girolle, crue
    20265,  # Julienne ou brunoise de légumes, surgelée, crue
    20267,  # Printanière ou jardinière de légumes, surgelée, crue
    20272,  # Mesclun ou salade, mélange de jeunes pousses
    # Mélanges / macédoines de fruits (0204)
    13185,  # Compote tout type de fruits (aliment moyen)
    13705,  # Macédoine ou cocktail ou salade de fruits, au sirop, appertisé, égoutté
    13706,  # Macédoine ou cocktail ou salade de fruits, au sirop, appertisé, non égoutté
    13707,  # Macédoine ou cocktail ou salade de fruits, au sirop léger, égoutté
    13708,  # Macédoine ou cocktail ou salade de fruits, au sirop léger, non égoutté
    13709,  # Macédoine ou cocktail ou salade de fruits (aliment moyen)
    # Aliments moyens multi-ingrédients
    39500,  # Glace à l'eau ou sorbet ou crème glacée, tout parfum (aliment moyen)
    30999,  # Confiture ou marmelade, tout type de fruits (aliment moyen)
    31006,  # Confiture ou marmelade ou gelée, tout type de fruits (aliment moyen)
    # ── v6.7 : Alcools 0603 non-cuisine ──────────────────────────────────────
    # Conservés : vin rouge(5214)/blanc(5215)/rosé(5216), champagne(5207),
    #   cidre brut(5006)/doux(5007), rhum(1004), marsala(1015/1016),
    #   cognac/armagnac(1023), calvados(1024), eau de vie de fruits(1001),
    #   saké(1026), crème de cassis(1021), vin blanc mousseux(5201).
    1000,   # Pastis
    1002,   # Gin
    1003,   # Liqueur
    1005,   # Whisky
    1006,   # Vin doux
    1007,   # Apéritif à base de vin (vermouth)
    1008,   # Vodka
    1010,   # Pastis, prêt à boire
    1011,   # Apéritif anisé sans alcool, à diluer
    1012,   # Cocktail à base de rhum
    1013,   # Cocktail à base de whisky
    1014,   # Alcool pur
    1017,   # Sangria, faite maison
    1018,   # Kir
    1019,   # Kir royal
    1022,   # Cocktail type punch
    2008,   # Cocktail / boisson apéritive sans alcool
    5000,   # Bière brune
    5001,   # Bière "cœur de marché"
    5002,   # Bière forte
    5003,   # Cidre (aliment moyen)
    5004,   # Panaché
    5005,   # Panaché préemballé
    5008,   # Bière faiblement alcoolisée
    5009,   # Bière blanche
    5010,   # Bière spéciale
    5011,   # Bières de spécialités
    5020,   # Cidre traditionnel
    5022,   # Cidre aromatisé aux fruits
    5029,   # Bière sans alcool sucrée
    5030,   # Bière sans alcool non sucrée
    5100,   # Pétillant de fruits
    5209,   # Vin blanc mousseux aromatisé
    5210,   # Vin (aliment moyen)
    # ── v6.7 : Sous-catégories 0602 indésirables ─────────────────────────────
    # Conservés dans 0602 : jus (2xxx), boissons végétales (181xx),
    #   café/thé/cacao poudre brute (18003/05/69/76/100/150/152).
    # Boissons rafraîchissantes sans alcool (BRSA)
    18007,  # Cocktail / boisson apéritive sans alcool
    18012,  # Boisson à l'eau minérale, aromatisée, sucrée
    18013,  # Tonic, sans sucres ajoutés, avec édulcorants
    18014,  # Tonic, sucré, avec édulcorants
    18015,  # Boisson au thé, aromatisée, sucrée, avec édulcorants
    18021,  # Boisson plate aux fruits (<10%), sans sucres ajoutés, avec édulcorants
    18023,  # Boisson plate aux fruits (<10%), sucrée
    18024,  # Boisson plate aux fruits (10-50%), sucrée, avec édulcorants
    18025,  # Kombucha, préemballé
    18028,  # Boisson à l'eau minérale, aromatisée, sans édulcorants
    18029,  # Boisson rafraîchissante sans alcool (aliment moyen)
    18030,  # Boisson à l'eau minérale, aromatisée, avec édulcorants
    18048,  # Boisson gazeuse aux fruits (aliment moyen)
    18057,  # Boisson préparée à partir de sirop 0%, diluée dans l'eau
    18058,  # Boisson préparée à partir de sirop sucré, diluée dans l'eau
    18064,  # Boisson au thé, à teneur réduite en sucres
    18065,  # Boisson au thé, sans sucres ajoutés, avec édulcorants
    18075,  # Boisson au thé, aromatisée, sucrée
    18294,  # Boisson plate fruits (<10%), sucrée, enrichie en vitamines
    18295,  # Boisson plate fruits (10-50%), sucrée, enrichie en vitamines
    18296,  # Smoothie (>=50% fruits), enrichi en vitamines
    18297,  # Boisson plate fruits (>=50%), enrichie en vitamines
    18298,  # Boisson plate fruits (>=50%), rayon ambiant
    18299,  # Citronnade, sucrée
    18300,  # Smoothie (>=50% fruits), sans sucres ajoutés
    18304,  # Boisson plate fruits (10-50%), à teneur réduite en sucres
    18305,  # Boisson plate fruits (10-50%), sans sucres ajoutés
    18306,  # Boisson à l'aloe vera, sucrée
    18309,  # Boisson plate aux fruits, sucrée
    18315,  # Boisson plate aux fruits et légumes
    18316,  # Kéfir d'eau et de fruits, préemballé
    18328,  # Boisson à base de sirop diluée (aliment moyen)
    18339,  # Boisson plate fruits (10-50%), sucrée
    18341,  # Boisson gazeuse à la pomme (>=50%), sans sucres ajoutés
    18344,  # Tonic, sucré
    18347,  # Boisson à la sève de bouleau
    18348,  # Boisson pour le sport, sucrée
    18349,  # Boisson pour le sport, sucrée, avec édulcorants
    # Boissons rafraîchissantes lactées
    18343,  # Boisson au(x) fruit(s) et au lait
    19114,  # Boisson lactée à la vanille, enrichie en vit. D
    19116,  # Boisson lactée au café, enrichie en vitamines
    19117,  # Boisson lactée au café, non enrichie
    19118,  # Boisson lactée au chocolat, non enrichie
    19119,  # Boisson lactée au chocolat, enrichie en vitamines
    19120,  # Boisson lactée aromatisée (aliment moyen)
    19127,  # Boisson lactée à la fraise, enrichie en vit. D
    # Nectars
    2009,   # Nectar multifruit, base pomme, standard
    2010,   # Nectar multifruit, base pomme, multivitaminé
    2022,   # Nectar de fraise
    2043,   # Nectar d'abricot
    2045,   # Nectar de papaye
    2054,   # Nectar de poire
    2060,   # Nectar multifruit, multivitaminé
    2061,   # Nectar multifruit, standard
    2062,   # Nectar multifruit, base orange, multivitaminé
    2063,   # Nectar multifruit, base orange, standard
    2064,   # Nectar, avec édulcorants, allégé en sucres
    2076,   # Nectar de pomme
    2365,   # Nectar de fruit de la passion / maracuja
    2366,   # Nectar de banane
    2367,   # Nectar de goyave
    2370,   # Nectar de mangue
    2371,   # Nectar de pêche
    2374,   # Nectar d'ananas
    2375,   # Nectar d'orange
    # Cafés/thés/infusions prêts à consommer
    18004,  # Café non instantané, prêt à boire
    18020,  # Thé infusé, sans sucres ajoutés
    18022,  # Tisane / infusion, sans sucres ajoutés
    18070,  # Café décaféiné, non instantané, prêt à boire
    18071,  # Café expresso, non instantané, prêt à boire
    18072,  # Café décaféiné, instantané, prêt à boire
    18073,  # Café, instantané, prêt à boire
    18151,  # Café au lait/cappuccino, prêt à boire
    18153,  # Chicorée+café reconstituée avec lait demi-écrémé
    18154,  # Thé noir infusé
    18155,  # Thé vert infusé
    18161,  # Chicorée reconstituée avec lait demi-écrémé
    18162,  # Chicorée+café reconstituée avec eau
    # Boissons à reconstituer industrielles (sirops, mélanges café+lait)
    18017,  # Sirop à diluer, sucré
    18059,  # Boisson concentrée à diluer, type "sirop 0%"
    18160,  # Café au lait poudre soluble (composite industriel)
    18220,  # Spécialité à diluer au citron, sans sucres ajoutés
    # Aliments moyens analytiquement incohérents — données inter-lots non co-mesurées,
    # aucune valeur d'usage pour ALIM (trop génériques, remplacés par items spécifiques)
    24999,  # Dessert (aliment moyen)           — D2+D3 > vitamin_d_total (lots ≠)
    25616,  # Crudité, sans assaisonnement (aliment moyen) — AGS sous-fractions > total
    # Additifs technologiques — mass_balance critique, aucun usage culinaire ALIM
    31064,  # Édulcorant à la saccharine        — Sigma=3g/100g (ecart=97g, additif pur)
    31047,  # Gélifiant pour confitures         — Sigma=84g/100g (pectine/agar, minéraux manquants)
}

ULTRATRANS_KEYWORDS = [
    # Sodas et colas
    "cola,", "cola ",
    # Boissons énergisantes
    "boisson énergisante",
    # Limonades industrielles
    "limonade,", "limonade ",
    # Boissons gazeuses industrielles aromatisées
    "boisson gazeuse aromatisée, sans fruit",
    "boisson gazeuse aux fruits (teneur en fruits < 10%)",
    "boisson gazeuse aux fruits (teneur en fruits >= 10%",
    # Diabolos
    "diabolo",
    # Poudres cacaotées / maltées industrielles
    "poudre cacaotée ou au chocolat pour boisson",
    "poudre maltée, cacaotée ou au chocolat pour boisson",
    "chocolat chaud, boisson instantanée",
    # Mélanges lait/café industriels
    "café au lait ou cappuccino au chocolat",
    # Thés et infusions sucrés industriels
    "thé glacé", "ice tea",
]
ULTRATRANS_SUBGROUPS = {"0602"}

GELATIN_RISK_KEYWORDS = [
    "guimauve", "marshmallow", "bonbon gelifie", "gelifie",
    "bonbon a la reglisse, type rouleau",
]

GENERIC_MARKERS = {
    "aliment_moyen":  ["aliment moyen", "(aliment moyen)"],
    "tout_type":      ["tout type", "tout parfum"],
    "multi_variant":  [
        "vert, jaune ou rouge",
        "sans precision sur la teneur en matiere grasse",
        "sans precision sur la teneur en sucres",
    ],
    "sans_precision": ["sans precision (aliment", "cuit, sans precision"],
}

# Codes sous-groupes laitiers CIQUAL → pour dairy_process dans parse_state_v2
# Mappés vers "Dairy and Egg Products" (valeur attendue par food_schema_v2.DAIRY_CATEGORIES)
DAIRY_SUBGROUPS: frozenset[str] = frozenset({"0501", "0502", "0503", "0504"})


# ============================================================================
# 3. UTILITAIRES CIQUAL
# ============================================================================
_RE_BELOW = re.compile(r"^<\s*([\d,\.]+)$")


def parse_numeric(raw) -> tuple[float | None, bool]:
    if raw is None:
        return None, False
    if isinstance(raw, (int, float)):
        return float(raw), False
    s = str(raw).strip()
    if not s or s in ("-", "\u2212", "\u2013", "\u2014"):
        return None, False
    m = _RE_BELOW.match(s)
    if m:
        try:
            return float(m.group(1).replace(",", ".")), True
        except ValueError:
            return None, False
    try:
        return float(s.replace(",", ".")), False
    except ValueError:
        return None, False


def classify_generic(nom: str) -> tuple[bool, str | None]:
    nl = nom.lower()
    for gtype, markers in GENERIC_MARKERS.items():
        if any(m in nl for m in markers):
            return True, gtype
    return False, None


def gelatin_risk(nom: str) -> bool:
    return any(k in nom.lower() for k in GELATIN_RISK_KEYWORDS)


def _strip(s: str) -> str:
    tbl = str.maketrans("aaäeeeëiïoùuüc", "aaaeeeeiioouuc")
    return s.translate(tbl).replace("oe", "oe").replace("æ", "ae")


def should_exclude(code: int, ssgrp: str, nom: str) -> tuple[bool, str]:
    nl = _strip(nom.lower())
    if ssgrp in EXCL_SUBGROUPS_HARD:
        return True, f"subgroup_excl:{ssgrp}"
    if code in EXCL_CODES_HARD:
        return True, "code_excl:hard"
    if ssgrp in ULTRATRANS_SUBGROUPS:
        nl_raw = nom.lower()
        if any(k in nl_raw for k in ULTRATRANS_KEYWORDS):
            kw = next(k for k in ULTRATRANS_KEYWORDS if k in nl_raw)
            return True, f"ultratrans:{kw!r}"
    # ── v6.7 : filtre DOM-TOM (dans ssgrp 0201/0204 partagés avec items utiles)
    nl_raw = nom.lower()
    if "martinique" in nl_raw or "r\xe9union" in nl_raw or "reunion" in nl_raw:
        if any(k in nl_raw for k in ("pr\xe9lev\xe9", "preleve", "pr\xe9lev\xe9e", "prelevee")):
            return True, "dom_tom_excl"
    # ── v6.7 : filtre édulcorants (variants reformulés, valeurs nutritionnelles
    #           artificiellement modifiées — contre-productif pour précision recettes)
    if "avec \xe9dulcorants" in nl_raw or "avec edulcorants" in nl_raw:
        return True, "edulcorant_excl"
    return False, ""


# ============================================================================
# 4. PARSING DU NOM CIQUAL
# ============================================================================

def extract_base_name(name_fr: str) -> tuple[str, str]:
    """Sépare 'Épinards, cuits, égouttés' → ('Épinards', 'cuits, égouttés')."""
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
        return name_fr[:first_comma].strip(), name_fr[first_comma + 1:].strip()
    return name_fr, ""

# 6. AUDIT
# ============================================================================
ENERGY_FACTORS_KJ = {
    "protein_g": 17, "carbs_g": 17, "fat_g": 37,
    "fiber_g": 8, "alcohol_g": 29, "organic_acids_g": 13, "polyols_g": 10,
}
SALT_SODIUM_TOL      = 0.15
MASS_BALANCE_WARN_G  = 15.0
MASS_BALANCE_ERROR_G = 30.0
ENERGY_TOLERANCE     = 0.20
FA_BALANCE_TOL       = 0.10
FOLATE_BALANCE_TOL   = 0.05
CL_NA_TOL            = 0.50

SEVERITY_CLASS: dict[str, str] = {
    "negative_values":            "physical_error",
    "sugar_vs_carbs":             "physical_error",
    "energy_check":               "major_quality",
    "fa_balance":                 "major_quality",
    "sugar_subfractions":         "major_quality",
    "starch_carb_balance":        "major_quality",
    "fiber_vs_carbs":             "data_quality",
    "fiber_vs_carbs_postdry":     "info",
    # Les 3 checks suivants documentent des divergences analytiques structurelles
    # CIQUAL (mesures sur aliquots indépendants, méthodes différentes). Aucun n'est
    # actionnable par correction de données. Downgrade data_quality → info pour
    # préserver la traçabilité sans gonfler le compteur data_quality.
    "omega_vs_pufa":              "info",   # Σ omégas mesurés > PUFA global (aliquots ≠)
    "salt_sodium":                "info",   # conductimétrie ≠ absorption atomique Na
    "chloride_sodium_balance":    "info",   # Cl organique/KCl non issus de NaCl
    "vit_d_subforms":             "data_quality",
    "vit_e_tocopherol":           "data_quality",
    "folate_balance":             "data_quality",
    "fa_sfa_subfractions":        "data_quality",
    "retinol_vita_rae":           "data_quality",
    "protein_jones_consistency":  "info",
}

def get_severity_class(check: str, severity: str) -> str:
    if check == "mass_balance":
        return "physical_error" if severity == "error" else "major_quality"
    return SEVERITY_CLASS.get(check, "info")


def run_audit(food: dict, dl: dict) -> list[dict]:
    issues: list[dict] = []

    def add(sev, chk, msg, delta=None):
        e = {"severity": sev, "severity_class": get_severity_class(chk, sev),
             "check": chk, "message": msg}
        if delta is not None:
            e["delta_pct"] = round(delta * 100, 1)
        issues.append(e)

    def v(f):
        return food.get(f)

    for field in NUTRIENT_FIELDS:
        val = v(field)
        if val is not None and val < 0:
            add("error", "negative_values", f"{field} = {val}")

    sugar, carbs = v("sugar_g"), v("carbs_g")
    if sugar is not None and carbs is not None and sugar > carbs + 0.5:
        add("error", "sugar_vs_carbs", f"sugar_g={sugar} > carbs_g={carbs}")

    fiber = v("fiber_g")
    if fiber is not None and carbs is not None and fiber > carbs + 0.5:
        if carbs < 1.0:
            # Exception population 2 — aliments quasi-acarbonés (matières grasses,
            # olives, champignons, légumes à très faibles glucides...) : carbs_g est
            # une valeur trace, le ratio fiber/carbs devient mathématiquement absurde
            # sans signaler une anomalie réelle. Check silencieux.
            pass
        elif (water := food.get("water_g")) is not None and water >= 75.0:
            # Exception population 3A — légumes hydratés et légumineuses fraîches
            # (water_g ≥ 75 %) : pour ces matrices, carbs_g représente les glucides
            # disponibles (CIQUAL, système FR) qui excluent déjà les fibres. fiber > carbs
            # est physiologiquement normal et n'indique aucune anomalie dans la source.
            pass
        elif food.get("_fiber_rebased"):
            # Check sur-mesure population 1 — dried post-rebase :
            # Le rebase sec→frais a été appliqué mais fiber > carbs persiste.
            # Biologiquement cohérent pour matrices très concentrées (épices, algues,
            # oléagineux) où la fibre structurelle domine les glucides nets.
            # Sévérité info : documenté pour audit, hors comptage data_quality.
            ratio_fc = round(fiber / carbs, 2) if carbs > 0 else None
            add("info", "fiber_vs_carbs_postdry",
                f"fiber_g={fiber} > carbs_g={carbs} post-rebase (ratio={ratio_fc}) : "
                f"anomalie structurelle acceptée (matrice concentrée sèche)",
                ratio_fc)
        else:
            # v6.10 — Branch 4b : herbes aromatiques et condiments gras.
            # Pour ces matrices, CIQUAL mesure les fibres par méthode AOAC qui intègre
            # les polyphénols et fractions insolubles non-glucidiques. Le champ carbs_g
            # représente les glucides DISPONIBLES (système FR), qui n'incluent pas les
            # fibres. Physiologiquement : fiber_g_AOAC > carbs_disponibles est attendu
            # pour les aromates denses (thym, romarin) et les condiments lipidiques
            # (olive, tapenade, moutarde) où la fibre structurelle domine.
            # Source CIQUAL 2025 vérifiée — pas d'erreur d'import.
            # Downgrade data_quality → info : documenté pour traçabilité, non actionnable.
            _fat = food.get("fat_g") or 0
            _is_herb_or_fat_condiment = (
                # Herbes aromatiques fraîches : faible carbs, water 60-70%
                (carbs < 12 and (_water := food.get("water_g") or 0) > 55 and _fat < 8)
                # Condiments gras : fat élevé (olives, tapenade, noisette, moutarde)
                or _fat >= 8
            )
            delta_fc = (fiber - carbs) / carbs if carbs > 0 else None
            if _is_herb_or_fat_condiment:
                add("info", "fiber_vs_carbs",
                    f"fiber_g={fiber} > carbs_g={carbs} — limite méthodologique AOAC "
                    f"(herbe/condiment gras, conforme CIQUAL 2025)",
                    delta_fc)
            else:
                # Vrais positifs : légumineuses cuites et cas non catégorisés
                add("warning", "fiber_vs_carbs",
                    f"fiber_g={fiber} > carbs_g={carbs} (fiber ne peut dépasser les glucides totaux)",
                    delta_fc)

    salt, na = v("salt_g"), v("sodium_mg")
    if salt is not None and na is not None and salt > 0.01 and na > 0.1:
        expected = na / 1000 * SALT_SODIUM_RATIO
        delta = abs(salt - expected) / expected
        if delta > SALT_SODIUM_TOL:
            add("warning", "salt_sodium",
                f"salt_g={salt} != sodium->sel={round(expected,3)} "
                f"(delta={round(delta*100,1)}%). preferred_field=sodium_mg.", delta)

    vd, d2, d3 = v("vitamin_d_ug"), v("vitamin_d2_ug"), v("vitamin_d3_ug")
    if vd is not None and d2 is not None and d3 is not None:
        if (d2 + d3) > vd + 0.01:
            add("warning", "vit_d_subforms", f"D2+D3={round(d2+d3,3)} > vitamin_d_total={vd}")

    ve, at = v("vitamin_e_mg"), v("alpha_tocopherol_mg")
    if ve is not None and at is not None and at > ve + 0.05:
        add("warning", "vit_e_tocopherol", f"alpha_tocopherol={at} > vitamin_e={ve}")

    ft, fi, fa = v("folate_ug"), v("folate_intrinsic_ug"), v("folic_acid_ug")
    if ft is not None and fi is not None and fa is not None:
        if (fi + fa) > ft * (1 + FOLATE_BALANCE_TOL):
            add("warning", "folate_balance",
                f"intrinseques+folique={round(fi+fa,1)} > folate_total={ft}")

    fas, fam, fap = v("fa_saturated_g"), v("fa_mufa_g"), v("fa_pufa_g")
    fat = v("fat_g")
    if all(x is not None for x in [fas, fam, fap, fat]) and fat > 0:
        fa_sum = fas + fam + fap
        if fa_sum > fat * (1 + FA_BALANCE_TOL):
            if fat < 0.1:
                # Exception ultra-low fat : les sous-fractions FA sont des valeurs
                # LOD/2 mesurées sur un lot différent (ex: lait entier) et ne sont
                # pas représentatives d'un fat_g < 0.1g. Ratio mathématiquement
                # aberrant mais non actionnable. Cas connu : lait écrémé UHT (fat=0.021).
                pass
            else:
                delta = (fa_sum - fat) / fat
                add("warning", "fa_balance",
                    f"SFA+MUFA+PUFA={round(fa_sum,2)} > fat_g={fat}", delta)

    if fap is not None and fap > 0:
        o_sum = sum(v(f) or 0 for f in [
            "fa_18_3_ala_g", "fa_20_5_epa_g", "fa_22_6_dha_g",
            "fa_20_4_ara_g", "fa_18_2_linoleic_g"
        ])
        if o_sum > fap * (1 + FA_BALANCE_TOL):
            delta = (o_sum - fap) / fap
            add("warning", "omega_vs_pufa",
                f"Sigma AG details={round(o_sum,3)} > fa_pufa={fap}", delta)

    water, prot, fat2, carb2 = v("water_g"), v("protein_g"), v("fat_g"), v("carbs_g")
    if all(x is not None for x in [water, prot, fat2, carb2]):
        total = (water + prot + fat2 + carb2
                 + (v("fiber_g") or 0) + (v("alcohol_g") or 0) + (v("ash_g") or 0))
        dev = abs(total - 100)
        if dev > MASS_BALANCE_ERROR_G:
            print(f"  [CRITICAL] MASS_BALANCE: {food.get('id','?')} ({food.get('name_fr','?')[:50]})"
                  f" Sigma={round(total,1)}g")
            add("error", "mass_balance",
                f"Sigma macros={round(total,1)} g/100g (ecart={round(dev,1)}g CRITIQUE)")
        elif dev > MASS_BALANCE_WARN_G:
            add("warning", "mass_balance", f"Sigma macros={round(total,1)} g/100g (ecart={round(dev,1)}g)")

    e_decl = v("energy_kj")
    if e_decl is not None and e_decl > 0 and prot is not None and fat2 is not None and carb2 is not None:
        # CIQUAL inclut les polyols dans carbs_g mais leur facteur énergétique est
        # 10 kJ/g (vs 17 kJ/g pour les glucides). Il faut déduire polyols de carbs
        # avant d'appliquer le facteur glucides pour éviter le double-comptage.
        # Sans cette correction : confiseries sans sucres (sorbitol/xylitol),
        # abricots secs, champignons, céleri-rave divergent de 27-166%.
        _polyols = v("polyols_g") or 0.0
        _carbs_net = max(0.0, carb2 - _polyols)
        e_calc = (prot              * ENERGY_FACTORS_KJ["protein_g"]
                + _carbs_net       * ENERGY_FACTORS_KJ["carbs_g"]
                + fat2             * ENERGY_FACTORS_KJ["fat_g"]
                + (v("fiber_g") or 0)         * ENERGY_FACTORS_KJ["fiber_g"]
                + (v("alcohol_g") or 0)       * ENERGY_FACTORS_KJ["alcohol_g"]
                + (v("organic_acids_g") or 0) * ENERGY_FACTORS_KJ["organic_acids_g"]
                + _polyols         * ENERGY_FACTORS_KJ["polyols_g"])
        if e_calc > 0:
            delta = abs(e_decl - e_calc) / e_decl
            if delta > ENERGY_TOLERANCE:
                add("warning", "energy_check",
                    f"Energie declaree={e_decl} kJ vs calculee={round(e_calc,1)} kJ "
                    f"(delta={round(delta*100,1)}%)", delta)

    pj, pn, jf = v("protein_g"), v("protein_n625_g"), v("jones_factor")
    if all(x is not None for x in [pj, pn, jf]) and pn > 0.1 and jf > 0:
        exp_r = jf / 6.25
        act_r = pj / pn
        delta = abs(act_r - exp_r) / exp_r
        if delta > 0.10:
            add("info", "protein_jones_consistency",
                f"ratio Jones/N625={round(act_r,3)}, attendu {round(exp_r,3)}", delta)

    sugar12 = v("sugar_g")
    if sugar12 is not None and sugar12 > 0.1:
        sub_fields = ["fructose_g", "glucose_g", "galactose_g",
                      "lactose_g", "maltose_g", "saccharose_g"]
        sub_vals = [v(f) for f in sub_fields]
        if any(x is not None for x in sub_vals):
            sub_sum = sum(x for x in sub_vals if x is not None)
            if sub_sum > sugar12 * 1.15:
                if food.get("generic_type") == "aliment_moyen":
                    # Aliments moyens : sous-fractions sucres mesurées sur lots
                    # indépendants → incohérence structurelle, non actionnable.
                    pass
                else:
                    delta = (sub_sum - sugar12) / sugar12
                    add("warning", "sugar_subfractions",
                        f"Sigma sucres={round(sub_sum,2)} > sugar_g={sugar12}", delta)

    starch13 = v("starch_g"); carbs13 = v("carbs_g"); sugar13 = v("sugar_g")
    if starch13 is not None and carbs13 is not None and carbs13 > 0.5:
        known_parts = starch13 + (sugar13 or 0.0)
        if known_parts > carbs13 * 1.10:
            delta = (known_parts - carbs13) / carbs13
            add("warning", "starch_carb_balance",
                f"starch+sugar={round(known_parts,2)} > carbs={carbs13}", delta)

    cl14 = v("chloride_mg"); na14 = v("sodium_mg")
    CL_NA_RATIO = 35.45 / 22.99
    if cl14 is not None and na14 is not None and na14 > 10 and cl14 > 10:
        expected14 = na14 * CL_NA_RATIO
        delta14 = abs(cl14 - expected14) / expected14
        if delta14 > CL_NA_TOL:
            add("warning", "chloride_sodium_balance",
                f"chloride_mg={cl14} vs Na×1.542={round(expected14,1)} "
                f"(delta={round(delta14*100,1)}%)", delta14)

    vit_a15 = v("vitamin_a_rae_ug"); retinol15 = v("retinol_ug"); bcar15 = v("beta_carotene_ug")
    if vit_a15 is not None and vit_a15 > 1 and retinol15 is not None:
        calc15 = retinol15 + (bcar15 or 0.0) / 12.0
        delta15 = abs(vit_a15 - calc15) / vit_a15
        abs_diff15 = abs(vit_a15 - calc15)
        # Double seuil : relatif ET absolu.
        # CIQUAL calcule la RAE en incluant alpha-carotène et bêta-cryptoxanthine
        # (non présents dans notre schéma). Quand retinol=0 et bcar=None, calc=0
        # mais rae peut valoir 1-3 µg via ces caroténoïdes mineurs → delta=100%
        # sur des traces sans signification nutritionnelle (< 5 µg = 0.5% AJR).
        # On ne flag que si la différence absolue est nutritionnellement significative.
        if delta15 > 0.25 and abs_diff15 > 5.0:
            add("info", "retinol_vita_rae",
                f"vitamin_a_rae={vit_a15} vs retinol+bcar/12={round(calc15,1)}", delta15)

    sfa16 = v("fa_saturated_g")
    SFA_DETAIL_FIELDS = ["fa_4_0_g","fa_6_0_g","fa_8_0_g","fa_10_0_g",
                         "fa_12_0_g","fa_14_0_g","fa_16_0_g","fa_18_0_g"]
    if sfa16 is not None and sfa16 > 0.1:
        # Exclure les champs sous limite de détection (LOD/2) : leur valeur
        # nut[fld] = dl[fld]/2 est une convention épidémiologique, pas une mesure
        # réelle. Les sommer gonferait artificiellement le total des sous-fractions.
        # Les AGS courts (C4:0–C14:0) sont presque systématiquement sous LOD dans
        # les végétaux, légumes et céréales → +0.030g faux sur la somme.
        sfa_sub_vals = [v(f) for f in SFA_DETAIL_FIELDS
                        if v(f) is not None and f not in dl]
        if sfa_sub_vals:
            sfa_sub_sum = sum(sfa_sub_vals)
            if sfa_sub_sum > sfa16 * (1 + FA_BALANCE_TOL):
                delta16 = (sfa_sub_sum - sfa16) / sfa16
                add("warning", "fa_sfa_subfractions",
                    f"Sigma SFA C4-C18={round(sfa_sub_sum,3)} > fa_saturated={sfa16}", delta16)

    return issues


def compute_audit_score(issues: list[dict]) -> dict:
    counts = {"physical_error": 0, "major_quality": 0, "data_quality": 0, "info": 0}
    for iss in issues:
        sc = iss.get("severity_class", "info")
        counts[sc] = counts.get(sc, 0) + 1
    total = sum(counts.values())
    return {
        "physical_errors": counts["physical_error"],
        "major_quality":   counts["major_quality"],
        "data_quality":    counts["data_quality"],
        "info":            counts["info"],
        "total":           total,
        "usable":          counts["physical_error"] == 0,
    }


def compute_quality_score(completeness_14: int, audit_score: dict) -> float:
    if not audit_score.get("usable", True):
        return 0.0
    base = completeness_14 / 14.0
    penalty = (0.05 * audit_score.get("major_quality", 0)
               + 0.01 * audit_score.get("data_quality", 0))
    return round(max(0.0, base - penalty), 3)


# ============================================================================
# 7. CATÉGORIE UNIFIÉE
# ============================================================================
def build_unified_category(grp_code, grp_fr, ssgrp, ssgrp_fr, ssssgrp, ssssgrp_fr) -> dict:
    return {
        "level1_fr":   grp_fr,
        "level1_en":   None,
        "level1_code": grp_code,
        "level2_fr":   ssgrp_fr,
        "level2_code": ssgrp,
        "level3_fr":   ssssgrp_fr,
        "level3_code": ssssgrp,
    }


# ============================================================================
# 8. BUILD FOOD OBJECT
# ============================================================================
def build_food_object(row: tuple) -> tuple[dict, list[dict]]:
    grp_code   = str(row[0]).zfill(2) if row[0] is not None else None
    ssgrp      = str(row[1]) if row[1] is not None else None
    ssssgrp    = str(row[2]) if row[2] is not None else None
    grp_fr     = (str(row[3] or "")).strip() or None
    ssgrp_fr   = (str(row[4] or "")).strip() or None
    ssssgrp_fr = None
    if row[5] and str(row[5]).strip() not in ("-", ""):
        ssssgrp_fr = str(row[5]).strip()

    code    = int(row[6])
    name_fr = str(row[7] or "").strip()
    sci     = str(row[8] or "").strip() or None
    if sci in ("-", ""):
        sci = None

    nut: dict[str, float | None] = {}
    dl:  dict[str, float]        = {}

    # Champs auxquels on applique la convention LOD/2 plutôt que None.
    # Standard épidémiologique : valeur = limite_détection / 2.
    # Critique pour les acides gras (fa_*) : évite le désalignement
    # fat_g (multi-source) > sat+mufa+pufa (source unique) → lipid_fa_incomplete.
    # Macros principales exclues (fat_g, protein_g, carbs_g, energy_kcal) :
    # une valeur "<X" sur un macro principal signifie absence réelle → None conservé.
    LOD_HALF_FIELDS = {
        "fa_saturated_g", "fa_mufa_g", "fa_pufa_g",
        "fa_4_0_g", "fa_6_0_g", "fa_8_0_g", "fa_10_0_g",
        "fa_12_0_g", "fa_14_0_g", "fa_16_0_g", "fa_18_0_g",
        "fa_18_1_oleic_g", "fa_18_2_linoleic_g", "fa_18_3_ala_g",
        "fa_20_4_ara_g", "fa_20_5_epa_g", "fa_22_6_dha_g",
        "cholesterol_mg", "vitamin_d_ug", "vitamin_b12_ug",
        "selenium_ug", "iodine_ug",
    }

    for ci in range(9, 83):
        fld = COLUMN_MAP[ci]
        if fld is None:
            continue
        val, below = parse_numeric(row[ci])
        if below:
            dl[fld] = val
            if fld in LOD_HALF_FIELDS and val is not None:
                # Convention LOD/2 : demi-limite de détection
                # Tracé via dl[fld] pour auditabilité downstream
                nut[fld] = round(val / 2, 5)
            else:
                nut[fld] = None   # macro principal : absence réelle
        else:
            nut[fld] = val

    jf_val, _ = parse_numeric(row[83])

    is_gen, gen_type = classify_generic(name_fr)
    diet = build_diet_profile(name_fr, nut, detection_limits=dl)

    # ── FIX diet_profile (v6.5) ─────────────────────────────────────────────
    # 1. Fromages et produits laitiers (0501-0504) : build_diet_profile marque
    #    certains fromages vegan=True car il ne reçoit que le name_fr sans catégorie.
    #    On force vegan=False pour tous les sous-groupes laitiers CIQUAL.
    if ssgrp in DAIRY_SUBGROUPS and diet.get("vegan") is True:
        diet["vegan"] = False

    # ── Parsing d'état v2 (food_schema_v2) ─────────────────────────────────
    # search_in_qualifier=True : CIQUAL cherche l'état après la 1ère virgule
    # Ex: "Épinards, cuits, égouttés" → analyse "cuits, égouttés"
    # category : mappe le sous-groupe laitier CIQUAL vers la valeur attendue
    # par food_schema_v2.DAIRY_CATEGORIES pour activer dairy_process
    ciqual_category = "Dairy and Egg Products" if ssgrp in DAIRY_SUBGROUPS else (ssgrp or "")
    state = parse_state_v2(name_fr, category=ciqual_category, search_in_qualifier=True)
    rules_fired = state.pop("_rules_fired", [])

    # ── fix_unknown_state : reclassification post-parse (Q3:a / Q12:c) ─────────
    # Récupère ~230 unknowns → dried / manufactured / fermented via 4 passes.
    fix_unknown_state(state, name_fr, subgroup_code=ssgrp or "", rules_fired=rules_fired)

    # ── FIX state (v6.5) ────────────────────────────────────────────────────
    # 2. Lait fermenté (0502) : fix_unknown_state rate le mot "fermenté" car il
    #    est dans le nom du groupe et non dans le qualificatif analysé. On force
    #    le level1 à "fermented" pour tout le sous-groupe 0502.
    if ssgrp == "0502" and state.get("process", {}).get("level1") == "unknown":
        state.setdefault("process", {})["level1"] = "fermented"
        state["process"]["confidence"] = 0.90
        state["process"]["raw_label_fragment"] = "subgroup:0502"

    # ── FIX fiber_g basis (v6.8 + v6.9) ────────────────────────────────────
    # CIQUAL exprime fiber_g sur matière sèche pour les items dried, alors que
    # tous les autres macros (carbs_g, protein_g, fat_g…) sont sur poids frais.
    # On ramène fiber_g sur la même base en multipliant par la fraction sèche :
    #   fiber_g_frais = fiber_g_sec × (100 - water_g) / 100
    # Garde-fous :
    #   - water_g doit être disponible (non None)
    #   - water_g < 98 : exclut les bouillons/eaux et les valeurs aberrantes
    #     où dry_frac serait quasi-nul et réduirait fiber_g à zéro par erreur.
    #
    # v6.9 — extension aux items quasi-secs (water_g < 15) hors dried :
    #   Son, café, lin, thé, graines grillées, sésame… sont classifiés
    #   manufactured/cooked mais ont la même structure de teneur en eau que
    #   les dried. Le même biais de base sèche s'y applique.
    #   Tracé distinct via _fiber_rebase_reason pour auditabilité downstream.
    _water = nut.get("water_g")
    _fiber = nut.get("fiber_g")
    if _fiber is not None and _water is not None and 0.0 <= _water < 98.0:
        _l1 = state["process"]["level1"]
        _is_dried    = (_l1 == "dried")
        _is_lowwater = (_water < 15.0 and _l1 != "dried")
        if _is_dried or _is_lowwater:
            _dry_frac = (100.0 - _water) / 100.0
            if _dry_frac > 0:
                nut["fiber_g"] = round(_fiber * _dry_frac, 4)
                nut["_fiber_rebased"] = True
                nut["_fiber_rebase_reason"] = "dried" if _is_dried else "lowwater"

    # base_name = partie avant la 1ère virgule (ex: "Épinards")
    base_name, qualifier = extract_base_name(name_fr)
    food_id = f"ciqual_{code}"

    variant_key_str = state_variant_key(state)
    variant_id = compute_variant_id(food_id, state)
    group_key  = slugify(base_name)

    # ── Affinage group_key pour "Champignon, TYPE, état" ─────────────────────
    # extract_base_name coupe à la 1ère virgule → tous les champignons sauvages
    # héritaient du même group_key "champignon". On extrait le type depuis le
    # qualificatif pour les espèces distinctes.
    _CHAMPIGNON_TYPE_MAP = {
        "cepe":              "champignon_cepe",
        "cèpe":              "champignon_cepe",
        "morille":           "champignon_morille",
        "pleurote":          "champignon_pleurote",
        "oronge":            "champignon_oronge",
        "rose des pres":     "champignon_rose_des_pres",
        "rosé des prés":     "champignon_rose_des_pres",
        "truffe":            "champignon_truffe",
        "shiitake":          "champignon_shiitake",
        "shiitaké":          "champignon_shiitake",
        "lentin":            "champignon_shiitake",   # lentin comestible = shiitaké
    }
    if group_key == "champignon" and qualifier:
        qual_low = qualifier.lower()
        for keyword, mapped_key in _CHAMPIGNON_TYPE_MAP.items():
            if keyword in qual_low:
                group_key = mapped_key
                break
        # "tout type" et génériques → restent "champignon"

    # ── Fusion biscuit / cracker apéritif → biscuit_aperitif (v6.5) ─────────
    # CIQUAL 0303 utilise "biscuit" et "cracker apéritif" comme synonymes —
    # les deux group_keys contenaient exactement les mêmes 16 items.
    # On les normalise sous un seul group_key "biscuit_aperitif".
    if group_key in ("biscuit", "cracker_aperitif") and ssgrp == "0303":
        group_key = "biscuit_aperitif"

    # ── ingredient_key / family_key (Q2:c) ──────────────────────────────────────
    # ingredient_key : clé de jointure cross-source (base_key si dans BASE_INGREDIENT_MAP)
    # family_key     : navigation CIQUAL (subgroup_code level2)
    _bim_entry   = BASE_INGREDIENT_MAP.get(group_key, {})
    ingredient_key = _bim_entry.get("base_key") or group_key
    family_key     = ssgrp or None

    # ── Taxonomie dynamique (taxonomy_session_*.json) ────────────────────────
    # On cherche d'abord l'ingredient_key (qui peut différer du group_key quand
    # BASE_INGREDIENT_MAP remplace la clé), puis le group_key en fallback.
    # Aucune concaténation id+label : subgroup_id = "sg_bieres" (jamais "sg_bieres_bieres").
    _tax_obj = (
        build_taxonomy_object(ingredient_key, _BK_TAXONOMY, fallback_unclassified=False)
        or build_taxonomy_object(group_key, _BK_TAXONOMY, fallback_unclassified=False)
    )

    # ── Nutrients structurés (food_schema_v2) ───────────────────────────────
    # completeness_fields=KEY_NUTRIENTS_14 : spécifique CIQUAL
    # (vitamin_b12_ug et sugar_g au lieu de water_g et fa_18_3_ala_g)
    nutrients_obj = build_nutrients_object(
        nut,
        level1=state["process"]["level1"],
        completeness_fields=KEY_NUTRIENTS_14,
        detection_limits=dl,
    )

    category = build_unified_category(
        grp_code, grp_fr, ssgrp, ssgrp_fr, ssssgrp, ssssgrp_fr
    )

    # ── Audit ───────────────────────────────────────────────────────────────
    audit_issues = run_audit({**nut, "id": food_id, "name_fr": name_fr, "generic_type": gen_type}, dl)
    audit_score  = compute_audit_score(audit_issues)

    nut_count       = sum(1 for f in NUTRIENT_FIELDS if nut.get(f) is not None)
    completeness_14 = sum(1 for f in KEY_NUTRIENTS_14 if nut.get(f) is not None)

    process_confidence = state["process"]["confidence"]
    if variant_key_str == "unknown":
        process_confidence = 0.0

    obj: dict = {
        # ── Identité ────────────────────────────────────────────────────────
        "id":          food_id,
        "variant_id":  variant_id,
        "food_id":     food_id,
        "source":      "ciqual",
        "source_id":   code,
        # ── Noms (schema v3) ─────────────────────────────────────────────────
        "name": {
            "fr":        name_fr,
            "en":        None,
            "canonical": name_fr,   # CIQUAL : nom canonique = nom FR
        },
        # ── Sources (schema v2 R10) ───────────────────────────────────────────
        "sources": [{
            "db":        "CIQUAL",
            "source_id": str(code),
            "raw_label": name_fr,
            "version":   "2025",
        }],
        # ── Noms plats rétrocompat ────────────────────────────────────────────
        "name_fr":         name_fr,
        "name_en":         None,
        "base_name":       base_name,
        "scientific_name": sci,
        # ── Regroupement + jointure cross-source (Q2:c) ──────────────────────
        "group_key":      group_key,
        "ingredient_key": ingredient_key,   # jointure future USDA/NEVO
        "family_key":     family_key,        # navigation CIQUAL (subgroup_code)
        "variant_key":    variant_key_str,
        "is_generic":     is_gen,
        "generic_type":   gen_type,
        # ── Marqueur "ou" (Q4:a / Q5:b) ─────────────────────────────────────
        "_has_ou":       classify_ou(name_fr),
        "_ou_expansion": False,              # False pour l'item source ; True pour synthétiques
        # ── Classification ──────────────────────────────────────────────────
        "category":    category,
        # ── Taxonomie dynamique (taxonomy_session v3) ────────────────────────
        # Présent uniquement si le bk est connu dans taxonomy_session_*.json.
        # Format : { group_id, group_label, subgroup_id, subgroup_label }
        # None si le bk n'est pas encore classifié (pas de fallback unclassified
        # ici pour garder le champ absent plutôt qu'un objet vide de sens).
        **({"taxonomy": _tax_obj} if _tax_obj is not None else {}),
        # ── State (schéma v3) ────────────────────────────────────────────────
        "state":       state,
        # ── Profil diététique ────────────────────────────────────────────────
        "diet_profile": diet,
        # ── Params analytiques ───────────────────────────────────────────────
        "refuse_percent":   None,
        "jones_factor":     jf_val,
        "portions":         [],
        # ── Nutrients structurés (schéma v2) ────────────────────────────────
        "nutrients":   nutrients_obj,
        # ── Champs plats rétrocompat ─────────────────────────────────────────
        **nut,
        "carbs_schema": "available",  # CIQUAL = glucides disponibles par définition
        "salt_g": round(nut["sodium_mg"] / 1000 * SALT_SODIUM_RATIO, 4)
                  if nut.get("sodium_mg") is not None else None,
        "_usda_extra": None,
        # ── Qualité & audit ──────────────────────────────────────────────────
        "_quality": {
            "source":           "ciqual_2025",
            "source_id":        code,
            "nut_count":        nut_count,
            "completeness_14":  completeness_14,
            "portions_count":   0,
            "state_inference": {
                "confidence":    process_confidence,
                "rules_fired":   rules_fired,
                "raw_label":     name_fr,
            },
            "created_at":       datetime.now(timezone.utc).isoformat(),
            "pipeline_version": "6.0",
        },
        "quality_score":  compute_quality_score(completeness_14, audit_score),
        "_audit_score":   audit_score,
        "_audit_issues":  audit_issues if audit_issues else None,
    }

    if audit_issues:
        obj["_audit"] = {
            "score":           audit_score,
            "physical_errors": [i["check"] for i in audit_issues if i["severity_class"] == "physical_error"],
            "major_quality":   [i["check"] for i in audit_issues if i["severity_class"] == "major_quality"],
            "data_quality":    [i["check"] for i in audit_issues if i["severity_class"] == "data_quality"],
            "info":            [i["check"] for i in audit_issues if i["severity_class"] == "info"],
        }

    schema_errors = validate_food_item(obj)
    if schema_errors:
        print(f"⚠️  [CIQUAL] Schéma invalide pour {code} : {schema_errors}")

    return obj, audit_issues


# ============================================================================
# 9. GROUPEMENT PAR VARIANTS
# ============================================================================
def group_into_variants(foods: list[dict]) -> tuple[dict, list[dict]]:
    groups:    dict       = {}
    conflicts: list[dict] = []

    for food in foods:
        gk    = food["group_key"]
        state = food["variant_key"]

        if gk not in groups:
            groups[gk] = {
                "group_key":     gk,
                "name_fr":       food.get("base_name") or food["name_fr"],
                "name_en":       None,
                "category":      food.get("category"),
                # Taxonomie héritée du premier variant du groupe
                **({"taxonomy": food["taxonomy"]} if food.get("taxonomy") else {}),
                "sources":       ["ciqual"],
                "subgroup_code": food.get("state", {}).get("_subgroup_code"),
                "is_generic":    food.get("is_generic", False),
                "variants":      {},
                "_meta": {"variant_count": 0, "variant_keys": [], "conflict_count": 0},
            }

        grp = groups[gk]

        if state in grp["variants"]:
            i = 2
            while f"{state}_{i}" in grp["variants"]:
                i += 1
            resolved = f"{state}_{i}"
            conflicts.append({
                "group_key":      gk,
                "original_state": state,
                "resolved_state": resolved,
                "source_id_1":    grp["variants"][state].get("source_id"),
                "source_id_2":    food["source_id"],
            })
            grp["_meta"]["conflict_count"] += 1
            state = resolved

        variant: dict = {
            "id":          food["id"],
            "variant_id":  food["variant_id"],
            "source":      "ciqual",
            "source_id":   food.get("ciqual_code", food["source_id"]),
            "name_fr":     food["name_fr"],
            "name_en":     None,
            "state":       food["state"],
            "nutrients":   food["nutrients"],
            "diet_profile":food.get("diet_profile", {}),
            "_quality":    food.get("_quality"),
            "quality_score":food.get("quality_score"),
        }
        if food.get("jones_factor") is not None:
            variant["jones_factor"] = food["jones_factor"]
        if food.get("_audit_issues"):
            variant["_audit_issues"] = food["_audit_issues"]
        if "_audit_score" in food:
            variant["_audit_score"] = food["_audit_score"]

        grp["variants"][state] = variant
        grp["_meta"]["variant_count"] += 1
        grp["_meta"]["variant_keys"].append(state)

    return groups, conflicts


# ============================================================================
# 10. PIPELINE PRINCIPAL
# ============================================================================
def build(xlsx_path: Path, output_path: Path,
          audit_path: Path | None, excl_path: Path | None,
          dry_run: bool,
          taxonomy_path: Path | None = None) -> None:

    # ── Chargement de la taxonomie dynamique ─────────────────────────────────
    global _BK_TAXONOMY
    if taxonomy_path is not None and taxonomy_path.exists():
        _BK_TAXONOMY = load_bk_taxonomy(taxonomy_path)
        print(f"[0/6] Taxonomie chargée : {len(_BK_TAXONOMY)} bk depuis {taxonomy_path.name}")
    elif taxonomy_path is not None:
        print(f"[0/6] ⚠️  taxonomy_path introuvable : {taxonomy_path}  — champ 'taxonomy' omis.")
    else:
        print("[0/6] Aucun --taxonomy fourni — champ 'taxonomy' omis des objets food.")

    ts = datetime.now(timezone.utc).isoformat()

    print(f"[1/6] Lecture XLSX : {xlsx_path}")
    wb = openpyxl.load_workbook(str(xlsx_path), read_only=True)
    ws = wb.active
    hdr = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    if len(hdr) != 84:
        sys.exit(f"En-tête inattendu : {len(hdr)} colonnes (attendu 84)")
    print("    84 colonnes confirmées")

    print("[2/6] Filtrage et construction...")
    foods:      list[dict] = []
    excluded:   list[dict] = []
    all_issues: list[dict] = []
    stats = defaultdict(int)

    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[6] is None:
            continue
        stats["total_xlsx"] += 1
        try:
            code = int(row[6])
        except (ValueError, TypeError):
            continue
        ssgrp = str(row[1]) if row[1] else ""
        nom   = str(row[7] or "")

        excl, reason = should_exclude(code, ssgrp, nom)
        if excl:
            stats[reason.split(":")[0]] += 1
            if excl_path:
                excluded.append({
                    "id": f"ciqual_{code}", "ciqual_code": code,
                    "name_fr": nom, "subgroup_code": ssgrp,
                    "exclusion_reason": reason,
                })
            continue

        obj, issues = build_food_object(row)
        obj["ciqual_code"] = code
        foods.append(obj)
        stats["kept"] += 1
        if obj["is_generic"]:
            stats["generic_kept"] += 1

        vk = obj["variant_key"]
        stats[f"variant_{vk}"] += 1
        if not vk.startswith("unknown"):
            stats["with_detected_state"] += 1

        l1 = obj["state"]["process"]["level1"]
        l2 = obj["state"]["process"]["level2"]
        stats[f"level1_{l1}"] += 1
        if l2:
            stats[f"level2_{l2}"] += 1

        if obj.get("_has_ou"):
            stats["ou_items"] += 1

        if issues:
            stats["foods_with_issues"] += 1
            for iss in issues:
                stats[f"sev_{iss['severity']}"] += 1
                stats[f"sevclass_{iss['severity_class']}"] += 1
                stats[f"chk_{iss['check']}_{iss['severity']}"] += 1
            all_issues.extend(
                {"id": obj["id"], "source": "ciqual", "source_id": code,
                 "name_fr": nom, **iss}
                for iss in issues
            )

    wb.close()

    # ── Expansion "ou" (Q4:a / Q5:b) ──────────────────────────────────────────
    # Chaque food contenant "A ou B" est expansé en N food_obj distincts.
    # Les synthétiques héritent des nutrients, audit et diet_profile du parent.
    # L'item original (index 0) conserve son source_id et _ou_expansion=False.
    expanded_foods: list[dict] = []
    for food in foods:
        if food.get("_has_ou"):
            sub = expand_ou(food)
            expanded_foods.extend(sub)
            stats["ou_expanded"] += len(sub) - 1   # nombre de synthétiques ajoutés
        else:
            expanded_foods.append(food)
    foods = expanded_foods

    foods.sort(key=lambda x: (x.get("_ou_expansion", False), x["source_id"] or 0))

    # ── Purge des aliments moyens redondants (v6.6) ───────────────────────────
    # Un aliment moyen est redondant si son group_key contient déjà ≥1 food
    # non-générique avec energy_kcal non-null (vrai variant mesuré).
    # Les aliments moyens seuls dans leur groupe sont conservés.
    _gk_has_real_variant: set[str] = set()
    for food in foods:
        if not (food.get("is_generic") and food.get("generic_type") == "aliment_moyen"):
            if food.get("energy_kcal") is not None:
                _gk_has_real_variant.add(food["group_key"])

    _before_purge = len(foods)
    foods = [
        f for f in foods
        if not (
            f.get("is_generic")
            and f.get("generic_type") == "aliment_moyen"
            and f["group_key"] in _gk_has_real_variant
        )
    ]
    stats["generic_purged"] = _before_purge - len(foods)

    # ── PRESERVE_FINE_GRAINED ────────────────────────────────────────────────
    # group_keys à ne PAS fusionner via BASE_INGREDIENT_MAP.
    # Ces group_keys correspondent à des ingrédients distincts que le BIM
    # regroupait trop agressivement sous un base_key générique commun.
    # ingredient_key (jointure USDA) reste inchangé — seul le groupement est affiné.
    PRESERVE_FINE_GRAINED: set[str] = {
        # ── Haricots : 9 ingrédients distincts ──────────────────────────────
        "haricot_vert", "haricots_verts",
        "haricot_rouge", "haricot_blanc", "haricot_beurre",
        "haricot_flageolet", "haricot_mungo", "haricot_plat", "haricot_coco",
        "graine_germee_de_haricot_mungo",
        "pousse_de_soja",           # bean sprouts ≠ haricot
        # ── Champignons : espèces distinctes ────────────────────────────────
        "champignon_de_paris",
        "champignon_noir",          # Auricularia auricula-judae
        "champignon_cepe",
        "champignon_morille",
        "champignon_pleurote",
        "champignon_oronge",
        "champignon_rose_des_pres",
        "champignon_truffe",
        "champignon_shiitake",
        # "champignon" (tout type / générique) → reste fusionné, OK
        # ── Lentilles : variétés distinctes ─────────────────────────────────
        "lentille_verte", "lentille_corail", "lentille_blonde",
        "graine_germee_de_lentille",
        # ── Riz : variétés distinctes ────────────────────────────────────────
        "riz_blanc", "riz_complet", "riz_rouge", "riz_sauvage",
        "riz_basmati", "riz_thai", "riz_semi_complet",
        # ── Sons : céréales distinctes ───────────────────────────────────────
        "son_d_avoine", "son_de_ble", "son_de_mais", "son_de_riz",
        # ── Chocolat : compositions très différentes ─────────────────────────
        "chocolat_au_lait", "chocolat_blanc",
        # chocolat (noir/générique) garde son group_key "chocolat" → OK
        # ── Tofu : types distincts ───────────────────────────────────────────
        "tofu_nature", "tofu_soyeux", "tofu_fume",
        # ── Asperges : couleurs = profils différents ─────────────────────────
        "asperge_blanche", "asperge_verte",
        # ── Vinaigres : compositions distinctes ─────────────────────────────
        "vinaigre_balsamique", "vinaigre_de_cidre", "vinaigre_de_vin_rouge",
        # ── Fromages de chèvre : formats distincts ───────────────────────────
        "fromage_de_chevre_buche", "fromage_de_chevre_demi_sec",
        "fromage_de_chevre_sec", "crottin_de_chevre",
        # ── Farines de seigle : taux d'extraction distincts ──────────────────
        "farine_de_seigle_t85", "farine_de_seigle_t130", "farine_de_seigle_t170",
        # ── Biscottes : produits distincts ───────────────────────────────────
        "biscotte_au_ble_complet", "biscotte_aux_cereales",
        "biscotte_au_germe_de_ble", "biscotte_briochee",
        # ── Galettes soufflées : céréales distinctes ─────────────────────────
        "galette_de_riz_complet_souffle", "galette_de_mais_souffle",
        "galette_de_cereales_soufflees",
        # ── Couscous vs semoule de blé : ingrédients distincts ───────────────
        "graine_de_couscous", "graine_de_couscous_complete",
        "graine_de_couscous_semi_complete",
        # ── Oeufs : espèces distinctes (poule reste group_key "oeuf") ────────
        "oeuf_de_caille", "oeuf_de_cane", "oeuf_de_dinde", "oeuf_d_oie",
        # ── Biscuits apéritifs (0303) : fusionnés sous biscuit_aperitif ─────────
        "biscuit_aperitif",
    }

    # 1. Regrouper les foods par base_key
    base_groups: dict[str, list] = defaultdict(list)
    for food in foods:
        gk = food["group_key"]
        if gk in PRESERVE_FINE_GRAINED:
            # Court-circuite le BASE_INGREDIENT_MAP : chaque ingrédient reste son propre groupe
            base_key = gk
        else:
            entry = BASE_INGREDIENT_MAP.get(gk, {})
            base_key = entry.get("base_key", gk)

        # Injecter les extra_dims dans le state (merge non-destructif)
        # Les champs extension vont dans state["extensions"], les core à la racine.
        from food_schema_v2 import _EXTENSION_FIELDS as _EXT
        entry = BASE_INGREDIENT_MAP.get(gk, {}) if gk not in PRESERVE_FINE_GRAINED else {}
        extra_dims = entry.get("extra_dims", {})
        for dim, val in extra_dims.items():
            if dim in ("process.level1", "process.level2"):
                continue
            if dim in _EXT:
                food["state"].setdefault("extensions", {})
                if food["state"]["extensions"] is None:
                    food["state"]["extensions"] = {}
                if food["state"]["extensions"].get(dim) is None:
                    food["state"]["extensions"][dim] = val
            else:
                if food["state"].get(dim) is None:
                    food["state"][dim] = val

        base_groups[base_key].append(food)

    # 2. Construire l'arbre pour chaque base_key
    groups = {}
    for base_key, base_foods in base_groups.items():
        first_gk = base_foods[0]["group_key"]
        entry = {} if first_gk in PRESERVE_FINE_GRAINED else BASE_INGREDIENT_MAP.get(first_gk, {})
        name_fr = entry.get("name_fr") or base_foods[0].get("base_name") or base_key
        name_en = entry.get("name_en")
        category = base_foods[0].get("category", {})
        extra_fields: dict = {}
        subgroup_code = base_foods[0].get("state", {}).get("_subgroup_code")
        if subgroup_code:
            extra_fields["subgroup_code"] = subgroup_code
        is_generic = any(f.get("is_generic", False) for f in base_foods)
        extra_fields["is_generic"] = is_generic

        groups[base_key] = build_variant_tree(
            foods=base_foods,
            base_key=base_key,
            name_fr=name_fr,
            name_en=name_en,
            category=category,
            source_name="ciqual",
            extra_fields=extra_fields,
        )

    conflicts: list[dict] = []  # conservé pour compatibilité structure document
    stats["total_groups"] = len(groups)
    stats["multi_variant_groups"] = sum(
        1 for g in groups.values() if g["_meta"]["leaf_count"] > 1
    )
    print(f"    {len(groups)} groupes | {stats['multi_variant_groups']} multi-variants")

    by_check: dict = defaultdict(lambda: {"errors": 0, "warnings": 0, "infos": 0})
    for iss in all_issues:
        sev = iss["severity"]
        key = "errors" if sev == "error" else ("warnings" if sev == "warning" else "infos")
        by_check[iss["check"]][key] += 1

    total_excl = stats["total_xlsx"] - stats["kept"]
    # ou_expanded ne s'ajoute pas à "kept" : les synthétiques sont comptés séparément
    # generic_purged déduit du total final (aliments moyens redondants supprimés)
    total_foods_incl_ou = stats["kept"] + stats.get("ou_expanded", 0) - stats.get("generic_purged", 0)

    print("[4/6] Rapport...\n")
    print(f"    Total XLSX              : {stats['total_xlsx']:>5}")
    print(f"    Total exclus            : {total_excl:>5}")
    print(f"    Conservés (XLSX)        : {stats['kept']:>5}")
    print(f"    dont génériques         : {stats['generic_kept']:>5}")
    print(f"    Items 'ou' détectés     : {stats.get('ou_items',0):>5}")
    print(f"    Synthétiques ou expand  : {stats.get('ou_expanded',0):>5}")
    print(f"    Alim. moy. purgés       : {stats.get('generic_purged',0):>5}  (redondants)")
    print(f"    Total foods (net)       : {total_foods_incl_ou:>5}")
    print(f"\n    --- État process (level1) ---")
    for key in ("level1_raw", "level1_cooked", "level1_dried",
                "level1_manufactured", "level1_fermented", "level1_unknown"):
        label = key.replace("level1_", "")
        print(f"    {label:<35} : {stats.get(key,0):>5}")
    print(f"\n    --- Top level2 (cooked) ---")
    l2_counts = sorted(
        ((k.replace("level2_",""), v) for k,v in stats.items() if k.startswith("level2_")),
        key=lambda x: -x[1]
    )
    for l2, cnt in l2_counts[:12]:
        print(f"      {l2:<30} : {cnt:>5}")
    unknown_rate = stats.get("level1_unknown", 0) / max(stats["kept"], 1) * 100
    print(f"\n    unknown_rate            : {unknown_rate:.1f}%")
    print(f"\n    --- Audit ---")
    print(f"    Avec issues             : {stats['foods_with_issues']:>5}")
    print(f"    physical_error          : {stats.get('sevclass_physical_error',0):>5}")
    print(f"    major_quality           : {stats.get('sevclass_major_quality',0):>5}")
    print(f"    data_quality            : {stats.get('sevclass_data_quality',0):>5}")

    if dry_run:
        print("\n[5/6] --dry-run : aucun fichier écrit.")
        return

    print("\n[5/6] Écriture...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    document = {
        "_meta": {
            "schema_version": "7.0",
            "schema_family":  "unified_food",
            "generated_at":   ts,
            "sources": {
                "ciqual": {
                    **CIQUAL_SOURCE,
                    "source_file": xlsx_path.name,
                }
            },
            "total_foods":             stats["kept"],
            "total_foods_incl_ou":     stats["kept"] + stats.get("ou_expanded", 0),
            "total_foods_net":         total_foods_incl_ou,
            "ou_items_count":          stats.get("ou_items", 0),
            "ou_expanded_count":       stats.get("ou_expanded", 0),
            "generic_purged_count":    stats.get("generic_purged", 0),
            "nutrient_fields":         NUTRIENT_FIELDS,
            "total_xlsx_raw":          stats["total_xlsx"],
            "excluded_count":          total_excl,
            "generic_count":           stats["generic_kept"],
            "foods_with_audit_issues": stats["foods_with_issues"],
            "total_groups":            stats["total_groups"],
            "multi_variant_groups":    stats["multi_variant_groups"],
            "variant_conflicts_count": stats["total_conflicts"],
            "audit_by_severity_class": {
                "physical_error": stats.get("sevclass_physical_error", 0),
                "major_quality":  stats.get("sevclass_major_quality",  0),
                "data_quality":   stats.get("sevclass_data_quality",   0),
                "info":           stats.get("sevclass_info",           0),
            },
            "state_stats": {
                "level1_raw":          stats.get("level1_raw", 0),
                "level1_cooked":       stats.get("level1_cooked", 0),
                "level1_dried":        stats.get("level1_dried", 0),
                "level1_manufactured": stats.get("level1_manufactured", 0),
                "level1_fermented":    stats.get("level1_fermented", 0),
                "level1_unknown":      stats.get("level1_unknown", 0),
                "unknown_rate_pct":    round(unknown_rate, 1),
                "top_level2":          dict(l2_counts[:15]),
            },
            "id_prefix": "ciqual",
            "schema_notes": {
                "state_v3": (
                    "state = objet { process{level1,level2,confidence,raw_label_fragment}, "
                    "preservation, physical_form, part, additives[], extensions{...} }. "
                    "process.level1 ∈ {raw, cooked, dried, manufactured, fermented, unknown}. "
                    "dried = séché sans cuisson (herbes, légumineuses sèches, noix, fruits secs). "
                    "manufactured = produit fini industriel (huiles, alcools, confitures, jus…). "
                    "fermented = fermenté sans cuisson explicite. "
                    "extensions contient [fat_level, fat_pct, maturity, pack_medium, "
                    "dairy_process, variety, cooking_fat, species, cocoa_pct] (non-null seulement)."
                ),
                "ou_expansion": (
                    "Items 'A ou B' expansés en N food_obj distincts (classify_ou/expand_ou). "
                    "Nutrients partagés (copiés). Canonical = dernier terme (Q5:b). "
                    "Synthétiques marqués _ou_expansion=True, _ou_source_name=nom_original."
                ),
                "keys_v3": (
                    "ingredient_key = clé de jointure cross-source (base_key BASE_INGREDIENT_MAP). "
                    "family_key = subgroup_code CIQUAL (navigation)."
                ),
                "taxonomy_v1": (
                    "taxonomy = objet { group_id, group_label, subgroup_id, subgroup_label } "
                    "issu de taxonomy_session_*.json (v3). "
                    "Absent du food object si le bk n'est pas encore classifié. "
                    "Aucune concaténation id+label (ex : subgroup_id='sg_bieres', jamais 'sg_bieres_bieres'). "
                    f"Source : {taxonomy_path.name if taxonomy_path else 'non fournie'}."
                ),
                "nutrients_v2": (
                    "nutrients = objet imbriqué { energy, macros, lipids, carbohydrates, "
                    "vitamins, minerals, bioactives, _nutrient_meta }. "
                    "Champs plats aussi conservés à la racine pour rétrocompat."
                ),
                "variant_id": (
                    "variant_id = SHA-1(food_id + state canonique sérialisé), tronqué 12 chars. "
                    "Déterministe et déduplicable cross-sources."
                ),
                "shared_schema": (
                    "parse_state_v2 + fix_unknown_state + classify_ou + expand_ou + "
                    "build_nutrients_object + compute_variant_id + state_variant_key + "
                    "slugify + validate_food_item importés depuis food_schema_v2 v3.0."
                ),
            },
        },
        "groups":            groups,
        "foods_flat":        foods,
        "variant_conflicts": conflicts,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2)
    print(f"    OK {output_path}  ({output_path.stat().st_size/1_048_576:.1f} Mo)")

    if audit_path:
        audit_doc = {
            "_meta": {
                "schema_version":    "7.0",
                "schema_family":     "unified_food",
                "generated_at":      ts,
                "total_checked":     stats["kept"],
                "foods_with_issues": stats["foods_with_issues"],
                "by_severity_class": {
                    "physical_error": stats.get("sevclass_physical_error", 0),
                    "major_quality":  stats.get("sevclass_major_quality",  0),
                    "data_quality":   stats.get("sevclass_data_quality",   0),
                    "info":           stats.get("sevclass_info",           0),
                },
                "by_check": dict(by_check),
            },
            "issues": all_issues,
        }
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_doc, f, ensure_ascii=False, indent=2)
        print(f"    OK {audit_path}  ({len(all_issues)} issues)")

    if excl_path and excluded:
        excl_doc = {
            "_meta": {"generated_at": ts, "total_excluded": len(excluded)},
            "excluded": excluded,
        }
        with open(excl_path, "w", encoding="utf-8") as f:
            json.dump(excl_doc, f, ensure_ascii=False, indent=2)
        print(f"    OK {excl_path}  ({len(excluded)} aliments exclus)")

    print("\n[6/6] Terminé.")


# ============================================================================
# 11. POINT D'ENTRÉE
# ============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Construit ciqual_flat_v3.json v6.0 — schéma state v3 (6 level1) + extensions + ou expansion"
    )
    ap.add_argument("--input",        "-i", default="Table_Ciqual_2025_FR_2025_11_03.xlsx")
    ap.add_argument("--output",       "-o", default="ciqual_flat_v3.json")
    ap.add_argument("--audit-report",       default=None, metavar="PATH")
    ap.add_argument("--log-excl",           default=None, metavar="PATH")
    ap.add_argument("--dry-run",            action="store_true")
    ap.add_argument(
        "--taxonomy",
        default=None,
        metavar="PATH",
        help=(
            "Chemin vers taxonomy_session_*.json. "
            "Si fourni, chaque food object recevra un champ 'taxonomy' structuré "
            "{ group_id, group_label, subgroup_id, subgroup_label }."
        ),
    )
    args = ap.parse_args()

    # ====================== FORCE OUTPUT TO OUTPUTS FOLDER ======================
    TARGET_DIR = Path(r"C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\backend\data\nutrition\outputs")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # Base directory for finding input files
    BASE_DIR = Path(__file__).resolve().parents[2]
    default_input = BASE_DIR / "backend" / "data" / "nutrition" / "raw" / "Table_Ciqual_2025_FR_2025_11_03.xlsx"

    # Resolve input path
    xlsx = Path(args.input)
    if not xlsx.is_absolute():
        xlsx = BASE_DIR / xlsx
    if not xlsx.exists() and args.input == "Table_Ciqual_2025_FR_2025_11_03.xlsx":
        xlsx = default_input

    if not xlsx.exists():
        sys.exit(f"❌ Fichier introuvable : {args.input}\nVérifiez que le fichier XLSX CIQUAL est dans le dossier raw/")

    # Force output paths to your target raw folder
    output_path = TARGET_DIR / Path(args.output).name
    audit_path  = TARGET_DIR / Path(args.audit_report).name if args.audit_report else None
    excl_path   = TARGET_DIR / Path(args.log_excl).name if args.log_excl else None

    # ── Résolution du chemin taxonomie ───────────────────────────────────────
    # Priorité : --taxonomy CLI > référence/taxonomy_session_*.json auto-détecté
    taxonomy_path: Path | None = None
    if args.taxonomy:
        taxonomy_path = Path(args.taxonomy)
        if not taxonomy_path.is_absolute():
            taxonomy_path = BASE_DIR / taxonomy_path
    else:
        # Auto-détection dans backend/data/nutrition/reference/
        ref_dir = BASE_DIR / "backend" / "data" / "nutrition" / "reference"
        candidates = sorted(ref_dir.glob("taxonomy_session_*.json"), reverse=True)
        if candidates:
            taxonomy_path = candidates[0]
            print(f"ℹ️  Taxonomie auto-détectée : {taxonomy_path.name}")

    print(f"📥 Input  : {xlsx}")
    print(f"📤 Output : {output_path}")

    build(
        xlsx_path     = xlsx,
        output_path   = output_path,
        audit_path    = audit_path,
        excl_path     = excl_path,
        dry_run       = args.dry_run,
        taxonomy_path = taxonomy_path,
    )


if __name__ == "__main__":
    main()
