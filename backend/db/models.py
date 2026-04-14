"""
models.py — Modèles SQLAlchemy pour ALIM_PROJECT_UNIFIED.

Tables migrées depuis JSON :
  - users           : comptes B2C (JWT Bearer)
  - user_profiles   : préférences utilisateurs (diet, allergies, budget…)
  - api_users       : comptes B2B (API key)
  - api_keys        : clés SHA-256 avec plans free/starter/pro
  - daily_quotas    : compteurs journaliers par clé

Données statiques (dataset culinaire) → restent en JSON + lru_cache.
"""
from datetime import datetime, date, timezone
from typing   import Optional

from sqlalchemy import (
    Column, String, Integer, Boolean, Date, DateTime,
    ForeignKey, JSON, UniqueConstraint, Index, text,
)
from backend.core.encryption import EncryptedString
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Comptes B2C (JWT Bearer) ──────────────────────────────────────────────────

class User(Base):
    """Compte utilisateur B2C — authentification JWT Bearer."""
    __tablename__ = "users"

    email         = Column(String(254), primary_key=True, index=True)
    password_hash = Column(String(255), nullable=False)
    plan          = Column(String(20),  nullable=False, default="free",
                          server_default="free")
    is_active     = Column(Boolean,     nullable=False, default=True,
                          server_default=text("true"))
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    # Relation
    profile = relationship("UserProfile", back_populates="user",
                           uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User email={self.email} plan={self.plan}>"


class UserProfile(Base):
    """Préférences culinaires d'un utilisateur B2C."""
    __tablename__ = "user_profiles"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_email    = Column(String(254),
                           ForeignKey("users.email", ondelete="CASCADE"),
                           nullable=False, unique=True, index=True)
    # Régime alimentaire
    diet          = Column(String(30),  nullable=True)   # vegan, vegetarien…
    # Données structurées stockées en JSON (liste d'allergènes, préférences…)
    allergies     = Column(JSON, nullable=True, default=list)
    liked_ingredients   = Column(JSON, nullable=True, default=list)
    disliked_ingredients= Column(JSON, nullable=True, default=list)
    # Budget et convives
    budget        = Column(String(20),  nullable=True)   # économique/standard/confort
    servings      = Column(Integer,     nullable=True)
    # Santé — chiffrées (RGPD Art. 9 — données de catégorie spéciale)
    cycle_phase   = Column(EncryptedString(120), nullable=True)
    health_goal   = Column(EncryptedString(120), nullable=True)
    # Timestamps
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="profile")

    def to_dict(self) -> dict:
        """Retourne le profil sous forme de dict (compatible avec l'ancien format JSON)."""
        d = {}
        for field in ("diet", "allergies", "liked_ingredients",
                      "disliked_ingredients", "budget", "servings",
                      "cycle_phase", "health_goal"):
            val = getattr(self, field)
            if val is not None:
                d[field] = val
        return d

    def __repr__(self):
        return f"<UserProfile user={self.user_email} diet={self.diet}>"


# ── Comptes B2B (API key) ─────────────────────────────────────────────────────

class ApiUser(Base):
    """Compte utilisateur B2B — authentification par clé API."""
    __tablename__ = "api_users"

    user_id    = Column(String(36),  primary_key=True)  # UUID
    email      = Column(String(254), nullable=False, unique=True, index=True)
    plan       = Column(String(20),  nullable=False, default="free")
    is_active  = Column(Boolean,     nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc))

    api_keys = relationship("ApiKey", back_populates="api_user",
                            cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ApiUser {self.email} plan={self.plan}>"


class ApiKey(Base):
    """Clé API SHA-256 liée à un compte B2B."""
    __tablename__ = "api_keys"

    key_hash   = Column(String(64),  primary_key=True)   # SHA-256 hex (64 chars)
    user_id    = Column(String(36),
                       ForeignKey("api_users.user_id", ondelete="CASCADE"),
                       nullable=False, index=True)
    is_active  = Column(Boolean,     nullable=False, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                       default=lambda: datetime.now(timezone.utc))

    api_user = relationship("ApiUser", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey hash={self.key_hash[:8]}… user={self.user_id}>"


class DailyQuota(Base):
    """Compteur de requêtes journalier par clé API."""
    __tablename__ = "daily_quotas"

    key_hash   = Column(String(64), ForeignKey("api_keys.key_hash",
                                                ondelete="CASCADE"),
                       nullable=False, primary_key=True)
    quota_date = Column(Date, nullable=False, default=date.today,
                       primary_key=True)
    count      = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("key_hash", "quota_date", name="uq_quota_key_date"),
        Index("ix_quota_date", "quota_date"),  # pour le nettoyage des vieux enregistrements
    )

    def __repr__(self):
        return f"<DailyQuota key={self.key_hash[:8]}… date={self.quota_date} count={self.count}>"

# ── Historique des recettes consultées (base du learning_engine) ──────────────

class RecipeHistory(Base):
    """
    Enregistre chaque interaction utilisateur avec une recette.

    Sert de source de données pour le learning_engine (v2) :
      - 1 000 interactions minimum pour démarrer la personnalisation
      - Mémorise action, score affiché et profil actif au moment de l'interaction

    Rétention : 500 entrées max par utilisateur (nettoyage via purge_old_history).
    """
    __tablename__ = "recipe_history"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(254),
                        ForeignKey("users.email", ondelete="CASCADE"),
                        nullable=False, index=True)
    recipe_id  = Column(Integer, nullable=False, index=True)
    action     = Column(String(30), nullable=False, default="view")
    # Actions : view | like | dislike | plan | cook | skip
    score_shown   = Column(Integer, nullable=True)   # score affiché (0-100)
    profile_used  = Column(String(30), nullable=True) # profil adaptatif actif
    created_at    = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_history_user_date", "user_email", "created_at"),
    )

    def __repr__(self):
        return f"<RecipeHistory user={self.user_email} recipe={self.recipe_id} action={self.action}>"



# ── Tokens de réinitialisation de mot de passe ────────────────────────────────

class PasswordResetToken(Base):
    """
    Token de réinitialisation de mot de passe persisté en base.

    Remplace le dict en mémoire (_reset_tokens) dans auth.py.
    Compatible multi-worker (uvicorn --workers N) et multi-process.

    Cycle de vie :
      1. Créé par forgot_password → is_used=False
      2. Consommé par reset_password → supprimé immédiatement (usage unique)
      3. Nettoyage automatique des tokens expirés via purge_expired_tokens()

    TTL : 30 minutes (configurable via RESET_TOKEN_TTL_MINUTES).
    """
    __tablename__ = "password_reset_tokens"

    token_hash = Column(String(64),  primary_key=True)   # SHA-256 du token brut
    email      = Column(String(254), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_reset_email", "email"),
        Index("ix_reset_expires", "expires_at"),   # pour le nettoyage par batch
    )

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def __repr__(self):
        return f"<PasswordResetToken email={self.email} expires={self.expires_at}>"
