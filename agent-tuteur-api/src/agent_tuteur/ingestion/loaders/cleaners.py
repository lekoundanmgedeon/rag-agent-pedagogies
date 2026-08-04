"""Nettoyage du texte extrait d'un PDF, avant normalisation pivot.

Porté de ``backend/app/rag/document_parser/cleaners.py`` (NURU). Trois
traitements, appliqués dans cet ordre par :func:`clean_text` :

1. retirer les en-têtes/pieds de page qui polluent chaque page d'un fascicule ;
2. resserrer les sauts de ligne laissés par l'extraction page à page ;
3. uniformiser les délimiteurs LaTeX (notation mathématique).

Le portage transforme la classe à méthodes statiques de NURU en fonctions de
module — c'est la forme utilisée partout ailleurs dans ``ingestion/`` — et sort
les motifs en constante pour qu'ils soient lisibles et ajustables sans toucher
au code.
"""

from __future__ import annotations

import re

#: Lignes considérées comme en-tête/pied de page et supprimées.
#:
#: Ces motifs sont **volontairement agressifs** : sur le corpus réel, les
#: fascicules répètent le nom de l'établissement et du professeur à chaque page,
#: ce qui pollue les chunks et fausse la recherche. Le risque assumé est qu'une
#: ligne de contenu commençant par « Professeur… » soit supprimée ; c'est
#: acceptable pour des documents de mathématiques.
HEADER_FOOTER_PATTERNS: tuple[str, ...] = (
    r"^\s*Page \d+\s*$",
    r"^\s*T\.?S\.?\s*\d+\s*$",
    r"^\s*Classe de Tle S\s*$",
    r"^\s*Année scolaire \d+-\d+\s*$",
    r"^\s*Groupe scolaire.*$",
    r"^\s*Lycée.*$",
    r"^\s*Collège.*$",
    r"^\s*Professeur.*$",
    r"^\s*Profs?.*$",
)

_HEADER_FOOTER = tuple(re.compile(p, re.IGNORECASE) for p in HEADER_FOOTER_PATTERNS)
_BLANK_RUN = re.compile(r"\n{4,}")
_TRAILING_SPACE = re.compile(r"[ \t]+\n")
_DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_INLINE_MATH = re.compile(r"\s*\$([^\$]+?)\$\s*")


def remove_headers_footers(text: str) -> str:
    """Supprime les lignes d'en-tête et de pied de page répétées.

    Les lignes vides sont conservées : elles portent la structure du document,
    dont dépend le découpage en chunks effectué plus loin.
    """
    kept: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            kept.append(line)
            continue
        if any(pattern.match(stripped) for pattern in _HEADER_FOOTER):
            continue
        kept.append(line)
    return "\n".join(kept)


def clean_newlines(text: str) -> str:
    """Ramène les blocs de lignes vides à un seul saut de paragraphe."""
    text = _BLANK_RUN.sub("\n\n", text)
    return _TRAILING_SPACE.sub("\n", text)


def fix_latex(text: str) -> str:
    """Uniformise les délimiteurs mathématiques.

    ``$$…$$`` devient ``\\[…\\]`` (formule centrée) et les formules en ligne
    ``$…$`` sont isolées par un espace. Objectif : que le rendu KaTeX du
    frontend reçoive toujours la même notation, quelle que soit la source.
    """
    text = _DISPLAY_MATH.sub(r"\\[\1\\]", text)
    return _INLINE_MATH.sub(r" $\1$ ", text)


def clean_text(text: str) -> str:
    """Chaîne de nettoyage complète appliquée au texte brut d'un PDF."""
    text = remove_headers_footers(text)
    text = clean_newlines(text)
    return fix_latex(text).strip()
