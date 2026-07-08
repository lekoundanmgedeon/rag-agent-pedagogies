"""Retriever hybride filtré par métadonnées curriculaires.

Rôle : traduire un *contexte curriculaire* (niveau, série, discipline…) en
filtres de store, encoder la question au même format que le contenu, et renvoyer
les chunks les plus pertinents avec leurs scores. L'expansion des alias de série
est appliquée ici pour qu'une question en « STIDD1 » atteigne des chunks « T1 ».
"""

from __future__ import annotations

from agent_tuteur.config.taxonomy import CHAMPS_INDEXES, serie_aliases
from agent_tuteur.domain.models import ScoredChunk
from agent_tuteur.vectorstore.embeddings import BaseEmbedder
from agent_tuteur.vectorstore.store import BaseVectorStore, Filters


def build_filters(context: dict) -> Filters:
    """Construit des filtres de store à partir d'un contexte curriculaire.

    Ne retient que les champs indexés non vides. La série est étendue à tous ses
    alias équivalents (ancienne ↔ nouvelle nomenclature).
    """
    filters: Filters = {}
    for field in CHAMPS_INDEXES:
        value = context.get(field)
        if not value:
            continue
        if field == "serie":
            filters[field] = serie_aliases(value)
        elif isinstance(value, (list, tuple, set)):
            filters[field] = [str(v) for v in value]
        else:
            filters[field] = [str(value)]
    return filters


class HybridRetriever:
    def __init__(
        self,
        embedder: BaseEmbedder,
        store: BaseVectorStore,
        top_k: int = 5,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._top_k = top_k

    def retrieve(
        self,
        query: str,
        context: dict | None = None,
        top_k: int | None = None,
    ) -> list[ScoredChunk]:
        filters = build_filters(context or {})
        query_emb = self._embedder.embed_query(query)
        return self._store.search(
            query_emb, top_k=top_k or self._top_k, filters=filters
        )
