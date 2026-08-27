"""Rejeu générique des 14 cas de priorité « Haute » (sprint 2).

Jumeau de :mod:`test_qa_critical` pour le sprint suivant, et pour la même
raison : sans lui, un cas Haute non encore traité ne produit **aucune** ligne
dans le rapport pytest. Les trois premiers correctifs du sprint (#8, #10, #15)
n'existaient ainsi que dans leurs fichiers dédiés — rien ne signalait les onze
autres.

Le verdict vient de :mod:`attentes`, partagé avec le sprint 1 : un cas sans
attente enregistrée ressort en ``xfail``, donc visible et compté, jamais
silencieux.
"""

from __future__ import annotations

import pytest

from .attentes import ATTENTES, CONTEXTE_DEFAUT, CONTEXTES, HORS_MOTEUR
from .cas import cas_hauts

CAS = cas_hauts()


@pytest.mark.parametrize("cas", CAS, ids=[c.identifiant_test for c in CAS])
async def test_cas_haute(cas, agent_qa, session_eleve):
    if cas.id in HORS_MOTEUR:
        pytest.xfail(f"cas QA #{cas.id} — {HORS_MOTEUR[cas.id]}")
    attente = ATTENTES.get(cas.id)
    if attente is None:
        pytest.xfail(f"cas QA #{cas.id} ({cas.subtheme}) — encore « à_traiter »")
    contexte = CONTEXTES.get(cas.id, CONTEXTE_DEFAUT)
    resultat = await agent_qa.respond(cas.prompt, contexte, session_eleve)
    attente(resultat, cas)


def test_chaque_cas_haute_est_rejouable():
    """Garde-fou sur la fixture : 14 cas, prompts non vides, ids attendus."""
    assert len(CAS) == 14
    assert all(cas.prompt.strip() for cas in CAS)
    assert {c.id for c in CAS} == set(range(8, 22))
