"""recipe_history.recipe_id en texte, colonnes santé chiffrées élargies

Revision ID: c5d6e7f8a9b0
Revises: a1b2c3d4e5f6
Create Date: 2026-09-14 14:00:00.000000

- recipe_history.recipe_id : Integer → String(100). Les identifiants de
  recettes sont des chaînes (« soup_minestrone_vegan_10bf61 ») : sous
  PostgreSQL l'enregistrement de l'historique échouait et se rabattait sur
  un fichier JSON local au conteneur.
- user_profiles.cycle_phase / health_goal : String(120) → String(512). Le
  jeton Fernet dépasse 120 caractères dès 16 octets de texte clair
  (« perte de poids et regain énergie » → 140) : PostgreSQL refusait
  l'enregistrement.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("recipe_history") as batch:
        batch.alter_column("recipe_id", existing_type=sa.Integer(), type_=sa.String(100),
                           existing_nullable=False,
                           postgresql_using="recipe_id::varchar")
    with op.batch_alter_table("user_profiles") as batch:
        batch.alter_column("cycle_phase", existing_type=sa.String(120), type_=sa.String(512),
                           existing_nullable=True)
        batch.alter_column("health_goal", existing_type=sa.String(120), type_=sa.String(512),
                           existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch:
        batch.alter_column("health_goal", existing_type=sa.String(512), type_=sa.String(120),
                           existing_nullable=True)
        batch.alter_column("cycle_phase", existing_type=sa.String(512), type_=sa.String(120),
                           existing_nullable=True)
    with op.batch_alter_table("recipe_history") as batch:
        batch.alter_column("recipe_id", existing_type=sa.String(100), type_=sa.Integer(),
                           existing_nullable=False,
                           postgresql_using="recipe_id::integer")
