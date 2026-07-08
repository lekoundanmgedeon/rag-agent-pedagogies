"""Upload et gestion des documents curriculaires.

**Exécution de l'ingestion.** Le job (``ingestion.pipeline.process_document`` +
``Indexer``) tourne soit dans le **worker ARQ** (``workers/ingestion_worker.py``,
séparé, consommant Redis) soit, si Redis est indisponible, en ``BackgroundTasks``
FastAPI **dans le même processus** (dégradation gracieuse — cf.
``api/main.py::_try_create_arq_pool``). Le contrat observable côté client est
identique dans les deux cas : ``document_id`` renvoyé immédiatement, statut
``pending``→``indexed``/``failed`` consultable ensuite. Voir le worker pour la
limitation connue du backend vectoriel in-memory en multi-processus.

``/status`` expose un flux SSE par **sondage** de la base (pas encore
d'événements fins par étape extract/normalize/chunk/embed — amélioration future
possible côté worker) : le contrat SSE observable ({status: ...} jusqu'à un état
terminal) reste stable indépendamment de l'exécuteur.

``reindex`` accepte un nouveau fichier plutôt qu'un identifiant sans contenu : le
stack verrouillée ne prévoit pas de stockage d'objets (S3/MinIO) pour conserver
le fichier original, donc une ré-indexation « à partir de la source » nécessite
de la refournir. Décision documentée dans docs/adr.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from agent_tuteur.api.dependencies import document_repo, get_indexer, get_session, get_tenant_id
from agent_tuteur.api.rate_limit import limiter
from agent_tuteur.api.schemas import DocumentOut, DocumentStatusEvent, UploadedDocumentOut
from agent_tuteur.api.streaming import sse_event
from agent_tuteur.config.settings import get_settings
from agent_tuteur.ingestion.loaders import SUPPORTED_EXTENSIONS
from agent_tuteur.ingestion.pipeline import process_document
from agent_tuteur.observability import get_logger, log_event
from agent_tuteur.persistence.db import session_scope
from agent_tuteur.persistence.models import Document
from agent_tuteur.persistence.repositories import DocumentRepository
from agent_tuteur.vectorstore.indexer import Indexer

router = APIRouter(prefix="/api/documents", tags=["documents"])
_logger = get_logger("agent_tuteur.api.routes.documents")


def _extension_ok(filename: str) -> bool:
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)


async def _ingest_in_background(
    document_id: str,
    filename: str,
    data: bytes,
    form_metadata: dict,
    tenant_id: str,
    indexer: Indexer,
    *,
    replace: bool = False,
) -> None:
    """Repli en tâche de fond **du même processus** (Redis/ARQ indisponible).

    Logique identique à ``workers.ingestion_worker.ingest_document_task``,
    dupliquée volontairement car cette version utilise l'``Indexer`` déjà
    construit par l'API (``app.state.indexer``) plutôt que d'en bâtir un nouveau.
    """
    log_event(_logger, "ingestion:job_start", document_id=document_id, filename=filename, tenant_id=tenant_id)
    async with session_scope(tenant_id) as session:
        repo = DocumentRepository(session)
        steps: list[dict] = []
        try:
            result = await asyncio.to_thread(
                process_document, filename, data, form_metadata, document_id=document_id
            )
            steps = result.steps
            t0 = time.perf_counter()
            if replace:
                await asyncio.to_thread(indexer.reindex_source, filename, result.chunks)
            else:
                await asyncio.to_thread(indexer.index_chunks, result.chunks)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            steps.append({"step": "embed_upsert", "duration_ms": duration_ms, "n_chunks": result.n_chunks})
            log_event(_logger, "ingestion:embed_upsert", document_id=document_id, filename=filename,
                      duration_ms=duration_ms, n_chunks=result.n_chunks)
            await repo.update_status(document_id, "indexed", tenant_id=tenant_id, log=steps)
            log_event(_logger, "ingestion:job_done", document_id=document_id, filename=filename, status="indexed")
        except Exception as exc:  # noqa: BLE001 — toute erreur d'ingestion doit aboutir en 'failed', pas planter le worker.
            log_event(_logger, "ingestion:job_failed", document_id=document_id, filename=filename,
                      error=str(exc), log_level=40)
            await repo.update_status(document_id, "failed", error=str(exc), tenant_id=tenant_id, log=steps)


async def _schedule_ingestion(
    request: Request,
    background_tasks: BackgroundTasks,
    *,
    document_id: str,
    filename: str,
    data: bytes,
    form_metadata: dict,
    tenant_id: str,
    replace: bool = False,
) -> None:
    """Programme le job d'ingestion : file ARQ si Redis dispo, sinon repli local."""
    pool = getattr(request.app.state, "arq_pool", None)
    if pool is not None:
        await pool.enqueue_job(
            "ingest_document_task", document_id, filename, data, form_metadata, tenant_id, replace
        )
        return
    background_tasks.add_task(
        _ingest_in_background,
        document_id,
        filename,
        data,
        form_metadata,
        tenant_id,
        get_indexer(request),
        replace=replace,
    )


