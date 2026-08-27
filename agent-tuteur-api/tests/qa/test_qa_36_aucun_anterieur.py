"""Cas QA #36 — « Génères un cours sur les nombres complexes » (Rahma).

L'agent renvoyait à « la première partie » du cours… sur le tout premier message
de la conversation. Ce n'est pas une invention gratuite : le prompt lui montrait
le plan en 8 sections et ne lui disait nulle part qu'il n'y avait pas d'avant.
Un historique **absent** ne se distingue pas, pour le modèle, d'un historique
qu'on aurait omis de lui rappeler — il comble, comme il comblait la série de
l'élève au cas #16 tant qu'on la lui laissait deviner.

Le correctif dit l'absence au lieu de compter sur le silence
(``CONSIGNE_AUCUN_ANTERIEUR``), sur les deux branches qui servent des extraits :
la référence inventée n'a rien de propre au mode cours.

La seconde moitié du retour (« fautes de grammaire relevées ») est un jugement
sur la prose : la règle de relecture est passée dans les règles communes aux
personas, mais son verdict relève de la décision **D2**, non tranchée.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.prompt import CONSIGNE_AUCUN_ANTERIEUR

from .cas import par_id, tous_les_cas

CAS_36 = par_id(tous_les_cas())[36]


@pytest.mark.parametrize(
    "question",
    [
        "Génères un cours sur les nombres complexes",  # le prompt du cas #36
        "z = 3 + 4i : quelle est sa partie réelle ?",  # branche exercice
    ],
)
async def test_le_premier_message_dit_qu_il_n_y_a_pas_d_avant(question, agent_qa, session_eleve):
    resultat = await agent_qa.respond(question, {"serie": "S2"}, session_eleve)
    assert CONSIGNE_AUCUN_ANTERIEUR in resultat.final_prompt


async def test_la_consigne_disparait_des_qu_il_y_a_un_historique(agent_qa):
    """Elle ne doit pas survivre au premier tour : au second, il y a bien un avant.

    Sans cette borne, l'agent nierait un échange qui a réellement eu lieu — le
    symétrique exact du défaut corrigé.
    """
    premier = await agent_qa.respond(
        CAS_36.prompt, {"serie": "S2"}, SessionState()
    )
    suivant = await agent_qa.respond(
        "continue",
        {"serie": "S2"},
        SessionState(),
        conversation_history=[
            {"role": "user", "content": CAS_36.prompt},
            {"role": "assistant", "content": "Introduction aux nombres complexes…"},
        ],
        course_state=premier.trace["course"],
    )
    assert CONSIGNE_AUCUN_ANTERIEUR not in suivant.final_prompt
    assert "Historique récent de la conversation" in suivant.final_prompt


async def test_la_relecture_est_demandee_aux_deux_postures(agent_qa, session_eleve):
    """La règle de relecture vit dans les règles COMMUNES, pas dans une persona.

    Le cas #36 est un tour de cours, mais rien ne rend le mode exercice moins
    exposé : une règle posée d'un seul côté aurait été un correctif de cas.
    """
    cours = await agent_qa.prepare(CAS_36.prompt, {"serie": "S2"}, session_eleve)
    exercice = await agent_qa.prepare(
        "z = 3 + 4i : quelle est sa partie réelle ?", {"serie": "S2"}, SessionState()
    )
    for prepared in (cours, exercice):
        assert "RELU" in prepared.system_prompt
