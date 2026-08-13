"""Montage de la couche B : fournisseur LLM réel et garde-fou anti-mock.

Ce fichier ne juge encore **aucun** cas du backlog : la méthode de verdict sur
la prose (heuristique lexicale ou LLM-juge) n'est pas tranchée, et les 10 cas
``COUCHE_B_SEULEMENT`` de ``test_qa_positive`` attendent cet arbitrage. Ce qui
est établi ici, c'est l'infrastructure — et surtout la preuve que le garde-fou
détecte bien le repli silencieux sur le mock, faute de quoi la couche B pourrait
être écrite en croyant interroger le modèle tout en jugeant un texte figé.

Les deux premiers tests appartiennent à la **couche A** : ils tournent toujours,
hors-ligne, et vérifient le garde-fou lui-même. Seul le dernier est marqué
``llm`` et sollicite un vrai fournisseur (``QA_LLM=1``).
"""

from __future__ import annotations

import pytest

from . import assertions

#: Question de contenu banale, dans le périmètre de l'index figé. Elle ne sert
#: pas à juger la réponse mais à provoquer un tour de génération complet.
QUESTION_TEMOIN = "Comment calculer le module d'un nombre complexe ?"


# --- Couche A : le garde-fou attrape-t-il vraiment le mock ? ------------------
async def test_le_garde_fou_detecte_le_repli_sur_le_mock(agent_qa, session_eleve):
    """``agent_qa`` tourne sur ``MockLLM`` : l'assertion DOIT échouer.

    C'est le seul test qui protège la couche B d'un faux sentiment de sécurité.
    Sans lui, un garde-fou mal branché (mauvaise clé de trace, propriété
    renommée) passerait inaperçu et laisserait toute la couche B valider la
    prose figée du mock.
    """
    resultat = await agent_qa.respond(QUESTION_TEMOIN, {"serie": "S2"}, session_eleve)
    with pytest.raises(AssertionError, match="mock"):
        assertions.assert_llm_reel(agent_qa, resultat)


async def test_le_garde_fou_rejette_un_tour_sans_generation(agent_qa, session_eleve):
    """Un court-circuit de sécurité n'appelle pas le modèle : rien à juger.

    Deuxième façon de ne pas solliciter le modèle, et la plus insidieuse : la
    réponse existe, elle est même bonne, mais elle est écrite par le code. La
    juger comme de la prose de modèle validerait une propriété qui n'a pas été
    testée.
    """
    resultat = await agent_qa.respond("Je me fais harceler au lycée", {"serie": "S2"}, session_eleve)
    with pytest.raises(AssertionError, match="court-circuit"):
        assertions.assert_llm_reel(agent_qa, resultat)


# --- Couche B : le montage atteint-il un fournisseur réel ? -------------------
@pytest.mark.llm
async def test_la_couche_b_atteint_un_fournisseur_reel(agent_qa_llm, session_eleve):
    """Fumée : un tour complet, généré par le modèle configuré pour la démo.

    Aucune assertion sur le contenu — c'est justement ce que la couche B ne sait
    pas encore faire. On vérifie que le tour aboutit, qu'il passe par le modèle
    et non par le mock, et que le corpus figé a bien été interrogé.
    """
    resultat = await agent_qa_llm.respond(QUESTION_TEMOIN, {"serie": "S2"}, session_eleve)
    assertions.assert_llm_reel(agent_qa_llm, resultat)
    assert resultat.answer.strip(), "réponse vide"
    assert resultat.retrieved, "le corpus figé n'a pas été interrogé"
