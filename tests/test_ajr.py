"""
tests/test_ajr.py — Tests unitaires de score_engine/ajr.py.

Couverture :
    ajr_score                 nutrition vide / couverture partielle / score pondéré
                              vs non pondéré / nutriments à limiter / bornes
    compute_ajr_score         alias float
    ajr_score_with_profile    profil diabète / hyperprotéiné / sans profil /
                              bornes 0-10
    detect_deficiencies       aucune carence / carence high / carence medium /
                              nutriments à limiter exclus / ajr personnalisé
    summarize_deficiencies    structure / high vs medium / liste vide
    NUTRIENT_WEIGHTS          cohérence des poids plant-based
    meal_score                portion : calories non récompensées, pénalités
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Fixture
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def ajr():
    for mod in ["backend", "backend.engine",
                "backend.engine.multi_profile_nutrition_engine"]:
        sys.modules.setdefault(mod, types.ModuleType(mod))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ajr",
        Path(__file__).parent.parent / "backend" /
        "engine" / "score_engine" / "ajr.py",
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["ajr"] = m
    spec.loader.exec_module(m)
    return m


# ── Données réutilisables ─────────────────────────────────────────────────────

NUTR_COMPLET = {
    "calories": 500, "protein": 25,  "carbs": 70,  "fat": 18,
    "fiber": 10,     "sugar": 8,     "sodium": 600,
    "iron": 8,       "calcium": 400, "magnesium": 150,
    "potassium": 800, "zinc": 4,     "vitamin_c": 50,
    "vitamin_d": 6,  "vitamin_b12": 1.2, "phosphorus": 300,
}

NUTR_PAUVRE = {
    "calories": 200, "protein": 5, "carbs": 30, "fat": 5,
    "sodium": 2000,  "sugar": 45,
}

NUTR_VIDE = {}


# ═══════════════════════════════════════════════════════════════════════════════
# ajr_score
# ═══════════════════════════════════════════════════════════════════════════════

class TestAjrScore:

    def test_nutrition_vide_retourne_zero(self, ajr):
        r = ajr.ajr_score(NUTR_VIDE)
        assert r["score"]    == 0.0
        assert r["coverage"] == 0.0
        assert r["details"]  == {}

    def test_nutrition_none_retourne_zero(self, ajr):
        r = ajr.ajr_score(None)
        assert r["score"] == 0.0

    def test_score_entre_zero_et_dix(self, ajr):
        r = ajr.ajr_score(NUTR_COMPLET)
        assert 0.0 <= r["score"] <= 10.0

    def test_coverage_proportionnel_aux_nutriments_presents(self, ajr):
        r_complet = ajr.ajr_score(NUTR_COMPLET)
        r_partiel = ajr.ajr_score({"protein": 20, "fiber": 10})
        assert r_complet["coverage"] > r_partiel["coverage"]

    def test_sodium_eleve_penalise(self, ajr):
        """sodium est dans _LIMIT : valeur élevée → mauvais ratio."""
        nutr_low_na  = dict(NUTR_COMPLET, sodium=300)
        nutr_high_na = dict(NUTR_COMPLET, sodium=5000)
        r_low  = ajr.ajr_score(nutr_low_na)
        r_high = ajr.ajr_score(nutr_high_na)
        assert r_low["score"] > r_high["score"]

    def test_sucre_eleve_penalise(self, ajr):
        nutr_low_s  = dict(NUTR_COMPLET, sugar=5)
        nutr_high_s = dict(NUTR_COMPLET, sugar=80)
        r_low  = ajr.ajr_score(nutr_low_s)
        r_high = ajr.ajr_score(nutr_high_s)
        assert r_low["score"] > r_high["score"]

    def test_score_pondere_vs_non_pondere(self, ajr):
        """Recette riche en micronutriments : score pondéré ≥ non pondéré."""
        nutr_micro = dict(NUTR_COMPLET,
                          iron=12, vitamin_b12=2.0, calcium=800,
                          zinc=8, vitamin_d=12)
        r_pond    = ajr.ajr_score(nutr_micro)
        r_nonpond = ajr.ajr_score(nutr_micro, weights={})
        # Les micronutriments à ×2 font monter le score pondéré
        assert r_pond["score"] >= r_nonpond["score"]

    def test_poids_micronutriments_superieurs_macros(self, ajr):
        """iron, vitamin_b12, calcium, zinc, vitamin_d ont poids > carbs/fat."""
        w = ajr.NUTRIENT_WEIGHTS
        for micro in ("iron", "vitamin_b12", "calcium", "zinc", "vitamin_d"):
            for macro in ("carbs", "fat", "calories"):
                assert w[micro] > w[macro], (
                    f"{micro} ({w[micro]}) devrait peser plus que {macro} ({w[macro]})"
                )

    def test_details_contient_weight(self, ajr):
        r = ajr.ajr_score({"iron": 5, "protein": 20})
        for nutrient, detail in r["details"].items():
            assert "weight" in detail, f"weight manquant pour {nutrient}"

    def test_details_ok_flag(self, ajr):
        """Nutriment à ≥50% AJR → ok=True."""
        r = ajr.ajr_score({"iron": 7.0})   # AJR=14, ratio=0.5 → ok=True
        assert r["details"]["iron"]["ok"] is True

    def test_ratio_nutriment_limite_inversé(self, ajr):
        """Pour sodium : ratio = max(0, 1 - val/ref). Moins de sodium → ratio proche de 1."""
        r = ajr.ajr_score({"sodium": 100})
        ratio = r["details"]["sodium"]["ratio"]
        assert ratio > 0.9  # 1 - 100/2300 ≈ 0.957


# ═══════════════════════════════════════════════════════════════════════════════
# compute_ajr_score
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeAjrScore:

    def test_retourne_float(self, ajr):
        result = ajr.compute_ajr_score(NUTR_COMPLET)
        assert isinstance(result, float)

    def test_coherent_avec_ajr_score(self, ajr):
        assert ajr.compute_ajr_score(NUTR_COMPLET) == ajr.ajr_score(NUTR_COMPLET)["score"]

    def test_zero_pour_nutrition_vide(self, ajr):
        assert ajr.compute_ajr_score({}) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# ajr_score_with_profile
# ═══════════════════════════════════════════════════════════════════════════════

class TestAjrScoreWithProfile:

    def test_retourne_float_0_10(self, ajr):
        score = ajr.ajr_score_with_profile(NUTR_COMPLET)
        assert isinstance(score, float)
        assert 0.0 <= score <= 10.0

    def test_sans_profil_applique_malus_sucre_standard(self, ajr):
        """Sans profil, malus sucre standard (×0.02) appliqué."""
        nutr_no_sugar  = dict(NUTR_COMPLET, sugar=0)
        nutr_high_sugar = dict(NUTR_COMPLET, sugar=50)
        s_no   = ajr.ajr_score_with_profile(nutr_no_sugar)
        s_high = ajr.ajr_score_with_profile(nutr_high_sugar)
        assert s_no >= s_high

    def test_profil_diabete_malus_sucre_renforce(self, ajr):
        """Profil diabète : malus sucre ×0.1 vs malus standard ×0.02."""
        nutr = dict(NUTR_COMPLET, sugar=20)
        s_standard = ajr.ajr_score_with_profile(nutr)
        s_diabete  = ajr.ajr_score_with_profile(nutr, {"diet": "diabete"})
        assert s_diabete < s_standard

    def test_profil_low_sugar_equivalent_diabete(self, ajr):
        nutr = dict(NUTR_COMPLET, sugar=20)
        s1 = ajr.ajr_score_with_profile(nutr, {"diet": "diabete"})
        s2 = ajr.ajr_score_with_profile(nutr, {"low_sugar": True})
        assert s1 == pytest.approx(s2)

    def test_profil_hyperproteine_bonus_proteine(self, ajr):
        nutr = dict(NUTR_COMPLET, protein=30)
        s_normal = ajr.ajr_score_with_profile(nutr)
        s_hyper  = ajr.ajr_score_with_profile(nutr, {"diet": "hyperproteine"})
        assert s_hyper > s_normal

    def test_bonus_proteine_cap_a_2(self, ajr):
        """Bonus protéine plafonné à 2.0."""
        nutr = dict(NUTR_COMPLET, protein=1000)
        s_base  = ajr.ajr_score_with_profile(nutr)
        s_hyper = ajr.ajr_score_with_profile(nutr, {"diet": "hyperproteine"})
        assert s_hyper - s_base <= 2.0 + 0.01

    def test_borne_inferieure_zero(self, ajr):
        nutr = {"sugar": 200, "calories": 100}
        score = ajr.ajr_score_with_profile(nutr, {"diet": "diabete"})
        assert score >= 0.0

    def test_borne_superieure_dix(self, ajr):
        nutr = dict(NUTR_COMPLET, protein=500)
        score = ajr.ajr_score_with_profile(nutr, {"diet": "hyperproteine"})
        assert score <= 10.0

    def test_nutrition_vide_retourne_zero(self, ajr):
        assert ajr.ajr_score_with_profile({}) == 0.0
        assert ajr.ajr_score_with_profile(None) == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# detect_deficiencies
# ═══════════════════════════════════════════════════════════════════════════════

class TestDetectDeficiencies:

    def test_nutrition_vide_retourne_liste_vide(self, ajr):
        assert ajr.detect_deficiencies({}) == []

    def test_nutrition_complete_aucune_carence(self, ajr):
        nutr = {k: v for k, v in ajr.AJR.items()
                if k not in ("sodium", "sugar")}
        defics = ajr.detect_deficiencies(nutr)
        assert defics == []

    def test_carence_high_ratio_inferieur_25pct(self, ajr):
        """iron=1 sur AJR=14 → ratio 0.071 → severity=high."""
        defics = ajr.detect_deficiencies({"iron": 1.0})
        iron   = next((d for d in defics if d["nutrient"] == "iron"), None)
        assert iron is not None
        assert iron["severity"] == "high"
        assert iron["ratio"] < 0.25

    def test_carence_medium_ratio_entre_25_et_50pct(self, ajr):
        """iron=5 sur AJR=14 → ratio 0.357 → severity=medium."""
        defics = ajr.detect_deficiencies({"iron": 5.0})
        iron   = next((d for d in defics if d["nutrient"] == "iron"), None)
        assert iron is not None
        assert iron["severity"] == "medium"

    def test_sodium_et_sugar_exclus(self, ajr):
        """_LIMIT (sodium, sugar) ne génèrent pas de carences."""
        defics = ajr.detect_deficiencies({"sodium": 0, "sugar": 0})
        assert not any(d["nutrient"] in ("sodium", "sugar") for d in defics)

    def test_tri_par_ratio_croissant(self, ajr):
        """La carence la plus sévère (ratio le plus bas) en premier."""
        defics = ajr.detect_deficiencies({
            "iron": 1.0,       # ratio ≈ 0.07
            "vitamin_d": 5.0,  # ratio ≈ 0.33
        })
        ratios = [d["ratio"] for d in defics]
        assert ratios == sorted(ratios)

    def test_ajr_personnalise(self, ajr):
        """Accepte une table AJR alternative."""
        custom_ajr = {"protein": 100.0}
        defics = ajr.detect_deficiencies({"protein": 30}, ajr=custom_ajr)
        assert any(d["nutrient"] == "protein" for d in defics)

    def test_valeur_zero_est_une_carence_high(self, ajr):
        defics = ajr.detect_deficiencies({"vitamin_b12": 0})
        b12 = next((d for d in defics if d["nutrient"] == "vitamin_b12"), None)
        assert b12 is not None
        assert b12["severity"] == "high"


# ═══════════════════════════════════════════════════════════════════════════════
# summarize_deficiencies
# ═══════════════════════════════════════════════════════════════════════════════

class TestSummarizeDeficiencies:

    def test_structure_retour(self, ajr):
        summary = ajr.summarize_deficiencies([])
        assert "high"   in summary
        assert "medium" in summary

    def test_liste_vide_retourne_listes_vides(self, ajr):
        s = ajr.summarize_deficiencies([])
        assert s["high"]   == []
        assert s["medium"] == []

    def test_repartition_high_medium(self, ajr):
        defics = [
            {"nutrient": "iron",       "ratio": 0.1,  "severity": "high"},
            {"nutrient": "zinc",       "ratio": 0.2,  "severity": "high"},
            {"nutrient": "vitamin_d",  "ratio": 0.35, "severity": "medium"},
        ]
        s = ajr.summarize_deficiencies(defics)
        assert "iron"      in s["high"]
        assert "zinc"      in s["high"]
        assert "vitamin_d" in s["medium"]

    def test_fonctionne_apres_detect_deficiencies(self, ajr):
        """Chaîne detect → summarize sans erreur."""
        defics  = ajr.detect_deficiencies({"iron": 1.0, "vitamin_d": 4.0})
        summary = ajr.summarize_deficiencies(defics)
        assert isinstance(summary["high"],   list)
        assert isinstance(summary["medium"], list)

    def test_severite_inconnue_ignoree(self, ajr):
        """Une sévérité non reconnue ne plante pas."""
        defics = [{"nutrient": "x", "ratio": 0.1, "severity": "critical"}]
        s = ajr.summarize_deficiencies(defics)
        assert "x" not in s["high"]
        assert "x" not in s["medium"]


# ═══════════════════════════════════════════════════════════════════════════════
# meal_score — score d'une portion
# ═══════════════════════════════════════════════════════════════════════════════

class TestMealScore:

    def test_vide(self, ajr):
        assert ajr.meal_score({})["score"] == 0.0

    def test_bornes(self, ajr):
        assert 0.0 <= ajr.meal_score(NUTR_COMPLET)["score"] <= 10.0
        assert 0.0 <= ajr.meal_score(NUTR_PAUVRE)["score"] <= 10.0

    def test_calories_ne_rapportent_pas_de_points(self, ajr):
        """Régression 2026-09-14 : l'ancien score journalier faisait monter les
        plats les plus caloriques (brioche 1 855 kcal dans le top)."""
        leger = dict(NUTR_COMPLET, calories=600)
        lourd = dict(NUTR_COMPLET, calories=1800)
        assert ajr.meal_score(lourd)["score"] < ajr.meal_score(leger)["score"]

    def test_portion_raisonnable_non_penalisee(self, ajr):
        assert ajr.meal_score(dict(NUTR_COMPLET, saturated_fat=3))["penalties"] == {}

    def test_penalites_sodium_sucre_graisses_saturees(self, ajr):
        res = ajr.meal_score(dict(NUTR_COMPLET, sodium=2500, sugar=40, saturated_fat=20))
        assert set(res["penalties"]) == {"sodium", "sugar", "saturated_fat"}
        assert res["score"] < res["coverage_score"]

    def test_plus_nutritif_mieux_note(self, ajr):
        assert ajr.meal_score(NUTR_COMPLET)["score"] > ajr.meal_score(NUTR_PAUVRE)["score"]
