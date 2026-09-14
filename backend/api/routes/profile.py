import logging
logger = logging.getLogger(__name__)

"""Routes profil utilisateur — repris de clean_pro."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from backend.core.auth_deps     import get_user
from backend.services.profile_service import set_profile, get_profile, delete_profile

router = APIRouter(prefix="/profil", tags=["Profil"])
# Import depuis validators (source unique — évite la duplication avec ALLOWED_DIETS)
from backend.core.validators import ALLOWED_DIETS as DIETS_VALIDES, normalize_diet

class ProfileUpdate(BaseModel):
    diet: str | None = None
    goal: str | None = None
    allergies: list[str] | None = None

@router.get("/")
def read_profile(user: dict = Depends(get_user)):
    """Retourne le profil de l'utilisateur connecté."""
    return get_profile(user["email"])

@router.post("/update")
def update_profile(update: ProfileUpdate, user: dict = Depends(get_user)):
    """Met à jour le profil (régime, allergies, objectifs santé)."""
    if update.diet and update.diet.lower() not in DIETS_VALIDES:
        raise HTTPException(status_code=400,
            detail=f"Régime invalide. Valeurs : {sorted(DIETS_VALIDES)}")
    data = update.model_dump(exclude_none=True)
    if update.diet:
        # Normaliser vers la clé canonique (ex: "sans_gluten" → "gluten_free")
        # pour que le profil stocke toujours la forme canonique.
        data["diet"] = normalize_diet(update.diet)
    # Sanitiser les champs texte libres
    from backend.core.validators import sanitize_text
    # Note : 'goal' est l'alias de 'health_goal' dans ProfileUpdate — les deux sont sanitisés
    for field in ("cycle_phase", "health_goal", "goal"):
        if field in data and data[field]:
            try:
                data[field] = sanitize_text(data[field], max_length=120)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
    # RGPD Art. 9 — données de santé nécessitent un consentement explicite
    profile_current = get_profile(user["email"])
    # 'goal' est l'alias de 'health_goal' envoyé par ProfileUpdate — inclus dans le guard
    health_fields   = {"cycle_phase", "health_goal", "goal"}
    if data.keys() & health_fields and not profile_current.get("health_consent"):
        raise HTTPException(
            status_code=403,
            detail="Consentement santé requis. Appelez PATCH /profil/consent d'abord."
        )
    updated = set_profile(user["email"], data)
    return {"message": "Profil mis à jour", "profile": updated}

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile_route(user: dict = Depends(get_user)):
    """Supprime le profil utilisateur. Retourne 204."""
    delete_profile(user["email"])


# ── Routes learning ───────────────────────────────────────────────────────────

class InteractionPayload(BaseModel):
    recipe_id:    int
    action:       str = "view"   # view | like | dislike | plan | cook | skip
    score_shown:  float | None = None
    profile_used: str   | None = None


@router.post("/interaction", status_code=status.HTTP_204_NO_CONTENT)
def record_interaction(payload: InteractionPayload,
                       user: dict = Depends(get_user)):
    """
    Enregistre une interaction utilisateur avec une recette.
    Alimente le moteur de personnalisation pour les recommandations futures.

    Actions valides : view | like | dislike | plan | cook | skip
    """
    VALID_ACTIONS = {"view", "like", "dislike", "plan", "cook", "skip"}
    if payload.action not in VALID_ACTIONS:
        raise HTTPException(status_code=400,
            detail=f"Action invalide. Valeurs : {sorted(VALID_ACTIONS)}")

    try:
        from backend.services.interaction_service import save_interaction
    except ImportError:
        logger.warning("record_interaction: interaction_service indisponible — interaction non enregistrée")
        return
    save_interaction(
        email        = user["email"],
        recipe_id    = payload.recipe_id,
        action       = payload.action,
        score_shown  = payload.score_shown,
        profile_used = payload.profile_used,
    )


@router.get("/learning")
def get_learning_stats(user: dict = Depends(get_user)):
    """
    Retourne les statistiques de personnalisation de l'utilisateur.

    Inclut le nombre de likes/dislikes, les préférences déduites
    et si la personnalisation est active.
    """
    try:
        from backend.services.interaction_service import get_user_stats
    except ImportError:
        raise HTTPException(status_code=503, detail="Service de personnalisation indisponible")
    return get_user_stats(user["email"])

