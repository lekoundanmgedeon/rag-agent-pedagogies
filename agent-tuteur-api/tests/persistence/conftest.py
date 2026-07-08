"""Fixtures de tests persistance.

Deux niveaux :
* ``session`` — SQLite en mémoire (aiosqlite), schéma créé directement depuis
  les modèles (sans Alembic). Rapide, sans infrastructure, valide la logique
  des repositories (filtrage tenant, agrégations, contraintes).
* ``postgres_engine`` — Postgres réel, activé seulement si ``TEST_DATABASE_URL``
  est défini et joignable (smoke test des migrations Alembic + JSONB + RLS).
  Skip automatique sinon : ne bloque pas la suite par défaut.
"""

from __future__ import annotations

import os

import pytest
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


@pytest_asyncio.fixture
async def postgres_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL non défini : smoke test Postgres ignoré.")
    engine = create_async_engine(url)
    try:
        async with engine.connect():
            pass
    except Exception as exc:  # pragma: no cover - dépend de l'infra
        pytest.skip(f"Postgres de test injoignable : {exc}")
    yield engine
    await engine.dispose()
