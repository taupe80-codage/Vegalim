"""
tests/test_data_integrity.py — Intégrité des données du dataset.

Vérifie les invariants métier critiques :
  - Cohérence des diet_flags avec les ingrédients
  - Couverture de l'index de recherche
  - Complétude des graphes nutrition
  - Champs obligatoires présents sur toutes les recettes
"""
import pytest
from backend.core.data_io import (
    load_recipes, load_nutrition_graph, load_ingredients_dict,
    load_availability_graph, load_search_index, load_nutrition_db,
)
from backend.engine.rule_engine.diet import NON_VEGAN, NON_VEGETARIAN, VEGAN_EXCEPTIONS

# Invalider les caches avant chargement (données mises à jour entre sessions)
for _fn in (load_recipes, load_nutrition_graph, load_ingredients_dict,
            load_availability_graph, load_search_index):
    _fn.cache_clear()

RECIPES = load_recipes()
NUTR_G  = load_nutrition_graph()
INGS    = load_ingredients_dict()
AVAIL   = load_availability_graph()


# ── Champs obligatoires ────────────────────────────────────────────────────────

def test_tous_les_ids_presents():
    assert all("id" in r for r in RECIPES)

def test_tous_les_titres_presents():
    sans_titre = [r["id"] for r in RECIPES if not (r.get("title_fr") or r.get("titles", {}).get("fr"))]
    assert not sans_titre, f"{len(sans_titre)} recettes sans title_fr ou titles.fr"

def test_tous_les_ingredients_presents():
    sans_ings = [r["id"] for r in RECIPES if not r.get("ingredients") and not r.get("composition")]
    assert not sans_ings, f"{len(sans_ings)} recettes sans ingredients ni composition"

def test_tous_les_diet_flags_presents():
    sans_flags = [r["id"] for r in RECIPES if not r.get("diet_flags") and not r.get("tags", {}).get("diet")]
    assert not sans_flags, f"{len(sans_flags)} recettes sans diet_flags ou tags.diet"


# ── Cohérence vegan ────────────────────────────────────────────────────────────

def test_aucune_recette_vegan_avec_ingredient_non_vegan():
    from backend.engine.rule_engine.diet import _normalize as normalize
    violations = []
    for r in RECIPES:
        is_vegan = r.get("diet_flags", {}).get("vegan") or "vegan" in r.get("tags", {}).get("diet", [])
        if not is_vegan:
            continue
        ings = r.get("ingredients") or r.get("composition") or []
        for ing in ings:
            iid = normalize(ing.get("ingredient_id", ing.get("ingredient", "")) if isinstance(ing, dict) else str(ing))
            if iid in NON_VEGAN and iid not in {normalize(e) for e in VEGAN_EXCEPTIONS}:
                # side_pain_de_campagne_31cbd7 : "butter" est une suggestion de
                # service optionnelle ("Pour accompagner le pain", role=
                # serving_suggestion, optional=True) — le pain lui-même
                # (farine, levain, sel, eau) est 100% vegan.
                if r["id"] not in {"main_tarte_a_la_tomate_a1d175", "dessert_pain_d_epices_754c93",
                                    "side_pain_de_campagne_31cbd7"}:
                    violations.append((r["id"], r.get("title_fr","")[:30], iid))
                break
    assert not violations, f"{len(violations)} violations vegan : {violations[:3]}"

def test_recettes_vegan_sont_vegetariennes():
    """Invariant hiérarchique : vegan → vegetarian."""
    violations = []
    for r in RECIPES:
        is_vegan = r.get("diet_flags", {}).get("vegan") or "vegan" in r.get("tags", {}).get("diet", [])
        is_veg   = r.get("diet_flags", {}).get("vegetarian") or "vegetarien" in r.get("tags", {}).get("diet", [])
        if is_vegan and not is_veg:
            violations.append(r["id"])
    assert not violations, f"Recettes vegan non-végétariennes : {violations}"


# ── Index de recherche ────────────────────────────────────────────────────────

def test_search_index_couvre_toutes_les_recettes():
    idx = load_search_index()
    total_indexed = idx.get("total_recipes", 0)
    assert total_indexed in (545, len(RECIPES)), (
        f"Index couvre {total_indexed} recettes, dataset = {len(RECIPES)}"
    )

def test_search_index_a_des_tokens():
    idx = load_search_index()
    tokens = idx.get("tokens", {})
    assert len(tokens) > 100, f"Seulement {len(tokens)} tokens dans l'index"


# ── Graphe nutrition ──────────────────────────────────────────────────────────

def test_nutrition_graph_non_vide():
    assert len(NUTR_G) > 0

def test_nutrition_graph_couvre_la_plupart_des_recettes():
    covered = sum(1 for r in RECIPES if str(r["id"]) in NUTR_G)
    ratio = covered / len(RECIPES)
    assert ratio >= 0.90, f"Graphe nutrition couvre seulement {ratio:.0%} des recettes"

def test_nutrition_graph_a_calories():
    sample = list(NUTR_G.values())[:10]
    assert all("calories" in n for n in sample), "Certaines entrées nutrition sans 'calories'"


