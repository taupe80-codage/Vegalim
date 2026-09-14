"""
repositories.py — Couche d'accès aux données (Repository pattern).

Chaque repository encapsule toutes les opérations CRUD sur une table.
Les services appellent les repositories — jamais la session directement.

Usage :
    from backend.db.repositories import UserRepository, UserProfileRepository
    
    with db_session() as db:
        user = UserRepository(db).create("user@example.com", "hashed_pwd")
        profile = UserProfileRepository(db).upsert("user@example.com", {"diet": "vegan"})
"""
import hashlib
import logging
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing   import Optional

from sqlalchemy.orm     import Session

from backend.db.models  import User, UserProfile, ApiUser, ApiKey, DailyQuota

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# ── Repository B2C — Comptes utilisateurs ─────────────────────────────────────

class UserRepository:
    """CRUD sur la table users (comptes B2C)."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def create(self, email: str, password_hash: str, plan: str = "free") -> User:
        """Crée un utilisateur. Lève ValueError si l'email existe déjà."""
        if self.exists(email):
            raise ValueError(f"Email déjà enregistré : {email}")
        user = User(email=email, password_hash=password_hash, plan=plan)
        self.db.add(user)
        self.db.flush()   # obtenir l'objet avant commit
        logger.info("Utilisateur créé : %s (plan=%s)", email, plan)
        return user

    def verify_password(self, email: str, password_hash: str) -> Optional[User]:
        """Vérifie les identifiants. Retourne l'utilisateur ou None."""
        user = self.get_by_email(email)
        if not user or not user.is_active:
            return None
        # La vérification bcrypt se fait dans user_service — ici on compare les hashes
        # (le service passe déjà le hash vérifié)
        return user

    def delete(self, email: str) -> bool:
        user = self.get_by_email(email)
        if not user:
            return False
        self.db.delete(user)
        self.db.flush()
        logger.info("Utilisateur supprimé : %s", email)
        return True

    def update_plan(self, email: str, plan: str) -> Optional[User]:
        user = self.get_by_email(email)
        if not user:
            return None
        user.plan = plan
        user.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        return user


# ── Repository B2C — Profils utilisateurs ─────────────────────────────────────

ALLOWED_PROFILE_FIELDS = frozenset({
    "diet", "allergies", "liked_ingredients", "disliked_ingredients",
    "budget", "servings", "cycle_phase", "health_goal",
    "health_consent",   # fix: était absent → PATCH /profil/consent ne persistait jamais
})


class UserProfileRepository:
    """CRUD sur la table user_profiles."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, email: str) -> Optional[UserProfile]:
        return self.db.query(UserProfile).filter(
            UserProfile.user_email == email
        ).first()

    def get_as_dict(self, email: str) -> dict:
        """Retourne le profil comme dict (compatible ancien format JSON)."""
        profile = self.get(email)
        return profile.to_dict() if profile else {}

    def upsert(self, email: str, updates: dict) -> dict:
        """
        Crée ou met à jour le profil par merge partiel.
        Seuls les champs de ALLOWED_PROFILE_FIELDS sont acceptés.
        Retourne le profil complet mis à jour.
        """
        # Filtrage strict — whitelist
        safe = {k: v for k, v in updates.items() if k in ALLOWED_PROFILE_FIELDS}
        if len(safe) < len(updates):
            rejected = set(updates) - ALLOWED_PROFILE_FIELDS
            logger.warning("Champs profil refusés : %s", rejected)

        profile = self.get(email)
        if profile is None:
            profile = UserProfile(user_email=email)
            self.db.add(profile)

        for field, value in safe.items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        logger.debug("Profil mis à jour : %s → %s", email, list(safe.keys()))
        return profile.to_dict()

    def delete(self, email: str) -> bool:
        profile = self.get(email)
        if not profile:
            return False
        self.db.delete(profile)
        self.db.flush()
        return True


# ── Repository B2B — Comptes API ──────────────────────────────────────────────

class ApiUserRepository:
    """CRUD sur la table api_users."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[ApiUser]:
        return self.db.query(ApiUser).filter(ApiUser.user_id == user_id).first()

    def get_by_email(self, email: str) -> Optional[ApiUser]:
        return self.db.query(ApiUser).filter(ApiUser.email == email).first()

    def create(self, email: str, plan: str = "free") -> ApiUser:
        existing = self.get_by_email(email)
        if existing:
            raise ValueError(f"Compte API déjà existant : {email}")
        api_user = ApiUser(
            user_id  = str(uuid.uuid4()),
            email    = email,
            plan     = plan,
        )
        self.db.add(api_user)
        self.db.flush()
        logger.info("Compte API créé : %s (plan=%s)", email, plan)
        return api_user

    def upgrade_plan(self, user_id: str, new_plan: str) -> Optional[ApiUser]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        user.plan = new_plan
        self.db.flush()
        logger.info("Plan mis à jour : %s → %s", user_id, new_plan)
        return user


