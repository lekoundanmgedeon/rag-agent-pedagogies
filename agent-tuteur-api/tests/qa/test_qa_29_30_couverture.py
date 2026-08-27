"""Cas QA #29 et #30 — hors-périmètre jamais signalé sur un tour conceptuel.

* **#29** « donne moi les inegalites remarquables » (Mohamed FAYE) : l'agent
  dévie vers le calcul intégral sans jamais dire qu'il n'a pas ce prérequis.
* **#30** « Je comprends pas pourquoi la dérivée de x² c'est 2x, d'où ça vient ? »
  (Tony SARRE) : un indice sans rapport (factorisation) au lieu du signalement.

**Pourquoi ces deux cas ont attendu.** Le seuil de pertinence du cas #5 décide
l'appartenance au périmètre par *consensus de chapitre* : il mesure l'accord du
top-k, et reste donc aveugle quand tout le top-k se trompe **ensemble** — ce que
la décision D7 a nommé et mesuré (« les dérivées ressemblent au calcul intégral
bien plus qu'aux nombres complexes »). D7 laissait trois voies ouvertes ; c'est
la troisième qui est mise en œuvre ici : **une liaison par titre restreinte aux
tours conceptuels**, le sous-classement d'intention qu'elle demandait de
concevoir et de mesurer.

**Ce qui rend la vérification sûre**, et que ces tests gèlent : elle ne
s'applique jamais à un énoncé apporté par l'élève. Un énoncé ne nomme pas son
chapitre — « z = 3 + 4i » ne contient pas le mot « complexes » — et c'est ce qui
avait fait fermer la voie « liaison par titre » en mode exercice. La borne est
la présence d'un verbe de résolution ; elle protège le cas critique **#6** et la
fixture positive **#55**, tous deux vérifiés ici.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.course_plan import notion_couverte_par_le_catalogue
from agent_tuteur.agent.intent import est_un_tour_conceptuel
from agent_tuteur.agent.prompt import CONSIGNE_HORS_PERIMETRE, CONSIGNE_LAISSER_LE_CHOIX

from .cas import par_id, tous_les_cas

CAS = par_id(tous_les_cas())
CATALOGUE_FIGE = ["Les Nombres Complexes", "Le Calcul Intégral"]
CATALOGUE_PRODUCTION = ["Dérivation", "Fonction dérivée et équation de la tangente", "Suites numériques"]


# --- La borne : conceptuel contre énoncé -------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "donne moi les inegalites remarquables",
        "Je comprends pas pourquoi la dérivée de x² c'est 2x, d'où ça vient ?",
        "c'est quoi une primitive ?",
        "quelle est la différence entre une limite et une dérivée ?",
        "que signifie « fonction bijective » ?",
    ],
)
def test_un_tour_conceptuel_est_reconnu(question):
    assert est_un_tour_conceptuel(question), question


@pytest.mark.parametrize(
    "question",
    [
        # L'élève apporte son matériel : le corpus n'a aucune raison de le nommer.
        "z = 3 + 4i : partie réelle, imaginaire, conjugué, module",  # cas #6
        "Calcule la dérivée de la fonction f(x) = x²·ln(x) et détaille chaque étape.",  # #55
        "Résous x² - 5x + 6 = 0",
        "démontre que la suite est croissante",
        "corrige mon exercice",
    ],
)
def test_un_enonce_apporte_par_l_eleve_n_est_jamais_verifie(question):
    assert not est_un_tour_conceptuel(question), question


def test_la_couverture_se_juge_sur_les_titres_reellement_indexes():
    # Ce que le corpus figé de la démo ne couvre pas…
    assert not notion_couverte_par_le_catalogue(CAS[29].prompt, CATALOGUE_FIGE)
    assert not notion_couverte_par_le_catalogue(CAS[30].prompt, CATALOGUE_FIGE)
    # …et ce qu'un corpus élargi couvre : le verdict suit le corpus, il n'est pas
    # écrit en dur. Sans rapprochement morphologique, « dériver » ne se lierait
    # pas à « Dérivation » et la fixture positive #54 serait déclarée à tort
    # hors périmètre sur le corpus de production.
    assert notion_couverte_par_le_catalogue(CAS[30].prompt, CATALOGUE_PRODUCTION)
    assert notion_couverte_par_le_catalogue(
        "Comment dériver un quotient de fonctions ?", CATALOGUE_PRODUCTION
    )


def test_une_question_sans_terme_de_sujet_reste_couverte():
    """Défaut de sûreté : sans matière à juger, on ne déclare rien.

    Mieux vaut servir des extraits imparfaits — le comportement d'avant — que
    d'annoncer à un élève que son chapitre n'existe pas sur la foi de rien.
    """
    assert notion_couverte_par_le_catalogue("pourquoi ?", CATALOGUE_FIGE)
    assert notion_couverte_par_le_catalogue("c'est quoi ?", CATALOGUE_FIGE)


# --- Les deux prompts des testeurs, rejoués ----------------------------------


@pytest.mark.parametrize("cid", [29, 30])
async def test_le_hors_perimetre_est_declare_et_la_main_rendue(cid, agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS[cid].prompt, {"serie": "S2"}, session_eleve)

    assert resultat.retrieved == [], (
        "des extraits étrangers sont servis : c'est là-dessus que l'agent dérivait — "
        f"{[sc.chunk.metadata.chapitre for sc in resultat.retrieved]}"
    )
    assert resultat.trace["hors_perimetre"] is True
    assert resultat.trace["sources"] == []
    assert CONSIGNE_HORS_PERIMETRE in resultat.final_prompt
    # Avouer ne suffit pas : le cas #40 exige aussi de laisser l'élève décider
    # de la suite plutôt que d'enchaîner.
    assert CONSIGNE_LAISSER_LE_CHOIX in resultat.final_prompt

    entree = next(e for e in resultat.node_trace if e["node"] == "retrieve_context")
    assert entree["notion_hors_catalogue"] is True


async def test_le_cas_6_garde_ses_extraits(agent_qa, session_eleve):
    """Le cas critique #6 est clos : la vérification ne doit pas le rouvrir.

    C'est le risque que D7 avait mesuré en fermant la voie « liaison par titre »
    en mode exercice — aucun terme de « z = 3 + 4i… » ne recoupe « Les Nombres
    Complexes », et le déclarer hors périmètre ferait échouer un cas clos.
    """
    resultat = await agent_qa.respond(CAS[6].prompt, {"serie": "S2"}, session_eleve)
    chapitres = {sc.chunk.metadata.chapitre for sc in resultat.retrieved}
    assert chapitres == {"Les Nombres Complexes"}
    assert resultat.trace["hors_perimetre"] is False
