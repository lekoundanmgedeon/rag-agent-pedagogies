"""Cas QA #19 et #21 — découragement et abandon (Tony SARRE).

* #19 « Je suis nul en maths, ça sert à rien d'essayer » — l'agent recolle un
  paragraphe de cours au lieu d'encourager l'élève.
* #21 « C'est trop dur, je laisse tomber » — réponse quasi identique aux deux
  précédentes.

**Ce fichier ne clôt ni l'un ni l'autre.** Il protège la seule moitié livrable :
la **détection**. Les deux cas restent ``en_cours``, et aucun n'est enregistré
dans ``attentes.ATTENTES`` — ils continuent donc de ressortir en ``xfail`` dans
le rejeu générique, comme les cas non traités qu'ils sont encore. Même patron
que le cas #5 (cf. ``test_qa_05_hors_perimetre``), pour la même raison : la
mécanique est en place, le verdict manque.

Ce qui bloque, et pourquoi c'est bien un blocage :

* **#19 → D5, point 1.** La décision du 2026-08-13 tranche l'ordre des travaux
  (« combler la détection d'abord ») et laisse ouvert ce qu'il faut *faire* du
  signal : disjoncteur déterministe comme le cas #7, ou modulation du ton. Le
  débat portait jusqu'ici sur un signal que rien ne produisait — sondé, le
  prompt sortait à ``frustration_score = 0.0``, quand « je ne comprends pas »
  sortait à 0,4. C'est ce trou-là qui est comblé ici.
* **#21 → D2.** L'action recommandée porte sur la **variété** de la prose de
  soutien, qu'aucune assertion de couche A ne peut juger : ``MockLLM`` renvoie
  une constante. Ce qui était en revanche mesurable et arbitraire, c'est que
  « j'abandonne » comptait comme marqueur et « je laisse tomber » non.

Le corollaire nommé dans D5 est le **faux positif** : un motif de découragement
écrit large capterait « je suis nul en maths » au sens de « j'ai du mal », le
message même que l'élève envoie *en travaillant*. La moitié basse de ce fichier
est consacrée à cette borne.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.frustration import (
    SessionState,
    detect_frustration,
    detecte_un_decouragement,
)
from agent_tuteur.agent.securite import detecter_detresse

from . import assertions
from .cas import cas_positifs, par_id, tous_les_cas

CAS_19 = par_id(tous_les_cas())[19]
CAS_21 = par_id(tous_les_cas())[21]


# --- Cas #19 : le prompt exact du testeur ------------------------------------


async def test_le_prompt_19_produit_enfin_un_signal(agent_qa, session_eleve):
    """0.0 → 0.4. Le découragement était invisible de bout en bout du pipeline."""
    resultat = await agent_qa.respond(CAS_19.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["decouragement"] is True
    assert resultat.trace["frustration_score"] > 0.0, (
        "le découragement du cas #19 n'est détecté par rien"
    )


async def test_le_prompt_19_expose_le_signal_dans_la_trace(agent_qa, session_eleve):
    """Le signal doit être lisible là où il sera exploité (D5, point 1).

    Noyé dans le score agrégé, il serait indiscernable d'une difficulté
    ordinaire — or c'est précisément la distinction sur laquelle porte D5.
    """
    prepared = await agent_qa.prepare(CAS_19.prompt, {"serie": "S2"}, session_eleve)

    entree = next(e for e in prepared.node_trace if e["node"] == "detect_frustration")
    assert entree["decouragement"] is True
    assert prepared.trace["decouragement"] is True
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


async def test_le_prompt_19_ne_declenche_pas_le_disjoncteur_de_securite(
    agent_qa, session_eleve
):
    """Contrepartie de D5 : la détection ne préjuge pas du routage.

    Reclasser le #19 en périmètre sécurité reste à trancher. Tant que ce n'est
    pas fait, combler la détection ne doit **pas** avoir détourné le tour vers
    la réponse de mise en sécurité par un effet de bord — ce serait prendre la
    décision à la place de l'humain, sur un périmètre qui exige justement sa
    validation explicite.
    """
    resultat = await agent_qa.respond(CAS_19.prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_aucun_court_circuit_securite(resultat)
    assert detecter_detresse(CAS_19.prompt).detectee is False


# --- Cas #21 : le prompt exact du testeur ------------------------------------


async def test_le_prompt_21_compte_ses_deux_signaux(agent_qa, session_eleve):
    """« c'est trop dur » ET « je laisse tomber » : 0,4 → 0,8."""
    resultat = await agent_qa.respond(CAS_21.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["frustration_score"] >= 0.5
    assert resultat.trace["hint_level"] > 1, (
        "l'élève annonce qu'il abandonne et reçoit le même niveau d'indice"
    )


def test_deux_facons_de_dire_qu_on_abandonne_valent_pareil():
    """L'asymétrie corrigée : « j'abandonne » comptait, « je laisse tomber » non."""
    session = SessionState()

    assert detect_frustration("j'abandonne", session).markers == 1
    assert detect_frustration("je laisse tomber", SessionState()).markers == 1


# --- Au-delà des prompts exacts ----------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Je suis nul en maths, ça sert à rien d'essayer",
        "je suis nul en maths",
        "je suis vraiment nulle",
        "je ne suis pas fait pour les maths",
        "ça sert à rien de travailler, j'y arriverai jamais",
        "je n'y arriverai jamais",
        "je comprendrai jamais les maths",
        "je suis un cas désespéré",
    ],
)
def test_le_decouragement_est_detecte(question):
    assert detecte_un_decouragement(question) is True


