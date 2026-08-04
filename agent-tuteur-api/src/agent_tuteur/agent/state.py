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
from agent_tuteur.agent.ports import AuditLogPort, MasteryPort, StudentMemoryPort
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
    #: Tours précédents de la conversation ([{"role": "user"|"assistant", "content": str}, ...]),
    #: chargés depuis la persistance par l'appelant (ex. chat.py) — vide pour un 1er tour.
    conversation_history: list[dict[str, str]]
    #: État du cours reconstruit du dernier tour ({"chapitre", "section_index"}),
    #: ou None si le tour précédent n'était pas en mode cours. Alimente detect_intent
    #: (continuité de session) puis course_planner (progression).
    course_state: dict[str, Any] | None

    #: Port de maîtrise, injecté par requête comme ``memory_port``/``audit_port``.
    mastery_port: MasteryPort | None
    #: Résultat d'un exercice ou d'un quiz corrigé, posé par la route
    #: d'évaluation. C'est la **seule** chose qui autorise la mise à jour de la
    #: maîtrise : un simple tour de chat ne prouve rien.
    exercise_outcome: dict[str, Any] | None

    # --- Intention (nœud detect_intent) ---
    intent: str  # "exercice" | "cours" | "quiz"
    intent_nav: str | None  # navigation cours détectée ("start"|"next"|"prev"|"goto")

    # --- Produits des nœuds a→e ---
    retrieved: list[ScoredChunk]
    #: Mode cours uniquement : le corpus a-t-il fourni du cours, ou seulement
    #: des TD et exercices ? Quand c'est faux, le prompt interdit explicitement
    #: d'inventer le cours manquant (cf. ``prompt.assemble_course_prompt``).
    has_course: bool
    frustration_score: float
    repetitions: int
    markers: int
    hint_level: int
    hint_label: str
    hint_reason: str
    tool_used: str | None
    tool_result: str | None
    moderation_flagged: bool
    #: Position dans le cours calculée par course_planner ({"chapitre", "section_index",
    #: "section_key", "section_title", "reason", "chapitre_confirmed", "alternatives",
    #: "topic"}) — présent uniquement en mode cours. ``chapitre_confirmed`` est faux
    #: quand la demande de l'élève n'a matché aucun chapitre du corpus : le prompt
    #: bascule alors en posture prudente au lieu de substituer un autre chapitre.
    course_section: dict[str, Any]
    #: Branche quiz : sur quoi interroger, et sous quelle forme.
    quiz_competence: str
    quiz_type: str
    system_prompt: str
    final_prompt: str
    trace: dict[str, Any]

    # --- Produit du nœud f ---
    answer: str

    # --- Produits des nœuds terminaux (graphe complet uniquement) ---
    #: Résultat des contrôles déterministes ({"valide": bool, "problemes": [...]}).
    verification: dict[str, Any]
    #: Quiz validé et prêt à l'affichage — vide si le modèle a échoué.
    quiz: dict[str, Any]
    #: Nouvel état de maîtrise, si ce tour l'a fait évoluer.
    mastery: dict[str, Any]

    # --- Diagnostic interne (reducer additif) ---
    node_trace: Annotated[list[dict], operator.add]
