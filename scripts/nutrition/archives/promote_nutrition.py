"""
promote_nutrition.py
════════════════════
Promeut la meilleure source disponible → nutrition_v2.json après validation.

Priorité source (v14) :
  1. nutrition_patched_v8.json   (sortie patch_nutrition_v8, schema carbs_schema)
  2. nutrition_corrected.json    (sortie auto_correct_v6)
  → si aucun des deux n'existe : erreur explicite

Workflow :
  1. Résout la source (patched > corrected)
  2. Lit le numéro de version actuel dans nutrition_v2.json (_meta.schema_version)
  3. Archive nutrition_v2.json → archive/nutrition_v{N}.json
  4. Copie la source → nutrition_v2.json
  5. Met à jour _meta.schema_version + _meta.promoted_date dans le nouveau nutrition_v2.json
  6. (Optionnel) supprime la source si --clean

Usage :
  python scripts/nutrition/promote_nutrition.py            # dry-run (affiche ce qui sera fait)
  python scripts/nutrition/promote_nutrition.py --confirm  # exécute la promotion
  python scripts/nutrition/promote_nutrition.py --confirm --clean  # + supprime source
  python scripts/nutrition/promote_nutrition.py --source=corrected  # forcer corrected
  python scripts/nutrition/promote_nutrition.py --source=patched    # forcer patched

NOUVEAUTES v1.1 (vs v1.0) :
  - Support nutrition_patched_v8.json (priorité v14 : patched > corrected)
  - resolve_source() : sélection automatique avec log explicite
  - --source=patched|corrected : forçage manuel
  - Affiche le nom du fichier source dans le résumé
"""

import copy
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parents[2]

NUTRITION_DIR  = BASE_DIR / "backend" / "data" / "nutrition"
PROCESSED_DIR  = NUTRITION_DIR / "processed"
REFERENCE_DIR  = NUTRITION_DIR / "reference"
ARCHIVE_DIR    = PROCESSED_DIR / "archive"

CANONICAL_FILE  = PROCESSED_DIR / "nutrition_v2.json"
CORRECTED_FILE  = REFERENCE_DIR / "nutrition_corrected.json"
# v14 : sortie de patch_nutrition_v8 — priorité maximale
PATCHED_FILE    = REFERENCE_DIR / "nutrition_patched_v8.json"
# Ontologie (générée à l'étape 1 du pipeline — stockée dans reference/)
ONTOLOGY_FILE   = NUTRITION_DIR / "reference" / "ontology_v6.json"

TODAY = datetime.now().strftime("%Y-%m-%d")

# ── Base-recipe purge ──────────────────────────────────────────────────────────
# Ces clés sont des recettes de base dont la valeur nutritionnelle est calculée
# dynamiquement depuis leur composition-recette — elles ne doivent PAS exister
# comme variants nutritionnels dans nutrition_v2.
# Source : rapport d'incohérences §2 — 9 clés survivantes du pipeline legacy.
# La correction STATIC_BASE_RECIPE_KEYS dans build_ontology empêche de nouveaux
# variants, mais ne purge pas les entrées déjà présentes dans nutrition_v2.
# Ce set complète _clean_base_recipe_variants() pour une purge totale.
# ── Mode par ingrédient ───────────────────────────────────────────────────
# "base_recipe" : valeur nutritionnelle calculée dynamiquement depuis la
#                 composition de la recette → entrée SUPPRIMÉE de nutrition_v2.
# "indus"       : produit industriel ou ingrédient simple avec données
#                 nutritionnelles validées → entrée CONSERVÉE dans nutrition_v2.
#
# Pour changer le mode d'un ingrédient, modifier sa valeur ici.
# Les nouveaux ingrédients ambigus peuvent être ajoutés avec le mode approprié.
BASE_RECIPE_MODES: dict[str, str] = {
    # ── Recettes composées pures → toujours base_recipe ──────────────────
    # Valeur nutritionnelle = somme des ingrédients, pas une donnée fixe.
    "chili_paste":      "base_recipe",
    "empanada_dough":   "base_recipe",
    "gochujang":        "base_recipe",
    "harissa":          "base_recipe",
    "natto":            "base_recipe",
    "pesto":            "base_recipe",
    "tamarind_paste":   "base_recipe",
    "falafel":          "base_recipe",   # recette composée (chickpeas+herbes) — 3 recettes dans recipes.json

    # ── Plats préparés migrés vers recipes.json (2026-05-01) ─────────────
    # Ces entrées avaient des données nutritionnelles figées dans nutrition_v2
    # mais sont des plats composés — leur valeur doit être calculée depuis
    # leur composition. Recettes CDC v6 créées dans recipes.json.
    "kombucha":         "base_recipe",   # boisson fermentée → beverage_kombucha_3df24c
    "buckwheat_crepe":  "base_recipe",   # galette sarrasin  → bread_buckwheat_crepe_03db22
    "crackers":         "base_recipe",   # biscuit sec       → snack_crackers_35f6a8
    "fried_rice":       "base_recipe",   # riz cantonais     → main_fried_rice_a6e811
    "gnocchi":          "base_recipe",   # gnocchis          → main_gnocchi_f17041
    "fried_onion":      "base_recipe",   # oignon frit       → condiment_fried_onion_217e6a

    # ── Ingrédients simples avec données validées → indus disponible ──────
    # Ces ingrédients ont des données CIQUAL/USDA dans l'ontologie.
    # Mode "indus" = conserver les valeurs nutritionnelles dans nutrition_v2.
    # Mode "base_recipe" = calculer depuis la composition (si recette définie).
    "seitan":           "indus",   # CIQUAL "Seitan, préemballé" 134 kcal
    "tahini":           "indus",   # USDA FDC #168573 + CIQUAL "Tahin" 631 kcal
}

