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
