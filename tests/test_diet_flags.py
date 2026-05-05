"""
tests/test_diet_flags.py — Tests unitaires du moteur de flags diététiques.

Couvre :
  - compute_diet_flags()    : les 7 flags binaires, logique vegan→vegetarian,
                              cas limites (manuel, ids mixtes, techniques),
                              lactose_trace_note, kid_friendly, raw
  - compute_health_scores() : seuils glycémique, high_protein, low_calorie,
                              high_fiber, low_sodium, fodmap_level,
                              anti_inflammatory_score
  - compute_context_tags()  : sport, meal_timing, cas None
  - apply_all_scores()      : 3 colonnes JSONB, protection flag manual, force=True
  - apply_flags()           : rétrocompatibilité, protection manual
  - batch_update()          : rapport total/updated/skipped/stats, force mode
  - audit()                 : détection divergences, recette sans divergence

Lance avec : pytest tests/test_diet_flags.py -v
"""
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers de construction de recettes
# ═══════════════════════════════════════════════════════════════════════════════

def _recipe(rid=1, *, ingredients=None, composition=None,
            technique=None, prep_time_min=None, cook_time_min=None,
            diet_flags=None, health_scores=None, nutrition_per_serving=None):
    """Construit une recette minimale pour les tests."""
    r = {"id": rid}
    if ingredients is not None:
        r["ingredients"] = [{"ingredient_id": i} for i in ingredients]
    if composition is not None:
        r["composition"] = [{"ingredient": c} for c in composition]
    if technique is not None:
        r["technique"] = technique if isinstance(technique, list) else [technique]
    if prep_time_min is not None:
        r["prep_time_min"] = prep_time_min
    if cook_time_min is not None:
        r["cook_time_min"] = cook_time_min
    if diet_flags is not None:
        r["diet_flags"] = diet_flags
    if health_scores is not None:
        r["health_scores"] = health_scores
    if nutrition_per_serving is not None:
        r["_nutrition_per_serving"] = nutrition_per_serving
    return r


