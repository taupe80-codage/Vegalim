"""add_health_consent_to_user_profiles

Revision ID: a1b2c3d4e5f6
Revises: 8cbe20c5762a
Create Date: 2026-05-23 23:45:00.000000

Ajoute la colonne health_consent (RGPD Art. 9) à user_profiles.
Requis pour que PATCH /profil/consent puisse persister le consentement.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '8cbe20c5762a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ajoute health_consent à user_profiles (défaut False — pas de consentement implicite)."""
    op.add_column(
        'user_profiles',
        sa.Column(
            'health_consent',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        )
    )


def downgrade() -> None:
    """Supprime health_consent de user_profiles."""
    op.drop_column('user_profiles', 'health_consent')
