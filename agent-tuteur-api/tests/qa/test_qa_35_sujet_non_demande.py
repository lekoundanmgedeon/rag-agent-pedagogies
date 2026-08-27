"""Cas QA #35 — « Expliques moi les dérivées » (Rahma) : réponse parlant des
nombres complexes, jamais demandés.

Le reproche porte sur un sujet introduit de nulle part. Mesuré, la cause n'est
pas une invention du modèle mais un **raté de routage sur une variante
d'accord** : ``_COURSE_START`` reconnaissait « explique-moi » et « expliquez-
moi », pas « expliques moi ». La phrase tombait donc en posture socratique de
niveau 1 — « rappelle la règle, la définition ou le théorème utile » — appliquée
aux cinq extraits remontés, tous du chapitre « Les Nombres Complexes ». Le sujet
non demandé était, une fois de plus, fourni par nous (cf. cas #16).

Une fois le tour routé en cours, ``resolve_chapitre`` lie le chapitre par titre :
sur le corpus figé (deux chapitres), les dérivées sont absentes et l'avertissement
de couverture interdit d'enseigner un autre chapitre à la place ; sur le corpus de
production, le vrai chapitre s'ouvre. Le verdict ci-dessous tient les deux cas,
pour la raison exposée dans ``attentes._cas_14_reformulation`` : exiger l'un des
deux ferait échouer ce test le jour où le corpus figé s'élargit.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.hint_strategy import HINT_INSTRUCTIONS
from agent_tuteur.agent.intent import Intent, classify_intent

from . import assertions
from .cas import par_id, tous_les_cas

CAS_35 = par_id(tous_les_cas())[35]


@pytest.mark.parametrize(
    "question",
    [
        "Expliques moi les dérivées",  # le prompt du cas #35
        "explique-moi les dérivées",
        "Explique moi les dérivées",
        "expliquez-moi les dérivées",
        "Expliquer les dérivées",
        "tu peux m'expliquer les dérivées ?",
        "présentes-moi les dérivées",
        "apprend moi les dérivées",
    ],
)
def test_une_faute_d_accord_ne_change_pas_de_branche(question):
    """La famille, pas la formulation : c'est ce qui distingue un correctif
    structurel d'un correctif pour le prompt exact du testeur."""
    assert classify_intent(question).intent == Intent.COURS, question


def test_le_constat_sur_les_tours_precedents_reste_socratique():
    """Frontière ouverte par le « s » : « tu m'expliques » n'est pas « explique-moi ».

    Le cas #20 (« Ça fait 3 fois que tu m'expliques, je comprends pas ») est un
    constat sur ce qui a déjà été dit, pas une demande de cours — l'y router
    ferait repartir un chapitre à zéro au moment précis où l'élève dit que ça ne
    passe pas.
    """
    for question in (
        "Ça fait 3 fois que tu m'expliques, je comprends pas",
        "je ne comprends rien à ce que tu m'expliques",
    ):
        assert classify_intent(question).intent != Intent.COURS, question


async def test_le_prompt_du_cas_35_n_introduit_aucun_sujet_etranger(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_35.prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_intention(resultat, "cours")
    # Aucune consigne socratique : c'est elle qui faisait « rappeler la règle »
    # d'un chapitre étranger faute de mieux.
    assert HINT_INSTRUCTIONS[1] not in resultat.final_prompt

    cours = resultat.trace["course"]
    assert cours is not None
    if cours["chapitre_confirmed"]:
        # Corpus de production : le vrai chapitre est ouvert, donc rien d'étranger.
        assert "dériv" in assertions._aplatir(cours["chapitre"])
    else:
        # Corpus figé : l'aveu, et l'interdiction de substituer un autre chapitre
        # — c'est exactement ce que la testeuse a vu se produire.
        assert "le chapitre demandé n'a pas pu être identifié" in resultat.final_prompt
        assert "n'enseigne SURTOUT PAS un autre chapitre à la place" in resultat.final_prompt