# ═══════════════════════════════════════════════════════════════════════════════
# TestComputeDietFlags
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeDietFlags:

    def setup_method(self):
        from backend.engine.rule_engine.diet import compute_diet_flags
        self.compute = compute_diet_flags

    # ── Structure de sortie ──────────────────────────────────────────────────

    def test_retourne_dict(self):
        flags = self.compute(_recipe(1, ingredients=[]))
        assert isinstance(flags, dict)

    def test_contient_7_flags_standard(self):
        flags = self.compute(_recipe(1, ingredients=[]))
        attendus = {"vegan", "vegetarian", "gluten_free", "lactose_free",
                    "nut_free", "raw", "kid_friendly"}
        assert attendus <= flags.keys()

    def test_tous_flags_sont_booleens(self):
        flags = self.compute(_recipe(1, ingredients=[]))
        bools = {k: v for k, v in flags.items() if not k.endswith("_note")}
        assert all(isinstance(v, bool) for v in bools.values()), \
            f"Flags non booléens : {bools}"

    # ── Recette entièrement vegan ────────────────────────────────────────────

    def test_recette_vegan_pure(self):
        r = _recipe(1, ingredients=["lentil", "carrot", "tomato"])
        flags = self.compute(r)
        assert flags["vegan"]       is True
        assert flags["vegetarian"]  is True

    def test_recette_vegan_implique_vegetarian(self):
        """vegan=True → vegetarian=True sans examen séparé de NON_VEGETARIAN."""
        r = _recipe(1, ingredients=["tofu", "spinach"])
        flags = self.compute(r)
        assert flags["vegan"] is True
        assert flags["vegetarian"] is True

    # ── Ingrédients non-vegan mais végétariens ───────────────────────────────

    def test_oeuf_non_vegan_mais_vegetarien(self):
        r = _recipe(2, ingredients=["egg", "flour"])
        flags = self.compute(r)
        assert flags["vegan"]      is False
        assert flags["vegetarian"] is True

    def test_beurre_non_vegan(self):
        r = _recipe(3, ingredients=["butter", "lentil"])
        flags = self.compute(r)
        assert flags["vegan"] is False

    def test_fromage_non_vegan(self):
        r = _recipe(4, ingredients=["parmesan", "pasta"])
        flags = self.compute(r)
        assert flags["vegan"] is False

    def test_miel_non_vegan(self):
        r = _recipe(5, ingredients=["honey", "lemon"])
        flags = self.compute(r)
        assert flags["vegan"] is False

    # ── Ingrédients non-végétariens ──────────────────────────────────────────

    def test_poulet_non_vegetarien(self):
        r = _recipe(6, ingredients=["chicken", "lemon"])
        flags = self.compute(r)
        assert flags["vegan"]      is False
        assert flags["vegetarian"] is False

    def test_saumon_non_vegetarien(self):
        r = _recipe(7, ingredients=["salmon", "dill"])
        flags = self.compute(r)
        assert flags["vegetarian"] is False

    def test_anchois_non_vegetarien(self):
        r = _recipe(8, ingredients=["anchovy", "garlic"])
        flags = self.compute(r)
        assert flags["vegetarian"] is False

    def test_bacon_non_vegetarien(self):
        r = _recipe(9, ingredients=["bacon", "egg"])
        flags = self.compute(r)
        assert flags["vegetarian"] is False

    def test_gelatin_non_vegetarien(self):
        """Gélatine = agent d'origine animale → non-végétarien."""
        r = _recipe(10, ingredients=["gelatin", "sugar"])
        flags = self.compute(r)
        assert flags["vegetarian"] is False

    # ── Gluten ───────────────────────────────────────────────────────────────

    def test_recette_sans_gluten(self):
        r = _recipe(11, ingredients=["rice", "carrot"])
        flags = self.compute(r)
        assert flags["gluten_free"] is True

    def test_farine_bloque_gluten_free(self):
        r = _recipe(12, ingredients=["flour", "sugar"])
        flags = self.compute(r)
        assert flags["gluten_free"] is False

    def test_pates_bloquent_gluten_free(self):
        r = _recipe(13, ingredients=["pasta", "tomato"])
        flags = self.compute(r)
        assert flags["gluten_free"] is False

    def test_couscous_bloque_gluten_free(self):
        r = _recipe(14, ingredients=["couscous", "chickpea"])
        flags = self.compute(r)
        assert flags["gluten_free"] is False

    def test_seitan_bloque_gluten_free(self):
        r = _recipe(15, ingredients=["seitan", "soy_sauce"])
        flags = self.compute(r)
        assert flags["gluten_free"] is False

    # ── Lactose ──────────────────────────────────────────────────────────────

    def test_recette_sans_lactose(self):
        r = _recipe(16, ingredients=["tofu", "rice"])
        flags = self.compute(r)
        assert flags["lactose_free"] is True

    def test_lait_bloque_lactose_free(self):
        r = _recipe(17, ingredients=["milk", "banana"])
        flags = self.compute(r)
        assert flags["lactose_free"] is False

    def test_creme_fraiche_bloque_lactose_free(self):
        r = _recipe(18, ingredients=["creme_fraiche", "mushroom"])
        flags = self.compute(r)
        assert flags["lactose_free"] is False

    def test_mozzarella_bloque_lactose_free(self):
        r = _recipe(19, ingredients=["mozzarella", "tomato"])
        flags = self.compute(r)
        assert flags["lactose_free"] is False

    # ── Lactose trace (ghee, kashk) ──────────────────────────────────────────

    def test_ghee_ne_bloque_pas_lactose_free(self):
        """ghee → LACTOSE_TRACE_IDS : lactose_free reste True."""
        r = _recipe(20, ingredients=["ghee", "spinach"])
        flags = self.compute(r)
        assert flags["lactose_free"] is True

    def test_ghee_ajoute_lactose_trace_note(self):
        r = _recipe(21, ingredients=["ghee", "onion"])
        flags = self.compute(r)
        assert "lactose_trace_note" in flags
        assert "ghee" in flags["lactose_trace_note"]

    def test_kashk_ajoute_lactose_trace_note(self):
        r = _recipe(22, ingredients=["kashk", "walnut"])
        flags = self.compute(r)
        assert "lactose_trace_note" in flags

    def test_sans_trace_pas_de_lactose_trace_note(self):
        r = _recipe(23, ingredients=["lentil", "carrot"])
        flags = self.compute(r)
        assert "lactose_trace_note" not in flags

    # ── Fruits à coque ───────────────────────────────────────────────────────

    def test_recette_nut_free(self):
        r = _recipe(24, ingredients=["rice", "pepper"])
        flags = self.compute(r)
        assert flags["nut_free"] is True

    def test_amande_bloque_nut_free(self):
        r = _recipe(25, ingredients=["almond", "sugar"])
        flags = self.compute(r)
        assert flags["nut_free"] is False

    def test_cajou_bloque_nut_free(self):
        r = _recipe(26, ingredients=["cashew", "lime"])
        flags = self.compute(r)
        assert flags["nut_free"] is False

    def test_beurre_de_cacahuete_bloque_nut_free(self):
        r = _recipe(27, ingredients=["peanut_butter", "banana"])
        flags = self.compute(r)
        assert flags["nut_free"] is False

    # ── Raw (cru) ────────────────────────────────────────────────────────────

    def test_technique_raw(self):
        r = _recipe(28, ingredients=["tomato"], technique="raw")
        flags = self.compute(r)
        assert flags["raw"] is True

    def test_technique_cru(self):
        r = _recipe(29, ingredients=["carrot"], technique="cru")
        flags = self.compute(r)
        assert flags["raw"] is True

    def test_technique_ceviche(self):
        r = _recipe(30, ingredients=["lime"], technique="ceviche")
        flags = self.compute(r)
        assert flags["raw"] is True

    def test_technique_cuisson_pas_raw(self):
        r = _recipe(31, ingredients=["potato"], technique="roasting")
        flags = self.compute(r)
        assert flags["raw"] is False

    def test_pas_de_technique_pas_raw(self):
        r = _recipe(32, ingredients=["lentil"])
        flags = self.compute(r)
        assert flags["raw"] is False

    # ── Kid friendly ─────────────────────────────────────────────────────────

    def test_recette_kid_friendly(self):
        """≤8 ingrédients, ≤30 min, pas d'épices fortes."""
        r = _recipe(33, ingredients=["pasta", "tomato", "olive_oil"],
                    prep_time_min=20)
        flags = self.compute(r)
        assert flags["kid_friendly"] is True

    def test_harissa_exclut_kid_friendly(self):
        r = _recipe(34, ingredients=["lentil", "harissa"], prep_time_min=15)
        flags = self.compute(r)
        assert flags["kid_friendly"] is False

    def test_piment_exclut_kid_friendly(self):
        r = _recipe(35, ingredients=["tofu", "piment"], prep_time_min=10)
        flags = self.compute(r)
        assert flags["kid_friendly"] is False

    def test_trop_long_exclut_kid_friendly(self):
        r = _recipe(36, ingredients=["lentil", "carrot"], prep_time_min=60)
        flags = self.compute(r)
        assert flags["kid_friendly"] is False

    def test_trop_ingredients_exclut_kid_friendly(self):
        """Plus de 8 ingrédients → kid_friendly=False."""
        ids = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]  # 9
        r = _recipe(37, ingredients=ids, prep_time_min=20)
        flags = self.compute(r)
        assert flags["kid_friendly"] is False

    # ── Lecture depuis composition (fallback) ────────────────────────────────

    def test_extrait_ids_depuis_composition(self):
        """_extract_ids() lit aussi recipe['composition']."""
        r = {
            "id": 38,
            "composition": [{"ingredient": "chicken"}, {"ingredient": "lemon"}],
        }
        flags = self.compute(r)
        assert flags["vegetarian"] is False

    def test_extrait_ids_depuis_ingredients_et_composition(self):
        """Les deux sources sont fusionnées."""
        r = {
            "id": 39,
            "ingredients": [{"ingredient_id": "flour"}],
            "composition": [{"ingredient": "egg"}],
        }
        flags = self.compute(r)
        assert flags["gluten_free"] is False  # flour
        assert flags["vegan"]       is False  # egg

    # ── Protection flag manuel ────────────────────────────────────────────────

    def test_flag_manuel_non_recalcule(self):
        """diet_flags_source='manual' → le dict existant est retourné tel quel."""
        manual = {
            "vegan": True, "vegetarian": True, "gluten_free": True,
            "lactose_free": True, "nut_free": True, "raw": False,
            "kid_friendly": False, "diet_flags_source": "manual",
        }
        r = _recipe(40, ingredients=["chicken"], diet_flags=manual)
        flags = self.compute(r)
        assert flags is manual   # même objet, pas de recalcul
        assert flags["vegan"] is True  # conservé malgré chicken

    # ── Recette vide ─────────────────────────────────────────────────────────

    def test_recette_vide_all_true_sauf_kid(self):
        """Aucun ingrédient → vegan/vegetarian/gluten_free/lactose_free/nut_free=True."""
        r = _recipe(41)
        flags = self.compute(r)
        assert flags["vegan"]        is True
        assert flags["vegetarian"]   is True
        assert flags["gluten_free"]  is True
        assert flags["lactose_free"] is True
        assert flags["nut_free"]     is True


