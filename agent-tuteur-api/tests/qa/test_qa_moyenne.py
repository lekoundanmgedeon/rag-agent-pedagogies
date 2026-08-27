"""Rejeu générique des 21 cas de priorité « Moyenne » (sprint 3).

Troisième instance du même patron que :mod:`test_qa_critical` et
:mod:`test_qa_haute`, pour la même raison : un cas sans attente enregistrée
ressort en ``xfail``, donc visible et compté dans le rapport, jamais silencieux.

Le sprint 3 se distingue des deux précédents sur un point : une partie de ses
cas ne relève pas du moteur pédagogique (suppression de conversation, upload
d'image, export PDF). Ils restent listés ici — c'est le backlog qui fait foi —
mais leur ``xfail`` signalera durablement qu'ils attendent un arbitrage produit
plutôt qu'un correctif, jusqu'à ce que leur statut le dise explicitement.
"""

from __future__ import annotations

import pytest

from .attentes import ATTENTES, CONTEXTE_DEFAUT, CONTEXTES, HORS_MOTEUR
from .cas import cas_par_priorite

CAS = cas_par_priorite("Moyenne")


@pytest.mark.parametrize("cas", CAS, ids=[c.identifiant_test for c in CAS])
async def test_cas_moyenne(cas, agent_qa, session_eleve):
    if cas.id in HORS_MOTEUR:
        pytest.xfail(f"cas QA #{cas.id} — {HORS_MOTEUR[cas.id]}")
    attente = ATTENTES.get(cas.id)
    if attente is None:
        pytest.xfail(f"cas QA #{cas.id} ({cas.subtheme}) — encore « à_traiter »")
    contexte = CONTEXTES.get(cas.id, CONTEXTE_DEFAUT)
    resultat = await agent_qa.respond(cas.prompt, contexte, session_eleve)
    attente(resultat, cas)


def test_chaque_cas_moyenne_est_rejouable():
    """Garde-fou sur la fixture : 21 cas, prompts non vides, ids attendus."""
    assert len(CAS) == 21
    assert all(cas.prompt.strip() for cas in CAS)
    assert {c.id for c in CAS} == set(range(22, 43))
