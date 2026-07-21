"""Graphe LangGraph de l'agent tuteur (6 nœuds séquentiels) + façade — async.

```
a. retrieve_context   → RAG hybride filtré
b. detect_frustration → répétition + marqueurs (session éphémère)
c. diagnose_hint_level→ échelle 0-4
d. route_tool         → SymPy si calcul détecté
e. guardrail          → modération + assemblage du prompt (application de l'indice)
f. compose_response   → génération LLM finale
```

**Découpage streaming.** Deux graphes compilés partagent les mêmes fonctions de
nœud : le graphe *complet* (a→f) sert aux appels non-streamés (tests, démo) ; le
graphe de *préparation* (a→e) est invoqué par ``prepare()`` pour obtenir le prompt
final assemblé **sans** lancer la génération — l'API streame ensuite le LLM à part.

**Async.** Tous les nœuds sont des coroutines et les graphes sont invoqués via
``ainvoke`` : le retriever (I/O réseau si Qdrant), le LLM et les ports mémoire/
audit (I/O PostgreSQL) ne bloquent jamais la boucle événementielle FastAPI.

**Ports par requête.** ``memory``/``audit`` peuvent être fournis à la
construction (démo, tests, in-memory) OU passés à chaque appel de
``prepare``/``respond`` (API : repositories Postgres liés à la session de la
requête). Un seul ``TutorAgent``/graphe compilé sert alors toutes les requêtes
concurrentes, chacune avec sa propre session DB, sans état partagé entre elles.

**Observabilité.** Chaque nœud est chronométré et loggé (JSON structuré, cf.
``observability.py``) sous un ``trace_id`` unique par tour, qui permet de
reconstituer tout le fil d'exécution d'une question dans les logs. Le détail
(nom du nœud, durée, sortie clé) est aussi accumulé dans ``node_trace`` et
exposé sur ``Prepared`` — c'est ce qu'affiche l'onglet « orchestration » du
frontend Streamlit et ce qui est persisté dans ``messages.trace``.
"""

from __future__ import annotations

import functools
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field

from langgraph.graph import END, START, StateGraph

from agent_tuteur.agent.course_plan import (
    CoursePosition,
    advance,
    plan_titles,
    resolve_chapitre,
)
from agent_tuteur.agent.frustration import SessionState, detect_frustration
from agent_tuteur.agent.guardrails import clamp_hint_level, moderate, sanitize
from agent_tuteur.agent.hint_strategy import (
    HINT_INSTRUCTIONS,
    HINT_LABELS,
    HintDecision,
    diagnose_hint_level,
)
from agent_tuteur.agent.intent import Intent, Navigation, classify_intent
from agent_tuteur.agent.llm.base import BaseLLM
from agent_tuteur.agent.ports import AuditLogPort, StudentMemoryPort
from agent_tuteur.agent.prompt import assemble_course_prompt, assemble_prompt
from agent_tuteur.agent.state import AgentState
from agent_tuteur.domain.models import ScoredChunk
from agent_tuteur.observability import get_logger, log_event
from agent_tuteur.tools.calculator import CalculationError, compute, looks_like_calculation
from agent_tuteur.vectorstore.retriever import HybridRetriever

_logger = get_logger("agent_tuteur.agent.graph")

#: Nombre d'échanges (paires élève/tuteur) réinjectés dans la requête de recherche.
_HISTORY_EXCHANGES_FOR_RETRIEVAL = 3


def _condense_retrieval_query(question: str, history: list[dict]) -> str:
    """Ancre la requête de recherche sur le fil de la conversation en cours.

    Une relance courte de l'élève ("un autre indice ?") ne contient aucun terme
    mathématique exploitable pour l'embedding : seule, elle ramène les chunks
    les plus proches dans l'espace vectoriel quel que soit leur sujet réel. On
    y réinjecte donc les questions précédentes de l'élève (pas les réponses du
    tuteur, pour ne pas renforcer une dérive déjà hors-sujet).
    """
    if not history:
        return question
    recent = history[-_HISTORY_EXCHANGES_FOR_RETRIEVAL * 2 :]
    prior_questions = " ".join(m["content"] for m in recent if m.get("role") == "user")
    return f"{prior_questions} {question}".strip() if prior_questions else question