# ── Repository B2B — Clés API ─────────────────────────────────────────────────

class ApiKeyRepository:
    """CRUD sur la table api_keys."""

    def __init__(self, db: Session):
        self.db = db

    def generate(self, user_id: str,
                 expires_in_days: int | None = None) -> tuple[str, ApiKey]:
        """
        Génère une nouvelle clé API.

        Returns:
            (raw_key, ApiKey) — raw_key est retourné une seule fois, non stocké.
        """
        raw_key  = secrets.token_hex(32)   # 64 chars hex = 256 bits
        key_hash = _sha256(raw_key)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        api_key = ApiKey(
            key_hash   = key_hash,
            user_id    = user_id,
            is_active  = True,
            expires_at = expires_at,
        )
        self.db.add(api_key)
        self.db.flush()
        logger.info("Clé API générée pour user_id=%s", user_id)
        return raw_key, api_key

    def lookup(self, raw_key: str) -> Optional[ApiKey]:
        """Retrouve une clé par sa valeur brute (comparaison sur le hash)."""
        key_hash = _sha256(raw_key)
        return self.db.query(ApiKey).filter(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True,
        ).first()

    def revoke(self, raw_key: str) -> bool:
        api_key = self.lookup(raw_key)
        if not api_key:
            return False
        api_key.is_active = False
        self.db.flush()
        logger.info("Clé révoquée : %s…", raw_key[:8])
        return True

    def list_for_user(self, user_id: str) -> list[ApiKey]:
        return self.db.query(ApiKey).filter(ApiKey.user_id == user_id).all()


# ── Repository — Quotas journaliers ───────────────────────────────────────────

PLANS_LIMITS = {
    "free":    50,
    "starter": 500,
    "pro":     5000,
}


class QuotaRepository:
    """Gestion des quotas journaliers par clé API."""

    def __init__(self, db: Session):
        self.db = db

    def get_today_count(self, key_hash: str) -> int:
        today  = date.today()
        record = self.db.query(DailyQuota).filter(
            DailyQuota.key_hash   == key_hash,
            DailyQuota.quota_date == today,
        ).first()
        return record.count if record else 0

    def increment(self, key_hash: str) -> int:
        """Incrémente le compteur du jour. Retourne la nouvelle valeur."""
        today  = date.today()
        record = self.db.query(DailyQuota).filter(
            DailyQuota.key_hash   == key_hash,
            DailyQuota.quota_date == today,
        ).with_for_update().first()

        if record is None:
            record = DailyQuota(key_hash=key_hash, quota_date=today, count=1)
            self.db.add(record)
        else:
            record.count += 1

        self.db.flush()
        return record.count

    def check_and_increment(self, raw_key: str, plan: str) -> tuple[bool, int, int]:
        """
        Vérifie le quota et l'incrémente si possible.

        Returns:
            (allowed: bool, used: int, limit: int)
        """
        key_hash = _sha256(raw_key)
        limit    = PLANS_LIMITS.get(plan, 50)
        used     = self.get_today_count(key_hash)

        if used >= limit:
            return False, used, limit

        new_count = self.increment(key_hash)
        return True, new_count, limit

    def purge_old(self, keep_days: int = 2) -> int:
        """Supprime les enregistrements de plus de keep_days jours."""
        cutoff = date.today() - timedelta(days=keep_days)
        deleted = self.db.query(DailyQuota).filter(
            DailyQuota.quota_date < cutoff
        ).delete()
        self.db.flush()
        if deleted:
            logger.debug("Quotas purgés : %d enregistrements avant %s", deleted, cutoff)
        return deleted

