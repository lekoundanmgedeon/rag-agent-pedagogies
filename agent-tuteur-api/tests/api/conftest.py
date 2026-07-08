"""Fixtures des tests API — application FastAPI complète contre Postgres réel.

Comme pour ``tests/persistence``, ces tests exigent ``TEST_DATABASE_URL``
(skip automatique sinon). ``LLM_BACKEND=mock`` force une chaîne déterministe
sans appel réseau réel ; ``VECTOR_BACKEND=memory`` évite toute dépendance à un
serveur Qdrant — le corpus d'exemple est auto-ingéré par le lifespan.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agent_tuteur.api.rate_limit import limiter
from agent_tuteur.config.settings import get_settings


@pytest_asyncio.fixture
async def api_client(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL non défini : tests API ignorés.")

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("VECTOR_BACKEND", "memory")
    monkeypatch.setenv("EMBEDDING_BACKEND", "light")
    monkeypatch.setenv("LLM_BACKEND", "mock")
    # Port délibérément injoignable : force le repli déterministe en BackgroundTasks
    # (même processus, sans queue) pour ces tests génériques d'API. La mécanique
    # ARQ réelle (queue + worker séparé) est testée à part dans tests/workers/,
    # contre le Redis de test dédié — ne jamais pointer ici vers le Redis par
    # défaut (6379) qui peut être un service tiers du système hôte.
    monkeypatch.setenv("REDIS_URL", "redis://localhost:1/0")
    get_settings.cache_clear()
    limiter.reset()  # évite les interférences de quota entre tests (limiter = singleton)

    from agent_tuteur.api.main import create_app

    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    get_settings.cache_clear()


@pytest.fixture
def tenant_id() -> str:
    """Tenant unique par test : évite toute interférence de données dans Postgres partagé."""
    return f"test_{uuid.uuid4().hex[:10]}"
