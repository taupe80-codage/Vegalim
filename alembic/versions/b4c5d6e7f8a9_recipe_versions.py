"""recipe_versions : recettes modifiées et enregistrées par un membre

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-11-26 18:00:00.000000

Idempotente : les bases créées par Base.metadata.create_all() ont déjà la table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "recipe_versions" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "recipe_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_email", sa.String(254),
                  sa.ForeignKey("users.email", ondelete="CASCADE"), nullable=False),
        sa.Column("recipe_id", sa.String(100), nullable=False),
        sa.Column("base", sa.String(10), nullable=False, server_default="original"),
        sa.Column("rows", sa.JSON(), nullable=False),
        sa.Column("servings", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_email", "recipe_id", name="uq_recipe_version_user_recipe"),
    )
    op.create_index("ix_recipe_versions_user_email", "recipe_versions", ["user_email"])


def downgrade() -> None:
    op.drop_index("ix_recipe_versions_user_email", table_name="recipe_versions")
    op.drop_table("recipe_versions")
