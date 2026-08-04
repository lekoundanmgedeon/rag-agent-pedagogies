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

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_tuteur.domain.mastery import (
    est_une_reussite,
    maitrise_mise_a_jour,
    score_observe,
)
from agent_tuteur.persistence.models import (
    AuditLog,
    Badge,
    ConceptMastery,
    Conversation,
    Document,
    ExerciseResult,
    Feedback,
    Message,
    Progress,
    Recommendation,
    StudentLink,
    User,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# --- Sérialisation des lignes pédagogiques -----------------------------------
# Les repositories renvoient des dictionnaires simples, jamais des objets ORM :
# le cœur métier et l'API restent ignorants de SQLAlchemy.


def _mastery_dict(row: ConceptMastery) -> dict:
    return {
        "student_id": row.student_id,
        "competence": row.competence,
        "chapitre": row.chapitre,
        "mastery_score": row.mastery_score,
        "attempts": row.attempts,
        "successes": row.successes,
        "last_seen": _iso(row.last_seen),
    }


def _result_dict(row: ExerciseResult) -> dict:
    return {
        "id": row.id,
        "student_id": row.student_id,
        "competence": row.competence,
        "chapitre": row.chapitre,
        "exercise_type": row.exercise_type,
        "difficulty": row.difficulty,
        "is_correct": row.is_correct,
        "score": row.score,
        "details": row.details,
        "created_at": _iso(row.created_at),
    }


def _badge_dict(row: Badge) -> dict:
    return {
        "code": row.code,
        "label": row.label,
        "description": row.description,
        "earned_at": _iso(row.earned_at),
    }


def _recommendation_dict(row: Recommendation) -> dict:
    return {
        "id": row.id,
        "student_id": row.student_id,
        "competence": row.competence,
        "chapitre": row.chapitre,
        "message": row.message,
        "author_user_id": row.author_user_id,
        "created_at": _iso(row.created_at),
    }


def _link_dict(row: StudentLink) -> dict:
    return {
        "user_id": row.user_id,
        "student_id": row.student_id,
        "created_at": _iso(row.created_at),
    }


class ProgressRepository:
    """Implémente ``StudentMemoryPort`` sur PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, entry: dict) -> None:
        row = Progress(
            tenant_id=entry.get("tenant_id", "default"),
            student_id=entry["student_id"],
            competence=entry.get("competence"),
            # Colonne NOT NULL : le mode cours n'a pas de niveau d'indice (None) ;
            # 0 est le neutre du codebase (le filtre difficultés est hint_level >= 3).
            hint_level=entry.get("hint_level") or 0,
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
            # NOT NULL : le mode cours envoie hint_level=None → 0 (neutre, cf. Progress.record).
            hint_level=event.get("hint_level") or 0,
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


class UserRepository:
    """Accès aux comptes. **Ne filtre pas par tenant** : la table ``users`` est
    hors RLS et l'email est unique globalement (recherche au login sans tenant).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.strip().lower())
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        tenant_id: str,
        email: str,
        password_hash: str,
        role: str = "student",
        student_id: str | None = None,
        display_name: str | None = None,
    ) -> User:
        user = User(
            tenant_id=tenant_id,
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            student_id=student_id,
            display_name=display_name,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def list_for_tenant(self, tenant_id: str) -> list[User]:
        stmt = select(User).where(User.tenant_id == tenant_id).order_by(User.created_at.desc())
        return list((await self._session.execute(stmt)).scalars().all())


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


# --- Domaine pédagogique -----------------------------------------------------


class MasteryRepository:
    """Niveau de maîtrise par compétence (``concept_mastery``).

    Implémente ``MasteryPort`` (agent/ports.py) : le cœur métier ne sait pas
    qu'il parle à PostgreSQL.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, student_id: str, competence: str, tenant_id: str = "default"
    ) -> dict | None:
        stmt = select(ConceptMastery).where(
            ConceptMastery.tenant_id == tenant_id,
            ConceptMastery.student_id == student_id,
            ConceptMastery.competence == competence,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _mastery_dict(row) if row else None

    async def record_attempt(
        self,
        *,
        student_id: str,
        competence: str,
        is_correct: bool | None = None,
        score: float | None = None,
        chapitre: str | None = None,
        tenant_id: str = "default",
    ) -> dict:
        """Enregistre une tentative et met à jour la maîtrise.

        La ligne est créée à la première tentative. Le calcul lui-même est dans
        ``domain/mastery.py`` : ce dépôt ne fait que lire, appliquer et écrire.
        """
        observe = score_observe(is_correct=is_correct, score=score)
        stmt = select(ConceptMastery).where(
            ConceptMastery.tenant_id == tenant_id,
            ConceptMastery.student_id == student_id,
            ConceptMastery.competence == competence,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = ConceptMastery(
                tenant_id=tenant_id,
                student_id=student_id,
                competence=competence,
                chapitre=chapitre,
                mastery_score=maitrise_mise_a_jour(None, observe),
                attempts=0,
                successes=0,
            )
            self._session.add(row)
        else:
            row.mastery_score = maitrise_mise_a_jour(row.mastery_score, observe)

        row.attempts += 1
        row.successes += 1 if est_une_reussite(observe) else 0
        row.last_seen = datetime.now(timezone.utc)
        if chapitre and not row.chapitre:
            row.chapitre = chapitre
        await self._session.flush()
        return _mastery_dict(row)

    async def list_for_student(
        self, student_id: str, tenant_id: str = "default"
    ) -> list[dict]:
        stmt = (
            select(ConceptMastery)
            .where(
                ConceptMastery.tenant_id == tenant_id,
                ConceptMastery.student_id == student_id,
            )
            .order_by(ConceptMastery.mastery_score.asc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_mastery_dict(r) for r in rows]

    async def weakest(
        self, student_id: str, tenant_id: str = "default", limit: int = 3
    ) -> list[dict]:
        """Compétences les moins maîtrisées — base des recommandations.

        Une compétence jamais tentée est exclue : un score de 0 sans tentative
        ne veut pas dire « non maîtrisée », il veut dire « inconnue ».
        """
        stmt = (
            select(ConceptMastery)
            .where(
                ConceptMastery.tenant_id == tenant_id,
                ConceptMastery.student_id == student_id,
                ConceptMastery.attempts > 0,
            )
            .order_by(ConceptMastery.mastery_score.asc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_mastery_dict(r) for r in rows]


class ExerciseResultRepository:
    """Résultats d'exercices et de quiz (``exercise_results``)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, entry: dict) -> dict:
        row = ExerciseResult(
            tenant_id=entry.get("tenant_id", "default"),
            student_id=entry["student_id"],
            competence=entry.get("competence"),
            chapitre=entry.get("chapitre"),
            exercise_type=entry.get("exercise_type", "exercice"),
            difficulty=entry.get("difficulty", "intermediate"),
            is_correct=entry.get("is_correct"),
            score=entry.get("score"),
            details=entry.get("details"),
        )
        self._session.add(row)
        await self._session.flush()
        return _result_dict(row)

    async def list_for_student(
        self, student_id: str, tenant_id: str = "default", limit: int = 50
    ) -> list[dict]:
        stmt = (
            select(ExerciseResult)
            .where(
                ExerciseResult.tenant_id == tenant_id,
                ExerciseResult.student_id == student_id,
            )
            .order_by(ExerciseResult.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_result_dict(r) for r in rows]


class BadgeRepository:
    """Badges débloqués (``badges``)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def award(
        self,
        *,
        student_id: str,
        code: str,
        label: str,
        description: str | None = None,
        tenant_id: str = "default",
    ) -> dict | None:
        """Attribue un badge. Renvoie ``None`` s'il était déjà acquis.

        L'unicité (tenant, élève, code) est aussi garantie en base : un badge ne
        peut pas être obtenu deux fois, même si deux requêtes arrivent ensemble.
        """
        stmt = select(Badge).where(
            Badge.tenant_id == tenant_id,
            Badge.student_id == student_id,
            Badge.code == code,
        )
        if (await self._session.execute(stmt)).scalar_one_or_none() is not None:
            return None
        row = Badge(
            tenant_id=tenant_id,
            student_id=student_id,
            code=code,
            label=label,
            description=description,
        )
        self._session.add(row)
        await self._session.flush()
        return _badge_dict(row)

    async def list_for_student(
        self, student_id: str, tenant_id: str = "default"
    ) -> list[dict]:
        stmt = (
            select(Badge)
            .where(Badge.tenant_id == tenant_id, Badge.student_id == student_id)
            .order_by(Badge.earned_at.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_badge_dict(r) for r in rows]


class RecommendationRepository:
    """Révisions recommandées à un élève (``recommendations``)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        student_id: str,
        competence: str,
        chapitre: str | None = None,
        message: str | None = None,
        author_user_id: str | None = None,
        tenant_id: str = "default",
    ) -> dict:
        row = Recommendation(
            tenant_id=tenant_id,
            student_id=student_id,
            competence=competence,
            chapitre=chapitre,
            message=message,
            author_user_id=author_user_id,
        )
        self._session.add(row)
        await self._session.flush()
        return _recommendation_dict(row)

    async def list_for_student(
        self, student_id: str, tenant_id: str = "default", limit: int = 20
    ) -> list[dict]:
        stmt = (
            select(Recommendation)
            .where(
                Recommendation.tenant_id == tenant_id,
                Recommendation.student_id == student_id,
            )
            .order_by(Recommendation.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_recommendation_dict(r) for r in rows]


class StudentLinkRepository:
    """Liaisons parent/enseignant → élève (``student_links``).

    **C'est ici que se joue la règle d'accès la plus importante du projet** :
    un parent ou un enseignant ne voit un élève que si une ligne l'y autorise.
    La question est toujours posée pour le compte **connecté**, jamais pour un
    identifiant fourni par le client — c'est précisément la faille relevée dans
    le dépôt NURU, où ``GET /parent/students/{parent_id}`` prenait l'identifiant
    dans l'URL et laissait donc consulter n'importe quel parent.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def link(
        self, *, user_id: str, student_id: str, tenant_id: str = "default"
    ) -> dict:
        row = StudentLink(tenant_id=tenant_id, user_id=user_id, student_id=student_id)
        self._session.add(row)
        await self._session.flush()
        return _link_dict(row)

    async def list_students_for(
        self, user_id: str, tenant_id: str = "default"
    ) -> list[str]:
        """Identifiants des élèves que ce compte a le droit de consulter."""
        stmt = (
            select(StudentLink.student_id)
            .where(StudentLink.tenant_id == tenant_id, StudentLink.user_id == user_id)
            .order_by(StudentLink.created_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def can_access(
        self, *, user_id: str, student_id: str, tenant_id: str = "default"
    ) -> bool:
        """Ce compte a-t-il le droit de consulter cet élève ?

        Réponse lue en base pour ce couple précis — à appeler avant **toute**
        lecture de données nominatives d'un élève par un tiers.
        """
        stmt = select(StudentLink.id).where(
            StudentLink.tenant_id == tenant_id,
            StudentLink.user_id == user_id,
            StudentLink.student_id == student_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None