@router.post("", response_model=list[UploadedDocumentOut])
@limiter.limit(get_settings().rate_limit_upload)
async def upload_documents(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    niveau: str | None = Form(default=None),
    classe: str | None = Form(default=None),
    serie: str | None = Form(default=None),
    discipline: str | None = Form(default=None),
    chapitre: str | None = Form(default=None),
    competence: str | None = Form(default=None),
    examen_associe: str | None = Form(default=None),
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> list[UploadedDocumentOut]:
    settings = get_settings()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    repo = DocumentRepository(session)

    form_metadata = {
        k: v
        for k, v in {
            "niveau": niveau,
            "classe": classe,
            "serie": serie,
            "discipline": discipline,
            "chapitre": chapitre,
            "competence": competence,
            "examen_associe": examen_associe,
        }.items()
        if v
    }

    results: list[UploadedDocumentOut] = []
    for file in files:
        if not _extension_ok(file.filename or ""):
            raise HTTPException(status_code=400, detail=f"Format non supporté : {file.filename}")
        data = await file.read()
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413, detail=f"Fichier trop volumineux : {file.filename} (> {settings.max_file_size_mb} Mo)"
            )
        doc_type = _doc_type_for(file.filename or "")
        doc = await repo.create_pending(tenant_id, file.filename or "sans-nom", doc_type, form_metadata or None)
        results.append(UploadedDocumentOut(document_id=doc.id, filename=doc.filename, status=doc.status))
        # Commit explicite AVANT de programmer la tâche d'arrière-plan : Starlette
        # exécute les BackgroundTasks pendant l'envoi de la réponse, donc AVANT que
        # la dépendance `get_session` ne se ferme (et commit) en sortie de requête.
        # Sans ce commit, la tâche (nouvelle session) ne verrait pas encore la ligne.
        await session.commit()
        await _schedule_ingestion(
            request,
            background_tasks,
            document_id=doc.id,
            filename=doc.filename,
            data=data,
            form_metadata=form_metadata,
            tenant_id=tenant_id,
        )
    return results


def _doc_type_for(filename: str) -> str:
    from agent_tuteur.ingestion.loaders import detect_doc_type

    try:
        return detect_doc_type(filename)
    except ValueError:
        return "txt"


def _to_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        doc_type=doc.doc_type,
        status=doc.status,
        error=doc.error,
        metadata=doc.metadata_,
        log=doc.log,
        created_at=doc.created_at,
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    tenant_id: str = Depends(get_tenant_id),
    repo: DocumentRepository = Depends(document_repo),
) -> list[DocumentOut]:
    docs = await repo.list(tenant_id)
    return [_to_out(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: str,
    tenant_id: str = Depends(get_tenant_id),
    repo: DocumentRepository = Depends(document_repo),
) -> DocumentOut:
    doc = await repo.get(document_id, tenant_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable")
    return _to_out(doc)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    request: Request,
    tenant_id: str = Depends(get_tenant_id),
    repo: DocumentRepository = Depends(document_repo),
) -> dict:
    doc = await repo.get(document_id, tenant_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable")
    get_indexer(request).delete_source(doc.filename)  # nettoie aussi le vectorstore
    await repo.delete(document_id, tenant_id)
    return {"deleted": True}


@router.get("/{document_id}/status")
async def document_status_stream(
    document_id: str,
    tenant_id: str = Depends(get_tenant_id),
) -> StreamingResponse:
    """SSE : émet le statut courant toutes les 500 ms jusqu'à un état terminal."""

    async def _events():
        terminal = {"indexed", "failed"}
        last_status: str | None = None
        for _ in range(120):  # ~60s garde-fou : évite un flux ouvert indéfiniment
            async with session_scope(tenant_id) as session:
                repo = DocumentRepository(session)
                doc = await repo.get(document_id, tenant_id)
            if doc is None:
                yield sse_event({"status": "not_found"})
                return
            if doc.status != last_status:
                yield sse_event(DocumentStatusEvent(status=doc.status, error=doc.error).model_dump())
                last_status = doc.status
            if doc.status in terminal:
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(_events(), media_type="text/event-stream")


@router.post("/{document_id}/reindex", response_model=UploadedDocumentOut)
async def reindex_document(
    document_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tenant_id: str = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
) -> UploadedDocumentOut:
    repo = DocumentRepository(session)
    doc = await repo.get(document_id, tenant_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable")

    data = await file.read()
    await repo.update_status(document_id, "pending", tenant_id=tenant_id)
    # Commit explicite AVANT la tâche d'arrière-plan (cf. commentaire dans upload_documents).
    await session.commit()
    await _schedule_ingestion(
        request,
        background_tasks,
        document_id=doc.id,
        filename=doc.filename,
        data=data,
        form_metadata=doc.metadata_ or {},
        tenant_id=tenant_id,
        replace=True,
    )
    return UploadedDocumentOut(document_id=doc.id, filename=doc.filename, status="pending")
