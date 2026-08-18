"""Cas QA #14 — « Je ne comprends pas les dérivées » (Pontiane).

Observé : l'agent reformule deux fois la question ; il faut trois prompts avant
d'obtenir une information utile.

Cause racine mesurée, en deux temps.

**Ce que D4 avait relevé** : le tour partait en intention ``exercice`` et
recevait cinq extraits « Les Nombres Complexes » — les dérivées ne sont dans
aucun chapitre indexé. Nourrir le modèle de cours étranger est une cause directe
de la reformulation à vide : le niveau 1 lui prescrit de « rappeler la règle
utile SANS l'appliquer », et la seule règle qu'on lui donne parle d'autre chose.

**Ce que D4 supposait, et qui est faux** : que cette moitié serait réglée par le
cas #5 (seuil de périmètre). Sondé sur BGE-M3, l'embedder de production, ce
prompt remonte cinq extraits « Le Calcul Intégral » — unanimes, donc
``hors_perimetre`` reste **faux**. Le consensus de chapitre mesure l'*accord* du
top-k ; il ne peut rien contre un top-k unanime sur le mauvais chapitre. Le cas
#14 n'hérite donc pas du correctif du #5 (cf. D7).

**Le correctif retenu porte ailleurs, sur le routage.** « Je veux comprendre les
dérivées » ouvrait un cours ; « Je ne comprends pas les dérivées » partait en
exercice. Les deux phrases disent la même chose, et cette asymétrie était le
défaut. Une fois le tour routé en cours, la machinerie qui manquait est déjà là
et déjà testée : ``resolve_chapitre`` lie le chapitre au **titre** demandé — pas
à une similarité vectorielle — échoue sur « dérivées », et le prompt reçoit
l'avertissement de couverture qui interdit d'enseigner un autre chapitre à la
place.

Ce que la couche A prouve ici : le routage, l'échec de liaison, l'avertissement
émis, et l'absence de consigne de reformulation. Que la prose soit effectivement
utile dès le premier tour relève de la couche B, donc de D2.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.hint_strategy import HINT_INSTRUCTIONS
from agent_tuteur.agent.intent import (
    Intent,
    classify_intent,
    declare_ne_pas_comprendre_une_notion,
)

from . import assertions
from .cas import cas_positifs, par_id, tous_les_cas

CAS_14 = par_id(tous_les_cas())[14]

#: La consigne de niveau 0, littéralement « Reformule la question de l'élève ».
#: C'est elle que la testeuse a vue à l'œuvre — le reproche portait sur une
#: consigne réellement émise, pas sur une dérive du modèle.
CONSIGNE_DE_REFORMULATION = HINT_INSTRUCTIONS[0]


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_ouvre_un_cours(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_14.prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_intention(resultat, "cours")


async def test_le_prompt_exact_avoue_que_le_chapitre_n_est_pas_couvert(
    agent_qa, session_eleve
):
    """Le cœur du cas : ne pas enseigner les complexes à qui demande les dérivées."""
    prepared = await agent_qa.prepare(CAS_14.prompt, {"serie": "S2"}, session_eleve)

    assert prepared.trace["course"]["chapitre_confirmed"] is False, (
        "un chapitre a été lié à une demande qu'il ne recouvre pas"
    )
    assert "le chapitre demandé n'a pas pu être identifié" in prepared.final_prompt
    assert "n'enseigne SURTOUT PAS un autre chapitre à la place" in prepared.final_prompt


async def test_le_prompt_exact_ne_demande_plus_de_reformuler(agent_qa, session_eleve):
    """La branche cours n'a pas de graduation socratique : rien à reformuler."""
    prepared = await agent_qa.prepare(CAS_14.prompt, {"serie": "S2"}, session_eleve)

    assert CONSIGNE_DE_REFORMULATION not in prepared.final_prompt
    assert prepared.trace["hint_level"] is None
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


async def test_le_sujet_cite_au_modele_est_lisible(agent_qa, session_eleve):
    """Le sujet est repris dans le prompt et peut être répété à l'élève.

    Sans nettoyage des verbes d'incompréhension, il s'écrivait « comprends pas
    dérivées » — une phrase que le modèle est explicitement autorisé à citer.
    """
    prepared = await agent_qa.prepare(CAS_14.prompt, {"serie": "S2"}, session_eleve)

    assert "« dérivées »" in prepared.final_prompt, prepared.final_prompt[:400]


# --- Au-delà du prompt exact -------------------------------------------------
# Corriger « Je ne comprends pas les dérivées » à la lettre serait un correctif
# de prompt exact. Ce qui est corrigé est l'asymétrie entre deux façons de
# demander la même chose.


@pytest.mark.parametrize(
    "question",
    [
        "Je ne comprends pas les dérivées",
        "je comprends pas les intégrales",
        "j'ai rien compris aux nombres complexes",
        "je n'ai pas compris la trigonométrie",
        "je comprends rien à la dérivation",
        "je ne comprends pas l'intégration",
        "j'y pige rien aux logarithmes",
    ],
)
def test_une_incomprehension_sur_une_notion_ouvre_un_cours(question):
    assert declare_ne_pas_comprendre_une_notion(question) is True
    assert classify_intent(question).intent is Intent.COURS


@pytest.mark.parametrize(
    "question",
    [
        # Rien n'est nommé : l'élève bute sur l'exercice en cours.
        "je ne comprends pas",
        "je ne comprends pas pourquoi",
        "je ne trouve pas",
        "je comprends pas, donne-moi la réponse",
        # Ce qui est nommé est le matériel du tour, pas une notion.
        "je ne comprends pas la question",
        "je n'ai pas compris l'énoncé",
        "je ne comprends pas cet exercice",
        "je ne comprends pas la correction",
        "je n'ai pas compris la démonstration",
        "je ne comprends pas la dernière étape",
        "je n'ai pas compris le calcul",
        # Cas #20 : une déclaration de répétition, pas une demande de cours.
        "Ça fait 3 fois que tu m'expliques, je comprends pas",
    ],
)
def test_une_difficulte_sur_le_tour_en_cours_reste_socratique(question):
    """Le faux positif est le risque : basculer en cours sur « je ne comprends
    pas » abandonnerait l'exercice que l'élève est en train de faire."""
    assert declare_ne_pas_comprendre_une_notion(question) is False
    assert classify_intent(question).intent is Intent.EXERCICE


def test_en_plein_cours_l_incomprehension_reste_une_sous_question():
    """« Je n'ai pas compris le module » pendant un cours ne le redémarre pas.

    Le module est bien une notion ; en plein cours c'est néanmoins la section
    courante qu'il faut reprendre, pas un nouveau chapitre. La borne est portée
    par ``_detect_navigation``, qui ne consulte ce signal que hors cours.
    """
    decision = classify_intent("je n'ai pas compris le module", in_course=True)

    assert decision.intent is Intent.COURS
    assert decision.navigation is None, "un cours en route a été redémarré"


# --- Non-régression ----------------------------------------------------------


@pytest.mark.parametrize("cas", cas_positifs(), ids=[c.identifiant_test for c in cas_positifs()])
def test_aucune_fixture_positive_ne_bascule_en_cours(cas):
    """Les 13 comportements validés ne changent pas de branche.

    Trois d'entre eux portent sur un hors-périmètre bien géré (#50 à #52) et
    quatre sur des refus (#57 à #61) : les faire changer de posture reviendrait
    à rejouer leur verdict sans l'avoir demandé.
    """
    assert declare_ne_pas_comprendre_une_notion(cas.prompt) is False
