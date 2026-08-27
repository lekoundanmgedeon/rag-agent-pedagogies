"""Cas QA #40 — « Différence entre une limite et une dérivée ? » (Tony SARRE).

Reproche : « l'agent signale correctement le hors-périmètre mais reprend de
force le cours sans laisser le choix à l'élève ».

Mesuré : la reprise n'est pas une dérive du modèle. La persona de cours lui
demande de « terminer TOUJOURS en proposant de passer à la section suivante » ;
juste après un aveu de non-couverture, cela revient à répondre « passons à autre
chose » à un élève qui vient de poser une vraie question. La consigne
``CONSIGNE_LAISSER_LE_CHOIX`` neutralise explicitement cette fin de tour sur les
tours où le code SAIT qu'il y a une lacune : aucun extrait servi, ou chapitre
non identifié.

**Ce que ces tests ne couvrent pas, et pourquoi.** Détecter qu'une relance
posée *pendant* un cours porte sur autre chose que le chapitre en train d'être
enseigné n'a aucun signal fiable sur ce corpus : le test lexical a été écrit,
mesuré, et jeté — « limite », « dérivée » et « probabilité » figurent tous dans
la leçon sur les nombres complexes (section « Liens avec les autres
chapitres »), si bien que rien ne distingue la question étrangère de la vraie
sous-question. C'est exactement l'angle mort ouvert par la décision **D7**, qui
reste à trancher par un humain.
"""

from __future__ import annotations

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.prompt import CONSIGNE_LAISSER_LE_CHOIX


async def test_un_chapitre_non_identifie_rend_la_main_a_l_eleve(agent_qa, session_eleve):
    resultat = await agent_qa.respond(
        "Fais-moi un cours sur les probabilités", {"serie": "S2"}, session_eleve
    )
    assert resultat.trace["course"]["chapitre_confirmed"] is False
    assert CONSIGNE_LAISSER_LE_CHOIX in resultat.final_prompt


async def test_un_tour_de_cours_ordinaire_garde_sa_progression(agent_qa, session_eleve):
    """La consigne ne doit pas s'appliquer partout : proposer la suite reste la
    bonne fin de tour quand le cours se déroule normalement.
    """
    resultat = await agent_qa.respond(
        "Fais-moi un cours sur les nombres complexes", {"serie": "S2"}, session_eleve
    )
    assert resultat.trace["course"]["chapitre_confirmed"] is True
    assert CONSIGNE_LAISSER_LE_CHOIX not in resultat.final_prompt


async def test_la_persona_de_cours_propose_sans_imposer(agent_qa):
    """Le texte de la persona porte la règle générale, la consigne le cas limite."""
    prepared = await agent_qa.prepare(
        "Fais-moi un cours sur les nombres complexes", {"serie": "S2"}, SessionState()
    )
    assert "tu ne l'imposes jamais" in prepared.system_prompt
