"""GET /api/logs/chat — vue d'ensemble de l'orchestration agent (tous élèves).

Alimente la page « Logs » du frontend : liste les derniers tours de chat du
tenant courant avec leur trace complète (question, détail nœud-par-nœud,
stats de génération). Les logs d'ingestion de documents n'ont pas besoin d'un
endpoint dédié : ``GET /api/documents`` expose déjà ``log`` par document.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from agent_tuteur.api.dependencies import get_tenant_id, message_repo
from agent_tuteur.api.schemas import ChatLogEntry
from agent_tuteur.persistence.repositories import MessageRepository

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/chat", response_model=list[ChatLogEntry])
async def list_chat_logs(
    limit: int = Query(default=50, ge=1, le=200),
    tenant_id: str = Depends(get_tenant_id),
    repo: MessageRepository = Depends(message_repo),
) -> list[ChatLogEntry]:
    entries = await repo.list_recent(tenant_id, limit)
    return [ChatLogEntry(**e) for e in entries]
