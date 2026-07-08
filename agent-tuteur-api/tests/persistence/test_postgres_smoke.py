"""Smoke test contre un Postgres réel — migrations Alembic déjà appliquées.

Activé uniquement si ``TEST_DATABASE_URL`` est défini et joignable (sinon skip
automatique, cf. ``conftest.postgres_engine``). Ne relance pas Alembic lui-même
(``env.py`` appelle ``asyncio.run`` en interne, incompatible avec la boucle déjà
active de pytest-asyncio) : suppose que les migrations ont été appliquées au
préalable, comme en CI (`DATABASE_URL=$TEST_DATABASE_URL alembic upgrade head`).

Valide ce qu'un test SQLite ne peut pas couvrir : colonnes JSONB réelles, et
policies RLS forcées effectivement présentes sur chaque table tenant.
"""

from __future__ import annotations

from sqlalchemy import text

from agent_tuteur.persistence.repositories import DocumentRepository

TENANT_TABLES = ("progress", "audit_log", "conversations", "messages", "feedback", "documents")


async def test_all_tables_exist(postgres_engine):
    async with postgres_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        tables = {row[0] for row in result}
    for table in TENANT_TABLES:
        assert table in tables


async def test_metadata_column_is_jsonb(postgres_engine):
    async with postgres_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'documents' AND column_name = 'metadata'"
            )
        )
        assert result.scalar_one() == "jsonb"


async def test_rls_forced_with_tenant_policy_on_every_table(postgres_engine):
    async with postgres_engine.connect() as conn:
        for table in TENANT_TABLES:
            row = await conn.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = :t"
                ),
                {"t": table},
            )
            row_security, forced = row.one()
            assert row_security is True, f"{table} : RLS non activée"
            assert forced is True, f"{table} : RLS non forcée (propriétaire contournerait la policy)"

            policies = await conn.execute(
                text("SELECT polname FROM pg_policy WHERE polrelid = to_regclass(:t)"), {"t": table}
            )
            assert "tenant_isolation" in {r[0] for r in policies}


async def test_repository_roundtrip_against_real_postgres(postgres_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with factory() as session:
        repo = DocumentRepository(session)
        doc = await repo.create_pending("smoke_test_tenant", "smoke.pdf", "pdf", metadata={"x": 1})
        await session.commit()
        fetched = await repo.get(doc.id, "smoke_test_tenant")
        assert fetched is not None
        assert fetched.metadata_ == {"x": 1}
        await repo.delete(doc.id, "smoke_test_tenant")
        await session.commit()
