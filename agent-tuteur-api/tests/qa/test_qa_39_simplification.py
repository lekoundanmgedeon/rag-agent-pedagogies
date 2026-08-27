"""Cas QA #39 — « J'ai rien compris, reprends plus simplement » (Tony SARRE).

Reproche : « l'agent reste vague, sans exemple concret ». Mesuré avant
correctif : intention ``exercice``, niveau d'indice **1**, dont la consigne dit
« Rappelle la règle, la définition ou le théorème utile, **SANS l'appliquer au
cas de l'élève** ». L'exemple concret réclamé par l'élève y était donc
explicitement interdit — même contradiction d'assemblage que les cas #11 et #13,
sur un autre axe.

Deux gestes, séparés à dessein :

* ``frustration.demande_une_simplification`` produit le signal, mais **sans**
  peser sur le score : demander des mots plus simples ne dit rien sur ce qu'il
  faut dévoiler. Le faire compter dans la graduation reviendrait à répondre par
  un cran de solution de plus à une question de registre ;
* ``hint_strategy.ajuster_pour_simplification`` lève l'interdiction en portant
  le tour au niveau 2 — le premier qui n'interdise plus d'illustrer — et
  ``prompt.CONSIGNE_SIMPLIFICATION`` nomme ce qui doit apparaître : un exemple
  chiffré déroulé jusqu'au bout.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.frustration import (
    SessionState,
    demande_une_simplification,
    detect_frustration,
)
from agent_tuteur.agent.hint_strategy import (
    HINT_INSTRUCTIONS,
    HintDecision,
    ajuster_pour_simplification,
)
from agent_tuteur.agent.prompt import CONSIGNE_SIMPLIFICATION

from .cas import par_id, tous_les_cas

CAS_39 = par_id(tous_les_cas())[39]


@pytest.mark.parametrize(
    "question",
    [
        "J'ai rien compris, reprends plus simplement",  # le prompt du cas #39
        "peux-tu reformuler plus simplement ?",
        "explique-moi ça autrement",
        "avec des mots simples s'il te plaît",
        "simplifie",
        "donne-moi un exemple plus simple",
    ],
)
def test_la_demande_de_simplification_est_reconnue(question):
    assert demande_une_simplification(question), question


@pytest.mark.parametrize(
    "question",
    [
        # Difficulté ordinaire : déjà couverte par les marqueurs de ton, elle ne
        # demande pas un changement de registre.
        "je n'ai rien compris",
        "je bloque sur cette question",
        "c'est trop dur",
        # Cas #20 : l'élève dit qu'on lui a déjà expliqué, pas que c'est trop
        # compliqué — l'un appelle un autre angle, l'autre des mots plus simples.
        "Ça fait 3 fois que tu m'expliques, je comprends pas",
    ],
)
def test_ce_qui_n_est_pas_une_demande_de_simplification(question):
    assert not demande_une_simplification(question), question


def test_le_signal_ne_pese_pas_sur_le_score_de_frustration():
    """Le registre demandé et le niveau à dévoiler sont deux axes distincts."""
    session = SessionState()
    avec = detect_frustration("reprends plus simplement", session)
    sans = detect_frustration("reprends", session)
    assert avec.demande_simplification is True
    assert sans.demande_simplification is False
    assert avec.score == sans.score


def test_l_ajustement_ne_redescend_jamais_un_niveau_atteint():
    """Un niveau obtenu par frustration ou répétition n'est pas rabaissé à 2."""
    haute = HintDecision(4, "Solution directe", HINT_INSTRUCTIONS[4], "demande explicite")
    assert ajuster_pour_simplification(haute, demande_simplification=True) is haute


async def test_le_prompt_du_cas_39_autorise_enfin_l_exemple(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_39.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["demande_simplification"] is True
    assert resultat.trace["hint_reason"] == "reformulation simplifiée demandée"
    assert CONSIGNE_SIMPLIFICATION in resultat.final_prompt
    # Le cœur du cas : la consigne qui INTERDISAIT l'exemple ne part plus.
    assert HINT_INSTRUCTIONS[1] not in resultat.final_prompt


async def test_les_deux_signaux_se_cumulent_sans_se_remplacer(agent_qa, session_eleve):
    """« Ça fait 3 fois, reprends plus simplement » : changer d'angle ET simplifier.

    Les deux consignes répondent à deux reproches différents (cas #20 et #39) ;
    servir l'une à la place de l'autre laisserait l'un des deux sans réponse.
    """
    from agent_tuteur.agent.prompt import CONSIGNE_VARIATION_APPROCHE

    resultat = await agent_qa.respond(
        "Ça fait 3 fois que tu m'expliques, reprends plus simplement",
        {"serie": "S2"},
        session_eleve,
    )
    assert CONSIGNE_VARIATION_APPROCHE in resultat.final_prompt
    assert CONSIGNE_SIMPLIFICATION in resultat.final_prompt
