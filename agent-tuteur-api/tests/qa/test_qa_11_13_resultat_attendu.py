"""Cas QA #11 et #13 — un résultat vérifié que la consigne interdisait de donner.

* #11 « je dis 1-1 donne combien? » (Rafiatou) — reformulation du #10 ; l'agent
  reste évasif et ne donne pas 0.
* #13 « Résous x² − 5x + 6 = 0 » (Tony SARRE) — l'agent donne la formule mais
  ne calcule pas les racines 2 et 3.

Traités ensemble parce qu'ils partagent une **cause racine unique**, mesurée et
non déduite des libellés : dans les deux cas l'outil symbolique avait déjà le
bon résultat (``compute`` rendait ``0`` et ``[2, 3]``), et ce résultat atteignait
même le prompt. Ce qui manquait, c'est la cohérence de ce prompt ::

    Résultat vérifié par l'outil de calcul : x**2 - 5x + 6 = 0 → [2, 3]
    Niveau d'indice : 1 (Rappel de notion).
    Consigne : Rappelle la règle […] SANS l'appliquer au cas de l'élève.

``diagnose_hint_level`` tranche avant ``route_tool`` : il ne pouvait pas savoir
qu'un résultat vérifié suivrait. Le correctif rétablit l'invariant au seul
endroit qui voit les deux — l'assemblage du prompt — et non par un cas
particulier sur ces deux phrases.

Le pendant obligatoire du correctif est la **borne** : escalader dès qu'un
résultat existe reviendrait à faire le devoir à la place de l'élève. C'est la
seconde moitié de ce fichier, adossée aux fixtures positives #53 et #60.
"""

from __future__ import annotations

import pytest

from agent_tuteur.agent.hint_strategy import (
    HINT_INSTRUCTIONS,
    HintDecision,
    diagnose_hint_level,
    escalade_pour_resultat_verifie,
)

from . import assertions
from .cas import par_id, tous_les_cas

CAS = par_id(tous_les_cas())
CAS_11, CAS_13 = CAS[11], CAS[13]

#: Fragment de la consigne de niveau 1. Sa présence à côté d'un résultat
#: vérifié *est* le bug : les deux ne peuvent pas coexister dans un prompt.
CONSIGNE_QUI_INTERDIT = "SANS l'appliquer au cas de l'élève"
RESULTAT_VERIFIE = "Résultat vérifié par l'outil de calcul"


# --- Les prompts exacts des testeurs -----------------------------------------


@pytest.mark.parametrize(
    ("cas", "attendu"), [(CAS_11, "0"), (CAS_13, "[2, 3]")], ids=["qa-11", "qa-13"]
)
async def test_le_prompt_exact_livre_le_resultat_verifie(cas, attendu, agent_qa, session_eleve):
    """Le résultat est calculé, porté au prompt, et la consigne autorise à le dire."""
    prepared = await agent_qa.prepare(cas.prompt, {"serie": "S2"}, session_eleve)

    assert prepared.trace["tool_used"] == "sympy_calculator"
    assert prepared.trace["tool_result"].split("→")[-1].strip() == attendu
    assert f"{RESULTAT_VERIFIE} :" in prepared.final_prompt
    assert attendu in prepared.final_prompt
    assert prepared.trace["hint_level"] == 4
    assert prepared.trace["hint_reason"] == "résultat vérifié et explicitement demandé"
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


@pytest.mark.parametrize("cas", [CAS_11, CAS_13], ids=["qa-11", "qa-13"])
async def test_le_prompt_exact_ne_se_contredit_plus(cas, agent_qa, session_eleve):
    """La formulation directe du bug, indépendante du niveau retenu."""
    prepared = await agent_qa.prepare(cas.prompt, {"serie": "S2"}, session_eleve)

    assert not (
        RESULTAT_VERIFIE in prepared.final_prompt
        and CONSIGNE_QUI_INTERDIT in prepared.final_prompt
    ), "le prompt porte un résultat vérifié ET la consigne de ne pas l'appliquer"


# --- Au-delà des prompts exacts ----------------------------------------------
# L'anti-pattern de CLAUDE.md : un correctif qui ne vaudrait que pour ces deux
# phrases serait considéré comme non résolu. L'invariant est vérifié sur des
# formulations qu'aucun testeur n'a envoyées.


