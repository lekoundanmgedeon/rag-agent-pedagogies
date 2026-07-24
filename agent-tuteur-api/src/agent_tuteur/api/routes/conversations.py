"""GET /api/conversations — sessions de chat d'un élève (liste, historique, suppression).

Une « session de chat » est une ``Conversation`` (persistée dès le premier tour
par ``routes/chat.py``, titrée à partir de la première question de l'élève).
Ces routes permettent au frontend de lister les sessions passées, recharger
l'historique complet de l'une d'elles pour la reprendre, ou la supprimer —
``/api/chat`` reste seul responsable de la création/écriture des tours.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from agent_tuteur.api.dependencies import conversation_repo, get_current_user, message_repo
from agent_tuteur.api.schemas import ConversationOut, MessageOut
from agent_tuteur.api.security import Principal
from agent_tuteur.persistence.repositories import ConversationRepository, MessageRepository

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _target_student_id(principal: Principal, requested: str | None) -> str:
    """Élève dont on liste les conversations : l'élève lui-même, ou l'élève ciblé
    par un admin. Un élève ne peut jamais viser un autre identifiant."""
    if principal.role == "student":
        return principal.student_id or principal.user_id
    if not requested:
        raise HTTPException(status_code=400, detail="Paramètre student_id requis pour un administrateur.")
    return requested


def _assert_can_access(principal: Principal, conversation) -> None:  # noqa: ANN001 - Conversation ORM
    """Un élève ne peut accéder qu'à ses propres conversations (admin : tout le tenant)."""
    if principal.role == "student":
        owner = principal.student_id or principal.user_id
        if conversation.student_id != owner:
            raise HTTPException(status_code=404, detail="Conversation introuvable")


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    student_id: str | None = Query(default=None, max_length=128),
    principal: Principal = Depends(get_current_user),
    conversations: ConversationRepository = Depends(conversation_repo),
) -> list[ConversationOut]:
    target = _target_student_id(principal, student_id)
    rows = await conversations.list_for_student(principal.tenant_id, target)
    return [ConversationOut(**row) for row in rows]


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def get_conversation_messages(
    conversation_id: str,
    principal: Principal = Depends(get_current_user),
    conversations: ConversationRepository = Depends(conversation_repo),
    messages: MessageRepository = Depends(message_repo),
) -> list[MessageOut]:
    conversation = await conversations.get(conversation_id, principal.tenant_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    _assert_can_access(principal, conversation)
    rows = await messages.list_for_conversation(conversation_id, principal.tenant_id)
    return [MessageOut.model_validate(m) for m in rows]


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    principal: Principal = Depends(get_current_user),
    conversations: ConversationRepository = Depends(conversation_repo),
) -> dict:
    conversation = await conversations.get(conversation_id, principal.tenant_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    _assert_can_access(principal, conversation)
    await conversations.delete(conversation_id, principal.tenant_id)
    return {"deleted": True}
