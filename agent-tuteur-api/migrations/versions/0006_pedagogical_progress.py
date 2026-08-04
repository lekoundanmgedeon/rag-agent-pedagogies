"""domaine pédagogique : maîtrise, résultats, badges, recommandations, liaisons

Revision ID: 0006_pedagogical_progress
Revises: 0005_add_users
Create Date: 2026-08-04 00:00:00.000000

Porte le modèle « mastery learning » de NURU (suivre ce que l'élève maîtrise
notion par notion) sur les conventions du dépôt : UUID, ``tenant_id``, RLS.

Trois tables de NURU sont **volontairement absentes** :

- ``students`` : le dépôt identifie déjà un élève par ``student_id``, présent
  sur ``progress``, ``audit_log``, ``conversations`` et ``users`` ;
- ``interactions`` : doublonne ``messages`` (avec sa trace d'orchestration) ;
- ``teachers`` : un enseignant est un ``User`` avec ``role='teacher'``, pas une
  table à part avec son propre mot de passe.

RLS activée comme dans ``0002_enable_rls``, y compris ``FORCE`` : sans lui, le
propriétaire de la table (souvent l'utilisateur applicatif) échapperait à la
policy.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_pedagogical_progress"
down_revision: str | Sequence[str] | None = "0005_add_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "concept_mastery",
    "exercise_results",
    "badges",
    "recommendations",
    "student_links",
)

JSONVariant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "concept_mastery",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("competence", sa.String(length=255), nullable=False),
        sa.Column("chapitre", sa.String(length=255), nullable=True),
        sa.Column("mastery_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id", "student_id", "competence", name="uq_mastery_student_competence"
        ),
        sa.CheckConstraint("mastery_score >= 0.0 AND mastery_score <= 1.0", name="ck_mastery_range"),
        sa.CheckConstraint("successes <= attempts", name="ck_mastery_successes"),
    )
    op.create_index("ix_concept_mastery_tenant_id", "concept_mastery", ["tenant_id"])
    op.create_index("ix_mastery_tenant_student", "concept_mastery", ["tenant_id", "student_id"])

    op.create_table(
        "exercise_results",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("competence", sa.String(length=255), nullable=True),
        sa.Column("chapitre", sa.String(length=255), nullable=True),
        sa.Column("exercise_type", sa.String(length=16), nullable=False, server_default="exercice"),
        sa.Column("difficulty", sa.String(length=16), nullable=False, server_default="intermediate"),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("details", JSONVariant, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("exercise_type IN ('exercice', 'quiz')", name="ck_exercise_type"),
        sa.CheckConstraint(
            "score IS NULL OR (score >= 0.0 AND score <= 1.0)", name="ck_exercise_score"
        ),
    )
    op.create_index("ix_exercise_results_tenant_id", "exercise_results", ["tenant_id"])
    op.create_index(
        "ix_exercise_results_tenant_student", "exercise_results", ["tenant_id", "student_id"]
    )

    op.create_table(
        "badges",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "student_id", "code", name="uq_badge_student_code"),
    )
    op.create_index("ix_badges_tenant_id", "badges", ["tenant_id"])
    op.create_index("ix_badges_tenant_student", "badges", ["tenant_id", "student_id"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column(
            "author_user_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("competence", sa.String(length=255), nullable=False),
        sa.Column("chapitre", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recommendations_tenant_id", "recommendations", ["tenant_id"])
    op.create_index(
        "ix_recommendations_tenant_student", "recommendations", ["tenant_id", "student_id"]
    )

    op.create_table(
        "student_links",
        sa.Column("id", sa.Uuid(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("student_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "user_id", "student_id", name="uq_student_link"),
    )
    op.create_index("ix_student_links_tenant_id", "student_links", ["tenant_id"])
    op.create_index("ix_student_links_tenant_user", "student_links", ["tenant_id", "user_id"])

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
    if op.get_bind().dialect.name == "postgresql":
        for table in TENANT_TABLES:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("student_links")
    op.drop_table("recommendations")
    op.drop_table("badges")
    op.drop_table("exercise_results")
    op.drop_table("concept_mastery")
