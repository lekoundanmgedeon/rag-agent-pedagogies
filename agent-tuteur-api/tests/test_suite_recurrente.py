"""Vérification symbolique d'une suite récurrente — cas QA #33.

Le testeur validait la réponse et demandait un garde-fou : « un outil de
vérification pour garantir que le raisonnement détaillé ne contient pas d'erreur
cachée ». On ne vérifie pas le raisonnement du modèle — aucun outil ne le fait
ici — mais on établit les **faits** sur lesquels il doit tomber, et on lui
interdit de les recalculer.

Ce que ces tests protègent avant tout, c'est le **silence** de l'outil : hors du
cas affine, la monotonie et la limite ne sont pas démontrées, et rien ne doit
alors être annoncé (règle non-négociable n°2).
"""

from __future__ import annotations

import pytest

from agent_tuteur.tools.suite import analyser_la_demande, demande_une_suite_recurrente

PROMPT_33 = (
    "Démontre que la suite définie par u₀ = 2 et uₙ₊₁ = (uₙ + 3)/2 est monotone, "
    "majorée, et calcule sa limite."
)


def test_le_prompt_du_cas_33_est_entierement_etabli():
    suite = analyser_la_demande(PROMPT_33)
    assert suite is not None
    # Les cinq premiers termes, exacts (pas de flottants : 5/2, pas 2.5).
    assert suite.premiers_termes == ["2", "5/2", "11/4", "23/8", "47/16"]
    assert suite.monotonie == "croissante"
    assert suite.borne == "majorée par 3"
    assert suite.limite == "3"
    assert suite.forme_close == "3 - 1/2**n"


def test_les_indices_unicode_sont_lus():
    """« u₀ » et « uₙ₊₁ » sont ce que l'élève tape réellement.

    C'est le défaut du cas #1 transposé : là-bas, « x³ − 3x » était tronqué au
    premier caractère non ASCII et produisait un résultat faux.
    """
    assert demande_une_suite_recurrente("u₀ = 2 et uₙ₊₁ = (uₙ + 3)/2")
    assert analyser_la_demande("u₀ = 2 et uₙ₊₁ = (uₙ + 3)/2") is not None


@pytest.mark.parametrize(
    ("enonce", "attendu"),
    [
        # a > 1 : la suite croît et diverge. Ne regarder que l'écart à la limite
        # donnait « décroissante » — un contresens que ce test verrouille.
        ("u_0 = 5 et u_{n+1} = 3*u_n - 4", "croissante"),
        ("u0 = 10 et u_{n+1} = 0.5*u_n + 1", "décroissante"),
        ("u0 = 1 et u(n+1) = u(n) + 7", "croissante"),
    ],
)
def test_le_sens_de_variation_suit_les_deux_facteurs(enonce, attendu):
    assert analyser_la_demande(enonce).monotonie == attendu


def test_une_suite_divergente_ne_recoit_aucune_limite():
    """Ce que l'outil ne démontre pas, il ne le dit pas."""
    suite = analyser_la_demande("u_0 = 5 et u_{n+1} = 3*u_n - 4")
    assert suite.limite is None


def test_une_recurrence_non_affine_reste_muette():
    """Hors du cadre démontré, seuls les termes calculés sont rendus."""
    suite = analyser_la_demande("u0 = 2 et u_{n+1} = u_n**2 + 1")
    assert suite.premiers_termes == ["2", "5", "26", "677", "458330"]
    assert suite.monotonie is None
    assert suite.limite is None
    assert suite.forme_close is None


def test_une_suite_alternee_n_est_pas_declaree_monotone():
    """a < 0 : les termes oscillent autour de la limite."""
    suite = analyser_la_demande("u0 = 3 et u_{n+1} = -0.5*u_n + 1")
    assert suite.monotonie is None
    assert suite.limite == "2/3"


@pytest.mark.parametrize(
    "enonce",
    [
        "calcule la dérivée de x^2",
        "explique-moi les suites numériques",
        "u_0 = 2 mais je ne connais pas la relation",
        "u0 = 2 et u_{n+1} = a*u_n + b",  # une lettre inconnue : on ne devine pas
    ],
)
def test_rien_n_est_invente_faute_d_enonce_lisible(enonce):
    assert analyser_la_demande(enonce) is None
