"""Schémas Pydantic des requêtes/réponses de l'API (couche transport uniquement).

Ces modèles ne dupliquent pas ``CurriculumMetadata`` : le contexte curriculaire
d'une requête est un simple ``dict[str, str]`` transmis tel quel au retriever
(qui applique déjà l'expansion d'alias de série).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    student_id: str = Field(min_length=1, max_length=128)
    conversation_id: str | None = None
    curriculum_context: dict[str, str] = Field(default_factory=dict)


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