@pytest.mark.parametrize(
    "question",
    [
        # Difficulté ordinaire : l'élève travaille, il ne se dévalorise pas.
        "j'ai du mal en maths",
        "c'est difficile",
        "C'est trop dur, je laisse tomber",
        "Je ne comprends pas les dérivées",
        "je bloque sur cette question",
        "je dois faire cet exercice tout seul",
        # « nul » qui n'est pas un jugement de valeur.
        "je suis nulle part dans le tableau de variation",
        "le discriminant est nul",
        # Le sujet du découragement n'est pas l'élève.
        "à quoi ça sert les nombres complexes ?",
        "ça sert à rien d'apprendre par cœur ?",
    ],
)
def test_une_difficulte_ordinaire_n_est_pas_un_decouragement(question):
    """Le faux positif nommé par D5 : capter l'élève qui travaille."""
    assert detecte_un_decouragement(question) is False


def test_le_decouragement_seul_ne_fait_pas_escalader():
    """0,4 : sous le seuil de 0,5. Le signal existe, il ne décide pas encore.

    C'est l'ordre demandé par D5 — combler la détection sans trancher le
    routage. Un poids qui aurait franchi le seuil à lui seul aurait pris la
    décision par la bande.
    """
    signal = detect_frustration("je suis nul en maths, ça sert à rien d'essayer", SessionState())

    assert signal.decouragement is True
    assert signal.markers == 0
    assert signal.score == pytest.approx(0.4)


def test_le_score_reste_borne_avec_le_nouveau_terme():
    session = SessionState(recent_questions=["je suis nul, je comprends pas"] * 3)
    signal = detect_frustration(
        "je suis nul, je comprends pas, ça fait 3 fois que tu m'expliques", session
    )

    assert signal.score <= 1.0


# --- Non-régression ----------------------------------------------------------


@pytest.mark.parametrize("cas", cas_positifs(), ids=[c.identifiant_test for c in cas_positifs()])
def test_aucune_fixture_positive_n_est_lue_comme_un_decouragement(cas):
    """Les 13 comportements validés, dont #53 « j'ai pas le temps »."""
    assert detecte_un_decouragement(cas.prompt) is False


@pytest.mark.parametrize("cas", cas_positifs(), ids=[c.identifiant_test for c in cas_positifs()])
async def test_aucune_fixture_positive_ne_change_de_niveau_d_indice(
    cas, agent_qa, session_eleve
):
    """La contrepartie du nouveau terme : il ne doit pas faire monter les autres.

    Un score gonflé ferait franchir le seuil d'escalade à des tours validés —
    notamment les refus (#57 à #61), dont c'est justement la fermeté qui a été
    confirmée.
    """
    prepared = await agent_qa.prepare(cas.prompt, {"serie": "S2"}, session_eleve)

    assert prepared.trace.get("decouragement") in (None, False)
