"""enable row level security per tenant

Revision ID: 0002_enable_rls
Revises: 0001_initial_schema
Create Date: 2026-07-08 02:40:00.000000

Active le Row Level Security sur toutes les tables porteuses de ``tenant_id``.
Chaque policy compare la colonne à ``current_setting('app.tenant_id', true)``,
positionné par ``persistence.db.set_tenant_context`` pour la session courante.

Défense en profondeur : les repositories filtrent de toute façon explicitement
par ``tenant_id`` dans leurs requêtes. RLS protège contre un filtre oublié ou
une requête ad-hoc mal écrite. ``FORCE ROW LEVEL SECURITY`` fait que même le
propriétaire de la table (souvent l'utilisateur applicatif) est soumis à la
policy — sans quoi RLS ne s'applique par défaut qu'aux rôles non-propriétaires.

No-op sur un dialecte non-Postgres (SQLite en tests) : RLS est une notion
Postgres uniquement.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_enable_rls"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ("progress", "audit_log", "conversations", "messages", "feedback", "documents")


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