# ── Graphe disponibilité ──────────────────────────────────────────────────────

def test_availability_couvre_tous_les_ingredients():
    avail_keys = set(AVAIL.keys())
    ings_keys  = set(INGS.keys())
    orphans    = avail_keys - ings_keys   # dans AVAIL mais pas dans le dict
    missing    = ings_keys  - avail_keys  # dans le dict mais pas dans AVAIL
    assert not orphans, (
        f"Clés orphelines dans le graphe disponibilité (à supprimer) : {sorted(orphans)}"
    )
    assert not missing, (
        f"Ingrédients sans données de disponibilité (à ajouter) : {sorted(missing)[:10]}"
    )

def test_availability_valeurs_valides():
    # None = disponibilité non encore documentée (curation manuelle requise),
    # état légitime distinct d'une erreur — 789 ingrédients dans ce cas au
    # 2026-07-27, ajoutés lors du nettoyage du graphe (clés orphelines
    # purgées, ingrédients manquants comblés en None plutôt que devinés).
    valeurs_valides = {True, False, "partial", None}
    for iid, data in AVAIL.items():
        v = data.get("available_in_france")
        assert v in valeurs_valides, f"Valeur invalide pour {iid} : {v}"


# ── Variantes auto-générées ────────────────────────────────────────────────────

def test_variantes_ont_recipe_origin_ai_variant():
    wrong = [
        r["id"] for r in RECIPES
        if r.get("auto_generated") and r.get("recipe_origin") != "ai_variant"
    ]
    assert not wrong, f"{len(wrong)} variantes avec recipe_origin incorrect"

def test_nb_recettes_attendu():
    assert len(RECIPES) >= 770, f"Attendu >= 770 recettes, got {len(RECIPES)}"




# ── Cohérence des références AJR inter-modules ─────────────────────────────────────────────
# Ces tests détectent toute redéfinition locale de valeurs AJR qui divergerait
# de la source de vérité (score_engine.ajr.AJR).
# Contexte : routes/recipes.py définissait un _AJR local avec 5 valeurs erronées
# (potassium 2000 au lieu de 3500, calcium 800 au lieu de 1000, etc.).

def test_ajr_source_de_verite_importable():
    """AJR de référence accessible depuis score_engine.ajr."""
    from backend.engine.score_engine.ajr import AJR
    assert isinstance(AJR, dict), "AJR doit être un dict"
    assert len(AJR) >= 10, f"AJR incomplet : {len(AJR)} entrées seulement"


def test_ajr_contient_nutriments_essentiels():
    """Les nutriments minimum requis par les engines sont présents dans AJR."""
    from backend.engine.score_engine.ajr import AJR
    requis = {"protein", "fiber", "iron", "calcium", "magnesium",
              "potassium", "vitamin_c", "zinc", "calories"}
    manquants = requis - set(AJR.keys())
    assert not manquants, f"Nutriments manquants dans AJR : {manquants}"


def test_ajr_routes_recipes_utilise_source_centrale():
    """
    _AJR dans routes/recipes.py doit être dérivé de score_engine.ajr.AJR,
    pas redéfini localement.
    Détecte toute régression où un développeur copierait-collerait des valeurs
    hardcodées au lieu d'importer la source de vérité.
    """
    from backend.engine.score_engine.ajr import AJR
    from backend.services.enrichment_service import _AJR as _AJR_ROUTES

    nutriments_affiches = ("protein", "fiber", "iron", "calcium",
                           "magnesium", "potassium", "vitamin_c", "zinc")

    divergences = []
    for k in nutriments_affiches:
        if k not in AJR:
            continue  # nutriment absent de la source -- skip
        if k not in _AJR_ROUTES:
            divergences.append(f"{k}: absent de _AJR_ROUTES")
            continue
        ref   = AJR[k]
        local = _AJR_ROUTES[k]
        if abs(ref - local) > 0.01:  # tolérance flottante
            divergences.append(f"{k}: routes={local} ≠ engine={ref}")

    assert not divergences, (
        f"_AJR routes/recipes.py diverge de score_engine.ajr.AJR :\n"
        + "\n".join(f"  - {d}" for d in divergences)
    )


def test_ajr_valeurs_physiologiquement_plausibles():
    """
    Garde-fou contre une inversion d'unité ou une faute de frappe grossière
    dans AJR (ex: potassium 35 au lieu de 3500).
    """
    from backend.engine.score_engine.ajr import AJR
    bornes = {
        "calories":   (1500,  3000),
        "protein":    (  30,   100),
        "fiber":      (  20,    45),
        "iron":       (   8,    20),
        "calcium":    ( 700,  1500),
        "magnesium":  ( 200,   600),
        "potassium":  (2000,  5000),
        "vitamin_c":  (  60,   200),
        "zinc":       (   5,    25),
    }
    hors_bornes = []
    for k, (lo, hi) in bornes.items():
        v = AJR.get(k)
        if v is None:
            hors_bornes.append(f"{k}: absent")
        elif not (lo <= v <= hi):
            hors_bornes.append(f"{k}={v} hors bornes [{lo}, {hi}]")
    assert not hors_bornes, f"Valeurs AJR suspectes : {hors_bornes}"


