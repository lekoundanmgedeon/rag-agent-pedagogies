"""Upload et gestion des documents curriculaires.

**Note d'implémentation (portée de cette session) :** l'ingestion asynchrone via
ARQ + Redis est prévue à l'étape 6 (hors périmètre). En attendant, le traitement
post-upload utilise ``BackgroundTasks`` de FastAPI : même contrat observable côté
client (``document_id`` renvoyé immédiatement, statut ``pending``→``indexed``/
``failed`` consultable ensuite), et le CODE de pipeline appelé
(``ingestion.pipeline.process_document`` + ``Indexer.index_chunks``) est
exactement celui qu'un futur worker ARQ invoquera — remplacer le exécuteur
(BackgroundTasks → job de queue) n'affectera pas cette couche.

De même, ``/status`` expose un flux SSE par **sondage** de la base (pas encore
d'événements fins par étape extract/normalize/chunk/embed, qui viendront avec le
worker à l'étape 6) : le contrat SSE observable ({status: ...} jusqu'à un état
terminal) restera stable.

``reindex`` accepte un nouveau fichier plutôt qu'un identifiant sans contenu : le
stack verrouillée ne prévoit pas de stockage d'objets (S3/MinIO) pour conserver
le fichier original, donc une ré-indexation « à partir de la source » nécessite
de la refournir. Décision documentée dans docs/adr.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from agent_tuteur.api.dependencies import document_repo, get_indexer, get_tenant_id
from agent_tuteur.api.rate_limit import limiter
from agent_tuteur.api.schemas import DocumentOut, DocumentStatusEvent, UploadedDocumentOut
from agent_tuteur.api.streaming import sse_event
from agent_tuteur.config.settings import get_settings
from agent_tuteur.ingestion.loaders import SUPPORTED_EXTENSIONS
from agent_tuteur.ingestion.pipeline import process_document
from agent_tuteur.persistence.db import session_scope
from agent_tuteur.persistence.models import Document
from agent_tuteur.persistence.repositories import DocumentRepository
from agent_tuteur.vectorstore.indexer import Indexer

router = APIRouter(prefix="/api/documents", tags=["documents"])

_METADATA_FIELDS = ("niveau", "classe", "serie", "discipline", "chapitre", "competence", "examen_associe")


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
    """Exécutée après la réponse HTTP : extraction → indexation → statut final.

    ``replace=True`` (cas ré-indexation) retire d'abord les anciens chunks du
    document avant d'indexer les nouveaux (``Indexer.reindex_source``).
    """
    async with session_scope(tenant_id) as session:
        repo = DocumentRepository(session)
        try:
            result = await asyncio.to_thread(process_document, filename, data, form_metadata)
            if replace:
                await asyncio.to_thread(indexer.reindex_source, filename, result.chunks)
            else:
                await asyncio.to_thread(indexer.index_chunks, result.chunks)
            await repo.update_status(document_id, "indexed")
        except Exception as exc:  # noqa: BLE001 — toute erreur d'ingestion doit aboutir en 'failed', pas planter le worker.
            await repo.update_status(document_id, "failed", error=str(exc))


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
    repo: DocumentRepository = Depends(document_repo),
) -> list[UploadedDocumentOut]:
    settings = get_settings()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    indexer = get_indexer(request)

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
        background_tasks.add_task(
            _ingest_in_background, doc.id, doc.filename, data, form_metadata, tenant_id, indexer
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
        created_at=doc.created_at,
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(repo: DocumentRepository = Depends(document_repo)) -> list[DocumentOut]:
    docs = await repo.list()
    return [_to_out(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, repo: DocumentRepository = Depends(document_repo)) -> DocumentOut:
    doc = await repo.get(document_id)
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
    repo: DocumentRepository = Depends(document_repo),
) -> UploadedDocumentOut:
    doc = await repo.get(document_id, tenant_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable")

    data = await file.read()
    await repo.update_status(document_id, "pending")
    background_tasks.add_task(
        _ingest_in_background,
        doc.id,
        doc.filename,
        data,
        doc.metadata_ or {},
        tenant_id,
        get_indexer(request),
        replace=True,
    )
    return UploadedDocumentOut(document_id=doc.id, filename=doc.filename, status="pending")
