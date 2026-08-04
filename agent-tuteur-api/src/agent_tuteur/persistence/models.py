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
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Boolean, DateTime, Float, Uuid

from agent_tuteur.persistence.db import Base

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


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

    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


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
    feedback: Mapped[list[Feedback]] = relationship(back_populates="message", cascade="all, delete-orphan")


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


class User(Base):
    """Compte authentifiable — porte du système (login) et rôle (admin/élève).

    **Hors RLS** (contrairement aux autres tables) : le login cherche l'utilisateur
    par email *avant* de connaître le tenant, donc aucun ``app.tenant_id`` n'est
    positionné à ce moment. L'email est donc unique **globalement** (pas par
    tenant) pour que la recherche au login soit sans ambiguïté. Le ``tenant_id``
    reste porté par la ligne : il est injecté dans le JWT après login et sert de
    contexte à toutes les requêtes ultérieures.

    ``student_id`` relie un compte élève à l'identifiant déjà utilisé partout dans
    le cœur (progression, conversations, audit) ; ``None`` pour un admin.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'teacher', 'parent', 'student')", name="ck_users_role"
        ),
        Index("ix_users_tenant", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="student")
    student_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# --- Domaine pédagogique (porté de NURU) -------------------------------------
# Ces cinq tables constituent le « mastery learning » : on suit ce que l'élève
# maîtrise notion par notion, plutôt que de compter des exercices faits.
# Portées de ``backend/app/memory/models.py`` (NURU) sur les conventions du
# dépôt : identifiants UUID, ``tenant_id`` pour la RLS, typage ``Mapped[...]``,
# horodatage avec fuseau. Le vocabulaire est aligné sur l'existant : NURU dit
# « concept », le dépôt dit déjà « competence » partout (``progress``,
# ``audit_log``, taxonomie) — c'est ce dernier qui est retenu.


class ConceptMastery(Base):
    """Niveau de maîtrise d'une compétence par un élève.

    Une ligne par couple (élève, compétence). ``mastery_score`` va de 0.0 (non
    maîtrisé) à 1.0 (maîtrisé) ; ``attempts``/``successes`` gardent la trace
    brute qui a produit ce score, pour pouvoir le recalculer si la formule
    change.
    """

    __tablename__ = "concept_mastery"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "student_id", "competence", name="uq_mastery_student_competence"
        ),
        Index("ix_mastery_tenant_student", "tenant_id", "student_id"),
        CheckConstraint("mastery_score >= 0.0 AND mastery_score <= 1.0", name="ck_mastery_range"),
        CheckConstraint("successes <= attempts", name="ck_mastery_successes"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False)
    competence: Mapped[str] = mapped_column(String(255), nullable=False)
    chapitre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mastery_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class ExerciseResult(Base):
    """Résultat d'un exercice ou d'un quiz — alimente la maîtrise et les badges."""

    __tablename__ = "exercise_results"
    __table_args__ = (
        Index("ix_exercise_results_tenant_student", "tenant_id", "student_id"),
        CheckConstraint("exercise_type IN ('exercice', 'quiz')", name="ck_exercise_type"),
        CheckConstraint("score IS NULL OR (score >= 0.0 AND score <= 1.0)", name="ck_exercise_score"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False)
    competence: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chapitre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exercise_type: Mapped[str] = mapped_column(String(16), nullable=False, default="exercice")
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False, default="intermediate")
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    #: Note de 0.0 à 1.0 (un quiz à plusieurs questions donne une note partielle).
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    #: Détail libre : réponses données, erreurs repérées…
    details: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class Badge(Base):
    """Badge de motivation débloqué par un élève (« premier quiz », « 10 exercices »)."""

    __tablename__ = "badges"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", "code", name="uq_badge_student_code"),
        Index("ix_badges_tenant_student", "tenant_id", "student_id"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False)
    #: Identifiant stable du badge (``premier_quiz``) — c'est lui qui fait foi ;
    #: ``label`` et ``description`` sont l'habillage affiché, modifiable.
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class Recommendation(Base):
    """Révision ou exercice recommandé à un élève.

    L'auteur (``author_user_id``) est un compte enseignant *ou* nul quand la
    recommandation est produite automatiquement à partir de la maîtrise.
    """

    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recommendations_tenant_student", "tenant_id", "student_id"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author_user_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    competence: Mapped[str] = mapped_column(String(255), nullable=False)
    chapitre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class StudentLink(Base):
    """Liaison entre un compte parent/enseignant et un élève suivi.

    **Cette seule table remplace** ``parent_students``, ``teacher_students`` et
    ``teachers`` de NURU. La raison : chez NURU, un enseignant avait sa propre
    table avec son propre mot de passe, donc **deux chemins d'authentification**
    à sécuriser au lieu d'un. Ici, un enseignant est un ``User`` avec
    ``role='teacher'`` : un seul chemin de login, un seul endroit où vérifier
    les droits.

    C'est cette table qui répond à la question « ce parent a-t-il le droit de
    voir cet élève ? ». La réponse se lit **en base, pour le compte connecté** —
    jamais à partir d'un identifiant envoyé par le client.
    """

    __tablename__ = "student_links"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "student_id", name="uq_student_link"),
        Index("ix_student_links_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    #: Compte parent ou enseignant. Le rôle est porté par ``users.role``.
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


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
