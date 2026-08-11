"""Cas QA #2, #3, #4 — questions méta traitées comme des questions de contenu.

- #2 « Quel est mon programme de cette année » (Pierre Ndong) → réponse sur
  l'intégrabilité des fonctions.
- #3 « Donne moi des astuces pour m'améliorer en maths ? » (Pierre Ndong) →
  même dérive.
- #4 « Quels sont les grands chapitres au programme … ? » (Pierre Ndong) →
  réponse confuse ; le testeur note que l'agent ne distingue pas questions
  générales et demandes d'exercice.

Cause racine commune : absence d'intention méta. Le correctif est un routage,
pas une règle de prompt — ces trois cas doivent donc se régler d'un seul geste,
et généraliser à des formulations que les testeurs n'ont pas employées.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.frustration import SessionState

from . import assertions
from .cas import cas_critiques, par_id

CAS = par_id(cas_critiques())

#: Ce que le corpus figé de la démo contient réellement.
CHAPITRES_INDEXES = {"Les Nombres Complexes", "Le Calcul Intégral"}


@pytest.mark.parametrize("cid", [2, 3, 4])
async def test_prompts_exacts_des_testeurs(cid, agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS[cid].prompt, {"serie": "S2"}, session_eleve)
    assertions.assert_intention(resultat, "meta")
    assertions.assert_pas_de_retrieval(resultat)


async def test_le_prompt_annonce_les_vrais_chapitres_et_seulement_eux(agent_qa):
    """Règles n°3 et n°4 : ni chapitre inventé, ni chapitre réel tu."""
    prepared = await agent_qa.prepare(CAS[4].prompt, {"serie": "S2"}, SessionState())
    assertions.assert_catalogue_honnete(prepared, CHAPITRES_INDEXES)


async def test_le_chemin_streaming_ne_lance_pas_de_retrieval(agent_qa):
    prepared = await agent_qa.prepare(CAS[2].prompt, {"serie": "S2"}, SessionState())
    assertions.assert_pas_de_retrieval(prepared)
    assertions.assert_trace_compatible_avec_le_streaming(prepared)
    assert "".join([tok async for tok in agent_qa.stream(prepared)]).strip()


# --- Généralisation : la cause racine, pas les trois formulations -------------


@pytest.mark.parametrize(
    "question",
    [
        # Programme / couverture.
        "Quel est mon programme de cette année",
        "quels sont les chapitres au programme ?",
        "qu'est-ce que tu as comme leçons ?",
        "sur quels chapitres peux-tu m'aider ?",
        "quelles leçons sont disponibles ?",
        # Méthode de travail.
        "Donne moi des astuces pour m'améliorer en maths ?",
        "des conseils pour progresser en maths",
        "comment réviser efficacement pour le bac ?",
        "quelle méthode pour mieux travailler les maths",
        # Capacités de l'agent.
        "qu'est-ce que tu sais faire ?",
        "comment tu fonctionnes ?",
    ],
)
async def test_les_questions_meta_ne_declenchent_aucun_retrieval(question, agent_qa):
    resultat = await agent_qa.respond(question, {"serie": "S2"}, SessionState())
    assertions.assert_intention(resultat, "meta")
    assertions.assert_pas_de_retrieval(resultat)


# --- Faux positifs : une question de contenu reste une question de contenu ----


@pytest.mark.parametrize(
    ("question", "intention"),
    [
        # Cas QA #5 : question de contenu hors périmètre. Elle NE doit PAS être
        # absorbée par le routeur méta — c'est le seuil de pertinence qui la
        # traite (ticket séparé), et l'y détourner masquerait le vrai défaut.
        ("Quelle est la différence entre une suite arithmétique et une suite géométrique ?",
         "exercice"),
        ("Calcule la dérivée de x³ − 3x", "exercice"),
        ("Comment dériver un quotient de fonctions ?", "exercice"),
        ("Fais-moi un cours sur les suites numériques", "cours"),
        ("Donne-moi les inégalités remarquables", "exercice"),
        ("fais-moi un quiz sur les nombres complexes", "quiz"),
        # Piège lexical : « chapitre » dans une demande de cours n'est pas méta.
        ("présente le chapitre sur les nombres complexes", "cours"),
    ],
)
async def test_les_questions_de_contenu_ne_sont_pas_absorbees(question, intention, agent_qa):
    resultat = await agent_qa.respond(question, {"serie": "S2"}, SessionState())
    assertions.assert_intention(resultat, intention)
