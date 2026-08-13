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

    #: Similarité minimale pour qu'un extrait soit jugé sur le sujet.
    #:
    #: Un seuil de pertinence n'est pas un réglage d'application : c'est une
    #: propriété de l'**espace vectoriel**, donc de l'embedder qui le produit.
    #: La même valeur n'a aucun sens d'un backend à l'autre, et un seuil hérité
    #: d'un embedder précédent est pire que pas de seuil du tout — il écarte du
    #: cours pertinent en silence.
    #:
    #: ``None`` signifie « aucun seuil posable sur cet espace » : le retriever
    #: ne filtre alors rien plutôt que de deviner. C'est le cas de tous les
    #: backends à ce jour — cf. les mesures ci-dessous et `qa/qa_status.json` #5.
    seuil_pertinence: float | None = None

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

    #: Aucun seuil. Mesuré, et non supposé : les deux nuages se recouvrent.
    #:
    #: Sur les 12 leçons du corpus (216 chunks), 28 questions couvertes contre
    #: 16 hors périmètre : le cosinus dense le plus bas d'une question couverte
    #: (0,278 — « loi binomiale, dans quel cas l'utiliser ») tombe **sous** le
    #: plus haut d'une question hors périmètre (0,524 — « limite de sin(x)/x »).
    #: Aucune valeur ne sépare : à 0,40, quatre questions étrangères passent
    #: encore et deux questions couvertes sont déjà rejetées. Le score lexical
    #: ne fait pas mieux (marge −0,168 sur le corpus figé QA).
    #:
    #: C'est attendu d'un hachage de n-grammes — la proximité y mesure un
    #: recouvrement de caractères, pas un rapport de sens. Poser malgré tout un
    #: seuil ici reviendrait à l'ajuster aux prompts des testeurs, ce que
    #: CLAUDE.md interdit explicitement (cas QA #5).
    seuil_pertinence = None

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
    """Adaptateur BGE-M3 (dense + sparse lexical natifs). Import tardif.

    Pas de ``seuil_pertinence`` déclaré à ce jour, et ce n'est pas un oubli.
    Mesuré sur le corpus figé QA (36 chunks, 2 chapitres), le **cosinus dense**
    ne sépare pas : le prompt exact du cas QA #5 y vaut 0,5031 quand la question
    couverte la plus faible vaut 0,5178. Toute valeur qui rejette l'un sans
    rejeter l'autre vit dans une fenêtre de 0,015 — soit un seuil ajusté au
    prompt d'un testeur, ce que CLAUDE.md interdit.

    Le **score lexical** du même modèle sépare, lui : 0,1402 pour ce prompt
    contre 0,2105 pour la question couverte la plus faible. Le poser en seuil
    suppose d'abord de rappeler ce score depuis Qdrant, comme cela a été fait
    pour ``dense_score``. Cf. `qa/qa_status.json` #5.
    """

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
        for i in range(len(texts)):
            lexical = result["lexical_weights"][i]
            sparse = {int(k): float(v) for k, v in lexical.items()}
            out.append(Embedding(dense=dense[i], sparse=sparse))
        return out


def build_embedder(backend: str = "light", dense_dim: int = 256) -> BaseEmbedder:
    """Fabrique un embedder selon la configuration (repli léger si BGE absent)."""
    if backend == "bge_m3":
        return BGEM3Embedder()
    return LightEmbedder(dim=dense_dim)