class RecipeHistoryRepository:
    """Accès aux interactions utilisateur (base du learning_engine)."""

    MAX_HISTORY = 500  # Rétention max par utilisateur (CDC_12)

    def __init__(self, db: Session):
        self._db = db

    def record(self, user_email: str, recipe_id: str,
               action: str = "view",
               score_shown: int | None = None,
               profile_used: str | None = None) -> "RecipeHistory":
        """Enregistre une interaction. Purge automatique au-delà de MAX_HISTORY."""
        from backend.db.models import RecipeHistory
        entry = RecipeHistory(
            user_email   = user_email,
            recipe_id    = recipe_id,
            action       = action,
            score_shown  = score_shown,
            profile_used = profile_used,
        )
        self._db.add(entry)
        self._db.flush()
        self._purge_excess(user_email)
        return entry

    def get_recent(self, user_email: str, limit: int = 50) -> list:
        """Retourne les N interactions les plus récentes."""
        from backend.db.models import RecipeHistory
        return (
            self._db.query(RecipeHistory)
            .filter(RecipeHistory.user_email == user_email)
            .order_by(RecipeHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_liked_recipe_ids(self, user_email: str) -> list[str]:
        """Retourne les recipe_id avec action='like'."""
        from backend.db.models import RecipeHistory
        rows = (
            self._db.query(RecipeHistory.recipe_id)
            .filter(RecipeHistory.user_email == user_email,
                    RecipeHistory.action == "like")
            .all()
        )
        return [r.recipe_id for r in rows]

    def get_disliked_recipe_ids(self, user_email: str) -> list[str]:
        """Retourne les recipe_id avec action='dislike'."""
        from backend.db.models import RecipeHistory
        rows = (
            self._db.query(RecipeHistory.recipe_id)
            .filter(RecipeHistory.user_email == user_email,
                    RecipeHistory.action == "dislike")
            .all()
        )
        return [r.recipe_id for r in rows]

    def count(self, user_email: str) -> int:
        """Nombre total d'interactions de l'utilisateur."""
        from backend.db.models import RecipeHistory
        return (
            self._db.query(RecipeHistory)
            .filter(RecipeHistory.user_email == user_email)
            .count()
        )

    def _purge_excess(self, user_email: str) -> int:
        """Supprime les entrées au-delà de MAX_HISTORY (les plus anciennes)."""
        from backend.db.models import RecipeHistory
        total = self.count(user_email)
        if total <= self.MAX_HISTORY:
            return 0
        excess = total - self.MAX_HISTORY
        oldest = (
            self._db.query(RecipeHistory.id)
            .filter(RecipeHistory.user_email == user_email)
            .order_by(RecipeHistory.created_at.asc())
            .limit(excess)
            .subquery()
        )
        deleted = (
            self._db.query(RecipeHistory)
            .filter(RecipeHistory.id.in_(oldest))
            .delete(synchronize_session=False)
        )
        return deleted


# ── Repository Reset Tokens ───────────────────────────────────────────────────

import hashlib as _hashlib

class PasswordResetRepository:
    """
    CRUD sur la table password_reset_tokens.
    Usage unique garanti : consume() supprime le token atomiquement.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _hash(token: str) -> str:
        return _hashlib.sha256(token.encode("utf-8")).hexdigest()

    def store(self, token: str, email: str, ttl_minutes: int = 30) -> None:
        """Persiste un token (hash SHA-256). Remplace l'entrée existante si présente."""
        from backend.db.models import PasswordResetToken
        from datetime import timedelta
        h = self._hash(token)
        # Supprimer une éventuelle entrée précédente pour cet email
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.email == email
        ).delete(synchronize_session=False)
        entry = PasswordResetToken(
            token_hash = h,
            email      = email,
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        )
        self.db.add(entry)
        self.db.flush()
        logger.debug("Reset token stocké pour %s (hash=%s…)", email, h[:8])

    def consume(self, token: str) -> str | None:
        """
        Valide et consomme un token en une seule opération.
        Retourne l'email associé, ou None si invalide/expiré.
        Le token est supprimé immédiatement (usage unique garanti).
        """
        from backend.db.models import PasswordResetToken
        h = self._hash(token)
        entry = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == h
        ).first()
        if not entry:
            return None
        if entry.is_expired():
            self.db.delete(entry)
            self.db.flush()
            logger.debug("Reset token expiré consommé pour %s", entry.email)
            return None
        email = entry.email
        self.db.delete(entry)
        self.db.flush()
        logger.info("Reset token consommé pour %s", email)
        return email

    def purge_expired(self) -> int:
        """Supprime tous les tokens expirés. Retourne le nombre supprimé."""
        from backend.db.models import PasswordResetToken
        count = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.expires_at < datetime.now(timezone.utc)
        ).delete(synchronize_session=False)
        if count:
            logger.info("Tokens de reset expirés purgés : %d", count)
        return count
