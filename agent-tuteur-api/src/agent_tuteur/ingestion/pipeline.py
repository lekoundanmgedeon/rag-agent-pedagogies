"""Pipeline d'ingestion — cœur synchrone, réutilisable.

Enchaîne : ``extract → normalize (pivot) → chunk (structurel) → annotate``.
Renvoie des ``Chunk`` prêts à indexer. Le worker ARQ (étape 6) se contentera
d'envelopper ``process_document`` puis d'appeler l'``Indexer`` — aucune logique
métier ne vit dans le worker.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_tuteur.domain.models import Chunk
from agent_tuteur.ingestion.annotation import annotate, parse_frontmatter
from agent_tuteur.ingestion.chunking import chunk_document
from agent_tuteur.ingestion.loaders import extract_text
from agent_tuteur.ingestion.normalize import to_pivot
from agent_tuteur.vectorstore.indexer import Indexer


@dataclass
class IngestionResult:
    source_document: str
    doc_type: str
    chunks: list[Chunk]

    @property
    def n_chunks(self) -> int:
        return len(self.chunks)


def process_document(
    filename: str,
    data: bytes,
    form_metadata: dict | None = None,
) -> IngestionResult:
    """Transforme un fichier en chunks annotés (sans indexation).

    Le frontmatter éventuel du document est fusionné avec les métadonnées du
    formulaire d'upload (le formulaire est prioritaire pour les champs fournis).
    """
    raw, doc_type = extract_text(filename, data)
    pivot = to_pivot(raw)
    meta, body = parse_frontmatter(pivot)

    merged = dict(meta)
    merged.update({k: v for k, v in (form_metadata or {}).items() if v not in (None, "")})

    drafts = chunk_document(body)
    chunks = annotate(drafts, merged, source_document=filename)
    return IngestionResult(source_document=filename, doc_type=doc_type, chunks=chunks)


def ingest_and_index(
    filename: str,
    data: bytes,
    indexer: Indexer,
    form_metadata: dict | None = None,
) -> IngestionResult:
    """Ingestion complète + indexation (chemin direct, hors worker)."""
    result = process_document(filename, data, form_metadata)
    indexer.index_chunks(result.chunks)
    return result
