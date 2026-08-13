"""Cas QA #38 et #41 — une salutation reçue comme un exercice.

* #38 « Bonsoir » (OKERE Rafiatou) — l'agent ne salue pas en retour et enchaîne
  sur une question de vérification de compréhension.
* #41 « Salut » (Pontiane) — l'agent lance une reformulation générique au lieu
  d'un accueil naturel.

Cause racine unique et mesurée : faute d'intention dédiée, une salutation
tombait en ``EXERCICE``. Faisant moins de quatre tokens, elle était ensuite
classée « question courte/vague » par ``diagnose_hint_level``, donc au niveau 0,
dont la consigne dit « Reformule la question de l'élève avec tes mots pour
vérifier sa compréhension. N'apporte AUCUNE information nouvelle ». Les deux
comportements rapportés sont les deux moitiés de cette consigne : la
reformulation pour l'un, la vérification de compréhension pour l'autre. Ni l'un
ni l'autre n'était une dérive du modèle.

Second effet mesuré : la recherche partait quand même sur « Bonsoir » et
remontait cinq extraits à des scores indiscernables (~0,03), qui servaient
ensuite de matière à la question posée à l'élève.

Le tour est donc dérouté avant la recherche, comme les tours méta des cas
#2/#3/#4, et ancré sur le catalogue réel du store — accueillir en proposant un
chapitre absent serait le défaut du cas #28 déplacé d'un écran.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.intent import Intent, classify_intent, est_une_salutation
from agent_tuteur.agent.prompt import CONSIGNE_ACCUEIL

from . import assertions
from .cas import cas_positifs, par_id, tous_les_cas

CAS = par_id(tous_les_cas())
CAS_38, CAS_41 = CAS[38], CAS[41]


# --- Les prompts exacts des testeurs -----------------------------------------


@pytest.mark.parametrize("cas", [CAS_38, CAS_41], ids=["qa-38", "qa-41"])
async def test_le_prompt_exact_est_route_en_accueil(cas, agent_qa, session_eleve):
    resultat = await agent_qa.respond(cas.prompt, {"serie": "S2"}, session_eleve)

    noeuds = [e["node"] for e in resultat.node_trace]
    assertions.assert_intention(resultat, "salutation")
    assert "guardrail_accueil" in noeuds, noeuds
    assert "guardrail" not in noeuds, "le tour est passé par l'assemblage socratique"


@pytest.mark.parametrize("cas", [CAS_38, CAS_41], ids=["qa-38", "qa-41"])
async def test_le_prompt_exact_ne_lance_aucune_recherche(cas, agent_qa, session_eleve):
    """« Bonsoir » n'a rien à retrouver : cinq extraits de bruit en moins."""
    resultat = await agent_qa.respond(cas.prompt, {"serie": "S2"}, session_eleve)

    assertions.assert_pas_de_retrieval(resultat)


@pytest.mark.parametrize("cas", [CAS_38, CAS_41], ids=["qa-38", "qa-41"])
async def test_le_prompt_exact_demande_un_accueil_avant_toute_pedagogie(
    cas, agent_qa, session_eleve
):
    prepared = await agent_qa.prepare(cas.prompt, {"serie": "S2"}, session_eleve)

    assert CONSIGNE_ACCUEIL in prepared.final_prompt
    assert prepared.trace["hint_level"] is None, "la graduation socratique s'applique encore"
    assert prepared.trace["hint_label"] == "Accueil"
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


@pytest.mark.parametrize("cas", [CAS_38, CAS_41], ids=["qa-38", "qa-41"])
async def test_le_prompt_exact_propose_les_chapitres_reels(cas, agent_qa, session_eleve):
    """Accueillir en proposant un chapitre absent serait le cas #28 déplacé."""
    prepared = await agent_qa.prepare(cas.prompt, {"serie": "S2"}, session_eleve)

    assert "Les Nombres Complexes" in prepared.final_prompt
    assert "Le Calcul Intégral" in prepared.final_prompt
    for invente in ("Suites Numériques", "Probabilités", "Arithmétique"):
        assert invente not in prepared.final_prompt


# --- Au-delà des prompts exacts ----------------------------------------------


@pytest.mark.parametrize(
    "message",
    ["Bonsoir", "Salut", "bonjour", "Coucou", "slt", "Hello", "Bonjour !",
     "Bonsoir, ça va ?", "salut, comment vas-tu ?", "Bonjour Monsieur",
     "bonjour, merci", "Salut, moi c'est Awa"],
)
def test_les_salutations_seules_sont_reconnues(message):
    assert est_une_salutation(message) is True
    assert classify_intent(message).intent is Intent.SALUTATION


# --- La borne : « rien d'autre » est le cœur du prédicat ---------------------
# Accueillir une vraie question sans y répondre reproduirait le défaut corrigé,
# à l'envers. C'est le risque principal de ce correctif.


@pytest.mark.parametrize(
    "message",
    [
        "Salut, comment on calcule le module d'un nombre complexe ?",
        "Bonjour, fais-moi un cours sur les nombres complexes",
        "Bonsoir, calcule la dérivée de x³ − 3x",
        "salut je bloque sur l'exercice 3",
        "Bonjour, je suis en S2",
        "Coucou, 1-1=?",
    ],
)
def test_une_salutation_suivie_d_une_demande_n_est_pas_un_accueil(message):
    assert est_une_salutation(message) is False
    assert classify_intent(message).intent is not Intent.SALUTATION


@pytest.mark.parametrize(
    "message",
    ["Je me fais harceler au lycée", "Je ne comprends pas les dérivées",
     "Ça fait 3 fois que tu m'expliques, je comprends pas", "quels chapitres as-tu ?"],
)
def test_un_message_sans_salutation_n_est_jamais_un_accueil(message):
    assert est_une_salutation(message) is False


async def test_une_salutation_ne_court_circuite_pas_la_securite(agent_qa, session_eleve):
    """Le triage de détresse passe avant tout, y compris avant l'accueil.

    L'ordre des nœuds le garantit déjà ; ce test fige la propriété, parce
    qu'une intention ajoutée en tête de ``classify_intent`` est exactement le
    genre de changement qui pourrait la déplacer un jour.
    """
    resultat = await agent_qa.respond(
        "Bonsoir, je me fais harceler au lycée", {"serie": "S2"}, session_eleve
    )

    assertions.assert_court_circuit_securite(resultat, motif="detresse")


@pytest.mark.parametrize("cas", cas_positifs(), ids=[c.identifiant_test for c in cas_positifs()])
async def test_aucune_fixture_positive_n_est_absorbee_par_l_accueil(
    cas, agent_qa, session_eleve
):
    resultat = await agent_qa.respond(cas.prompt, {"serie": "S2"}, session_eleve)

    entree = next(e for e in resultat.node_trace if e["node"] == "detect_intent")
    assert entree["intent"] != "salutation", f"comportement validé absorbé : {cas.prompt!r}"
