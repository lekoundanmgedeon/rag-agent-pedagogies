"""Normaliseur « format pivot » : Markdown + LaTeX inline ($...$, $$...$$).

Point de cohérence critique : *toute* extraction (PDF, DOCX, TXT, MD) et la
future sortie OCR passent par cette fonction, afin que contenu curriculaire et
questions élève vivent dans le même espace typographique. Les transformations
sont **conservatrices** (aucune réécriture sémantique) et déterministes.
"""

from __future__ import annotations

import re

_TRAILING_WS = re.compile(r"[ \t]+$", re.MULTILINE)
_MULTI_BLANK = re.compile(r"\n{3,}")
# Coupure de mot en fin de ligne (fréquent en extraction PDF) : « déri-\nvée ».
_HYPHEN_WRAP = re.compile(r"(\w)-\n(\w)")
# Titre Markdown sans espace après les dièses : « ##Titre » -> « ## Titre ».
_HEADING_NO_SPACE = re.compile(r"^(#{1,6})([^#\s])", re.MULTILINE)

# Délimiteurs LaTeX de la forme \( … \) et \[ … \], ramenés au format pivot
# ($ … $ et $$ … $$) annoncé en tête de module. Les 12 leçons du corpus les
# emploient massivement (120 occurrences dans la seule leçon 01) : ces extraits
# partent tels quels dans le prompt, et le modèle recopie spontanément le
# vocabulaire typographique qu'on lui montre — c'est le rendu « à revoir » des
# cas QA #37 et #47, mesuré sur la stack réelle. La transformation ne touche
# QUE les délimiteurs, jamais le contenu mathématique entre eux.
_LATEX_INLINE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
_LATEX_BLOC = re.compile(r"\\\[(.+?)\\\]", re.DOTALL)


def delimiteurs_latex(text: str) -> str:
    """Ramène ``\\( … \\)`` et ``\\[ … \\]`` aux délimiteurs du format pivot.

    Appliquée à deux endroits, pour deux raisons distinctes : à l'ingestion,
    parce que le format pivot est le contrat du corpus ; à l'assemblage du
    prompt, parce qu'un index déjà construit garde ses délimiteurs d'origine et
    qu'une réindexation est une opération sur données, pas un correctif de code.
    """
    text = _LATEX_BLOC.sub(lambda m: f"$${m.group(1)}$$", text)
    return _LATEX_INLINE.sub(lambda m: f"${m.group(1)}$", text)


def to_pivot(text: str) -> str:
    """Normalise un texte brut vers le format pivot Markdown + LaTeX."""
    # 1. Uniformise les fins de ligne.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 2. Recolle les mots coupés en fin de ligne (artefact PDF).
    text = _HYPHEN_WRAP.sub(r"\1\2", text)
    # 3. Espace manquant après les dièses de titre.
    text = _HEADING_NO_SPACE.sub(r"\1 \2", text)
    # 4. Supprime les espaces de fin de ligne.
    text = _TRAILING_WS.sub("", text)
    # 5. Réduit les lignes vides multiples à une seule séparation de paragraphe.
    text = _MULTI_BLANK.sub("\n\n", text)
    # 6. Ramène les délimiteurs LaTeX au format pivot annoncé ($ … $).
    text = delimiteurs_latex(text)
    return text.strip() + "\n"
