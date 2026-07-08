"""Calculatrice symbolique SymPy, exécutée en **sandbox**.

L'agent délègue ici tout calcul détecté, plutôt que de le confier au LLM (peu
fiable en arithmétique). Sécurité : on n'utilise jamais ``eval`` ; l'expression
passe par ``parse_expr`` avec un dictionnaire de noms restreint, et tout jeton
suspect (dunder, import, appel système) est rejeté en amont.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

# convert_xor : « ^ » signifie puissance (usage scolaire), pas XOR bit-à-bit.
_TRANSFORMS = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
)

# Noms autorisés dans une expression (fonctions/constantes usuelles).
_ALLOWED_NAMES: dict[str, object] = {
    name: getattr(sympy, name)
    for name in (
        "sqrt", "exp", "log", "ln", "sin", "cos", "tan", "asin", "acos", "atan",
        "sinh", "cosh", "tanh", "Abs", "factorial", "binomial", "gcd", "lcm",
        "pi", "E", "oo", "Rational", "Integer", "Float",
    )
    if hasattr(sympy, name)
}
_ALLOWED_NAMES["ln"] = sympy.log

# Jetons interdits : toute tentative d'accès hors périmètre mathématique.
_FORBIDDEN = re.compile(r"(__|\bimport\b|\blambda\b|\bos\b|\bsys\b|\beval\b|\bexec\b)")

# Déclencheurs d'un besoin de calcul (route_tool).
_CALC_KEYWORDS = re.compile(
    r"\b(calcul\w*|d[ée]riv\w*|int[ée]gr\w*|r[ée]sou\w*|simplif\w*|factoris\w*|"
    r"[ée]quation|solve|derivative|integral)\b",
    re.IGNORECASE,
)
_MATH_EXPR = re.compile(r"\d\s*[-+*/^=]\s*\d|[-+*/^]\s*x|\bx\s*[-+*/^=]")


class CalculationError(ValueError):
    """Erreur de calcul (expression invalide ou hors périmètre)."""


@dataclass
class CalculationResult:
    expression: str
    kind: str            # eval | simplify | solve | derivative | integral
    result: str
    latex: str


def looks_like_calculation(text: str) -> bool:
    """Heuristique : la question requiert-elle l'outil de calcul ?"""
    return bool(_CALC_KEYWORDS.search(text) or _MATH_EXPR.search(text))


def _guard(expression: str) -> None:
    if _FORBIDDEN.search(expression):
        raise CalculationError("Expression rejetée par le sandbox.")


def _parse(expression: str):
    _guard(expression)
    try:
        # global_dict laissé par défaut : parse_expr a besoin du namespace SymPy
        # (Symbol, Integer…) pour l'auto-symbolisation. La sûreté vient de la
        # tokenisation (les noms inconnus deviennent des Symbol, jamais des
        # appels) et du garde-fou _guard en amont.
        return parse_expr(
            expression,
            local_dict=dict(_ALLOWED_NAMES),
            transformations=_TRANSFORMS,
            evaluate=True,
        )
    except CalculationError:
        raise
    except Exception as exc:
        # Entrée élève arbitraire (texte, apostrophes, syntaxe invalide…) :
        # toute défaillance d'analyse devient une CalculationError que
        # route_tool traite par un repli silencieux vers le LLM.
        raise CalculationError(f"Impossible d'analyser l'expression : {expression!r}") from exc


def evaluate(expression: str) -> CalculationResult:
    """Évalue/simplifie une expression (arithmétique ou algébrique composite)."""
    expr = _parse(expression)
    simplified = sympy.simplify(expr)
    kind = "eval" if simplified.is_number else "simplify"
    result = str(simplified)
    if simplified.is_number and simplified.free_symbols == set():
        # Forme décimale utile pour les résultats numériques.
        try:
            numeric = simplified.evalf()
            if numeric != simplified:
                result = f"{simplified} = {numeric}"
        except (ValueError, TypeError):
            pass
    return CalculationResult(expression, kind, result, sympy.latex(simplified))


def differentiate(expression: str, variable: str = "x") -> CalculationResult:
    expr = _parse(expression)
    var = sympy.Symbol(variable)
    derivative = sympy.diff(expr, var)
    return CalculationResult(expression, "derivative", str(derivative), sympy.latex(derivative))


def solve_equation(equation: str, variable: str = "x") -> CalculationResult:
    _guard(equation)
    var = sympy.Symbol(variable)
    if "=" in equation:
        left, right = equation.split("=", 1)
        expr = _parse(left) - _parse(right)
    else:
        expr = _parse(equation)
    solutions = sympy.solve(expr, var)
    return CalculationResult(equation, "solve", str(solutions), sympy.latex(solutions))


def compute(query: str) -> CalculationResult:
    """Route une requête de calcul vers l'opération appropriée.

    Détecte l'intention par mots-clés ; à défaut, évalue/simplifie l'expression.
    Le texte narratif est nettoyé pour isoler l'expression mathématique.
    """
    _guard(query)
    lowered = query.lower()
    expr_text = _extract_expression(query)
    try:
        if re.search(r"d[ée]riv|derivative", lowered):
            return differentiate(expr_text)
        if re.search(r"r[ée]sou|solve|[ée]quation", lowered) or "=" in expr_text:
            return solve_equation(expr_text)
        return evaluate(expr_text)
    except CalculationError:
        raise
    except Exception as exc:  # défaillance sympy résiduelle -> repli silencieux
        raise CalculationError(f"Calcul impossible pour : {query!r}") from exc


def _extract_expression(query: str) -> str:
    """Isole la sous-chaîne mathématique d'une question en langage naturel."""
    # Retire les délimiteurs LaTeX inline et garde la partie « calculable ».
    cleaned = query.replace("$", " ")
    match = re.search(r"[0-9x)(][0-9xX\s+\-*/^=.,()sqrtcoinlgexp]*", cleaned)
    candidate = (match.group(0) if match else cleaned).strip(" .,")
    return candidate or cleaned
