"""Fixtures des tests worker ARQ — nécessitent Postgres ET Redis réels (skip sinon)."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from arq.connections import RedisSettings, create_pool


@pytest_asyncio.fixture
async def redis_pool():
    url = os.environ.get("TEST_REDIS_URL")
    if not url:
        pytest.skip("TEST_REDIS_URL non défini : tests worker ARQ ignorés.")
    settings = RedisSettings.from_dsn(url)
    settings.conn_retries = 0
    try:
        pool = await create_pool(settings)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Redis de test injoignable : {exc}")
    yield pool
    await pool.aclose()


@pytest.fixture
def redis_url() -> str:
    url = os.environ.get("TEST_REDIS_URL")
    if not url:
        pytest.skip("TEST_REDIS_URL non défini : tests worker ARQ ignorés.")
    return url
