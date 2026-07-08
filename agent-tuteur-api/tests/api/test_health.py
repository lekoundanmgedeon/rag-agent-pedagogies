import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agent_tuteur.api.rate_limit import limiter
from agent_tuteur.config.settings import get_settings


async def test_health_reports_db_ok_and_mock_llm(api_client):
    resp = await api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] is True
    assert data["redis"] == "degraded"  # REDIS_URL injoignable dans le fixture de test (voir conftest)
    assert data["qdrant"] == "not_configured"
    assert data["llm"] == ["mock"]


@pytest_asyncio.fixture
async def api_client_with_redis(monkeypatch):
    """Variante du fixture api_client pointant vers un Redis réellement joignable."""
    db_url = os.environ.get("TEST_DATABASE_URL")
    redis_url = os.environ.get("TEST_REDIS_URL")
    if not db_url or not redis_url:
        pytest.skip("TEST_DATABASE_URL et TEST_REDIS_URL requis pour ce test.")

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("VECTOR_BACKEND", "memory")
    monkeypatch.setenv("EMBEDDING_BACKEND", "light")
    monkeypatch.setenv("LLM_BACKEND", "mock")
    get_settings.cache_clear()
    limiter.reset()

    from agent_tuteur.api.main import create_app

    app = create_app()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client

    get_settings.cache_clear()


async def test_health_reports_redis_ok_when_reachable(api_client_with_redis):
    resp = await api_client_with_redis.get("/health")
    assert resp.json()["redis"] == "ok"
