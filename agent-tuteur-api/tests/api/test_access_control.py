"""Contrôle d'accès aux données d'un élève — le garde-fou qui manquait à NURU.

Ces tests existent parce que le dépôt NURU exposait la progression nominative de
n'importe quel élève à qui devinait son identifiant. La règle est désormais
écrite une seule fois (``dependencies.ensure_can_access_student``) et vérifiée
ici pour chaque rôle.
"""

import uuid

import pytest

from agent_tuteur.persistence.db import session_scope
from agent_tuteur.persistence.repositories import StudentLinkRepository, UserRepository


# --- Aucune route métier ne répond sans jeton --------------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/progression/eleve1"),
        ("GET", "/api/conversations"),
        ("POST", "/api/chat"),
        ("GET", "/api/documents"),
        ("POST", "/api/search"),
        ("GET", "/api/logs/chat"),
        ("POST", "/api/quiz"),
        ("POST", "/api/quiz/answer"),
        ("GET", "/api/evaluation/eleve1"),
        ("GET", "/api/mastery/eleve1"),
    ],
)
async def test_aucune_route_metier_ne_repond_sans_jeton(api_client, method, path):
    """Régression NURU : 31 routes y étaient ouvertes à tous."""
    reponse = await api_client.request(method, path, json={})
    assert reponse.status_code == 401, f"{method} {path} accessible sans authentification"


async def test_un_jeton_invalide_est_refuse(api_client):
    reponse = await api_client.get(
        "/api/progression/eleve1", headers={"Authorization": "Bearer pas-un-jeton"}
    )
    assert reponse.status_code == 401


# --- Un élève ne voit que lui-même -------------------------------------------


async def test_un_eleve_voit_sa_propre_progression(api_client, student_headers):
    reponse = await api_client.get("/api/progression/eleve1", headers=student_headers)
    assert reponse.status_code == 200


async def test_un_eleve_ne_voit_pas_celle_d_un_autre(api_client, student_headers):
    reponse = await api_client.get("/api/progression/eleve2", headers=student_headers)
    assert reponse.status_code == 403


# --- Un parent ou un enseignant ne voit que les élèves qui lui sont rattachés --


async def _compte_encadrant(tenant_id: str, role: str) -> str:
    """Crée un vrai compte parent/enseignant en base et renvoie son identifiant."""
    async with session_scope(None) as session:
        user = await UserRepository(session).create(
            tenant_id=tenant_id,
            email=f"{role}-{uuid.uuid4().hex[:8]}@ecole.sn",
            password_hash="x",
            role=role,
        )
        return user.id


async def _rattacher(tenant_id: str, user_id: str, student_id: str) -> None:
    async with session_scope(tenant_id) as session:
        await StudentLinkRepository(session).link(
            user_id=user_id, student_id=student_id, tenant_id=tenant_id
        )


@pytest.mark.parametrize("role", ["parent", "teacher"])
async def test_un_encadrant_voit_l_eleve_qui_lui_est_rattache(
    api_client, tenant_id, make_headers, role
):
    user_id = await _compte_encadrant(tenant_id, role)
    await _rattacher(tenant_id, user_id, "mon-eleve")

    headers = make_headers(tenant_id=tenant_id, role=role, user_id=user_id)
    reponse = await api_client.get("/api/progression/mon-eleve", headers=headers)
    assert reponse.status_code == 200


@pytest.mark.parametrize("role", ["parent", "teacher"])
async def test_un_encadrant_ne_voit_pas_un_eleve_non_rattache(
    api_client, tenant_id, make_headers, role
):
    """Le cas qui comptait : sans ce test, l'extension des rôles ouvrait une faille."""
    user_id = await _compte_encadrant(tenant_id, role)
    await _rattacher(tenant_id, user_id, "mon-eleve")

    headers = make_headers(tenant_id=tenant_id, role=role, user_id=user_id)
    reponse = await api_client.get("/api/progression/eleve-des-voisins", headers=headers)
    assert reponse.status_code == 403


@pytest.mark.parametrize("role", ["parent", "teacher"])
async def test_un_encadrant_sans_aucun_rattachement_ne_voit_rien(
    api_client, tenant_id, make_headers, role
):
    user_id = await _compte_encadrant(tenant_id, role)
    headers = make_headers(tenant_id=tenant_id, role=role, user_id=user_id)
    reponse = await api_client.get("/api/progression/nimporte-qui", headers=headers)
    assert reponse.status_code == 403


async def test_un_rattachement_ne_traverse_pas_les_etablissements(
    api_client, tenant_id, make_headers
):
    """Un parent rattaché dans un établissement n'a aucun droit dans un autre."""
    user_id = await _compte_encadrant(tenant_id, "parent")
    await _rattacher(tenant_id, user_id, "mon-eleve")

    autre_etablissement = f"test_{uuid.uuid4().hex[:10]}"
    headers = make_headers(tenant_id=autre_etablissement, role="parent", user_id=user_id)
    reponse = await api_client.get("/api/progression/mon-eleve", headers=headers)
    assert reponse.status_code == 403


# --- L'admin voit son établissement, et lui seul -------------------------------


async def test_un_admin_voit_n_importe_quel_eleve_de_son_etablissement(
    api_client, admin_headers
):
    reponse = await api_client.get("/api/progression/eleve-quelconque", headers=admin_headers)
    assert reponse.status_code == 200


async def test_un_role_inconnu_n_obtient_aucun_acces(api_client, tenant_id, make_headers):
    """Le défaut est le refus : un rôle non prévu ne passe pas au travers."""
    headers = make_headers(tenant_id=tenant_id, role="inspecteur")
    reponse = await api_client.get("/api/progression/eleve1", headers=headers)
    assert reponse.status_code == 403
