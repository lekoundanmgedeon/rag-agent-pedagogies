"""Métadonnées déduites du nom de fichier et du chemin.

Porté de ``backend/app/rag/metadata_extractor/file_metadata.py`` (NURU), en
fonctions plutôt qu'en classe : il n'y a pas d'état à conserver entre deux
appels, seulement des motifs figés (:mod:`~.patterns`).

**Ordre de priorité.** Le chemin est lu en premier (indice faible : le dossier
parent), puis le nom de fichier (indice fort : plus précis). Le second écrase
donc le premier quand les deux se prononcent.
"""

from __future__ import annotations

from pathlib import Path

from agent_tuteur.ingestion.loaders.metadata import patterns


def _depuis_le_chemin(chemin: Path) -> dict[str, str]:
    """Indices tirés des dossiers parents (``data/raw/cours/…``)."""
    trouve: dict[str, str] = {}
    for segment in chemin.parts:
        minuscule = segment.lower()
        if minuscule in patterns.TYPES_PAR_DOSSIER:
            trouve["type_document"] = minuscule
        elif minuscule in patterns.DISCIPLINES_PAR_DOSSIER:
            trouve["discipline"] = minuscule
        elif minuscule in patterns.CLASSES_CANONIQUES:
            trouve["classe"] = segment.capitalize()
        elif minuscule not in patterns.SEGMENTS_STRUCTURELS:
            # Sous-dossier « métier » possible, ex. « Chap1_Probabilite ».
            notion = patterns.detecter_notion(segment)
            if notion and "chapitre" not in trouve:
                trouve["chapitre"] = notion
    return trouve


def _depuis_le_nom(nom: str) -> dict[str, str]:
    """Indices tirés du nom de fichier, sans son extension."""
    trouve: dict[str, str] = {}

    if (serie := patterns.SERIE.search(nom)) is not None:
        trouve["serie"] = serie.group(1)

    if (chapitre := patterns.CHAPITRE_FICHIER.search(nom)) is not None:
        numero = chapitre.group(1)
        titre = (chapitre.group(2) or "").strip()
        trouve["chapitre_numero"] = numero
        trouve["chapitre"] = titre if titre else f"Chapitre {numero}"
    else:
        # Pas de « Chapitre N » explicite : on tente de reconnaître la notion
        # directement (« TD1-Probabilite-TS1.pdf » -> « Probabilités »).
        if (notion := patterns.detecter_notion(nom)) is not None:
            trouve["chapitre"] = notion

    if (type_doc := patterns.TYPE_DOCUMENT.search(nom)) is not None:
        trouve["type_document"] = type_doc.group(1).lower()

    if (annee := patterns.ANNEE.search(nom)) is not None:
        trouve["annee"] = annee.group(0)

    if (auteur := patterns.AUTEUR_FICHIER.search(nom)) is not None:
        trouve["auteur"] = auteur.group(1)

    if (etab := patterns.ETABLISSEMENT.search(nom)) is not None:
        trouve["etablissement"] = etab.group(2).strip()

    return trouve


def extraire(chemin: Path) -> dict[str, str]:
    """Métadonnées brutes déduites de l'emplacement et du nom du fichier.

    Les valeurs ne sont **pas** encore alignées sur la taxonomie du projet :
    c'est le rôle de :mod:`~.merge`. Ici on se contente de reconnaître ce qui
    est écrit.
    """
    trouve = _depuis_le_chemin(chemin)
    trouve.update(_depuis_le_nom(chemin.stem))
    trouve["source_document"] = chemin.name
    return trouve
