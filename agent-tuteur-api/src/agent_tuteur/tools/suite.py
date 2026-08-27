"""Suite récurrente vérifiée symboliquement — cas QA #33.

Le testeur **valide** la réponse reçue : il ne signale pas d'erreur, il signale
un risque — « le besoin d'un outil de vérification pour garantir que le
raisonnement détaillé ne contient pas d'erreur cachée ». Une démonstration par
récurrence est longue, et chacune de ses étapes est une occasion de se tromper
avec assurance : c'est exactement la situation que la règle non-négociable n°2
vise.

Ce module ne juge pas *le raisonnement* — aucun outil ne le fait ici — mais il
établit les **faits** sur lesquels ce raisonnement doit tomber : les premiers
termes, la monotonie, la borne, la limite. Le prompt les donne ensuite au modèle
comme déjà vérifiés, avec interdiction de les recalculer. Une démonstration qui
conclurait autrement se contredirait alors visiblement.

**Ce qui est démontré, et ce qui ne l'est pas.** Pour une récurrence *affine*
``u(n+1) = a·u(n) + b`` — le cas de figure du programme de Terminale, et celui du
cas #33 — la forme close ``u(n) = L + (u0 − L)·aⁿ`` (avec ``L = b/(1−a)``) donne
la monotonie, la borne et la limite de façon exacte. Hors de ce cadre, on rend
les premiers termes et le point fixe candidat, et rien d'autre : le champ reste
vide plutôt que d'être approximé.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import sympy

#: Indices et exposants Unicode que les élèves (et les énoncés) emploient
#: couramment : « u₀ », « uₙ₊₁ ». Sans cette translittération, l'expression est
#: illisible pour SymPy — le même défaut qui produisait un résultat faux au cas
#: QA #1, où « x³ − 3x » était tronqué au premier caractère non ASCII.
_INDICES_UNICODE = str.maketrans(
    {
        "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
        "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
        "ₙ": "n", "₊": "+", "₋": "-", "⁺": "+", "⁻": "-",
        "−": "-", "–": "-", "—": "-", "×": "*", "÷": "/",
        "’": "'", " ": " ",
    }
)

#: Terme initial : « u0 = 2 », « u_0 = 2 », « u(0) = 2 ».
_TERME_INITIAL = re.compile(
    r"\bu\s*(?:_\s*)?(?:\(\s*0\s*\)|\{?\s*0\s*\}?)\s*=\s*(?P<valeur>-?\d+(?:[./]\d+)?)",
    re.IGNORECASE,
)

#: Relation de récurrence : « u_{n+1} = (u_n + 3)/2 », « u(n+1) = ... ».
#: Le membre de droite s'arrête au premier mot de français : sans cette borne,
#: « u(n+1) = (u(n) + 3)/2 **est monotone, majorée, et calcule sa limite** »
#: partait en entier dans SymPy, qui renonçait — et l'outil rendait ``None`` sur
#: le prompt même du cas #33.
_FIN_D_EXPRESSION = (
    r"(?=\s+(?:est|sont|pour|avec|donc|montre|d[ée]montre|calcule|d[ée]termine|"
    r"sachant|puis|alors|en\s|o[ùu]\b|et\s+(?:que|calcul|montre|d[ée]montre))"
    # Un point suivi d'un chiffre est une décimale, pas une fin de phrase : sans
    # cette borne, « u(n+1) = 0.5*u(n) + 1 » était tronqué à « 0 ».
    r"|\s*[.;\n](?!\d)|$)"
)

_RECURRENCE = re.compile(
    r"\bu\s*(?:_\s*)?(?:\(\s*n\s*\+\s*1\s*\)|\{?\s*n\s*\+\s*1\s*\}?)\s*=\s*"
    # Le point n'est PAS exclu de la classe : il appartient aux décimales. C'est
    # le lookahead ci-dessus qui distingue la fin de phrase du séparateur
    # décimal.
    r"(?P<membre>[^;\n]+?)" + _FIN_D_EXPRESSION,
    re.IGNORECASE,
)

#: Occurrences de « u_n » dans le membre de droite, ramenées à un symbole.
_TERME_COURANT = re.compile(r"\bu\s*(?:_\s*)?(?:\(\s*n\s*\)|\{?\s*n\s*\}?|n)", re.IGNORECASE)

#: Formulations qui appellent une étude de suite récurrente.
_DEMANDE_SUITE = re.compile(
    r"\b(?:suite|s[ée]rie)\b[^.;\n]{0,60}\b(?:d[ée]finie|r[ée]currente|par\s+r[ée]currence)\b"
    r"|\bu\s*(?:_\s*)?(?:\(\s*n\s*\+\s*1\s*\)|\{?\s*n\s*\+\s*1\s*\}?)\s*=",
    re.IGNORECASE,
)

#: Nombre de termes explicités pour l'élève. Assez pour amorcer une récurrence,
#: pas au point de faire le travail à sa place.
NB_TERMES = 5


@dataclass
class SuiteRecurrente:
    """Ce qui a été **établi** sur la suite. Les champs vides sont des aveux."""

    terme_initial: str
    relation: str
    premiers_termes: list[str] = field(default_factory=list)
    #: « croissante », « décroissante », « constante » — ou ``None`` si non établi.
    monotonie: str | None = None
    #: Majorant ou minorant démontré, avec son sens (« majorée par 3 »).
    borne: str | None = None
    #: Limite exacte, ou ``None`` si la convergence n'est pas démontrée.
    limite: str | None = None
    #: Forme close, quand elle existe (récurrence affine).
    forme_close: str | None = None

    @property
    def est_exploitable(self) -> bool:
        return bool(self.premiers_termes)


def demande_une_suite_recurrente(query: str) -> bool:
    """Vrai si l'énoncé définit une suite par récurrence."""
    return bool(_DEMANDE_SUITE.search(_normaliser(query)))


