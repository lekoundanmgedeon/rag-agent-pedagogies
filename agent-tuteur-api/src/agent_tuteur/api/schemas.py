"""Schémas Pydantic des requêtes/réponses de l'API (couche transport uniquement).

Ces modèles ne dupliquent pas ``CurriculumMetadata`` : le contexte curriculaire
d'une requête est un simple ``dict[str, str]`` transmis tel quel au retriever
(qui applique déjà l'expansion d'alias de série).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    tenant_id: str
    student_id: str | None = None
    display_name: str | None = None

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=256)
    #: Les quatre rôles acceptés en base depuis la migration 0007. Un rôle
    #: `teacher`/`parent` ne donne par lui-même aucun accès aux données d'un
    #: élève : c'est la table `student_links` qui l'autorise, élève par élève.
    role: Literal["admin", "teacher", "parent", "student"] = "student"
    student_id: str | None = Field(default=None, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    #: Optionnel : ignoré pour un élève (dérivé de son jeton). Un admin peut le
    #: fournir pour dialoguer au nom d'un élève donné.
    student_id: str | None = Field(default=None, max_length=128)
    conversation_id: str | None = None
    curriculum_context: dict[str, str] = Field(default_factory=dict)


class ConversationOut(BaseModel):
    id: str
    title: str | None
    created_at: str
    last_message_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    trace: dict | None = None

    model_config = {"from_attributes": True}


class SourceOut(BaseModel):
    id: str
    label: str
    type_chunk: str
    score: float


class NodeTraceEntry(BaseModel):
    node: str
    duration_ms: float
    trace_id: str | None = None

    model_config = {"extra": "allow"}  # champs additionnels selon le nœud (n_sources, level, tool_used…)


class ChatMeta(BaseModel):
    hint_level: int
    hint_label: str
    sources: list[SourceOut]
    scores: list[float]
    tool_used: str | None
    frustration_score: float
    trace_id: str
    node_trace: list[NodeTraceEntry]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    curriculum_context: dict[str, str] = Field(default_factory=dict)
    top_k: int = Field(default=5, ge=1, le=50)


class SearchResultOut(BaseModel):
    id: str
    text: str
    score: float
    dense_score: float | None
    sparse_score: float | None
    metadata: dict


class CatalogueOut(BaseModel):
    """Chapitres réellement indexés pour un cadre curriculaire donné.

    Sert l'écran d'accueil : les sujets proposés à l'élève doivent venir de ce
    que le corpus contient, jamais d'une liste écrite à la main (cas QA #28 —
    l'accueil proposait « Fais-moi un cours sur les suites numériques », que
    l'agent refusait ensuite, à juste titre, faute de leçon indexée).
    """

    chapitres: list[str]


class UploadedDocumentOut(BaseModel):
    document_id: str
    filename: str
    status: str


class DocumentOut(BaseModel):
    id: str
    filename: str
    doc_type: str
    status: str
    error: str | None
    metadata: dict | None
    log: list[dict] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentStatusEvent(BaseModel):
    status: str
    error: str | None = None


class ProgressEntryOut(BaseModel):
    id: str
    competence: str | None
    hint_level: int
    question: str
    created_at: str


class ProgressionOut(BaseModel):
    student_id: str
    history: list[ProgressEntryOut]
    recurrent_difficulties: list[str]


class FeedbackRequest(BaseModel):
    value: Literal[-1, 1]


class FeedbackOut(BaseModel):
    id: str
    message_id: str
    value: int


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    db: bool
    redis: str
    qdrant: str
    llm: list[str]
    documents_orphaned: int


class DocumentConsistencyOut(BaseModel):
    document_id: str
    filename: str
    status: str
    chunks_in_store: int
    consistent: bool


class VerifyAllOut(BaseModel):
    checked: int
    orphaned: list[DocumentConsistencyOut]


class ChatLogEntry(BaseModel):
    """Un tour de chat, pour la page « Logs » (vue d'ensemble multi-élèves).

    ``trace`` contient déjà la question (clé ``question``), le detail
    nœud-par-nœud (``node_trace``) et les stats de génération (``generation``)
    — voir ``api/routes/chat.py`` pour la construction de cet objet avant
    persistance.
    """

    message_id: str
    conversation_id: str
    student_id: str
    created_at: datetime
    trace: dict


# --- Domaine pédagogique -----------------------------------------------------


class QuizRequest(BaseModel):
    #: Compétence à évaluer. Absente, elle est déduite du cadre curriculaire et
    #: des extraits remontés par la recherche.
    competence: str | None = Field(default=None, max_length=255)
    quiz_type: Literal["qcm", "vrai_faux"] = "qcm"
    curriculum_context: dict[str, str] = Field(default_factory=dict)


class QuizChoiceOut(BaseModel):
    id: str
    text: str


class QuizOut(BaseModel):
    """Quiz remis à l'élève. **Sans la bonne réponse** — voir ``quiz_token``."""

    competence: str
    quiz_type: str
    #: Faux quand le modèle n'a pas produit de quiz exploitable. Les autres
    #: champs sont alors vides : l'interface doit afficher ``instructions``.
    available: bool
    question: str = ""
    choices: list[QuizChoiceOut] = Field(default_factory=list)
    #: Correction scellée et signée, à renvoyer tel quel à ``/api/quiz/answer``.
    #: Opaque pour le client : il ne peut ni la lire ni la modifier.
    quiz_token: str = ""
    instructions: str = ""


class QuizAnswerRequest(BaseModel):
    quiz_token: str = Field(min_length=1)
    answer: str = Field(min_length=1, max_length=64)
    #: Optionnel : ignoré pour un élève (dérivé de son jeton d'identité).
    student_id: str | None = Field(default=None, max_length=128)


class MasteryEntryOut(BaseModel):
    competence: str
    chapitre: str | None = None
    mastery_score: float
    attempts: int
    successes: int
    #: « maitrise » | « en_cours » | « faible » | « non_commence ».
    statut: str
    last_seen: str | None = None


class BadgeOut(BaseModel):
    code: str
    label: str
    description: str | None = None
    earned_at: str


class QuizCorrectionOut(BaseModel):
    is_correct: bool
    correct_answer: str
    given_answer: str
    explanation: str
    score: float
    #: Nouvel état de maîtrise de la compétence après ce résultat.
    mastery: MasteryEntryOut | None = None
    #: Badges débloqués par ce résultat (vide la plupart du temps).
    badges: list[BadgeOut] = Field(default_factory=list)


class ExerciseResultOut(BaseModel):
    id: str
    competence: str | None = None
    chapitre: str | None = None
    exercise_type: str
    difficulty: str
    is_correct: bool | None = None
    score: float | None = None
    created_at: str


class EvaluationHistoryOut(BaseModel):
    student_id: str
    results: list[ExerciseResultOut]


class MasteryOut(BaseModel):
    student_id: str
    #: Toutes les compétences travaillées, de la moins à la mieux maîtrisée.
    competences: list[MasteryEntryOut]
    #: Les compétences à retravailler en priorité (jamais celles non tentées).
    weakest: list[MasteryEntryOut]
    badges: list[BadgeOut]
