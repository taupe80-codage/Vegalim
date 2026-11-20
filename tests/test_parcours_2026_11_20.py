"""Revue des parcours (2026-11-20) : planning généré, version vegan d'une fiche, frigo."""
import random

import pytest
from fastapi.testclient import TestClient

from backend.core.data_io import is_component_recipe, load_recipes

IDX = {r["id"]: r for r in load_recipes()}
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


# ── Planning ──────────────────────────────────────────────────────────────────

def test_preferences_pratiques_du_planning():
    from backend.engine.planning_engine.planner import _practical_score
    trempage = {"dish_type": "main", "timing": {"prep_passive_min": 720}}
    assert _practical_score(trempage, 2, 20) < _practical_score(trempage, 6, 20)   # mercredi < dimanche
    plat = {"dish_type": "main", "timing": {}}
    assert _practical_score(plat, 6, 25) > _practical_score(plat, 6, 12) > _practical_score(plat, 6, 8)
    assert _practical_score({"dish_type": "dessert", "timing": {}}, 6, 2) == 0   # pas de malus hors plat


def test_planning_sans_trempage_en_semaine_et_signale():
    from backend.engine.planning_engine.planner import generate_plan
    random.seed(1)
    plan = generate_plan(dish_type="main", month=11, diversity=0.5)
    for i, d in enumerate(DAYS):
        for meal in ("lunch", "dinner"):
            item = plan[d][meal]
            passive = (IDX[item["id"]].get("timing") or {}).get("prep_passive_min") or 0
            assert item["prep_ahead"] == (passive >= 240)
            if i < 5:
                assert not item["prep_ahead"], (d, item["title_fr"])


def test_planning_varie_d_une_semaine_a_l_autre():
    # vivier fixe de 12 : 30 semaines ne puisaient que dans ~25 plats
    from backend.engine.planning_engine.planner import generate_plan
    ids = set()
    for seed in range(6):
        random.seed(seed)
        p = generate_plan(dish_type="main", month=11, diversity=0.5)
        ids |= {p[d][m]["id"] for d in DAYS for m in ("lunch", "dinner")}
    assert len(ids) >= 25          # 6 semaines ; avant : 25 plats sur 30 semaines


# ── Version vegan ─────────────────────────────────────────────────────────────

def test_variante_vegan_recalcule_allergenes_et_regimes():
    from backend.engine.rule_engine.variants import vegan_variant
    v = vegan_variant(IDX["curry_matar_paneer_4a7c19"])["recipe"]          # paneer → tofu
    assert set(v["tags"]["allergens"]) == {"soy"}
    assert v["diet_flags"]["vegan"] and v["diet_flags"]["lactose_free"]
    assert v["diet_flags_enriched"] == {"egg_free": True, "dairy_free": True, "soy_free": False}

    d = vegan_variant(IDX["tart_asperges_vertes_ricotta_2c85b3"])           # ricotta de cajou, tofu soyeux
    t = d["recipe"]
    assert d["source"] == "generated"                                       # pâte brisée végétale
    assert {"tree_nuts", "soy"} <= set(t["tags"]["allergens"])
    assert not {"eggs", "milk"} & set(t["tags"]["allergens"])               # plus de beurre dans la pâte
    assert t["diet_flags"]["nut_free"] is False and t["diet_flags"]["vegan"] is True


def test_allergen_tags_coherent_avec_les_donnees():
    from backend.engine.rule_engine.diet import allergen_tags
    fautes = [r["id"] for r in IDX.values()
              if not set(allergen_tags(r)) <= set((r.get("tags") or {}).get("allergens") or [])]
    assert not fautes, fautes[:10]


# ── Frigo ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nom, attendu, exclu", [
    ("fromage râpé", "gruyere_whole_cow", None),
    ("crème fraîche", "cream_heavy_refrigerated_30pct", None),
    ("courge", "pumpkin_raw", None),
    ("farine", "wheat_flour_t55", "chickpea_flour"),
])
def test_noms_courants_du_frigo(nom, attendu, exclu):
    from backend.services.ingredient_catalog import resolve_names
    ids = resolve_names([nom])[nom]
    assert attendu in ids and exclu not in ids


def _suggest(fridge):
    from backend.api.main import app
    return TestClient(app).post("/frigo/suggestions",
                                json={"ingredients": fridge, "max_missing": 3, "limit": 10}).json()["results"]


