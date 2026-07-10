"""Repositories PostgreSQL — implémentations async des ports du cœur agent.

``ProgressRepository`` et ``AuditLogRepository`` implémentent respectivement
``StudentMemoryPort`` et ``AuditLogPort`` (agent/ports.py) : le cœur métier ne
sait pas qu'il parle à Postgres. Les autres repositories (conversation,
message, feedback, document) sont consommés directement par la couche API
(étape 5), qui n'a pas besoin de passer par une interface du cœur.

Chaque requête filtre explicitement par ``tenant_id`` — défense en profondeur
indépendante des policies RLS (cf. ``persistence/db.py::set_tenant_context``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_tuteur.persistence.models import AuditLog, Conversation, Document, Feedback, Message, Progress


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class ProgressRepository:
    """Implémente ``StudentMemoryPort`` sur PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, entry: dict) -> None:
        row = Progress(
            tenant_id=entry.get("tenant_id", "default"),
            student_id=entry["student_id"],
            competence=entry.get("competence"),
            hint_level=entry.get("hint_level", 0),
            question=entry["question"],
        )
        self._session.add(row)
        await self._session.flush()

    async def history(self, student_id: str, tenant_id: str = "default") -> list[dict]:
        stmt = (
            select(Progress)
            .where(Progress.tenant_id == tenant_id, Progress.student_id == student_id)
            .order_by(Progress.created_at.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "student_id": r.student_id,
                "competence": r.competence,
                "hint_level": r.hint_level,
                "question": r.question,
                "created_at": _iso(r.created_at),
            }
            for r in rows
        ]

    async def recurrent_difficulties(self, student_id: str, tenant_id: str = "default") -> list[str]:
        """Compétences où l'élève a eu besoin d'indices poussés (niveau ≥ 3)."""
        stmt = (
            select(Progress.competence, func.count().label("n"))
            .where(
                Progress.tenant_id == tenant_id,
                Progress.student_id == student_id,
                Progress.hint_level >= 3,
                Progress.competence.is_not(None),
            )
            .group_by(Progress.competence)
            .order_by(func.count().desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [competence for competence, _n in rows]


class AuditLogRepository:
    """Implémente ``AuditLogPort`` sur PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(self, event: dict) -> None:
        row = AuditLog(
            tenant_id=event.get("tenant_id", "default"),
            student_id=event["student_id"],
            question=event["question"],
            competence=event.get("competence"),
            rag_sources=event.get("sources"),
            hint_level=event.get("hint_level", 0),
            hint_label=event.get("hint_label", ""),
            frustration_score=event.get("frustration_score", 0.0),
            tool_used=event.get("tool_used"),
        )
        self._session.add(row)
        await self._session.flush()

    async def read(self, student_id: str, tenant_id: str = "default") -> list[dict]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id, AuditLog.student_id == student_id)
            .order_by(AuditLog.created_at.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "tenant_id": r.tenant_id,
                "student_id": r.student_id,
                "question": r.question,
                "competence": r.competence,
                "rag_sources": r.rag_sources,
                "hint_level": r.hint_level,
                "hint_label": r.hint_label,
                "frustration_score": r.frustration_score,
                "tool_used": r.tool_used,
                "created_at": _iso(r.created_at),
            }
            for r in rows
        ]


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, tenant_id: str, student_id: str, title: str | None = None) -> Conversation:
        conv = Conversation(tenant_id=tenant_id, student_id=student_id, title=title)
        self._session.add(conv)
        await self._session.flush()
        return conv

    async def get(self, conversation_id: str, tenant_id: str = "default") -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id, Conversation.tenant_id == tenant_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_student(self, tenant_id: str, student_id: str) -> list[dict]:
        """Sessions de chat d'un élève, plus récente activité en premier.

        Triées par dernier message plutôt que par date de création : une
        conversation reprise il y a longtemps mais relancée aujourd'hui doit
        remonter en tête, comme dans un client de chat classique.
        """
        last_message = (
            select(Message.conversation_id, func.max(Message.created_at).label("last_at"))
            .where(Message.tenant_id == tenant_id)
            .group_by(Message.conversation_id)
            .subquery()
        )
        stmt = (
            select(Conversation, last_message.c.last_at)
            .outerjoin(last_message, last_message.c.conversation_id == Conversation.id)
            .where(Conversation.tenant_id == tenant_id, Conversation.student_id == student_id)
            .order_by(func.coalesce(last_message.c.last_at, Conversation.created_at).desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "created_at": _iso(conv.created_at),
                "last_message_at": _iso(last_at) if last_at is not None else _iso(conv.created_at),
            }
            for conv, last_at in rows
        ]

    async def delete(self, conversation_id: str, tenant_id: str) -> bool:
        conv = await self.get(conversation_id, tenant_id)
        if conv is None:
            return False
        await self._session.delete(conv)  # cascade ORM + FK ON DELETE CASCADE : messages/feedback inclus
        await self._session.flush()
        return True


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        conversation_id: str,
        tenant_id: str,
        role: str,
        content: str,
        trace: dict[str, Any] | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role=role,
            content=content,
            trace=trace,
        )
        self._session.add(msg)
        await self._session.flush()
        return msg

    async def get(self, message_id: str, tenant_id: str = "default") -> Message | None:
        stmt = select(Message).where(Message.id == message_id, Message.tenant_id == tenant_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_conversation(self, conversation_id: str, tenant_id: str = "default") -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.tenant_id == tenant_id)
            .order_by(Message.created_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_recent(self, tenant_id: str = "default", limit: int = 50) -> list[dict]:
        """Derniers tours de chat (réponses assistant + leur trace complète),
        tous élèves confondus — alimente la page Logs (vue d'ensemble)."""
        stmt = (
            select(Message, Conversation.student_id)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Message.tenant_id == tenant_id, Message.role == "assistant")
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            {
                "message_id": msg.id,
                "conversation_id": msg.conversation_id,
                "student_id": student_id,
                "created_at": msg.created_at,
                "trace": msg.trace or {},
            }
            for msg, student_id in rows
        ]


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message_id: str, tenant_id: str, value: int) -> Feedback:
        if value not in (-1, 1):
            raise ValueError("La valeur de feedback doit être -1 ou 1.")
        row = Feedback(message_id=message_id, tenant_id=tenant_id, value=value)
        self._session.add(row)
        await self._session.flush()
        return row


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
        self, tenant_id: str, filename: str, doc_type: str, metadata: dict[str, Any] | None = None
    ) -> Document:
        doc = Document(
            tenant_id=tenant_id, filename=filename, doc_type=doc_type, metadata_=metadata, status="pending"
        )
        self._session.add(doc)
        await self._session.flush()
        return doc

    async def update_status(
        self,
        document_id: str,
        status: str,
        error: str | None = None,
        tenant_id: str = "default",
        log: list[dict] | None = None,
    ) -> None:
        doc = await self.get(document_id, tenant_id)
        if doc is None:
            raise LookupError(f"Document introuvable : {document_id}")
        doc.status = status
        doc.error = error
        if log is not None:
            doc.log = log
        await self._session.flush()

    async def get(self, document_id: str, tenant_id: str = "default") -> Document | None:
        stmt = select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(self, tenant_id: str = "default") -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.tenant_id == tenant_id)
            .order_by(Document.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_by_status(self, tenant_id: str, status: str) -> list[Document]:
        stmt = select(Document).where(Document.tenant_id == tenant_id, Document.status == status)
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_by_status(self, tenant_id: str, status: str) -> int:
        stmt = select(func.count()).select_from(Document).where(
            Document.tenant_id == tenant_id, Document.status == status
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def delete(self, document_id: str, tenant_id: str = "default") -> bool:
        doc = await self.get(document_id, tenant_id)
        if doc is None:
            return False
        await self._session.delete(doc)
        await self._session.flush()
        return True
