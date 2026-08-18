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

    #: Fraction du top-k qui doit se porter sur un **même chapitre** pour que la
    #: question soit jugée dans le périmètre du corpus (cas QA #5).
    #:
    #: Mesuré sur les 12 leçons (216 chunks, 35 questions couvertes contre 18
    #: étrangères), aucun score scalaire — ni le cosinus dense, ni le poids
    #: lexical — ne sépare les deux nuages : toutes les marges sont négatives.
    #: Ce qui sépare est un **consensus**, pas une grandeur : une question
    #: couverte concentre son top-k sur un chapitre, une question étrangère
    #: l'éparpille faute d'avoir un foyer dans le corpus.
    #:
    #: L'avantage sur un seuil scalaire n'est pas qu'accidentel : la règle ne
    #: dépend d'aucune échelle, donc ni du backend, ni d'un ``dense_score`` que
    #: le store doit renseigner. Elle dépend en revanche de la **qualité
    #: sémantique** de l'embedder — d'où sa déclaration ici, backend par
    #: backend, et non en réglage d'application.
    #:
    #: ``None`` = « pas de périmètre décidable sur cet espace » : le retriever
    #: sert alors ce qu'il trouve, comme avant.
    consensus_chapitre: float | None = None

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

    #: Pas de périmètre décidable non plus, et mesuré de même. Le vote par
    #: chapitre, qui donne 5,7 % de faux rejets sous BGE-M3, en donne **40 %**
    #: ici au même réglage (0,8) : deux questions couvertes sur cinq seraient
    #: déclarées hors programme. Le consensus de chapitre suppose une proximité
    #: de sens ; un hachage de n-grammes n'en produit pas, il éparpille les
    #: résultats d'une question couverte comme ceux d'une question étrangère.
    consensus_chapitre = None

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

    Le score **lexical** avait un temps paru séparer (0,1402 contre 0,2105).
    Remesuré sur un jeu élargi — 35 questions couvertes contre 18 étrangères,
    sur les 12 leçons — il ne sépare pas davantage : marge −0,024. La première
    mesure portait sur trop peu de points, ce que CLAUDE.md avertissait.

    Le périmètre est donc décidé par ``consensus_chapitre`` et non par un
    seuil scalaire. Cf. `qa/qa_status.json` #5.
    """

    #: Mesuré sur les 12 leçons (216 chunks) : à 0,8 — soit 4 résultats sur 5
    #: portés par un même chapitre — 5,7 % de faux rejets sur 35 questions
    #: couvertes et 16,7 % de faux services sur 18 questions étrangères. Aucun
    #: plancher de cosinus ajouté à ce vote n'améliore le compromis : jusqu'à
    #: 0,45 il ne retire rien, et à 0,50 il coûte plus de faux rejets qu'il
    #: n'évite de faux services.
    #:
    #: Les trois fixtures qui arbitrent tombent du bon côté : le prompt exact du
    #: cas #5 est servi (les suites SONT indexées — le défaut rapporté venait
    #: d'un index incomplet), et les fixtures positives #54/#55, sur les
    #: dérivées, sortent hors périmètre, ce que la décision D6 attend pour
    #: divulguer sans refuser.
    consensus_chapitre = 0.8

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
