"""Sprint 4 (priorité Basse) — cas #43, #46, #47 et #48.

Trois familles, et elles ne se corrigent pas au même endroit :

* **#43** « À quoi servent les mathématiques … ? » (Pierre Ndong) — la réponse de
  fond est jugée bonne ; c'est la relance finale (« attends la publication du
  programme ») qui est déplacée. Mesuré : la question tombait en intention
  ``exercice``, donc au niveau d'indice 1 sur cinq extraits pris au hasard, et la
  clôture s'inventait faute de cadre. Elle est désormais routée en orientation,
  avec une consigne qui exige d'y répondre pour de bon et interdit d'annoncer un
  contenu à venir.
* **#48** « je ne comprends pas la fonction » (Mohamed FAYE) — bonne définition,
  aucun exemple. La consigne de niveau 1 disait « SANS l'appliquer au cas de
  l'élève », ce que le modèle lisait comme « sans exemple ». La distinction est
  maintenant explicite : illustrer est obligatoire, appliquer à SON énoncé reste
  interdit. Même exigence dans l'introduction du plan de cours.
* **#46** et **#47** ne demandent aucun code ici : le premier est une question de
  couverture curriculaire (le comportement de l'agent est déjà correct, cf.
  ``test_le_chapitre_absent_est_avoue_sans_pivot``), le second est le rendu LaTeX
  déjà traité au cas #37 — ce qui se vérifie plutôt que se suppose.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.hint_strategy import HINT_INSTRUCTIONS
from agent_tuteur.agent.intent import Intent, classify_intent
from agent_tuteur.agent.prompt import CONSIGNE_UTILITE_DISCIPLINE

from . import assertions
from .cas import par_id, tous_les_cas

CAS = par_id(tous_les_cas())


# --- Cas 43 — question sur l'utilité de la discipline ------------------------


@pytest.mark.parametrize(
    "question",
    [
        "À quoi servent les mathématiques dans la vie de tous les jours et dans les études supérieures ?",
        "à quoi ça sert les maths ?",
        "pourquoi étudier les mathématiques",
        "les maths servent à quoi",
        "l'utilité des mathématiques",
    ],
)
def test_une_question_sur_la_discipline_est_une_orientation(question):
    assert classify_intent(question).intent == Intent.META, question


@pytest.mark.parametrize(
    "question",
    [
        # Frontière : l'utilité d'une NOTION est une question de contenu, et doit
        # continuer d'atteindre le corpus (frontière déjà nommée dans D5).
        "à quoi ça sert les nombres complexes ?",
        "à quoi sert la dérivée",
        "pourquoi apprendre les intégrales",
    ],
)
def test_l_utilite_d_une_notion_reste_du_contenu(question):
    assert classify_intent(question).intent != Intent.META, question


async def test_le_prompt_du_cas_43_repond_et_n_annonce_rien(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS[43].prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_intention(resultat, "meta")
    assertions.assert_pas_de_retrieval(resultat)
    assert CONSIGNE_UTILITE_DISCIPLINE in resultat.final_prompt
    assert resultat.trace["hint_reason"] == "question sur l'utilité de la discipline"
    # Le tour reste ancré sur les chapitres réels : la relance de clôture a de
    # quoi s'appuyer au lieu de s'inventer.
    for chapitre in ("Les Nombres Complexes", "Le Calcul Intégral"):
        assert chapitre in resultat.final_prompt


# --- Cas 48 — définition donnée sans exemple ---------------------------------


def test_la_consigne_de_niveau_1_exige_desormais_un_exemple():
    """Le cœur du #48 : « sans l'appliquer » ne veut pas dire « sans exemple »."""
    consigne = HINT_INSTRUCTIONS[1]
    assert "illustre" in consigne.lower()
    assert "exemple" in consigne.lower()
    # …et la retenue reste : on n'applique pas la règle à l'énoncé de l'élève.
    assert "Ne l'applique pas à SON énoncé" in consigne


async def test_l_introduction_d_un_cours_illustre_sa_definition(agent_qa, session_eleve):
    """L'autre moitié : une définition fondatrice servie nue, en mode cours."""
    resultat = await agent_qa.respond(
        "Fais-moi un cours sur les nombres complexes", {"serie": "S2"}, session_eleve
    )
    assert "exemple concret" in resultat.final_prompt


async def test_le_prompt_du_cas_48_demande_un_exemple(agent_qa, session_eleve):
    """« je ne comprends pas la fonction » : quelle que soit la branche prise.

    Le tour part en cours quand le chapitre existe, et reste en posture
    socratique sinon ; l'exigence d'illustrer doit tenir dans les deux cas,
    faute de quoi le correctif ne vaudrait que pour un corpus donné.
    """
    resultat = await agent_qa.respond(CAS[48].prompt, {"serie": "S2"}, session_eleve)
    prompt = resultat.final_prompt
    assert "exemple concret" in prompt or HINT_INSTRUCTIONS[1] in prompt


# --- Cas 46 et 47 — vérifiés plutôt que supposés -----------------------------


async def test_le_chapitre_absent_est_avoue_sans_pivot(agent_qa, session_eleve):
    """Cas #46 : la trigonométrie n'est pas indexée, et l'agent le dit déjà.

    Ce qui reste au cas #46 n'est pas un correctif de code mais une question de
    couverture — la trigonométrie doit-elle être au programme couvert ? — qui
    relève du processus de génération de contenu, hors de ce backlog.
    """
    resultat = await agent_qa.respond(CAS[46].prompt, {"serie": "S2"}, session_eleve)
    cours = resultat.trace["course"]
    assert cours is not None and cours["chapitre_confirmed"] is False
    assert "n'enseigne SURTOUT PAS un autre chapitre à la place" in resultat.final_prompt


async def test_le_cours_du_cas_47_part_au_format_pivot(agent_qa, session_eleve):
    """Cas #47 : même correctif que le #37, vérifié sur le prompt du testeur.

    Le prompt est en capitales et contient une faute (« COPLEXES ») : on vérifie
    au passage que la liaison du chapitre y survit, sans quoi le rendu serait le
    moindre des problèmes.
    """
    resultat = await agent_qa.respond(CAS[47].prompt, {"serie": "S2"}, session_eleve)
    assert resultat.trace["course"]["chapitre"] == "Les Nombres Complexes"
    for delimiteur in (r"\(", r"\)", r"\[", r"\]"):
        assert delimiteur not in resultat.final_prompt
