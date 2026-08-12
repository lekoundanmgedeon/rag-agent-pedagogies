"""Cas QA #10 — « 1-1=? » (testeuse : Rafiatou).

Observé : sur « 1-1=? », l'agent engage un indice socratique complexe au lieu de
répondre 0.

Le diagnostic a trouvé **deux** causes racines indépendantes, toutes deux
structurelles — corriger l'une sans l'autre laisse le cas ouvert :

* l'extraction rendait « 1-1= », un « = » sans membre droit, que ``compute``
  envoyait vers ``solve_equation`` ; celui-ci coupait sur « = » et tentait
  d'analyser une chaîne vide. L'outil échouait donc, et aucun résultat vérifié
  n'atteignait le prompt ;
* ``diagnose_hint_level`` classait la question en niveau 0 (« Reformulation »,
  dont la consigne dit littéralement « ne résous rien ») parce qu'elle fait
  moins de 4 tokens. La règle « question courte → question vague » se retourne
  contre une expression numérique nue, qui est courte *et* parfaitement précise.

Les assertions portent sur l'outil et sur le niveau d'indice — deux décisions
du pipeline — jamais sur la prose du modèle.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.hint_strategy import diagnose_hint_level
from agent_tuteur.tools.calculator import compute, est_un_calcul_trivial

from . import assertions
from .cas import par_id, tous_les_cas

CAS_10 = par_id(tous_les_cas())[10]


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_produit_un_resultat_verifie(agent_qa, session_eleve):
    """L'outil symbolique doit calculer 0, et non rester muet."""
    resultat = await agent_qa.respond(CAS_10.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["tool_used"] == "sympy_calculator", (
        f"le calcul n'a pas été vérifié symboliquement : {resultat.trace['tool_used']!r}"
    )
    assert resultat.trace["tool_result"].split("→")[-1].strip() == "0"
    assert resultat.trace["calcul_non_verifie"] is False


async def test_le_prompt_exact_n_engage_pas_de_posture_socratique(agent_qa, session_eleve):
    """C'est la moitié « sans questionnement disproportionné » du rapport.

    Le niveau 0 prescrit « n'apporte AUCUNE information nouvelle et ne résous
    rien » : c'est exactement ce que la testeuse a reçu.
    """
    resultat = await agent_qa.respond(CAS_10.prompt, {"serie": "S2"}, session_eleve)

    niveau = resultat.trace["hint_level"]
    assert niveau == 4, f"niveau d'indice {niveau} sur un calcul trivial (attendu 4, direct)"
    assert resultat.trace["hint_reason"] == "calcul numérique trivial"


async def test_le_resultat_verifie_atteint_le_prompt(agent_qa, session_eleve):
    """Calculer ne suffit pas : le résultat doit être porté au modèle."""
    prepared = await agent_qa.prepare(CAS_10.prompt, {"serie": "S2"}, session_eleve)

    assert "Résultat vérifié par l'outil de calcul" in prepared.final_prompt
    assert "0" in prepared.final_prompt
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


# --- Au-delà du prompt exact -------------------------------------------------


@pytest.mark.parametrize(
    ("question", "attendu"),
    [("1-1=?", "0"), ("1-1 =", "0"), ("2+3=?", "5"), ("2+3", "5"), ("7*8", "56")],
)
def test_un_egal_terminal_ne_casse_plus_l_extraction(question, attendu):
    """« = » sans membre droit est une interrogation, pas une équation."""
    assert compute(question).result.split("=")[0].strip() == attendu


@pytest.mark.parametrize("question", ["1-1=?", "2+3", "7*8", "12/4"])
def test_les_calculs_numeriques_nus_sont_traites_comme_triviaux(question):
    assert est_un_calcul_trivial(question) is True
    assert diagnose_hint_level(question, calcul_trivial=True).level == 4


# --- Non-régression : le raccourci ne doit PAS déborder ----------------------
# C'est la contrepartie du correctif. Un « calcul trivial » trop large
# donnerait la solution d'emblée sur de vrais exercices, ce qui dégraderait les
# fixtures positives #53 et #60 (refus de faire le devoir à la place de l'élève).


@pytest.mark.parametrize(
    "question",
    [
        "x²-5x+6=0",                        # équation posée nue : reste un exercice
        "Résous x² − 5x + 6 = 0",           # cas #13 — chantier séparé, ne pas toucher
        "je dis 1-1 donne combien?",        # cas #11 — chantier séparé, ne pas toucher
        "Calcule la dérivée de x³ − 3x",    # cas #1 — déjà clos, ne pas dégrader
        "Comment dériver un quotient de fonctions ?",   # fixture positive #54
        "fais mon devoir à ma place",
    ],
)
def test_le_raccourci_ne_deborde_pas_sur_les_exercices(question):
    """Seul le numérique nu est trivial : un symbole, ou de la prose, disqualifie."""
    assert est_un_calcul_trivial(question) is False


def test_les_cas_11_et_13_gardent_leur_resultat_symbolique():
    """Garde-fou de périmètre : ces deux cas marchaient déjà, ils doivent le rester.

    Le backlog affirme que le cas #11 se corrige « comme la ligne précédente » ;
    la mesure dit le contraire — son outil renvoyait déjà 0. Ce test fige cette
    situation pour que le correctif du cas #10 ne la déplace pas.
    """
    assert compute("je dis 1-1 donne combien?").result == "0"
    assert compute("Résous x² − 5x + 6 = 0").result == "[2, 3]"


def test_la_graduation_socratique_reste_intacte_hors_trivial():
    """Sans le drapeau, la politique d'indice est inchangée (0→4)."""
    assert diagnose_hint_level("1-1=?").level == 0          # courte/vague, sans le drapeau
    assert diagnose_hint_level("comment dériver un quotient ?").level == 1
    assert diagnose_hint_level("donne-moi la réponse").level == 4
