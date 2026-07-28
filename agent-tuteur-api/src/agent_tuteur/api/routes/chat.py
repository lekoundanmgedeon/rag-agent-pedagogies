"""POST /api/chat — a→e synchrones puis streaming SSE de la génération (f).

Contrat SSE : ``{meta: {...}}`` en premier, puis une série de ``{token: "..."}``,
enfin ``{done: {message_id, conversation_id, generation}}``. La persistance
(conversation + messages) a lieu **après** la fin du flux de tokens (non-bloquant
pour le streaming token-par-token), mais **avant** l'événement ``done`` puisque
son payload contient le ``message_id`` fraîchement créé.

Anti-injection : ``sanitize`` est appelé ici, hors du générateur, pour pouvoir
renvoyer un vrai HTTP 400 — impossible de changer le status code une fois la
``StreamingResponse`` entamée.

Observabilité : ``meta`` inclut ``trace_id``/``node_trace`` (détail nœud-par-nœud
de l'orchestration a→e, cf. ``agent/graph.py``) — c'est ce qu'affiche l'onglet
« orchestration » du chat Streamlit. Le ``trace`` persisté dans ``messages.trace``
regroupe la question, le node_trace et les stats de génération, pour que la page
Logs puisse reconstituer tout le tour sans consulter les logs bruts.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.agent.guardrails import PromptInjectionError, sanitize
from agent_tuteur.agent.llm.base import LLMError
from agent_tuteur.api.dependencies import get_agent, get_current_user
from agent_tuteur.api.rate_limit import limiter
from agent_tuteur.api.schemas import ChatRequest
from agent_tuteur.api.security import Principal
from agent_tuteur.api.streaming import sse_event
from agent_tuteur.config.settings import get_settings
from agent_tuteur.observability import get_logger, log_event
from agent_tuteur.persistence.db import session_scope
from agent_tuteur.persistence.repositories import (
    AuditLogRepository,
    ConversationRepository,
    MessageRepository,
    ProgressRepository,
)

router = APIRouter(tags=["chat"])
_logger = get_logger("agent_tuteur.api.routes.chat")

_TITLE_MAX_LEN = 60


def _make_title(question: str) -> str:
    """Libellé de session dérivé de la première question (aplatie, tronquée)."""
    flat = " ".join(question.split())
    return flat if len(flat) <= _TITLE_MAX_LEN else flat[:_TITLE_MAX_LEN].rstrip() + "…"


def _reconstruct_course_state(past_messages: list) -> dict | None:
    """Position dans un cours au dernier tour, ou ``None`` si le fil n'était pas
    en mode cours.

    On lit le bloc ``course`` (chapitre + section_index) de la trace du **dernier
    message assistant**. C'est ce qui donne au tour courant la continuité du
    cours (« continue », « passe aux exercices » ne prennent leur sens que là).
    Zéro table dédiée : l'état voyage dans ``messages.trace`` déjà persisté.
    """
    for msg in reversed(past_messages):
        if msg.role != "assistant":
            continue
        course = (msg.trace or {}).get("course")
        return course or None  # 1er assistant remonté = tour le plus récent
    return None


async def _chat_stream(
    agent: TutorAgent, payload: ChatRequest, tenant_id: str, student_id: str
) -> AsyncIterator[str]:
    async with session_scope(tenant_id) as session:
        memory = ProgressRepository(session)
        audit = AuditLogRepository(session)
        conv_repo = ConversationRepository(session)
        msg_repo = MessageRepository(session)

        conversation_id = payload.conversation_id
        conversation = None
        history: list[dict[str, str]] = []
        course_state: dict | None = None
        if conversation_id:
            conversation = await conv_repo.get(conversation_id, tenant_id)
        if conversation is not None:
            past_messages = await msg_repo.list_for_conversation(conversation.id, tenant_id)
            history = [{"role": m.role, "content": m.content} for m in past_messages]
            course_state = _reconstruct_course_state(past_messages)

        session_state = SessionState(student_id=student_id, tenant_id=tenant_id)
        # Recharge la fenêtre de répétition depuis l'historique persisté : sans ça,
        # la détection de frustration repart à zéro à chaque requête HTTP.
        session_state.recent_questions = [m["content"] for m in history if m["role"] == "user"]

        prepared = await agent.prepare(
            payload.question,
            payload.curriculum_context,
            session_state,
            memory=memory,
            audit=audit,
            conversation_history=history,
            course_state=course_state,
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
                    "course": prepared.trace.get("course"),
                    "trace_id": prepared.trace_id,
                    "node_trace": prepared.node_trace,
                }
            }
        )

        answer_parts: list[str] = []
        try:
            async for token in agent.stream(prepared):
                answer_parts.append(token)
                yield sse_event({"token": token})
        except LLMError as exc:
            log_event(_logger, "chat:generation_failed", trace_id=prepared.trace_id,
                      error=str(exc), log_level=40)
            yield sse_event({"error": f"Génération indisponible : {exc}"})
            return

        answer = "".join(answer_parts)
        await agent.commit_memory(prepared)

        if conversation is None:
            conversation = await conv_repo.create(
                tenant_id, student_id, title=_make_title(prepared.question)
            )
        conversation_id = conversation.id

        # Trace complète persistée : question + orchestration a→e + génération —
        # c'est ce que relit GET /api/logs/chat pour la page Logs Streamlit.
        full_trace = {
            **prepared.trace,
            "question": prepared.question,
            "node_trace": prepared.node_trace,
            "generation": prepared.generation,
        }

        await msg_repo.add(conversation_id, tenant_id, "user", prepared.question)
        assistant_message = await msg_repo.add(
            conversation_id, tenant_id, "assistant", answer, trace=full_trace
        )
        log_event(_logger, "chat:turn_persisted", trace_id=prepared.trace_id,
                  message_id=assistant_message.id, conversation_id=conversation_id)

        yield sse_event(
            {
                "done": {
                    "message_id": assistant_message.id,
                    "conversation_id": conversation_id,
                    "generation": prepared.generation,
                }
            }
        )


def _effective_student_id(payload: ChatRequest, principal: Principal) -> str:
    """Élève concerné par le tour de chat.

    Un élève est toujours lui-même (identité prouvée par le jeton — il ne peut pas
    dialoguer au nom d'un autre). Un admin peut cibler un élève via ``student_id``
    (utile pour tester/déboguer), à défaut son propre identifiant de compte.
    """
    if principal.role == "student":
        return principal.student_id or principal.user_id
    return payload.student_id or principal.user_id


@router.post("/api/chat")
@limiter.limit(get_settings().rate_limit_chat)
async def chat(
    request: Request,
    payload: ChatRequest,
    principal: Principal = Depends(get_current_user),
) -> StreamingResponse:
    try:
        sanitize(payload.question)
    except PromptInjectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    agent = get_agent(request)
    student_id = _effective_student_id(payload, principal)
    return StreamingResponse(
        _chat_stream(agent, payload, principal.tenant_id, student_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