# Rétrocompatibilité — utilisé par build_ontology pour filtrer les variants
STATIC_BASE_RECIPE_KEYS: frozenset[str] = frozenset(
    k for k, v in BASE_RECIPE_MODES.items() if v == "base_recipe"
)


# ══════════════════════════════════════════════════════════════════════════════
# RÈGLES ALLERGÈNES — EU Reg. 1169/2011 (14 allergènes obligatoires)
# Appliquées automatiquement à chaque promote --confirm.
#
# Deux niveaux :
#   BASE_ALLERGEN_RULES   : s'appliquent à TOUS les variants d'une base.
#                           Ajouter ici quand l'allergen est intrinsèque
#                           à l'ingrédient, quelle que soit sa forme.
#
#   VARIANT_ALLERGEN_RULES : s'appliquent à un (base, variant) précis.
#                           Utiliser pour les bases "mixtes" où certains
#                           variants sont allergènes et d'autres non
#                           (ex: flour/wheat vs flour/rice, butter/dairy vs
#                           butter/coconut).
#
# Règles :
#   - Allergènes INTRINSÈQUES uniquement (pas de contamination croisée).
#   - Idempotent : on n'ajoute que ce qui manque, on ne retire jamais.
#   - Pour ajouter un nouvel ingrédient : une ligne dans le bon bloc,
#     avec un commentaire justifiant la classification EU.
#
# Faux positifs exclus explicitement :
#   butter/peanut  → peanut ✅, milk ❌  (beurre de cacahuète, sans lait)
#   squash/butternut → ❌  (courge, aucun allergène)
#   flax_egg/default → ❌  (substitut végétal, pas d'œuf)
#   tamarind/default → ❌  (tamarin ≠ tamari, regex exclue)
# ══════════════════════════════════════════════════════════════════════════════

# Clé base → allergènes à appliquer sur TOUS ses variants
BASE_ALLERGEN_RULES: dict[str, list[str]] = {
    # ── GLUTEN ────────────────────────────────────────────────────────────────
    "barley":          ["gluten"],   # orge — céréale gluten
    "bread":           ["gluten"],   # tout pain contient gluten (sauf recettes GF explicites)
    "breadcrumbs":     ["gluten"],   # chapelure de blé
    "seitan":          ["gluten"],   # gluten de blé pur
    "spelt":           ["gluten"],   # épeautre — céréale gluten
    "wheat_germ":      ["gluten"],   # germe de blé
    "wheat_grass":     ["gluten"],   # herbe de blé

    # ── NUTS — fruits à coque EU (Annexe II) ──────────────────────────────────
    "almond":          ["nuts"],     # amande
    "cashew":          ["nuts"],     # noix de cajou
    "chestnut":        ["nuts"],     # châtaigne / marron (inclus EU)
    "hazelnut":        ["nuts"],     # noisette
    "macadamia":       ["nuts"],     # noix de macadamia
    "nut":             ["nuts"],     # noix (nut/brazil, nut/pine…)
    "pecan":           ["nuts"],     # noix de pécan
    "pistachio":       ["nuts"],     # pistache
    "walnut":          ["nuts"],     # noix

    # ── MILK ──────────────────────────────────────────────────────────────────
    "cheese":          ["milk"],     # tous les fromages
    "cheese_curds":    ["milk"],     # fromage blanc / caillé
    "cream_animal":    ["milk"],     # crème fraîche, crème liquide
    "fromage_blanc":   ["milk"],     # fromage blanc
    "greek_yogurt":    ["milk"],     # yaourt grec (variant milk_animal)
    "milk_animal":     ["milk"],     # lait animal (entier, écrémé…)
    "yogurt_animal":   ["milk"],     # yaourts animaux

    # ── SOY ───────────────────────────────────────────────────────────────────
    "edamame":         ["soy"],      # haricots de soja frais
    "miso":            ["soy"],      # pâte de soja fermentée
    "tamari":          ["soy"],      # sauce tamari = soja
    "tempeh":          ["soy"],      # soja fermenté
    "tofu":            ["soy"],      # tofu = coagulat soja

    # ── SESAME ────────────────────────────────────────────────────────────────
    "sesame":          ["sesame"],   # sesame/* (tahini_raw…)
    "tahini":          ["sesame"],   # purée de sésame

    # ── PEANUT ────────────────────────────────────────────────────────────────
    "peanut":          ["peanut"],   # cacahuète sous toutes ses formes

    # ── EGG ───────────────────────────────────────────────────────────────────
    "egg":             ["egg"],      # œuf entier
    "hard_boiled_egg": ["egg"],      # œuf dur

    # ── MUSTARD ───────────────────────────────────────────────────────────────
    "mustard":         ["mustard"],  # moutarde (condiment)
}