def _normaliser(texte: str) -> str:
    return unicodedata.normalize("NFKC", texte).translate(_INDICES_UNICODE)


def _rogner_jusqu_a_l_expression(membre: str, u: sympy.Symbol) -> str | None:
    """Garde le plus long **début** du membre droit qui soit une expression.

    Le motif s'arrête déjà aux mots de liaison les plus courants, mais la liste
    ne peut pas être exhaustive : « … = 3*u_n - 4 **converge**, et calcule sa
    limite » lui échappait, et l'énoncé entier partait dans SymPy, qui renonçait
    — l'outil rendait alors ``None`` sur une suite parfaitement analysable.

    On rogne donc mot à mot par la fin jusqu'à obtenir quelque chose de lisible.
    Ce qui n'est pas une expression tombe de lui-même, sans qu'on ait à prévoir
    la formulation de l'énoncé.
    """
    mots = membre.split()
    while mots:
        candidat = " ".join(mots).rstrip(" ,;:")
        try:
            expression = sympy.sympify(candidat, locals={"u": u})
        except (sympy.SympifyError, TypeError, ValueError, SyntaxError):
            mots.pop()
            continue
        if getattr(expression, "free_symbols", set()) <= {u}:
            return candidat
        mots.pop()
    return None


def analyser_la_demande(query: str) -> SuiteRecurrente | None:
    """Établit ce qui est démontrable sur la suite de l'énoncé, ou ``None``.

    ``None`` signifie « rien d'exploitable ici » : ni terme initial, ni relation
    de récurrence lisibles. C'est un aveu, pas un échec silencieux — l'appelant
    laisse alors le tour se dérouler sans prétendre avoir vérifié quoi que ce soit.
    """
    texte = _normaliser(query)
    depart = _TERME_INITIAL.search(texte)
    relation = _RECURRENCE.search(texte)
    if depart is None or relation is None:
        return None

    u = sympy.Symbol("u", real=True)
    membre = _rogner_jusqu_a_l_expression(
        _TERME_COURANT.sub("u", relation.group("membre").strip()), u
    )
    if membre is None:
        return None
    try:
        # ``rational=True`` : « 0.5 » devient 1/2, et toute la suite reste
        # exacte. Un flottant ferait dériver les termes puis la limite, et la
        # règle n°2 interdit d'annoncer un résultat qu'on n'a pas exactement.
        f = sympy.nsimplify(sympy.sympify(membre, locals={"u": u}), rational=True)
        u0 = sympy.nsimplify(depart.group("valeur").replace("/", "/"))
    except (sympy.SympifyError, TypeError, ValueError, SyntaxError):
        return None
    if f.free_symbols - {u}:
        # Une lettre inconnue traîne dans la relation : on ne devine pas.
        return None

    # Le symbole de travail s'appelle « u » ; on l'affiche « u(n) », qui est la
    # notation de l'énoncé. Une relation rendue « u/2 + 3/2 » se relit mal, et
    # c'est le modèle qui devrait deviner de quoi « u » est le nom.
    lisible = sympy.sstr(f.subs(u, sympy.Symbol("u(n)")))
    suite = SuiteRecurrente(
        terme_initial=f"u(0) = {u0}",
        relation=f"u(n+1) = {lisible}",
    )

    terme = sympy.nsimplify(u0)
    termes = [terme]
    for _ in range(NB_TERMES - 1):
        terme = sympy.simplify(f.subs(u, terme))
        termes.append(terme)
    suite.premiers_termes = [sympy.sstr(t) for t in termes]

    _completer_si_affine(suite, f, u, sympy.nsimplify(u0))
    return suite


