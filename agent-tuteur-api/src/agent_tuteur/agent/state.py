"""État partagé du graphe LangGraph.

Chaque nœud reçoit l'état et renvoie une mise à jour partielle. Le champ
``node_trace`` utilise un *reducer* additif : chaque nœud y ajoute un petit
événement de diagnostic interne, et LangGraph concatène (à ne pas confondre
avec ``audit_port``, le journal de traçabilité pédagogique persistant).

``memory_port``/``audit_port`` sont injectés par requête (ex. repositories
Postgres liés à la session de la requête FastAPI) plutôt que figés à la
construction de l'agent — un seul ``TutorAgent``/graphe compilé sert toutes les
requêtes concurrentes sans jamais partager d'état entre elles.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.ports import AuditLogPort, StudentMemoryPort
from agent_tuteur.domain.models import ScoredChunk


class AgentState(TypedDict, total=False):
    # --- Entrées ---
    question: str
    curriculum_context: dict[str, Any]
    session: SessionState
    memory_port: StudentMemoryPort | None
    audit_port: AuditLogPort | None
    #: Corrélation logs/trace pour tout le tour (généré par prepare()/respond()).
    trace_id: str

    # --- Produits des nœuds a→e ---
    retrieved: list[ScoredChunk]
    frustration_score: float
    repetitions: int
    markers: int
    hint_level: int
    hint_label: str
    hint_reason: str
    tool_used: str | None
    tool_result: str | None
    moderation_flagged: bool
    system_prompt: str
    final_prompt: str
    trace: dict[str, Any]

    # --- Produit du nœud f ---
    answer: str

    # --- Diagnostic interne (reducer additif) ---
    node_trace: Annotated[list[dict], operator.add]