# ═══════════════════════════════════════════════════════════════════════════════
# TestComputeHealthScores
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeHealthScores:

    def setup_method(self):
        from backend.engine.rule_engine.diet import compute_health_scores
        self.compute = compute_health_scores

    def _r(self, **nutr):
        return {"id": 1, "_nutrition_per_serving": nutr}

    # ── Structure ────────────────────────────────────────────────────────────

    def test_retourne_dict(self):
        assert isinstance(self.compute(self._r()), dict)

    def test_cles_attendues_presentes(self):
        hs = self.compute(self._r())
        for cle in ("glycemic_category", "high_protein", "low_calorie",
                    "high_fiber", "low_sodium", "fodmap_level",
                    "anti_inflammatory_score"):
            assert cle in hs, f"Clé manquante : {cle}"

    # ── Glycemic category ────────────────────────────────────────────────────

    def test_glycemic_low(self):
        assert self.compute(self._r(glycemic_index=5))["glycemic_category"] == "low"

    def test_glycemic_medium(self):
        assert self.compute(self._r(glycemic_index=9))["glycemic_category"] == "medium"

    def test_glycemic_high(self):
        assert self.compute(self._r(glycemic_index=15))["glycemic_category"] == "high"

    def test_glycemic_seuil_bas_exact(self):
        """gi=8 → medium (borne exclusive pour low)."""
        assert self.compute(self._r(glycemic_index=8))["glycemic_category"] == "medium"

    def test_glycemic_seuil_haut_exact(self):
        """gi=12 → high (borne exclusive pour medium)."""
        assert self.compute(self._r(glycemic_index=12))["glycemic_category"] == "high"

    # ── High protein ─────────────────────────────────────────────────────────

    def test_high_protein_vrai(self):
        assert self.compute(self._r(protein=25))["high_protein"] is True

    def test_high_protein_faux(self):
        assert self.compute(self._r(protein=10))["high_protein"] is False

    def test_high_protein_seuil_exact(self):
        """Seuil = 20g → high_protein=True."""
        assert self.compute(self._r(protein=20))["high_protein"] is True

    def test_protein_g_arrondi(self):
        hs = self.compute(self._r(protein=18.567))
        assert hs["protein_g"] == round(18.567, 1)

    # ── Low calorie ──────────────────────────────────────────────────────────

    def test_low_calorie_vrai(self):
        assert self.compute(self._r(calories=200))["low_calorie"] is True

    def test_low_calorie_faux(self):
        assert self.compute(self._r(calories=450))["low_calorie"] is False

    def test_kcal_arrondi(self):
        hs = self.compute(self._r(calories=349.7))
        assert hs["kcal"] == 350

    # ── High fiber ───────────────────────────────────────────────────────────

    def test_high_fiber_vrai(self):
        assert self.compute(self._r(fiber=10))["high_fiber"] is True

    def test_high_fiber_faux(self):
        assert self.compute(self._r(fiber=3))["high_fiber"] is False

    def test_high_fiber_seuil_exact(self):
        assert self.compute(self._r(fiber=8))["high_fiber"] is True

    # ── Low sodium ───────────────────────────────────────────────────────────

    def test_low_sodium_vrai(self):
        assert self.compute(self._r(sodium=100))["low_sodium"] is True

    def test_low_sodium_faux(self):
        assert self.compute(self._r(sodium=350))["low_sodium"] is False

    # ── Anti-inflammatory ────────────────────────────────────────────────────

    def test_anti_inflam_high(self):
        assert self.compute(self._r(omega_3=1.5))["anti_inflammatory_score"] == "high"

    def test_anti_inflam_medium(self):
        assert self.compute(self._r(omega_3=0.5))["anti_inflammatory_score"] == "medium"

    def test_anti_inflam_low(self):
        assert self.compute(self._r(omega_3=0.1))["anti_inflammatory_score"] == "low"

    def test_anti_inflam_seuil_high(self):
        """omega_3=1.0 → high (borne inclusive)."""
        assert self.compute(self._r(omega_3=1.0))["anti_inflammatory_score"] == "high"

    # ── FODMAP ───────────────────────────────────────────────────────────────

    def test_fodmap_low_zero_triggers(self):
        r = {"id": 1, "ingredients": [{"ingredient_id": "rice"}], "_nutrition_per_serving": {}}
        assert self.compute(r)["fodmap_level"] == "low"

    def test_fodmap_medium(self):
        r = {"id": 1, "ingredients": [{"ingredient_id": "garlic"},
                                       {"ingredient_id": "onion"}],
             "_nutrition_per_serving": {}}
        assert self.compute(r)["fodmap_level"] == "medium"

    def test_fodmap_high(self):
        r = {"id": 1, "ingredients": [{"ingredient_id": "garlic"},
                                       {"ingredient_id": "onion"},
                                       {"ingredient_id": "apple"},
                                       {"ingredient_id": "honey"}],
             "_nutrition_per_serving": {}}
        assert self.compute(r)["fodmap_level"] == "high"

    # ── Cache — health_scores déjà présent ───────────────────────────────────

    def test_health_scores_existants_retournes_tel_quel(self):
        """Si health_scores est déjà présent, compute_health_scores() ne recalcule pas."""
        existing = {"glycemic_category": "low", "high_protein": True}
        r = {"id": 1, "health_scores": existing}
        result = self.compute(r)
        assert result is existing

    # ── Valeurs nulles / absentes ────────────────────────────────────────────

    def test_nutrition_absente_retourne_defaults(self):
        """Sans _nutrition_per_serving, tous les scores utilisent 0."""
        r = {"id": 1}
        hs = self.compute(r)
        assert hs["glycemic_category"] == "low"   # gi=0 → low
        assert hs["high_protein"]      is False
        assert hs["low_calorie"]       is True     # kcal=0 < 300


