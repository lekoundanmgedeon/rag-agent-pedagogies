"""étend les rôles de compte à teacher et parent

Revision ID: 0007_extend_roles
Revises: 0006_pedagogical_progress
Create Date: 2026-08-04 00:00:00.000000

``users.role`` passait de ``('admin', 'student')`` à
``('admin', 'teacher', 'parent', 'student')``.

Les rôles sont posés **dès maintenant** même si les écrans enseignant et parent
sont reportés : ajouter une valeur à une contrainte est indolore aujourd'hui,
alors que reprendre après coup des comptes déjà créés ne l'est pas.

SQLite ne sait pas modifier une contrainte en place ; le mode « batch »
d'Alembic reconstruit la table. Sans cela, la migration ne passerait que sur
PostgreSQL et les tests sur SQLite divergeraient de la production.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_extend_roles"
down_revision: str | Sequence[str] | None = "0006_pedagogical_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES_ETENDUS = "role IN ('admin', 'teacher', 'parent', 'student')"
ROLES_INITIAUX = "role IN ('admin', 'student')"


def _remplacer_contrainte(condition: str) -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_role", type_="check")
        batch.create_check_constraint("ck_users_role", condition)


def upgrade() -> None:
    _remplacer_contrainte(ROLES_ETENDUS)


def downgrade() -> None:
    # Un compte enseignant ou parent existant violerait la contrainte initiale :
    # on le ramène à « student », le rôle le moins privilégié. Jamais l'inverse.
    op.execute("UPDATE users SET role = 'student' WHERE role IN ('teacher', 'parent')")
    _remplacer_contrainte(ROLES_INITIAUX)
