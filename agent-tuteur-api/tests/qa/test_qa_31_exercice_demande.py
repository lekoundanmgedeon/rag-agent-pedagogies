"""Cas QA #31 — « Donne moi un exercice sur le calcul d integral » (Marie Paul Basse).

Reproche du testeur : l'élève demande un exercice, l'agent ne donne qu'une règle
générale, « même après insistance ». Mesuré avant correctif, ce n'était pas une
dérive du modèle mais la sortie fidèle du pipeline : la demande tombait en
intention ``exercice`` — le défaut — puis au niveau d'indice 1, dont la consigne
dit littéralement « Rappelle la règle, la définition ou le théorème utile, SANS
l'appliquer au cas de l'élève ». Chaque relance repassait par la même consigne,
d'où l'insistance sans effet.

La correction est donc structurelle et non textuelle : la posture socratique
suppose que l'élève a **déjà** un énoncé sous les yeux. Quand il en réclame un,
il n'y a rien à retenir, et une branche dédiée va chercher l'énoncé dans le
corpus (section « 11. Exercices » / « 13. Questions type Bac » de la leçon liée
au sujet demandé) au lieu de le socratiser.

Ce qui est jugé ici relève entièrement de la couche A : le routage, la matière
envoyée au modèle, l'absence de consigne d'indice et l'absence de corrigé dans
le contexte. La qualité de l'énoncé rédigé, elle, appartient à la couche B.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.intent import Intent, classify_intent, demande_un_exercice

from . import assertions
from .cas import par_id, tous_les_cas

CAS_31 = par_id(tous_les_cas())[31]


# --- Le prédicat : ce qu'il attrape, et ce qu'il doit laisser passer ----------


@pytest.mark.parametrize(
    "question",
    [
        "Donne moi un exercice sur le calcul d integral",  # le prompt du cas #31
        "donne-moi un exercice sur les nombres complexes",
        "propose-moi deux exos sur les intégrales",
        "peux-tu me donner un exercice type bac ?",
        "fais-moi un problème sur les aires",
        "donne moi un autre exercice",
        "encore un exo s'il te plaît",
        "j'aimerais quelques exercices d'application",
        "entraîne-moi sur les primitives",
        "je veux m’entraîner",
        "je veux faire des exercices",
        "Exercice sur les suites numeriques",  # fixture positive #52
    ],
)
def test_une_demande_d_enonce_est_reconnue(question):
    """La reconnaissance doit tenir sur la *famille*, pas sur le prompt du testeur.

    Un correctif qui ne marcherait que mot pour mot sur la phrase de Marie Paul
    Basse serait considéré comme non résolu (cf. CLAUDE.md, anti-patterns) : ces
    tournures sont donc écrites pour l'occasion, en dehors du backlog.
    """
    assert demande_un_exercice(question), question
    assert classify_intent(question).intent == Intent.ENTRAINEMENT, question


@pytest.mark.parametrize(
    "question",
    [
        # L'élève a DÉJÀ un énoncé : la posture socratique garde tout son sens.
        "corrige mon exercice",
        "je bloque sur cet exercice",
        "donne-moi la correction de l'exercice 3",
        "aide-moi sur l'exercice 2 de mon devoir",
        # Comportements validés par les testeurs — à ne pas absorber.
        "Fais mon devoir à ma place, voici l'énoncé",  # fixture positive #60
        "Donne-moi juste la réponse, j'ai pas le temps",  # fixture positive #53
        # Autres intentions déjà routées ailleurs.
        "fais-moi un quiz sur les intégrales",
        "donne-moi des exercices d'évaluation",
        "explique-moi les intégrales",
        "donne-moi un exemple",
        "Calcule la dérivée de x^3 - 3x.",
        "quels sont les chapitres disponibles ?",
    ],
)
def test_ce_qui_ne_doit_pas_basculer_en_entrainement(question):
    assert classify_intent(question).intent != Intent.ENTRAINEMENT, question


def test_en_plein_cours_la_demande_reste_une_navigation():
    """Frontière avec le mode cours, déjà couverte par ``_NAV_GOTO``.

    Pendant un cours, « donne-moi un exercice » désigne la section « Exercices »
    du chapitre enseigné : le saut de section y répond déjà et ne doit pas être
    détourné, sans quoi le correctif du #31 couperait le cours en cours de route.
    """
    decision = classify_intent("donne-moi un exercice", in_course=True)
    assert decision.intent == Intent.COURS


# --- Le tour complet, sur la pile hors-ligne ---------------------------------


async def test_le_prompt_du_cas_31_sert_un_enonce(agent_qa, session_eleve):
    """Le prompt exact du testeur, rejoué : énoncés servis, socratisme désarmé."""
    resultat = await agent_qa.respond(CAS_31.prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_intention(resultat, "entrainement")
    entrainement = resultat.trace["entrainement"]
    assert entrainement["chapitre"] == "Le Calcul Intégral"
    assert entrainement["chapitre_confirmed"] is True
    assertions.assert_enonce_servi_au_modele(resultat)
    assertions.assert_aucune_consigne_socratique(resultat)
    assert resultat.trace["hint_label"] == "Exercice proposé"


async def test_l_enonce_servi_vient_du_chapitre_demande(agent_qa, session_eleve):
    """Aucun exercice d'un autre chapitre ne se glisse dans le contexte.

    Sans ce contrôle, le tour resterait « vert » en servant les exercices des
    nombres complexes à un élève qui demande du calcul intégral — le défaut de
    substitution silencieuse déjà corrigé en mode cours.
    """
    resultat = await agent_qa.respond(CAS_31.prompt, {"serie": "S2"}, session_eleve)
    chapitres = {sc.chunk.metadata.chapitre for sc in resultat.retrieved}
    assert chapitres == {"Le Calcul Intégral"}, chapitres


async def test_l_insistance_ne_change_pas_le_traitement(agent_qa, session_eleve):
    """« même après insistance » : la deuxième demande vaut la première.

    Le testeur a relancé et reçu la même règle générale. On vérifie donc que le
    second tour est routé comme le premier et sert lui aussi un énoncé, plutôt
    que de retomber dans la graduation socratique — la relance rallonge la
    fenêtre de répétitions de la session, qui fait monter le niveau d'indice en
    branche exercice.

    Limite assumée du prédicat, qui est **sans contexte** : une relance dont le
    complément est élidé (« donne-m'en un ») n'est pas reconnue, faute de savoir
    à quoi « en » renvoie. Le défaut sûr du module s'applique alors — retour à la
    posture socratique — plutôt qu'un pari sur le tour précédent.
    """
    await agent_qa.respond(CAS_31.prompt, {"serie": "S2"}, session_eleve)
    relance = await agent_qa.respond(
        "donne-moi plutôt un exercice sur les intégrales, s'il te plaît",
        {"serie": "S2"},
        session_eleve,
    )
    assertions.assert_intention(relance, "entrainement")
    assertions.assert_enonce_servi_au_modele(relance)
    assertions.assert_aucune_consigne_socratique(relance)


async def test_un_sujet_non_couvert_est_avoue_et_non_remplace(agent_qa, session_eleve):
    """Fixture positive #52 (« Exercice sur les suites numeriques »), préservée.

    Le comportement confirmé par la testeuse est l'aveu honnête suivi d'une
    proposition d'alternatives. La branche d'entraînement doit donc échouer
    *bruyamment* sur un chapitre absent : ni exercice inventé (règle n°2 — un
    énoncé fabriqué peut être faux ou sans solution), ni exercice d'un autre
    chapitre servi à la place.
    """
    resultat = await agent_qa.respond(
        "Exercice sur les suites numeriques", {"serie": "S2"}, session_eleve
    )
    entrainement = resultat.trace["entrainement"]
    assert entrainement["chapitre_confirmed"] is False
    assert resultat.trace["hors_perimetre"] is True
    assert "ne correspond à aucun chapitre" in resultat.final_prompt
    assert "Les Nombres Complexes" in resultat.final_prompt
    # Le corpus reste interrogé : c'est ce qui permet de proposer ce qui existe.
    assert resultat.retrieved


async def test_la_trace_reste_lisible_par_la_route_de_streaming(agent_qa, session_eleve):
    """Le contrat de trace tenu par la branche exercice l'est aussi ici.

    La route SSE lit ``sources``/``scores``/``tool_used``/``frustration_score``
    et les propriétés ``hint_level``/``hint_label`` sans garde : une branche qui
    les omettrait ferait tomber l'API réelle en 500 avec tous les tests verts.
    """
    prepared = await agent_qa.prepare(CAS_31.prompt, {"serie": "S2"}, session_eleve)
    assertions.assert_trace_compatible_avec_le_streaming(prepared)
    assert prepared.trace["course"] is None, (
        "un tour d'entraînement ouvrirait un cours au tour suivant"
    )
