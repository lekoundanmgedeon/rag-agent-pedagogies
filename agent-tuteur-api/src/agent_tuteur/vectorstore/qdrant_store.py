"""Backend Qdrant (dense + sparse, fusion RRF côté serveur).

Isolé dans son propre module pour n'importer ``qdrant-client`` que lorsque
``VECTOR_BACKEND=qdrant``. Non exercé par la suite de tests hors-ligne (nécessite
un serveur Qdrant) mais aligné sur l'interface ``BaseVectorStore``.
"""

from __future__ import annotations

import uuid

from agent_tuteur.config.taxonomy import CHAMPS_INDEXES
from agent_tuteur.domain.models import Chunk, CurriculumMetadata, ScoredChunk
from agent_tuteur.vectorstore.embeddings import Embedding
from agent_tuteur.vectorstore.store import BaseVectorStore, Filters


class QdrantVectorStore(BaseVectorStore):  # pragma: no cover - nécessite un serveur
    """Collection Qdrant à vecteurs nommés ``dense`` + ``sparse``."""

    DENSE = "dense"
    SPARSE = "sparse"

    def __init__(
        self,
        *,
        url: str = "http://localhost:6333",
        api_key: str = "",
        collection: str = "curriculum",
        dense_dim: int = 256,
        rrf_k: int = 60,
    ) -> None:
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError(
                "Qdrant requiert 'qdrant-client' "
                "(pip install 'agent-tuteur-api[vectorstore]'). "
                "Basculez VECTOR_BACKEND=memory pour un fonctionnement sans serveur."
            ) from exc
        self._client = QdrantClient(url=url, api_key=api_key or None)
        self._collection = collection
        self._dense_dim = dense_dim
        self._rrf_k = rrf_k
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        from qdrant_client import models as qm

        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection in existing:
            return
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config={
                self.DENSE: qm.VectorParams(size=self._dense_dim, distance=qm.Distance.COSINE)
            },
            sparse_vectors_config={self.SPARSE: qm.SparseVectorParams()},
        )
        # Index de payload pour le filtrage curriculaire.
        for field in CHAMPS_INDEXES:
            self._client.create_payload_index(
                self._collection, field_name=field, field_schema=qm.PayloadSchemaType.KEYWORD
            )
        self._client.create_payload_index(
            self._collection, field_name="serie_alias", field_schema=qm.PayloadSchemaType.KEYWORD
        )

    def upsert(self, chunks: list[Chunk], embeddings: list[Embedding]) -> None:
        from qdrant_client import models as qm

        points = []
        for chunk, emb in zip(chunks, embeddings):
            indices = list(emb.sparse.keys())
            values = [emb.sparse[i] for i in indices]
            points.append(
                qm.PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk.id)),
                    vector={
                        self.DENSE: emb.dense.tolist(),
                        self.SPARSE: qm.SparseVector(indices=indices, values=values),
                    },
                    payload={"chunk_id": chunk.id, "text": chunk.text, **chunk.metadata.model_dump()},
                )
            )
        self._client.upsert(collection_name=self._collection, points=points)

    def _build_filter(self, filters: Filters):
        from qdrant_client import models as qm

        conditions = []
        for field, allowed in filters.items():
            if not allowed:
                continue
            key = "serie_alias" if field == "serie" else field
            conditions.append(qm.FieldCondition(key=key, match=qm.MatchAny(any=list(allowed))))
        return qm.Filter(must=conditions) if conditions else None

    def search(
        self, query: Embedding, top_k: int = 5, filters: Filters | None = None
    ) -> list[ScoredChunk]:
        from qdrant_client import models as qm

        qfilter = self._build_filter(filters or {})
        indices = list(query.sparse.keys())
        values = [query.sparse[i] for i in indices]
        response = self._client.query_points(
            collection_name=self._collection,
            prefetch=[
                qm.Prefetch(query=query.dense.tolist(), using=self.DENSE, filter=qfilter, limit=top_k * 4),
                qm.Prefetch(
                    query=qm.SparseVector(indices=indices, values=values),
                    using=self.SPARSE,
                    filter=qfilter,
                    limit=top_k * 4,
                ),
            ],
            query=qm.FusionQuery(fusion=qm.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        results: list[ScoredChunk] = []
        for point in response.points:
            payload = dict(point.payload or {})
            text = payload.pop("text", "")
            chunk_id = payload.pop("chunk_id", str(point.id))
            metadata = CurriculumMetadata(**{k: v for k, v in payload.items()
                                             if k in CurriculumMetadata.model_fields})
            results.append(
                ScoredChunk(
                    chunk=Chunk(id=chunk_id, text=text, metadata=metadata),
                    score=round(float(point.score), 6),
                )
            )
        return results

    def delete_by_source(self, source_document: str) -> int:
        from qdrant_client import models as qm

        self._client.delete(
            collection_name=self._collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[qm.FieldCondition(key="source_document", match=qm.MatchValue(value=source_document))]
                )
            ),
        )
        return -1  # Qdrant ne renvoie pas le compte supprimé ici.

    def count(self) -> int:
        return self._client.count(collection_name=self._collection).count
