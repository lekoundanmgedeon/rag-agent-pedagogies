from agent_tuteur.config.taxonomy import TypeChunk
from agent_tuteur.ingestion.chunking import chunk_document

MARKDOWN = """## Compétence : Faire quelque chose

Contenu de la compétence.

## Chapitre : Un chapitre

Contenu du chapitre.

### Exercice 1 : Un exercice

**Énoncé.** Résoudre le problème.

**Indice.** Pense à la méthode.

**Solution.** La réponse est 42.
"""


def test_markers_produce_expected_types():
    drafts = chunk_document(MARKDOWN)
    types = [d.type_chunk for d in drafts]
    assert types == [
        TypeChunk.COMPETENCE_COMPLETE.value,
        TypeChunk.CHAPITRE.value,
        TypeChunk.EXERCICE.value,
    ]


def test_exercise_is_indivisible():
    # L'énoncé, l'indice et la solution doivent rester dans le MÊME chunk.
    drafts = chunk_document(MARKDOWN)
    exercice = next(d for d in drafts if d.type_chunk == TypeChunk.EXERCICE.value)
    assert "Énoncé" in exercice.text
    assert "Indice" in exercice.text
    assert "Solution" in exercice.text
    assert "42" in exercice.text


def test_subsection_non_exercise_stays_in_parent():
    text = "## Chapitre : Titre\n\nintro\n\n### Une sous-notion\n\ndétails\n"
    drafts = chunk_document(text)
    # Un ### non-exercice ne crée pas de nouveau chunk : reste dans le chapitre.
    assert len(drafts) == 1
    assert "sous-notion" in drafts[0].text


def test_heuristic_fallback_without_markers():
    # Texte « PDF » sans dièses : découpe heuristique sur titres numérotés.
    text = (
        "Introduction générale du document.\n"
        "1. Première partie\ncontenu un\n"
        "2. Deuxième partie\ncontenu deux\n"
    )
    drafts = chunk_document(text)
    assert len(drafts) >= 2


def test_single_chunk_when_no_structure():
    drafts = chunk_document("Juste un paragraphe sans aucun titre ni marqueur.")
    assert len(drafts) == 1
