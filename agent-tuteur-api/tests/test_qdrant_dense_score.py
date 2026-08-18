"""Câblage de ``dense_score`` sur le backend Qdrant.

``ScoredChunk.dense_score`` existait comme champ depuis l'origine mais n'était
jamais renseigné par ``QdrantVectorStore`` : la recherche interroge Qdrant avec
``FusionQuery(RRF)``, si bien que ``point.score`` est un score de **rang**
(~1/(k+rang)) et non une similarité. C'est la raison technique pour laquelle
aucun seuil de pertinence n'était posable (cas QA #5, décision D3) — mesuré sur
ce dépôt, un résultat hors périmètre obtenait 0,0325 en RRF, au-dessus d'un
témoin dans le périmètre à 0,0318.

Ces tests n'ont pas besoin d'un serveur : ils substituent un client factice au
client Qdrant et vérifient la logique d'appariement, qui est tout ce que ce
dépôt contrôle. Ce qu'ils ne peuvent pas prouver — que Qdrant renvoie bien un
cosinus — tient à la configuration de la collection (``Distance.COSINE``), et
relève d'un test d'intégration sur la pile réelle.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field

import numpy as np
import pytest

from agent_tuteur.vectorstore.embeddings import Embedding
from agent_tuteur.vectorstore.qdrant_store import QdrantVectorStore


@dataclass
class _Point:
    id: object
    score: float
    payload: dict | None = None


@dataclass
class _Reponse:
    points: list[_Point]


@dataclass
class _ClientFactice:
    """Rend les réponses préparées, dans l'ordre, en enregistrant les appels."""

    reponses: list[_Reponse]
    appels: list[dict] = field(default_factory=list)

    def query_points(self, **kwargs):
        self.appels.append(kwargs)
        return self.reponses[len(self.appels) - 1]


def _store(reponses: list[_Reponse]) -> QdrantVectorStore:
    """Instancie sans ``__init__`` : celui-ci ouvre une connexion réelle."""
    store = object.__new__(QdrantVectorStore)
    store._client = _ClientFactice(reponses)
    store._collection = "curriculum"
    store._dense_dim = 4
    store._rrf_k = 60
    return store


def _requete() -> Embedding:
    return Embedding(dense=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32), sparse={7: 1.0})


def _payload(nom: str) -> dict:
    return {
        "text": f"contenu {nom}",
        "chunk_id": nom,
        "niveau": "Terminale",
        "chapitre": "Les Nombres Complexes",
    }


def test_le_cosinus_est_attache_a_chaque_resultat():
    fusion = _Reponse([
        _Point(id=1, score=0.0325, payload=_payload("a")),
        _Point(id=2, score=0.0318, payload=_payload("b")),
    ])
    dense = _Reponse([_Point(id=1, score=0.83), _Point(id=2, score=0.21)])
    store = _store([fusion, dense])

    resultats = store.search(_requete(), top_k=2)

    assert [sc.dense_score for sc in resultats] == [0.83, 0.21]
    # Le score RRF reste rendu tel quel : on ajoute une mesure, on n'en remplace pas.
    assert [sc.score for sc in resultats] == [0.0325, 0.0318]


def test_le_cosinus_discrimine_la_ou_le_rrf_ne_discrimine_pas():
    """Le cas QA #5 en miniature : deux RRF voisins, deux cosinus opposés."""
    fusion = _Reponse([
        _Point(id="hors", score=0.0325, payload=_payload("hors")),
        _Point(id="dans", score=0.0318, payload=_payload("dans")),
    ])
    dense = _Reponse([_Point(id="dans", score=0.71), _Point(id="hors", score=0.09)])
    store = _store([fusion, dense])

    par_id = {sc.chunk.id: sc for sc in store.search(_requete(), top_k=2)}

    assert par_id["hors"].score > par_id["dans"].score          # RRF : trompeur
    assert par_id["hors"].dense_score < par_id["dans"].dense_score   # cosinus : correct


def test_un_point_absent_de_la_reponse_dense_vaut_none_et_non_zero():
    """« Inconnu » et « orthogonal » ne sont pas la même chose.

    Les confondre ferait rejeter à tort un chunk par un futur seuil, ce qui est
    exactement le risque que le cas #6 matérialise dans l'autre sens.
    """
    fusion = _Reponse([
        _Point(id=1, score=0.03, payload=_payload("a")),
        _Point(id=2, score=0.02, payload=_payload("b")),
    ])
    store = _store([fusion, _Reponse([_Point(id=1, score=0.5)])])

    resultats = store.search(_requete(), top_k=2)

    assert resultats[0].dense_score == 0.5
    assert resultats[1].dense_score is None


def test_la_seconde_requete_est_dense_pure_et_restreinte_aux_resultats():
    """Un aller-retour, pas un second classement."""
    fusion = _Reponse([_Point(id=11, score=0.03, payload=_payload("a"))])
    store = _store([fusion, _Reponse([_Point(id=11, score=0.6)])])

    store.search(_requete(), top_k=5)

    appel = store._client.appels[1]
    assert appel["using"] == QdrantVectorStore.DENSE
    assert appel["limit"] == 1, "la limite suit les résultats retenus, pas top_k"
    assert appel["with_payload"] is False, "le payload est déjà connu du premier appel"
    assert "prefetch" not in appel, "la seconde requête ne doit pas refusionner"


def test_aucun_appel_supplementaire_quand_la_fusion_ne_rend_rien():
    store = _store([_Reponse([])])

    assert store.search(_requete(), top_k=5) == []
    assert len(store._client.appels) == 1


@pytest.mark.parametrize("filtres", [None, {"serie": ["S2"]}])
def test_le_filtre_curriculaire_est_conserve_sur_la_seconde_requete(filtres):
    """Sans lui, le cosinus pourrait être lu sur un point hors périmètre élève."""
    fusion = _Reponse([_Point(id=3, score=0.03, payload=_payload("a"))])
    store = _store([fusion, _Reponse([_Point(id=3, score=0.4)])])

    store.search(_requete(), top_k=5, filters=filtres)

    assert store._client.appels[1]["query_filter"] is not None


def test_les_appels_respectent_la_signature_du_vrai_client():
    """Garde-fou : le client factice accepte ``**kwargs``, le vrai non.

    ``query_points`` nomme son filtre ``query_filter`` ; un ``filter`` y part
    dans ``**kwargs``, que le client réel refuse par une assertion. Les tests
    ci-dessus ne pouvaient pas le voir — leur double est plus permissif que le
    vrai client. Résultat en production : toute recherche filtrée levait, le
    nœud ``retrieve_context`` échouait, et le flux SSE du chat se coupait sans
    jamais émettre ``done`` — l'élève n'avait qu'un chargement sans fin.

    On confronte donc les appels réellement émis à la signature du vrai client.
    """
    qdrant_client = pytest.importorskip("qdrant_client")

    fusion = _Reponse([_Point(id=3, score=0.03, payload=_payload("a"))])
    store = _store([fusion, _Reponse([_Point(id=3, score=0.4)])])
    store.search(_requete(), top_k=5, filters={"serie": ["S2"]})

    attendus = set(
        inspect.signature(qdrant_client.QdrantClient.query_points).parameters
    ) - {"self", "kwargs"}
    for appel in store._client.appels:
        inconnus = set(appel) - attendus
        assert not inconnus, f"arguments inconnus de query_points : {sorted(inconnus)}"