_MODERATION_OVERRIDE = (
    "IMPORTANT : la question de l'élève aborde un sujet inapproprié pour un cadre "
    "scolaire. Décline avec bienveillance, n'entre pas dans le détail, et invite "
    "l'élève à en parler à un adulte de confiance ou à son enseignant."
)


def _timed_node(name: str) -> Callable:
    """Chronomètre un nœud, logge l'événement, et horodate son ``node_trace``.

    Chaque nœud décoré doit renvoyer un dict contenant ``"node_trace": [{...}]``
    (une seule entrée) — le décorateur y injecte ``duration_ms``/``trace_id``
    et émet le log structuré correspondant, sans dupliquer ce code dans
    chaque nœud.
    """

    def decorator(fn: Callable[..., Awaitable[dict]]) -> Callable[..., Awaitable[dict]]:
        @functools.wraps(fn)
        async def wrapper(self: "TutorAgent", state: AgentState) -> dict:
            t0 = time.perf_counter()
            result = await fn(self, state)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            trace_id = state.get("trace_id")
            entries = result.get("node_trace", [])
            for entry in entries:
                entry["duration_ms"] = duration_ms
                entry.setdefault("trace_id", trace_id)
            extra = {k: v for k, v in (entries[0] if entries else {}).items() if k not in ("trace_id",)}
            log_event(_logger, f"node:{name}", trace_id=trace_id, **extra)
            return result

        return wrapper

    return decorator


@dataclass
class Prepared:
    """Résultat des nœuds a→e : tout le nécessaire pour streamer la génération."""

    question: str
    system_prompt: str
    final_prompt: str
    trace: dict
    retrieved: list[ScoredChunk]
    session: SessionState
    curriculum_context: dict = field(default_factory=dict)
    #: Port mémoire capturé au moment de prepare() ; réutilisé par commit_memory()
    #: pour écrire dans le MÊME store (ex. session Postgres de la requête).
    memory: StudentMemoryPort | None = None
    #: Identifiant de corrélation du tour (logs + trace persistée).
    trace_id: str = ""
    #: Détail nœud-par-nœud des étapes a→e (nom, durée, sortie clé).
    node_trace: list[dict] = field(default_factory=list)
    #: Rempli par stream() une fois la génération terminée (durée, tokens, fournisseur LLM).
    generation: dict | None = None

    @property
    def hint_level(self) -> int:
        return self.trace["hint_level"]

    @property
    def hint_label(self) -> str:
        return self.trace["hint_label"]


@dataclass
class AgentResult:
    """Résultat d'un tour complet (a→f)."""

    answer: str
    trace: dict
    retrieved: list[ScoredChunk]
    trace_id: str = ""
    node_trace: list[dict] = field(default_factory=list)

    @property
    def hint_level(self) -> int:
        return self.trace["hint_level"]

    @property
    def hint_label(self) -> str:
        return self.trace["hint_label"]


