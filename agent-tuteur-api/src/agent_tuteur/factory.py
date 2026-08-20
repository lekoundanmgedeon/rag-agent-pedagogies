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
from agent_tuteur.mcp.tools import build_tool_registry
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
        # La dimension vient de l'EMBEDDER, jamais du réglage : lui seul la
        # connaît. ``embedding_dense_dim`` ne pilote que le backend « light » ;
        # BGE-M3 impose 1024 et ignore ce réglage. Passer la valeur configurée
        # créerait une collection en 256 pour des vecteurs en 1024 — collection
        # muette à la création, puis en échec au premier upsert.
        dense_dim=embedder.dense_dim,
    )
    indexer = Indexer(embedder, store)
    retriever = HybridRetriever(
        embedder,
        store,
        top_k=settings.retrieval_top_k,
        # None = le seuil de l'embedder. Cf. Settings.rag_seuil_pertinence.
        seuil_pertinence=settings.rag_seuil_pertinence,
        # Idem : None = le consensus déclaré par l'embedder, qui est le cas normal.
        consensus_chapitre=settings.rag_consensus_chapitre,
    )
    return RagStack(indexer=indexer, retriever=retriever)


def build_llm_cours(settings: Settings | None = None, *, probe_ollama: bool = True) -> BaseLLM:
    settings = settings or get_settings()
    # Le backend cible pour le cours est GPT-5.5 (Gemini par défaut pour l'instant)
    return build_router(
<<<<<<< HEAD
        backend="gemini", # On force Gemini
=======
        backend=settings.llm_backend,
>>>>>>> 12555b75fe53161ddcede17d5663bb2b1f1155a8
        chain=settings.llm_chain,
        mistral_api_key=settings.mistral_api_key,
        mistral_model=settings.mistral_model,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        probe_ollama=probe_ollama,
    )

def build_llm_exercice(settings: Settings | None = None, *, probe_ollama: bool = True) -> BaseLLM:
    settings = settings or get_settings()
    # Le backend cible pour exercice est Mistral
    return build_router(
        backend="mistral", # On force Mistral
        chain=settings.llm_chain,
        mistral_api_key=settings.mistral_api_key,
        mistral_model=settings.mistral_model,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        probe_ollama=probe_ollama,
    )

def build_agent(
    *,
    settings: Settings | None = None,
    retriever: HybridRetriever | None = None,
    llm_cours: BaseLLM | None = None,
    llm_exercice: BaseLLM | None = None,
    memory: StudentMemoryPort | None = None,
    audit: AuditLogPort | None = None,
    probe_ollama: bool = True,
) -> TutorAgent:
    settings = settings or get_settings()
    retriever = retriever or build_rag_stack(settings).retriever
    llm_cours = llm_cours or build_llm_cours(settings, probe_ollama=probe_ollama)
    llm_exercice = llm_exercice or build_llm_exercice(settings, probe_ollama=probe_ollama)
    registry = build_tool_registry()

    return TutorAgent(
        retriever,
        llm_cours=llm_cours,
        llm_exercice=llm_exercice,
        memory=memory if memory is not None else InMemoryStudentMemory(),
        audit=audit if audit is not None else InMemoryAuditLog(),
        top_k=settings.retrieval_top_k,
        tool_registry=registry,
    )

def build_llm(settings: Settings | None = None, *, probe_ollama: bool = True) -> BaseLLM:
    """Factory for tests (layer B) returning the appropriate LLM.

    Chooses le LLM selon ``settings.llm_backend`` :
    - ``gemini`` → ``build_llm_cours`` (GPT‑5.5)
    - ``mistral`` → ``build_llm_exercice`` (Mistral)
    - autre valeur → ``MockLLM`` (fallback safe).
    """
    settings = settings or get_settings()
    backend = settings.llm_backend
    if backend == "gemini":
        return build_llm_cours(settings, probe_ollama=probe_ollama)
    if backend == "mistral":
        return build_llm_exercice(settings, probe_ollama=probe_ollama)
    from agent_tuteur.agent.llm.mock import MockLLM
    return MockLLM()



def ingest_corpus(indexer: Indexer, corpus_dir: str | Path) -> int:
    """Ingestion + indexation de tous les .md d'un dossier corpus."""
    total = 0
    for path in sorted(Path(corpus_dir).glob("*.md")):
        result = ingest_and_index(
            path.name, path.read_bytes(), indexer, source_path=path
        )
        total += result.n_chunks
    return total
