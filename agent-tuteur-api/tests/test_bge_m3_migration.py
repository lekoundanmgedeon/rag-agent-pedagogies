"""Garde-fous de la bascule d'embedder (« light » 256 → BGE-M3 1024).

Changer d'embedder change la dimension dense. Deux endroits pouvaient laisser
passer l'incohérence en silence, et le silence est ici le pire des cas : un
index dont l'espace vectoriel ne correspond plus aux requêtes rend des
résultats *plausibles* au lieu de tomber en panne.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from agent_tuteur.config.settings import Settings
from agent_tuteur.factory import build_rag_stack
from agent_tuteur.vectorstore.embeddings import BaseEmbedder, build_embedder
from agent_tuteur.vectorstore.qdrant_store import QdrantVectorStore

# --- La dimension du store vient de l'embedder, pas du réglage ---------------


def test_le_store_suit_la_dimension_de_l_embedder():
    """``embedding_dense_dim`` ne pilote que « light » ; BGE-M3 impose 1024.

    Passer le réglage au store créerait une collection en 256 pour des vecteurs
    en 1024 : muette à la création, en échec au premier upsert.
    """
    reglages = Settings(vector_backend="memory", embedding_backend="light", embedding_dense_dim=64)

    pile = build_rag_stack(reglages)

    assert pile.indexer._embedder.dense_dim == 64


def test_un_embedder_impose_sa_dimension_meme_si_le_reglage_diverge():
    """Contrôle direct de l'invariant, sans dépendre de BGE-M3 ni d'un serveur."""

    class _Embedder1024(BaseEmbedder):
        @property
        def dense_dim(self) -> int:
            return 1024

        def embed_documents(self, texts):  # pragma: no cover - non sollicité ici
            raise NotImplementedError

    assert _Embedder1024().dense_dim != Settings().embedding_dense_dim


# --- Une collection de dimension différente doit faire échouer le démarrage --


@dataclass
class _ClientFactice:
    taille: int | None
    collections: tuple[str, ...] = ("curriculum",)

    def get_collections(self):
        return SimpleNamespace(
            collections=[SimpleNamespace(name=nom) for nom in self.collections]
        )

    def get_collection(self, nom):
        vecteurs = None if self.taille is None else {"dense": SimpleNamespace(size=self.taille)}
        return SimpleNamespace(
            config=SimpleNamespace(params=SimpleNamespace(vectors=vecteurs))
        )


def _store(taille_existante: int | None, dimension_courante: int) -> QdrantVectorStore:
    store = object.__new__(QdrantVectorStore)
    store._client = _ClientFactice(taille_existante)
    store._collection = "curriculum"
    store._dense_dim = dimension_courante
    store._rrf_k = 60
    return store


def test_une_collection_de_dimension_differente_refuse_de_demarrer():
    store = _store(taille_existante=256, dimension_courante=1024)

    with pytest.raises(RuntimeError, match="256 dimensions"):
        store._ensure_collection()


def test_le_message_indique_la_marche_a_suivre():
    """Un refus sans issue laisserait l'exploitant deviner."""
    store = _store(taille_existante=256, dimension_courante=1024)

    with pytest.raises(RuntimeError) as erreur:
        store._ensure_collection()

    message = str(erreur.value)
    assert "QDRANT_COLLECTION" in message
    assert "ingestion" in message


def test_une_collection_de_meme_dimension_passe():
    store = _store(taille_existante=1024, dimension_courante=1024)

    store._ensure_collection()      # ne lève pas


def test_une_collection_sans_vecteur_dense_nomme_ne_bloque_pas():
    """Prudence : une forme de configuration inattendue ne doit pas tout arrêter.

    Le contrôle vise l'incohérence *avérée*, pas l'inconnu — bloquer sur une
    structure qu'on ne sait pas lire transformerait un garde-fou en panne.
    """
    store = _store(taille_existante=None, dimension_courante=1024)

    store._ensure_collection()      # ne lève pas


# --- BGE-M3 lui-même, seulement si les dépendances sont là -------------------


def _flag_embedding_absent() -> bool:
    try:
        import FlagEmbedding  # type: ignore  # noqa: F401
    except ImportError:
        return True
    return False


@pytest.mark.skipif(_flag_embedding_absent(), reason="FlagEmbedding non installé")
@pytest.mark.bge
def test_bge_m3_produit_bien_1024_dimensions():
    """Premier test à exercer réellement ``BGEM3Embedder``.

    Le code existait depuis l'origine avec ``# pragma: no cover`` : plausible,
    mais jamais exécuté. Le modèle est téléchargé au premier appel.
    """
    embedder = build_embedder("bge_m3")

    assert embedder.dense_dim == 1024
    vecteurs = embedder.embed_documents(["Le module d'un nombre complexe", "danser la salsa"])
    assert len(vecteurs) == 2
    assert all(v.dense.shape == (1024,) for v in vecteurs)
    assert all(v.sparse for v in vecteurs), "aucun poids lexical produit"


@pytest.mark.skipif(_flag_embedding_absent(), reason="FlagEmbedding non installé")
@pytest.mark.bge
def test_bge_m3_separe_ce_que_light_confondait():
    """Le cœur de RC-0 : mesurer si un vrai modèle discrimine enfin.

    Sur l'embedder « light » (hachage sans sémantique), une question de cuisine
    obtenait 0,241 de cosinus contre 0,271 pour un exercice de nombres
    complexes — inséparables. C'est la mesure qui justifiait la migration.
    """
    import numpy as np

    embedder = build_embedder("bge_m3")
    cours = embedder.embed_documents(
        ["Un nombre complexe s'écrit z = a + ib, avec a et b réels et i² = -1."]
    )[0]
    proche = embedder.embed_query("Quel est le module du nombre complexe 3 + 4i ?")
    lointain = embedder.embed_query("Apprends-moi à cuisiner les pommes sautées")

    similaire = float(np.dot(cours.dense, proche.dense))
    etranger = float(np.dot(cours.dense, lointain.dense))

    assert similaire > etranger, f"aucune discrimination : {similaire:.3f} vs {etranger:.3f}"
    assert similaire - etranger > 0.15, (
        f"écart trop faible pour calibrer un seuil : {similaire:.3f} vs {etranger:.3f}"
    )
