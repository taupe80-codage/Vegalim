"""photo_submissions : photos de plats proposées par les membres

Revision ID: a3b4c5d6e7f8
Revises: a7b8c9d0e1f2
Create Date: 2026-11-26 12:00:00.000000

Idempotente : les bases créées par Base.metadata.create_all() ont déjà la table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "photo_submissions" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "photo_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("recipe_id", sa.String(100), nullable=False),
        sa.Column("recipe_slug", sa.String(200), nullable=False),
        sa.Column("recipe_title", sa.String(200), nullable=False),
        # NULL après suppression du compte : la photo publiée reste, avec son pseudo
        sa.Column("user_email", sa.String(254),
                  sa.ForeignKey("users.email", ondelete="SET NULL"), nullable=True),
        sa.Column("author_name", sa.String(40), nullable=False),
        sa.Column("photo_token", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="submitted"),
        sa.Column("moderator_note", sa.Text(), nullable=True),
        sa.Column("moderator_email", sa.String(254), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_photo_submissions_recipe_id", "photo_submissions", ["recipe_id"])
    op.create_index("ix_photo_submissions_user_email", "photo_submissions", ["user_email"])
    op.create_index("ix_photo_submission_status", "photo_submissions", ["status", "created_at"])


def downgrade() -> None:
    op.drop_table("photo_submissions")
