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

from agent_tuteur.domain.models import Chunk
from agent_tuteur.ingestion.annotation import annotate, parse_frontmatter
from agent_tuteur.ingestion.chunking import chunk_document
from agent_tuteur.ingestion.loaders import extract_text
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
) -> IngestionResult:
    """Transforme un fichier en chunks annotés (sans indexation).

    Le frontmatter éventuel du document est fusionné avec les métadonnées du
    formulaire d'upload (le formulaire est prioritaire pour les champs fournis).
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
    merged = dict(meta)
    merged.update({k: v for k, v in (form_metadata or {}).items() if v not in (None, "")})

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
) -> IngestionResult:
    """Ingestion complète + indexation (chemin direct, hors worker)."""
    result = process_document(filename, data, form_metadata, document_id=document_id)
    t0 = time.perf_counter()
    indexer.index_chunks(result.chunks)
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    result.steps.append({"step": "embed_upsert", "duration_ms": duration_ms, "n_chunks": result.n_chunks})
    log_event(
        _logger, "ingestion:embed_upsert", document_id=document_id, filename=filename,
        duration_ms=duration_ms, n_chunks=result.n_chunks,
    )
    return result