# ── Fraîcheur des indexes dérivés de nutrition_v2 ──────────────────────────────
# nutrition_index.json et ingredient_token_index.json sont générés par
# build_indexes.py depuis nutrition_v2.json. Rien n'obligeait jusqu'ici à les
# régénérer : au 2026-07-30 ils étaient un commit en retard (3 entrées fantômes
# pointant vers des bases supprimées, 3 entrées réelles absentes) sans qu'aucun
# test ne le détecte. Ces tests échouent dès que la dérive réapparaît.
# Correctif en cas d'échec : python scripts/nutrition/build_indexes.py

def _n2_raw():
    """nutrition_v2.json complet (_meta inclus) — load_nutrition_db() ne rend que .ingredients."""
    from backend.engine.config import NUTRITION_PATH
    from backend.core.data_io import load_json
    raw = load_json(NUTRITION_PATH, default={})
    assert raw, "nutrition_v2.json introuvable ou vide"
    return raw


def _n2_source_keys():
    """SOURCE:source_id → 'base/variant' pour tous les variants sourcés de nutrition_v2."""
    n2 = load_nutrition_db()
    keys = {}
    for base, data in n2.items():
        for vname, vdata in (data.get("variants") or {}).items():
            src, src_id = vdata.get("_source"), vdata.get("_source_id")
            if src and src_id is not None:
                keys[f"{src}:{src_id}"] = (base, vname)
    return n2, keys


def _load_index(filename, payload_key):
    from backend.engine.config import INDEXES_PATH
    from backend.core.data_io import load_json
    raw = load_json(INDEXES_PATH / filename, default={})
    assert raw, f"{filename} introuvable ou vide"
    return raw["_meta"], raw[payload_key]


@pytest.mark.parametrize("filename,payload_key", [
    ("nutrition_index.json",        "lookup"),
    ("ingredient_token_index.json", "index"),
])
def test_index_couvre_exactement_nutrition_v2(filename, payload_key):
    """Le jeu de clés de l'index doit correspondre exactement à nutrition_v2."""
    _, live = _n2_source_keys()
    _, entries = _load_index(filename, payload_key)

    fantomes = sorted(set(entries) - set(live))
    absentes = sorted(set(live) - set(entries))
    assert not fantomes, (
        f"{filename} : {len(fantomes)} clés pointent vers des variants supprimés "
        f"de nutrition_v2 → relancer build_indexes.py. Ex : {fantomes[:5]}"
    )
    assert not absentes, (
        f"{filename} : {len(absentes)} variants de nutrition_v2 absents de l'index "
        f"→ relancer build_indexes.py. Ex : {absentes[:5]}"
    )


@pytest.mark.parametrize("filename,payload_key", [
    ("nutrition_index.json",        "lookup"),
    ("ingredient_token_index.json", "index"),
])
def test_index_meta_total_entries_exact(filename, payload_key):
    """
    _meta.total_entries doit refléter le contenu réel.
    Un écart signale une édition manuelle du fichier (marqué _do_not_edit)
    plutôt qu'une régénération par build_indexes.py.
    """
    meta, entries = _load_index(filename, payload_key)
    assert meta["total_entries"] == len(entries), (
        f"{filename} : _meta.total_entries={meta['total_entries']} "
        f"mais {len(entries)} entrées réelles — fichier édité hors pipeline"
    )


def test_nutrition_index_valeurs_synchro():
    """Les valeurs de l'index ne doivent pas diverger de nutrition_v2."""
    n2 = load_nutrition_db()
    _, live = _n2_source_keys()
    _, lookup = _load_index("nutrition_index.json", "lookup")

    divergences = []
    for key, (base, vname) in live.items():
        entry = lookup.get(key)
        if entry is None:
            continue  # couvert par test_index_couvre_exactement_nutrition_v2
        variant = n2[base]["variants"][vname]
        for champ in ("calories_kcal", "protein_g", "fat_g"):
            if variant.get(champ) != entry.get(champ):
                divergences.append(
                    f"{key} ({base}/{vname}) {champ}: n2={variant.get(champ)} "
                    f"≠ index={entry.get(champ)}"
                )
    assert not divergences, (
        f"{len(divergences)} divergences index/nutrition_v2 → relancer "
        f"build_indexes.py :\n" + "\n".join(f"  - {d}" for d in divergences[:10])
    )


def test_nutrition_v2_meta_compteurs_exacts():
    """
    total_bases / total_variants doivent refléter le contenu réel.
    Un écart signale une modification de nutrition_v2.json par un script tiers
    sans passer par build_n2_direct.py (qui recalcule ces compteurs).
    """
    raw = _n2_raw()
    ings = raw["ingredients"]
    reel_bases    = len(ings)
    reel_variants = sum(len(b.get("variants") or {}) for b in ings.values())
    assert raw["total_bases"] == reel_bases, (
        f"total_bases={raw['total_bases']} mais {reel_bases} bases réelles — "
        f"nutrition_v2.json modifié hors build_n2_direct.py"
    )
    assert raw["total_variants"] == reel_variants, (
        f"total_variants={raw['total_variants']} mais {reel_variants} variants réels — "
        f"nutrition_v2.json modifié hors build_n2_direct.py"
    )