def test_frigo_privilegie_les_recettes_qui_l_utilisent():
    res = _suggest(["oeufs", "lait", "farine"])
    assert len(res[0]["have"]) >= 3                      # crêpes, pas un pain à la seule farine
    assert all("pain de campagne" not in r["title_fr"].lower() for r in res)
    res = _suggest(["tofu", "riz", "brocoli", "sauce soja", "gingembre", "ail"])
    assert len(res[0]["have"]) >= 4                      # tofu sauté, pas « Riz blanc »
    assert not any(is_component_recipe(IDX[r["id"]]) for r in res)


# ── Version vegan : étapes réécrites ─────────────────────────────────────────

def _steps(rid):
    from backend.engine.rule_engine.variants import vegan_variant
    return " ".join(vegan_variant(IDX[rid])["recipe"]["instructions"])


def test_etapes_vegan_reecrites():
    tarte = _steps("tart_asperges_vertes_ricotta_2c85b3")
    assert "150 g de tofu soyeux" in tarte and "3 œufs" not in tarte        # « 3 œufs (150 g) »
    assert "40 g de levure nutritionnelle en paillettes" in tarte
    assert "250 g de ricotta de cajou" in tarte
    radis = _steps("side_radis_glaces_miel_3a8e51")
    assert "15 g de sirop d'agave" in radis and "beurre végétal" in radis
    holl = _steps("main_spargel_sauce_hollandaise_3d9f15")
    assert "60 g de tofu soyeux" in holl and "jaunes d'œufs" not in holl


def test_etapes_vegan_prudentes():
    import re
    from backend.engine.rule_engine.variants import vegan_variant
    for r in IDX.values():
        if is_component_recipe(r) or (r.get("diet_flags") or {}).get("vegan"):
            continue
        for o, v in zip(r.get("instructions") or [], vegan_variant(r)["recipe"].get("instructions") or []):
            if o == v:
                continue
            assert not re.search(r"\b(les|des|\d+) tofu soyeux(?! \()", v) or re.search(r"\d+ ?(g|ml) de tofu soyeux", v), v
            assert "d'yaourt" not in v and "de la yaourt" not in v, v
            assert ("de haricots" in v) or ("de haricots" not in o), v          # texte voisin intact


def test_variante_vegan_description_reecrite():
    """La description suivait le plat d'origine (« monté au ghee ») ; le titre reste
    le nom du plat. « à l'huile », pas « à la huile » ; majuscule de début gardée."""
    from backend.core.data_io import load_recipes
    from backend.engine.rule_engine.variants import vegan_variant
    r = next(x for x in load_recipes() if x["id"] == "curry_palak_paneer_b4ca11")
    v = vegan_variant(r)["recipe"]
    assert v["description"].startswith("Tofu maison")
    assert "montée à l'huile de coco" in v["description"] and "ghee" not in v["description"]
    assert v["titles"]["fr"] == r["titles"]["fr"]
    assert any("30 ml d'huile de coco" in s for s in v["instructions"])


def test_variantes_vegan_completes():
    """Fromages sous leur id réel (gruyere_whole_cow…), pâte brisée et pâte à
    empanada végétales, nouilles sans œuf : 44 variantes incomplètes → 10."""
    from backend.core.data_io import load_recipes
    from backend.engine.rule_engine.variants import vegan_variant
    idx = {r["id"]: r for r in load_recipes()}
    restes = {u["id"] for r in idx.values() if r.get("composition") and not r["id"].startswith("base_")
              for u in vegan_variant(r)["unresolved"]}
    # les 6 derniers ont leur version vegan maison (lot n18) depuis le 2026-11-20
    assert restes == set(), restes
    v = vegan_variant(idx["dessert_tarte_citron_meringuee_7f6440"])
    assert v["source"] == "generated"
    assert "200 g de pâte brisée végétale et la cuire" in v["recipe"]["instructions"][0]
    # « pâtes aux œufs » : pas de « pâtes œufs » (préfixe « pâtes aux » écarté)
    assert all("pâtes œufs" not in s for s in vegan_variant(idx["dal_linsen_spatzle_71ea34"])["recipe"]["instructions"])


