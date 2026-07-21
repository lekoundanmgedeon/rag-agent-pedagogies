import pytest

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.agent.llm.mock import MockLLM
from agent_tuteur.agent.ports import InMemoryAuditLog, InMemoryStudentMemory


@pytest.fixture
def agent(rag_stack):
    return TutorAgent(
        rag_stack.retriever,
        MockLLM(),
        memory=InMemoryStudentMemory(),
        audit=InMemoryAuditLog(),
        top_k=5,
    )


async def test_course_request_routes_to_didactic_branch(agent):
    prep = await agent.prepare("explique-moi les dérivées", {"serie": "S1"})
    node_names = [n["node"] for n in prep.node_trace]
    # La branche cours remplace frustration/hint/tool par le planificateur de cours.
    assert node_names == [
        "detect_intent",
        "retrieve_context",
        "course_planner",
        "guardrail_course",
    ]
    assert prep.trace["course"] is not None
    assert prep.trace["course"]["section_index"] == 0  # démarre à l'Introduction
    assert prep.hint_label == "Cours"
    assert prep.hint_level is None


async def test_course_prompt_uses_didactic_persona(agent):
    prep = await agent.prepare("fais-moi un cours sur les dérivées", {"serie": "S1"})
    assert "professeur" in prep.system_prompt.lower()
    assert "PAS À PAS" in prep.system_prompt
    # Le plan et la section courante sont injectés dans le prompt utilisateur.
    assert "Plan du cours" in prep.final_prompt
    assert "Section à enseigner : 1. Introduction" in prep.final_prompt


async def test_course_progression_advances_with_continue(agent):
    first = await agent.prepare("explique-moi les dérivées", {"serie": "S1"})
    course_state = first.trace["course"]
    assert course_state["section_index"] == 0

    second = await agent.prepare(
        "continue", {"serie": "S1"}, course_state=course_state
    )
    assert second.trace["course"]["section_index"] == 1  # Définitions
    assert "Définitions" in second.final_prompt


async def test_course_goto_jumps_to_exercises(agent):
    start = await agent.prepare("explique-moi les dérivées", {"serie": "S1"})
    jumped = await agent.prepare(
        "passe aux exercices", {"serie": "S1"}, course_state=start.trace["course"]
    )
    assert jumped.trace["course"]["section_key"] == "exercices"


async def test_course_full_turn_generates_and_audits(agent):
    session = SessionState(student_id="eleveC", tenant_id="ecoleB")
    result = await agent.respond("explique-moi les dérivées", {"serie": "S1"}, session)
    assert result.answer
    assert result.hint_label == "Cours"
    # La trace d'audit est écrite comme pour la branche exercice.
    assert await agent._audit.read("eleveC", "ecoleB")


async def test_short_followup_stays_in_course_when_in_course(agent):
    start = await agent.prepare("explique-moi les dérivées", {"serie": "S1"})
    # Sans course_state, « et après ? » serait un exercice court (niveau 0) ;
    # avec l'état de cours, il reste dans le cours sur la section courante.
    follow = await agent.prepare(
        "et après ?", {"serie": "S1"}, course_state=start.trace["course"]
    )
    assert follow.trace["course"] is not None
    assert follow.trace["course"]["section_index"] == 0


async def test_exercise_question_ignores_course_state_default(agent):
    # Non-régression : une vraie question d'exercice reste socratique même si un
    # champ course_state absent — défaut sûr.
    prep = await agent.prepare("comment dériver un quotient de fonctions ?", {"serie": "S1"})
    assert prep.trace["course"] is None
    assert prep.hint_level == 1


async def test_course_does_not_substitute_an_unrelated_chapter(agent):
    """Régression : « nombres complexes » enseigné comme un cours de suites.

    Le corpus de test ne contient aucun chapitre sur les complexes ; le RAG
    remonte donc quand même ses meilleurs extraits (suites, dérivées). L'agent
    doit refuser de lier un chapitre et demander au LLM de le dire honnêtement,
    plutôt que d'affirmer un chapitre déduit du meilleur extrait.
    """
    prep = await agent.prepare("Explique moi les nombres complexes", {"serie": "S1"})

    course = prep.trace["course"]
    assert course["chapitre_confirmed"] is False
    assert course["chapitre"] is None
    # Le prompt nomme le sujet demandé et interdit la substitution silencieuse.
    assert "nombres complexes" in prep.final_prompt
    assert "ATTENTION" in prep.final_prompt
    assert "n'enseigne SURTOUT PAS un autre chapitre" in prep.final_prompt


async def test_course_binds_chapter_present_in_corpus(agent):
    prep = await agent.prepare("Explique moi les dérivées", {"serie": "S1"})

    course = prep.trace["course"]
    assert course["chapitre_confirmed"] is True
    assert "dériv" in (course["chapitre"] or "").lower()
    # Liaison réussie => aucun avertissement, et les extraits sont recentrés
    # sur le seul chapitre enseigné.
    assert "ATTENTION" not in prep.final_prompt
    assert {s["label"] for s in prep.trace["sources"]}
    chapters = {sc.chunk.metadata.chapitre for sc in prep.retrieved}
    assert chapters == {course["chapitre"]}