class TutorAgent:
    """Façade du cœur agent : orchestre le graphe et expose prepare/stream/respond."""

    def __init__(
        self,
        retriever: HybridRetriever,
        llm: BaseLLM,
        *,
        memory: StudentMemoryPort | None = None,
        audit: AuditLogPort | None = None,
        top_k: int = 5,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._memory = memory
        self._audit = audit
        self._top_k = top_k
        self._prep_graph = self._build_graph(include_compose=False)
        self._full_graph = self._build_graph(include_compose=True)

    @property
    def llm_chain(self) -> list[str]:
        """Chaîne de fallback LLM effective (exposée pour ``GET /health``)."""
        return self._llm.chain

    @property
    def last_llm_used(self) -> str | None:
        """Fournisseur LLM ayant effectivement servi le dernier appel."""
        return getattr(self._llm, "last_used", None) or self._llm.name

    # ------------------------------------------------------------------ nœuds
    @_timed_node("detect_intent")
    async def _n_detect_intent(self, state: AgentState) -> dict:
        in_course = bool(state.get("course_state"))
        decision = classify_intent(state["question"], in_course=in_course)
        nav = decision.navigation.value if decision.navigation else None
        return {
            "intent": decision.intent.value,
            "intent_nav": nav,
            "node_trace": [{"node": "detect_intent", "intent": decision.intent.value, "nav": nav}],
        }

    @_timed_node("retrieve_context")
    async def _n_retrieve(self, state: AgentState) -> dict:
        query = _condense_retrieval_query(state["question"], state.get("conversation_history", []))
        retrieved = self._retriever.retrieve(
            query, state.get("curriculum_context", {}), top_k=self._top_k
        )
        return {
            "retrieved": retrieved,
            "node_trace": [{"node": "retrieve_context", "n_sources": len(retrieved)}],
        }

    @_timed_node("detect_frustration")
    async def _n_frustration(self, state: AgentState) -> dict:
        session = state.get("session") or SessionState()
        signal = detect_frustration(state["question"], session)
        session.add(state["question"])  # mémoire de session (éphémère)
        return {
            "frustration_score": signal.score,
            "repetitions": signal.repetitions,
            "markers": signal.markers,
            "node_trace": [{"node": "detect_frustration", "score": signal.score}],
        }

    @_timed_node("diagnose_hint_level")
    async def _n_hint(self, state: AgentState) -> dict:
        decision = diagnose_hint_level(
            state["question"], state.get("frustration_score", 0.0), state.get("repetitions", 0)
        )
        return {
            "hint_level": decision.level,
            "hint_label": decision.label,
            "hint_reason": decision.reason,
            "node_trace": [{"node": "diagnose_hint_level", "level": decision.level}],
        }

    @_timed_node("route_tool")
    async def _n_route_tool(self, state: AgentState) -> dict:
        question = state["question"]
        tool_used: str | None = None
        tool_result: str | None = None
        if looks_like_calculation(question):
            try:
                res = compute(question)
                tool_used = "sympy_calculator"
                tool_result = f"{res.expression} → {res.result}"
            except CalculationError:
                tool_used = None  # échec silencieux : on laisse le LLM gérer.
        return {
            "tool_used": tool_used,
            "tool_result": tool_result,
            "node_trace": [{"node": "route_tool", "tool_used": tool_used}],
        }

    @_timed_node("guardrail")
    async def _n_guardrail(self, state: AgentState) -> dict:
        question = state["question"]
        ctx = state.get("curriculum_context", {})
        retrieved = state.get("retrieved", [])
        moderation = moderate(question)

        level = clamp_hint_level(state.get("hint_level", 1))
        decision = HintDecision(
            level=level,
            label=HINT_LABELS[level],
            instruction=HINT_INSTRUCTIONS[level],
            reason=state.get("hint_reason", ""),
        )
        system, user_prompt = assemble_prompt(
            question, decision, retrieved, state.get("tool_result"), ctx,
            state.get("conversation_history", []),
        )
        if moderation.flagged:
            user_prompt = f"{_MODERATION_OVERRIDE}\n\n{user_prompt}"

        competence = _competence_from_context(ctx, retrieved)
        trace = {
            "trace_id": state.get("trace_id"),
            "hint_level": level,
            "hint_label": HINT_LABELS[level],
            "hint_reason": decision.reason,
            "frustration_score": state.get("frustration_score", 0.0),
            "tool_used": state.get("tool_used"),
            "competence": competence,
            "course": None,
            "sources": _sources_payload(retrieved),
            "scores": [sc.score for sc in retrieved],
        }
        await self._write_audit(state, trace)
        return {
            "system_prompt": system,
            "final_prompt": user_prompt,
            "moderation_flagged": moderation.flagged,
            "trace": trace,
            "node_trace": [{"node": "guardrail", "moderation_flagged": moderation.flagged}],
        }

    # ------------------------------------------------------------ branche cours
    @_timed_node("course_planner")
    async def _n_course_planner(self, state: AgentState) -> dict:
        ctx = state.get("curriculum_context", {})
        retrieved = state.get("retrieved", [])
        nav_raw = state.get("intent_nav")
        navigation = Navigation(nav_raw) if nav_raw else None
        # Le chapitre est lié à la DEMANDE de l'élève, pas au meilleur extrait ;
        # un contexte curriculaire explicite reste prioritaire (l'élève a choisi).
        binding = resolve_chapitre(
            state["question"], [sc.chunk.metadata.chapitre for sc in retrieved]
        )
        position = advance(
            state.get("course_state"), navigation, state["question"],
            chapitre_fallback=ctx.get("chapitre"),
            binding=binding,
        )
        section = position.section
        course_section = {
            "chapitre": position.chapitre,
            "section_index": position.section_index,
            "section_key": section.key,
            "section_title": section.title,
            "reason": position.reason,
            "chapitre_confirmed": position.chapitre_confirmed,
            "alternatives": list(position.alternatives),
            "topic": position.topic,
        }
        # Un cours ne doit pas piocher dans les autres chapitres remontés par le
        # RAG : on restreint les extraits au chapitre enseigné (sauf si cela ne
        # laisse rien, auquel cas mieux vaut un contexte large que pas de contexte).
        focused = _focus_on_chapitre(retrieved, position.chapitre)
        return {
            "retrieved": focused,
            "course_section": course_section,
            "node_trace": [
                {"node": "course_planner", "section": section.key,
                 "section_index": position.section_index,
                 "chapitre": position.chapitre,
                 "chapitre_confirmed": position.chapitre_confirmed,
                 "n_sources_focused": len(focused)}
            ],
        }

    @_timed_node("guardrail_course")
    async def _n_guardrail_course(self, state: AgentState) -> dict:
        question = state["question"]
        ctx = state.get("curriculum_context", {})
        retrieved = state.get("retrieved", [])
        cs = state["course_section"]
        moderation = moderate(question)

        position = CoursePosition(
            chapitre=cs["chapitre"],
            section_index=cs["section_index"],
            reason=cs.get("reason", ""),
            chapitre_confirmed=cs.get("chapitre_confirmed", True),
            alternatives=tuple(cs.get("alternatives", ())),
            topic=cs.get("topic", ""),
        )
        system, user_prompt = assemble_course_prompt(
            question, position, retrieved, ctx, state.get("conversation_history", []),
        )
        if moderation.flagged:
            user_prompt = f"{_MODERATION_OVERRIDE}\n\n{user_prompt}"

        competence = _competence_from_context(ctx, retrieved)
        trace = {
            "trace_id": state.get("trace_id"),
            # Pas de niveau d'indice en mode cours : on conserve les clés du
            # contrat (meta/logs/frontend) avec des valeurs adaptées.
            "hint_level": None,
            "hint_label": "Cours",
            "hint_reason": cs.get("reason", ""),
            "frustration_score": 0.0,
            "tool_used": None,
            "competence": competence,
            "course": {
                "chapitre": cs["chapitre"],
                "section_index": cs["section_index"],
                "section_key": cs["section_key"],
                "section_title": cs["section_title"],
                # Faux quand la demande de l'élève n'a matché aucun chapitre du
                # corpus : le tour suivant hérite ainsi de la posture prudente.
                "chapitre_confirmed": cs.get("chapitre_confirmed", True),
                "plan": plan_titles(),
            },
            "sources": _sources_payload(retrieved),
            "scores": [sc.score for sc in retrieved],
        }
        await self._write_audit(state, trace)
        return {
            "system_prompt": system,
            "final_prompt": user_prompt,
            "moderation_flagged": moderation.flagged,
            "trace": trace,
            "node_trace": [{"node": "guardrail_course", "moderation_flagged": moderation.flagged}],
        }

    @_timed_node("compose_response")
    async def _n_compose(self, state: AgentState) -> dict:
        answer = await self._llm.generate(state["final_prompt"], system=state.get("system_prompt"))
        await self._write_memory(state)
        return {"answer": answer, "node_trace": [{"node": "compose_response", "chars": len(answer)}]}

    # ------------------------------------------------------------ persistance
    async def _write_audit(self, state: AgentState, trace: dict) -> None:
        audit = state.get("audit_port") or self._audit
        if audit is None:
            return
        session = state.get("session") or SessionState()
        await audit.log(
            {
                "student_id": session.student_id,
                "tenant_id": session.tenant_id,
                "question": state["question"],
                "created_at": time.time(),
                **trace,
            }
        )

    async def _write_memory(self, state: AgentState, memory: StudentMemoryPort | None = None) -> None:
        memory = memory or state.get("memory_port") or self._memory
        if memory is None:
            return
        session = state.get("session") or SessionState()
        trace = state.get("trace", {})
        await memory.record(
            {
                "student_id": session.student_id,
                "tenant_id": session.tenant_id,
                "competence": trace.get("competence"),
                "hint_level": trace.get("hint_level"),
                "question": state["question"],
                "created_at": time.time(),
            }
        )

    # ---------------------------------------------------------------- graphes
    def _build_graph(self, *, include_compose: bool):
        """Graphe commun aux deux postures, aiguillé après ``retrieve_context``.

        ``detect_intent`` classe le tour ; la recherche RAG est partagée ; puis
        un edge conditionnel envoie vers la branche **exercice** (socratique,
        inchangée) ou **cours** (didactique). Les deux branches convergent sur
        ``compose_response`` (graphe complet) ou ``END`` (graphe de préparation).
        """
        g = StateGraph(AgentState)
        g.add_node("detect_intent", self._n_detect_intent)
        g.add_node("retrieve_context", self._n_retrieve)
        # Branche exercice (posture socratique) — inchangée.
        g.add_node("detect_frustration", self._n_frustration)
        g.add_node("diagnose_hint_level", self._n_hint)
        g.add_node("route_tool", self._n_route_tool)
        g.add_node("guardrail", self._n_guardrail)
        # Branche cours (posture didactique).
        g.add_node("course_planner", self._n_course_planner)
        g.add_node("guardrail_course", self._n_guardrail_course)

        g.add_edge(START, "detect_intent")
        g.add_edge("detect_intent", "retrieve_context")
        g.add_conditional_edges(
            "retrieve_context",
            _route_by_intent,
            {"exercice": "detect_frustration", "cours": "course_planner"},
        )
        g.add_edge("detect_frustration", "diagnose_hint_level")
        g.add_edge("diagnose_hint_level", "route_tool")
        g.add_edge("route_tool", "guardrail")
        g.add_edge("course_planner", "guardrail_course")

        if include_compose:
            g.add_node("compose_response", self._n_compose)
            g.add_edge("guardrail", "compose_response")
            g.add_edge("guardrail_course", "compose_response")
            g.add_edge("compose_response", END)
        else:
            g.add_edge("guardrail", END)
            g.add_edge("guardrail_course", END)
        return g.compile()

    # --------------------------------------------------------- API publique
    async def prepare(
        self,
        question: str,
        curriculum_context: dict | None = None,
        session: SessionState | None = None,
        *,
        memory: StudentMemoryPort | None = None,
        audit: AuditLogPort | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        course_state: dict | None = None,
    ) -> Prepared:
        """Exécute a→e et renvoie le prompt final **sans** générer.

        ``sanitize`` (anti-injection) est appliqué en tout premier : une entrée
        malveillante lève ``PromptInjectionError`` avant tout traitement.
        ``memory``/``audit`` permettent d'injecter des ports liés à la requête
        (ex. repositories Postgres d'une session FastAPI) ; à défaut, les ports
        fournis à la construction de l'agent sont utilisés. ``conversation_history``
        (tours précédents, chargés par l'appelant depuis la persistance) ancre la
        recherche RAG et le prompt sur le fil de la conversation en cours.
        ``course_state`` (position dans un cours au tour précédent, reconstruite
        par l'appelant depuis ``trace['course']``) active la continuité du mode
        cours ; ``None`` si le tour précédent n'était pas un cours.
        """
        clean = sanitize(question)
        session = session or SessionState()
        trace_id = str(uuid.uuid4())
        state: AgentState = {
            "question": clean,
            "curriculum_context": curriculum_context or {},
            "session": session,
            "audit_port": audit,
            "trace_id": trace_id,
            "node_trace": [],
            "conversation_history": conversation_history or [],
            "course_state": course_state,
        }
        log_event(
            _logger, "turn:start", trace_id=trace_id, student_id=session.student_id,
            tenant_id=session.tenant_id, question_len=len(clean),
        )
        result = await self._prep_graph.ainvoke(state)
        return Prepared(
            question=clean,
            system_prompt=result["system_prompt"],
            final_prompt=result["final_prompt"],
            trace=result["trace"],
            retrieved=result.get("retrieved", []),
            session=session,
            curriculum_context=curriculum_context or {},
            memory=memory or self._memory,
            trace_id=trace_id,
            node_trace=result.get("node_trace", []),
        )

    async def stream(self, prepared: Prepared) -> AsyncIterator[str]:
        """Streame la génération finale à partir d'un prompt préparé.

        Une fois le flux épuisé, ``prepared.generation`` est rempli (durée,
        nombre de tokens, fournisseur LLM effectif) — lu par l'appelant après
        la boucle ``async for`` pour compléter la trace persistée.
        """
        t0 = time.perf_counter()
        token_count = 0
        async for token in self._llm.generate_stream(
            prepared.final_prompt, system=prepared.system_prompt
        ):
            token_count += 1
            yield token
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        prepared.generation = {
            "node": "compose_response",
            "duration_ms": duration_ms,
            "token_count": token_count,
            "llm_provider": self.last_llm_used,
        }
        log_event(
            _logger, "node:compose_response_stream", trace_id=prepared.trace_id,
            duration_ms=duration_ms, token_count=token_count, llm_provider=self.last_llm_used,
        )

    async def commit_memory(self, prepared: Prepared) -> None:
        """Persiste le résultat notable (à appeler après un stream réussi)."""
        await self._write_memory(
            {
                "question": prepared.question,
                "session": prepared.session,
                "trace": prepared.trace,
            },
            memory=prepared.memory,
        )

    async def respond(
        self,
        question: str,
        curriculum_context: dict | None = None,
        session: SessionState | None = None,
        *,
        memory: StudentMemoryPort | None = None,
        audit: AuditLogPort | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        course_state: dict | None = None,
    ) -> AgentResult:
        """Tour complet non-streamé (a→f) — pratique pour tests et démo."""
        clean = sanitize(question)
        session = session or SessionState()
        trace_id = str(uuid.uuid4())
        state: AgentState = {
            "question": clean,
            "curriculum_context": curriculum_context or {},
            "session": session,
            "memory_port": memory,
            "audit_port": audit,
            "trace_id": trace_id,
            "node_trace": [],
            "conversation_history": conversation_history or [],
            "course_state": course_state,
        }
        log_event(
            _logger, "turn:start", trace_id=trace_id, student_id=session.student_id,
            tenant_id=session.tenant_id, question_len=len(clean),
        )
        result = await self._full_graph.ainvoke(state)
        return AgentResult(
            answer=result["answer"],
            trace=result["trace"],
            retrieved=result.get("retrieved", []),
            trace_id=trace_id,
            node_trace=result.get("node_trace", []),
        )


def _route_by_intent(state: AgentState) -> str:
    """Aiguillage conditionnel après ``retrieve_context`` (défaut : exercice)."""
    return "cours" if state.get("intent") == Intent.COURS.value else "exercice"


def _sources_payload(retrieved: list[ScoredChunk]) -> list[dict]:
    """Liste d'attribution des sources RAG (identique aux deux branches)."""
    return [
        {
            "id": sc.chunk.id,
            "label": sc.source_label,
            "type_chunk": sc.chunk.metadata.type_chunk,
            "score": sc.score,
        }
        for sc in retrieved
    ]


def _focus_on_chapitre(
    retrieved: list[ScoredChunk], chapitre: str | None
) -> list[ScoredChunk]:
    """Restreint les extraits au chapitre enseigné, si cela laisse de quoi travailler.

    Une requête « nombres complexes » remonte aussi des extraits d'arithmétique :
    les laisser dans le prompt d'un cours de complexes n'apporte que du bruit. On
    ne filtre jamais jusqu'au vide — sans extrait, le LLM n'a plus d'ancrage du tout.
    """
    if not chapitre:
        return retrieved
    focused = [sc for sc in retrieved if sc.chunk.metadata.chapitre == chapitre]
    return focused or retrieved


def _competence_from_context(ctx: dict, retrieved: list[ScoredChunk]) -> str | None:
    """Compétence mobilisée : celle du contexte, sinon du meilleur extrait."""
    if ctx.get("competence"):
        return ctx["competence"]
    for sc in retrieved:
        if sc.chunk.metadata.competence:
            return sc.chunk.metadata.competence
        if sc.chunk.metadata.chapitre:
            return sc.chunk.metadata.chapitre
    return None
