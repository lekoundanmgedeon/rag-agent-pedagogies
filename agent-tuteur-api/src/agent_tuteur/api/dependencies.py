"""Dépendances FastAPI : identité, tenant, session DB, repositories, singletons.

**Authentification obligatoire.** L'identité provient d'un JWT ``Bearer`` (cf.
``api/security.py``) : ``get_current_user`` décode le jeton en ``Principal``, d'où
sont dérivés le tenant (``get_tenant_id``) et le contrôle de rôle
(``require_admin``). Il n'y a plus d'en-tête ``X-Tenant-Id`` déclaratif — le
tenant est prouvé par le jeton.

``get_session`` n'est utilisée que par les routes **non-streamées** : pour
``/api/chat`` (SSE), la session doit vivre le temps du flux complet, au-delà du
retour de la fonction de route ; elle est donc ouverte manuellement dans le
générateur via ``session_scope`` (cf. ``routes/chat.py``), pas via cette
dépendance dont le cycle de vie est lié au retour de la fonction de route.

``get_session_no_tenant`` sert au **login** : la recherche de l'utilisateur par
email précède la connaissance du tenant. Elle n'accède qu'à la table ``users``,
volontairement hors RLS.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.api.security import AuthError, Principal, decode_access_token
from agent_tuteur.persistence.db import session_scope
from agent_tuteur.persistence.repositories import (
    AuditLogRepository,
    ConversationRepository,
    DocumentRepository,
    FeedbackRepository,
    MessageRepository,
    ProgressRepository,
    UserRepository,
)
from agent_tuteur.vectorstore.indexer import Indexer
from agent_tuteur.vectorstore.retriever import HybridRetriever

#: ``auto_error=False`` : on gère nous-mêmes l'absence de jeton pour renvoyer un
#: message cohérent (et un 401, pas le 403 par défaut de HTTPBearer).
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    """Identité authentifiée dérivée du JWT ``Authorization: Bearer``.

    Lève 401 si le jeton est absent, mal formé, expiré ou de signature invalide.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentification requise.")
    try:
        return decode_access_token(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal | None:
    """Identité si un jeton **valide** est présent, sinon ``None`` (jamais 401).

    Réservé aux routes publiques qui enrichissent leur réponse quand l'appelant
    est authentifié (ex. ``/health`` reste une sonde de liveness publique, mais
    ajoute le compteur d'orphelins du tenant si un jeton est fourni).
    """
    if credentials is None or not credentials.credentials:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except AuthError:
        return None


async def require_admin(principal: Principal = Depends(get_current_user)) -> Principal:
    """Réserve une route au rôle admin (403 sinon)."""
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")
    return principal


async def get_tenant_id(principal: Principal = Depends(get_current_user)) -> str:
    """Tenant prouvé par le jeton (plus d'en-tête déclaratif)."""
    return principal.tenant_id


async def get_session(tenant_id: str = Depends(get_tenant_id)) -> AsyncIterator[AsyncSession]:
    """Session par requête, contexte RLS positionné. Commit auto en fin de requête."""
    async with session_scope(tenant_id) as session:
        yield session


async def get_session_no_tenant() -> AsyncIterator[AsyncSession]:
    """Session sans contexte tenant — réservée au login (table ``users``, hors RLS)."""
    async with session_scope(None) as session:
        yield session


async def user_repo(session: AsyncSession = Depends(get_session_no_tenant)) -> UserRepository:
    return UserRepository(session)


async def progress_repo(session: AsyncSession = Depends(get_session)) -> ProgressRepository:
    return ProgressRepository(session)


async def audit_repo(session: AsyncSession = Depends(get_session)) -> AuditLogRepository:
    return AuditLogRepository(session)


async def conversation_repo(session: AsyncSession = Depends(get_session)) -> ConversationRepository:
    return ConversationRepository(session)


async def message_repo(session: AsyncSession = Depends(get_session)) -> MessageRepository:
    return MessageRepository(session)


async def feedback_repo(session: AsyncSession = Depends(get_session)) -> FeedbackRepository:
    return FeedbackRepository(session)


async def document_repo(session: AsyncSession = Depends(get_session)) -> DocumentRepository:
    return DocumentRepository(session)


def get_agent(request: Request) -> TutorAgent:
    return request.app.state.agent


def get_indexer(request: Request) -> Indexer:
    return request.app.state.indexer


def get_retriever(request: Request) -> HybridRetriever:
    return request.app.state.retriever