def test_variantes_vegan_preparations_maison():
    """Roux, spätzle, galette, glace et boudoirs vegan (lot n18) ; « lait » liquide ne
    devient pas « farine d'amande » (début de « lait en poudre ») ; pas d'écho
    « roux de curry japonais au beurre végétal de curry »."""
    from backend.core.data_io import load_recipes
    from backend.engine.rule_engine.variants import vegan_variant
    from backend.engine.planning_engine.budget import estimate_price
    idx = {r["id"]: r for r in load_recipes()}
    for rid in ("base_roux_curry_japonais_vegetal_f245c7", "base_spaetzle_vegan_265b64",
                "base_galette_sarrasin_eau_533afe", "base_glace_vanille_vegan_4e694a",
                "base_biscuits_cuillere_vegan_40fae8"):
        assert idx[rid]["diet_flags"]["vegan"] is True, rid
    gj = vegan_variant(idx["dessert_gulab_jamun_a6b371"])["recipe"]["instructions"]
    assert "200 g de farine d'amande" in gj[1] and "60 ml de lait de soja" in gj[2]
    cj = vegan_variant(idx["curry_japonais_1caddf"])
    assert cj["source"] == "generated" and estimate_price(cj["recipe"])["complete"]
    assert any("80 g de roux de curry japonais au beurre végétal dans la sauce" in s
               for s in cj["recipe"]["instructions"])


def test_variante_vegan_description_sans_oeuf_ni_nom_anglais():
    """Vu à l'écran : « appareil de ricotta de cajou, d'œufs… » (description), « 300 g de
    ladyfinger » (nom anglais), « l'tofu soyeux », « à le tofu soyeux »."""
    from backend.core.data_io import load_recipes
    from backend.engine.rule_engine.variants import vegan_variant
    idx = {r["id"]: r for r in load_recipes()}
    tarte = vegan_variant(idx["tart_asperges_vertes_ricotta_2c85b3"])["recipe"]
    assert "un appareil de ricotta de cajou, de tofu soyeux et de levure" in tarte["description"]
    assert tarte["ingredients_meta"]["shortcrust_pastry_vegetable_fat_raw_paste_pre_packaged_plant"][
        "name_fr"].lower() == "pâte brisée végétale"
    tira = vegan_variant(idx["dessert_tiramisu_classique_ea8ddb"])["recipe"]
    assert "ladyfinger" not in (tira["description"] + " ".join(tira["instructions"])).lower()
    katsu = vegan_variant(idx["bread_katsu_bf3f1e"])["recipe"]["description"]
    assert "panées au tofu soyeux" in katsu
    quiche = vegan_variant(next(r for i, r in idx.items() if i.startswith("egg_quiche_lorraine_vegetarien")))
    assert "œufs-crème" in quiche["recipe"]["description"]          # mot composé laissé tel quel


def test_similaires_sans_preparation_de_base_et_par_regime():
    """Un plat ne propose plus de sauce ou de pâte comme « recette similaire » ; en
    version vegan (diet=vegan), les suggestions sont vegan."""
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.services.filter_service import match_diet
    from backend.core.data_io import load_recipes
    idx = {r["id"]: r for r in load_recipes()}
    c = TestClient(app)
    tous = c.get("/recettes/tart_asperges_vertes_ricotta_2c85b3/similaires?limit=10").json()["similar"]
    assert tous and not any(s["id"].startswith("base_") for s in tous)
    assert any(not match_diet(idx[s["id"]], "vegan") for s in tous)
    veg = c.get("/recettes/tart_asperges_vertes_ricotta_2c85b3/similaires?limit=10&diet=vegan").json()["similar"]
    assert len(veg) == 10 and all(match_diet(idx[s["id"]], "vegan") for s in veg)
    # une préparation de base peut, elle, proposer d'autres préparations
    sauce = c.get("/recettes/base_mayonnaise_0d3e4e/similaires?limit=10").json()["similar"]
    assert any(s["id"].startswith("base_") for s in sauce)


def test_variante_vegan_sans_qualificatif_laitier():
    """« crème de soja maison fraîche », « lait de soja entier / de vache » : le
    qualificatif du produit d'origine disparaît avec lui."""
    import re
    from backend.core.data_io import load_recipes
    from backend.engine.rule_engine.variants import vegan_variant, _short
    restes = []
    for r in load_recipes():
        if not r.get("composition") or r["id"].startswith("base_"):
            continue
        v = vegan_variant(r)
        textes = [v["recipe"].get("description") or ""] + [s for s in v["recipe"]["instructions"] if isinstance(s, str)]
        for s in {_short(x["substitute_name"]) for x in v["substitutions"]}:
            pat = re.compile(re.escape(s) + r" (?:fraîches?|entiers?|entières?|de vache)\b", re.I)
            restes += [r["id"] for t in textes if pat.search(t)]
    assert restes == []
