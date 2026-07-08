"""Modèles du domaine — structures partagées par toutes les couches.

Aucune dépendance à un framework web ni à une base : ce sont les objets que
l'ingestion, le vectorstore, l'agent et (plus tard) l'API échangent. Pydantic
sert uniquement de validation/sérialisation, pas de couche applicative.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_tuteur.config.taxonomy import (
    EXAMEN_PAR_NIVEAU,
    Niveau,
    TypeChunk,
    serie_aliases,
)


class CurriculumMetadata(BaseModel):
    """Métadonnées curriculaires attachées à chaque chunk (fait foi partout)."""

    model_config = ConfigDict(use_enum_values=True)

    niveau: str
    classe: str | None = None
    serie: str | None = None
    serie_alias: list[str] = Field(default_factory=list)
    discipline: str | None = None
    chapitre: str | None = None
    competence: str | None = None
    examen_associe: str | None = None
    type_chunk: str = TypeChunk.CHAPITRE.value
    source_document: str | None = None

    @model_validator(mode="after")
    def _enrichir(self) -> "CurriculumMetadata":
        # Aligne serie_alias[] sur les classes d'équivalence si non fourni.
        if self.serie and not self.serie_alias:
            self.serie_alias = serie_aliases(self.serie)
        # Examen déduit du niveau si absent (indicatif).
        if not self.examen_associe:
            try:
                examen = EXAMEN_PAR_NIVEAU.get(Niveau(self.niveau))
                if examen is not None:
                    self.examen_associe = examen.value
            except ValueError:
                pass
        return self


class Chunk(BaseModel):
    """Unité indexable : un texte pédagogiquement cohérent + ses métadonnées."""

    id: str
    text: str
    metadata: CurriculumMetadata


class ScoredChunk(BaseModel):
    """Chunk remonté par le retriever, avec les scores de fusion hybride."""

    chunk: Chunk
    score: float
    dense_score: float | None = None
    sparse_score: float | None = None

    @property
    def source_label(self) -> str:
        """Libellé court d'attribution pour l'affichage des sources RAG."""
        m = self.chunk.metadata
        parts = [p for p in (m.source_document, m.chapitre or m.competence) if p]
        return " — ".join(parts) if parts else self.chunk.id
