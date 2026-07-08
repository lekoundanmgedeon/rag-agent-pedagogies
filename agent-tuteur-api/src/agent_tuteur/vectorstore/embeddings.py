"""Embeddings hybrides (dense + sparse).

Deux backends derrière une interface commune :

* ``LightEmbedder`` — **défaut, déterministe, hors-ligne**. Dense = hachage de
  n-grammes projeté et L2-normalisé ; sparse = poids lexicaux ``log(1 + tf)``.
  Aucune dépendance lourde, reproductible, suffisant pour la démo et les tests.
* ``BGEM3Embedder`` — BGE-M3 réel (dense + sparse), chargé en **import tardif**
  pour ne pas imposer ``FlagEmbedding``/torch au premier lancement.

Représentation commune : un vecteur dense ``np.ndarray`` + un vecteur sparse
``dict[int, float]`` (indice de terme haché -> poids).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass

import numpy as np

from agent_tuteur.textutil import char_ngrams, stable_hash, tokenize

# Espace d'indices des vecteurs sparse (assez grand pour limiter les collisions).
_SPARSE_SPACE = 2**20


@dataclass(frozen=True)
class Embedding:
    """Représentation hybride d'un texte."""

    dense: np.ndarray               # shape (dim,), float32, L2-normalisé
    sparse: dict[int, float]        # indice de terme -> poids


class BaseEmbedder(ABC):
    """Contrat d'un fournisseur d'embeddings hybrides."""

    @property
    @abstractmethod
    def dense_dim(self) -> int: ...

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[Embedding]: ...

    def embed_query(self, text: str) -> Embedding:
        # Par défaut, une requête s'encode comme un document (symétrie voulue :
        # même normaliseur/format pivot des deux côtés).
        return self.embed_documents([text])[0]


class LightEmbedder(BaseEmbedder):
    """Embedder déterministe hors-ligne (hachage dense + lexical sparse)."""

    def __init__(self, dim: int = 256) -> None:
        self._dim = dim

    @property
    def dense_dim(self) -> int:
        return self._dim

    def _dense(self, tokens: list[str]) -> np.ndarray:
        """Hashing trick : chaque feature indexe une dimension avec un signe.

        Features = tokens + n-grammes de caractères. Le signe (±1) déterministe
        limite le biais d'accumulation. Vecteur final L2-normalisé (cosinus).
        """
        vec = np.zeros(self._dim, dtype=np.float32)
        features: list[str] = list(tokens)
        for tok in tokens:
            features.extend(char_ngrams(tok, 3))
        for feat in features:
            h = stable_hash(feat)
            idx = h % self._dim
            sign = 1.0 if (h >> 20) & 1 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0.0:
            vec /= norm
        return vec

    def _sparse(self, tokens: list[str]) -> dict[int, float]:
        """Poids lexicaux ``log(1 + tf)`` indexés par terme haché."""
        counts = Counter(tokens)
        return {
            stable_hash(term) % _SPARSE_SPACE: math.log1p(tf)
            for term, tf in counts.items()
        }

    def embed_documents(self, texts: list[str]) -> list[Embedding]:
        out: list[Embedding] = []
        for text in texts:
            tokens = tokenize(text)
            out.append(Embedding(dense=self._dense(tokens), sparse=self._sparse(tokens)))
        return out


class BGEM3Embedder(BaseEmbedder):
    """Adaptateur BGE-M3 (dense + sparse lexical natifs). Import tardif."""

    def __init__(self, model_name: str = "BAAI/bge-m3") -> None:
        try:
            from FlagEmbedding import BGEM3FlagModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - dépend de l'infra
            raise RuntimeError(
                "BGE-M3 requiert le paquet 'FlagEmbedding' "
                "(pip install 'agent-tuteur-api[embeddings]'). "
                "Basculez EMBEDDING_BACKEND=light pour un fonctionnement hors-ligne."
            ) from exc
        self._model = BGEM3FlagModel(model_name, use_fp16=False)
        self._dim = 1024  # dimension dense de BGE-M3

    @property
    def dense_dim(self) -> int:
        return self._dim

    def embed_documents(self, texts: list[str]) -> list[Embedding]:  # pragma: no cover
        result = self._model.encode(
            texts, return_dense=True, return_sparse=True, return_colbert_vecs=False
        )
        dense = np.asarray(result["dense_vecs"], dtype=np.float32)
        out: list[Embedding] = []
        for i, text in enumerate(texts):
            lexical = result["lexical_weights"][i]
            sparse = {int(k): float(v) for k, v in lexical.items()}
            out.append(Embedding(dense=dense[i], sparse=sparse))
        return out


def build_embedder(backend: str = "light", dense_dim: int = 256) -> BaseEmbedder:
    """Fabrique un embedder selon la configuration (repli léger si BGE absent)."""
    if backend == "bge_m3":
        return BGEM3Embedder()
    return LightEmbedder(dim=dense_dim)
