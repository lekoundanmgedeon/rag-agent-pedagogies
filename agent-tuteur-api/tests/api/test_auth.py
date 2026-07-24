"""Tests d'authentification : login, profil, création de comptes, garde-fous.

L'email étant unique **global** et la base de test partagée n'étant pas purgée
entre tests, chaque test dérive ses emails du ``tenant_id`` (unique par test)
pour éviter toute collision inter-tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from agent_tuteur.config.settings import get_settings


async def test_login_returns_token_and_profile(api_client, tenant_id, seed_user):
    email = f"admin-{tenant_id}@ecole.sn"
    await seed_user(email=email, password="secret123", tenant_id=tenant_id, role="admin")

    resp = await api_client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "admin"
    assert body["user"]["tenant_id"] == tenant_id


async def test_login_wrong_password_is_401(api_client, tenant_id, seed_user):
    email = f"prof-{tenant_id}@ecole.sn"
    await seed_user(email=email, password="bon-mot-de-passe", tenant_id=tenant_id)
    resp = await api_client.post("/api/auth/login", json={"email": email, "password": "mauvais"})
    assert resp.status_code == 401


async def test_login_unknown_email_is_401(api_client):
    resp = await api_client.post(
        "/api/auth/login", json={"email": "personne@nulle.part", "password": "x"}
    )
    assert resp.status_code == 401


async def test_me_returns_current_profile(api_client, tenant_id, seed_user):
    email = f"moi-{tenant_id}@ecole.sn"
    await seed_user(email=email, password="secret123", tenant_id=tenant_id, role="admin")
    login = await api_client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    token = login.json()["access_token"]

    me = await api_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


async def test_me_requires_token(api_client):
    assert (await api_client.get("/api/auth/me")).status_code == 401


async def test_admin_can_create_and_new_user_can_login(api_client, tenant_id, admin_headers):
    email = f"eleve-new-{tenant_id}@ecole.sn"
    created = await api_client.post(
        "/api/auth/users",
        headers=admin_headers,
        json={"email": email, "password": "motdepasse", "role": "student", "student_id": "e42"},
    )
    assert created.status_code == 201
    assert created.json()["role"] == "student"

    login = await api_client.post("/api/auth/login", json={"email": email, "password": "motdepasse"})
    assert login.status_code == 200
    assert login.json()["user"]["student_id"] == "e42"


async def test_create_user_forbidden_for_student(api_client, student_headers):
    resp = await api_client.post(
        "/api/auth/users",
        headers=student_headers,
        json={"email": "x@y.z", "password": "motdepasse", "role": "student"},
    )
    assert resp.status_code == 403


async def test_create_user_duplicate_email_is_409(api_client, tenant_id, admin_headers, seed_user):
    email = f"deja-{tenant_id}@ecole.sn"
    await seed_user(email=email, password="secret123", tenant_id=tenant_id)
    resp = await api_client.post(
        "/api/auth/users",
        headers=admin_headers,
        json={"email": email, "password": "motdepasse", "role": "student"},
    )
    assert resp.status_code == 409


async def test_expired_token_is_rejected(api_client, tenant_id):
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": "u1",
            "tenant_id": tenant_id,
            "role": "admin",
            "email": "a@b.c",
            "student_id": None,
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    resp = await api_client.get("/api/documents", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


async def test_malformed_token_is_rejected(api_client):
    resp = await api_client.get("/api/documents", headers={"Authorization": "Bearer pas-un-jwt"})
    assert resp.status_code == 401
