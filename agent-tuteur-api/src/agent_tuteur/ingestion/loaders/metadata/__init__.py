"""Reconnaissance des métadonnées curriculaires d'un document du corpus.

Sur les 103 PDF du programme sénégalais, presque rien n'est renseigné
explicitement : la classe, la série et le chapitre sont dans le nom du fichier
(« TD1-Probabilite-TS1.pdf »), dans le dossier (« data/raw/cours/ ») ou dans
l'en-tête de la première page. Ce package en fait des métadonnées exploitables
par le filtrage curriculaire.

Point d'entrée unique : :func:`extraire_metadonnees`.
"""

from __future__ import annotations

from agent_tuteur.ingestion.loaders.metadata.merge import extraire_metadonnees

__all__ = ["extraire_metadonnees"]
