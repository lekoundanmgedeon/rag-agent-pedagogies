"""Dépendances FastAPI : tenant, session DB, repositories, singletons applicatifs.

Le tenant est lu depuis l'en-tête ``X-Tenant-Id`` (défaut ``settings.default_tenant``,
JWT complet différé — cf. ADR). Les singletons (agent, indexer, retriever) sont
posés sur ``app.state`` par le ``lifespan`` (voir ``api/main.py``) et simplement
lus ici, pour rester découplés du cycle de vie de l'application.

``get_session`` n'est utilisée que par les routes **non-streamées** : pour
``/api/chat`` (SSE), la session doit vivre le temps du flux complet, au-delà du
retour de la fonction de route ; elle est donc ouverte manuellement dans le
générateur via ``session_scope`` (cf. ``routes/chat.py``), pas via cette
dépendance dont le cycle de vie est lié au retour de la fonction de route.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.config.settings import get_settings
from agent_tuteur.persistence.db import session_scope
from agent_tuteur.persistence.repositories import (
    AuditLogRepository,
    ConversationRepository,
    DocumentRepository,
    FeedbackRepository,
    MessageRepository,
    ProgressRepository,
)
from agent_tuteur.vectorstore.indexer import Indexer
from agent_tuteur.vectorstore.retriever import HybridRetriever


async def get_tenant_id(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")) -> str:
    return x_tenant_id or get_settings().default_tenant


async def get_session(tenant_id: str = Depends(get_tenant_id)) -> AsyncIterator[AsyncSession]:
    """Session par requête, contexte RLS positionné. Commit auto en fin de requête."""
    async with session_scope(tenant_id) as session:
        yield session


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
