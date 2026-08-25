"""Cas QA #19 et #21 — découragement et abandon (Tony SARRE).

* #19 « Je suis nul en maths, ça sert à rien d'essayer » — l'agent recolle un
  paragraphe de cours au lieu d'encourager l'élève.
* #21 « C'est trop dur, je laisse tomber » — réponse quasi identique aux deux
  précédentes.

**Les deux cas sont clos ici**, en deux temps qu'il vaut mieux ne pas
confondre.

*La détection*, livrée d'abord (D5 : « combler le trou avant de trancher le
routage »). Sondé, le prompt du #19 sortait à ``frustration_score = 0.0`` quand
« je ne comprends pas » sortait à 0,4 : le découragement n'était détecté par
rien — ni par ``securite.py``, dont la frontière l'exclut volontairement, ni par
``frustration.py``, involontairement. Le débat sécurité-vs-ton portait sur un
signal que rien ne produisait.

*Le routage*, tranché le 2026-08-24 (D5, point 1) : **ouverture de soutien puis
reprise du cours**. Ni disjoncteur complet — l'élève resterait sans aide et le
message du cas #7 s'userait à force d'être servi sur du découragement scolaire —
ni simple consigne de prompt, qui n'aurait rien rendu vérifiable.

**Pourquoi ces deux cas ne dépendent plus de D2.** L'ouverture est écrite par
``soutien.py``, donc par le code : elle peut être *choisie* et *assérée*. C'est
ce qui règle le #21, dont la demande porte sur la variété — deux signaux
distincts reçoivent deux textes distincts, et deux découragements dans la même
session ne reçoivent pas le même paragraphe. La prose que le modèle ajoute
ensuite reste, elle, hors de portée de la couche A ; ce qui est vérifié ici,
c'est qu'il est prévenu de ne pas doubler l'ouverture.

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
from agent_tuteur.agent.hint_strategy import HINT_INSTRUCTIONS
from agent_tuteur.agent.securite import detecter_detresse
from agent_tuteur.agent.soutien import (
    SignalSoutien,
    choisir_ouverture,
    detecte_un_abandon,
    detecter_signal_soutien,
)

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
    """La borne basse de D5 : du découragement scolaire n'est pas de la détresse.

    Le reclassement en périmètre sécurité a été écarté le 2026-08-24, et c'est
    ce test qui tient la frontière : router « je suis nul en maths » vers la
    réponse de mise en sécurité userait le message du cas #7 — celui qu'un élève
    harcelé doit recevoir — en le servant à chaque découragement de contrôle.
    """
    resultat = await agent_qa.respond(CAS_19.prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_aucun_court_circuit_securite(resultat)
    assert detecter_detresse(CAS_19.prompt).detectee is False


async def test_le_prompt_19_ouvre_sur_du_soutien_avant_le_cours(agent_qa, session_eleve):
    """Le cœur du cas : « l'agent recolle un paragraphe de cours ».

    L'ouverture arrive **avant** la reprise pédagogique, et le tour continue —
    c'est la décision D5 dans les deux sens : dédramatiser d'abord, aider quand
    même ensuite.
    """
    resultat = await agent_qa.respond(CAS_19.prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_ouverture_de_soutien(resultat, signal="decouragement")
    assertions.assert_le_tour_pedagogique_continue(resultat)


async def test_le_prompt_19_previent_le_modele_de_ne_pas_doubler_l_ouverture(
    agent_qa, session_eleve
):
    """Sans cette consigne, l'élève reçoit deux préambules et toujours pas d'aide.

    C'est le reproche du cas #19 déplacé d'un cran plutôt que corrigé : le
    modèle, laissé libre, ouvre lui aussi sur de l'encouragement.
    """
    prepared = await agent_qa.prepare(CAS_19.prompt, {"serie": "S2"}, session_eleve)

    assert "une ouverture de soutien lui a DÉJÀ été adressée" in prepared.final_prompt
    assert prepared.preambule_soutien, "rien à émettre avant la génération streamée"
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


async def test_le_prompt_19_emet_l_ouverture_avant_le_premier_token_du_modele(
    agent_qa, session_eleve
):
    """Le chemin streamé doit produire la même réponse que le chemin complet.

    C'est le seul endroit où les deux peuvent diverger sans que rien ne le
    signale : la démo streame, les tests appellent ``respond``. Une ouverture
    câblée d'un seul côté serait verte ici et invisible en production.
    """
    prepared = await agent_qa.prepare(CAS_19.prompt, {"serie": "S2"}, session_eleve)

    flux = "".join([token async for token in agent_qa.stream(prepared)])

    assert flux.startswith(prepared.preambule_soutien)
    assert prepared.generation["llm_provider"] != "securite", (
        "le modèle n'a pas été sollicité : l'ouverture a remplacé le tour"
    )


# --- Cas #21 : le prompt exact du testeur ------------------------------------


async def test_le_prompt_21_compte_ses_deux_signaux(agent_qa, session_eleve):
    """« c'est trop dur » ET « je laisse tomber » : 0,4 → 0,8."""
    resultat = await agent_qa.respond(CAS_21.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["frustration_score"] >= 0.5
    assert resultat.trace["hint_level"] > 1, (
        "l'élève annonce qu'il abandonne et reçoit le même niveau d'indice"
    )


async def test_le_prompt_21_ne_recoit_pas_la_reponse_du_prompt_19(agent_qa, session_eleve):
    """Le reproche exact du #21 : « réponse quasi identique aux deux précédentes ».

    Deux registres, deux ouvertures. C'est vérifiable ici — et seulement ici —
    parce que ces textes sont écrits par le code : la prose du modèle, elle,
    n'est pas jugeable en couche A.
    """
    r19 = await agent_qa.respond(CAS_19.prompt, {"serie": "S2"}, session_eleve)
    r21 = await agent_qa.respond(CAS_21.prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_ouverture_de_soutien(r21, signal="abandon")
    assertions.assert_le_tour_pedagogique_continue(r21)
    assert r21.trace["soutien"]["texte"] != r19.trace["soutien"]["texte"]


async def test_deux_decouragements_de_suite_ne_donnent_pas_le_meme_texte(
    agent_qa, session_eleve
):
    """Même registre, deux tours : l'ouverture change quand même.

    Sans cela, l'élève qui insiste relirait mot pour mot le paragraphe du tour
    précédent — la version « copiée-collée » que le testeur a vue.
    """
    premier = await agent_qa.respond("je suis nul en maths", {"serie": "S2"}, session_eleve)
    second = await agent_qa.respond(
        "je n'y arriverai jamais", {"serie": "S2"}, session_eleve
    )

    assert premier.trace["soutien"]["variante"] != second.trace["soutien"]["variante"]
    assert premier.trace["soutien"]["texte"] != second.trace["soutien"]["texte"]


async def test_un_abandon_annonce_n_est_pas_lu_comme_une_question_vague(
    agent_qa, session_eleve
):
    """« je laisse tomber » : trois tokens, donc niveau 0 — « reformule ».

    C'est le défaut du cas #14 tombant sur le message du cas #21 : la phrase est
    courte parce qu'elle est nette, pas parce qu'elle est floue. Demander à
    l'élève de reformuler son abandon est la pire réponse possible, et elle
    était produite par une règle générique, pas par ce prompt-là.
    """
    resultat = await agent_qa.respond("je laisse tomber", {"serie": "S2"}, session_eleve)

    assert resultat.trace["hint_label"] != "Reformulation"
    assert HINT_INSTRUCTIONS[0] not in resultat.final_prompt


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


@pytest.mark.parametrize(
    "question",
    [
        "C'est trop dur, je laisse tomber",
        "je laisse tomber",
        "j'abandonne",
        "j'abandonne, c'est trop compliqué",
        "je vais arrêter les maths",
        "j'arrête les maths",
        "ça vaut pas la peine",
        "je continue pas",
    ],
)
def test_l_abandon_annonce_est_detecte(question):
    """Généralisation du #21 : ce n'est pas la phrase de Tony qui est corrigée."""
    assert detecte_un_abandon(question) is True
    assert detecter_signal_soutien(question) is SignalSoutien.ABANDON


@pytest.mark.parametrize(
    "question",
    [
        # Difficulté déclarée : l'élève demande de l'aide, il ne s'arrête pas.
        "c'est trop dur",
        "je bloque sur cette question",
        "je ne comprends pas",
        "j'ai du mal en maths",
        # « tomber » et « arrêter » au sens mathématique ou ordinaire.
        "pourquoi la courbe tombe à zéro ?",
        "je dois arrêter le calcul à quelle étape ?",
        "on laisse tomber le terme en x² ou pas ?",
    ],
)
def test_une_difficulte_ordinaire_n_est_pas_un_abandon(question):
    """Même borne que pour le découragement : ne pas capter l'élève au travail."""
    assert detecte_un_abandon(question) is False


def test_le_decouragement_prime_sur_l_abandon():
    """« je suis nul, je laisse tomber » demande d'abord qu'on démente.

    Proposer un pas plus petit ne répond pas à une phrase où l'élève met en
    cause sa valeur : les deux signaux sont ordonnés, pas concurrents.
    """
    assert detecter_signal_soutien("je suis nul, je laisse tomber") is (
        SignalSoutien.DECOURAGEMENT
    )


def test_la_rotation_ne_s_arrete_pas_quand_les_variantes_sont_epuisees():
    """Un élève peut se décourager plus de trois fois : le produit ne cale pas.

    On repart alors sur la première ouverture — revoir un texte lu trois tours
    plus tôt vaut mieux que répéter celui du tour précédent, qui est le défaut
    rapporté.
    """
    servies: list[str] = []
    for _ in range(7):
        ouverture = choisir_ouverture(SignalSoutien.DECOURAGEMENT, servies)
        assert servies[-1:] != [ouverture.variante], "même ouverture deux tours de suite"
        servies.append(ouverture.variante)


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
def test_aucune_fixture_positive_ne_declenche_une_ouverture_de_soutien(cas):
    """Contrepartie du nouveau registre : #53 « j'ai pas le temps » n'est pas un
    abandon, et les refus (#57 à #61) ne doivent pas s'ouvrir sur du soutien —
    c'est leur fermeté qui a été validée."""
    assert detecter_signal_soutien(cas.prompt) is None


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