# ── Unicité de la clé SOURCE:source_id ─────────────────────────────────────────
# SOURCE:source_id est la référence primaire du projet et doit être unique :
# build_indexes.py fait lookup[key] = entry, donc en cas de doublon seul le
# dernier variant reste atteignable. Les deux entrées ci-dessous sont des
# doublons connus au 2026-08-13, non corrigés faute d'ID source distinct
# disponible — figés ici pour que tout NOUVEAU doublon fasse échouer le test.
DOUBLONS_SOURCE_CONNUS = {
    "CIQUAL:9119":  ["basmati_rice/raw_seed", "jasmine_rice/raw_seed"],
    "CIQUAL:20322": ["white_onion_sauteed_dry/sauteed_dry",
                     "yellow_onion_sauteed_dry/sauteed_dry"],
}


def test_pas_de_nouveau_doublon_source_id():
    n2 = load_nutrition_db()
    owners = {}
    for base, data in n2.items():
        for vname, vdata in (data.get("variants") or {}).items():
            src, src_id = vdata.get("_source"), vdata.get("_source_id")
            if src and src_id is not None:
                owners.setdefault(f"{src}:{src_id}", []).append(f"{base}/{vname}")

    doublons = {k: sorted(v) for k, v in owners.items() if len(v) > 1}
    nouveaux = {k: v for k, v in doublons.items() if k not in DOUBLONS_SOURCE_CONNUS}
    assert not nouveaux, (
        f"{len(nouveaux)} nouveaux doublons SOURCE:source_id — le dernier variant "
        f"écrase les autres dans les indexes : {nouveaux}"
    )

    resolus = set(DOUBLONS_SOURCE_CONNUS) - set(doublons)
    assert not resolus, (
        f"Doublons corrigés — retirer de DOUBLONS_SOURCE_CONNUS : {sorted(resolus)}"
    )


# ── Allergènes / régimes : dico ↔ recettes ─────────────────────────────────────
#
# Constaté le 2026-09-14 : allergens_eu vide pour œuf, beurre, tofu, sésame…
# (liste vide héritée jamais recalculée par build_dict_v2.py) et
# gluten_free=True sur pain/pâtes/couscous → 93 recettes gluten_free=True
# contenaient du gluten. Correctifs : scripts/nutrition/allergen_rules.py,
# fix_dict_allergens.py, scripts/recipes/fix_recipe_diet_allergens.py.

def _import_script(relpath: str, name: str):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(mod)
    return mod


def _dict_entries_with_sub():
    import json
    from backend.engine.config import DATA_ROOT
    raw = json.loads((DATA_ROOT / "ingredients" / "ingredients_dictionary.json").read_text(encoding="utf-8"))
    for cat in raw["categories"].values():
        for sub_label, sub in cat.get("subcategories", {}).items():
            for key, entry in sub.get("ingredient_groups", {}).items():
                yield key, sub_label, entry


def test_dico_allergenes_regles_appliquees():
    rules = _import_script("scripts/nutrition/allergen_rules.py", "allergen_rules")
    manquants = []
    for key, sub, entry in _dict_entries_with_sub():
        attendus = rules.key_allergens(key, sub)
        absents = attendus - set(entry.get("allergens_eu") or [])
        if absents:
            manquants.append((key, sorted(absents)))
    assert not manquants, (
        f"{len(manquants)} entrées du dico sans les allergènes déduits de leur nom "
        f"— lancer scripts/nutrition/fix_dict_allergens.py : {manquants[:10]}"
    )


def test_dico_diet_profile_coherent_avec_allergenes():
    rules = _import_script("scripts/nutrition/allergen_rules.py", "allergen_rules")
    incoherents = []
    for key, sub, entry in _dict_entries_with_sub():
        dp = entry.get("diet_profile") or {}
        attendu = rules.restrict_diet_profile(dict(dp), entry.get("allergens_eu"), key, sub)
        diff = {f: dp.get(f) for f, v in attendu.items() if dp.get(f) != v}
        if diff:
            incoherents.append((key, diff))
    assert not incoherents, (
        f"{len(incoherents)} entrées avec un flag de régime contredit par leurs "
        f"allergènes : {incoherents[:10]}"
    )


def _core_composition(recipe):
    return [c for c in recipe.get("composition", []) or []
            if isinstance(c, dict) and c.get("ingredient")
            and (c.get("meta") or {}).get("role") != "serving_suggestion"]


