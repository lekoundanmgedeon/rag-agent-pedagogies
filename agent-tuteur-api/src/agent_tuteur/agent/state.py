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

    # --- Triage de sécurité (nœud triage_securite, en tête de graphe) ---
    #: Signal de détresse détecté ({"motif", "categorie"}), ou ``None``. Quand il
    #: est posé, le graphe est dérouté vers ``reponse_securite`` : ni RAG, ni
    #: intention, ni cours, ni génération (règle non-négociable n°1).
    securite: dict[str, Any] | None
    #: Réponse écrite par le code plutôt que produite par le modèle. Quand elle
    #: est posée, ``compose_response`` est contourné et ``stream()`` la restitue
    #: telle quelle, sans jamais solliciter le LLM.
    reponse_directe: str | None

    # --- Intention (nœud detect_intent) ---
    intent: str  # "exercice" | "cours" | "quiz"
    intent_nav: str | None  # navigation cours détectée ("start"|"next"|"prev"|"goto")

    # --- Produits des nœuds a→e ---
    retrieved: list[ScoredChunk]
    #: Mode cours uniquement : le corpus a-t-il fourni du cours, ou seulement
    #: des TD et exercices ? Quand c'est faux, le prompt interdit explicitement
    #: d'inventer le cours manquant (cf. ``prompt.assemble_course_prompt``).
    has_course: bool
    #: Aucun extrait n'a survécu à la recherche : soit le seuil de pertinence a
    #: tout écarté, soit le cadre curriculaire ne couvre pas le sujet. Le prompt
    #: fait alors dire à l'agent qu'il n'a pas ce chapitre, au lieu de répondre
    #: sur des extraits étrangers (cas QA #5, règle non-négociable n°4).
    hors_perimetre: bool
    frustration_score: float
    repetitions: int
    markers: int
    #: L'élève a signalé lui-même que l'explication a déjà été donnée. Distinct
    #: de ``repetitions``, qui est observé par comparaison des questions
    #: récentes : ici c'est l'élève qui l'énonce (cas QA #20).
    blocage_declare: bool
    hint_level: int
    hint_label: str
    hint_reason: str
    #: Étude de fonction vérifiée par SymPy (domaine, dérivée, limites,
    #: variations), quand l'élève en a demandé une. ``None`` sinon — y compris
    #: quand la demande était bien une étude mais que rien n'a pu être établi :
    #: on ne remplit pas le vide (cas QA #9, règle n°2).
    etude_fonction: dict | None
    #: Éléments vérifiés d'un nombre complexe défini par l'énoncé (cas QA #6).
    complexe: dict | None
    tool_used: str | None
    tool_result: str | None
    #: Le résultat seul (sans « expression → »), pour le contrôle de fidélité
    #: de ``verify.py`` : c'est cette valeur-là que la réponse doit contenir.
    tool_result_brut: str | None
    #: Vrai quand l'élève demandait un calcul concret que l'outil symbolique n'a
    #: pas pu vérifier. Le prompt interdit alors d'annoncer un résultat plutôt
    #: que de laisser le modèle en inventer un (règle non-négociable n°2).
    calcul_non_verifie: bool
    #: Verdict symbolique sur une affirmation mathématique de l'élève
    #: ({"operation", "sujet", "affirme", "attendu", "correcte"}), ou ``None``
    #: si rien de vérifiable n'a été détecté. Quand l'affirmation est fausse, le
    #: prompt impose une correction explicite (cas QA #15) : ne rien dire
    #: laisserait l'erreur s'installer, et la réfuter sans vérification
    #: violerait la règle n°2.
    affirmation_eleve: dict[str, Any] | None
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
