"""Modèles ORM PostgreSQL (SQLAlchemy 2.0 déclaratif).

``tenant_id`` figure sur **toutes** les tables (y compris ``messages`` et
``feedback``, dénormalisé depuis leur parent) pour permettre un filtrage direct
et des policies RLS simples, sans jointure — décision documentée dans l'ADR
« tenant_id dès le départ ».

Les colonnes JSON utilisent ``JSON().with_variant(JSONB(), "postgresql")`` :
JSONB en production, JSON générique en test (SQLite), sans dupliquer le schéma.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON, DateTime, Float, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent_tuteur.persistence.db import Base

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Progress(Base):
    """Mémoire élève : résultat notable persisté (jamais l'état de session)."""

    __tablename__ = "progress"
    __table_args__ = (Index("ix_progress_tenant_student", "tenant_id", "student_id"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False)
    competence: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hint_level: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class AuditLog(Base):
    """Traçabilité pédagogique — store distinct de la mémoire élève."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_tenant_student", "tenant_id", "student_id"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    competence: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rag_sources: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    hint_level: Mapped[int] = mapped_column(Integer, nullable=False)
    hint_label: Mapped[str] = mapped_column(String(64), nullable=False)
    frustration_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tool_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_tenant_student", "tenant_id", "student_id"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False)
    #: Dérivé du premier message élève (tronqué) — sert de libellé de session
    #: dans la liste de conversations ; ``None`` pour les conversations créées
    #: avant l'ajout de cette colonne.
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_tenant_conversation", "tenant_id", "conversation_id"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    # Dénormalisé depuis conversations.tenant_id : filtrage direct + RLS sans jointure.
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    trace: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("value IN (-1, 1)", name="ck_feedback_value"),
        Index("ix_feedback_tenant_message", "tenant_id", "message_id"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    # Dénormalisé depuis messages.tenant_id.
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    message: Mapped[Message] = relationship(back_populates="feedback")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_tenant_status", "tenant_id", "status"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # Attribut renommé (suffixe _) : "metadata" est réservé par le déclaratif
    # SQLAlchemy (Base.metadata). Colonne DB toujours nommée "metadata".
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONVariant, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Étapes chronométrées de l'ingestion (extract/normalize/chunk/annotate/
    #: embed_upsert), pour affichage détaillé dans la page Upload/Logs.
    log: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