# ═══════════════════════════════════════════════════════════════════════════════
# TestComputeContextTags
# ═══════════════════════════════════════════════════════════════════════════════

class TestComputeContextTags:

    def setup_method(self):
        from backend.engine.rule_engine.diet import compute_context_tags
        self.compute = compute_context_tags

    def _r(self, *, protein=0, calories=0, prep=99, cook=99):
        return {
            "id": 1,
            "_nutrition_per_serving": {"protein": protein, "calories": calories},
            "prep_time_min": prep,
            "cook_time_min": cook,
        }

    def test_retourne_none_si_pas_de_tags(self):
        r = self._r(protein=5, calories=300, prep=60, cook=60)
        assert self.compute(r) is None

    def test_sport_high_protein(self):
        r = self._r(protein=25, prep=45)
        tags = self.compute(r)
        assert tags is not None
        assert tags.get("sport", {}).get("high_protein_sport") is True

    def test_sport_post_workout(self):
        """kcal≥400 et protein≥15 → post_workout."""
        r = self._r(protein=18, calories=450, prep=45)
        tags = self.compute(r)
        assert tags.get("sport", {}).get("post_workout") is True

    def test_meal_timing_quick(self):
        r = self._r(prep=10, cook=5)  # total=15 ≤ 20
        tags = self.compute(r)
        assert tags.get("meal_timing", {}).get("quick") is True

    def test_meal_timing_weeknight(self):
        r = self._r(prep=15, cook=10)  # total=25 → weeknight
        tags = self.compute(r)
        assert tags.get("meal_timing", {}).get("weeknight") is True

    def test_pas_de_meal_timing_si_trop_long(self):
        r = self._r(prep=30, cook=30)  # total=60 → ni quick ni weeknight
        tags = self.compute(r)
        # meal_timing absent ou vide
        assert not (tags or {}).get("meal_timing")


