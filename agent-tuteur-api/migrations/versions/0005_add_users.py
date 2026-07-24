"""add users table (authentification + rôles)

Revision ID: 0005_add_users
Revises: 0004_add_conversation_title
Create Date: 2026-07-24 12:00:00.000000

Table des comptes authentifiables (login + rôle admin/élève). Voir
``persistence/models.py::User`` pour la justification des choix :

- **Volontairement HORS RLS** : le login recherche l'utilisateur par email avant
  de connaître le tenant (aucun ``app.tenant_id`` positionné). Aucune policy RLS
  n'est donc créée ici, contrairement à ``0002_enable_rls``.
- **Email unique global** (pas par tenant) : recherche de login sans ambiguïté.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_add_users"
down_revision: Union[str, Sequence[str], None] = "0004_add_conversation_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="student"),
        sa.Column("student_id", sa.String(length=128), nullable=True),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'student')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_tenant", "users", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_users_tenant", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
