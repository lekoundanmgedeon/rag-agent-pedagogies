"""POST /api/chat — a→e synchrones puis streaming SSE de la génération (f).

Contrat SSE : ``{meta: {...}}`` en premier, puis une série de ``{token: "..."}``,
enfin ``{done: {message_id, conversation_id}}``. La persistance (conversation +
messages) a lieu **après** la fin du flux de tokens (non-bloquant pour le
streaming token-par-token), mais **avant** l'événement ``done`` puisque son
payload contient le ``message_id`` fraîchement créé.

Anti-injection : ``sanitize`` est appelé ici, hors du générateur, pour pouvoir
renvoyer un vrai HTTP 400 — impossible de changer le status code une fois la
``StreamingResponse`` entamée.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.agent.guardrails import PromptInjectionError, sanitize
from agent_tuteur.agent.llm.base import LLMError
from agent_tuteur.api.dependencies import get_agent, get_tenant_id
from agent_tuteur.api.rate_limit import limiter
from agent_tuteur.api.schemas import ChatRequest
from agent_tuteur.api.streaming import sse_event
from agent_tuteur.config.settings import get_settings
from agent_tuteur.persistence.db import session_scope
from agent_tuteur.persistence.repositories import (
    AuditLogRepository,
    ConversationRepository,
    MessageRepository,
    ProgressRepository,
)

router = APIRouter(tags=["chat"])


async def _chat_stream(agent: TutorAgent, payload: ChatRequest, tenant_id: str) -> AsyncIterator[str]:
    async with session_scope(tenant_id) as session:
        memory = ProgressRepository(session)
        audit = AuditLogRepository(session)
        conv_repo = ConversationRepository(session)
        msg_repo = MessageRepository(session)

        session_state = SessionState(student_id=payload.student_id, tenant_id=tenant_id)
        prepared = await agent.prepare(
            payload.question, payload.curriculum_context, session_state, memory=memory, audit=audit
        )

        yield sse_event(
            {
                "meta": {
                    "hint_level": prepared.hint_level,
                    "hint_label": prepared.hint_label,
                    "sources": prepared.trace["sources"],
                    "scores": prepared.trace["scores"],
                    "tool_used": prepared.trace["tool_used"],
                    "frustration_score": prepared.trace["frustration_score"],
                }
            }
        )

        answer_parts: list[str] = []
        try:
            async for token in agent.stream(prepared):
                answer_parts.append(token)
                yield sse_event({"token": token})
        except LLMError as exc:
            yield sse_event({"error": f"Génération indisponible : {exc}"})
            return

        answer = "".join(answer_parts)
        await agent.commit_memory(prepared)

        conversation_id = payload.conversation_id
        conversation = None
        if conversation_id:
            conversation = await conv_repo.get(conversation_id, tenant_id)
        if conversation is None:
            conversation = await conv_repo.create(tenant_id, payload.student_id)
        conversation_id = conversation.id

        await msg_repo.add(conversation_id, tenant_id, "user", prepared.question)
        assistant_message = await msg_repo.add(
            conversation_id, tenant_id, "assistant", answer, trace=prepared.trace
        )

        yield sse_event({"done": {"message_id": assistant_message.id, "conversation_id": conversation_id}})


@router.post("/api/chat")
@limiter.limit(get_settings().rate_limit_chat)
async def chat(
    request: Request,
    payload: ChatRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> StreamingResponse:
    try:
        sanitize(payload.question)
    except PromptInjectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    agent = get_agent(request)
    return StreamingResponse(
        _chat_stream(agent, payload, tenant_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
