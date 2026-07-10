"""add conversations.title

Revision ID: 0004_add_conversation_title
Revises: 0003_add_document_log
Create Date: 2026-07-10 10:00:00.000000

Colonne libellé de session (dérivée du premier message élève, tronquée),
affichée dans la liste de conversations du frontend — voir
``api/routes/conversations.py``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_add_conversation_title"
down_revision: Union[str, Sequence[str], None] = "0003_add_document_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("title", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "title")
