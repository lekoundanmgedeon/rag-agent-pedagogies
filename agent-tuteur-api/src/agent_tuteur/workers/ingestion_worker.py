"""Worker ARQ — ingestion asynchrone (extract → normalize → chunk → embed → upsert).

Remplace le ``BackgroundTasks`` provisoire de l'étape 5 : même code de pipeline
(``ingestion.pipeline.process_document`` + ``vectorstore.indexer.Indexer``),
exécuté cette fois dans un **processus séparé**, consommant une file Redis.
``api/routes/documents.py`` reste inchangé côté contrat observable — seule la
manière dont le job est déclenché change (``pool.enqueue_job`` au lieu de
``BackgroundTasks.add_task``), avec repli automatique sur ``BackgroundTasks``
si Redis/le worker sont indisponibles (dégradation gracieuse, cf. ``api/main.py``).

**Limitation connue (documentée, pas un bug) :** avec ``VECTOR_BACKEND=memory``
(défaut hors-ligne), le worker construit son **propre** store en mémoire,
distinct de celui du processus API — un document ingéré par le worker n'est
donc PAS visible en recherche/chat tant que l'API tourne dans un processus
différent. Ce mode convient pour valider la mécanique de queue (voir tests),
mais un flux upload→recherche cohérent en multi-processus exige
``VECTOR_BACKEND=qdrant`` (serveur externe partagé par API et worker) — c'est
la configuration recommandée pour la stack complète (``docker-compose``,
étape 8). Le corpus de démonstration reste fonctionnel indépendamment de ceci
car il est ingéré directement par le processus API à son démarrage.
"""

from __future__ import annotations

import time
from typing import Any

from arq.connections import RedisSettings

from agent_tuteur.config.settings import get_settings
from agent_tuteur.factory import build_rag_stack
from agent_tuteur.ingestion.pipeline import process_document
from agent_tuteur.observability import get_logger, log_event, setup_logging
from agent_tuteur.persistence.db import dispose_engine, init_engine, session_scope
from agent_tuteur.persistence.repositories import DocumentRepository

setup_logging("worker")
_logger = get_logger("agent_tuteur.workers.ingestion_worker")


async def ingest_document_task(
    ctx: dict[str, Any],
    document_id: str,
    filename: str,
    data: bytes,
    form_metadata: dict,
    tenant_id: str,
    replace: bool = False,
) -> None:
    """Job ARQ : extrait, normalise, chunk, annote, embed, upsert, puis statut final.

    Chaque étape (y compris l'embedding/upsert, chronométré ici) est accumulée
    dans ``steps`` et persistée dans ``documents.log`` — succès ou échec — pour
    reconstituer précisément où en est/où a échoué une ingestion donnée.
    """
    indexer = ctx["indexer"]
    log_event(_logger, "ingestion:job_start", document_id=document_id, filename=filename, tenant_id=tenant_id)
    async with session_scope(tenant_id) as session:
        repo = DocumentRepository(session)
        steps: list[dict] = []
        try:
            result = process_document(filename, data, form_metadata, document_id=document_id)
            steps = result.steps
            t0 = time.perf_counter()
            if replace:
                indexer.reindex_source(filename, result.chunks)
            else:
                indexer.index_chunks(result.chunks)
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            steps.append({"step": "embed_upsert", "duration_ms": duration_ms, "n_chunks": result.n_chunks})
            log_event(_logger, "ingestion:embed_upsert", document_id=document_id, filename=filename,
                      duration_ms=duration_ms, n_chunks=result.n_chunks)
            await repo.update_status(document_id, "indexed", tenant_id=tenant_id, log=steps)
            log_event(_logger, "ingestion:job_done", document_id=document_id, filename=filename, status="indexed")
        except Exception as exc:  # noqa: BLE001 — toute erreur d'ingestion doit aboutir en 'failed'.
            log_event(_logger, "ingestion:job_failed", document_id=document_id, filename=filename,
                      error=str(exc), log_level=40)
            await repo.update_status(document_id, "failed", error=str(exc), tenant_id=tenant_id, log=steps)


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    init_engine(settings.database_url)
    ctx["indexer"] = build_rag_stack(settings).indexer


async def shutdown(ctx: dict[str, Any]) -> None:
    await dispose_engine()


class WorkerSettings:
    """Point d'entrée ARQ : ``arq agent_tuteur.workers.ingestion_worker.WorkerSettings``."""

    functions = [ingest_document_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
