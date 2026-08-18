"""Modèles du domaine — structures partagées par toutes les couches.

Aucune dépendance à un framework web ni à une base : ce sont les objets que
l'ingestion, le vectorstore, l'agent et (plus tard) l'API échangent. Pydantic
sert uniquement de validation/sérialisation, pas de couche applicative.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agent_tuteur.config.taxonomy import (
    CHAMPS_NORMALISES,
    EXAMEN_PAR_NIVEAU,
    Niveau,
    TypeChunk,
    est_chunk_de_cours,
    serie_aliases,
    taxonomy_key,
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
    #: Nature du **document source** (« cours », « td », « annales »…), déduite
    #: de son dossier et de son nom à l'ingestion. À ne pas confondre avec
    #: ``type_chunk``, qui décrit un *morceau* de ce document. Les deux
    #: ensemble décident si un chunk relève du cours (cf. ``est_chunk_de_cours``).
    type_document: str | None = None

    # Clés de filtrage normalisées (accents/casse/article neutralisés), dérivées
    # des libellés ci-dessus. Elles sont indexées et interrogées à leur place ;
    # les libellés, eux, restent la forme affichée à l'élève. Pendant du
    # mécanisme ``serie_alias`` pour les champs sans classe d'équivalence connue.
    niveau_key: str | None = None
    classe_key: str | None = None
    discipline_key: str | None = None
    chapitre_key: str | None = None

    @model_validator(mode="after")
    def _enrichir(self) -> CurriculumMetadata:
        # Aligne serie_alias[] sur les classes d'équivalence si non fourni.
        if self.serie and not self.serie_alias:
            self.serie_alias = serie_aliases(self.serie)
        # Dérive les clés de filtrage — toujours recalculées depuis le libellé,
        # pour qu'une valeur persistée obsolète ne puisse pas prendre le dessus.
        for champ in CHAMPS_NORMALISES:
            libelle = getattr(self, champ, None)
            setattr(self, f"{champ}_key", taxonomy_key(libelle) if libelle else None)
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

    @property
    def est_cours(self) -> bool:
        """Ce chunk relève-t-il du cours (par opposition à un complément) ?"""
        return est_chunk_de_cours(self.metadata.type_chunk, self.metadata.type_document)


class ScoredChunk(BaseModel):
    """Chunk remonté par le retriever, avec les scores de fusion hybride."""

    chunk: Chunk
    score: float
    dense_score: float | None = None
    sparse_score: float | None = None

    @property
    def source_label(self) -> str:
        """Libellé court d'attribution pour l'affichage des sources RAG.

        Destiné au **client** (onglet sources, trace persistée), où le nom de
        fichier est une information de provenance utile. Ne jamais l'envoyer au
        modèle : voir :attr:`libelle_interne`.
        """
        m = self.chunk.metadata
        parts = [p for p in (m.source_document, m.chapitre or m.competence) if p]
        return " — ".join(parts) if parts else self.chunk.id

    @property
    def libelle_interne(self) -> str:
        """Attribution destinée au **prompt** : le chapitre, jamais le fichier.

        Le nom de fichier du corpus encode la série (« Lecon_01_Nombres_
        Complexes_TS2S4.md »). Envoyé au modèle dans le bloc de documentation,
        il y était lu comme un fait sur l'élève, qui se voyait répondre « tu as
        déjà étudié les complexes en S2/S4 » sans avoir jamais donné sa série
        (cas QA #16, règle non-négociable n°3). L'hallucination était en réalité
        **fournie par nous** : rien dans ce bloc ne distingue une métadonnée de
        document d'un fait sur l'élève.

        Le modèle n'a besoin que de savoir de quel chapitre vient l'extrait, ce
        qui suffit à l'ancrer. L'attribution complète reste servie au client par
        :attr:`source_label`, qui n'est pas dégradée.
        """
        m = self.chunk.metadata
        return m.chapitre or m.competence or "cours"
