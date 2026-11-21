"""avis (notes et commentaires), révisions des recettes publiées, préférence e-mail

Revision ID: e1f2a3b4c5d6
Revises: d7e8f9a0b1c2
Create Date: 2026-11-21 04:00:00.000000

- recipe_reviews, review_votes, review_reports : notes et commentaires sur
  toutes les recettes, votes « utile », signalements.
- recipe_submissions.revision_* : modification d'une recette déjà publiée,
  relue avant de remplacer la version en ligne.
- users.email_notifications : e-mails de suivi désactivables.
Idempotente : les bases créées par Base.metadata.create_all() ont déjà tout.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REVISION_COLS = ("revision_data", "revision_status", "revision_photo_token", "revision_submitted_at")


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())

    if "email_notifications" not in {c["name"] for c in insp.get_columns("users")}:
        op.add_column("users", sa.Column("email_notifications", sa.Boolean(), nullable=False,
                                         server_default=sa.text("true")))

    existing = {c["name"] for c in insp.get_columns("recipe_submissions")}
    with op.batch_alter_table("recipe_submissions") as batch:
        if "revision_data" not in existing:
            batch.add_column(sa.Column("revision_data", sa.JSON(), nullable=True))
        if "revision_status" not in existing:
            batch.add_column(sa.Column("revision_status", sa.String(20), nullable=True))
        if "revision_photo_token" not in existing:
            batch.add_column(sa.Column("revision_photo_token", sa.String(40), nullable=True))
        if "revision_submitted_at" not in existing:
            batch.add_column(sa.Column("revision_submitted_at", sa.DateTime(timezone=True), nullable=True))

    if "recipe_reviews" not in tables:
        op.create_table(
            "recipe_reviews",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("recipe_id", sa.String(100), nullable=False),
            sa.Column("user_email", sa.String(254),
                      sa.ForeignKey("users.email", ondelete="CASCADE"), nullable=False),
            sa.Column("author_name", sa.String(40), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("made_it", sa.Boolean(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("helpful_count", sa.Integer(), nullable=False),
            sa.Column("report_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("recipe_id", "user_email", name="uq_review_recipe_user"),
        )
        op.create_index("ix_recipe_reviews_recipe_id", "recipe_reviews", ["recipe_id"])
        op.create_index("ix_recipe_reviews_user_email", "recipe_reviews", ["user_email"])
        op.create_index("ix_review_recipe_status", "recipe_reviews", ["recipe_id", "status"])

    if "review_votes" not in tables:
        op.create_table(
            "review_votes",
            sa.Column("review_id", sa.Integer(),
                      sa.ForeignKey("recipe_reviews.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("user_email", sa.String(254),
                      sa.ForeignKey("users.email", ondelete="CASCADE"), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "review_reports" not in tables:
        op.create_table(
            "review_reports",
            sa.Column("review_id", sa.Integer(),
                      sa.ForeignKey("recipe_reviews.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("user_email", sa.String(254),
                      sa.ForeignKey("users.email", ondelete="CASCADE"), primary_key=True),
            sa.Column("reason", sa.String(30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("review_reports")
    op.drop_table("review_votes")
    op.drop_index("ix_review_recipe_status", table_name="recipe_reviews")
    op.drop_index("ix_recipe_reviews_user_email", table_name="recipe_reviews")
    op.drop_index("ix_recipe_reviews_recipe_id", table_name="recipe_reviews")
    op.drop_table("recipe_reviews")
    with op.batch_alter_table("recipe_submissions") as batch:
        for col in reversed(_REVISION_COLS):
            batch.drop_column(col)
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email_notifications")
