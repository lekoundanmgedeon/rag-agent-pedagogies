"""Fixtures partagées par la suite de tests (mode hors-ligne, in-memory)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from agent_tuteur.ingestion.pipeline import ingest_and_index
from agent_tuteur.vectorstore.embeddings import BaseEmbedder, build_embedder
from agent_tuteur.vectorstore.indexer import Indexer
from agent_tuteur.vectorstore.retriever import HybridRetriever
from agent_tuteur.vectorstore.store import BaseVectorStore, build_vector_store

CORPUS_DIR = Path(__file__).resolve().parents[1] / "corpus"


@dataclass
class RagStack:
    embedder: BaseEmbedder
    store: BaseVectorStore
    indexer: Indexer
    retriever: HybridRetriever


@pytest.fixture
def corpus_dir() -> Path:
    return CORPUS_DIR


@pytest.fixture
def rag_stack() -> RagStack:
    """Stack RAG in-memory alimentée par le corpus d'exemple."""
    embedder = build_embedder("light", dense_dim=256)
    store = build_vector_store("memory", rrf_k=60)
    indexer = Indexer(embedder, store)
    for path in sorted(CORPUS_DIR.glob("*.md")):
        ingest_and_index(path.name, path.read_bytes(), indexer)
    retriever = HybridRetriever(embedder, store, top_k=5)
    return RagStack(embedder=embedder, store=store, indexer=indexer, retriever=retriever)


@pytest_asyncio.fixture
async def postgres_engine():
    """Engine Postgres réel — partagé par tests/persistence et tests/workers.

    Skip automatique si ``TEST_DATABASE_URL`` n'est pas défini/joignable.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL non défini : smoke test Postgres ignoré.")
    engine = create_async_engine(url)
    try:
        async with engine.connect():
            pass
    except Exception as exc:  # pragma: no cover - dépend de l'infra
        pytest.skip(f"Postgres de test injoignable : {exc}")
    yield engine
    await engine.dispose()
