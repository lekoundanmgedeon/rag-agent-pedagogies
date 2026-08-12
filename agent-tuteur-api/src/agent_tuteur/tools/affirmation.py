"""Vérification symbolique des **affirmations de l'élève** — cas QA #15.

La calculatrice (:mod:`agent_tuteur.tools.calculator`) vérifie ce que l'agent
s'apprête à dire. Ce module fait le trajet inverse : il vérifie ce que l'élève
vient d'affirmer. « La dérivée de ln(x) c'est bien 1/x² non ? » est une
demande de confirmation, et l'agent y répondait par une question vague — donc
laissait une erreur s'installer.

C'est la règle non-négociable n°2 lue dans l'autre sens : ne jamais halluciner
un résultat, mais ne jamais laisser passer un faux non plus quand l'outil peut
trancher. Le module ne décide de rien tout seul : il renvoie un verdict
symbolique, et le graphe s'en sert pour contraindre le prompt.

**Périmètre volontairement étroit.** Seules les affirmations de la forme
« la dérivée / la primitive / l'intégrale de X, c'est Y » sont reconnues. Ce
sont celles où l'élève énonce un résultat vérifiable sans ambiguïté. Hors de
cette forme, le module renvoie ``None`` et rien n'est affirmé sur la validité :
un silence vaut mieux qu'un verdict fabriqué.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy

from agent_tuteur.tools.calculator import (
    CalculationError,
    analyser_expression,
    normaliser_expression,
)

#: Formes d'énoncé reconnues, et l'opération symbolique correspondante.
_OPERATIONS = {
    "derivee": ("d[ée]riv[ée]?e?", "dérivée"),
    "primitive": ("primitive", "primitive"),
    "integrale": ("int[ée]grale", "intégrale"),
}

#: « la dérivée de X c'est Y », « la primitive de X est Y », « … vaut Y ».
#: Le sujet est capté sans gourmandise pour s'arrêter au premier verbe
#: d'attribution, sinon il avalerait l'affirmation elle-même.
_AFFIRMATION = re.compile(
    r"(?:la\s+|l['’]\s*)?"
    r"(?P<op>d[ée]riv[ée]?e?|primitive|int[ée]grale)\s+de\s+"
    r"(?P<sujet>.+?)\s*"
    r"(?:,\s*)?(?:c['’e]est|est|vaut|fait|donne|=)\s*"
    r"(?:bien\s+|[ée]gale?\s+[àa]\s+|[àa]\s+)?"
    r"(?P<affirme>[^,;?!]+)",
    re.IGNORECASE,
)

#: Marqueur de demande de confirmation en fin de phrase (« …, non ? »). Il fait
#: partie de la question, pas de l'expression : le laisser ferait échouer
#: l'analyse symbolique de ce que l'élève affirme.
_TAG_FINAL = re.compile(
    r"\s*,?\s*(?:non|n['’e]est[\s-]?ce\s+pas|c['’e]est\s+[cç]a|hein|je\s+crois|"
    r"il\s+me\s+semble|right)\s*\??\s*$",
    re.IGNORECASE,
)

#: L'élève pose sa question, il n'affirme rien : « quelle est la dérivée de… ».
#: Sans ce filtre, une question serait traitée comme une affirmation fausse.
_INTERROGATIF = re.compile(
    r"\b(?:quelle?\s+est|quel\s+est|comment|pourquoi|calcule[rz]?|"
    r"donne[\s-]?moi|trouve[rz]?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AffirmationEleve:
    """Verdict symbolique sur ce que l'élève vient d'affirmer."""

    operation: str      # libellé lisible : « dérivée », « primitive »…
    sujet: str          # l'expression sur laquelle porte l'affirmation
    affirme: str        # ce que l'élève annonce, tel qu'analysé
    attendu: str        # ce que le calcul symbolique donne
    correcte: bool

    @property
    def a_corriger(self) -> bool:
        return not self.correcte


def _nettoyer(fragment: str) -> str:
    return _TAG_FINAL.sub("", fragment).strip(" .,;:")


def _resultat_attendu(operation: str, sujet, variable):
    if operation == "derivee":
        return sympy.diff(sujet, variable)
    # Primitive et intégrale se comparent à une constante près : c'est la
    # dérivée de ce que l'élève propose qu'on confronte au sujet.
    return sympy.integrate(sujet, variable)


def _equivalent(operation: str, sujet, affirme, attendu, variable) -> bool:
    if operation == "derivee":
        return sympy.simplify(affirme - attendu) == 0
    # Une primitive est juste si sa dérivée redonne le sujet — sans quoi
    # « x²/2 + 3 » serait déclaré faux pour la primitive de x.
    return sympy.simplify(sympy.diff(affirme, variable) - sujet) == 0


def verifier_affirmation(question: str, variable: str = "x") -> AffirmationEleve | None:
    """Vérifie une affirmation mathématique de l'élève, ou renvoie ``None``.

    ``None`` signifie « aucune affirmation vérifiable détectée » — soit la
    tournure n'est pas reconnue, soit l'élève pose une question au lieu
    d'affirmer, soit SymPy n'a pas pu trancher. Dans tous ces cas, le graphe
    n'annonce rien : c'est la règle n°2 (ne jamais affirmer ce qui n'a pas été
    vérifié), appliquée au verdict lui-même.
    """
    if _INTERROGATIF.search(question):
        return None

    match = _AFFIRMATION.search(question)
    if match is None:
        return None

    brut_op = match.group("op").lower()
    cle = next(
        (k for k, (motif, _) in _OPERATIONS.items() if re.fullmatch(motif, brut_op, re.IGNORECASE)),
        None,
    )
    if cle is None:
        return None
    libelle = _OPERATIONS[cle][1]

    texte_sujet = _nettoyer(match.group("sujet"))
    texte_affirme = _nettoyer(match.group("affirme"))
    if not texte_sujet or not texte_affirme:
        return None

    var = sympy.Symbol(variable)
    try:
        sujet = analyser_expression(texte_sujet)
        affirme = analyser_expression(texte_affirme)
        attendu = _resultat_attendu(cle, sujet, var)
        correcte = bool(_equivalent(cle, sujet, affirme, attendu, var))
    except (CalculationError, TypeError, ValueError, AttributeError):
        # Entrée élève arbitraire : l'incapacité à trancher n'est pas un
        # verdict. On se tait plutôt que de déclarer une erreur à tort.
        return None

    return AffirmationEleve(
        operation=libelle,
        sujet=str(sujet),
        affirme=str(affirme),
        attendu=str(attendu),
        correcte=correcte,
    )


def normaliser(texte: str) -> str:
    """Réexport utilitaire (les tests comparent des formes normalisées)."""
    return normaliser_expression(texte)