# (base, variant) → allergènes à appliquer sur CE variant uniquement.
# Utilisé pour les bases où tous les variants ne partagent pas le même allergène.
VARIANT_ALLERGEN_RULES: dict[tuple[str, str], list[str]] = {
    # ── GLUTEN — farines (seules les céréales à gluten) ──────────────────────
    ("flour", "oat"):         ["gluten"],   # avoine — classé gluten EU (contamination)
    ("flour", "rye"):         ["gluten"],   # seigle
    ("flour", "spelt"):       ["gluten"],   # épeautre
    ("flour", "wheat"):       ["gluten"],   # blé
    ("flour", "whole_wheat"): ["gluten"],   # blé complet
    # flour/almond → nuts (ci-dessous), flour/rice/corn/potato → rien

    # ── GLUTEN — pâtes (uniquement blé/seigle, pas rice/soba pur) ────────────
    ("pasta", "noodles"):     ["gluten"],   # nouilles de blé
    ("pasta", "orzo"):        ["gluten"],   # orzo = petites pâtes de blé
    ("pasta", "soba"):        ["gluten"],   # soba FR = mélange blé+sarrasin
    ("pasta", "udon"):        ["gluten"],   # udon = blé
    ("pasta", "wheat"):       ["gluten"],   # pâtes de blé générique
    ("pasta", "ziti"):        ["gluten"],   # ziti = blé

    # ── NUTS — cas particuliers (bases mixtes) ────────────────────────────────
    ("butter", "almond"):     ["nuts"],     # beurre d'amande
    ("flour",  "almond"):     ["nuts"],     # farine d'amande

    # ── MILK — cas particuliers ───────────────────────────────────────────────
    ("butter", "dairy"):      ["milk"],     # beurre laitier
    ("sauce",  "yogurt"):     ["milk"],     # sauce au yaourt

    # ── SOY — cas particuliers ────────────────────────────────────────────────
    # (toutes les bases soy déjà couvertes en BASE_ALLERGEN_RULES)

    # ── SESAME — cas particuliers (seeds est une base mixte) ─────────────────
    ("seeds", "sesame"):       ["sesame"],  # graines de sésame blanc
    ("seeds", "black_sesame"): ["sesame"],  # graines de sésame noir
    ("oil",   "sesame"):       ["sesame"],  # huile de sésame

    # ── PEANUT — cas particuliers ─────────────────────────────────────────────
    ("butter", "peanut"):     ["peanut"],   # beurre de cacahuète (pas de milk !)
    ("oil",    "peanut"):     ["peanut"],   # huile d'arachide

    # ── MUSTARD — cas particuliers (seeds est une base mixte) ────────────────
    ("seeds", "mustard"):     ["mustard"],  # graines de moutarde
}



# ══════════════════════════════════════════════════════════════════════════════
# RESTRUCTURE NODES — voir restructure_nutrition_v2.py (script autonome, step 10)
# Cette section a été déplacée vers restructure_nutrition_v2.py qui est la
# version canonique appelée par reset_pipeline.bat. Les fonctions ci-dessous
# (_get_onto_nutrients, _build_variant_from_onto, _copy_leaf_as_variant,
# _infer_type_from_key, _restructure_nodes) sont importées depuis ce module si
# besoin d'un import direct.
# ══════════════════════════════════════════════════════════════════════════════
try:
    from restructure_nutrition_v2 import (
        _get_onto_nutrients, _build_variant_from_onto,
        _copy_leaf_as_variant, _infer_type_from_key,
        _restructure_nodes,
    )
except ImportError:
    # restructure_nutrition_v2.py non disponible en import — OK si non utilisé en import.
    pass