@pytest.mark.parametrize(
    "question",
    [
        "Résous x² − 5x + 6 = 0",
        "résous 2x + 4 = 0",
        "je dis 1-1 donne combien?",
        "calcule 12/4 s'il te plaît",
        "Calcule la dérivée de x³ − 3x",       # cas #1, déjà clos
        "combien fait 7*8 ?",
    ],
)
async def test_aucun_prompt_ne_porte_deux_consignes_contraires(question, agent_qa, session_eleve):
    prepared = await agent_qa.prepare(question, {"serie": "S2"}, session_eleve)

    assert not (
        RESULTAT_VERIFIE in prepared.final_prompt
        and CONSIGNE_QUI_INTERDIT in prepared.final_prompt
    ), f"prompt contradictoire sur {question!r}"


# --- La borne : le correctif ne doit PAS déborder ----------------------------
# Contrepartie exacte du précédent. Les deux conditions de l'escalade sont
# nécessaires ; ces tests protègent celle qui retient le raccourci.


@pytest.mark.parametrize(
    "question",
    [
        "Donne-moi juste la réponse, j'ai pas le temps",   # fixture positive #53
        "Fais mon devoir à ma place, voici l'énoncé",      # fixture positive #60
        "Comment dériver un quotient de fonctions ?",      # fixture positive #54
        "Fais-moi un cours sur les nombres complexes",     # cas #12, chantier séparé
        "fais moi l'etude de fonction de ln(x)",           # cas #9, chantier séparé
    ],
)
async def test_le_raccourci_n_atteint_pas_les_demandes_sans_calcul(
    question, agent_qa, session_eleve
):
    """Sans résultat vérifié, la posture pédagogique reste entière.

    C'est ce qui protège #53 et #60 : aucune expression n'y est soumise, donc
    l'outil ne produit rien, donc l'escalade ne peut structurellement pas se
    déclencher — ce n'est pas une liste de phrases à épargner.

    Les lectures sont tolérantes à la branche : « Fais-moi un cours sur … »
    part en mode cours, dont la trace ne porte ni outil ni niveau d'indice.
    L'absence de ces clés est un *succès* ici — le nœud d'assemblage concerné
    n'est même pas traversé.
    """
    prepared = await agent_qa.prepare(question, {"serie": "S2"}, session_eleve)

    assert prepared.trace.get("tool_result") is None, "un résultat calculé de façon inattendue"
    assert prepared.trace.get("hint_reason") != "résultat vérifié et explicitement demandé"
    niveau = prepared.trace.get("hint_level")
    assert niveau is None or niveau < 4, f"posture directe imposée sur {question!r}"


# --- L'invariant lui-même, hors pipeline -------------------------------------


def test_les_deux_conditions_sont_necessaires():
    base = diagnose_hint_level("Résous x² − 5x + 6 = 0")
    assert base.level == 1

    assert escalade_pour_resultat_verifie(
        base, resultat_verifie=False, demande_concrete=True
    ) is base
    assert escalade_pour_resultat_verifie(
        base, resultat_verifie=True, demande_concrete=False
    ) is base
    escalade = escalade_pour_resultat_verifie(
        base, resultat_verifie=True, demande_concrete=True
    )
    assert escalade.level == 4
    assert escalade.instruction == HINT_INSTRUCTIONS[4]


def test_un_motif_plus_precis_n_est_pas_ecrase():
    """Le cas #10 garde son motif « calcul numérique trivial ».

    Les deux chemins mènent au niveau 4 ; c'est la traçabilité du *pourquoi*
    qu'on protège ici, et le harnais du cas #10 s'appuie dessus.
    """
    trivial = diagnose_hint_level("1-1=?", calcul_trivial=True)
    assert trivial.level == 4

    inchange = escalade_pour_resultat_verifie(
        trivial, resultat_verifie=True, demande_concrete=True
    )
    assert inchange.reason == "calcul numérique trivial"


def test_la_graduation_socratique_reste_intacte_sans_resultat():
    """Aucune escalade ne s'applique quand l'outil n'a rien vérifié."""
    for question in ("Je ne comprends pas les dérivées", "comment dériver un quotient ?"):
        decision = diagnose_hint_level(question)
        assert (
            escalade_pour_resultat_verifie(
                decision, resultat_verifie=False, demande_concrete=False
            )
            is decision
        )


def test_l_escalade_ne_redescend_jamais_un_niveau():
    """Propriété de sûreté : l'escalade est monotone."""
    for niveau in range(5):
        decision = HintDecision(
            level=niveau, label="x", instruction="y", reason="test"
        )
        resultat = escalade_pour_resultat_verifie(
            decision, resultat_verifie=True, demande_concrete=True
        )
        assert resultat.level >= decision.level
