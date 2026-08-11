"""Cas QA #1 — « Calcule la dérivée de x³ − 3x » (testeur : Tony SARRE).

Observé : l'agent annonce −9x²−3x au lieu de 3x²−3.

Cause racine mesurée : le prompt contient ``³`` (U+00B3) et ``−`` (U+2212).
``_extract_expression`` s'arrêtait au premier caractère hors de sa classe et
renvoyait ``'x'`` — sur quoi SymPy calculait consciencieusement la dérivée de
*x*, soit ``1``. Le résultat faux était ensuite injecté dans le prompt sous le
libellé « Résultat vérifié par l'outil de calcul », donc avec l'autorité d'une
vérification symbolique.

Règle non-négociable n°2 : jamais de calcul faux annoncé avec assurance. Le
correctif tient en deux propriétés, toutes deux testées ici :

1. l'expression est **normalisée** avant analyse (Unicode mathématique) ;
2. si l'extraction ne couvre pas tout ce que l'élève a écrit, l'outil
   **refuse** au lieu de calculer sur un fragment.
"""

from __future__ import annotations

import pytest
import sympy

from agent_tuteur.agent.frustration import SessionState

from .cas import cas_critiques, par_id

CAS_01 = par_id(cas_critiques())[1]


def _equivalent(resultat: str, attendu: str) -> bool:
    """Égalité symbolique, pas textuelle : ``3*x**2 - 3`` ≡ ``-3 + 3*x^2``."""
    return sympy.simplify(sympy.sympify(resultat) - sympy.sympify(attendu)) == 0


async def test_prompt_exact_du_testeur_donne_la_bonne_derivee(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_01.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["tool_used"] == "sympy_calculator"
    calcule = resultat.trace["tool_result"].split("→")[-1].strip()
    assert _equivalent(calcule, "3*x**2 - 3"), f"dérivée fausse : {calcule}"


@pytest.mark.parametrize(
    ("question", "attendu"),
    [
        # Le prompt du testeur et ses variantes de saisie : le résultat ne doit
        # pas dépendre de la façon dont l'élève tape les puissances et le moins.
        ("Calcule la dérivée de x³ − 3x", "3*x**2 - 3"),
        ("calcule la dérivée de x^3 - 3x", "3*x**2 - 3"),
        ("calcule la dérivée de x**3 - 3*x", "3*x**2 - 3"),
        ("calcule la dérivée de x^3 − 3x", "3*x**2 - 3"),
        ("calcule la dérivée de x² + 2x", "2*x + 2"),
        ("calcule la dérivée de 2x⁴ − x²", "8*x**3 - 2*x"),
    ],
)
async def test_les_notations_unicode_donnent_le_meme_resultat(question, attendu, agent_qa):
    resultat = await agent_qa.respond(question, {"serie": "S2"}, SessionState())
    assert resultat.trace["tool_used"] == "sympy_calculator", f"outil non sollicité : {question}"
    calcule = resultat.trace["tool_result"].split("→")[-1].strip()
    assert _equivalent(calcule, attendu), f"{question} -> {calcule}, attendu {attendu}"


@pytest.mark.parametrize(
    ("question", "attendu"),
    [
        ("calcule 3 × 4 ÷ 2", "6"),
        ("calcule 10 − 4", "6"),
    ],
)
async def test_les_operateurs_unicode_sont_normalises(question, attendu, agent_qa):
    resultat = await agent_qa.respond(question, {"serie": "S2"}, SessionState())
    calcule = resultat.trace["tool_result"].split("→")[-1].strip().split("=")[0].strip()
    assert _equivalent(calcule, attendu)


# --- Le cœur de la règle n°2 : refuser plutôt que calculer sur un fragment ----


@pytest.mark.parametrize(
    "question",
    [
        # Fragment de mot pris pour une expression : c'est ce qui produisait
        # « c**2*e**2*i*r*x » à partir du mot « exercice » (cas QA #6).
        "Aide moi avec cet exercice sur les nombres complexes",
        # Expression réellement inanalysable : refus attendu, pas d'à-peu-près.
        "calcule la dérivée de ∫∫ x dx dy",
    ],
)
async def test_aucun_resultat_annonce_quand_l_expression_n_est_pas_sure(question, agent_qa):
    resultat = await agent_qa.respond(question, {"serie": "S2"}, SessionState())
    assert resultat.trace["tool_used"] is None, (
        f"un résultat a été présenté comme vérifié : {resultat.trace['tool_result']}"
    )


async def test_un_calcul_invérifiable_est_signalé_au_modèle(agent_qa):
    """Le prompt doit interdire d'annoncer un résultat que rien n'a vérifié.

    Sans ce signal, l'échec de l'outil est silencieux (``tool_used=None``) et le
    modèle reprend la main comme si de rien n'était — c'est très exactement le
    scénario que la règle n°2 interdit.
    """
    prepared = await agent_qa.prepare(
        "calcule la dérivée de ∫∫ x dx dy", {"serie": "S2"}, SessionState()
    )
    assert prepared.trace["calcul_non_verifie"] is True
    assert "n'a PAS pu être vérifié" in prepared.final_prompt


# --- Non-régression : les questions conceptuelles gardent leur comportement ---


@pytest.mark.parametrize(
    "question",
    [
        # Positif #54 : question de méthode, sans expression concrète. L'outil
        # n'a rien à vérifier — ce n'est pas un calcul invérifiable.
        "Comment dériver un quotient de fonctions ?",
        "à quoi sert une intégrale ?",
    ],
)
async def test_une_question_conceptuelle_n_est_pas_un_calcul_a_verifier(question, agent_qa):
    prepared = await agent_qa.prepare(question, {"serie": "S2"}, SessionState())
    assert prepared.trace["calcul_non_verifie"] is False
    assert "n'a PAS pu être vérifié" not in prepared.final_prompt


async def test_positif_55_la_derivee_de_x2_lnx_est_bien_calculee(agent_qa):
    """Fixture positive #55 : elle ne doit surtout pas devenir un refus.

    Elle passait auparavant par un échec silencieux de l'outil, la bonne réponse
    venant du modèle seul. Elle doit maintenant être réellement vérifiée.
    """
    prepared = await agent_qa.prepare(
        "Calcule la dérivée de la fonction f(x) = x²·ln(x) et détaille chaque étape.",
        {"serie": "S2"},
        SessionState(),
    )
    assert prepared.trace["calcul_non_verifie"] is False
    assert prepared.trace["tool_used"] == "sympy_calculator"


async def test_le_controle_de_fidelite_ne_crie_plus_au_loup(agent_qa):
    """Le contrôle de verify.py compare au résultat seul, pas à « expr → résultat ».

    Il comparait la réponse rédigée à la chaîne complète, que le modèle n'écrit
    jamais telle quelle : chaque calcul juste était donc signalé comme suspect.
    Une vérification qui alerte toujours n'alerte plus.
    """
    resultat = await agent_qa.respond(CAS_01.prompt, {"serie": "S2"}, SessionState())
    faux_positifs = [p for p in resultat.verification["problemes"] if "n'apparaît pas" in p]
    attendu = resultat.trace["tool_result"].split("→")[-1].strip()
    assert attendu in resultat.answer or faux_positifs, "cas de figure inattendu"
    # Le message doit citer le résultat seul, jamais la chaîne « expression → ».
    assert all("→" not in p for p in faux_positifs), faux_positifs