def _completer_si_affine(
    suite: SuiteRecurrente, f: sympy.Expr, u: sympy.Symbol, u0: sympy.Expr
) -> None:
    """Monotonie, borne et limite — **démontrées**, pour une récurrence affine.

    Le raisonnement tient en une ligne et il est exact : si ``u(n+1) = a·u(n) + b``
    avec ``a ≠ 1``, alors ``u(n) − L = aⁿ·(u0 − L)`` où ``L = b/(1−a)`` est le
    point fixe. Le signe de ``u0 − L`` donne le sens de variation et la borne, et
    ``|a| < 1`` donne la convergence vers ``L``.

    Hors de ce cadre (récurrence non affine), rien n'est renseigné : les champs
    restent vides et le prompt n'annoncera donc ni monotonie ni limite.
    """
    polynome = sympy.Poly(sympy.expand(f), u) if f.is_polynomial(u) else None
    if polynome is None or polynome.degree() > 1:
        return
    a = polynome.coeff_monomial(u)
    b = polynome.coeff_monomial(1)
    if a == 1:
        # Suite arithmétique : monotonie et absence de borne se lisent sur b.
        suite.monotonie = "croissante" if b > 0 else "décroissante" if b < 0 else "constante"
        suite.forme_close = sympy.sstr(sympy.simplify(u0 + b * sympy.Symbol("n")))
        return

    limite = sympy.simplify(b / (1 - a))
    ecart = sympy.simplify(u0 - limite)
    n = sympy.Symbol("n", integer=True, nonnegative=True)
    suite.forme_close = sympy.sstr(sympy.simplify(limite + ecart * a**n))

    if a > 0:
        # u(n+1) − u(n) = aⁿ(a − 1)(u0 − L) : le signe est constant, donc la
        # monotonie est stricte et démontrée. Il dépend de DEUX facteurs — ne
        # regarder que l'écart à la limite donnait « décroissante » pour
        # u(n+1) = 3u(n) − 4 partant de 5, qui croît vers l'infini.
        sens = sympy.sign((a - 1) * ecart)
        if sens > 0:
            suite.monotonie = "croissante"
        elif sens < 0:
            suite.monotonie = "décroissante"
        else:
            suite.monotonie = "constante"

        # L'écart garde son signe : la suite reste du même côté de L, quel que
        # soit a. C'est une borne démontrée — pas nécessairement la plus utile
        # quand la suite diverge, mais elle est vraie.
        if ecart < 0:
            suite.borne = f"majorée par {sympy.sstr(limite)}"
        elif ecart > 0:
            suite.borne = f"minorée par {sympy.sstr(limite)}"
        else:
            suite.borne = f"constante égale à {sympy.sstr(limite)}"

    if abs(a) < 1:
        suite.limite = sympy.sstr(limite)
