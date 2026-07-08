"""add documents.log (étapes d'ingestion chronométrées)

Revision ID: 0003_add_document_log
Revises: 0002_enable_rls
Create Date: 2026-07-08 15:50:00.000000

Colonne JSONB (JSON générique hors Postgres) portant la liste des étapes
d'ingestion (extract/normalize/chunk/annotate/embed_upsert), chacune avec sa
durée — alimentée par ``ingestion.pipeline.process_document`` et le
worker/BackgroundTasks. Sert l'affichage détaillé dans la page Upload/Logs du
frontend, en complément du statut coarse (pending/indexed/failed) déjà existant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_add_document_log"
down_revision: Union[str, Sequence[str], None] = "0002_enable_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "log",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "log")
