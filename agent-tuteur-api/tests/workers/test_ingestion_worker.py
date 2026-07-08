"""Valide la mécanique réelle de queue : job enqueué → worker ARQ burst → statut final.

Nécessite ``TEST_DATABASE_URL`` et ``TEST_REDIS_URL`` (skip automatique sinon).
Le worker tourne en mode ``burst`` (traite les jobs en attente puis s'arrête) —
pattern recommandé par ARQ pour les tests, pas un serveur longue durée.
"""

from __future__ import annotations

import os

from arq.connections import RedisSettings
from arq.worker import Worker

from agent_tuteur.persistence.repositories import DocumentRepository
from agent_tuteur.workers.ingestion_worker import ingest_document_task, shutdown, startup

MARKDOWN_DOC = (
    b"## Chapitre : Test worker ARQ\n\n"
    b"Contenu ingere par le vrai worker ARQ (pas BackgroundTasks).\n\n"
    b"### Exercice : Verification\n\n"
    b"**Enonce.** Un test.\n\n**Indice.** Un indice.\n\n**Solution.** Une solution.\n"
)


async def _run_burst_worker(redis_url: str) -> None:
    worker = Worker(
        functions=[ingest_document_task],
        redis_settings=RedisSettings.from_dsn(redis_url),
        on_startup=startup,
        on_shutdown=shutdown,
        burst=True,
        handle_signals=False,
        poll_delay=0.05,
    )
    await worker.async_run()
    await worker.close()


async def test_enqueued_job_is_processed_by_burst_worker(monkeypatch, redis_pool, redis_url, postgres_engine):
    tenant_id = "worker_test_tenant"
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("VECTOR_BACKEND", "memory")
    monkeypatch.setenv("EMBEDDING_BACKEND", "light")
    from agent_tuteur.config.settings import get_settings

    get_settings.cache_clear()

    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with factory() as session:
        repo = DocumentRepository(session)
        doc = await repo.create_pending(tenant_id, "worker_doc.md", "markdown")
        await session.commit()
        document_id = doc.id

    await redis_pool.enqueue_job(
        "ingest_document_task", document_id, "worker_doc.md", MARKDOWN_DOC, {}, tenant_id, False
    )

    await _run_burst_worker(redis_url)

    async with factory() as session:
        repo = DocumentRepository(session)
        final = await repo.get(document_id, tenant_id)
        assert final.status == "indexed"

    get_settings.cache_clear()
