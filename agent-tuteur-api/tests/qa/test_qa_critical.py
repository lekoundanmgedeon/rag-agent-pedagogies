"""Rejeu générique des 7 cas de `qa/qa_cases_critical.json` (sprint 1).

Chaque cas est rejoué avec son ``prompt`` exact ; le verdict vient de
:mod:`attentes`. Les cas encore « à_traiter » ressortent en ``xfail`` : ils
restent comptés dans le rapport, sans faire échouer la suite.
"""

from __future__ import annotations

import pytest

from .attentes import ATTENTES
from .cas import cas_critiques

CAS = cas_critiques()


@pytest.mark.parametrize("cas", CAS, ids=[c.identifiant_test for c in CAS])
async def test_cas_critique(cas, agent_qa, session_eleve):
    attente = ATTENTES.get(cas.id)
    if attente is None:
        pytest.xfail(f"cas QA #{cas.id} ({cas.subtheme}) — encore « à_traiter »")
    resultat = await agent_qa.respond(cas.prompt, {"serie": "S2"}, session_eleve)
    attente(resultat, cas)


def test_chaque_cas_critique_est_rejouable():
    """Garde-fou sur la fixture elle-même : 7 cas, prompts non vides."""
    assert len(CAS) == 7
    assert all(cas.prompt.strip() for cas in CAS)
    assert {c.id for c in CAS} == set(range(1, 8))
