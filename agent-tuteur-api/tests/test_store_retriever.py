import pytest

from agent_tuteur.config.taxonomy import taxonomy_key
from agent_tuteur.domain.models import CurriculumMetadata
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
    # La discipline est réduite à sa clé de filtrage (confrontée à discipline_key).
    assert filters["discipline"] == ["MATHS"]
    # competence n'est pas un champ indexé -> ignoré du filtrage.
    assert "competence" not in filters
    assert "student_id" not in filters


def test_count_for_source_matches_only_that_document(rag_stack):
    indexer = rag_stack.indexer
    assert indexer.count_for_source("maths_ts1_derivees.md") > 0
    assert indexer.count_for_source("document_qui_n_existe_pas.md") == 0


def test_count_for_source_sums_to_total_count(rag_stack):
    # Chaque chunk appartient à exactement un document -> la somme par source
    # doit reconstituer le total (pas de double-comptage, pas d'oubli).
    from pathlib import Path

    total = 0
    for path in sorted((Path(__file__).resolve().parents[1] / "corpus").glob("*.md")):
        total += rag_stack.indexer.count_for_source(path.name)
    assert total == rag_stack.indexer.count()


# --- Robustesse orthographique du filtrage curriculaire ----------------------


@pytest.mark.parametrize(
    "saisi, indexe",
    [
        ("Mathematiques", "Mathématiques"),   # accent manquant côté élève
        ("Mathématiques", "Mathematiques"),   # accent manquant côté corpus
        ("MATHEMATIQUES", "Mathématiques"),   # casse
        ("Sciences  Physiques", "Sciences Physiques"),  # espaces surnuméraires
    ],
)
def test_taxonomy_key_unifies_spelling_variants(saisi, indexe):
    assert taxonomy_key(saisi) == taxonomy_key(indexe)


@pytest.mark.parametrize(
    "avec, sans",
    [
        ("Les Suites Numériques", "Suites Numeriques"),
        ("Le Calcul Intégral", "Calcul Integral"),
        ("L'Arithmétique", "Arithmetique"),
    ],
)
def test_taxonomy_key_ignores_leading_article(avec, sans):
    assert taxonomy_key(avec) == taxonomy_key(sans)


def test_taxonomy_key_keeps_words_that_merely_start_like_an_article():
    """« Deuxième degré » ne doit pas perdre son « De » initial."""
    assert taxonomy_key("Deuxième degré") == "DEUXIEMEDEGRE"
    assert taxonomy_key("Dérivées") == "DERIVEES"


def test_metadata_derives_filter_keys():
    meta = CurriculumMetadata(
        niveau="secondaire", classe="Terminale",
        discipline="Mathématiques", chapitre="Les Suites Numériques",
    )
    assert meta.discipline_key == "MATHEMATIQUES"
    assert meta.chapitre_key == "SUITESNUMERIQUES"
    # Le libellé affiché n'est jamais altéré.
    assert meta.chapitre == "Les Suites Numériques"


def test_filter_matches_across_accent_variants(rag_stack):
    """Régression : un accent de différence coupait l'élève du corpus."""
    accentue = rag_stack.retriever.retrieve("dérivée", {"discipline": "Mathématiques"}, top_k=10)
    nu = rag_stack.retriever.retrieve("dérivée", {"discipline": "Mathematiques"}, top_k=10)
    assert accentue and nu
    assert [sc.chunk.id for sc in accentue] == [sc.chunk.id for sc in nu]
