"""Fixtures des tests API — application FastAPI complète contre Postgres réel.

Comme pour ``tests/persistence``, ces tests exigent ``TEST_DATABASE_URL``
(skip automatique sinon). ``LLM_BACKEND=mock`` force une chaîne déterministe
sans appel réseau réel ; ``VECTOR_BACKEND=memory`` évite toute dépendance à un
serveur Qdrant — le corpus d'exemple est auto-ingéré par le lifespan.

**Authentification.** Toutes les routes métier exigent désormais un JWT ``Bearer``.
``get_current_user`` se contente de *décoder* le jeton (aucune lecture en base,
sauf ``/auth/me`` et ``/auth/login``), donc la plupart des tests forgent un jeton
signé valide via ``auth_header`` sans seed. Les fixtures ``admin_headers`` /
``student_headers`` couvrent les cas courants ; ``seed_user`` crée un vrai compte
en base pour les tests de login.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Awaitable, Callable

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agent_tuteur.api.rate_limit import limiter
from agent_tuteur.api.security import Principal, create_access_token, hash_password
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
            client.app = app  # accès direct à app.state (ex. simuler la perte de vecteurs dans les tests)
            yield client

    get_settings.cache_clear()


@pytest.fixture
def tenant_id() -> str:
    """Tenant unique par test : évite toute interférence de données dans Postgres partagé."""
    return f"test_{uuid.uuid4().hex[:10]}"


# ── Authentification : forge de jetons signés valides (sans seed) ────────────


def auth_header(
    *,
    tenant_id: str,
    role: str = "admin",
    student_id: str | None = None,
    user_id: str | None = None,
    email: str | None = None,
) -> dict[str, str]:
    """En-tête ``Authorization: Bearer`` pour un principal forgé.

    Le jeton est signé avec le ``jwt_secret`` courant : ``get_current_user`` le
    décode sans consulter la base, donc aucun compte n'a besoin d'exister.
    """
    principal = Principal(
        user_id=user_id or f"user_{uuid.uuid4().hex[:8]}",
        tenant_id=tenant_id,
        role=role,
        email=email or "test@example.com",
        student_id=student_id,
    )
    return {"Authorization": f"Bearer {create_access_token(principal)}"}


@pytest.fixture
def make_headers() -> Callable[..., dict[str, str]]:
    """Fabrique d'en-têtes d'auth (ex. pour un second tenant/élève dans un test)."""
    return auth_header


@pytest.fixture
def admin_headers(tenant_id: str) -> dict[str, str]:
    return auth_header(tenant_id=tenant_id, role="admin")


@pytest.fixture
def student_headers(tenant_id: str) -> dict[str, str]:
    return auth_header(tenant_id=tenant_id, role="student", student_id="eleve1")


@pytest.fixture
def seed_user(api_client) -> Callable[..., Awaitable]:
    """Crée un vrai compte en base (pour les tests de login/me).

    Dépend de ``api_client`` pour que l'engine soit initialisé (lifespan actif).
    """
    from agent_tuteur.persistence.db import session_scope
    from agent_tuteur.persistence.repositories import UserRepository

    async def _seed(
        *,
        email: str,
        password: str,
        tenant_id: str,
        role: str = "admin",
        student_id: str | None = None,
    ):
        async with session_scope(None) as session:
            return await UserRepository(session).create(
                tenant_id=tenant_id,
                email=email,
                password_hash=hash_password(password),
                role=role,
                student_id=student_id,
            )

    return _seed
