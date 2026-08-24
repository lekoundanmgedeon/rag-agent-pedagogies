"""MCP Math Server (Priorité 1) — Serveur MCP dédié aux calculs mathématiques.

Expose les capacités SymPy en tant que tools standards MCP.
Ce serveur peut être lancé de manière autonome via FastMCP.
"""

import sympy
from mcp.server.fastmcp import FastMCP

# Initialisation du serveur FastMCP
mcp = FastMCP("nuru-math-mcp")

def _parse(expr_str: str) -> sympy.Expr:
    """Parse une expression avec sécurité basique (sans eval natif)."""
    from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor
    transformations = standard_transformations + (convert_xor, implicit_multiplication_application)
    # Limiter les variables pour éviter l'exécution arbitraire
    return parse_expr(expr_str, transformations=transformations, evaluate=False)

@mcp.tool()
def sympy_solve(equation: str, variable: str = "x") -> str:
    """Résout une équation ou un système.
    
    Args:
        equation: L'équation à résoudre (ex: "x**2 - 4 = 0" ou "x**2 = 4").
        variable: La variable par rapport à laquelle résoudre.
    """
    try:
        var = sympy.Symbol(variable)
        if "=" in equation:
            gauche, droite = equation.split("=", 1)
            expr = _parse(gauche) - _parse(droite)
        else:
            expr = _parse(equation)
        
        resultat = sympy.solve(expr, var)
        return str(resultat)
    except Exception as e:
        return f"Erreur de résolution : {e}"

@mcp.tool()
def sympy_simplify(expression: str) -> str:
    """Simplifie une expression mathématique.
    
    Args:
        expression: L'expression à simplifier.
    """
    try:
        expr = _parse(expression)
        resultat = sympy.simplify(expr)
        return str(resultat)
    except Exception as e:
        return f"Erreur de simplification : {e}"

@mcp.tool()
def sympy_derivative(expression: str, variable: str = "x") -> str:
    """Calcule la dérivée d'une expression.
    
    Args:
        expression: L'expression à dériver.
        variable: La variable de dérivation.
    """
    try:
        var = sympy.Symbol(variable)
        expr = _parse(expression)
        resultat = sympy.diff(expr, var)
        return str(resultat)
    except Exception as e:
        return f"Erreur de dérivation : {e}"

@mcp.tool()
def sympy_integrate(expression: str, variable: str = "x") -> str:
    """Calcule une intégrale indéfinie.
    
    Args:
        expression: L'expression à intégrer.
        variable: La variable d'intégration.
    """
    try:
        var = sympy.Symbol(variable)
        expr = _parse(expression)
        resultat = sympy.integrate(expr, var)
        return str(resultat)
    except Exception as e:
        return f"Erreur d'intégration : {e}"

@mcp.tool()
def sympy_factor(expression: str) -> str:
    """Factorise une expression mathématique.
    
    Args:
        expression: L'expression à factoriser.
    """
    try:
        expr = _parse(expression)
        resultat = sympy.factor(expr)
        return str(resultat)
    except Exception as e:
        return f"Erreur de factorisation : {e}"

@mcp.tool()
def sympy_check(expression1: str, expression2: str) -> str:
    """Vérifie si deux expressions mathématiques sont algébriquement équivalentes.
    Utile pour vérifier si la réponse proposée par un modèle ou un élève est correcte.
    
    Args:
        expression1: La première expression (ex: résultat attendu).
        expression2: La seconde expression (ex: réponse proposée).
    """
    try:
        expr1 = _parse(expression1)
        expr2 = _parse(expression2)
        # simplify(expr1 - expr2) == 0 est le test standard d'équivalence
        diff = sympy.simplify(expr1 - expr2)
        if diff == 0:
            return "Vrai : Les expressions sont mathématiquement équivalentes."
        else:
            return "Faux : Les expressions ne sont pas équivalentes."
    except Exception as e:
        return f"Erreur de vérification : {e}"

if __name__ == "__main__":
    mcp.run()
