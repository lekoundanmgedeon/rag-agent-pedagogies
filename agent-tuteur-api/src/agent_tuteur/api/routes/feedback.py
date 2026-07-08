"""POST /api/messages/{id}/feedback — vote ±1 sur une réponse de l'agent."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from agent_tuteur.api.dependencies import feedback_repo, get_tenant_id, message_repo
from agent_tuteur.api.schemas import FeedbackOut, FeedbackRequest
from agent_tuteur.persistence.repositories import FeedbackRepository, MessageRepository

router = APIRouter(prefix="/api/messages", tags=["feedback"])


@router.post("/{message_id}/feedback", response_model=FeedbackOut)
async def submit_feedback(
    message_id: str,
    payload: FeedbackRequest,
    tenant_id: str = Depends(get_tenant_id),
    messages: MessageRepository = Depends(message_repo),
    feedback: FeedbackRepository = Depends(feedback_repo),
) -> FeedbackOut:
    message = await messages.get(message_id, tenant_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message introuvable")
    row = await feedback.add(message_id, tenant_id, payload.value)
    return FeedbackOut(id=row.id, message_id=row.message_id, value=row.value)
