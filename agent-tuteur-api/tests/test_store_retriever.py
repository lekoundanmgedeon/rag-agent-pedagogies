from agent_tuteur.vectorstore.retriever import build_filters


def test_hybrid_retrieval_surfaces_relevant_chunk(rag_stack):
    results = rag_stack.retriever.retrieve(
        "comment dériver un quotient de deux fonctions",
        {"serie": "S1", "discipline": "Mathématiques"},
    )
    assert results
    assert results[0].chunk.metadata.source_document == "maths_ts1_derivees.md"
    # Scores hybrides exposés pour la transparence.
    assert results[0].dense_score is not None
    assert results[0].sparse_score is not None


def test_serie_alias_expansion_matches(rag_stack):
    # Question en nouvelle nomenclature « STIDD1 » doit atteindre du « T1 ».
    results = rag_stack.retriever.retrieve(
        "calcul de la moyenne et de l'écart-type", {"serie": "STIDD1"}
    )
    assert results
    assert all(r.chunk.metadata.serie == "T1" for r in results)


def test_metadata_filter_restricts_scope(rag_stack):
    # Filtrer sur la physique-chimie ne doit jamais remonter de maths.
    results = rag_stack.retriever.retrieve(
        "poids et masse", {"discipline": "Physique-Chimie"}
    )
    assert results
    assert all(r.chunk.metadata.discipline == "Physique-Chimie" for r in results)


def test_filter_with_no_match_returns_empty(rag_stack):
    results = rag_stack.retriever.retrieve("quoi que ce soit", {"serie": "S5"})
    assert results == []


def test_build_filters_expands_serie_and_ignores_unindexed():
    filters = build_filters(
        {"serie": "STEG", "discipline": "Maths", "student_id": "x", "competence": "y"}
    )
    assert set(filters["serie"]) == {"G", "STEG"}
    assert filters["discipline"] == ["Maths"]
    # competence n'est pas un champ indexé -> ignoré du filtrage.
    assert "competence" not in filters
    assert "student_id" not in filters