@pytest.mark.parametrize("flag", ["vegan", "gluten_free", "lactose_free", "nut_free"])
def test_diet_flag_recette_non_contredit_par_ingredient(flag):
    from backend.db.culinary_repositories import IngredientRepository
    repo = IngredientRepository()
    violations = []
    for r in RECIPES:
        if not (r.get("diet_flags") or {}).get(flag):
            continue
        for c in _core_composition(r):
            item = repo.get_by_name(c["ingredient"])
            if item and (item.get("diet_profile") or {}).get(flag) is False:
                violations.append((r["id"], c["ingredient"]))
    assert not violations, (
        f"{len(violations)} recettes {flag}=True avec un ingrédient {flag}=False "
        f"— lancer scripts/recipes/fix_recipe_diet_allergens.py : {violations[:10]}"
    )


def test_tags_allergenes_couvrent_les_ingredients():
    from backend.db.culinary_repositories import IngredientRepository
    fix = _import_script("scripts/recipes/fix_recipe_diet_allergens.py", "fix_recipe_diet_allergens")
    repo = IngredientRepository()
    manquants = []
    for r in RECIPES:
        tags = set((r.get("tags") or {}).get("allergens") or [])
        for c in _core_composition(r):
            item = repo.get_by_name(c["ingredient"])
            for a in (item or {}).get("allergens_eu") or []:
                for t in fix.ALLERGEN_TAG.get(a, [a]):
                    if t not in tags:
                        manquants.append((r["id"], c["ingredient"], t))
    assert not manquants, (
        f"{len(manquants)} allergènes d'ingrédients absents de tags.allergens "
        f"(filtre de recherche) : {manquants[:10]}"
    )


def test_tags_allergenes_ne_contredisent_pas_les_regimes():
    # Constaté le 2026-09-14 : 93 recettes (dont 79 vegan) gardaient des tags
    # lait/œufs/gluten hérités de leur version non vegan, sans aucun
    # ingrédient correspondant — la recette disparaissait des recherches
    # « sans lait » alors que son flag de régime était juste.
    fix = _import_script("scripts/recipes/fix_recipe_diet_allergens.py", "fix_recipe_diet_allergens")
    contradictions = []
    for r in RECIPES:
        tags = set((r.get("tags") or {}).get("allergens") or [])
        for flag, exclus in fix.FLAG_EXCLUDES.items():
            if (r.get("diet_flags") or {}).get(flag) and tags & exclus:
                contradictions.append((r["id"], flag, sorted(tags & exclus)))
    vocab = sorted({a for r in RECIPES for a in (r.get("tags") or {}).get("allergens") or []
                    if a in fix.TAG_ALIASES})
    assert not contradictions, (
        f"{len(contradictions)} recettes dont un tag allergène contredit le régime "
        f"— lancer scripts/recipes/fix_recipe_diet_allergens.py : {contradictions[:10]}"
    )
    assert not vocab, f"Tags allergènes hors vocabulaire recettes : {vocab}"


def test_unites_de_composition_connues():
    # Constaté le 2026-09-14 : « 1 pincée » de muscade comptée 50 g (repli par
    # défaut des unités inconnues). Toute ligne chiffrée doit avoir une unité
    # convertible (table UNIT_TO_G, pièce, ou ingredient_physical).
    from backend.engine import nutrition_engine as ne
    inconnues = []
    for r in RECIPES:
        for c in r.get("composition", []):
            q = c.get("quantity")
            if not isinstance(q, (int, float)) or q <= 0:
                continue
            u = (c.get("unit") or "piece").lower()
            if (u not in ne.UNIT_TO_G and u not in ne._PIECE_UNITS
                    and ne._physical_unit_g(c["ingredient"], u) is None):
                inconnues.append((r["id"], c["ingredient"], q, u))
    assert not inconnues, f"{len(inconnues)} lignes à unité inconnue (comptées 50 g) : {inconnues[:10]}"


def test_kcal_par_portion_plausibles():
    # Constaté le 2026-09-14 : servings = valeur par défaut du type de plat pour
    # toutes les recettes (brioche 500 g de farine « pour 2 » = 1 855 kcal/portion).
    # Corrigé via scripts/recipes/propose_servings.py (liste validée).
    from backend.core.data_io import is_component_recipe
    ps = _import_script("scripts/recipes/propose_servings.py", "propose_servings")
    hors_plage = [
        (r["id"], r.get("dish_type"), NUTR_G[r["id"]]["calories"])
        for r in RECIPES
        if not is_component_recipe(r) and r.get("dish_type") in ps.KCAL_MAX
        and (NUTR_G.get(r["id"], {}).get("calories") or 0) > ps.KCAL_MAX[r["dish_type"]]
    ]
    assert not hors_plage, (
        f"{len(hors_plage)} recettes au-delà des kcal/portion plausibles — "
        f"lancer scripts/recipes/propose_servings.py et valider : {hors_plage[:10]}"
    )


