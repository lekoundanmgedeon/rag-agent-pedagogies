"""Taxonomie curriculaire sénégalaise — source de vérité du filtrage RAG.

Hiérarchie : ``niveau → classe → série (secondaire) → discipline → chapitre →
compétence``. Le point délicat est la **double nomenclature des séries** (réforme
en cours) : une requête élève peut employer l'ancien ou le nouveau libellé. On
stocke donc, pour chaque chunk, *tous* les alias équivalents (``serie_alias[]``)
et on normalise toute série entrante vers une forme canonique.
"""

from __future__ import annotations

import unicodedata
from enum import Enum

# --- Niveaux du système éducatif ---------------------------------------------


class Niveau(str, Enum):
    PRESCOLAIRE = "préscolaire"
    ELEMENTAIRE = "élémentaire"
    MOYEN = "moyen"
    SECONDAIRE = "secondaire"
    EBJA = "EBJA"  # Éducation de Base des Jeunes et Adultes


class Examen(str, Enum):
    CFEE = "CFEE"          # fin d'élémentaire
    BFEM = "BFEM"          # fin de moyen
    BACCALAUREAT = "Baccalauréat"  # fin de secondaire


# Examen associé « par défaut » à un niveau (indicatif, surchargé par le chunk).
EXAMEN_PAR_NIVEAU: dict[Niveau, Examen] = {
    Niveau.ELEMENTAIRE: Examen.CFEE,
    Niveau.MOYEN: Examen.BFEM,
    Niveau.SECONDAIRE: Examen.BACCALAUREAT,
}


# --- Types de chunk (granularité pédagogique du RAG) -------------------------


class TypeChunk(str, Enum):
    COMPETENCE_COMPLETE = "competence_complete"
    CHAPITRE = "chapitre"
    SOUS_NOTION = "sous_notion"
    EXERCICE = "exercice"


# --- Séries du secondaire : classes d'équivalence ancienne/nouvelle nomenclature
# Chaque groupe = un même parcours désigné par des libellés interchangeables.
# Le premier élément est la forme *canonique* retenue en interne.
SERIE_EQUIVALENCES: list[list[str]] = [
    # Scientifiques
    ["S1"], ["S2"], ["S3"], ["S4"], ["S5"], ["F6"],
    # Littéraires
    ["L1a"], ["L1b"], ["L'1"], ["L2"], ["LA"],
    # Techniques / gestion — ancienne ↔ nouvelle nomenclature
    ["T1", "STIDD1"],
    ["T2", "STIDD2"],
    ["G", "STEG"],
]

# Champs matérialisés comme index Qdrant (payload filtering).
CHAMPS_INDEXES: tuple[str, ...] = (
    "niveau",
    "classe",
    "serie",
    "discipline",
    "chapitre",
    "type_chunk",
)


def _key(label: str) -> str:
    """Clé de comparaison robuste : sans accents, majuscules, sans espaces.

    L'apostrophe (``L'1``) est conservée car distinctive ; seuls les blancs et la
    casse sont neutralisés. Permet de matcher « stidd1 », « STIDD 1 », « T1 »…
    """
    norm = unicodedata.normalize("NFKD", label)
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    return norm.replace(" ", "").upper()


# Index inversé libellé-normalisé -> groupe d'équivalence.
_SERIE_LOOKUP: dict[str, list[str]] = {
    _key(alias): group for group in SERIE_EQUIVALENCES for alias in group
}


def is_serie_connue(serie: str) -> bool:
    return _key(serie) in _SERIE_LOOKUP


def canonical_serie(serie: str) -> str | None:
    """Forme canonique d'une série (ex. ``STIDD1`` -> ``T1``), ou ``None``."""
    group = _SERIE_LOOKUP.get(_key(serie))
    return group[0] if group else None


def serie_aliases(serie: str) -> list[str]:
    """Tous les libellés équivalents d'une série, canonique en tête.

    Sert à peupler ``serie_alias[]`` sur un chunk et à élargir un filtre : une
    question mentionnant « STIDD1 » doit remonter des chunks annotés « T1 ».
    """
    group = _SERIE_LOOKUP.get(_key(serie))
    if group is not None:
        return list(group)
    # Série inconnue : on la conserve telle quelle (corpus expérimental).
    return [serie]
