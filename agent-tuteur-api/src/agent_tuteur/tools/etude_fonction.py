"""Étude de fonction vérifiée symboliquement — cas QA #9.

« Fais-moi l'étude de fonction de ln(x) » est une demande de **livrable
structuré** : domaine de définition, limites aux bornes, dérivée, sens de
variation. L'agent la traitait comme un exercice ordinaire et lui appliquait la
graduation socratique, dont le niveau 1 prescrit « rappelle la règle SANS
l'appliquer au cas de l'élève » — d'où la définition redemandée à l'élève au
lieu de l'étude demandée.

Le contenu ne peut pas venir du corpus : aucune leçon indexée ne porte sur
l'étude des fonctions logarithmes. Le produire par le modèle serait exactement
ce qu'interdit la règle non-négociable n°2. Chaque élément rendu ici est donc
**calculé par SymPy**, et ce qui ne peut pas l'être n'est pas rendu du tout :
:class:`EtudeFonction` porte des champs vides plutôt que des approximations, et
le prompt sait alors ne rien affirmer là-dessus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy
from sympy.calculus.util import continuous_domain

from agent_tuteur.tools.calculator import (
    CalculationError,
    analyser_expression,
    extraire_expression,
)

#: Formulations d'une demande d'étude de fonction. Le point commun est
#: l'attente d'un livrable complet, pas d'un indice : « étudie », « tableau de
#: variation », « sens de variation » appellent tous les mêmes quatre blocs.
_DEMANDE_ETUDE = re.compile(
    r"[ée]tude\s+(?:complete\s+|complète\s+)?(?:de\s+(?:la\s+)?fonction|de\s+fct)"
    r"|[ée]tudie[rz]?\s+(?:la\s+)?(?:fonction|les\s+variations)"
    r"|tableau\s+de\s+variations?"
    r"|sens\s+de\s+variations?"
    r"|variations?\s+de\s+la\s+fonction",
    re.IGNORECASE,
)

#: Variable d'étude. Le programme de Terminale n'étudie que des fonctions d'une
#: variable réelle, et le corpus les note toutes ``x``.
VARIABLE = "x"


#: Mots de liaison entre la formule de demande et la fonction elle-même
#: (« étude de fonction **de la** fonction f définie par … »).
_LIAISON = re.compile(
    r"^[\s:,]*(?:de\s+la\s+|de\s+l['’]|de\s+|d['’]|la\s+|le\s+|les\s+|suivante\s*)*",
    re.IGNORECASE,
)


def demande_une_etude_de_fonction(query: str) -> bool:
    """Vrai si l'élève réclame une étude de fonction, sous l'une de ses formes."""
    return bool(_DEMANDE_ETUDE.search(query))


def expression_demandee(query: str) -> str:
    """Portion de la question qui nomme la fonction à étudier.

    On découpe **après** la formule de demande plutôt que d'extraire depuis la
    phrase entière. La raison est concrète : ``extraire_expression`` refuse — à
    raison — de tronquer une phrase où un caractère mathématiquement signifiant
    resterait dehors, et le trait d'union de « Fais-moi » en est un. Extraire
    depuis la phrase complète échouait donc sur « Fais-moi l'étude de fonction
    de ln(x) » tout en réussissant sur « fais moi l'etude … », ce qui aurait
    fait dépendre le correctif de la ponctuation du testeur.

    La fonction suit toujours la formule de demande : couper là supprime le
    problème à la source au lieu d'affaiblir le garde-fou d'extraction.
    """
    correspondance = _DEMANDE_ETUDE.search(query)
    if correspondance is None:
        return ""
    reste = query[correspondance.end() :]
    return _LIAISON.sub("", reste, count=1).strip(" .?!:;")


@dataclass(frozen=True)
class EtudeFonction:
    """Résultat d'une étude, entièrement vérifié symboliquement.

    Tout champ que SymPy n'a pas su établir reste vide. C'est volontaire : un
    champ absent laisse le prompt muet sur ce point, là où une valeur inventée
    ferait dire à l'agent une chose fausse avec assurance.
    """

    #: Expression sous sa forme SymPy (« log(x) »), telle qu'analysée.
    expression: str
    #: Domaine de continuité, ou "" si SymPy n'a pas conclu.
    domaine: str
    #: Dérivée simplifiée, ou "" si SymPy n'a pas conclu.
    derivee: str
    #: Limites aux bornes du domaine : ``(borne, valeur)``.
    limites: tuple[tuple[str, str], ...] = ()
    #: Sens de variation par intervalle : ``(intervalle, "croissante"|"décroissante")``.
    variations: tuple[tuple[str, str], ...] = ()

    @property
    def est_exploitable(self) -> bool:
        """Au moins le domaine et la dérivée, sans quoi il n'y a pas d'étude."""
        return bool(self.domaine and self.derivee)


def _borne_lisible(valeur) -> str:
    """« oo » → « +∞ », « -oo » → « -∞ » ; le reste inchangé."""
    texte = str(valeur)
    return {"oo": "+∞", "-oo": "-∞", "zoo": "∞"}.get(texte, texte)


def format_ensemble(ensemble) -> str:
    """Rend un ensemble SymPy dans la notation française du lycée.

    ``Interval.open(0, oo)`` → ``]0 ; +∞[``. La forme SymPy est exacte mais
    illisible pour un élève de Terminale, et la donner telle quelle au modèle
    l'inviterait à la retranscrire lui-même — donc à se tromper sur une valeur
    pourtant vérifiée. On la traduit ici, une fois, plutôt que d'espérer.
    """
    if ensemble == sympy.S.Reals:
        return "ℝ"
    if isinstance(ensemble, sympy.Union):
        return " ∪ ".join(format_ensemble(part) for part in ensemble.args)
    if isinstance(ensemble, sympy.Interval):
        gauche = "[" if ensemble.left_open is False else "]"
        droite = "]" if ensemble.right_open is False else "["
        return f"{gauche}{_borne_lisible(ensemble.inf)} ; {_borne_lisible(ensemble.sup)}{droite}"
    return str(ensemble)


def _composantes(domaine) -> list:
    """Intervalles connexes du domaine, dans l'ordre.

    Une union (``1/x`` → ``(-oo, 0) ∪ (0, oo)``) a des bornes internes qui
    n'apparaissent ni dans son ``inf`` ni dans son ``sup`` : ce sont pourtant
    celles qui portent les limites intéressantes. Les traiter composante par
    composante est le seul moyen de ne pas les manquer.
    """
    if isinstance(domaine, sympy.Union):
        return sorted(domaine.args, key=lambda i: sympy.sympify(i.inf))
    return [domaine]


def _limites(expr, var, domaine) -> tuple[tuple[str, str], ...]:
    """Limites aux bornes de chaque composante, avec la direction qui convient."""
    trouvees: list[tuple[str, str]] = []
    for composante in _composantes(domaine):
        for borne, direction in ((composante.inf, "+"), (composante.sup, "-")):
            try:
                valeur = sympy.limit(expr, var, borne, direction)
            except Exception:      # noqa: BLE001 — SymPy lève des types variés
                continue
            etiquette = _borne_lisible(borne)
            if borne.is_finite:
                etiquette += direction
            trouvees.append((etiquette, _borne_lisible(valeur)))
    return tuple(trouvees)


def _variations(derivee, var, domaine) -> tuple[tuple[str, str], ...]:
    """Sens de variation, déduit du **signe de la dérivée** sur le domaine."""
    trouvees: list[tuple[str, str]] = []
    for sens, relation in (("croissante", derivee > 0), ("décroissante", derivee < 0)):
        try:
            ensemble = sympy.solveset(relation, var, domaine)
        except Exception:          # noqa: BLE001
            continue
        if ensemble is sympy.EmptySet or ensemble == sympy.EmptySet:
            continue
        for composante in _composantes(ensemble):
            trouvees.append((format_ensemble(composante), sens))
    return tuple(trouvees)


def etudier(expression: str) -> EtudeFonction:
    """Étudie une expression déjà isolée. Lève ``CalculationError`` si impossible.

    Chaque étape est protégée séparément : SymPy peut très bien dériver une
    fonction dont il ne sait pas résoudre l'inéquation de signe. Dans ce cas
    l'étude est rendue partielle plutôt qu'abandonnée — le domaine et la dérivée
    valent déjà mieux que la relance socratique reçue par le testeur.
    """
    expr = analyser_expression(expression)
    var = sympy.Symbol(VARIABLE)
    if var not in expr.free_symbols:
        raise CalculationError(f"Pas une fonction de {VARIABLE} : {expression!r}")

    try:
        domaine = continuous_domain(expr, var, sympy.S.Reals)
    except Exception:              # noqa: BLE001
        domaine = None
    try:
        derivee = sympy.simplify(sympy.diff(expr, var))
    except Exception:              # noqa: BLE001
        derivee = None

    return EtudeFonction(
        expression=str(expr),
        domaine="" if domaine is None else format_ensemble(domaine),
        derivee="" if derivee is None else str(derivee),
        limites=() if domaine is None else _limites(expr, var, domaine),
        variations=(
            () if (domaine is None or derivee is None)
            else _variations(derivee, var, domaine)
        ),
    )


def etudier_la_demande(query: str) -> EtudeFonction | None:
    """Étude de la fonction nommée dans la question, ou ``None``.

    ``None`` couvre les deux façons honnêtes d'échouer : la question ne demande
    pas d'étude, ou aucune expression exploitable n'a pu en être extraite. Dans
    les deux cas l'agent poursuit son pipeline normal ; rien n'est inventé.
    """
    portion = expression_demandee(query)
    if not portion:
        return None
    try:
        etude = etudier(extraire_expression(portion))
    except CalculationError:
        return None
    return etude if etude.est_exploitable else None
