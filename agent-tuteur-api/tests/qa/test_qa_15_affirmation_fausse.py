"""Cas QA #15 — « La dérivée de ln(x) c'est bien 1/x² non ? » (testeur : Tony SARRE).

Observé : l'élève affirme à tort que la dérivée de ln(x) est 1/x² ; l'agent ne
corrige pas et renvoie une question vague.

C'est la règle non-négociable n°2 lue dans l'autre sens. Elle interdit
d'annoncer un résultat non vérifié ; elle n'autorise pas pour autant à laisser
passer un faux quand l'outil peut trancher. Le correctif fait donc le trajet
inverse de la calculatrice : au lieu de vérifier ce que l'agent s'apprête à
dire, il vérifie ce que l'élève vient d'affirmer.

Mesure d'origine : ``compute()`` refusait la question (« Texte non mathématique
dans l'expression (est, bien) »), donc l'affirmation n'était même pas extraite.

Assertions sur le verdict symbolique et sur le prompt assemblé — deux artefacts
produits par le code. Que le modèle formule effectivement la correction relève
de la couche B (décision D2).
"""

from __future__ import annotations

import pytest

from agent_tuteur.tools.affirmation import verifier_affirmation

from . import assertions
from .cas import par_id, tous_les_cas

CAS_15 = par_id(tous_les_cas())[15]


# --- Le prompt exact du testeur ----------------------------------------------


def test_le_prompt_exact_est_desormais_analysable():
    """Point de départ du bug : l'affirmation n'était pas extraite du tout."""
    verdict = verifier_affirmation(CAS_15.prompt)

    assert verdict is not None, "l'affirmation de l'élève n'a pas été détectée"
    assert verdict.correcte is False
    assert verdict.attendu == "1/x"


async def test_le_prompt_exact_produit_un_verdict_dans_la_trace(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_15.prompt, {"serie": "S2"}, session_eleve)

    affirmation = resultat.trace["affirmation_eleve"]
    assert affirmation is not None, "aucun verdict sur l'affirmation de l'élève"
    assert affirmation["correcte"] is False
    assert affirmation["attendu"] == "1/x"


async def test_le_prompt_exact_impose_une_correction_explicite(agent_qa, session_eleve):
    """La correction doit être une consigne, pas une chance laissée au modèle."""
    prepared = await agent_qa.prepare(CAS_15.prompt, {"serie": "S2"}, session_eleve)

    assert "C'est FAUX" in prepared.final_prompt
    assert "1/x" in prepared.final_prompt
    assert "corriger cette erreur explicitement" in prepared.final_prompt
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


async def test_aucune_consigne_contradictoire_dans_le_prompt(agent_qa, session_eleve):
    """Régression traitée pendant le correctif, et facile à réintroduire.

    ``compute`` échoue sur cette phrase (ce n'est pas une demande de calcul),
    ce qui armait ``calcul_non_verifie`` et injectait « tu ne dois annoncer
    AUCUN résultat » — l'exact contraire de la correction demandée. Le contenu
    mathématique du tour ayant bien été vérifié, l'avertissement n'a pas lieu
    d'être.
    """
    prepared = await agent_qa.prepare(CAS_15.prompt, {"serie": "S2"}, session_eleve)

    assert prepared.trace["calcul_non_verifie"] is False
    assert "n'annonce" not in prepared.final_prompt.lower()
    assert "AUCUN résultat chiffré" not in prepared.final_prompt


# --- Au-delà du prompt exact -------------------------------------------------


@pytest.mark.parametrize(
    ("question", "attendu"),
    [
        ("La dérivée de ln(x) c'est bien 1/x² non ?", "1/x"),
        ("la dérivée de x^2 est 2x²", "2*x"),
        ("la dérivée de x³ c'est 3x", "3*x**2"),
        ("la primitive de x c'est x²", "x**2/2"),
    ],
)
def test_les_affirmations_fausses_sont_detectees(question, attendu):
    verdict = verifier_affirmation(question)
    assert verdict is not None and verdict.correcte is False
    assert verdict.attendu == attendu


@pytest.mark.parametrize(
    "question",
    [
        "La dérivée de ln(x) c'est bien 1/x non ?",
        "la dérivée de x^2 est 2x",
        "la primitive de x c'est x²/2",
        "la primitive de x c'est x²/2 + 3",   # constante d'intégration
    ],
)
def test_les_affirmations_justes_sont_confirmees(question):
    """Un faux positif serait pire que le bug : il contredirait un élève qui a raison."""
    verdict = verifier_affirmation(question)
    assert verdict is not None and verdict.correcte is True


@pytest.mark.parametrize(
    "question",
    [
        "Quelle est la dérivée de ln(x) ?",          # question, pas affirmation
        "Comment dériver un quotient de fonctions ?",  # fixture positive #54
        "Calcule la dérivée de x³ − 3x",             # cas #1 — demande de calcul
        "1-1=?",                                      # cas #10
        "je suis en S2",                              # cas #8
        "Je me fais harceler au lycée",               # cas #7
        "fais-moi un cours sur les nombres complexes",
    ],
)
def test_rien_n_est_juge_hors_affirmation(question):
    """Le silence est le comportement par défaut : pas de verdict fabriqué."""
    assert verifier_affirmation(question) is None


async def test_une_affirmation_juste_n_injecte_aucune_correction(agent_qa, session_eleve):
    prepared = await agent_qa.prepare(
        "La dérivée de ln(x) c'est bien 1/x non ?", {"serie": "S2"}, session_eleve
    )

    assert prepared.trace["affirmation_eleve"]["correcte"] is True
    assert "C'est FAUX" not in prepared.final_prompt


async def test_les_cas_deja_clos_ne_sont_pas_perturbes(agent_qa, session_eleve):
    """Le cas #1 doit garder son résultat vérifié et aucun verdict d'affirmation."""
    resultat = await agent_qa.respond(
        "Calcule la dérivée de x³ − 3x", {"serie": "S2"}, session_eleve
    )

    assert resultat.trace["tool_used"] == "sympy_calculator"
    assert resultat.trace["affirmation_eleve"] is None
