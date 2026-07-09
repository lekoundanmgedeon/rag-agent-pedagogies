from dataclasses import dataclass

from agent_tuteur.ingestion.consistency import check_document_consistency, check_documents_consistency
from agent_tuteur.vectorstore.embeddings import build_embedder
from agent_tuteur.vectorstore.indexer import Indexer
from agent_tuteur.vectorstore.store import build_vector_store


@dataclass
class _FakeDocument:
    id: str
    filename: str
    status: str


def _empty_indexer() -> Indexer:
    return Indexer(build_embedder("light", 64), build_vector_store("memory"))


def test_non_indexed_document_is_always_consistent():
    doc = _FakeDocument(id="1", filename="x.md", status="pending")
    result = check_document_consistency(doc, _empty_indexer())
    assert result.consistent is True
    assert result.chunks_in_store == 0


def test_indexed_document_with_no_chunks_in_store_is_orphaned():
    # Reproduit exactement le bug diagnostiqué : statut "indexed" persisté,
    # mais le store actuel (vide, ex. après un changement de VECTOR_BACKEND ou
    # un redémarrage) ne contient plus aucun chunk pour ce document.
    doc = _FakeDocument(id="1", filename="cours_disparu.md", status="indexed")
    result = check_document_consistency(doc, _empty_indexer())
    assert result.consistent is False
    assert result.chunks_in_store == 0
    assert result.document_id == "1"
    assert result.filename == "cours_disparu.md"


def test_indexed_document_with_chunks_present_is_consistent(rag_stack):
    doc = _FakeDocument(id="1", filename="maths_ts1_derivees.md", status="indexed")
    result = check_document_consistency(doc, rag_stack.indexer)
    assert result.consistent is True
    assert result.chunks_in_store > 0


def test_check_documents_consistency_filters_only_orphaned(rag_stack):
    docs = [
        _FakeDocument(id="1", filename="maths_ts1_derivees.md", status="indexed"),  # présent
        _FakeDocument(id="2", filename="disparu.md", status="indexed"),  # orphelin
        _FakeDocument(id="3", filename="en_cours.pdf", status="pending"),  # non concerné
    ]
    results = check_documents_consistency(docs, rag_stack.indexer)
    by_id = {r.document_id: r for r in results}
    assert by_id["1"].consistent is True
    assert by_id["2"].consistent is False
    assert by_id["3"].consistent is True