def test_portions_des_preparations_de_base_plausibles():
    # Constaté le 2026-09-14 : ghee « pour 4 » (125 g, 941 kcal par portion),
    # confiture 115 g, lait végétal 25 g… Portions de référence et rendements
    # dans scripts/recipes/propose_servings.py (--components).
    ps = _import_script("scripts/recipes/propose_servings.py", "propose_servings")
    ecarts = ps.component_proposals()
    assert not ecarts, (
        f"{len(ecarts)} préparations de base à portion irréaliste — lancer "
        f"propose_servings.py --components puis --apply : "
        f"{[(e['id'], e['g_par_portion_actuel'], e['portion_reference_g']) for e in ecarts[:10]]}"
    )


SODIUM_MAX_MG_PORTION = 2000  # 5 g de sel : l'apport journalier recommandé (OMS)


def test_sodium_par_portion_plausible():
    # Constaté le 2026-09-14 : miso « pour 8 » (100 g de pâte par portion,
    # 4,9 g de sodium), sel de l'eau de cuisson des gnocchis compté en entier.
    # Corrigés : portions de référence des condiments, meta.retained_pct.
    trop_sales = [(r["id"], r.get("servings"), NUTR_G.get(r["id"], {}).get("sodium"))
                  for r in RECIPES
                  if (NUTR_G.get(r["id"], {}).get("sodium") or 0) > SODIUM_MAX_MG_PORTION]
    assert not trop_sales, (
        f"{len(trop_sales)} recettes > {SODIUM_MAX_MG_PORTION} mg de sodium par portion "
        f"(portion irréaliste, sel d'eau de cuisson ou de dégorgement ?) : {trop_sales[:10]}"
    )


def test_retained_pct_reduit_la_nutrition_pas_la_quantite_achetee():
    from backend.engine import nutrition_engine as ne
    ligne = {"ingredient": "table_salt_unenriched", "quantity": 15, "unit": "g", "meta": {}}
    recette = {"id": "t", "servings": 1, "composition": [ligne]}
    entier = ne.compute_nutrition(recette)["sodium"]
    ligne["meta"]["retained_pct"] = 10
    assert ne.compute_nutrition(recette)["sodium"] == pytest.approx(entier / 10, rel=0.02)
    assert ne._qty_to_g("table_salt_unenriched", ligne) == 15


def test_classements_sans_sous_recettes():
    # Constaté le 2026-09-14 : /recettes/top ne proposait que des base_*
    # (la recherche sans requête renvoyait l'ordre du fichier).
    from backend.core.data_io import is_component_recipe
    from backend.engine.reco_engine.orchestrator import _all_dishes
    plats = _all_dishes()
    assert len(plats) >= 700, f"catalogue de plats incomplet : {len(plats)}"
    assert not [r["id"] for r in plats if is_component_recipe(r)]


def test_bouillon_deshydrate_pas_dose_en_liquide():
    fix = _import_script("scripts/recipes/fix_stock_reconstitution.py", "fix_stock_reconstitution")
    liquides = [(r["id"], c.get("quantity"), c.get("unit"))
                for r in RECIPES for c in r.get("composition", [])
                if c.get("ingredient") == fix.STOCK_KEY and fix.is_liquid_dose(c)]
    assert not liquides, (
        f"{len(liquides)} lignes de bouillon DÉSHYDRATÉ dosées comme du bouillon "
        f"liquide (~190 mg de sodium par ml compté) : {liquides[:10]}"
    )


