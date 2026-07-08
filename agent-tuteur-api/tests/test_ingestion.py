from agent_tuteur.ingestion.annotation import parse_frontmatter
from agent_tuteur.ingestion.pipeline import process_document


def test_frontmatter_parsed_and_stripped():
    text = "---\nniveau: moyen\ndiscipline: Maths\n---\n## Titre\n\ncorps\n"
    meta, body = parse_frontmatter(text)
    assert meta == {"niveau": "moyen", "discipline": "Maths"}
    assert body.startswith("## Titre")


def test_process_markdown_document_annotates_chunks():
    data = (
        "---\nniveau: secondaire\nclasse: Terminale\nserie: S1\n"
        "discipline: Mathématiques\n---\n"
        "## Compétence : Dériver\n\ncontenu\n\n### Exercice 1\n\nénoncé indice solution\n"
    ).encode("utf-8")
    result = process_document("cours.md", data)
    assert result.doc_type == "markdown"
    assert result.n_chunks == 2
    for chunk in result.chunks:
        assert chunk.metadata.serie == "S1"
        assert chunk.metadata.serie_alias == ["S1"]
        assert chunk.metadata.source_document == "cours.md"
        assert chunk.metadata.examen_associe == "Baccalauréat"
    # ids uniques et déterministes.
    assert len({c.id for c in result.chunks}) == result.n_chunks


def test_form_metadata_overrides_frontmatter():
    data = b"---\nniveau: moyen\ndiscipline: Maths\n---\n## Titre\n\ncorps\n"
    result = process_document("x.md", data, form_metadata={"discipline": "Physique-Chimie"})
    assert result.chunks[0].metadata.discipline == "Physique-Chimie"


def test_txt_document_supported():
    result = process_document("notes.txt", b"Juste du texte brut sans structure.")
    assert result.doc_type == "txt"
    assert result.n_chunks == 1


def test_process_document_records_timed_steps():
    data = b"## Chapitre : Test\n\ncontenu\n\n### Exercice 1\n\nenonce indice solution\n"
    result = process_document("cours.md", data, document_id="doc-123")
    step_names = [s["step"] for s in result.steps]
    assert step_names == ["extract", "normalize", "chunk", "annotate"]
    for step in result.steps:
        assert step["duration_ms"] >= 0
    # Détails spécifiques à chaque étape.
    assert result.steps[0]["doc_type"] == "markdown"
    assert result.steps[2]["n_drafts"] == 2
    assert result.steps[3]["n_chunks"] == 2
