"""Cas QA #20 — « Ça fait 3 fois que tu m'expliques, je comprends pas ».

Testeur : Tony SARRE. Observé : l'élève signale avoir déjà entendu la même
explication trois fois ; l'agent redonne presque le même texte.

Cause racine mesurée : la répétition n'était comptée que lorsqu'elle était
**observée** — ``count_repetitions`` compare la question courante aux questions
récentes par similarité de Jaccard. Or « Ça fait 3 fois que tu m'expliques » ne
ressemble à aucune question précédente : c'est une *déclaration* de blocage, pas
une répétition de question. Le signal le plus fiable disponible — l'élève le dit
lui-même — n'était lu par personne.

Conséquence chiffrée : score de frustration 0,4 (le seul marqueur « je comprends
pas »), juste sous le seuil d'escalade de 0,5. L'agent restait au niveau 1
« Rappelle la règle », c'est-à-dire le même registre une quatrième fois.

Le correctif a deux moitiés, et la seconde est la vraie réponse au testeur :
le blocage déclaré alimente le score (donc la graduation monte), **et** injecte
une consigne de variation de forme. Monter d'un cran sans changer d'angle
aurait laissé le reproche intact — il ne portait pas sur le niveau mais sur la
répétition du même texte.

Ce que la couche A prouve ici : le signal est détecté, la stratégie change, la
consigne part. Que la prose soit effectivement *différente* de la précédente
relève de la couche B — ``MockLLM`` renvoie une constante — donc de D2.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.frustration import (
    SessionState,
    detect_frustration,
    detecte_un_blocage_declare,
)
from agent_tuteur.agent.prompt import CONSIGNE_VARIATION_APPROCHE

from . import assertions
from .cas import cas_positifs, par_id, tous_les_cas

CAS_20 = par_id(tous_les_cas())[20]


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_est_reconnu_comme_un_blocage_declare(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_20.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["blocage_declare"] is True
    entree = next(e for e in resultat.node_trace if e["node"] == "detect_frustration")
    assert entree["blocage_declare"] is True


async def test_le_prompt_exact_franchit_le_seuil_d_escalade(agent_qa, session_eleve):
    """0,4 → 0,7 : le blocage déclaré pèse autant qu'une répétition observée."""
    resultat = await agent_qa.respond(CAS_20.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["frustration_score"] >= 0.5
    assert resultat.trace["hint_level"] > 1, (
        "l'agent reste au même niveau après trois explications infructueuses"
    )


async def test_le_prompt_exact_impose_un_changement_d_approche(agent_qa, session_eleve):
    """Le cœur du cas : ne pas se contenter de monter d'un cran."""
    prepared = await agent_qa.prepare(CAS_20.prompt, {"serie": "S2"}, session_eleve)

    assert CONSIGNE_VARIATION_APPROCHE in prepared.final_prompt
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


# --- Au-delà du prompt exact -------------------------------------------------
# Un correctif qui ne vaudrait que pour « ça fait 3 fois » serait un correctif
# de prompt exact, ce que CLAUDE.md classe en non-résolu.


@pytest.mark.parametrize(
    "question",
    [
        "Ça fait 3 fois que tu m'expliques, je comprends pas",
        "ca fait deux fois que tu m'expliques la même chose",
        "tu m'as déjà expliqué ça",
        "tu répètes toujours la même chose",
        "c'est la troisième fois que je pose la question",
        "je comprends toujours pas",
        "tu dis toujours la même chose",
    ],
)
def test_les_declarations_de_blocage_sont_detectees(question):
    assert detecte_un_blocage_declare(question) is True


@pytest.mark.parametrize(
    "question",
    [
        "Je ne comprends pas les dérivées",              # cas #14 — difficulté simple
        "C'est trop dur, je laisse tomber",              # cas #21 — découragement, pas répétition
        "Comment calculer le module d'un nombre complexe ?",
        "explique-moi les nombres complexes",
        "1-1=?",
        "Résous x² − 5x + 6 = 0",
    ],
)
def test_une_difficulte_ordinaire_n_est_pas_un_blocage_declare(question):
    """Le faux positif est le risque principal : il crierait « je me répète »
    au premier tour d'une conversation, alors que rien n'a encore été dit."""
    assert detecte_un_blocage_declare(question) is False


def test_le_score_reste_borne_et_cumulable():
    session = SessionState()
    signal = detect_frustration("Ça fait 3 fois que tu m'expliques, je comprends pas", session)
    assert signal.blocage_declare is True
    assert signal.markers == 1
    assert signal.score == pytest.approx(0.7)

    session.recent_questions = ["Ça fait 3 fois que tu m'expliques, je comprends pas"] * 3
    sature = detect_frustration("Ça fait 3 fois que tu m'expliques, je comprends pas", session)
    assert sature.score <= 1.0


# --- Non-régression : le signal ne doit pas déborder -------------------------


@pytest.mark.parametrize("cas", cas_positifs(), ids=[c.identifiant_test for c in cas_positifs()])
async def test_aucune_fixture_positive_ne_declenche_la_variation(cas, agent_qa, session_eleve):
    """Les 13 comportements validés doivent rester intacts.

    Une consigne de variation injectée à tort demanderait au modèle de changer
    d'angle sur un refus (#57 à #61) ou sur un aveu de hors-périmètre (#50 à
    #52), là où c'est justement la constance qui a été validée.
    """
    prepared = await agent_qa.prepare(cas.prompt, {"serie": "S2"}, session_eleve)

    assert CONSIGNE_VARIATION_APPROCHE not in prepared.final_prompt


async def test_un_premier_tour_ordinaire_reste_socratique(agent_qa, session_eleve):
    """Contrôle de la contrepartie : sans déclaration, rien ne change."""
    prepared = await agent_qa.prepare(
        "Je ne comprends pas les dérivées", {"serie": "S2"}, session_eleve
    )

    assert prepared.trace["blocage_declare"] is False
    assert CONSIGNE_VARIATION_APPROCHE not in prepared.final_prompt
