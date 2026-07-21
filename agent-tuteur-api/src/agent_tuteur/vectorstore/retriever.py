"""Retriever hybride filtré par métadonnées curriculaires.

Rôle : traduire un *contexte curriculaire* (niveau, série, discipline…) en
filtres de store, encoder la question au même format que le contenu, et renvoyer
les chunks les plus pertinents avec leurs scores. L'expansion des alias de série
est appliquée ici pour qu'une question en « STIDD1 » atteigne des chunks « T1 ».
"""

from __future__ import annotations

from agent_tuteur.config.taxonomy import (
    CHAMPS_INDEXES,
    CHAMPS_NORMALISES,
    serie_aliases,
    taxonomy_key,
)
from agent_tuteur.domain.models import ScoredChunk
from agent_tuteur.vectorstore.embeddings import BaseEmbedder
from agent_tuteur.vectorstore.store import BaseVectorStore, Filters


def build_filters(context: dict) -> Filters:
    """Construit des filtres de store à partir d'un contexte curriculaire.

    Ne retient que les champs indexés non vides. Deux normalisations s'appliquent
    pour qu'un libellé saisi par un humain atteigne les chunks correspondants :

    * la **série** est étendue à tous ses alias équivalents (ancienne ↔ nouvelle
      nomenclature) — « STIDD1 » atteint des chunks « T1 » ;
    * les autres libellés curriculaires sont réduits à leur clé normalisée —
      « Mathematiques » atteint « Mathématiques », « Les Suites Numériques »
      atteint « Suites Numeriques ».

    Les valeurs renvoyées pour ces champs sont donc des *clés*, que les stores
    confrontent aux compagnons ``<champ>_key`` des chunks, jamais aux libellés.
    """
    filters: Filters = {}
    for field in CHAMPS_INDEXES:
        value = context.get(field)
        if not value:
            continue
        if field == "serie":
            filters[field] = serie_aliases(value)
            continue
        values = (
            [str(v) for v in value]
            if isinstance(value, (list, tuple, set))
            else [str(value)]
        )
        filters[field] = (
            [taxonomy_key(v) for v in values] if field in CHAMPS_NORMALISES else values
        )
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
