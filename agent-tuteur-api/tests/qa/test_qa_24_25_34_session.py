"""Cas QA #24, #25 et #34 — trois demandes que le fil de discussion seul pouvait
satisfaire.

* **#24** « Puis uploader une capture d'écran de mon exercice ? » (Pierre Ndong)
  — l'agent répondait hors-sujet en parlant de LaTeX. Ce qu'il fallait dire est
  une **capacité** : il ne lit pas d'image. Une capacité annoncée doit être
  exacte, donc le texte est écrit par le code, sans promettre de fonctionnalité
  future — ce que devient l'upload relève de D9.
* **#25** « Résume-moi toutes les questions que je viens de poser … » (Pierre
  Ndong) — le récapitulatif est lui aussi écrit par le code, à partir des
  messages réellement persistés : c'est exactement le genre de texte où un
  modèle ajoute une question jamais posée.
* **#34** (OKERE Rafiatou) — le résultat de l'intégrale était **correct** ; la
  dérive apparaissait en redemandant un autre format. Cause structurelle : sans
  sa réponse précédente sous les yeux, le modèle la reconstruit au lieu de la
  reformater, et une reconstruction est un nouveau calcul.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.intent import Intent, classify_intent
from agent_tuteur.agent.prompt import CONSIGNE_REFORMATAGE

from . import assertions
from .cas import par_id, tous_les_cas

CAS = par_id(tous_les_cas())


# --- Cas 24 — l'agent ne lit pas les images ----------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Puis uploader une capture d'écran de mon exercice ?",
        "je peux t'envoyer une photo de mon cahier ?",
        "tu peux lire une image ?",
        "je te transmets le PDF du devoir",
    ],
)
def test_une_demande_d_envoi_de_fichier_est_reconnue(question):
    assert classify_intent(question).intent == Intent.META, question


async def test_le_prompt_du_cas_24_dit_la_capacite_reelle(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS[24].prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_intention(resultat, "meta")
    assertions.assert_pas_de_retrieval(resultat)
    reponse = assertions._aplatir(resultat.answer)
    assert "je ne sais pas encore lire les images" in reponse
    # Ce qu'il faut faire à la place, concrètement — et aucune promesse.
    assert "recopie l'enonce" in reponse
    for promesse in ("bientot", "prochainement", "sera bientot", "nous travaillons"):
        assert promesse not in reponse, f"promesse de fonctionnalité future : {promesse}"


# --- Cas 25 — récapitulatif de la session ------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Résume moi tous les questions que je viens de poser et notre session",
        "fais le point sur ce qu'on a vu",
        "qu'est-ce qu'on a fait aujourd'hui ?",
        "rappelle-moi mes questions",
        "fais un résumé de la conversation",
    ],
)
def test_une_demande_de_recapitulatif_est_reconnue(question):
    assert classify_intent(question).intent == Intent.META, question


@pytest.mark.parametrize(
    "question",
    [
        # Frontière : résumer un CHAPITRE est une demande de contenu.
        "résume ce chapitre",
        "résume-moi la leçon sur les complexes",
        "fais-moi une fiche de révision sur les intégrales",
    ],
)
def test_resumer_du_contenu_n_est_pas_un_recapitulatif(question):
    assert classify_intent(question).intent != Intent.META, question


async def test_le_recapitulatif_ne_liste_que_de_vraies_questions(agent_qa, session_eleve):
    """Ce que le modèle aurait pu inventer, le code ne le peut pas."""
    historique = [
        {"role": "user", "content": "Fais-moi un cours sur les nombres complexes"},
        {"role": "assistant", "content": "Introduction…",
         "trace": {"course": {"chapitre": "Les Nombres Complexes", "chapitre_confirmed": True}}},
        {"role": "user", "content": "comment calculer un module ?"},
        {"role": "assistant", "content": "…", "trace": {"hint_label": "Rappel de notion"}},
    ]
    resultat = await agent_qa.respond(
        CAS[25].prompt, {"serie": "S2"}, session_eleve, conversation_history=historique
    )
    assertions.assert_intention(resultat, "meta")
    assert "Fais-moi un cours sur les nombres complexes" in resultat.answer
    assert "comment calculer un module ?" in resultat.answer
    assert "Les Nombres Complexes" in resultat.answer
    # Aucune question inventée : ce qui est listé vient des messages persistés.
    assert resultat.answer.count("\\n1. ") + resultat.answer.count("\\n2. ") <= 2


async def test_le_recapitulatif_d_une_session_vide_le_dit(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS[25].prompt, {"serie": "S2"}, session_eleve)
    assert "vient de commencer" in resultat.answer


# --- Cas 34 — remise en forme d'une réponse déjà correcte --------------------


@pytest.mark.parametrize(
    "question",
    [
        "mets ça sous forme de tableau",
        "présente-le en liste",
        "réécris ta réponse au format tableau",
        "fais plus court",
    ],
)
def test_une_demande_de_reformatage_ne_relance_pas_un_cours(question):
    """« présente-le en liste » ouvrait un chapitre : l'élève demandait l'inverse."""
    assert classify_intent(question).intent == Intent.EXERCICE, question


def test_le_plus_court_chemin_reste_une_question_de_geometrie():
    """Borne du motif : « plus court » n'est pas toujours une demande de format."""
    assert classify_intent("quel est le plus court chemin entre A et B ?").intent != Intent.META
    from agent_tuteur.agent.intent import demande_un_reformatage

    assert not demande_un_reformatage("quel est le plus court chemin entre A et B ?")


async def test_la_reponse_a_reformater_est_donnee_au_modele(agent_qa, session_eleve):
    """Le correctif tient dans ce que le prompt CONTIENT, pas dans une consigne
    de fidélité : sans le texte d'origine, il n'y a rien à être fidèle à."""
    precedente = "Le résultat est $2x + \\\\frac{3x^2}{2} + C$."
    historique = [
        {"role": "user", "content": CAS[34].prompt},
        {"role": "assistant", "content": precedente, "trace": {"hint_label": "Indice ciblé"}},
    ]
    resultat = await agent_qa.respond(
        "mets ça sous forme de tableau", {"serie": "S2"}, session_eleve,
        conversation_history=historique,
    )
    assert resultat.trace["reformatage"] is True
    assert precedente in resultat.final_prompt
    assert CONSIGNE_REFORMATAGE in resultat.final_prompt


async def test_sans_reponse_precedente_aucune_consigne_de_reformatage(agent_qa, session_eleve):
    """Premier message : il n'y a rien à remettre en forme, et le dire serait faux."""
    resultat = await agent_qa.respond(
        "mets ça sous forme de tableau", {"serie": "S2"}, session_eleve
    )
    assert resultat.trace["reformatage"] is False
    assert CONSIGNE_REFORMATAGE not in resultat.final_prompt
