"""Re-ranker pédagogique : le cours d'abord, les compléments sous quota.

Porté de l'idée de `search_course_first` (NURU), posé **au-dessus** du
classement RRF existant et non à sa place.
"""

import pytest

from agent_tuteur.config.taxonomy import TypeChunk, est_chunk_de_cours
from agent_tuteur.domain.models import Chunk, CurriculumMetadata, ScoredChunk
from agent_tuteur.vectorstore.retriever import HybridRetriever, ResultatsPedagogiques


# --- Classement d'un chunk : cours ou complément ? ---------------------------


def test_un_chapitre_est_du_cours():
    assert est_chunk_de_cours(TypeChunk.CHAPITRE.value, "cours") is True


def test_un_exercice_n_est_jamais_du_cours():
    assert est_chunk_de_cours(TypeChunk.EXERCICE.value, "cours") is False


@pytest.mark.parametrize("nature", ["td", "exercices", "annales", "devoir", "corrigé"])
def test_un_document_de_td_ne_fournit_jamais_de_cours(nature):
    """Même quand le découpage produit des sections d'allure théorique.

    C'est le cas fréquent des « rappels de cours » en tête de TD : ils sont
    découpés en sous-notions, mais restent des compléments.
    """
    assert est_chunk_de_cours(TypeChunk.SOUS_NOTION.value, nature) is False


def test_une_sous_notion_d_un_cours_est_du_cours():
    assert est_chunk_de_cours(TypeChunk.SOUS_NOTION.value, "cours") is True


def test_la_nature_du_document_est_insensible_a_la_casse():
    assert est_chunk_de_cours(TypeChunk.CHAPITRE.value, "  TD ") is False


# --- Partition des résultats de recherche ------------------------------------


class _StoreFactice:
    """Store qui renvoie une liste figée, pour tester la partition seule."""

    def __init__(self, resultats):
        self._resultats = resultats
        self.dernier_top_k = None

    def search(self, query_emb, top_k, filters):
        self.dernier_top_k = top_k
        return self._resultats[:top_k]


class _EmbedderFactice:
    def embed_query(self, query):
        return [0.0]


def _chunk(identifiant, type_chunk, type_document, score):
    return ScoredChunk(
        chunk=Chunk(
            id=identifiant,
            text=f"texte {identifiant}",
            metadata=CurriculumMetadata(
                niveau="secondaire", type_chunk=type_chunk, type_document=type_document
            ),
        ),
        score=score,
    )


def _retriever(resultats, top_k=3):
    store = _StoreFactice(resultats)
    return HybridRetriever(_EmbedderFactice(), store, top_k=top_k), store


def test_le_cours_passe_devant_meme_classe_dernier_par_le_rrf():
    """Le cas qui motive tout le module : 4 TD mieux classés qu'un cours."""
    resultats = [
        _chunk("td-1", TypeChunk.EXERCICE.value, "td", 0.9),
        _chunk("td-2", TypeChunk.EXERCICE.value, "td", 0.8),
        _chunk("td-3", TypeChunk.EXERCICE.value, "td", 0.7),
        _chunk("td-4", TypeChunk.EXERCICE.value, "td", 0.6),
        _chunk("cours-1", TypeChunk.CHAPITRE.value, "cours", 0.5),
    ]
    retriever, _ = _retriever(resultats)
    r = retriever.retrieve_course_first("explique-moi les probabilités")

    assert r.a_du_cours is True
    assert [sc.chunk.id for sc in r.cours] == ["cours-1"]
    assert r.tous()[0].chunk.id == "cours-1"       # le cours est en tête
    assert len(r.complements) == 2                  # quota respecté


def test_l_ordre_du_rrf_est_conserve_a_l_interieur_de_chaque_groupe():
    """On partitionne, on ne recalcule aucun score."""
    resultats = [
        _chunk("cours-a", TypeChunk.CHAPITRE.value, "cours", 0.9),
        _chunk("td-1", TypeChunk.EXERCICE.value, "td", 0.85),
        _chunk("cours-b", TypeChunk.SOUS_NOTION.value, "cours", 0.8),
        _chunk("td-2", TypeChunk.EXERCICE.value, "td", 0.7),
    ]
    retriever, _ = _retriever(resultats)
    r = retriever.retrieve_course_first("q")

    assert [sc.chunk.id for sc in r.cours] == ["cours-a", "cours-b"]
    assert [sc.chunk.id for sc in r.complements] == ["td-1", "td-2"]


def test_sans_aucun_cours_le_drapeau_le_signale():
    """C'est ce drapeau qui déclenche l'aveu au lieu de l'invention."""
    resultats = [
        _chunk("td-1", TypeChunk.EXERCICE.value, "td", 0.9),
        _chunk("td-2", TypeChunk.EXERCICE.value, "td", 0.8),
    ]
    retriever, _ = _retriever(resultats)
    r = retriever.retrieve_course_first("q")

    assert r.a_du_cours is False
    assert r.cours == []
    assert len(r.complements) == 2


def test_le_vivier_est_sur_echantillonne_avant_partition():
    """Sans sur-échantillonnage, la partition n'aurait rien à répartir."""
    retriever, store = _retriever([], top_k=5)
    retriever.retrieve_course_first("q")
    assert store.dernier_top_k == 20   # 5 × 4


def test_le_quota_de_complements_est_reglable():
    resultats = [_chunk(f"td-{i}", TypeChunk.EXERCICE.value, "td", 0.9) for i in range(6)]
    retriever, _ = _retriever(resultats)
    assert len(retriever.retrieve_course_first("q", quota_complements=4).complements) == 4


def test_resultats_vides():
    retriever, _ = _retriever([])
    r = retriever.retrieve_course_first("q")
    assert r == ResultatsPedagogiques(cours=[], complements=[])
    assert r.a_du_cours is False
