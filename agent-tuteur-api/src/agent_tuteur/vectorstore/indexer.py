"""Indexer : embeddings des chunks puis upsert dans le store vectoriel.

Couche mince mais utile : centralise le couplage embedder ↔ store, de sorte que
l'ingestion et la ré-indexation partagent exactement la même logique.
"""

from __future__ import annotations

from agent_tuteur.domain.models import Chunk
from agent_tuteur.vectorstore.embeddings import BaseEmbedder
from agent_tuteur.vectorstore.store import BaseVectorStore


class Indexer:
    def __init__(self, embedder: BaseEmbedder, store: BaseVectorStore) -> None:
        self._embedder = embedder
        self._store = store

    def index_chunks(self, chunks: list[Chunk]) -> int:
        """Encode puis upsert une liste de chunks. Retourne le nombre indexé."""
        if not chunks:
            return 0
        embeddings = self._embedder.embed_documents([c.text for c in chunks])
        self._store.upsert(chunks, embeddings)
        return len(chunks)

    def reindex_source(self, source_document: str, chunks: list[Chunk]) -> int:
        """Remplace tous les chunks d'un document par une nouvelle version."""
        self._store.delete_by_source(source_document)
        return self.index_chunks(chunks)

    def delete_source(self, source_document: str) -> int:
        """Retire du vectorstore tous les chunks d'un document (sans réindexer)."""
        return self._store.delete_by_source(source_document)
