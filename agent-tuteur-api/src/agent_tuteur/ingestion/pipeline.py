"""Pipeline d'ingestion — cœur synchrone, réutilisable.

Enchaîne : ``extract → normalize (pivot) → chunk (structurel) → annotate``.
Renvoie des ``Chunk`` prêts à indexer. Le worker ARQ et le repli
``BackgroundTasks`` (étape 6) se contentent d'envelopper ``process_document``
puis d'appeler l'``Indexer`` — aucune logique métier ne vit dans le worker.

**Observabilité.** Chaque étape est chronométrée et loggée (JSON structuré),
et accumulée dans ``IngestionResult.steps`` — c'est ce que
``api/routes/documents.py``/``workers/ingestion_worker.py`` persistent dans
``documents.log`` pour l'afficher dans la page Upload/Logs du frontend.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from agent_tuteur.domain.models import Chunk
from agent_tuteur.ingestion.annotation import annotate, parse_frontmatter
from agent_tuteur.ingestion.chunking import chunk_document
from agent_tuteur.ingestion.loaders import extract_text
from agent_tuteur.ingestion.loaders.metadata import extraire_metadonnees
from agent_tuteur.ingestion.normalize import to_pivot
from agent_tuteur.observability import get_logger, log_event
from agent_tuteur.vectorstore.indexer import Indexer

_logger = get_logger("agent_tuteur.ingestion.pipeline")


@dataclass
class IngestionResult:
    source_document: str
    doc_type: str
    chunks: list[Chunk]
    #: Étapes chronométrées (extract/normalize/chunk/annotate), pour affichage
    #: et persistance (``documents.log``).
    steps: list[dict] = field(default_factory=list)

    @property
    def n_chunks(self) -> int:
        return len(self.chunks)


def process_document(
    filename: str,
    data: bytes,
    form_metadata: dict | None = None,
    *,
    document_id: str | None = None,
    source_path: str | Path | None = None,
) -> IngestionResult:
    """Transforme un fichier en chunks annotés (sans indexation).

    Trois sources de métadonnées, de la plus faible à la plus forte :

    1. ce que l'on **devine** du nom de fichier, du dossier et de l'en-tête
       (``ingestion/loaders/metadata``) — c'est une déduction, elle cède
       devant tout le reste ;
    2. le **frontmatter** YAML en tête du document, quand il y en a un ;
    3. les métadonnées **saisies** au téléversement, qui font toujours foi.

    ``source_path`` sert à l'ingestion par lot depuis le disque : le dossier
    parent (``data/raw/cours/…``) est un indice fort sur la nature du document,
    que le seul nom de fichier ne donne pas. Hors de ce cas, ``filename``
    suffit.

    ``document_id`` est facultatif (absent hors contexte d'upload, ex. démo) et
    sert uniquement à corréler les logs de cette ingestion.
    """
    steps: list[dict] = []

    def _record(step: str, t0: float, **detail) -> None:
        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        steps.append({"step": step, "duration_ms": duration_ms, **detail})
        log_event(_logger, f"ingestion:{step}", document_id=document_id, filename=filename,
                  duration_ms=duration_ms, **detail)

    t0 = time.perf_counter()
    raw, doc_type = extract_text(filename, data)
    _record("extract", t0, doc_type=doc_type, raw_chars=len(raw))

    t0 = time.perf_counter()
    pivot = to_pivot(raw)
    _record("normalize", t0, pivot_chars=len(pivot))

    meta, body = parse_frontmatter(pivot)

    t0 = time.perf_counter()
    explicite = dict(meta)
    explicite.update({k: v for k, v in (form_metadata or {}).items() if v not in (None, "")})
    merged = extraire_metadonnees(
        Path(source_path or filename), body, saisies=explicite
    )
    _record("metadata", t0, type_document=merged.get("type_document"),
            chapitre=merged.get("chapitre"), serie=merged.get("serie"))

    t0 = time.perf_counter()
    drafts = chunk_document(body)
    _record("chunk", t0, n_drafts=len(drafts))

    t0 = time.perf_counter()
    chunks = annotate(drafts, merged, source_document=filename)
    _record("annotate", t0, n_chunks=len(chunks))

    return IngestionResult(source_document=filename, doc_type=doc_type, chunks=chunks, steps=steps)


def ingest_and_index(
    filename: str,
    data: bytes,
    indexer: Indexer,
    form_metadata: dict | None = None,
    *,
    document_id: str | None = None,
    source_path: str | Path | None = None,
) -> IngestionResult:
    """Ingestion complète + indexation (chemin direct, hors worker)."""
    result = process_document(
        filename, data, form_metadata, document_id=document_id, source_path=source_path
    )
    t0 = time.perf_counter()
    indexer.index_chunks(result.chunks)
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    result.steps.append({"step": "embed_upsert", "duration_ms": duration_ms, "n_chunks": result.n_chunks})
    log_event(
        _logger, "ingestion:embed_upsert", document_id=document_id, filename=filename,
        duration_ms=duration_ms, n_chunks=result.n_chunks,
    )
    return result
