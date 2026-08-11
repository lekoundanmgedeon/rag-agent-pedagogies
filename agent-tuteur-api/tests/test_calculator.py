import pytest

from agent_tuteur.tools.calculator import (
    CalculationError,
    compute,
    demande_un_calcul_concret,
    differentiate,
    evaluate,
    looks_like_calculation,
    normaliser_expression,
    solve_equation,
)


def test_composite_arithmetic():
    assert evaluate("2*(3+4)^2").result.startswith("98")


def test_derivative():
    assert differentiate("x^3 - 3*x").result == "3*x**2 - 3"


def test_solve_quadratic():
    assert solve_equation("x^2 - 4 = 0").result == "[-2, 2]"


def test_compute_routes_by_keyword():
    assert compute("dérivée de x^2").result == "2*x"
    assert compute("calcule 12*8").result.startswith("96")


def test_detection_positive_and_negative():
    assert looks_like_calculation("quelle est la dérivée de x^2 ?")
    assert looks_like_calculation("résous 2x + 1 = 5")
    assert not looks_like_calculation("raconte-moi l'histoire de Senghor")


@pytest.mark.parametrize("payload", ["__import__('os')", "os.system('ls')", "lambda: 1"])
def test_sandbox_blocks_dangerous_input(payload):
    with pytest.raises(CalculationError):
        evaluate(payload)


def test_invalid_expression_raises():
    with pytest.raises(CalculationError):
        evaluate("2 +* 3")


# --- Notations Unicode réellement saisies par les élèves (cas QA #1) ---------


@pytest.mark.parametrize(
    ("brut", "normalise"),
    [
        ("x³ − 3x", "x**3 - 3x"),
        ("x² + 2x", "x**2 + 2x"),
        ("2x⁴", "2x**4"),
        ("x¹²", "x**12"),          # exposant à plusieurs chiffres
        ("3 × 4 ÷ 2", "3 * 4 / 2"),
        ("x²·ln(x)", "x**2*ln(x)"),
        ("√2", "sqrt2"),
    ],
)
def test_normalisation_des_notations_unicode(brut, normalise):
    assert normaliser_expression(brut) == normalise


def test_le_deux_points_reste_une_ponctuation():
    """« le nombre complexe : z = 3 + 4i » ne contient pas une division."""
    assert ":" in normaliser_expression("le nombre complexe : z = 3 + 4i")


@pytest.mark.parametrize(
    ("question", "attendu"),
    [
        ("Calcule la dérivée de x³ − 3x", "3*x**2 - 3"),
        ("calcule la dérivée de x² + 2x", "2*x + 2"),
        ("calcule 3 × 4 ÷ 2", "6"),
    ],
)
def test_le_calcul_est_juste_malgre_les_notations_unicode(question, attendu):
    assert compute(question).result.split("=")[0].strip() == attendu


# --- Refus plutôt que calcul sur un fragment (règle non-négociable n°2) ------


def test_une_extraction_tronquee_leve_au_lieu_de_calculer():
    """Le défaut du cas QA #1 : « x³ − 3x » réduit à « x », dérivé en « 1 ».

    On simule ici une troncature en glissant un caractère signifiant hors de la
    fenêtre extraite ; l'outil doit refuser plutôt que rendre un résultat partiel.
    """
    with pytest.raises(CalculationError):
        compute("calcule 2 + 3 puis ajoute 7 au résultat et divise par 4 le tout ≠ 9")


def test_un_mot_francais_n_est_jamais_pris_pour_une_expression():
    """« exercice » devenait le produit c*e*i*r*x, annoncé comme vérifié."""
    with pytest.raises(CalculationError):
        compute("Aide moi avec cet exercice sur les nombres complexes")


# --- Calcul concret vs question de méthode -----------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Calcule la dérivée de x³ − 3x",
        "résous 2x + 1 = 5",
        "calcule la dérivée de ∫∫ x dx dy",   # impératif, sans expression analysable
    ],
)
def test_demande_de_calcul_concret(question):
    assert demande_un_calcul_concret(question)


@pytest.mark.parametrize(
    "question",
    [
        "Comment dériver un quotient de fonctions ?",   # fixture positive #54
        "à quoi sert une intégrale ?",
        "quelle est la formule de la dérivée d'un produit ?",
        "pourquoi dérive-t-on une fonction ?",
    ],
)
def test_question_de_methode_n_est_pas_un_calcul_concret(question):
    assert not demande_un_calcul_concret(question)
