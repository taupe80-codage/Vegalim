"""notifications : nouveautés affichées dans l'application

Revision ID: a7b8c9d0e1f2
Revises: f2a3b4c5d6e7
Create Date: 2026-11-21 08:00:00.000000

Idempotente : les bases créées par Base.metadata.create_all() ont déjà la table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "notifications" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_email", sa.String(254),
                  sa.ForeignKey("users.email", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_user_email", "notifications", ["user_email"])
    op.create_index("ix_notification_user_read", "notifications", ["user_email", "read_at"])


def downgrade() -> None:
    op.drop_index("ix_notification_user_read", table_name="notifications")
    op.drop_index("ix_notifications_user_email", table_name="notifications")
    op.drop_table("notifications")