def resolve_source(force: str | None = None) -> Path:
    """
    Résout le fichier source à promouvoir, par ordre de priorité :
      1. --source=patched   → PATCHED_FILE
      2. --source=corrected → CORRECTED_FILE
      3. auto : PATCHED_FILE si présent, sinon CORRECTED_FILE
    Lève FileNotFoundError si le fichier résolu n'existe pas.
    """
    if force == "patched":
        if not PATCHED_FILE.exists():
            raise FileNotFoundError(f"--source=patched : fichier introuvable :\n   {PATCHED_FILE}")
        print(f"  Source (forcée) : nutrition_patched_v8.json")
        return PATCHED_FILE
    if force == "corrected":
        if not CORRECTED_FILE.exists():
            raise FileNotFoundError(f"--source=corrected : fichier introuvable :\n   {CORRECTED_FILE}")
        print(f"  Source (forcée) : nutrition_corrected.json")
        return CORRECTED_FILE
    # Auto
    if PATCHED_FILE.exists():
        print(f"  Source (auto)   : nutrition_patched_v8.json  [priorité v14]")
        return PATCHED_FILE
    if CORRECTED_FILE.exists():
        print(f"  Source (auto)   : nutrition_corrected.json")
        return CORRECTED_FILE
    raise FileNotFoundError(
        "Aucune source disponible :\n"
        f"   {PATCHED_FILE}\n"
        f"   {CORRECTED_FILE}\n"
        "Lancer d'abord : patch_nutrition_v7.py  ou  auto_correct_v6.py"
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_meta(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        db = json.load(f)
    return db.get("_meta", {})


def read_schema_version(meta: dict, filepath: Path) -> str:
    """
    Lit schema_version depuis _meta (champ canonique).
    Accepte aussi 'version' pour la rétro-compatibilité.
    Lève ValueError si aucun champ n'est présent — refus de deviner depuis le nom de fichier.
    """
    version = meta.get("schema_version") or meta.get("version")
    if not version:
        raise ValueError(
            f"Impossible de déterminer la version de {filepath.name} : "
            f"_meta.schema_version absent. Vérifier le fichier avant promotion."
        )
    return str(version)


def next_archive_path(version_str: str) -> Path:
    """
    Détermine le chemin d'archive : archive/nutrition_v{N}.json
    Si version_str = "2.1", archive = nutrition_v2.1.json
    Si déjà pris, incrémente le suffixe : nutrition_v2.1.1.json
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    base_name = f"nutrition_v{version_str}.json"
    candidate = ARCHIVE_DIR / base_name
    counter = 1
    while candidate.exists():
        candidate = ARCHIVE_DIR / f"nutrition_v{version_str}.{counter}.json"
        counter += 1
    return candidate


def bump_version(version_str: str) -> str:
    """
    Incrémente la version mineure : "2" → "2.1", "2.1" → "2.2", "2.9" → "2.10"
    """
    parts = str(version_str).split(".")
    if len(parts) == 1:
        return f"{parts[0]}.1"
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except ValueError:
        parts.append("1")
    return ".".join(parts)


# ── Main ──────────────────────────────────────────────────────────────────────

def promote(dry_run: bool = True, clean_source: bool = False, force_source: str | None = None):
    print("══════════════════════════════════════════════════════")
    print(f"  PROMOTE NUTRITION {'[DRY-RUN]' if dry_run else '[EXÉCUTION]'}")
    print("══════════════════════════════════════════════════════\n")

    # ── Résolution de la source ───────────────────────────────────────────────
    try:
        source_file = resolve_source(force_source)
    except FileNotFoundError as e:
        print(f"  ❌ {e}")
        return 1

    # ── Vérifications préalables ──────────────────────────────────────────────
    if not CANONICAL_FILE.exists():
        print("  ⚠  nutrition_v2.json absent — création directe sans archivage.")
        archive_path = None
        current_version = "1"
    else:
        # Fraîcheur relative
        if source_file.stat().st_mtime <= CANONICAL_FILE.stat().st_mtime:
            print(f"  ⚠  {source_file.name} n'est pas plus récent que nutrition_v2.json.")
            print("     Regénérer la source ou utiliser --force.")

        # Fix P2 : root.schema_version prime sur _meta.schema_version.
        # _meta peut rester bloqué si la source écrasée avait un _meta
        # désynchronisé — root est toujours réécrit à chaque promote.
        with open(CANONICAL_FILE, encoding="utf-8") as _f:
            _canon = json.load(_f)
        _root_sv = _canon.get("schema_version")
        meta = _canon.get("_meta", {})
        _sv_src = {"schema_version": _root_sv} if _root_sv else meta
        try:
            current_version = read_schema_version(_sv_src, CANONICAL_FILE)
        except ValueError as e:
            print(f"  ❌ {e}")
            return 1
        archive_path = next_archive_path(current_version)

    new_version = bump_version(current_version)

    # ── Résumé des opérations ─────────────────────────────────────────────────
    print(f"  Version actuelle : {current_version}")
    print(f"  Nouvelle version : {new_version}")
    if archive_path:
        print(f"  Archive          : {archive_path.relative_to(BASE_DIR)}")
    print(f"  Cible            : {CANONICAL_FILE.relative_to(BASE_DIR)}")
    print(f"  Source           : {source_file.relative_to(BASE_DIR)}")
    if clean_source:
        print(f"  Nettoyage        : suppression de {source_file.name} après promotion")

    if dry_run:
        print("\n  ──────────────────────────────────────────────────")
        print("  Dry-run : aucune modification. Ajouter --confirm pour exécuter.")
        print("  ══════════════════════════════════════════════════\n")
        return 0

    # ── Exécution ─────────────────────────────────────────────────────────────
    print()

    # 1. Archiver l'ancien canonical
    if archive_path and CANONICAL_FILE.exists():
        shutil.copy2(CANONICAL_FILE, archive_path)
        print(f"  💾 Archivé  → {archive_path.name}")

    # 2. Charger la source, mettre à jour _meta, écrire canonical
    with open(source_file, encoding="utf-8") as f:
        db = json.load(f)

    db.setdefault("_meta", {})

    # Respecter la version explicite de la source si elle est supérieure
    source_sv = db.get("schema_version") or db.get("_meta", {}).get("schema_version")
    try:
        use_version = (
            source_sv
            if source_sv and tuple(int(x) for x in str(source_sv).split(".")) >
               tuple(int(x) for x in new_version.split("."))
            else new_version
        )
    except (ValueError, TypeError):
        use_version = new_version

    db["_meta"]["schema_version"]   = use_version
    db["schema_version"]            = use_version   # fix P0 (rapport_incoherences_v2 §1) : root.schema_version était bloqué à 6.0
    db["_meta"]["promoted_date"]    = TODAY
    db["_meta"]["promoted_from"]    = source_file.name
    db["_meta"]["previous_version"] = current_version

    with open(CANONICAL_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    ing_count = len(db.get("ingredients", {}))
    print(f"  ✅ Promo    → {CANONICAL_FILE.name}  (v{use_version}, {ing_count} ingrédients)")

    # 3. Optionnel : supprimer la source
    if clean_source:
        source_file.unlink()
        print(f"  🗑  Supprimé → {source_file.name}")

    # 4. Promouvoir les items CIQUAL mapped=ABSENT vers nutrition_v2
    #    (bug de pipeline : ces items sont dans ciqual_flat_v3 mais jamais injectés)
    _promote_ciqual_absent(CANONICAL_FILE)

    # 5. Appliquer les règles allergènes EU 1169/2011
    #    Déclaratives, idempotentes — s'appliquent à chaque promote.
    _apply_allergen_rules(CANONICAL_FILE)

    # 6. Appliquer la classification NOVA (Monteiro 2019)
    #    Reclassifie les variants sous-classés : fermentés → 3, ultra-transformés → 4.
    #    Idempotente, déclarative.
    _apply_nova_rules(CANONICAL_FILE)

    # 7. Purger les entrées base_recipe de nutrition_v2
    #    Passe 1 (marqueur) : supprime les variants listés dans _base_recipe_excluded.
    #    Passe 2 (statique) : supprime intégralement les base_keys de STATIC_BASE_RECIPE_KEYS
    #    héritées du pipeline legacy (chili_paste, gochujang, harissa, natto, pesto,
    #    seitan, tahini, tamarind_paste, empanada_dough) — rapport d'incohérences §2.
    _clean_base_recipe_variants(CANONICAL_FILE)

    # 8. Fusionner les doublons sémantiques (pluriel/singulier)
    #    snow_peas → snow_pea  |  capers → caper
    #    Idempotent — sans effet si les alias sont déjà absents.
    _merge_semantic_duplicates(CANONICAL_FILE)

    # 9. Recalculer les compteurs top-level depuis le contenu réel
    #    total_bases, total_variants, standalone_bases
    #    Garantit la cohérence après toutes les passes de purge/fusion.
    _recompute_meta_counters(CANONICAL_FILE)

    # NOTE : la restructuration structurelle (step 10 pipeline) est appelée
    # par reset_pipeline.bat APRÈS les patches 7b→7e, via restructure_nutrition_v2.py.
    # _restructure_nodes() reste disponible ici pour import direct si besoin.

    print(f"\n  {'='*50}")
    print(f"  Promotion v{current_version} → v{use_version} terminée.")
    print(f"  Archive : {ARCHIVE_DIR.relative_to(BASE_DIR)}/\n")
    return 0


# ── Table des fusions sémantiques ────────────────────────────────────────────
# Format : alias_à_supprimer → clé_canonique_à_conserver
# Règle : on garde le singulier EN snake_case (convention du projet).
# En cas de micro-écart de valeurs, la clé canonique fait foi.
SEMANTIC_DUPLICATES: dict[str, str] = {
    "snow_peas": "snow_pea",   # données identiques, pluriel redondant
    "capers":    "caper",      # micro-écart (protein 2.36 vs 2.4) → caper conservé
}


def _merge_semantic_duplicates(n2_path: Path) -> None:
    """
    Supprime les alias pluriel/singulier redondants de nutrition_v2.

    Pour chaque paire dans SEMANTIC_DUPLICATES :
      - Vérifie que la clé canonique existe (sinon skip avec warning).
      - Supprime l'alias si présent.
      - Idempotent — sans effet si l'alias est déjà absent.

    Intégré dans le build (promote_nutrition --confirm), step 8.
    """
    with open(n2_path, encoding="utf-8") as _f:
        n2 = json.load(_f)
    ings = n2["ingredients"]
    removed = []
    skipped = []

    for alias, canonical in SEMANTIC_DUPLICATES.items():
        if alias not in ings:
            continue  # déjà absent — idempotent
        if canonical not in ings:
            skipped.append(f"{alias} (canonique '{canonical}' introuvable)")
            continue
        del ings[alias]
        removed.append(f"{alias} → {canonical}")

    if removed:
        with open(n2_path, "w", encoding="utf-8") as fh:
            json.dump(n2, fh, ensure_ascii=False, indent=2)
        print(f"  Doublons fusionnés ({len(removed)}) :")
        for r in removed:
            print(f"    - {r}")
    else:
        print("  Doublons sémantiques : déjà fusionnés (idempotent)")

    for s in skipped:
        print(f"  ⚠ SKIP fusion : {s}")


def _recompute_meta_counters(n2_path: Path) -> None:
    """
    Recalcule et écrit les compteurs top-level de nutrition_v2 depuis le contenu réel :
      - total_bases      : len(ingredients)
      - total_variants   : somme de len(variants) pour chaque base
      - standalone_bases : bases avec _meta.is_standalone == True

    Doit être appelé en dernier, après toutes les passes de purge et fusion,
    pour garantir la cohérence des métadonnées.

    Intégré dans le build (promote_nutrition --confirm), step 9.
    """
    with open(n2_path, encoding="utf-8") as _f:
        n2 = json.load(_f)
    ings = n2["ingredients"]

    total_bases      = len(ings)
    total_variants   = sum(len(v.get("variants", {})) for v in ings.values())
    standalone_bases = sum(
        1 for v in ings.values()
        if v.get("_meta", {}).get("is_standalone", False)
    )

    old = {
        "total_bases":      n2.get("total_bases"),
        "total_variants":   n2.get("total_variants"),
        "standalone_bases": n2.get("standalone_bases"),
    }

    n2["total_bases"]      = total_bases
    n2["total_variants"]   = total_variants
    n2["standalone_bases"] = standalone_bases

    with open(n2_path, "w", encoding="utf-8") as fh:
        json.dump(n2, fh, ensure_ascii=False, indent=2)

    changed = {k for k in old if old[k] != n2[k]}
    if changed:
        print("  Compteurs recalculés :")
        for k in ("total_bases", "total_variants", "standalone_bases"):
            marker = " ← corrigé" if k in changed else ""
            print(f"    {k}: {old[k]} → {n2[k]}{marker}")
    else:
        print("  Compteurs top-level : déjà cohérents")


def _promote_ciqual_absent(n2_path: Path) -> None:
    """
    Injecte dans nutrition_v2 les items CIQUAL utiles qui sont restés mapped=ABSENT
    à cause d'un bug de pipeline (non-promotion des group_keys fins, ex: champignon_cepe).

    ⚠️  SÉCURITÉ — Approche WHITELIST uniquement :
    Cette fonction n'itère PAS sur tous les items mapped=ABSENT.
    Elle utilise exclusivement PROMOTE_MAP — une liste curative et explicite
    des group_keys utiles à promouvoir.

    Cela garantit que les items délibérément rejetés par build_ciqual_flat_v3.py
    (via should_exclude → EXCL_SUBGROUPS_HARD, EXCL_CODES_HARD, ultratrans,
    edulcorant_excl, dom_tom_excl) restent ABSENT et ne sont jamais injectés ici.

    Idempotent : si le variant est déjà dans nutrition_v2, il est ignoré.
    Appelé automatiquement à chaque `promote_nutrition.py --confirm`.

    Pour ajouter un nouvel item :
      → Ajouter une entrée dans PROMOTE_MAP ci-dessous avec justification.
      → NE PAS utiliser de scan générique des mapped=ABSENT.
    """
    ciqual_path = BASE_DIR / "backend/data/nutrition/outputs/ciqual_flat_v3.json"
    if not ciqual_path.exists():
        print("  ⚠  ciqual_flat_v3.json absent — promotion CIQUAL absente ignorée")
        return

    with open(n2_path, encoding="utf-8") as _f:
        n2 = json.load(_f)
    with open(ciqual_path, encoding="utf-8") as _f:
        ciqual = json.load(_f)
    ings   = n2["ingredients"]
    foods  = ciqual.get("foods_flat", [])

    # Indexer les absents par group_key (premier item = meilleur)
    absent_by_gk: dict = {}
    for f in foods:
        if not f.get("mapped_to") or f.get("mapped_to") == "ABSENT":
            gk = f.get("group_key") or ""
            if gk not in absent_by_gk:
                absent_by_gk[gk] = f

    # Mapping culinaire group_key → (base_n2, variant_key, name_fr, name_en)
    PROMOTE_MAP = {
        "champignon_cepe":        ("mushroom", "porcini",     "Cèpe",        "porcini"),
        "champignon_morille":     ("mushroom", "morel",       "Morille",     "morel"),
        "champignon_pleurote":    ("mushroom", "oyster",      "Pleurote",    "oyster mushroom"),
        "champignon_chanterelle": ("mushroom", "chanterelle", "Chanterelle", "chanterelle"),
        "champignon_shiitake":    ("mushroom", "shiitake",    "Shiitake",    "shiitake"),
        "champignon_noir":        ("mushroom", "wood_ear",    "Champignon noir", "wood ear"),
        "pois_gourmands":         ("bean",     "snow_pea",    "Pois gourmands",  "snow peas"),
        "pate_filo":              ("pastry",   "phyllo",      "Pâte filo",   "phyllo pastry"),
        "marron":                 ("chestnut", "cooked",      "Marron cuit", "cooked chestnut"),
    }

    CIQUAL_SRC = {"name": "CIQUAL", "version": "2020",
                  "url": "https://ciqual.anses.fr", "confidence": 0.92}

    promoted = 0
    for gk, (base_key, var_key, name_fr, name_en) in PROMOTE_MAP.items():
        item = absent_by_gk.get(gk)
        if item is None:
            continue
        kcal = item.get("calories_kcal") or item.get("energy_kcal")
        if not kcal:
            continue
        base_entry = ings.setdefault(base_key, {
            "_meta": {"category": "other", "name_fr": name_fr, "is_standalone": False},
            "variants": {}
        })
        variants = base_entry.setdefault("variants", {})
        if var_key in variants:
            continue   # idempotent — déjà présent

        def _g(k, d=None):
            v = item.get(k)
            return v if v is not None else d

        variants[var_key] = {
            "name_fr": name_fr, "name_en": name_en,
            "source_key": item.get("id", ""),
            "ingredient_type": "raw",
            "calories_kcal":  round(float(kcal), 1),
            "protein_g":      round(float(_g("protein_g", 0) or 0), 3),
            "carbs_g":        round(float(_g("carbs_g",   0) or 0), 3),
            "fat_g":          round(float(_g("fat_g",     0) or 0), 3),
            "fiber_g":        round(float(_g("fiber_g",   0) or 0), 3),
            "sugar_g":        round(float(_g("sugar_g",   0) or 0), 3),
            "added_sugar": 0, "alcohol_g": 0.0,
            "sodium_mg":    _g("sodium_mg", 0),
            "calcium_mg":   _g("calcium_mg"), "iron_mg":       _g("iron_mg"),
            "magnesium_mg": _g("magnesium_mg"), "phosphorus_mg": _g("phosphorus_mg"),
            "potassium_mg": _g("potassium_mg"), "zinc_mg":       _g("zinc_mg"),
            "vitamin_c_mg": _g("vitamin_c_mg"), "vitamin_d_ug":  _g("vitamin_d_ug"),
            "folate_ug":    _g("folate_ug"),    "vitamin_b12_ug":_g("vitamin_b12_ug", 0),
            "nova_group": 1, "allergens": [],
            "confidence": 0.90, "sources": [CIQUAL_SRC],
            "last_updated": TODAY, "version": 1, "data_quality": "high",
        }
        item["mapped_to"] = f"{base_key}/{var_key}"
        promoted += 1

    if promoted:
        with open(n2_path, "w", encoding="utf-8") as fh:
            json.dump(n2, fh, ensure_ascii=False, indent=2)
        with open(ciqual_path, "w", encoding="utf-8") as fh:
            json.dump(ciqual, fh, ensure_ascii=False, indent=2)
        print(f"  ✅ CIQUAL absent→n2 : {promoted} variants injectés")
    else:
        print(f"  ✅ CIQUAL absent→n2 : tous déjà présents (idempotent)")



def _apply_allergen_rules(n2_path: Path) -> None:
    """
    Applique BASE_ALLERGEN_RULES et VARIANT_ALLERGEN_RULES sur nutrition_v2.json.

    Logique :
      1. Pour chaque base dans BASE_ALLERGEN_RULES : injecter les allergènes
         sur TOUS ses variants présents dans n2.
      2. Pour chaque (base, variant) dans VARIANT_ALLERGEN_RULES : injecter
         les allergènes sur CE variant uniquement.
      3. Idempotent : on ne fait qu'ajouter (union de sets), jamais supprimer.
      4. Les bases / variants absents de n2 sont silencieusement ignorés
         (logs disponibles en mode verbose).

    Appelée automatiquement par promote() après _promote_ciqual_absent()
    et avant _clean_base_recipe_variants().
    """
    with open(n2_path, encoding="utf-8") as _f:
        n2 = json.load(_f)
    ings = n2["ingredients"]
    # ── Passe 0 : init allergens:[] (rapport_incoherences_v2 §12) ──────────
    # 5 variants orphelins (ancho_chili, chinese_cabbage, dandelion, chicory,
    # dried_pea) n'ont pas de champ allergens car absents des règles.
    # Pour tout variant sans ce champ : allergens=[] (idempotent).
    _allergen_init = 0
    for _bk, _entry in ings.items():
        for _vname, _vdata in _entry.get("variants", {}).items():
            if isinstance(_vdata, dict) and "allergens" not in _vdata:
                _vdata["allergens"] = []
                _allergen_init += 1
    if _allergen_init:
        print(f"  ✅ Allergens init : {_allergen_init} variant(s) → allergens=[]")


    added_count   = 0
    touched_paths: list[str] = []

    def _inject(variant_dict: dict, allergens: list[str], path: str) -> None:
        nonlocal added_count
        existing = set(variant_dict.get("allergens", []))
        to_add   = [a for a in allergens if a not in existing]
        if to_add:
            variant_dict["allergens"] = sorted(existing | set(to_add))
            added_count += len(to_add)
            touched_paths.append(f"{path} +{','.join(to_add)}")

    # ── 1. Règles par base (tous variants) ───────────────────────────────────
    for base_key, allergens in BASE_ALLERGEN_RULES.items():
        base_entry = ings.get(base_key)
        if base_entry is None:
            continue
        for var_key, var_data in base_entry.get("variants", {}).items():
            _inject(var_data, allergens, f"{base_key}/{var_key}")

    # ── 2. Règles par variant (cas mixtes) ───────────────────────────────────
    for (base_key, var_key), allergens in VARIANT_ALLERGEN_RULES.items():
        base_entry = ings.get(base_key)
        if base_entry is None:
            continue
        var_data = base_entry.get("variants", {}).get(var_key)
        if var_data is None:
            continue
        _inject(var_data, allergens, f"{base_key}/{var_key}")

    # ── Passe 3 : synchronisation diet_profile ↔ allergen_flags ─────────────
    # Après injection des allergènes, certains diet_profile peuvent être
    # contradictoires (ex: milk_plant a dairy_free=True mais allergens=[milk]).
    # Règle : les allergens font autorité → on corrige diet_profile en cohérence.
    #
    # Mapping allergen → champ diet_profile à mettre à False si allergène présent
    _ALLERGEN_TO_DIET: dict[str, list[str]] = {
        "milk":     ["dairy_free"],
        "nuts":     ["nut_free"],
        "peanuts":  ["nut_free"],   # allergologique : arachide = nut_free=False
        "gluten":   ["gluten_free"],
        "eggs":     ["egg_free", "vegan"],
        "soy":      ["soy_free"],
    }
    diet_sync_count = 0
    diet_sync_paths: list[str] = []

    for bk, entry in ings.items():
        for vname, vdata in entry.get("variants", {}).items():
            if not isinstance(vdata, dict):
                continue
            allergens = set(vdata.get("allergens", []))
            diet = vdata.get("diet_profile")
            if not isinstance(diet, dict) or not allergens:
                continue
            for allergen, diet_fields in _ALLERGEN_TO_DIET.items():
                if allergen in allergens:
                    for field in diet_fields:
                        if diet.get(field) is True:
                            diet[field] = False
                            diet_sync_count += 1
                            diet_sync_paths.append(f"{bk}/{vname} {field}=False (allergen={allergen})")

    if diet_sync_count:
        print(f"  ✅ diet_profile synchronisé : {diet_sync_count} correction(s) sur {len(diet_sync_paths)} champs")
        for p in diet_sync_paths:
            print(f"       ~ {p}")
    else:
        print("  ✅ diet_profile : cohérent avec allergens (idempotent)")

    if added_count or diet_sync_count:
        with open(n2_path, "w", encoding="utf-8") as fh:
            json.dump(n2, fh, ensure_ascii=False, indent=2)
        if added_count:
            print(f"  ✅ Allergènes injectés : {added_count} ajouts sur {len(touched_paths)} variants")
            for p in touched_paths:
                print(f"       + {p}")
    else:
        print("  ✅ Allergènes : tous déjà présents (idempotent)")


def _apply_nova_rules(n2_path: Path) -> None:
    """
    Applique la classification NOVA (Monteiro 2019) sur nutrition_v2.json.

    Règles :
      NOVA 1 = aliments bruts/minimalement transformés
      NOVA 2 = ingrédients culinaires (huiles, sel, sucre, farine, amidon, beurre)
      NOVA 3 = aliments transformés (fromages, pain, pâtes, fermentés, alcools, conserves)
      NOVA 4 = ultra-transformés (additifs, arômes, émulsifiants multiples)

    Idempotente — ne fait que corriger/confirmer, jamais ne rétrograde vers un NOVA inférieur.
    Appelée automatiquement à chaque `promote_nutrition.py --confirm`.

    Pour ajouter une règle : ajouter un tuple dans NOVA_RULES ci-dessous.
    """
    with open(n2_path, encoding="utf-8") as _f:
        n2 = json.load(_f)
    ings = n2["ingredients"]

    # (base_key_contient, variant_key_contient_ou_None, nova_cible)
    # Première règle qui match gagne.
    NOVA_RULES = [
        # NOVA 4 — ultra-transformés
        ("sriracha",          None,        4),
        ("liquid_smoke",      None,        4),
        ("worcestershire",    None,        4),
        # NOVA 3 — fermentés
        ("miso",              None,        3),
        ("tempeh",            None,        3),
        ("tofu",              None,        3),
        ("kimchi",            None,        3),
        ("kefir",             None,        3),
        ("wine",              None,        3),
        ("sake",              None,        3),
        ("umeboshi",          None,        3),
        ("fermented_bean",    None,        3),
        ("coconut_aminos",    None,        3),
        ("ponzu",             None,        3),
        ("mirin",             None,        3),
        ("sauce",             "soy",       3),
        ("tamari",            None,        3),
        ("vinegar",           "balsamic",  3),
        # NOVA 3 — produits laitiers fermentés/transformés
        ("cheese",            None,        3),
        ("cheese_curds",      None,        3),
        ("fromage_blanc",     None,        3),
        ("greek_yogurt",      None,        3),
        ("yogurt_animal",     None,        3),
        # NOVA 3 — pain et dérivés
        ("bread",             None,        3),
        ("breadcrumbs",       None,        3),
        # NOVA 3 — pâtes alimentaires
        ("pasta",             None,        3),
        # NOVA 3 — protéines végétales transformées
        ("seitan",            None,        3),
        ("natto",             None,        3),
        # NOVA 3 — olives, chocolat, caroube
        ("olive",             None,        3),
        ("chocolate",         None,        3),
        ("carob",             None,        3),
        # NOVA 3 — crèmes végétales industrielles
        ("cream_plant",       None,        3),
        # NOVA 2 — ingrédients culinaires (huiles, sucres, farines, sels, levures)
        ("flour",             None,        2),
        ("corn_starch",       None,        2),
        ("starch",            None,        2),
        ("tapioca_starch",    None,        2),
        ("sugar",             "cane",      2),
        ("sugar",             "white",     2),
        ("sugar",             "coconut",   2),
        ("icing_sugar",       None,        2),
        ("honey",             None,        2),
        ("maple_syrup",       None,        2),
        ("date_syrup",        None,        2),
        ("salt",              None,        2),
        ("yeast",             None,        2),
        ("nutritional_yeast", None,        2),
        ("cream_animal",      None,        2),
        ("vinegar",           None,        2),
    ]

    # Exceptions : faux positifs à ne pas reclasser
    EXCEPTIONS = {
        ("hard_boiled_egg", "default"),  # "oil" dans le nom → NOVA 1 conservé
        ("sugar_snap_pea",  "default"),  # "sugar" dans le nom → légume NOVA 1
        ("tamarind",        "default"),  # "tamari" substring → pulpe de fruit NOVA 1
        ("smoked_paprika",  "default"),  # épice séchée NOVA 1
    }

    changed = 0
    for base_key, entry in ings.items():
        for vk, vdata in entry.get("variants", {}).items():
            if (base_key, vk) in EXCEPTIONS:
                continue
            nova_cur = vdata.get("nova_group")
            for rule_base, rule_var, nova_target in NOVA_RULES:
                if rule_base not in base_key.lower():
                    continue
                if rule_var is not None and rule_var not in vk.lower():
                    continue
                if nova_target != nova_cur:
                    vdata["nova_group"] = nova_target
                    changed += 1
                break

    if changed:
        with open(n2_path, "w", encoding="utf-8") as fh:
            json.dump(n2, fh, ensure_ascii=False, indent=2)
        print(f"  ✅ NOVA : {changed} variants reclassifiés")
    else:
        print("  ✅ NOVA : classification à jour (idempotent)")


def _clean_base_recipe_variants(n2_path):
    """
    Supprime de nutrition_v2 les variants/entrées couverts par des base_recipes.

    Deux passes complémentaires :
      1. Purge par marqueur  : supprime les variants listés dans _base_recipe_excluded
         pour chaque entrée qui porte ce champ.
      2. Purge par liste statique : supprime intégralement les base_keys présentes
         dans STATIC_BASE_RECIPE_KEYS (héritage pipeline legacy — rapport §2).
         Ces entrées ne doivent jamais exister comme variants nutritionnels car
         leur valeur est calculée depuis leur composition-recette.

    Idempotent — sans effet si les entrées sont déjà absentes.
    Intégré dans le build (promote_nutrition --confirm), step 7.
    """
    with open(n2_path, encoding="utf-8") as _f:
        n2 = json.load(_f)
    ings = n2["ingredients"]
    removed_variants = []
    removed_entries  = []
    kept_partial     = []
    keys_to_delete   = []

    # ── Passe 1 : purge par marqueur _base_recipe_excluded ───────────────────
    for base_key, entry in list(ings.items()):
        excl = entry.get("_base_recipe_excluded", [])
        if not excl:
            continue
        variants = entry.get("variants", {})
        for vk in excl:
            if vk in variants:
                del variants[vk]
                removed_variants.append(base_key + "/" + vk)
        entry.pop("_base_recipe_excluded", None)
        if not variants:
            keys_to_delete.append(base_key)
            removed_entries.append(base_key)
        else:
            kept_partial.append(base_key + " " + str(list(variants.keys())))

    # ── Passe 2 : purge sélective selon BASE_RECIPE_MODES ────────────────
    # Mode "base_recipe" → supprimé de nutrition_v2 (valeur calculée depuis recette)
    # Mode "indus"       → conservé dans nutrition_v2 (données nutritionnelles validées)
    static_purged = []   # supprimés (base_recipe)
    indus_kept    = []   # conservés (indus)

    for base_key, mode in BASE_RECIPE_MODES.items():
        if base_key not in ings or base_key in keys_to_delete:
            continue
        if mode == "base_recipe":
            keys_to_delete.append(base_key)
            static_purged.append(base_key)
        elif mode == "indus":
            indus_kept.append(base_key)

    for k in keys_to_delete:
        del ings[k]

    dirty = removed_variants or removed_entries or static_purged
    if dirty or indus_kept:
        if dirty:
            with open(n2_path, "w", encoding="utf-8") as fh:
                _json.dump(n2, fh, ensure_ascii=False, indent=2)
        if removed_variants:
            print("  Variants nettoyes  : " + str(len(removed_variants)))
            for rv in removed_variants:
                print("       - " + rv)
        if removed_entries:
            print("  Entrees supprimees (marqueur) : " + str(removed_entries))
        if static_purged:
            print("  Entrees supprimees (base_recipe) : " + str(static_purged))
        if indus_kept:
            print("  Entrees conservees (indus)       : " + str(indus_kept))
        if kept_partial:
            print("  Entrees partielles : " + str(kept_partial))
    else:
        print("  Variants base_recipe : deja nettoyes (idempotent)")

if __name__ == "__main__":
    args = sys.argv[1:]
    confirm = "--confirm" in args
    clean   = "--clean"   in args

    # --source=patched | --source=corrected
    force = None
    for a in args:
        if a.startswith("--source="):
            val = a.split("=", 1)[1].strip().lower()
            if val not in ("patched", "corrected"):
                print(f"  ❌ --source invalide : '{val}'. Valeurs acceptées : patched, corrected")
                sys.exit(1)
            force = val
            break

    sys.exit(promote(dry_run=not confirm, clean_source=clean, force_source=force))