class ConsentUpdate(BaseModel):
    health_consent: bool = Field(
        ...,
        description="Consentement explicite pour stocker données de santé (cycle, objectif)"
    )


@router.patch("/consent", status_code=200)
def update_consent(payload: ConsentUpdate, user: dict = Depends(get_user)):
    """
    Active ou révoque le consentement pour le traitement des données de santé.

    Conformément au RGPD Article 9, les données relatives à la santé (cycle_phase,
    health_goal) ne peuvent être stockées qu'avec un consentement explicite.
    Si health_consent=False, ces champs sont effacés du profil.
    """
    email = user["email"]
    profile = get_profile(email)

    if not payload.health_consent:
        # Révoquer → effacer les données de santé
        profile.pop("cycle_phase", None)
        profile.pop("health_goal", None)
        profile["health_consent"] = False
    else:
        profile["health_consent"] = True

    updated = set_profile(email, profile)
    return {
        "health_consent": updated.get("health_consent", False),
        "message": (
            "Consentement santé accordé — données de santé activées."
            if payload.health_consent else
            "Consentement santé révoqué — données de santé effacées."
        ),
    }

@router.get("/export")
def export_profile(user: dict = Depends(get_user)):
    """
    Export complet des données personnelles (RGPD Art. 15 — droit d'accès).

    Retourne en JSON toutes les données associées au compte :
    profil, historique d'interactions, préférences apprises.
    """
    email   = user["email"]
    profile = get_profile(email)

    # Historique des interactions
    history_data = {}
    try:
        from backend.services.interaction_service import load_history, get_user_stats
        history = load_history(email)
        stats   = get_user_stats(email)
        history_data = {
            "liked_count":    len(history.get("liked", set())),
            "disliked_count": len(history.get("disliked", set())),
            "viewed_count":   len(history.get("viewed", set())),
            "personalization_active": stats.get("personalization_active", False),
        }
    except Exception:
        logger.warning("export_profile : erreur ignorée (repli)", exc_info=True)

    import datetime
    return {
        "export_date":  datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "email":        email,
        "profile":      profile,
        "interactions": history_data,
        "rights": {
            "rectification": "POST /profil/update",
            "erasure":       "DELETE /profil/ ou DELETE /auth/account",
            "portability":   "Ce fichier JSON constitue l'export de portabilité",
            "contact":       "privacy@alim-platform.com",
        },
    }

@router.get("/export/csv")
def export_profile_csv(user: dict = Depends(get_user)):
    """
    Export CSV des données personnelles (RGPD Art. 20 — portabilité).

    Retourne un fichier CSV téléchargeable avec le profil et l'historique.
    Complément de GET /profil/export (JSON).
    """
    import csv, io, datetime
    email   = user["email"]
    profile = get_profile(email)

    history_data = {}
    try:
        from backend.services.interaction_service import load_history
        history      = load_history(email)
        history_data = {
            "liked_count":    len(history.get("liked", set())),
            "disliked_count": len(history.get("disliked", set())),
            "viewed_count":   len(history.get("viewed", set())),
        }
    except Exception:
        logger.warning("export_profile_csv : erreur ignorée (repli)", exc_info=True)

    # Construire le CSV
    output  = io.StringIO()
    writer  = csv.writer(output)

    writer.writerow(["# Export ALIM — Données personnelles"])
    writer.writerow(["# Date", datetime.datetime.now(datetime.timezone.utc).isoformat()])
    writer.writerow(["# Email", email])
    writer.writerow([])

    writer.writerow(["=== PROFIL ==="])
    writer.writerow(["Champ", "Valeur"])
    for k, v in profile.items():
        writer.writerow([k, v])
    writer.writerow([])

    writer.writerow(["=== STATISTIQUES ==="])
    writer.writerow(["Métrique", "Valeur"])
    for k, v in history_data.items():
        writer.writerow([k, v])
    writer.writerow([])

    writer.writerow(["=== DROITS RGPD ==="])
    writer.writerow(["Rectification", "POST /profil/update"])
    writer.writerow(["Effacement",    "DELETE /profil/ ou DELETE /auth/account"])
    writer.writerow(["Contact",       "privacy@alim-platform.com"])

    csv_content = output.getvalue()

    from fastapi.responses import Response
    return Response(
        content    = csv_content,
        media_type = "text/csv",
        headers    = {
            "Content-Disposition": f'attachment; filename="alim_export_{email}.csv"',
            "X-Export-Format": "csv",
        }
    )
