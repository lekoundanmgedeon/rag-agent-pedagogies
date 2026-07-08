"""Assemblage du cœur (composition root, hors API).

Câble embeddings → store → indexer → retriever → agent (LLM + garde-fous +
mémoire + audit) selon la configuration. L'API (étape 5) réutilisera ces mêmes
fabriques ; ici elles servent la démo et les tests d'intégration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.agent.llm.base import BaseLLM
from agent_tuteur.agent.llm.router import build_router
from agent_tuteur.agent.ports import (
    AuditLogPort,
    InMemoryAuditLog,
    InMemoryStudentMemory,
    StudentMemoryPort,
)
from agent_tuteur.config.settings import Settings, get_settings
from agent_tuteur.ingestion.pipeline import ingest_and_index
from agent_tuteur.vectorstore.embeddings import build_embedder
from agent_tuteur.vectorstore.indexer import Indexer
from agent_tuteur.vectorstore.retriever import HybridRetriever
from agent_tuteur.vectorstore.store import build_vector_store


@dataclass
class RagStack:
    indexer: Indexer
    retriever: HybridRetriever


def build_rag_stack(settings: Settings | None = None) -> RagStack:
    settings = settings or get_settings()
    embedder = build_embedder(settings.embedding_backend, dense_dim=settings.embedding_dense_dim)
    store = build_vector_store(
        settings.vector_backend,
        rrf_k=settings.rrf_k,
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        collection=settings.qdrant_collection,
        dense_dim=settings.embedding_dense_dim,
    )
    indexer = Indexer(embedder, store)
    retriever = HybridRetriever(embedder, store, top_k=settings.retrieval_top_k)
    return RagStack(indexer=indexer, retriever=retriever)


def build_llm(settings: Settings | None = None, *, probe_ollama: bool = True) -> BaseLLM:
    settings = settings or get_settings()
    return build_router(
        backend=settings.llm_backend,
        mistral_api_key=settings.mistral_api_key,
        mistral_model=settings.mistral_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        probe_ollama=probe_ollama,
    )


def build_agent(
    *,
    settings: Settings | None = None,
    retriever: HybridRetriever | None = None,
    llm: BaseLLM | None = None,
    memory: StudentMemoryPort | None = None,
    audit: AuditLogPort | None = None,
    probe_ollama: bool = True,
) -> TutorAgent:
    settings = settings or get_settings()
    retriever = retriever or build_rag_stack(settings).retriever
    llm = llm or build_llm(settings, probe_ollama=probe_ollama)
    return TutorAgent(
        retriever,
        llm,
        memory=memory if memory is not None else InMemoryStudentMemory(),
        audit=audit if audit is not None else InMemoryAuditLog(),
        top_k=settings.retrieval_top_k,
    )


def ingest_corpus(indexer: Indexer, corpus_dir: str | Path) -> int:
    """Ingestion + indexation de tous les .md d'un dossier corpus."""
    total = 0
    for path in sorted(Path(corpus_dir).glob("*.md")):
        result = ingest_and_index(path.name, path.read_bytes(), indexer)
        total += result.n_chunks
    return total
