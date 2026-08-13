"""Backend Qdrant (dense + sparse, fusion RRF côté serveur).

Isolé dans son propre module pour n'importer ``qdrant-client`` que lorsque
``VECTOR_BACKEND=qdrant``. Non exercé par la suite de tests hors-ligne (nécessite
un serveur Qdrant) mais aligné sur l'interface ``BaseVectorStore``.
"""

from __future__ import annotations

import uuid

from agent_tuteur.config.taxonomy import CHAMPS_INDEXES, CHAMPS_NORMALISES
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

    def _verifier_dimension(self) -> None:
        """Refuse de servir une collection dont la dimension dense a changé.

        Changer d'embedder change la dimension (« light » 256 → BGE-M3 1024).
        Sans ce contrôle, ``_ensure_collection`` voyait la collection présente,
        sortait, et l'application démarrait sur un index inutilisable : les
        vecteurs déjà stockés répondent encore aux recherches mais dans un
        espace qui n'a plus rien à voir avec celui des requêtes. Les résultats
        restent plausibles — c'est le pire des cas de figure, une dérive
        silencieuse plutôt qu'une panne.

        On échoue donc au démarrage, avec la marche à suivre. Recréer la
        collection à la volée serait pire : cela effacerait un index de
        production sur un simple changement de variable d'environnement.
        """
        info = self._client.get_collection(self._collection)
        vecteurs = info.config.params.vectors or {}
        params = vecteurs.get(self.DENSE) if isinstance(vecteurs, dict) else None
        if params is None or params.size == self._dense_dim:
            return
        raise RuntimeError(
            f"La collection Qdrant « {self._collection} » est en {params.size} dimensions, "
            f"l'embedder courant en produit {self._dense_dim}. L'index existant est "
            "inutilisable tel quel. Recréez-le explicitement — supprimez la collection "
            "puis relancez l'ingestion du corpus — ou pointez QDRANT_COLLECTION sur un "
            "nouveau nom pour conserver l'ancien index le temps de la bascule."
        )

    def _ensure_collection(self) -> None:
        from qdrant_client import models as qm
        from qdrant_client.http.exceptions import UnexpectedResponse

        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection in existing:
            self._verifier_dimension()
            return
        try:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config={
                    self.DENSE: qm.VectorParams(size=self._dense_dim, distance=qm.Distance.COSINE)
                },
                sparse_vectors_config={self.SPARSE: qm.SparseVectorParams()},
            )
        except UnexpectedResponse as exc:
            if exc.status_code == 409:
                # Créée entre-temps par un autre processus (API/worker démarrent
                # en parallèle) : la collection existe déjà, rien à faire de plus
                # (l'index de payload a été créé par le gagnant de la course).
                return
            raise
        # Index de payload pour le filtrage curriculaire : les libellés bruts
        # (utiles à l'inspection), les compagnons normalisés effectivement
        # interrogés, et les alias de série.
        indexes = (
            *CHAMPS_INDEXES,
            *(f"{field}_key" for field in CHAMPS_NORMALISES),
            "serie_alias",
        )
        for field in indexes:
            self._client.create_payload_index(
                self._collection, field_name=field, field_schema=qm.PayloadSchemaType.KEYWORD
            )

    def upsert(self, chunks: list[Chunk], embeddings: list[Embedding]) -> None:
        from qdrant_client import models as qm

        points = []
        # strict=True : si l'embedder renvoie moins de vecteurs que de chunks,
        # zip() tronquerait en silence et des morceaux ne seraient jamais
        # indexés — panne invisible jusqu'à ce qu'un élève ne trouve rien.
        for chunk, emb in zip(chunks, embeddings, strict=True):
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
            # Le filtrage porte sur les compagnons normalisés, jamais sur les
            # libellés bruts : côté serveur le match est exact, donc un accent de
            # différence exclurait silencieusement le chunk (cf. taxonomy).
            if field == "serie":
                key = "serie_alias"
            elif field in CHAMPS_NORMALISES:
                key = f"{field}_key"
            else:
                key = field
            conditions.append(qm.FieldCondition(key=key, match=qm.MatchAny(any=list(allowed))))
        return qm.Filter(must=conditions) if conditions else None

    #: Garde-fou de pagination du catalogue : au-delà, on considère que la
    #: collection est trop grosse pour être énumérée dans un prompt de toute façon.
    MAX_PAGES_CATALOGUE = 50
    TAILLE_PAGE_CATALOGUE = 256

    def catalogue(self, filters: Filters | None = None) -> list[str]:
        """Chapitres distincts, obtenus par ``scroll`` sur les seuls payloads.

        ⚠️ Chemin **non couvert par les tests** : il demande un serveur Qdrant,
        absent de l'environnement de test (les tests correspondants sautent).
        Le déploiement de démo tourne sur ``VECTOR_BACKEND=memory``, dont
        l'implémentation, elle, est testée.
        """
        qfilter = self._build_filter(filters or {})
        chapitres: set[str] = set()
        offset = None
        for _ in range(self.MAX_PAGES_CATALOGUE):
            points, offset = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=qfilter,
                limit=self.TAILLE_PAGE_CATALOGUE,
                offset=offset,
                with_payload=["chapitre"],
                with_vectors=False,
            )
            for point in points:
                if chapitre := (point.payload or {}).get("chapitre"):
                    chapitres.add(chapitre)
            if offset is None:
                break
        return sorted(chapitres)

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
        cosinus = self._cosinus_par_point(
            [point.id for point in response.points], query, qfilter
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
                    dense_score=cosinus.get(point.id),
                )
            )
        return results

    def _cosinus_par_point(self, point_ids: list, query: Embedding, qfilter) -> dict:
        """Similarité cosinus dense, par identifiant de point.

        ``score`` ne peut pas servir de mesure de pertinence : la fusion RRF
        est fondée sur les **rangs** (~1/(k+rang)), si bien qu'un résultat sans
        aucun rapport avec le corpus obtient un score voisin d'un résultat
        parfaitement pertinent — mesuré sur ce dépôt, un hors-périmètre à 0,0325
        au-dessus d'un témoin dans le périmètre à 0,0318. Aucun seuil ne peut
        être posé là-dessus (cas QA #5).

        On rappelle donc le **cosinus**, borné et interprétable, par une seconde
        requête dense pure. Elle est restreinte aux identifiants déjà retenus :
        le coût est un aller-retour, pas un second classement, et chaque chunk
        rendu porte son cosinus exact plutôt qu'une valeur approchée par une
        fenêtre de candidats.

        Un identifiant absent de la réponse reçoit ``None`` et non ``0.0`` :
        « inconnu » et « orthogonal » sont deux choses différentes, et les
        confondre ferait rejeter à tort un chunk par un futur seuil.
        """
        if not point_ids:
            return {}
        from qdrant_client import models as qm

        conditions = [qm.HasIdCondition(has_id=list(point_ids))]
        filtre = qm.Filter(must=conditions)
        if qfilter is not None:
            filtre = qm.Filter(must=[*conditions, qfilter])
        reponse = self._client.query_points(
            collection_name=self._collection,
            query=query.dense.tolist(),
            using=self.DENSE,
            filter=filtre,
            limit=len(point_ids),
            with_payload=False,
        )
        return {p.id: round(float(p.score), 6) for p in reponse.points}

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

    def count_for_source(self, source_document: str) -> int:
        from qdrant_client import models as qm

        result = self._client.count(
            collection_name=self._collection,
            count_filter=qm.Filter(
                must=[qm.FieldCondition(key="source_document", match=qm.MatchValue(value=source_document))]
            ),
        )
        return result.count
