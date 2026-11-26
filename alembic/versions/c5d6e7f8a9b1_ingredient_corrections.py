"""ingredient_corrections : corrections des fiches ingrédients, source à l'appui

Revision ID: c5d6e7f8a9b1
Revises: b4c5d6e7f8a9
Create Date: 2026-11-26 22:00:00.000000

Idempotente : les bases créées par Base.metadata.create_all() ont déjà la table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b1'
down_revision: Union[str, Sequence[str], None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "ingredient_corrections" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "ingredient_corrections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ingredient_id", sa.String(120), nullable=False),
        sa.Column("ingredient_name", sa.String(200), nullable=False),
        sa.Column("field", sa.String(40), nullable=False),
        sa.Column("unit", sa.String(10), nullable=True),
        sa.Column("current_value", sa.JSON(), nullable=True),
        sa.Column("proposed_value", sa.JSON(), nullable=True),
        sa.Column("source_id", sa.String(40), nullable=True),
        sa.Column("source_ref", sa.String(300), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("user_email", sa.String(254),
                  sa.ForeignKey("users.email", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="submitted"),
        sa.Column("moderator_note", sa.Text(), nullable=True),
        sa.Column("moderator_email", sa.String(254), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ingredient_corrections_ingredient_id", "ingredient_corrections", ["ingredient_id"])
    op.create_index("ix_ingredient_corrections_user_email", "ingredient_corrections", ["user_email"])
    op.create_index("ix_ingredient_correction_status", "ingredient_corrections", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("ingredient_corrections")
