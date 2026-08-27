"""Mémoire de la conversation en cours — le fil de discussion enfin transmis.

**Le défaut mesuré (2026-08-27).** Le prompt ne portait qu'une fenêtre glissante
de six messages, soit trois échanges. Au-delà, plus rien : l'élève qui donnait
son prénom au premier tour ne le retrouvait pas au cinquième, l'exercice servi
trois tours plus tôt n'existait plus, et le chapitre travaillé depuis le début
n'était connu que tant qu'il restait dans la fenêtre. Ce n'était pas un défaut
du modèle — rien de tout cela ne lui était transmis.

**Ce qui a été ajouté**, et la contrainte qui en dicte la forme : la règle
non-négociable n°3 interdit d'inventer du contexte élève. Une mémoire *résumée
par le modèle* l'aurait violée tôt ou tard. Celle-ci est donc construite par le
code à partir des messages persistés et des traces des tours joués — mêmes
entrées, même mémoire, et rien qui ne soit vérifiable dans la conversation.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.memoire_session import (
    MAX_CARACTERES_PAR_MESSAGE,
    MAX_MESSAGES_RECENTS,
    construire,
)


def _tour(question: str, reponse: str, trace: dict | None = None) -> list[dict]:
    return [
        {"role": "user", "content": question},
        {"role": "assistant", "content": reponse, "trace": trace or {}},
    ]


# --- Ce que la mémoire retient, et d'où elle le tient ------------------------


def test_le_prenom_vient_d_une_phrase_de_l_eleve():
    for phrase, attendu in (
        ("Bonjour, je m'appelle Awa", "Awa"),
        ("moi c'est Mamadou", "Mamadou"),
        ("mon prénom est fatou", "Fatou"),
    ):
        assert construire(_tour(phrase, "Bonjour !")).prenom == attendu


@pytest.mark.parametrize(
    "phrase",
    [
        # Rien de tout cela n'est un prénom : un prénom mal capté est pire que
        # pas de prénom — l'agent appellerait l'élève par un mot au hasard.
        "moi c'est pareil",
        "je m'appelle... enfin peu importe",
        "comment tu t'appelles ?",
        "je ne comprends pas les complexes",
    ],
)
def test_aucun_prenom_n_est_invente(phrase):
    assert construire(_tour(phrase, "…")).prenom is None


def test_les_chapitres_viennent_des_traces_et_non_des_extraits():
    """Un extrait peut être remonté sans être le sujet du tour.

    On lit donc la décision du pipeline (chapitre enseigné, confirmé), pas le
    classement du retrieval — sinon la mémoire dirait « nous avons travaillé les
    nombres complexes » d'un tour où ils n'ont fait que passer.
    """
    historique = (
        _tour("cours sur les complexes", "…",
              {"course": {"chapitre": "Les Nombres Complexes", "chapitre_confirmed": True}})
        + _tour("et les suites ?", "…",
                {"course": {"chapitre": None, "chapitre_confirmed": False}})
    )
    assert construire(historique).chapitres == ["Les Nombres Complexes"]


def test_le_dernier_exercice_servi_est_retenu():
    historique = _tour(
        "donne-moi un exercice", "Énoncé : calculer l'intégrale de 2x+1 sur [1,2].",
        {"hint_label": "Exercice proposé",
         "entrainement": {"chapitre": "Le Calcul Intégral", "chapitre_confirmed": True}},
    )
    memoire = construire(historique)
    assert "calculer l'intégrale" in memoire.dernier_exercice
    assert memoire.chapitres == ["Le Calcul Intégral"]


def test_une_conversation_vide_ne_produit_aucune_memoire():
    assert construire([]).est_vide
    assert construire(None).est_vide


# --- Le tour complet : ce qui atteint réellement le modèle -------------------


async def test_le_prenom_survit_a_la_fenetre_glissante(agent_qa, session_eleve):
    """Le cœur du défaut : au-delà de la fenêtre, l'information était perdue.

    Le prénom est donné au premier tour, puis douze messages passent — soit plus
    que la fenêtre. Il doit rester connu, sans quoi l'élève a l'impression de
    parler à quelqu'un qui l'oublie en cours de route.
    """
    historique = _tour("Bonjour, je m'appelle Awa", "Bonjour Awa !")
    for i in range(6):
        historique += _tour(f"question {i}", f"réponse {i}")
    assert len(historique) > MAX_MESSAGES_RECENTS

    resultat = await agent_qa.respond(
        "Comment je m'appelle ?", {"serie": "S2"}, session_eleve,
        conversation_history=historique,
    )
    assert "Awa" in resultat.final_prompt
    entree = next(e for e in resultat.node_trace if e["node"] == "memoire_session")
    assert entree["prenom_connu"] is True
    assert entree["tours"] == 7


async def test_les_messages_longs_sont_tronques_pas_supprimes(agent_qa, session_eleve):
    """Élargir la fenêtre ne devait pas faire exploser le prompt.

    Une section de cours fait plusieurs milliers de caractères ; seul son début
    sert à se rappeler de quoi on parlait. On vérifie donc les deux moitiés : le
    message est bien présent, et il ne l'est pas en entier.
    """
    long_texte = "Les nombres complexes prolongent les réels. " * 60
    historique = _tour("explique", long_texte)

    resultat = await agent_qa.respond(
        "et ensuite ?", {"serie": "S2"}, session_eleve, conversation_history=historique
    )
    assert "Les nombres complexes prolongent les réels." in resultat.final_prompt
    assert long_texte.strip() not in resultat.final_prompt

    reprise = resultat.final_prompt.split("Tuteur : ")[1].split("\n")[0]
    assert reprise.endswith("[…]")
    assert len(reprise) <= MAX_CARACTERES_PAR_MESSAGE + len(" […]")


async def test_la_memoire_ne_dit_rien_d_un_premier_tour(agent_qa, session_eleve):
    """Règle n°3 : sans conversation, il n'y a rien à se rappeler.

    C'est la contrepartie du correctif — et elle compte autant : un bloc de
    mémoire vide mais présent inviterait le modèle à le remplir.
    """
    resultat = await agent_qa.respond(
        "Comment calculer un module ?", {"serie": "S2"}, session_eleve
    )
    assert "Mémoire de cette conversation" not in resultat.final_prompt


async def test_toutes_les_branches_recoivent_la_memoire(agent_qa, session_eleve):
    """Le fil de discussion n'appartient à aucune posture.

    Le nœud est placé avant l'aiguillage pour cette raison : une mémoire câblée
    sur la seule branche exercice aurait laissé l'élève sans contexte dès qu'il
    ouvre un cours ou demande un exercice.
    """
    historique = _tour("je m'appelle Awa", "Bonjour Awa !")
    for question in (
        "Fais-moi un cours sur les nombres complexes",  # cours
        "Donne-moi un exercice sur le calcul intégral",  # entraînement
        "Comment calculer un module ?",  # exercice
        "quels chapitres as-tu ?",  # méta
    ):
        resultat = await agent_qa.respond(
            question, {"serie": "S2"}, session_eleve, conversation_history=historique
        )
        assert "Awa" in resultat.final_prompt, question