# ═══════════════════════════════════════════════════════════════════════════════
# TestApplyAllScores
# ═══════════════════════════════════════════════════════════════════════════════

class TestApplyAllScores:

    def setup_method(self):
        from backend.engine.rule_engine.diet import apply_all_scores
        self.apply = apply_all_scores

    def test_applique_3_colonnes(self):
        r = _recipe(1, ingredients=["lentil"])
        self.apply(r)
        assert "diet_flags"    in r
        assert "health_scores" in r
        assert "context_tags"  in r

    def test_retourne_meme_objet(self):
        r = _recipe(1, ingredients=["lentil"])
        result = self.apply(r)
        assert result is r

    def test_flag_manuel_protege_sans_force(self):
        manual = {"vegan": True, "vegetarian": True, "gluten_free": True,
                  "lactose_free": True, "nut_free": True, "raw": False,
                  "kid_friendly": False, "diet_flags_source": "manual"}
        r = _recipe(2, ingredients=["chicken"], diet_flags=manual)
        # diet_flags_source est au niveau diet_flags, pas recette —
        # apply_all_scores vérifie recipe.get("diet_flags_source") == "manual"
        r["diet_flags_source"] = "manual"
        self.apply(r)
        assert r["diet_flags"]["vegan"] is True  # conservé

    def test_force_recalcule_flag_manuel(self):
        manual = {"vegan": True, "vegetarian": True, "gluten_free": True,
                  "lactose_free": True, "nut_free": True, "raw": False,
                  "kid_friendly": False, "diet_flags_source": "manual"}
        r = _recipe(3, ingredients=["chicken"], diet_flags=manual)
        r["diet_flags_source"] = "manual"
        self.apply(r, force=True)
        # chicken → vegetarian=False, donc vegan doit aussi être False
        assert r["diet_flags"]["vegetarian"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# TestApplyFlags (rétrocompatibilité)
# ═══════════════════════════════════════════════════════════════════════════════

class TestApplyFlags:

    def setup_method(self):
        from backend.engine.rule_engine.diet import apply_flags
        self.apply = apply_flags

    def test_applique_uniquement_diet_flags(self):
        r = _recipe(1, ingredients=["lentil"])
        self.apply(r)
        assert "diet_flags" in r
        assert "health_scores" not in r

    def test_retourne_meme_objet(self):
        r = _recipe(1, ingredients=["tofu"])
        assert self.apply(r) is r

    def test_protection_flag_manuel(self):
        manual = {"vegan": True, "diet_flags_source": "manual"}
        r = _recipe(2, ingredients=["chicken"], diet_flags=manual)
        r["diet_flags_source"] = "manual"
        self.apply(r)
        assert r["diet_flags"]["vegan"] is True

    def test_force_ecrase_flag_manuel(self):
        manual = {"vegan": True, "diet_flags_source": "manual"}
        r = _recipe(3, ingredients=["bacon"], diet_flags=manual)
        r["diet_flags_source"] = "manual"
        self.apply(r, force=True)
        assert r["diet_flags"]["vegetarian"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# TestBatchUpdate
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchUpdate:

    def setup_method(self):
        from backend.engine.rule_engine.diet import batch_update
        self.batch = batch_update

    def _rapport(self, recipes, **kwargs):
        return self.batch(recipes, **kwargs)

    # ── Structure du rapport ─────────────────────────────────────────────────

    def test_rapport_contient_cles_attendues(self):
        rapport = self._rapport([])
        for cle in ("total", "updated", "skipped", "stats"):
            assert cle in rapport, f"Clé manquante dans le rapport : {cle}"

    def test_rapport_liste_vide(self):
        rapport = self._rapport([])
        assert rapport["total"]   == 0
        assert rapport["updated"] == 0
        assert rapport["skipped"] == 0

    # ── Compteurs ────────────────────────────────────────────────────────────

    def test_total_et_updated(self):
        recettes = [
            _recipe(1, ingredients=["lentil"]),
            _recipe(2, ingredients=["carrot"]),
        ]
        rapport = self._rapport(recettes)
        assert rapport["total"]   == 2
        assert rapport["updated"] == 2
        assert rapport["skipped"] == 0

    def test_recette_manuelle_comptee_dans_skipped(self):
        manual = _recipe(1, ingredients=["chicken"],
                         diet_flags={"vegan": True, "diet_flags_source": "manual"})
        manual["diet_flags_source"] = "manual"
        normale = _recipe(2, ingredients=["lentil"])
        rapport = self._rapport([manual, normale])
        assert rapport["skipped"] == 1
        assert rapport["updated"] == 1

    def test_force_traite_les_recettes_manuelles(self):
        manual = _recipe(1, ingredients=["chicken"],
                         diet_flags={"vegan": True, "diet_flags_source": "manual"})
        manual["diet_flags_source"] = "manual"
        rapport = self._rapport([manual], force=True)
        assert rapport["skipped"] == 0
        assert rapport["updated"] == 1

    # ── Stats des flags ──────────────────────────────────────────────────────

    def test_stats_vegan_correctes(self):
        recettes = [
            _recipe(1, ingredients=["lentil"]),   # vegan=True
            _recipe(2, ingredients=["egg"]),       # vegan=False
            _recipe(3, ingredients=["tofu"]),      # vegan=True
        ]
        rapport = self._rapport(recettes)
        assert rapport["stats"]["vegan"] == 2

    def test_stats_gluten_free_correctes(self):
        recettes = [
            _recipe(1, ingredients=["rice"]),      # gluten_free=True
            _recipe(2, ingredients=["pasta"]),     # gluten_free=False
        ]
        rapport = self._rapport(recettes)
        assert rapport["stats"]["gluten_free"] == 1

    # ── Modification en place ────────────────────────────────────────────────

    def test_recettes_modifiees_en_place(self):
        r = _recipe(1, ingredients=["lentil"])
        self._rapport([r])
        assert "diet_flags" in r
        assert r["diet_flags"]["vegan"] is True

    def test_force_recalcule_flags_manuels(self):
        """force=True → les recettes manuelles sont recalculées."""
        r = _recipe(1, ingredients=["chicken"],
                    diet_flags={"vegan": True, "diet_flags_source": "manual"})
        r["diet_flags_source"] = "manual"
        self._rapport([r], force=True)
        assert r["diet_flags"]["vegetarian"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# TestAudit
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudit:

    def setup_method(self):
        from backend.engine.rule_engine.diet import audit
        self.audit = audit

    def test_retourne_liste(self):
        assert isinstance(self.audit([]), list)

    def test_pas_de_divergence_si_flags_corrects(self):
        """Recette dont les diet_flags stockés correspondent au calcul → 0 divergences."""
        from backend.engine.rule_engine.diet import compute_diet_flags
        r = _recipe(1, ingredients=["lentil", "carrot"])
        r["diet_flags"] = compute_diet_flags(r)
        assert self.audit([r]) == []

    def test_detecte_divergence_vegan(self):
        """diet_flags stocké vegan=True mais chicken présent → divergence."""
        r = _recipe(2, ingredients=["chicken"])
        r["diet_flags"] = {"vegan": True, "vegetarian": True,
                            "gluten_free": True, "lactose_free": True,
                            "nut_free": True, "raw": False, "kid_friendly": False}
        divergences = self.audit([r])
        assert len(divergences) == 1
        assert "vegan" in divergences[0]["diff"]
        assert divergences[0]["diff"]["vegan"]["stored"]   is True
        assert divergences[0]["diff"]["vegan"]["computed"] is False

    def test_divergence_contient_id_et_diff(self):
        from backend.engine.rule_engine.diet import compute_diet_flags
        r = _recipe(42, ingredients=["pasta"])
        stored = compute_diet_flags(r)
        stored["gluten_free"] = True   # divergence forcée
        r["diet_flags"] = stored
        divs = self.audit([r])
        assert divs[0]["id"] == 42
        assert "gluten_free" in divs[0]["diff"]

    def test_recette_sans_diet_flags_stockes(self):
        """Recette sans diet_flags stocké → divergence sur chaque flag calculé."""
        r = _recipe(3, ingredients=["lentil"])
        divs = self.audit([r])
        # Tous les flags calculés diffèrent de None
        assert len(divs) == 1

    def test_plusieurs_recettes_mixtes(self):
        from backend.engine.rule_engine.diet import compute_diet_flags
        r_ok  = _recipe(10, ingredients=["tofu"])
        r_ok["diet_flags"] = compute_diet_flags(r_ok)

        r_bad = _recipe(11, ingredients=["salmon"])
        r_bad["diet_flags"] = {"vegan": True, "vegetarian": True,
                                "gluten_free": True, "lactose_free": True,
                                "nut_free": True, "raw": False, "kid_friendly": False}
        divs = self.audit([r_ok, r_bad])
        assert len(divs) == 1
        assert divs[0]["id"] == 11
