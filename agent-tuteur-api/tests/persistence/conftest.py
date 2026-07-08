"""Fixtures de tests persistance.

``session`` — SQLite en mémoire (aiosqlite), schéma créé directement depuis les
modèles (sans Alembic). Rapide, sans infrastructure, valide la logique des
repositories (filtrage tenant, agrégations, contraintes).

``postgres_engine`` (Postgres réel, smoke test migrations/JSONB/RLS) est défini
au niveau racine ``tests/conftest.py`` — partagé avec ``tests/workers``.
"""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from agent_tuteur.persistence.db import Base
from agent_tuteur.persistence import models  # noqa: F401  (enregistre les tables)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()
