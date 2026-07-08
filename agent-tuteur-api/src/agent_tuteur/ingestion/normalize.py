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
    return text.strip() + "\n"
