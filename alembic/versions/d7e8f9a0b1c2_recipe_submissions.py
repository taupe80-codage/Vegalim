"""recipe_submissions : recettes proposées par les utilisateurs

Revision ID: d7e8f9a0b1c2
Revises: c5d6e7f8a9b0
Create Date: 2026-11-21 02:00:00.000000

Table des propositions de recettes (brouillon → relecture → publication).
Idempotente : les bases créées par Base.metadata.create_all() l'ont déjà.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, Sequence[str], None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "recipe_submissions" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "recipe_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_email", sa.String(254),
                  sa.ForeignKey("users.email", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("author_name", sa.String(40), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("photo_token", sa.String(40), nullable=True),
        sa.Column("moderator_note", sa.Text(), nullable=True),
        sa.Column("moderator_email", sa.String(254), nullable=True),
        sa.Column("published_recipe_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_recipe_submissions_user_email", "recipe_submissions", ["user_email"])
    op.create_index("ix_recipe_submissions_published_recipe_id", "recipe_submissions",
                    ["published_recipe_id"])
    op.create_index("ix_submission_status", "recipe_submissions", ["status", "submitted_at"])


def downgrade() -> None:
    op.drop_index("ix_submission_status", table_name="recipe_submissions")
    op.drop_index("ix_recipe_submissions_published_recipe_id", table_name="recipe_submissions")
    op.drop_index("ix_recipe_submissions_user_email", table_name="recipe_submissions")
    op.drop_table("recipe_submissions")
