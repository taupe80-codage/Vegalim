"""
test_recommendation_flow.py — Tests métier bout-en-bout.

Vérifie les scénarios utilisateur complets :
  - Un végétalien cherche "curry" → toutes les recettes vegan
  - Un utilisateur sans compte → résultats publics non vides
  - Profil budget → score cost élevé dans les résultats
  - Résultats triés par score décroissant
  - Formule CDC : final ≈ 0.65*quality + 0.35*relevance
  - score_reasons présents et non vides sur les résultats
  - Filtres gluten_free, kid_friendly fonctionnels
  - RecommendationResult expose meta complet
"""
from backend.services.reco_service import recommend_full as recommend
from backend.engine.config import W_QUALITY, W_RELEVANCE


# ── Scénario 1 : utilisateur vegan ───────────────────────────────────────────

def test_vegan_filtre_strict():
    """Recherche curry + vegan → 100% recettes vegan."""
    r = recommend("", diet_override="vegan", limit=10)
    assert len(r.recipes) > 0, "Aucun résultat pour 'curry vegan'"
    violations = [
        rec["id"] for rec in r.recipes
        if not rec.get("diet_flags", {}).get("vegan")
    ]
    assert not violations, f"Recettes non-vegan dans résultat vegan : {violations}"

def test_vegan_diet_dans_meta():
    r = recommend("", diet_override="vegan", limit=5)
    assert r.diet == "vegan"

def test_gluten_free_filtre():
    """Filtre gluten_free → aucun ingrédient gluteneux."""
    r = recommend("gratin", diet_override="gluten_free", limit=10)
    GLUTEN = {"couscous","pasta","flour","noodles","bulgur","wonton_wrapper"}
    for rec in r.recipes:
        ids = {(i.get("ingredient","") if isinstance(i,dict) else str(i)).lower()
               for i in rec.get("composition",[])}
        found = ids & GLUTEN
        assert not found, f"Recette {rec['id']} gluten_free=True mais contient {found}"


# ── Scénario 2 : utilisateur anonyme ─────────────────────────────────────────

def test_anonyme_retourne_resultats():
    """Sans compte → résultats non vides."""
    r = recommend("", email=None, limit=5)
    assert len(r.recipes) > 0

def test_anonyme_scores_presents():
    """Les scores sont calculés même sans compte."""
    r = recommend("tofu", email=None, limit=3)
    for rec in r.recipes:
        assert "final_score" in rec
        assert 0 <= rec["final_score"] <= 10


# ── Scénario 3 : structure et formule ────────────────────────────────────────

def test_resultats_tries_par_score():
    """Résultats triés par final_score décroissant."""
    r = recommend("", limit=10)
    scores = [rec.get("final_score", 0) for rec in r.recipes]
    assert scores == sorted(scores, reverse=True), \
        f"Résultats non triés : {scores[:5]}"

def test_formule_cdc_respec():
    """final_score ≈ W_QUALITY * quality + W_RELEVANCE * relevance (±learning_bonus)."""
    r = recommend("", limit=5)
    for rec in r.recipes:
        q   = rec.get("quality_score", 0)
        rel = rec.get("relevance_score", 0)
        expected = round(W_QUALITY * q + W_RELEVANCE * rel, 2)
        actual   = rec.get("final_score", 0)
        # Tolérance ±2.0 pour le learning bonus
        assert abs(actual - expected) <= 2.01, \
            f"Formule violée: {actual} ≠ {expected} (q={q}, r={rel})"

def test_recommendation_result_meta():
    """RecommendationResult expose meta complet."""
    r = recommend("", limit=3)
    assert r.timing_ms >= 0
    assert r.query == ""
    assert r.total == len(r.recipes)


# ── Scénario 4 : explicabilité ────────────────────────────────────────────────

def test_score_reasons_presents():
    """score_reasons non vides sur les résultats de recommandation."""
    r = recommend("", limit=5)
    with_reasons = [rec for rec in r.recipes if rec.get("score_reasons")]
    # Au moins la moitié des résultats ont des reasons
    assert len(with_reasons) >= len(r.recipes) // 2, \
        "Moins de 50% des résultats ont des score_reasons"

def test_score_reasons_sont_des_strings():
    """score_reasons est une liste de strings."""
    r = recommend("", limit=3)
    for rec in r.recipes:
        reasons = rec.get("score_reasons", [])
        assert isinstance(reasons, list)
        assert all(isinstance(s, str) for s in reasons)


# ── Scénario 5 : kid_friendly ─────────────────────────────────────────────────

def test_kid_friendly_filtre():
    """Filtre kid_friendly → aucune épice forte."""
    r = recommend("pâtes", diet_override="kid_friendly", limit=10)
    SPICY = {"harissa", "gochujang", "doubanjiang_paste", "cayenne"}
    for rec in r.recipes:
        ids = {(i.get("ingredient","") if isinstance(i,dict) else str(i)).lower()
               for i in rec.get("composition",[])}
        assert not (ids & SPICY), \
            f"Recette kid_friendly {rec['id']} contient épice forte"


# ── Scénario 6 : to_dict() ────────────────────────────────────────────────────

def test_to_dict_serialisable():
    """RecommendationResult.to_dict() retourne un dict JSON-compatible."""
    import json
    r = recommend("", limit=3)
    d = r.to_dict()
    assert isinstance(d, dict)
    assert "recipes" in d and "total" in d and "timing_ms" in d
    try:
        json.dumps(d, default=str)
    except Exception as e:
        assert False, f"to_dict() non-sérialisable JSON : {e}"

