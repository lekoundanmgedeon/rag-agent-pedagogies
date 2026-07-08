"""Moteur et sessions SQLAlchemy async.

Une seule fabrique d'engine par processus (réutilisée par l'API et les scripts).
``session_scope`` fournit une session par unité de travail (pattern
« session-per-request » côté API, à l'étape 5).

Isolation multi-tenant : ``set_tenant_context`` positionne le paramètre de
session Postgres ``app.tenant_id``, lu par les policies RLS (migration
``0002_enable_rls``). C'est une **défense en profondeur** : chaque repository
filtre de toute façon explicitement par ``tenant_id`` dans ses requêtes ; RLS
protège contre un filtre oublié. Sur un dialecte non-Postgres (tests SQLite),
c'est un no-op silencieux.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base déclarative commune à tous les modèles ORM."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Crée (ou remplace) l'engine global. Appelé une fois au démarrage."""
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=echo, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Engine non initialisé : appelez init_engine() au démarrage.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory non initialisée : appelez init_engine() au démarrage.")
    return _session_factory


async def set_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """Positionne ``app.tenant_id`` pour la transaction courante (RLS)."""
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    await session.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})


@asynccontextmanager
async def session_scope(tenant_id: str | None = None) -> AsyncIterator[AsyncSession]:
    """Session avec commit/rollback automatique, contexte tenant appliqué."""
    factory = get_session_factory()
    async with factory() as session:
        if tenant_id is not None:
            await set_tenant_context(session, tenant_id)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Ferme proprement le pool de connexions (arrêt de l'application)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
