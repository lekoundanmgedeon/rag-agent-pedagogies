import pytest
from unittest.mock import AsyncMock, MagicMock
from agent_tuteur.agent.validation_agent import ValidationAgent, Verdict
from agent_tuteur.agent.verify import RapportVerification
from agent_tuteur.agent.llm.base import BaseLLM

@pytest.fixture
def mock_llm():
    llm = AsyncMock(spec=BaseLLM)
    # Par défaut, le LLM renvoie un JSON valide tout à fait positif
    llm.generate.return_value = """
    {
      "criteres": {
        "exactitude_pedagogique": {"ok": true, "note": "Correct"},
        "coherence_question": {"ok": true, "note": "Oui"},
        "conformite_programme": {"ok": true, "note": "Oui"},
        "fidelite_rag": {"ok": true, "note": "Oui"},
        "clarte_explication": {"ok": true, "note": "Oui"},
        "absence_hallucination": {"ok": true, "note": "Oui"},
        "respect_niveau_indice": {"ok": true, "note": "Oui"}
      },
      "verdict": "PASS",
      "explication": "Tout est parfait",
      "recommandations": []
    }
    """
    return llm

@pytest.fixture
def agent(mock_llm):
    return ValidationAgent(mock_llm)

@pytest.mark.asyncio
async def test_validation_pass_complet(agent):
    """Cas 1 : Tout est parfait, couche déterministe et juge LLM valident."""
    res = await agent.validate(
        answer="La dérivée de f est f'(x) = 2x.",
        question="Quelle est la dérivée de x^2 ?",
        intent="exercice",
        hint_level=1,
        rag_sources=[],
        etude_fonction={"derivee": "2*x"}
    )
    
    assert res.verdict == Verdict.PASS
    assert res.score == 1.0
    assert not res.erreurs
    assert res.est_valide is True

@pytest.mark.asyncio
async def test_validation_fail_deterministe_etude(agent):
    """Cas 2 : Incohérence déterministe sur l'étude de fonction (calcul SymPy ignoré)."""
    res = await agent.validate(
        answer="La dérivée est 3x.",
        question="Quelle est la dérivée de x^2 ?",
        intent="exercice",
        hint_level=1,
        rag_sources=[],
        etude_fonction={"derivee": "2*x"}
    )
    
    # La dérivée calculée est "2*x" mais l'Agent répond "3x" et mentionne "dérivée"
    assert res.verdict == Verdict.REPAIR
    assert len(res.erreurs) > 0
    assert "2*x" in res.erreurs[0]

@pytest.mark.asyncio
async def test_validation_llm_judge_repair(agent, mock_llm):
    """Cas 3 : Le juge LLM demande un REPAIR (ex: Exactitude pédagogique en défaut)."""
    mock_llm.generate.return_value = """
    {
      "criteres": {
        "exactitude_pedagogique": {"ok": false, "note": "Faux, c'est -1"}
      },
      "verdict": "REPAIR",
      "explication": "Erreur de signe",
      "recommandations": ["Corriger le signe"]
    }
    """
    res = await agent.validate(
        answer="La réponse est 1.",
        question="Calcule -1.",
        intent="exercice",
    )
    
    assert res.verdict == Verdict.REPAIR
    assert not res.est_valide
    assert "exactitude_pedagogique" in res.erreurs[0]

@pytest.mark.asyncio
async def test_validation_llm_judge_fail(agent, mock_llm):
    """Cas 4 : Le juge LLM détecte un contenu hors-programme (FAIL)."""
    mock_llm.generate.return_value = """
    {
      "criteres": {
        "conformite_programme": {"ok": false, "note": "Gradient non au programme"}
      },
      "verdict": "FAIL",
      "explication": "Hors programme",
      "recommandations": []
    }
    """
    res = await agent.validate(
        answer="Utilisons le gradient.",
        question="...",
        intent="cours",
    )
    
    assert res.verdict == Verdict.FAIL

@pytest.mark.asyncio
async def test_validation_llm_judge_review(agent, mock_llm):
    """Cas 5 : Le juge LLM demande une revue humaine (REVIEW) pour cas ambigu."""
    mock_llm.generate.return_value = """
    {
      "criteres": {
        "fidelite_rag": {"ok": false, "note": "Source manquante ou douteuse"}
      },
      "verdict": "REVIEW",
      "explication": "Doute sur la source",
      "recommandations": []
    }
    """
    res = await agent.validate(
        answer="D'après le cours...",
        question="...",
        intent="cours",
    )
    
    assert res.verdict == Verdict.REVIEW

@pytest.mark.asyncio
async def test_validation_exercice_solution_complete(agent):
    """Cas 6 : Détection déterministe d'une solution complète non autorisée en mode exercice."""
    res = await agent.validate(
        answer="La solution est x = 5. Voici la réponse : c'est 5.",
        question="Résous x - 5 = 0.",
        intent="exercice",
        hint_level=1,
    )
    
    # 2 marqueurs trouvés ("La solution est", "voici la réponse")
    assert res.verdict == Verdict.REPAIR
    assert any("marqueur(s) de solution complète" in e for e in res.erreurs)