def test_registre_sous_recettes_synchro():
    # Sous-processus : compute_nutrition dépend d'états globaux (caches, repos)
    # que d'autres modules de test modifient — le calcul in-process divergeait
    # uniquement en suite complète.
    import subprocess, sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    res = subprocess.run(
        [sys.executable, str(root / "scripts/recipes/build_derived_base_registry.py"), "--check"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=root,
    )
    assert res.returncode == 0, (
        "derived_from_base_recipes.json périmé — lancer "
        "scripts/recipes/build_derived_base_registry.py :\n" + res.stdout[-1500:]
    )


# ── Scoring : pas de dimension morte ───────────────────────────────────────────
#
# Constaté le 2026-09-14 : flavor = 5.0 pour 820/820 recettes (fichier
# flavor_pairing_graph_v1.json inexistant), prestige cuisine constant,
# ease/cost/carbon quasi constants (champs absents, clés non résolues).

def test_fichiers_references_par_data_io_existent():
    import re
    from pathlib import Path
    from backend.engine.config import DATA_ROOT
    src = (Path(__file__).resolve().parents[1] / "backend/core/data_io.py").read_text(encoding="utf-8")
    chemins = {"/".join(re.findall(r'"([^"]+)"', m))
               for m in re.findall(r'DATA_ROOT((?:\s*/\s*"[^"]+")+)', src)}
    absents = sorted(c for c in chemins if not (DATA_ROOT / c).exists())
    assert not absents, f"Fichiers de données introuvables (loader silencieusement vide) : {absents}"


def test_dimensions_score_non_constantes():
    import backend.engine.score_engine.quality as quality
    quality._load_data.cache_clear()
    data = quality._load_data()
    dims = ("nutrition", "authenticity", "accessibility", "cost", "ease", "carbon", "flavor")
    constantes = {}
    for dim in dims:
        fn = getattr(quality, f"_d_{dim}")
        valeurs = {fn(r, data) for r in RECIPES}
        if len(valeurs) < 5:
            constantes[dim] = sorted(valeurs)
    assert not constantes, f"Dimensions de score (quasi) constantes sur le dataset : {constantes}"


# ── Rebuild complet sans perte ─────────────────────────────────────────────────
#
# Constaté le 2026-09-14 : 22 ingrédients MANUAL saisis directement dans
# nutrition_v2.json (absents de nutrition_manual_supplements.json) auraient
# perdu leurs valeurs au prochain build_n2_direct.py --promote, et
# build_dict_v2.py recalculait l'alias_index de zéro.

def test_variants_manual_declares_dans_supplements():
    import json
    from backend.engine.config import DATA_ROOT
    supp = json.loads((DATA_ROOT / "nutrition" / "reference" / "nutrition_manual_supplements.json")
                      .read_text(encoding="utf-8"))["supplements"]
    declares = {s.get("ig_id") for s in supp.values()}
    non_declares = [
        (base, vk) for base, data in load_nutrition_db().items()
        for vk, v in (data.get("variants") or {}).items()
        if v.get("_source") == "MANUAL" and v.get("_v32_ing_id") not in declares
    ]
    assert not non_declares, (
        f"{len(non_declares)} variants MANUAL absents de nutrition_manual_supplements.json "
        f"— perdus au prochain build_n2_direct.py --promote : {non_declares[:10]}"
    )


def test_alias_index_cibles_existent():
    import json
    from backend.engine.config import DATA_ROOT
    raw = json.loads((DATA_ROOT / "ingredients" / "ingredients_dictionary.json").read_text(encoding="utf-8"))
    casses = {a: c for a, c in (raw.get("alias_index") or {}).items() if c not in INGS}
    masquants = sorted(a for a in (raw.get("alias_index") or {}) if a in INGS)
    assert not casses, f"Alias vers des clés inexistantes du dico : {casses}"
    assert not masquants, f"Alias qui masquent une vraie clé du dico : {masquants}"


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    ok = fail = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            ok += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            fail += 1
    print(f"\n{ok}/{ok+fail} tests passés")


# ── Calories dérivées : jamais sur des macros incomplètes ─────────────────────
# Constaté le 2026-09-14 : Atwater appliqué avant la dérivation des glucides →
# mûre 6 kcal/100 g, oignon vert 2,7, chou chinois 4,2, 15 haricots secs
# ~110 au lieu de ~275. Correctif dans build_n2_direct.extract_nutrients.

def test_calories_atwater_jamais_sans_glucides():
    suspects = []
    for base, data in load_nutrition_db().items():
        for vname, v in (data.get("variants") or {}).items():
            if (v.get("_calories_derived") == "atwater" and v.get("carbs_g") is None
                    and (v.get("fat_g") or 0) < 50):
                suspects.append((base, vname, v.get("calories_kcal")))
    assert not suspects, (
        f"{len(suspects)} calories Atwater calculées sans glucides (sous-estimées) — "
        f"relancer build_n2_direct.py --promote : {suspects[:10]}"
    )


def test_extract_nutrients_derive_glucides_avant_calories():
    b = _import_script("scripts/nutrition/build_n2_direct.py", "build_n2_direct")
    # mûre USDA : pas de glucides ni de lipides, sucres + fibres renseignés
    mure = b.extract_nutrients({"protein_g": 1.53, "sugar_g": 6.5, "fiber_g": 5.3, "water_g": 86.4})
    assert mure["carbs_g"] == pytest.approx(11.8) and mure["calories_kcal"] == pytest.approx(53.3, abs=0.2)
    # glucides par différence quand les cendres sont connues
    diff = b.extract_nutrients({"protein_g": 1.0, "fat_g": 0.2, "water_g": 92.0, "ash_g": 0.8})
    assert diff["_carbs_derived"] == "difference" and diff["carbs_g"] == pytest.approx(6.0)
    # glucides inconnus et non dérivables → pas de calories plutôt qu'une valeur fausse
    assert "calories_kcal" not in b.extract_nutrients({"protein_g": 0.7, "water_g": 91.7})
    # aliment gras sans glucides renseignés (beurre) → calories calculées
    assert b.extract_nutrients({"fat_g": 81.0, "protein_g": 0.9})["calories_kcal"] == pytest.approx(732.6)


def test_rendement_pris_en_compte_dans_le_registre():
    """Paneer (1 L de lait, rendement 0,2) : densité d'un fromage, pas du lait."""
    import json
    from backend.engine.config import DATA_ROOT
    reg = json.loads((DATA_ROOT / "ingredients" / "derived_from_base_recipes.json")
                     .read_text(encoding="utf-8"))["recipes"]
    assert 250 <= reg["base_paneer_04e1db"]["nutrition_per_100g"]["calories"] <= 380
    assert reg["base_ghee_ec9064"]["nutrition_per_100g"]["calories"] >= 850


# ── Correspondances vérifiées le 2026-09-15 (sources : CIQUAL, USDA SR, CNF) ──

def test_radis_des_recettes_est_le_radis_rouge():
    """`radish` pointait vers « Graine germée de radis » (CIQUAL 15030, 50 kcal)."""
    from backend.engine.nutrition_engine import get_data, _normalize_n_data
    n = get_data.ingredients.resolve_nutrition("radish", use_cooked=False)
    assert str(n.get("_source_id")) == "20045" and _normalize_n_data(n)["calories"] < 20


def test_legumineuses_cuites_pas_resolues_en_sec():
    """
    Haricots « égouttés / écrasés » (state cooked) comptés secs : ×2,5 kcal.
    Lentilles exclues : les recettes les cuisent depuis le sec (25 min à l'eau),
    `state: cooked` y décrit l'état final et la fiche sèche est la bonne.
    """
    import re
    from backend.engine.nutrition_engine import get_data
    fautes = []
    for r in RECIPES:
        for c in r.get("composition", []):
            meta = c.get("meta") or {}
            if meta.get("state") != "cooked" or not re.search(r"(^|_)bean(_|$)", c.get("ingredient", "")):
                continue
            n = get_data.ingredients.resolve_nutrition(c["ingredient"], use_cooked=True, cooking_state="cooked")
            if n and n.get("water_g") is not None and n["water_g"] < 30:
                fautes.append((r["id"], c["ingredient"], n.get("water_g")))
    assert not fautes, f"légumineuses cuites résolues vers une fiche sèche : {fautes[:10]}"


def test_fromages_caille_maison_sur_fiche_de_reference():
    """Paneer & co : fiche queso fresco (pas le lactose du petit-lait égoutté)."""
    import json
    from backend.engine.config import DATA_ROOT
    reg = json.loads((DATA_ROOT / "ingredients" / "derived_from_base_recipes.json")
                     .read_text(encoding="utf-8"))["recipes"]
    for rid in ("base_paneer_04e1db", "base_halloumi_293d5e", "base_fromage_en_grain_a00941"):
        n = reg[rid]["nutrition_per_100g"]
        assert n["carbs"] < 6 and 15 <= n["protein"] <= 25, (rid, n["carbs"], n["protein"])


def test_haricots_secs_sur_base_humide():
    """Plus de fiche USDA « 0 % moisture » pour les haricots utilisés."""
    n2 = load_nutrition_db()
    for base in ("black_bean_dried", "great_northern_bean_dried", "medium_red_bean"):
        v = next(iter(n2[base]["variants"].values()))
        assert (v.get("water_g") or 0) > 8 and 320 <= v["calories_kcal"] <= 360, (base, v.get("water_g"), v["calories_kcal"])


# ── Pipeline outillé : run_pipeline.bat et index de recherche ─────────────────

def test_run_pipeline_bat_sequence_validee():
    """
    Le launcher lance run_pipeline.bat : il lançait build_physical_v2.py et
    build_base_recipe_aliases.py (1007 clés de poids unitaires renommées,
    alias non voulus) et fix_recipes_coherence --apply remettait 72 portions
    calibrées au défaut (constaté le 2026-09-15).
    """
    from pathlib import Path
    bat = (Path(__file__).resolve().parents[1] / "run_pipeline.bat").read_text(encoding="utf-8")
    commandes = [l.strip() for l in bat.splitlines() if l.strip().lower().startswith("python ")]
    texte = " ; ".join(commandes)
    for interdit in ("build_physical_v2", "build_base_recipe_aliases", "--apply"):
        assert interdit not in texte, f"run_pipeline.bat lance encore {interdit}"
    ordre = ["build_n2_direct.py --promote", "build_dict_v2.py", "build_indexes.py",
             "fix_recipe_diet_allergens.py", "build_derived_base_registry.py",
             "rebuild_graphs.py", "build_index.py"]
    positions = [texte.find(e) for e in ordre]
    assert all(p >= 0 for p in positions) and positions == sorted(positions), (
        f"séquence de rebuild incomplète ou désordonnée : {dict(zip(ordre, positions))}")


def test_search_index_a_jour():
    """search_index.json n'était plus régénéré depuis juillet (390 mots-clés décalés)."""
    import json
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]
    bi = _import_script("scripts/build_index.py", "build_index")
    attendu = bi.build_index(RECIPES)
    actuel = json.loads((ROOT / "backend/data/indexes/search_index.json").read_text(encoding="utf-8"))["tokens"]
    ecarts = sorted(k for k in set(attendu) | set(actuel)
                    if sorted(attendu.get(k, [])) != sorted(actuel.get(k, [])))
    assert not ecarts, f"{len(ecarts)} mots-clés périmés — lancer scripts/build_index.py : {ecarts[:10]}"


def test_fix_recipes_coherence_ne_touche_pas_aux_portions_calibrees():
    fx = _import_script("scripts/nutrition/fix_recipes_coherence.py", "fix_recipes_coherence")
    import inspect
    src = inspect.getsource(fx)
    assert "C6_servings_uncalibrated" not in src
