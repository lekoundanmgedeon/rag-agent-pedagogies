"""La branche quiz du graphe, de la détection d'intention au quiz validé."""

import json

import pytest

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.agent.intent import Intent, classify_intent
from agent_tuteur.agent.llm.mock import MockLLM
from agent_tuteur.agent.ports import (
    InMemoryAuditLog,
    InMemoryMastery,
    InMemoryStudentMemory,
)

QUIZ_JSON = json.dumps(
    {
        "question": "Quelle est la dérivée de $x^2$ ?",
        "choices": [
            {"id": "A", "text": "$2x$"},
            {"id": "B", "text": "$x$"},
            {"id": "C", "text": "$x^3$"},
            {"id": "D", "text": "$2$"},
        ],
        "correct_answer": "A",
        "explanation": "La dérivée de $x^2$ vaut $2x$.",
    }
)


class _LLMQuiz(MockLLM):
    """Modèle qui renvoie toujours un quiz JSON valide."""

    async def generate(self, prompt, *, system=None):
        return QUIZ_JSON


@pytest.fixture
def agent(rag_stack):
    return TutorAgent(
        rag_stack.retriever,
        _LLMQuiz(),
        memory=InMemoryStudentMemory(),
        audit=InMemoryAuditLog(),
        mastery=InMemoryMastery(),
        top_k=5,
    )


# --- Détection d'intention ----------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "fais-moi un quiz sur les dérivées",
        "teste-moi",
        "interroge-moi sur les limites",
        "pose-moi des questions",
        "un QCM s'il te plaît",
        "évalue-moi",
    ],
)
def test_les_demandes_d_evaluation_sont_reconnues(question):
    assert classify_intent(question).intent is Intent.QUIZ


@pytest.mark.parametrize(
    "question",
    [
        "je bloque sur l'exercice 3",
        "calcule la dérivée de x carré",
        "je ne comprends pas cette question",
    ],
)
def test_une_question_ordinaire_ne_declenche_pas_de_quiz(question):
    """Le défaut sûr reste l'exercice : on n'interroge pas sans qu'on le demande."""
    assert classify_intent(question).intent is Intent.EXERCICE


def test_une_demande_de_quiz_sort_du_mode_cours():
    """« teste-moi » pendant un cours veut dire « interroge-moi maintenant »."""
    decision = classify_intent("teste-moi maintenant", in_course=True)
    assert decision.intent is Intent.QUIZ


def test_un_cours_en_cours_reste_un_cours():
    assert classify_intent("continue", in_course=True).intent is Intent.COURS


# --- Parcours dans le graphe --------------------------------------------------


async def test_le_quiz_emprunte_sa_propre_branche(agent):
    prep = await agent.prepare("fais-moi un quiz sur les dérivées", {"serie": "S1"})
    noeuds = [n["node"] for n in prep.node_trace]
    assert noeuds == [
        "triage_securite",  # disjoncteur de détresse en tête de graphe (cas QA #7)
        "profil_eleve",     # série résolue avant la recherche (cas QA #8)
        "detect_intent",
        "retrieve_context",
        "quiz_planner",
        "guardrail_quiz",
    ]


async def test_le_planificateur_choisit_un_qcm_par_defaut(agent):
    prep = await agent.prepare("interroge-moi", {"serie": "S1"})
    planner = next(n for n in prep.node_trace if n["node"] == "quiz_planner")
    assert planner["quiz_type"] == "qcm"


async def test_un_vrai_faux_est_demande_explicitement(agent):
    prep = await agent.prepare("fais-moi un quiz vrai ou faux", {"serie": "S1"})
    planner = next(n for n in prep.node_trace if n["node"] == "quiz_planner")
    assert planner["quiz_type"] == "vrai_faux"


async def test_le_tour_complet_produit_un_quiz_utilisable(agent):
    reponse = await agent.respond(
        "fais-moi un quiz sur les dérivées", {"serie": "S1"}, SessionState()
    )
    noeuds = [n["node"] for n in reponse.node_trace]
    assert "verify_response" in noeuds
    assert "persist_progression" in noeuds

    verify = next(n for n in reponse.node_trace if n["node"] == "verify_response")
    assert verify["quiz_utilisable"] is True


async def test_les_noeuds_terminaux_tournent_aussi_hors_quiz(agent):
    """Les contrôles déterministes s'appliquent à tous les tours, pas qu'aux quiz."""
    reponse = await agent.respond("je bloque sur l'exercice", {"serie": "S1"}, SessionState())
    noeuds = [n["node"] for n in reponse.node_trace]
    assert noeuds[-2:] == ["verify_response", "persist_progression"]


async def test_un_tour_de_chat_ordinaire_ne_touche_pas_a_la_maitrise(agent):
    """Poser une question ne prouve ni la maîtrise ni son absence."""
    reponse = await agent.respond("explique-moi les dérivées", {"serie": "S1"}, SessionState())
    persist = next(n for n in reponse.node_trace if n["node"] == "persist_progression")
    assert persist["enregistre"] is False


async def test_un_resultat_d_exercice_met_a_jour_la_maitrise(rag_stack):
    """Le chemin qui compte : un vrai résultat alimente bien la maîtrise."""
    mastery = InMemoryMastery()
    agent = TutorAgent(
        rag_stack.retriever, _LLMQuiz(),
        memory=InMemoryStudentMemory(), audit=InMemoryAuditLog(),
        mastery=mastery, top_k=5,
    )
    session = SessionState()
    reponse = await agent.respond(
        "je bloque sur cet exercice",
        {"serie": "S1", "competence": "Dérivation"},
        session,
        exercise_outcome={"is_correct": True},
    )

    persist = next(n for n in reponse.node_trace if n["node"] == "persist_progression")
    assert persist["enregistre"] is True
    assert reponse.mastery["mastery_score"] == 1.0

    enregistre = await mastery.list_for_student(session.student_id)
    assert len(enregistre) == 1
    assert enregistre[0]["attempts"] == 1


async def test_un_echec_fait_baisser_la_maitrise(rag_stack):
    mastery = InMemoryMastery()
    agent = TutorAgent(
        rag_stack.retriever, _LLMQuiz(),
        memory=InMemoryStudentMemory(), audit=InMemoryAuditLog(),
        mastery=mastery, top_k=5,
    )
    session = SessionState()
    ctx = {"serie": "S1", "competence": "Dérivation"}
    await agent.respond("q1", ctx, session, exercise_outcome={"is_correct": True})
    apres_echec = await agent.respond("q2", ctx, session, exercise_outcome={"is_correct": False})

    assert apres_echec.mastery["mastery_score"] < 1.0
    assert apres_echec.mastery["attempts"] == 2
    assert apres_echec.mastery["successes"] == 1


async def test_la_verification_est_exposee_sur_le_resultat(rag_stack):
    agent = TutorAgent(
        rag_stack.retriever, _LLMQuiz(),
        memory=InMemoryStudentMemory(), audit=InMemoryAuditLog(), top_k=5,
    )
    reponse = await agent.respond("teste-moi", {"serie": "S1"}, SessionState())
    assert reponse.verification is not None
    assert reponse.verification["valide"] is True
    assert reponse.quiz["questions"][0]["correct_answer"] == "A"
