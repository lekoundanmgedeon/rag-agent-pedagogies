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
frontend web et ce qui est persisté dans ``messages.trace``.
"""

from __future__ import annotations

import functools
import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field

from langgraph.graph import END, START, StateGraph

from agent_tuteur.agent.course_plan import (
    CLE_SECTION_EXERCICES,
    CoursePosition,
    Section,
    advance,
    plan_titles,
    resolve_chapitre,
    section_par_cle,
    sources_absentes,
    texte_releve_de_la_section,
    titre_de_section,
    topic_label,
)
from agent_tuteur.agent.frustration import SessionState, detect_frustration
from agent_tuteur.agent.guardrails import clamp_hint_level, moderate, sanitize
from agent_tuteur.agent.hint_strategy import (
    HINT_INSTRUCTIONS,
    HINT_LABELS,
    HintDecision,
    ajuster_pour_simplification,
    diagnose_hint_level,
    escalade_pour_resultat_verifie,
)
from agent_tuteur.agent.intent import (
    Intent,
    Navigation,
    classify_intent,
    demande_le_catalogue,
    est_une_demande_ouverte,
)
from agent_tuteur.agent.llm.base import BaseLLM
from agent_tuteur.agent.ports import AuditLogPort, MasteryPort, StudentMemoryPort
from agent_tuteur.agent.profil import detecter_serie, serie_effective
from agent_tuteur.agent.prompt import (
    CONSIGNE_SOUTIEN_DEJA_ADRESSE,
    SYSTEM_PERSONA_QUIZ,
    assemble_accueil_prompt,
    assemble_course_prompt,
    assemble_exercise_prompt,
    assemble_meta_prompt,
    assemble_prompt,
    build_context_block,
    consigne_complexe,
    consigne_correction_affirmation,
    consigne_etude_de_fonction,
)
from agent_tuteur.agent.quiz import (
    Quiz,
    analyser_reponse_quiz,
    construire_prompt_quiz,
    contient_du_factice,
)
from agent_tuteur.agent.orientation import reponse_catalogue
from agent_tuteur.agent.securite import detecter_detresse, reponse_detresse
from agent_tuteur.agent.soutien import ouverture_pour
from agent_tuteur.agent.state import AgentState
from agent_tuteur.agent.verify import verifier_coherence_mathematique
from agent_tuteur.domain.models import ScoredChunk
from agent_tuteur.observability import get_logger, log_event
from agent_tuteur.textutil import strip_accents
from agent_tuteur.tools.affirmation import verifier_affirmation
from agent_tuteur.tools.complexe import analyser_la_demande as analyser_complexe_demande
from agent_tuteur.tools.etude_fonction import etudier_la_demande
from agent_tuteur.tools.calculator import (
    CalculationError,
    compute,
    demande_un_calcul_concret,
    est_un_calcul_trivial,
    looks_like_calculation,
)
from agent_tuteur.vectorstore.retriever import HybridRetriever

_logger = get_logger("agent_tuteur.agent.graph")

#: Nombre d'échanges (paires élève/tuteur) réinjectés dans la requête de recherche.
_HISTORY_EXCHANGES_FOR_RETRIEVAL = 3

#: Demande explicite d'un quiz vrai/faux plutôt que d'un QCM.
_VRAI_FAUX = re.compile(r"vrai\s*[/ou-]+\s*faux", re.IGNORECASE)


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


def _prefixer_consigne_de_soutien(user_prompt: str, state: AgentState) -> str:
    """Prévient le modèle qu'une ouverture de soutien a déjà été servie.

    Même patron que ``_MODERATION_OVERRIDE`` : une consigne en tête du prompt,
    posée après l'assemblage. Sans elle, le modèle ouvre à son tour sur de
    l'encouragement et l'élève reçoit deux préambules avant la moindre aide —
    le reproche du cas #19, déplacé d'un cran plutôt que corrigé.
    """
    if not state.get("soutien"):
        return user_prompt
    return f"{CONSIGNE_SOUTIEN_DEJA_ADRESSE}\n\n{user_prompt}"


def _timed_node(name: str) -> Callable:
    """Chronomètre un nœud, logge l'événement, et horodate son ``node_trace``.

    Chaque nœud décoré doit renvoyer un dict contenant ``"node_trace": [{...}]``
    (une seule entrée) — le décorateur y injecte ``duration_ms``/``trace_id``
    et émet le log structuré correspondant, sans dupliquer ce code dans
    chaque nœud.
    """

    def decorator(fn: Callable[..., Awaitable[dict]]) -> Callable[..., Awaitable[dict]]:
        @functools.wraps(fn)
        async def wrapper(self: TutorAgent, state: AgentState) -> dict:
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
    #: Réponse déjà écrite par le graphe (mise en sécurité). Quand elle est
    #: présente, ``stream()`` la restitue sans appeler le modèle.
    reponse_directe: str | None = None
    #: Ouverture de soutien à émettre **avant** la génération (cas #19/#21).
    #: À la différence de ``reponse_directe``, elle ne remplace pas le tour :
    #: le modèle est bien appelé ensuite, et prévenu par sa consigne.
    preambule_soutien: str | None = None

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
    #: Prompt réellement assemblé pour ce tour. Symétrique de ``Prepared``, qui
    #: le portait déjà : c'est du texte produit par le code, donc la seule
    #: matière assérable d'un tour complet — la prose du modèle, elle, ne l'est
    #: pas. Vide sur un tour court-circuité (mise en sécurité).
    final_prompt: str = ""
    #: Produits des nœuds terminaux (graphe complet uniquement).
    verification: dict | None = None
    #: Quiz validé, présent uniquement pour un tour d'intention « quiz ».
    #: ``questions`` vide signifie que le modèle n'a rien produit d'exploitable.
    quiz: dict | None = None
    #: Nouvel état de maîtrise, si ce tour l'a fait évoluer.
    mastery: dict | None = None

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
        mastery: MasteryPort | None = None,
        top_k: int = 5,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._memory = memory
        self._audit = audit
        self._mastery = mastery
        self._top_k = top_k
        self._prep_graph = self._build_graph(include_compose=False)
        self._full_graph = self._build_graph(include_compose=True)

    @property
    def llm(self) -> BaseLLM:
        """Modèle de langage utilisé par l'agent.

        Exposé pour les usages hors graphe qui ont besoin de la **même** chaîne
        de repli que le chat — la génération de quiz, par exemple.
        """
        return self._llm

    @property
    def llm_chain(self) -> list[str]:
        """Chaîne de fallback LLM effective (exposée pour ``GET /health``)."""
        return self._llm.chain

    @property
    def last_llm_used(self) -> str | None:
        """Fournisseur LLM ayant effectivement servi le dernier appel."""
        return getattr(self._llm, "last_used", None) or self._llm.name

    # ------------------------------------------------- branche sécurité (n°1)
    @_timed_node("triage_securite")
    async def _n_triage_securite(self, state: AgentState) -> dict:
        """Premier nœud du graphe : l'élève va-t-il bien ?

        Placé **avant** ``detect_intent`` pour que rien — ni la détection
        d'intention, ni le RAG, ni la continuité d'un cours — ne puisse prendre
        le pas sur un signal de détresse (règle non-négociable n°1).
        """
        signal = detecter_detresse(state["question"])
        if not signal.detectee:
            return {"securite": None, "node_trace": [{"node": "triage_securite", "detresse": False}]}
        return {
            "securite": {"motif": "detresse", "categorie": signal.nature.value},
            "node_trace": [
                {"node": "triage_securite", "detresse": True, "categorie": signal.nature.value}
            ],
        }

    @_timed_node("reponse_securite")
    async def _n_reponse_securite(self, state: AgentState) -> dict:
        """Réponse de mise en sécurité — écrite par le code, pas par le modèle.

        La trace produite porte les mêmes clés qu'un tour ordinaire : la route
        SSE (``api/routes/chat.py``) les lit sans garde, et un tour de détresse
        ne doit pas être le seul à faire tomber l'API.

        L'événement est journalisé dans l'audit (un établissement doit pouvoir
        savoir qu'un signalement a eu lieu) mais **pas** dans la mémoire élève,
        qui suit les compétences et les niveaux d'indice : une confidence n'y a
        rien à faire.
        """
        signal = state.get("securite") or {}
        nature = signal.get("categorie", "")
        reponse = reponse_detresse(detecter_detresse(state["question"]))
        trace = {
            "trace_id": state.get("trace_id"),
            "securite": signal,
            "hint_level": 0,
            "hint_label": HINT_LABELS[0],
            "hint_reason": "tour de mise en sécurité",
            "frustration_score": 0.0,
            "tool_used": None,
            "competence": None,
            "course": None,
            "sources": [],
            "scores": [],
        }
        await self._write_audit(state, trace)
        log_event(
            _logger, "securite:detresse_detectee",
            trace_id=state.get("trace_id"), categorie=nature,
        )
        return {
            "answer": reponse,
            "reponse_directe": reponse,
            "system_prompt": "",
            "final_prompt": "",
            "trace": trace,
            "retrieved": [],
            "node_trace": [{"node": "reponse_securite", "categorie": nature}],
        }

    # ------------------------------------------------------------------ nœuds
    @_timed_node("profil_eleve")
    async def _n_profil_eleve(self, state: AgentState) -> dict:
        """Résout la série applicable au tour — cas QA #8.

        Placé **avant** ``detect_intent``, donc en amont du retrieval et de
        tous les assembleurs de prompt : la série sert de filtre de recherche
        autant que de cadre annoncé à l'élève, et les deux doivent voir la même
        valeur. Le corriger plus bas laisserait la recherche tourner sur
        l'ancienne série.

        Une déclaration explicite écrase immédiatement l'état antérieur et la
        série du profil, pour tout le reste de la session (règle n°5). En
        l'absence de déclaration comme d'un profil, rien n'est écrit : le tour
        se déroule sans série plutôt qu'avec une série devinée (règle n°3).
        """
        session = state.get("session") or SessionState()
        contexte = dict(state.get("curriculum_context", {}))

        declaree = detecter_serie(state["question"])
        if declaree is not None:
            session.serie = declaree

        effective = serie_effective(session.serie, contexte)
        if effective is not None:
            contexte["serie"] = effective
        else:
            # Aucune source fiable : on retire la clé plutôt que de la laisser
            # vide, pour que les assembleurs de prompt n'annoncent aucun cadre.
            contexte.pop("serie", None)

        return {
            "curriculum_context": contexte,
            "node_trace": [{
                "node": "profil_eleve",
                "serie_declaree": declaree,
                "serie_effective": effective,
                "corrigee_par_eleve": session.serie is not None,
            }],
        }

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

    @_timed_node("soutien_eleve")
    async def _n_soutien(self, state: AgentState) -> dict:
        """L'élève se décourage : on dédramatise, puis le tour continue.

        **Placement.** Juste après ``detect_intent``, donc avant l'aiguillage
        vers les branches et avant toute recherche. Deux raisons, et la première
        est structurelle : le découragement est un état de l'**élève**, pas une
        propriété du sujet — le brancher sur la seule branche exercice (là où
        vit ``detect_frustration``) l'aurait rendu muet dès que l'élève se
        décourage pendant un cours, c'est-à-dire au moment où c'est le plus
        probable. La seconde est que l'intention est alors connue, ce qui permet
        d'exclure le seul tour où une ouverture serait nuisible.

        **Pourquoi le quiz est exclu.** La réponse d'un tour quiz n'est pas de la
        prose adressée à l'élève mais un JSON relu par ``analyser_reponse_quiz``.
        Y préfixer un paragraphe rendrait le quiz illisible, donc inutilisable —
        l'inverse du service rendu. Un élève découragé qui demande explicitement
        à être interrogé reçoit son quiz ; le soutien viendra au tour suivant.

        Le tour de détresse (``reponse_securite``) ne passe jamais ici : il sort
        du graphe avant, et son texte doit rester seul (règle n°1).
        """
        if state.get("intent") == Intent.QUIZ.value:
            return {"soutien": None, "preambule_soutien": None}
        session = state.get("session") or SessionState()
        ouverture = ouverture_pour(state["question"], session.ouvertures_soutien)
        if ouverture is None:
            return {
                "soutien": None,
                "preambule_soutien": None,
                "node_trace": [{"node": "soutien_eleve", "signal": None}],
            }
        # Mémoire de session, éphémère : c'est elle qui garantit que la prochaine
        # ouverture ne sera pas la même (cas #21).
        session.ouvertures_soutien.append(ouverture.variante)
        return {
            "soutien": ouverture.as_trace(),
            "preambule_soutien": ouverture.texte,
            "node_trace": [
                {
                    "node": "soutien_eleve",
                    "signal": ouverture.signal.value,
                    "variante": ouverture.variante,
                }
            ],
        }

    @_timed_node("retrieve_context")
    async def _n_retrieve(self, state: AgentState) -> dict:
        query = _condense_retrieval_query(state["question"], state.get("conversation_history", []))
        context = state.get("curriculum_context", {})

        # En mode cours, l'élève demande une explication : on cherche d'abord du
        # cours, et on ne joint des exercices qu'en complément. En mode
        # exercice, l'ordre du RRF convient tel quel — c'est justement les
        # énoncés et corrigés que l'on veut voir remonter.
        if state.get("intent") == Intent.COURS.value:
            resultats = self._retriever.retrieve_course_first(
                query, context, top_k=self._top_k
            )
            return {
                "retrieved": resultats.tous(),
                "has_course": resultats.a_du_cours,
                "hors_perimetre": not resultats.tous(),
                "node_trace": [{
                    "node": "retrieve_context",
                    "n_sources": len(resultats.tous()),
                    "n_course": len(resultats.cours),
                    "has_course": resultats.a_du_cours,
                    "hors_perimetre": not resultats.tous(),
                }],
            }

        retrieved = self._retriever.retrieve(query, context, top_k=self._top_k)
        return {
            "retrieved": retrieved,
            # Le corpus n'a rien à dire sur cette question : soit aucun extrait
            # n'a passé le seuil de pertinence, soit le cadre curriculaire ne
            # couvre pas le sujet. Pour l'élève, les deux se disent pareil — il
            # faut l'avouer plutôt que répondre sur des extraits étrangers
            # (cas QA #5, règle non-négociable n°4).
            "hors_perimetre": not retrieved,
            "node_trace": [{
                "node": "retrieve_context",
                "n_sources": len(retrieved),
                "hors_perimetre": not retrieved,
            }],
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
            "blocage_declare": signal.blocage_declare,
            "decouragement": signal.decouragement,
            "demande_simplification": signal.demande_simplification,
            "node_trace": [
                {"node": "detect_frustration", "score": signal.score,
                 "blocage_declare": signal.blocage_declare,
                 "decouragement": signal.decouragement,
                 "demande_simplification": signal.demande_simplification}
            ],
        }

    @_timed_node("diagnose_hint_level")
    async def _n_hint(self, state: AgentState) -> dict:
        decision = diagnose_hint_level(
            state["question"],
            state.get("frustration_score", 0.0),
            state.get("repetitions", 0),
            calcul_trivial=est_un_calcul_trivial(state["question"]),
            # Un élève qui annonce qu'il abandonne écrit court, mais pas flou :
            # sans cela « je laisse tomber » recevait la consigne de niveau 0,
            # « reformule la question de l'élève » (cas #21 croisé au #14).
            signal_de_soutien=bool(state.get("soutien")),
        )
        return {
            "hint_level": decision.level,
            "hint_label": decision.label,
            "hint_reason": decision.reason,
            "node_trace": [{"node": "diagnose_hint_level", "level": decision.level}],
        }

    @_timed_node("route_tool")
    async def _n_route_tool(self, state: AgentState) -> dict:
        """Calcul symbolique, ou aveu explicite qu'il n'a pas pu être fait.

        L'ancien comportement repliait *silencieusement* sur le LLM en cas
        d'échec : l'élève recevait alors un calcul produit par le modèle, sans
        que rien ne l'ait vérifié. La règle non-négociable n°2 l'interdit —
        quand l'outil ne peut pas garantir le résultat d'une demande de calcul
        concrète, on le signale (``calcul_non_verifie``) et le prompt interdit
        d'annoncer un résultat.

        Le silence reste la bonne réponse pour une question *conceptuelle*
        (« comment dériver un quotient ? ») : il n'y a aucun résultat à vérifier.
        """
        question = state["question"]
        tool_used: str | None = None
        tool_result: str | None = None
        tool_result_brut: str | None = None
        calcul_non_verifie = False
        if looks_like_calculation(question):
            try:
                res = compute(question)
                tool_used = "sympy_calculator"
                tool_result = f"{res.expression} → {res.result}"
                tool_result_brut = res.result
            except CalculationError:
                calcul_non_verifie = demande_un_calcul_concret(question)

        # Trajet inverse de la vérification ci-dessus : ce n'est plus ce que
        # l'agent s'apprête à dire qu'on contrôle, mais ce que l'élève vient
        # d'affirmer (cas QA #15). Indépendant de ``looks_like_calculation`` :
        # « la dérivée de ln(x) c'est bien 1/x² non ? » est une demande de
        # confirmation, pas une demande de calcul.
        verdict = verifier_affirmation(question)
        affirmation = None
        if verdict is not None:
            # Le contenu mathématique du tour A été vérifié symboliquement, même
            # si ``compute`` a renoncé : la phrase n'est pas une demande de
            # calcul, c'est une demande de confirmation. Laisser
            # ``calcul_non_verifie`` à vrai mettrait dans le prompt deux
            # consignes contradictoires — « n'annonce aucun résultat » et
            # « donne le résultat correct » — et la première ferait taire la
            # correction que le cas #15 exige précisément.
            calcul_non_verifie = False
            affirmation = {
                "operation": verdict.operation,
                "sujet": verdict.sujet,
                "affirme": verdict.affirme,
                "attendu": verdict.attendu,
                "correcte": verdict.correcte,
            }
            if verdict.a_corriger:
                log_event(
                    _logger, "affirmation:erreur_eleve", trace_id=state.get("trace_id"),
                    operation=verdict.operation, affirme=verdict.affirme, attendu=verdict.attendu,
                )
        # Troisième usage du calcul symbolique dans ce nœud, après la
        # vérification d'un calcul demandé et celle d'une affirmation de
        # l'élève : établir une étude de fonction complète. Le corpus ne peut
        # pas la fournir (aucune leçon indexée sur l'étude des fonctions), et la
        # laisser au modèle violerait la règle n°2 — elle est donc calculée.
        etude = etudier_la_demande(question)
        etude_fonction = None
        if etude is not None:
            etude_fonction = {
                "expression": etude.expression,
                "domaine": etude.domaine,
                "derivee": etude.derivee,
                "limites": [list(couple) for couple in etude.limites],
                "variations": [list(couple) for couple in etude.variations],
            }
            # Même raison qu'au verdict d'affirmation ci-dessus : le contenu
            # mathématique du tour A été vérifié. Garder l'avertissement
            # armé interdirait d'annoncer l'étude qu'on vient d'établir.
            calcul_non_verifie = False

        # Quatrième usage du calcul symbolique de ce nœud. Sans lui, l'exercice
        # le plus basique du chapitre le mieux couvert (« z = 3 + 4i ») armait
        # calcul_non_verifie : `i` n'étant pas l'unité imaginaire, `compute`
        # échouait et le prompt interdisait d'annoncer le moindre résultat.
        analyse = analyser_complexe_demande(question)
        complexe = None
        if analyse is not None:
            complexe = {
                "nom": analyse.nom,
                "forme": analyse.forme,
                "partie_reelle": analyse.partie_reelle,
                "partie_imaginaire": analyse.partie_imaginaire,
                "conjugue": analyse.conjugue,
                "module": analyse.module,
                "argument": analyse.argument,
            }
            calcul_non_verifie = False

        return {
            "tool_used": tool_used,
            "tool_result": tool_result,
            "tool_result_brut": tool_result_brut,
            "calcul_non_verifie": calcul_non_verifie,
            "affirmation_eleve": affirmation,
            "etude_fonction": etude_fonction,
            "complexe": complexe,
            "node_trace": [
                {"node": "route_tool", "tool_used": tool_used,
                 "calcul_non_verifie": calcul_non_verifie,
                 "etude_fonction": etude_fonction is not None,
                 "complexe": complexe is not None,
                 "affirmation_correcte": None if affirmation is None else affirmation["correcte"]}
            ],
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
        # Le niveau a été décidé deux nœuds plus tôt, avant que l'outil ait
        # tourné. C'est ici — et seulement ici — qu'on sait *à la fois* quelle
        # consigne va partir et si un résultat vérifié l'accompagne : le seul
        # endroit où la contradiction des cas #11 et #13 est visible.
        decision = escalade_pour_resultat_verifie(
            decision,
            resultat_verifie=state.get("tool_result") is not None,
            demande_concrete=demande_un_calcul_concret(question),
        )
        # Demande de reformulation simplifiée : la consigne de niveau 1
        # interdit explicitement l'exemple concret que l'élève réclame (cas #39).
        decision = ajuster_pour_simplification(
            decision, demande_simplification=bool(state.get("demande_simplification"))
        )
        etude = state.get("etude_fonction")
        complexe = state.get("complexe")
        # Une étude de fonction est un livrable, pas un indice : la même
        # contradiction que pour les cas #11/#13 s'y appliquait, en plus large.
        if etude:
            decision = escalade_pour_resultat_verifie(
                decision, resultat_verifie=True, demande_concrete=True
            )
        level = decision.level
        affirmation = state.get("affirmation_eleve")
        correction = None
        if affirmation is not None and not affirmation["correcte"]:
            correction = consigne_correction_affirmation(
                affirmation["operation"], affirmation["sujet"],
                affirmation["affirme"], affirmation["attendu"],
            )
        varier_approche = bool(state.get("blocage_declare"))
        simplifier = bool(state.get("demande_simplification"))
        system, user_prompt = assemble_prompt(
            question, decision, retrieved, state.get("tool_result"), ctx,
            state.get("conversation_history", []),
            calcul_non_verifie=bool(state.get("calcul_non_verifie")),
            correction_affirmation=correction,
            varier_approche=varier_approche,
            simplifier=simplifier,
            etude_fonction=consigne_etude_de_fonction(etude) if etude else None,
            complexe=consigne_complexe(complexe) if complexe else None,
        )
        if moderation.flagged:
            user_prompt = f"{_MODERATION_OVERRIDE}\n\n{user_prompt}"
        user_prompt = _prefixer_consigne_de_soutien(user_prompt, state)

        competence = _competence_from_context(ctx, retrieved)
        trace = {
            "trace_id": state.get("trace_id"),
            "hint_level": level,
            "hint_label": HINT_LABELS[level],
            "hint_reason": decision.reason,
            "frustration_score": state.get("frustration_score", 0.0),
            "blocage_declare": varier_approche,
            # Exposé à côté de ``blocage_declare`` et non fondu dedans : les
            # deux signaux appellent des consignes différentes, et la trace doit
            # dire lequel a joué (cas #20 contre cas #39).
            "demande_simplification": simplifier,
            # Exposé dans la trace pour que le signal du cas #19 soit lisible
            # là où il sera exploité (routage ou modulation de ton, D5 point 1)
            # plutôt que noyé dans le score agrégé.
            "decouragement": bool(state.get("decouragement")),
            # Ce que le découragement a effectivement produit (D5, point 1) :
            # l'ouverture servie, ou None. Le signal seul ne disait pas si
            # quelque chose en avait été fait.
            "soutien": state.get("soutien"),
            "etude_fonction": etude,
            "complexe": complexe,
            "tool_used": state.get("tool_used"),
            "tool_result": state.get("tool_result"),
            "calcul_non_verifie": bool(state.get("calcul_non_verifie")),
            "affirmation_eleve": affirmation,
            "competence": competence,
            "course": None,
            "hors_perimetre": bool(state.get("hors_perimetre")),
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

    # ------------------------------------------------------------- branche méta
    @_timed_node("guardrail_meta")
    async def _n_guardrail_meta(self, state: AgentState) -> dict:
        """Tour méta : on répond sur la couverture du service, sans chercher.

        Le nœud est branché **avant** ``retrieve_context`` : sur « quel est mon
        programme ? », une recherche par similarité remonte le chunk le moins
        éloigné du corpus, qui n'a aucun rapport (cas QA #2/#3/#4). L'ancrage
        factuel vient du catalogue du store, pas d'un classement.
        """
        ctx = state.get("curriculum_context", {})
        catalogue = self._retriever.catalogue(ctx)

        # Demande d'inventaire : la réponse est écrite par le code (cas QA #26).
        # Une liste de chapitres doit être exacte et **identique** d'un tour à
        # l'autre ; la faire reformuler à chaque fois était la cause directe des
        # « réponses de qualité variable » rapportées par la testeuse.
        inventaire = demande_le_catalogue(state["question"])
        ouverte = est_une_demande_ouverte(state["question"])
        system, user_prompt = assemble_meta_prompt(
            state["question"], catalogue, ctx, state.get("conversation_history", []),
            demande_ouverte=ouverte,
        )
        user_prompt = _prefixer_consigne_de_soutien(user_prompt, state)
        trace = {
            "trace_id": state.get("trace_id"),
            "securite": None,
            "soutien": state.get("soutien"),
            "hint_level": None,
            "hint_label": "Orientation",
            "hint_reason": (
                "demande d'inventaire des chapitres"
                if inventaire
                else "demande d'aide sans objet nommé"
                if ouverte
                else "question sur le service"
            ),
            "frustration_score": 0.0,
            "tool_used": None,
            "competence": None,
            "course": None,
            "sources": [],
            "scores": [],
            "catalogue": catalogue,
        }
        await self._write_audit(state, trace)
        return {
            "system_prompt": system,
            "final_prompt": user_prompt,
            "retrieved": [],
            # Posée seulement sur l'inventaire : ``compose_response`` et
            # ``stream()`` la restituent alors telle quelle, sans appeler le
            # modèle. Le prompt reste assemblé et tracé — il documente ce que le
            # tour aurait envoyé, et le rejeu QA continue de l'assérer.
            "reponse_directe": reponse_catalogue(catalogue) if inventaire else None,
            "trace": trace,
            "node_trace": [
                {
                    "node": "guardrail_meta",
                    "n_chapitres": len(catalogue),
                    "inventaire": inventaire,
                    "demande_ouverte": ouverte,
                }
            ],
        }

    @_timed_node("guardrail_accueil")
    async def _n_guardrail_accueil(self, state: AgentState) -> dict:
        """Salutation seule : on accueille, sans rien chercher (cas #38, #41).

        Branché au même endroit que ``guardrail_meta``, avant la recherche, et
        pour une raison voisine : « Bonsoir » n'a aucun contenu à retrouver, et
        la recherche y remontait quand même cinq extraits à des scores
        indiscernables (~0,03) — du bruit, qui servait ensuite de matière à une
        question de vérification que l'élève n'avait pas appelée.
        """
        ctx = state.get("curriculum_context", {})
        catalogue = self._retriever.catalogue(ctx)
        system, user_prompt = assemble_accueil_prompt(state["question"], catalogue, ctx)
        user_prompt = _prefixer_consigne_de_soutien(user_prompt, state)
        trace = {
            "trace_id": state.get("trace_id"),
            "securite": None,
            "soutien": state.get("soutien"),
            "hint_level": None,
            "hint_label": "Accueil",
            "hint_reason": "salutation seule",
            "frustration_score": 0.0,
            "tool_used": None,
            "competence": None,
            "course": None,
            "sources": [],
            "scores": [],
            "catalogue": catalogue,
        }
        await self._write_audit(state, trace)
        return {
            "system_prompt": system,
            "final_prompt": user_prompt,
            "retrieved": [],
            "trace": trace,
            "node_trace": [{"node": "guardrail_accueil", "n_chapitres": len(catalogue)}],
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
        focused, sections_servies = self._ancrer_sur_la_section(
            focused, section, position.chapitre, ctx
        )
        return {
            "retrieved": focused,
            "course_section": course_section,
            "node_trace": [
                {"node": "course_planner", "section": section.key,
                 "section_index": position.section_index,
                 "chapitre": position.chapitre,
                 "chapitre_confirmed": position.chapitre_confirmed,
                 "sections_servies": sections_servies,
                 "n_sources_focused": len(focused)}
            ],
        }

    def _ancrer_sur_la_section(
        self, focused: list[ScoredChunk], section: Section, chapitre: str | None, ctx: dict
    ) -> tuple[list[ScoredChunk], list[str]]:
        """Place en tête les extraits de la section enseignée, en les cherchant au besoin.

        La récupération a lieu **avant** ce nœud, sur la phrase brute de l'élève :
        elle ignore donc quelle section va être enseignée. Sur « Fais-moi un
        cours sur les nombres complexes », elle remontait Introduction, Astuces
        et Auto-évaluation — la définition fondatrice n'était nulle part, et le
        modèle n'avait rien pour l'énoncer (cas QA #12).

        Deux temps, dans cet ordre : réordonner ce qu'on a déjà, puis compléter
        par une recherche circonscrite au chapitre **uniquement si** une source
        déclarée manque encore. Le cas nominal ne coûte donc aucun appel
        supplémentaire.

        Le repli est silencieux et volontaire : si le corpus ne contient pas la
        section (leçon partielle), on rend ce qu'on a. Inventer la section
        manquante serait exactement ce que la règle n°4 interdit ; c'est au
        prompt de dire honnêtement ce qui manque, pas à ce nœud de le combler.
        """
        if not section.sources:
            return focused, []

        de_la_section = [sc for sc in focused if texte_releve_de_la_section(sc.chunk.text, section)]
        autres = [sc for sc in focused if sc not in de_la_section]

        titres_retenus = [t for sc in de_la_section if (t := titre_de_section(sc.chunk.text))]
        if sources_absentes(titres_retenus, section) and chapitre:
            deja = {sc.chunk.id for sc in focused}
            for sc in self._retriever.chunks_du_chapitre(chapitre, ctx):
                if sc.chunk.id not in deja and texte_releve_de_la_section(sc.chunk.text, section):
                    de_la_section.append(sc)

        servies = [t for sc in de_la_section if (t := titre_de_section(sc.chunk.text))]
        return [*de_la_section, *autres], servies

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
            has_course=state.get("has_course", True),
        )
        if moderation.flagged:
            user_prompt = f"{_MODERATION_OVERRIDE}\n\n{user_prompt}"
        user_prompt = _prefixer_consigne_de_soutien(user_prompt, state)

        competence = _competence_from_context(ctx, retrieved)
        trace = {
            "trace_id": state.get("trace_id"),
            "soutien": state.get("soutien"),
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
            # Présent aussi en mode exercice : la clé manquait ici, si bien
            # qu'aucun appelant — trace, journal, test — ne pouvait savoir qu'un
            # tour de cours était parti sans documentation.
            "hors_perimetre": bool(state.get("hors_perimetre")),
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

    # --- Branche entraînement (l'élève réclame un énoncé) --------------------

    @_timed_node("entrainement_planner")
    async def _n_entrainement_planner(self, state: AgentState) -> dict:
        """Va chercher un énoncé du corpus, plutôt qu'un rappel de règle (cas #31).

        Le nœud réemploie hors cours les deux mécanismes du mode cours qui ne
        dépendent pas de la similarité vectorielle : la **liaison du chapitre au
        sujet demandé** (``resolve_chapitre``, par recoupement de titre) et
        l'**ancrage sur une section nommée** (``_ancrer_sur_la_section``, par
        titre de section). La recherche, elle, a eu lieu sur la phrase brute de
        l'élève : elle ignore qu'on cherche des énoncés, et remontait ici
        « Astuces », « Erreurs fréquentes » et « Théorèmes » — de quoi rappeler
        une règle, jamais de quoi proposer un exercice.

        Les corrigés sont écartés du contexte : les laisser, c'est mettre la
        solution sous les yeux du modèle au moment précis où on lui demande de
        ne pas la donner. Le repli garde la liste d'origine si le filtre la
        vidait — mieux vaut un contexte imparfait qu'un tour sans documentation.
        """
        ctx = state.get("curriculum_context", {})
        retrieved = state.get("retrieved", [])
        binding = resolve_chapitre(
            state["question"], [sc.chunk.metadata.chapitre for sc in retrieved]
        )
        chapitre = binding.chapitre if binding.confirmed else None
        section = section_par_cle(CLE_SECTION_EXERCICES)

        focused = _focus_on_chapitre(retrieved, chapitre) if chapitre else retrieved
        focused, sections_servies = self._ancrer_sur_la_section(focused, section, chapitre, ctx)
        sans_corriges = [sc for sc in focused if not _est_un_corrige(sc)]
        focused = sans_corriges or focused

        # Quand la demande ne se rattache à aucun chapitre, ce sont les chapitres
        # réellement indexés qu'on propose — lus dans le store, jamais déduits
        # des extraits remontés, qui peuvent être vides (fixture positive #52).
        alternatives = list(binding.alternatives) or self._retriever.catalogue(ctx)

        entrainement = {
            "chapitre": binding.chapitre,
            "chapitre_confirmed": binding.confirmed,
            "topic": topic_label(state["question"]),
            "alternatives": alternatives,
            "sections_servies": sections_servies,
        }
        return {
            "retrieved": focused,
            "entrainement": entrainement,
            "node_trace": [
                {
                    "node": "entrainement_planner",
                    "chapitre": binding.chapitre,
                    "chapitre_confirmed": binding.confirmed,
                    "sections_servies": sections_servies,
                    "n_sources": len(focused),
                }
            ],
        }

    @_timed_node("guardrail_entrainement")
    async def _n_guardrail_entrainement(self, state: AgentState) -> dict:
        question = state["question"]
        ctx = state.get("curriculum_context", {})
        retrieved = state.get("retrieved", [])
        entrainement = state["entrainement"]
        moderation = moderate(question)

        system, user_prompt = assemble_exercise_prompt(
            question, entrainement, retrieved, ctx, state.get("conversation_history", [])
        )
        if moderation.flagged:
            user_prompt = f"{_MODERATION_OVERRIDE}\n\n{user_prompt}"
        user_prompt = _prefixer_consigne_de_soutien(user_prompt, state)

        trace = {
            "trace_id": state.get("trace_id"),
            "soutien": state.get("soutien"),
            # Pas de niveau d'indice ici, comme en mode cours et pour la même
            # raison : la graduation socratique n'a pas d'objet tant que l'élève
            # n'a pas d'énoncé. Les clés du contrat restent présentes.
            "hint_level": None,
            "hint_label": "Exercice proposé",
            "hint_reason": (
                "exercice demandé par l'élève"
                if entrainement["chapitre_confirmed"]
                else "exercice demandé, chapitre non couvert"
            ),
            "frustration_score": 0.0,
            "tool_used": None,
            "competence": _competence_from_context(ctx, retrieved),
            "course": None,
            "entrainement": entrainement,
            "hors_perimetre": bool(state.get("hors_perimetre"))
            or not entrainement["chapitre_confirmed"],
            "sources": _sources_payload(retrieved),
            "scores": [sc.score for sc in retrieved],
        }
        await self._write_audit(state, trace)
        return {
            "system_prompt": system,
            "final_prompt": user_prompt,
            "moderation_flagged": moderation.flagged,
            "trace": trace,
            "node_trace": [
                {"node": "guardrail_entrainement", "moderation_flagged": moderation.flagged}
            ],
        }

    # --- Branche quiz (posture d'évaluation) --------------------------------

    @_timed_node("quiz_planner")
    async def _n_quiz_planner(self, state: AgentState) -> dict:
        """Détermine sur quoi interroger l'élève et sous quelle forme.

        La compétence est déduite du cadre curriculaire et des extraits
        remontés — jamais demandée à l'élève, qui a écrit « teste-moi » et
        n'attend pas un questionnaire préalable.
        """
        ctx = state.get("curriculum_context", {})
        retrieved = state.get("retrieved", [])
        competence = _competence_from_context(ctx, retrieved) or "le chapitre en cours"
        quiz_type = "vrai_faux" if _VRAI_FAUX.search(state["question"]) else "qcm"
        return {
            "quiz_competence": competence,
            "quiz_type": quiz_type,
            "node_trace": [
                {"node": "quiz_planner", "competence": competence, "quiz_type": quiz_type}
            ],
        }

    @_timed_node("guardrail_quiz")
    async def _n_guardrail_quiz(self, state: AgentState) -> dict:
        question = state["question"]
        ctx = state.get("curriculum_context", {})
        retrieved = state.get("retrieved", [])
        moderation = moderate(question)

        cadre = ", ".join(
            f"{v}" for k in ("classe", "serie") if (v := ctx.get(k))
        )
        user_prompt = construire_prompt_quiz(
            state["quiz_competence"],
            state["quiz_type"],
            contexte_curriculaire=cadre,
            extraits=build_context_block(retrieved) if retrieved else "",
        )
        if moderation.flagged:
            user_prompt = f"{_MODERATION_OVERRIDE}\n\n{user_prompt}"

        trace = {
            "trace_id": state.get("trace_id"),
            # Pas de niveau d'indice en évaluation : on garde les clés du
            # contrat (logs, frontend) avec des valeurs adaptées.
            "hint_level": None,
            "hint_label": "Quiz",
            "hint_reason": "demande explicite d'évaluation",
            "frustration_score": 0.0,
            "tool_used": None,
            "competence": state["quiz_competence"],
            "quiz": {"competence": state["quiz_competence"], "quiz_type": state["quiz_type"]},
            "sources": _sources_payload(retrieved),
            "scores": [sc.score for sc in retrieved],
        }
        await self._write_audit(state, trace)
        return {
            "system_prompt": SYSTEM_PERSONA_QUIZ,
            "final_prompt": user_prompt,
            "moderation_flagged": moderation.flagged,
            "trace": trace,
            "node_trace": [{"node": "guardrail_quiz", "moderation_flagged": moderation.flagged}],
        }

    @_timed_node("compose_response")
    async def _n_compose(self, state: AgentState) -> dict:
        # Réponse déjà écrite par le code (inventaire des chapitres, cas #26) :
        # le modèle n'est pas sollicité. C'est le pendant non streamé du même
        # court-circuit dans ``stream()`` — les deux chemins doivent rendre le
        # même texte, sans quoi la démo et les tests divergeraient.
        directe = state.get("reponse_directe")
        answer = (
            directe
            if directe is not None
            else await self._llm.generate(state["final_prompt"], system=state.get("system_prompt"))
        )
        # L'ouverture de soutien passe devant la génération — c'est ce que veut
        # dire « dédramatiser AVANT de reprendre le cours » (cas #19). Le
        # pendant streamé est dans ``stream()`` : les deux chemins doivent
        # produire la même réponse, sans quoi la démo et les tests divergent.
        preambule = state.get("preambule_soutien")
        if preambule:
            answer = f"{preambule}\n\n{answer}"
        await self._write_memory(state)
        return {"answer": answer, "node_trace": [{"node": "compose_response", "chars": len(answer)}]}

    # --- Nœuds terminaux (graphe complet uniquement) ------------------------

    @_timed_node("verify_response")
    async def _n_verify(self, state: AgentState) -> dict:
        """Contrôles déterministes sur la réponse produite.

        Deux choses distinctes s'y passent :

        * pour **tous** les tours, les deux contrôles factuels de
          ``agent/verify.py`` (vocabulaire hors-programme, fidélité au calcul) ;
        * pour un tour **quiz**, la validation du JSON produit par le modèle.
          Un quiz invalide n'est jamais montré à l'élève : mieux vaut annoncer
          l'échec qu'afficher un QCM aux propositions factices.

        Aucun appel au modèle : ce nœud ne coûte rien et ne peut pas échouer
        pour cause de réseau.
        """
        answer = state.get("answer", "")
        trace = state.get("trace", {})
        rapport = verifier_coherence_mathematique(
            answer,
            competence=trace.get("competence"),
            # Le résultat SEUL, pas la chaîne « expression → résultat » : cette
            # dernière n'apparaît jamais telle quelle dans une réponse rédigée,
            # si bien que le contrôle signalait un problème à chaque calcul juste.
            resultat_calcule=state.get("tool_result_brut"),
        )

        mise_a_jour: dict = {
            "verification": {"valide": rapport.est_valide, "problemes": rapport.problemes},
        }
        entree_trace = {
            "node": "verify_response",
            "valide": rapport.est_valide,
            "n_problemes": len(rapport.problemes),
        }

        if state.get("intent") == Intent.QUIZ.value:
            valide = analyser_reponse_quiz(answer)
            utilisable = valide is not None and not contient_du_factice(valide)
            quiz = Quiz(
                competence=state.get("quiz_competence", ""),
                quiz_type=state.get("quiz_type", "qcm"),
                questions=[valide] if utilisable else [],
            )
            mise_a_jour["quiz"] = quiz.to_dict()
            entree_trace["quiz_utilisable"] = utilisable

        mise_a_jour["node_trace"] = [entree_trace]
        return mise_a_jour

    @_timed_node("persist_progression")
    async def _n_persist_progression(self, state: AgentState) -> dict:
        """Met à jour la maîtrise quand le tour porte un résultat mesurable.

        Un tour de chat ordinaire ne prouve rien : ce n'est pas parce qu'un
        élève a posé une question qu'il maîtrise ou ne maîtrise pas la notion.
        Seul un **résultat** (``exercise_outcome``, posé par la route de
        correction) alimente la maîtrise. Sans lui, ce nœud ne fait rien —
        c'est voulu.
        """
        resultat = state.get("exercise_outcome")
        mastery = state.get("mastery_port") or self._mastery
        competence = state.get("trace", {}).get("competence")

        if not resultat or mastery is None or not competence:
            return {"node_trace": [{"node": "persist_progression", "enregistre": False}]}

        session = state.get("session") or SessionState()
        maj = await mastery.record_attempt(
            student_id=session.student_id,
            competence=competence,
            is_correct=resultat.get("is_correct"),
            score=resultat.get("score"),
            chapitre=resultat.get("chapitre"),
            tenant_id=session.tenant_id,
        )
        return {
            "mastery": maj,
            "node_trace": [
                {"node": "persist_progression", "enregistre": True,
                 "competence": competence, "mastery_score": maj["mastery_score"]}
            ],
        }

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
        # Disjoncteur de sécurité : en tête, avec sa propre sortie vers END.
        g.add_node("triage_securite", self._n_triage_securite)
        g.add_node("reponse_securite", self._n_reponse_securite)
        g.add_node("profil_eleve", self._n_profil_eleve)
        g.add_node("detect_intent", self._n_detect_intent)
        # Ouverture de soutien : après l'intention, avant l'aiguillage — le
        # découragement est un état de l'élève, pas une propriété du sujet, et
        # les trois branches de contenu doivent pouvoir le porter (cas #19/#21).
        g.add_node("soutien_eleve", self._n_soutien)
        g.add_node("retrieve_context", self._n_retrieve)
        # Branche exercice (posture socratique) — inchangée.
        g.add_node("detect_frustration", self._n_frustration)
        g.add_node("diagnose_hint_level", self._n_hint)
        g.add_node("route_tool", self._n_route_tool)
        g.add_node("guardrail", self._n_guardrail)
        # Branche cours (posture didactique).
        g.add_node("course_planner", self._n_course_planner)
        g.add_node("guardrail_course", self._n_guardrail_course)
        # Branche entraînement (l'élève réclame un énoncé à traiter, cas #31).
        g.add_node("entrainement_planner", self._n_entrainement_planner)
        g.add_node("guardrail_entrainement", self._n_guardrail_entrainement)
        # Branche quiz (posture d'évaluation) — portée de NURU.
        g.add_node("quiz_planner", self._n_quiz_planner)
        g.add_node("guardrail_quiz", self._n_guardrail_quiz)
        # Branche méta (question sur le service) — sans recherche de contenu.
        g.add_node("guardrail_meta", self._n_guardrail_meta)
        g.add_node("guardrail_accueil", self._n_guardrail_accueil)

        g.add_edge(START, "triage_securite")
        # Le profil est résolu avant tout le reste (sauf la mise en sécurité,
        # qui prime sur tout) : la série gouverne les filtres de recherche
        # autant que le cadre annoncé dans le prompt (cas #8).
        g.add_conditional_edges(
            "triage_securite",
            _route_par_securite,
            {"detresse": "reponse_securite", "normal": "profil_eleve"},
        )
        g.add_edge("profil_eleve", "detect_intent")
        g.add_edge("reponse_securite", END)
        # Une question méta est détournée AVANT la recherche : c'est le
        # retrieval lui-même qui produisait la réponse hors-sujet (cas #2/#3/#4).
        g.add_edge("detect_intent", "soutien_eleve")
        g.add_conditional_edges(
            "soutien_eleve",
            _route_meta_ou_contenu,
            {
                "meta": "guardrail_meta",
                "accueil": "guardrail_accueil",
                "contenu": "retrieve_context",
            },
        )
        g.add_conditional_edges(
            "retrieve_context",
            _route_by_intent,
            {
                "exercice": "detect_frustration",
                "cours": "course_planner",
                "quiz": "quiz_planner",
                "entrainement": "entrainement_planner",
            },
        )
        g.add_edge("detect_frustration", "diagnose_hint_level")
        g.add_edge("diagnose_hint_level", "route_tool")
        g.add_edge("route_tool", "guardrail")
        g.add_edge("course_planner", "guardrail_course")
        g.add_edge("entrainement_planner", "guardrail_entrainement")
        g.add_edge("quiz_planner", "guardrail_quiz")

        if include_compose:
            # Les deux nœuds terminaux ne vivent que dans le graphe complet :
            # en streaming, la réponse est produite hors graphe, et ils sont
            # appelés après épuisement du flux (cf. ``stream``).
            g.add_node("compose_response", self._n_compose)
            g.add_node("verify_response", self._n_verify)
            g.add_node("persist_progression", self._n_persist_progression)
            g.add_edge("guardrail", "compose_response")
            g.add_edge("guardrail_course", "compose_response")
            g.add_edge("guardrail_entrainement", "compose_response")
            g.add_edge("guardrail_quiz", "compose_response")
            g.add_edge("guardrail_meta", "compose_response")
            g.add_edge("guardrail_accueil", "compose_response")
            g.add_edge("compose_response", "verify_response")
            g.add_edge("verify_response", "persist_progression")
            g.add_edge("persist_progression", END)
        else:
            g.add_edge("guardrail", END)
            g.add_edge("guardrail_course", END)
            g.add_edge("guardrail_entrainement", END)
            g.add_edge("guardrail_quiz", END)
            g.add_edge("guardrail_meta", END)
            g.add_edge("guardrail_accueil", END)
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
            reponse_directe=result.get("reponse_directe"),
            preambule_soutien=result.get("preambule_soutien"),
        )

    async def stream(self, prepared: Prepared) -> AsyncIterator[str]:
        """Streame la génération finale à partir d'un prompt préparé.

        Une fois le flux épuisé, ``prepared.generation`` est rempli (durée,
        nombre de tokens, fournisseur LLM effectif) — lu par l'appelant après
        la boucle ``async for`` pour compléter la trace persistée.
        """
        t0 = time.perf_counter()
        token_count = 0
        # Réponse déjà écrite par le code — mise en sécurité (cas #7) ou
        # inventaire des chapitres (cas #26). Le modèle n'est pas sollicité :
        # c'est ce qui garantit que le texte ne varie pas d'un appel à l'autre.
        # Le fournisseur déclaré distingue les deux, parce que la trace sert
        # aussi à prouver qu'un tour de détresse n'est jamais passé par le
        # modèle — un libellé unique noierait ce contrôle.
        if prepared.reponse_directe is not None:
            fournisseur = "securite" if prepared.trace.get("securite") else "code"
            for token in re.findall(r"\S+\s*", prepared.reponse_directe):
                token_count += 1
                yield token
        else:
            # Pendant streamé de ``_n_compose`` : l'ouverture de soutien part
            # avant le premier token du modèle. Elle est découpée comme la
            # réponse de mise en sécurité, pour que le client voie du texte
            # arriver au même rythme et non un bloc suivi d'une pause.
            if prepared.preambule_soutien:
                for token in re.findall(r"\S+\s*", prepared.preambule_soutien):
                    token_count += 1
                    yield token
                yield "\n\n"
            async for token in self._llm.generate_stream(
                prepared.final_prompt, system=prepared.system_prompt
            ):
                token_count += 1
                yield token
            fournisseur = self.last_llm_used
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        prepared.generation = {
            "node": "compose_response",
            "duration_ms": duration_ms,
            "token_count": token_count,
            "llm_provider": fournisseur,
        }
        log_event(
            _logger, "node:compose_response_stream", trace_id=prepared.trace_id,
            duration_ms=duration_ms, token_count=token_count, llm_provider=fournisseur,
        )

    async def commit_memory(self, prepared: Prepared) -> None:
        """Persiste le résultat notable (à appeler après un stream réussi)."""
        # Un tour de mise en sécurité n'apprend rien sur les compétences de
        # l'élève : il est tracé dans l'audit, pas dans la mémoire pédagogique.
        # (Le graphe complet fait de même : il contourne ``compose_response``,
        # seul endroit où la mémoire est écrite sur le chemin non streamé.)
        if prepared.trace.get("securite"):
            return
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
        mastery: MasteryPort | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        course_state: dict | None = None,
        exercise_outcome: dict | None = None,
    ) -> AgentResult:
        """Tour complet non-streamé (a→f) — pratique pour tests et démo.

        ``exercise_outcome`` porte le résultat d'un exercice ou d'un quiz déjà
        corrigé (``{"is_correct": ..., "score": ...}``). C'est la **seule**
        entrée qui autorise la mise à jour de la maîtrise : sans elle, le tour
        ne prouve rien sur ce que l'élève sait faire.
        """
        clean = sanitize(question)
        session = session or SessionState()
        trace_id = str(uuid.uuid4())
        state: AgentState = {
            "question": clean,
            "curriculum_context": curriculum_context or {},
            "session": session,
            "memory_port": memory,
            "audit_port": audit,
            "mastery_port": mastery,
            "trace_id": trace_id,
            "node_trace": [],
            "conversation_history": conversation_history or [],
            "course_state": course_state,
            "exercise_outcome": exercise_outcome,
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
            final_prompt=result.get("final_prompt", ""),
            verification=result.get("verification"),
            quiz=result.get("quiz"),
            mastery=result.get("mastery"),
        )


def _route_par_securite(state: AgentState) -> str:
    """Aiguillage en tête de graphe. Le défaut sûr est ici ``normal``.

    Symétrique de ``_route_by_intent`` : en cas de doute on ne déclenche pas le
    message d'aide, qui perdrait son sens s'il tombait à chaque blocage scolaire.
    La sélectivité est portée par ``securite.detecter_detresse``, pas ici.
    """
    return "detresse" if state.get("securite") else "normal"


def _route_meta_ou_contenu(state: AgentState) -> str:
    """Aiguillage juste après ``detect_intent``, avant toute recherche.

    Défaut sûr : ``contenu``. Une intention non reconnue continue vers le
    pipeline habituel — la sélectivité est portée par ``intent.is_meta_request``
    et ``intent.est_une_salutation``.
    """
    intention = state.get("intent")
    if intention == Intent.META.value:
        return "meta"
    if intention == Intent.SALUTATION.value:
        return "accueil"
    return "contenu"


def _route_by_intent(state: AgentState) -> str:
    """Aiguillage conditionnel après ``retrieve_context``.

    Le **défaut reste ``exercice``** : toute intention non reconnue retombe sur
    la posture socratique, qui est celle qui ne dévoile rien à l'élève. C'est la
    règle de sûreté déjà appliquée à l'ajout du mode cours.
    """
    intent = state.get("intent")
    if intent == Intent.COURS.value:
        return "cours"
    if intent == Intent.QUIZ.value:
        return "quiz"
    if intent == Intent.ENTRAINEMENT.value:
        return "entrainement"
    return "exercice"


def _sources_payload(retrieved: list[ScoredChunk]) -> list[dict]:
    """Liste d'attribution des sources RAG (identique aux deux branches).

    ``score`` est le score de fusion RRF, fondé sur les rangs : il classe mais
    ne mesure pas, et deux extraits d'à-propos opposés y sont voisins.
    ``dense_score`` est le cosinus, borné et interprétable — c'est sur lui, et
    non sur ``score``, qu'un seuil de pertinence pourra être calibré (cas QA #5).
    Il est exposé ici pour que cette calibration puisse s'observer sur la pile
    réelle plutôt que se deviner. Il vaut ``None`` quand le backend ne le
    fournit pas : une absence de mesure, pas une similarité nulle.
    """
    return [
        {
            "id": sc.chunk.id,
            "label": sc.source_label,
            "type_chunk": sc.chunk.metadata.type_chunk,
            "score": sc.score,
            "dense_score": sc.dense_score,
        }
        for sc in retrieved
    ]


def _est_un_corrige(sc: ScoredChunk) -> bool:
    """Vrai si ce chunk est la section « Corrigés détaillés » d'une leçon.

    Écarté du tour d'entraînement : donner au modèle l'énoncé ET sa solution
    pendant qu'on lui demande de ne pas résoudre, c'est compter sur sa retenue
    là où le code peut simplement ne pas la lui montrer.
    """
    titre = titre_de_section(sc.chunk.text)
    return bool(titre) and "corrig" in strip_accents(titre).lower()


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
