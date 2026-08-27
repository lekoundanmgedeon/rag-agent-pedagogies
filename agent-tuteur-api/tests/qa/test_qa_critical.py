"""Rejeu générique des 7 cas de `qa/qa_cases_critical.json` (sprint 1).

Chaque cas est rejoué avec son ``prompt`` exact ; le verdict vient de
:mod:`attentes`. Les cas encore « à_traiter » ressortent en ``xfail`` : ils
restent comptés dans le rapport, sans faire échouer la suite.
"""

from __future__ import annotations

import pytest

from .attentes import AGENT_PAR_CAS, ATTENTES, CONTEXTE_DEFAUT, CONTEXTES, HORS_MOTEUR
from .cas import cas_critiques

CAS = cas_critiques()


def _parametre(cas):
    """Un cas rejoué sur une pile plus lourde porte le marqueur correspondant.

    Sans cela, ``-m "not bge"`` ne saurait pas quels cas il vient d'écarter.
    """
    marks = [pytest.mark.bge] if cas.id in AGENT_PAR_CAS else []
    return pytest.param(cas, marks=marks, id=cas.identifiant_test)


@pytest.mark.parametrize("cas", [_parametre(c) for c in CAS])
async def test_cas_critique(cas, request, session_eleve):
    if cas.id in HORS_MOTEUR:
        pytest.xfail(f"cas QA #{cas.id} — {HORS_MOTEUR[cas.id]}")
    attente = ATTENTES.get(cas.id)
    if attente is None:
        pytest.xfail(f"cas QA #{cas.id} ({cas.subtheme}) — encore « à_traiter »")
    # La plupart des cas se jugent sur la pile hors-ligne ; certains exigent
    # l'embedder de production (cf. AGENT_PAR_CAS).
    agent = request.getfixturevalue(AGENT_PAR_CAS.get(cas.id, "agent_qa"))
    contexte = CONTEXTES.get(cas.id, CONTEXTE_DEFAUT)
    resultat = await agent.respond(cas.prompt, contexte, session_eleve)
    attente(resultat, cas)


def test_chaque_cas_critique_est_rejouable():
    """Garde-fou sur la fixture elle-même : 7 cas, prompts non vides."""
    assert len(CAS) == 7
    assert all(cas.prompt.strip() for cas in CAS)
    assert {c.id for c in CAS} == set(range(1, 8))
