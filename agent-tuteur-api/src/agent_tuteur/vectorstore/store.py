"""Stockage vectoriel hybride derrière une interface commune.

* ``InMemoryVectorStore`` — **défaut dev/tests, sans serveur**. Similarité dense
  cosinus + score sparse par produit scalaire, fusionnés par **RRF** (Reciprocal
  Rank Fusion). Filtrage par métadonnées curriculaires (avec expansion des alias
  de série).
* ``QdrantVectorStore`` — Qdrant réel (dense + sparse natifs, RRF côté serveur),
  chargé en **import tardif**.

Le filtrage `serie` est spécial : un chunk annoté « T1 » doit répondre à un filtre
« STIDD1 » — on compare donc contre l'union `{serie} ∪ serie_alias`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from agent_tuteur.domain.models import Chunk, ScoredChunk
from agent_tuteur.vectorstore.embeddings import Embedding

# Champs de métadonnées autorisés au filtrage (cf. CHAMPS_INDEXES).
Filters = dict[str, list[str]]


def _matches(metadata, filters: Filters) -> bool:
    """Vrai si le chunk satisfait tous les filtres (ET logique entre champs)."""
    for field, allowed in filters.items():
        if not allowed:
            continue
        if field == "serie":
            candidate = {metadata.serie, *metadata.serie_alias} - {None}
            if candidate.isdisjoint(set(allowed)):
                return False
        else:
            value = getattr(metadata, field, None)
            if value not in allowed:
                return False
    return True


def _rrf(rankings: list[list[str]], k: int) -> dict[str, float]:
    """Reciprocal Rank Fusion : combine plusieurs classements en un score.

    ``score(d) = Σ_liste 1 / (k + rang_d)`` (rang à partir de 1). Robuste car
    fondé sur les rangs, pas sur des scores d'échelles hétérogènes (cosinus vs
    produit scalaire lexical).
    """
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (k + rank)
    return fused


@dataclass
class _Record:
    chunk: Chunk
    dense: np.ndarray
    sparse: dict[int, float]


class BaseVectorStore(ABC):
    @abstractmethod
    def upsert(self, chunks: list[Chunk], embeddings: list[Embedding]) -> None: ...

    @abstractmethod
    def search(
        self, query: Embedding, top_k: int = 5, filters: Filters | None = None
    ) -> list[ScoredChunk]: ...

    @abstractmethod
    def delete_by_source(self, source_document: str) -> int: ...

    @abstractmethod
    def count(self) -> int: ...


class InMemoryVectorStore(BaseVectorStore):
    """Store hybride en mémoire (dense cosinus + sparse dot + RRF)."""

    def __init__(self, rrf_k: int = 60) -> None:
        self._records: dict[str, _Record] = {}
        self._rrf_k = rrf_k

    def upsert(self, chunks: list[Chunk], embeddings: list[Embedding]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks et embeddings doivent avoir la même longueur")
        for chunk, emb in zip(chunks, embeddings):
            self._records[chunk.id] = _Record(chunk=chunk, dense=emb.dense, sparse=emb.sparse)

    @staticmethod
    def _sparse_dot(a: dict[int, float], b: dict[int, float]) -> float:
        # Itère sur le plus petit vecteur pour l'efficacité.
        if len(a) > len(b):
            a, b = b, a
        return sum(w * b.get(idx, 0.0) for idx, w in a.items())

    def search(
        self, query: Embedding, top_k: int = 5, filters: Filters | None = None
    ) -> list[ScoredChunk]:
        filters = filters or {}
        candidates = [
            rec for rec in self._records.values() if _matches(rec.chunk.metadata, filters)
        ]
        if not candidates:
            return []

        dense_scores: dict[str, float] = {}
        sparse_scores: dict[str, float] = {}
        for rec in candidates:
            # Vecteurs denses déjà L2-normalisés -> le produit scalaire = cosinus.
            dense_scores[rec.chunk.id] = float(np.dot(query.dense, rec.dense))
            sparse_scores[rec.chunk.id] = self._sparse_dot(query.sparse, rec.sparse)

        dense_rank = sorted(dense_scores, key=lambda i: dense_scores[i], reverse=True)
        sparse_rank = sorted(sparse_scores, key=lambda i: sparse_scores[i], reverse=True)
        fused = _rrf([dense_rank, sparse_rank], self._rrf_k)

        ordered = sorted(fused, key=lambda i: fused[i], reverse=True)[:top_k]
        return [
            ScoredChunk(
                chunk=self._records[cid].chunk,
                score=round(fused[cid], 6),
                dense_score=round(dense_scores[cid], 6),
                sparse_score=round(sparse_scores[cid], 6),
            )
            for cid in ordered
        ]

    def delete_by_source(self, source_document: str) -> int:
        to_remove = [
            cid
            for cid, rec in self._records.items()
            if rec.chunk.metadata.source_document == source_document
        ]
        for cid in to_remove:
            del self._records[cid]
        return len(to_remove)

    def count(self) -> int:
        return len(self._records)


def build_vector_store(backend: str = "memory", *, rrf_k: int = 60, **kwargs) -> BaseVectorStore:
    """Fabrique un store selon la configuration."""
    if backend == "qdrant":
        from agent_tuteur.vectorstore.qdrant_store import QdrantVectorStore

        return QdrantVectorStore(rrf_k=rrf_k, **kwargs)
    return InMemoryVectorStore(rrf_k=rrf_k)
