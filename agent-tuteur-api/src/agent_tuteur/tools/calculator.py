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
_TRANSFORMS = (
    *standard_transformations,
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

# --- Normalisation des notations réellement saisies par les élèves -----------
# Un élève tape « x³ − 3x », colle « x²·ln(x) », écrit « 3 × 4 ÷ 2 ». Sans cette
# normalisation, l'extraction s'arrêtait au premier caractère non ASCII et
# calculait sur le fragment restant — c'est l'origine du cas QA #1, où « x³ − 3x »
# était réduit à « x » et dérivé en « 1 », résultat faux présenté comme vérifié.
_EXPOSANTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_RUN_EXPOSANTS = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+")
_SYMBOLES = {
    "−": "-", "–": "-", "—": "-", "‐": "-",   # moins et tirets typographiques
    "×": "*", "·": "*", "∗": "*", "⋅": "*",
    "÷": "/", "⁄": "/",
    # « : » n'est PAS normalisé en division : en français c'est d'abord de la
    # ponctuation (« le nombre complexe : z = … »), et le confondre avec un
    # opérateur fabriquait des expressions absurdes.
    "√": "sqrt",
    "\u00a0": " ", "\u202f": " ",   # espaces insécables (dont la fine française)
    "’": "'",
}

#: Caractères qui portent du sens mathématique et ne doivent JAMAIS être perdus
#: silencieusement par l'extraction.
_SIGNIFIANTS = set("0123456789+-*/^=()")

#: Sous-ensemble servant à *détecter* la présence d'une expression. Le tiret en
#: est exclu à dessein : en français il relie des mots (« dérive-t-on »,
#: « donne-moi ») bien plus souvent qu'il ne soustrait. Il reste en revanche
#: dans :data:`_SIGNIFIANTS`, car perdre un moins pendant l'extraction fausse
#: le calcul en silence.
_SIGNIFIANTS_DETECTION = set("0123456789+*/^=()")

#: Suites de lettres admises dans une expression : une variable d'une lettre, ou
#: une fonction connue. Tout autre mot signale que l'extraction a happé du texte
#: français — « exercice » se parsait en produit ``c*e*i*r*x``, et le résultat
#: était présenté à l'élève comme vérifié symboliquement (cas QA #1 et #6).
_MOTS_AUTORISES = {nom.lower() for nom in _ALLOWED_NAMES} | {"d", "dx", "dy", "dt"}
_MOTS = re.compile(r"[a-zA-Z_]+")


def normaliser_expression(texte: str) -> str:
    """Ramène les notations Unicode usuelles à une syntaxe analysable par SymPy.

    ``x³`` → ``x**3``, ``−`` → ``-``, ``×``/``·`` → ``*``, ``÷`` → ``/``,
    ``√`` → ``sqrt``. Purement lexical : aucune interprétation mathématique.
    """
    texte = _RUN_EXPOSANTS.sub(lambda m: "**" + m.group(0).translate(_EXPOSANTS), texte)
    for source, cible in _SYMBOLES.items():
        texte = texte.replace(source, cible)
    return texte


# Verbe impératif de calcul : l'élève demande un résultat concret, pas une
# explication de méthode. Distinction indispensable — « Comment dériver un
# quotient ? » (fixture positive #54) est une question de cours, pas un calcul.
_CALC_IMPERATIF = re.compile(
    r"\b(?:calcule[rz]?|r[ée]sous|r[ée]soudre|resous|simplifie[rz]?|factorise[rz]?|"
    r"d[ée]veloppe[rz]?|d[ée]rive[rz]?|int[èe]gre[rz]?)\b",
    re.IGNORECASE,
)
_INTERROGATIF = re.compile(
    r"\b(?:comment|pourquoi|qu['e]\s*est[\s-]?ce|[àa]\s+quoi\s+sert|"
    r"quelle?\s+est\s+la\s+(?:formule|m[ée]thode|r[èe]gle|d[ée]finition)|"
    r"quand\s+(?:peut|doit)[\s-]?on)\b",
    re.IGNORECASE,
)


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
            # « dérive f(x) = x²·ln(x) » : c'est le membre de droite qu'on dérive,
            # pas l'égalité (qui, elle, partirait en résolution d'équation).
            if definition := _DEFINITION_FONCTION.match(expr_text):
                expr_text = definition.group("corps").strip()
            return differentiate(expr_text)
        if re.search(r"r[ée]sou|solve|[ée]quation", lowered) or "=" in expr_text:
            return solve_equation(expr_text)
        return evaluate(expr_text)
    except CalculationError:
        raise
    except Exception as exc:  # défaillance sympy résiduelle -> repli silencieux
        raise CalculationError(f"Calcul impossible pour : {query!r}") from exc


def contient_une_expression(query: str) -> bool:
    """Vrai si la question porte une expression mathématique concrète."""
    return any(c in _SIGNIFIANTS_DETECTION for c in normaliser_expression(query))


def demande_un_calcul_concret(query: str) -> bool:
    """Vrai si l'élève attend un **résultat**, pas une explication de méthode.

    C'est ce prédicat qui décide si un échec de l'outil doit être avoué à
    l'élève (règle non-négociable n°2) ou simplement ignoré. « Comment dériver
    un quotient de fonctions ? » ne demande aucun résultat : l'outil n'a rien à
    vérifier, et son silence n'est pas un aveu à faire.
    """
    if contient_une_expression(query):
        return True
    return bool(_CALC_IMPERATIF.search(query)) and not _INTERROGATIF.search(query)


#: Définition de fonction en tête d'énoncé : « f(x) = … », « y = … ». Sur une
#: demande de dérivée, c'est le membre de droite qui doit être dérivé.
_DEFINITION_FONCTION = re.compile(
    r"^\s*(?:[a-zA-Z]\s*\(\s*[a-zA-Z]\s*\)|[yz])\s*=\s*(?P<corps>.+)$", re.DOTALL
)


def _extract_expression(query: str) -> str:
    """Isole l'expression mathématique d'une question en langage naturel.

    **Propriété de sûreté centrale** : l'extraction ne tronque jamais en
    silence. La sous-chaîne retenue doit contenir *tous* les caractères
    mathématiquement signifiants de la question ; sinon on lève plutôt que de
    calculer sur un fragment. Sans ce contrôle, « x³ − 3x » devenait « x » et
    « exercice » devenait le produit ``c*e*i*r*x`` — dans les deux cas un
    résultat faux annoncé comme vérifié (cas QA #1 et #6).
    """
    texte = normaliser_expression(query).replace("$", " ")

    positions = [i for i, c in enumerate(texte) if c in _SIGNIFIANTS]
    if not positions:
        raise CalculationError(f"Aucune expression mathématique dans : {query!r}")

    debut, fin = positions[0], positions[-1] + 1
    # Étend la fenêtre aux identifiants collés aux bornes : « **3 - 3 » doit
    # redevenir « x**3 - 3x », sans quoi la variable elle-même serait perdue.
    while debut > 0 and (texte[debut - 1].isalnum() or texte[debut - 1] == "_"):
        debut -= 1
    while fin < len(texte) and (texte[fin].isalnum() or texte[fin] == "_"):
        fin += 1

    candidate = texte[debut:fin].strip(" .,;:")
    if not candidate:
        raise CalculationError(f"Aucune expression mathématique dans : {query!r}")

    # Contrôle de couverture : rien de signifiant ne doit rester dehors.
    perdus = [c for c in texte[:debut] + texte[fin:] if c in _SIGNIFIANTS]
    if perdus:
        raise CalculationError(
            f"Expression ambiguë (fragments hors analyse : {''.join(perdus)!r}) dans {query!r}"
        )

    # Contrôle inverse : rien de non mathématique ne doit être entré dedans.
    # Sans lui, la fenêtre happe le texte français qui sépare deux nombres et
    # SymPy le transforme docilement en produit de variables.
    intrus = [m for m in _MOTS.findall(candidate) if len(m) > 1 and m.lower() not in _MOTS_AUTORISES]
    if intrus:
        raise CalculationError(
            f"Texte non mathématique dans l'expression ({', '.join(intrus)}) : {query!r}"
        )
    return candidate
