"""recipe_reviews.author_reply : réponse de l'auteur d'une recette à un avis

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-11-21 06:00:00.000000

Idempotente : les bases créées par Base.metadata.create_all() ont déjà les colonnes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("recipe_reviews")}
    with op.batch_alter_table("recipe_reviews") as batch:
        if "author_reply" not in existing:
            batch.add_column(sa.Column("author_reply", sa.Text(), nullable=True))
        if "author_reply_at" not in existing:
            batch.add_column(sa.Column("author_reply_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("recipe_reviews") as batch:
        batch.drop_column("author_reply_at")
        batch.drop_column("author_reply")
