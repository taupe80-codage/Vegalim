"""initial_schema

Revision ID: 8cbe20c5762a
Revises:
Create Date: 2026-05-20 03:54:01.194383

Schéma initial. La version d'origine était vide (`pass`) : sur une base neuve,
`alembic upgrade head` échouait à la révision suivante (ALTER TABLE
user_profiles inexistante) et l'API se rabattait sur Base.metadata.create_all()
en laissant alembic_version bloquée (constaté le 2026-09-14).

Les tables sont créées uniquement si elles n'existent pas : les bases déjà
initialisées par create_all() restent compatibles.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cbe20c5762a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    """Crée les tables du schéma initial absentes."""
    existing = _existing_tables()

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("email", sa.String(254), primary_key=True),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_users_email", "users", ["email"])

    if "user_profiles" not in existing:
        op.create_table(
            "user_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_email", sa.String(254),
                      sa.ForeignKey("users.email", ondelete="CASCADE"), nullable=False),
            sa.Column("diet", sa.String(30), nullable=True),
            sa.Column("allergies", sa.JSON(), nullable=True),
            sa.Column("liked_ingredients", sa.JSON(), nullable=True),
            sa.Column("disliked_ingredients", sa.JSON(), nullable=True),
            sa.Column("budget", sa.String(20), nullable=True),
            sa.Column("servings", sa.Integer(), nullable=True),
            sa.Column("cycle_phase", sa.String(120), nullable=True),
            sa.Column("health_goal", sa.String(120), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_user_profiles_user_email", "user_profiles", ["user_email"], unique=True)

    if "api_users" not in existing:
        op.create_table(
            "api_users",
            sa.Column("user_id", sa.String(36), primary_key=True),
            sa.Column("email", sa.String(254), nullable=False),
            sa.Column("plan", sa.String(20), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_api_users_email", "api_users", ["email"], unique=True)

    if "api_keys" not in existing:
        op.create_table(
            "api_keys",
            sa.Column("key_hash", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(36),
                      sa.ForeignKey("api_users.user_id", ondelete="CASCADE"), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    if "daily_quotas" not in existing:
        op.create_table(
            "daily_quotas",
            sa.Column("key_hash", sa.String(64),
                      sa.ForeignKey("api_keys.key_hash", ondelete="CASCADE"), primary_key=True),
            sa.Column("quota_date", sa.Date(), primary_key=True),
            sa.Column("count", sa.Integer(), nullable=False),
            sa.UniqueConstraint("key_hash", "quota_date", name="uq_quota_key_date"),
        )
        op.create_index("ix_quota_date", "daily_quotas", ["quota_date"])

    if "recipe_history" not in existing:
        op.create_table(
            "recipe_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_email", sa.String(254),
                      sa.ForeignKey("users.email", ondelete="CASCADE"), nullable=False),
            sa.Column("recipe_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(30), nullable=False),
            sa.Column("score_shown", sa.Integer(), nullable=True),
            sa.Column("profile_used", sa.String(30), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_recipe_history_user_email", "recipe_history", ["user_email"])
        op.create_index("ix_recipe_history_recipe_id", "recipe_history", ["recipe_id"])
        op.create_index("ix_history_user_date", "recipe_history", ["user_email", "created_at"])

    if "password_reset_tokens" not in existing:
        op.create_table(
            "password_reset_tokens",
            sa.Column("token_hash", sa.String(64), primary_key=True),
            sa.Column("email", sa.String(254), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_password_reset_tokens_email", "password_reset_tokens", ["email"])
        op.create_index("ix_reset_email", "password_reset_tokens", ["email"])
        op.create_index("ix_reset_expires", "password_reset_tokens", ["expires_at"])


def downgrade() -> None:
    """Supprime les tables du schéma initial."""
    for table in ("password_reset_tokens", "recipe_history", "daily_quotas",
                  "api_keys", "api_users", "user_profiles", "users"):
        op.drop_table(table)
