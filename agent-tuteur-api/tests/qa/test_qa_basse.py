"""Rejeu générique des 6 cas de priorité « Basse » (sprint 4).

Quatrième instance du même patron que :mod:`test_qa_critical`,
:mod:`test_qa_haute` et :mod:`test_qa_moyenne`, pour la même raison : un cas sans
attente enregistrée ressort en ``xfail``, donc visible et compté dans le rapport,
jamais silencieux.

Particularité du sprint 4 : deux de ses six cas (#44 et #45) relèvent de la
**qualité des données de test** et non du comportement de l'agent. Leur prompt
est rejoué comme les autres — c'est ce qui permet de compléter la ligne
manquante du suivi — mais ce qu'on en attend porte sur le tour lui-même, pas sur
un défaut à corriger.
"""

from __future__ import annotations

import pytest

from .attentes import ATTENTES, CONTEXTE_DEFAUT, CONTEXTES, HORS_MOTEUR
from .cas import cas_par_priorite

CAS = cas_par_priorite("Basse")


@pytest.mark.parametrize("cas", CAS, ids=[c.identifiant_test for c in CAS])
async def test_cas_basse(cas, agent_qa, session_eleve):
    if cas.id in HORS_MOTEUR:
        pytest.xfail(f"cas QA #{cas.id} — {HORS_MOTEUR[cas.id]}")
    attente = ATTENTES.get(cas.id)
    if attente is None:
        pytest.xfail(f"cas QA #{cas.id} ({cas.subtheme}) — encore « à_traiter »")
    contexte = CONTEXTES.get(cas.id, CONTEXTE_DEFAUT)
    resultat = await agent_qa.respond(cas.prompt, contexte, session_eleve)
    attente(resultat, cas)


def test_chaque_cas_basse_est_rejouable():
    """Garde-fou sur la fixture : 6 cas, prompts non vides, ids attendus."""
    assert len(CAS) == 6
    assert all(cas.prompt.strip() for cas in CAS)
    assert {c.id for c in CAS} == set(range(43, 49))
