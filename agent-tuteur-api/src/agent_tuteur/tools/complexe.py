"""Analyse vérifiée d'un nombre complexe — cas QA #6.

L'exercice du testeur (« z = 3 + 4i : donne la partie réelle, la partie
imaginaire, le conjugué, le module ») est le plus basique du chapitre le mieux
couvert du corpus. L'agent y répondait en affirmant ne pas avoir accès au
chapitre — « très préoccupant pour la fiabilité perçue », dit le rapport.

Deux causes distinctes, et une seule relève de ce module :

* l'index Qdrant de la démo était périmé et incomplet au moment du test (149
  chunks sur 176 sans métadonnée chapitre) — c'est un problème de données, tracé
  dans ``qa_status.json``, et le rejeu sur corpus figé montre que la
  récupération ramène aujourd'hui les bons extraits ;
* ``i`` n'était pas l'unité imaginaire. ``analyser_expression("3+4i")`` rend
  ``4*i + 3`` où ``i`` est un **symbole libre**, si bien que ``compute`` échouait
  et que ``calcul_non_verifie`` s'armait : le prompt interdisait alors d'annoncer
  le moindre résultat chiffré. L'agent avait les extraits sous les yeux et
  l'interdiction de s'en servir.

Le mapping ``i → I`` est délibérément **local à ce module** plutôt qu'ajouté au
dictionnaire de noms global : ``i`` est un indice de sommation parfaitement
ordinaire ailleurs en mathématiques, et le promouvoir partout ferait taire des
calculs corrects sur des expressions qui n'ont rien de complexe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy

from sympy.parsing.sympy_parser import parse_expr

from agent_tuteur.tools.calculator import (
    _ALLOWED_NAMES,
    _TRANSFORMS,
    CalculationError,
    normaliser_expression,
)

#: Contexte qui autorise à lire ``i`` comme l'unité imaginaire. Sans un de ces
#: marqueurs, on ne touche à rien : voir la note du module sur les indices.
_CONTEXTE_COMPLEXE = re.compile(
    r"\bnombres?\s+complexes?\b|\bcomplexe\b|\bimaginaire\b|\bi\s*\^?2\s*=\s*-\s*1\b"
    r"|\bconjugu[ée]\b|\baffixe\b|\bforme\s+(?:alg[ée]brique|trigonom[ée]trique|exponentielle)\b",
    re.IGNORECASE,
)

#: Définition d'un complexe dans l'énoncé : « z = 3 + 4i », « Z = -1+i√3 ».
#:
#: Le corps ne capture **que** des caractères mathématiques, et s'arrête donc de
#: lui-même à la prose qui suit. C'est nécessaire : l'énoncé du cas #6 enchaîne
#: « z = 3 + 4i où i est le nombre imaginaire tel que i^2 = -1 » sans virgule, et
#: une capture jusqu'au séparateur de phrase avalait toute l'explication.
#:
#: ``e`` est délibérément exclu de la classe, bien qu'il soit mathématiquement
#: légitime : sans cela « z = 5 et le module » capturerait « 5 e » et
#: fabriquerait un produit par le nombre d'Euler à partir d'une conjonction.
_DEFINITION = re.compile(
    r"\b(?P<nom>[zZwu])\s*=\s*(?P<corps>[0-9ijI+\-*/^().√π][0-9ijI\s+\-*/^().√π]*)",
)


@dataclass(frozen=True)
class ComplexeAnalyse:
    """Éléments d'un complexe, tous établis par SymPy."""

    #: Nom donné par l'énoncé (« z »), pour que la réponse parle la même langue.
    nom: str
    #: Forme algébrique normalisée (« 3 + 4*I »).
    forme: str
    partie_reelle: str
    partie_imaginaire: str
    conjugue: str
    module: str
    #: Argument en radians, ou "" si SymPy n'a pas su le réduire.
    argument: str = ""


def _analyser(corps: str):
    """Analyse le corps d'une définition en lisant ``i`` comme l'unité imaginaire.

    ``parse_expr`` et non ``sympify`` : « 3 + 4i » est une multiplication
    implicite, que seul le jeu de transformations du calculateur sait lire. Le
    dictionnaire local n'y ajoute que la promotion de ``i`` en unité imaginaire.
    """
    texte = normaliser_expression(corps)
    try:
        return parse_expr(
            texte,
            local_dict={**_ALLOWED_NAMES, "i": sympy.I, "j": sympy.I, "I": sympy.I},
            transformations=_TRANSFORMS,
            evaluate=True,
        )
    except Exception as exc:      # noqa: BLE001 — SymPy lève des types variés
        raise CalculationError(f"Complexe non analysable : {corps!r}") from exc


def analyser_complexe(corps: str, nom: str = "z") -> ComplexeAnalyse:
    """Analyse une expression complexe déjà isolée. Lève ``CalculationError``.

    L'argument est le seul champ facultatif : il n'existe pas pour ``z = 0`` et
    SymPy ne le réduit pas toujours à une forme présentable. Un champ vide vaut
    mieux qu'une valeur approximative — le prompt n'en dira alors rien.
    """
    expr = sympy.expand(_analyser(corps))
    reelle, imaginaire = sympy.re(expr), sympy.im(expr)
    if reelle.free_symbols or imaginaire.free_symbols:
        raise CalculationError(f"Complexe non numérique : {corps!r}")

    argument = ""
    if expr != 0:
        try:
            argument = str(sympy.simplify(sympy.arg(expr)))
        except Exception:          # noqa: BLE001
            argument = ""

    return ComplexeAnalyse(
        nom=nom,
        forme=str(expr),
        partie_reelle=str(reelle),
        partie_imaginaire=str(imaginaire),
        conjugue=str(sympy.conjugate(expr)),
        module=str(sympy.simplify(sympy.Abs(expr))),
        argument=argument,
    )


def analyser_la_demande(query: str) -> ComplexeAnalyse | None:
    """Analyse le complexe défini dans l'énoncé, ou ``None``.

    ``None`` couvre toutes les façons honnêtes d'échouer — pas de contexte
    complexe, pas de définition, corps non exploitable. Le pipeline normal
    reprend alors la main et rien n'est affirmé.
    """
    if not _CONTEXTE_COMPLEXE.search(query):
        return None
    for correspondance in _DEFINITION.finditer(query):
        corps = correspondance.group("corps").strip()
        if not corps:
            continue
        try:
            return analyser_complexe(corps, correspondance.group("nom"))
        except CalculationError:
            continue
    return None
