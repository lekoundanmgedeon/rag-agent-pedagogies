"""GET /api/conversations — sessions de chat d'un élève (liste, historique, suppression).

Une « session de chat » est une ``Conversation`` (persistée dès le premier tour
par ``routes/chat.py``, titrée à partir de la première question de l'élève).
Ces routes permettent au frontend de lister les sessions passées, recharger
l'historique complet de l'une d'elles pour la reprendre, ou la supprimer —
``/api/chat`` reste seul responsable de la création/écriture des tours.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from agent_tuteur.api.dependencies import conversation_repo, get_tenant_id, message_repo
from agent_tuteur.api.schemas import ConversationOut, MessageOut
from agent_tuteur.persistence.repositories import ConversationRepository, MessageRepository

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    student_id: str = Query(..., min_length=1, max_length=128),
    tenant_id: str = Depends(get_tenant_id),
    conversations: ConversationRepository = Depends(conversation_repo),
) -> list[ConversationOut]:
    rows = await conversations.list_for_student(tenant_id, student_id)
    return [ConversationOut(**row) for row in rows]


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def get_conversation_messages(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    conversations: ConversationRepository = Depends(conversation_repo),
    messages: MessageRepository = Depends(message_repo),
) -> list[MessageOut]:
    conversation = await conversations.get(conversation_id, tenant_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    rows = await messages.list_for_conversation(conversation_id, tenant_id)
    return [MessageOut.model_validate(m) for m in rows]


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    tenant_id: str = Depends(get_tenant_id),
    conversations: ConversationRepository = Depends(conversation_repo),
) -> dict:
    deleted = await conversations.delete(conversation_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {"deleted": True}
