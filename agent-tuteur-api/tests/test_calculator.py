import pytest

from agent_tuteur.tools.calculator import (
    CalculationError,
    compute,
    differentiate,
    evaluate,
    looks_like_calculation,
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
