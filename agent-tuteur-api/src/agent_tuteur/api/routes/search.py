"""POST /api/search — recherche hybride filtrée (chunks + scores + métadonnées).

Expose directement le ``HybridRetriever`` du cœur RAG. Note : avec le backend
par défaut (``VECTOR_BACKEND=memory``), la recherche est un calcul CPU pur donc
sans risque de bloquer la boucle événementielle ; avec un backend Qdrant réel,
``vectorstore/qdrant_store.py`` utilise un client **synchrone** (limitation
connue, cf. docs/architecture.md) et bloquerait le event loop le temps de
l'appel réseau — non corrigé dans cette session, documenté comme dette.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agent_tuteur.api.dependencies import get_retriever, require_admin
from agent_tuteur.api.schemas import SearchRequest, SearchResultOut
from agent_tuteur.vectorstore.retriever import HybridRetriever

# Recherche RAG de débogage : espace administrateur uniquement.
router = APIRouter(prefix="/api/search", tags=["search"], dependencies=[Depends(require_admin)])


@router.post("", response_model=list[SearchResultOut])
async def search(
    payload: SearchRequest,
    retriever: HybridRetriever = Depends(get_retriever),
) -> list[SearchResultOut]:
    results = retriever.retrieve(payload.query, payload.curriculum_context, top_k=payload.top_k)
    return [
        SearchResultOut(
            id=sc.chunk.id,
            text=sc.chunk.text,
            score=sc.score,
            dense_score=sc.dense_score,
            sparse_score=sc.sparse_score,
            metadata=sc.chunk.metadata.model_dump(),
        )
        for sc in results
    ]
