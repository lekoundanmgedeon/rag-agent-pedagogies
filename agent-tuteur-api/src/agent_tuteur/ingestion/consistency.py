"""Vérifie la cohérence entre le statut persisté d'un document (``indexed``)
et la présence réelle de ses chunks dans le vectorstore.

Un document peut devenir **orphelin** : marqué ``indexed`` en base (l'ingestion
a réellement réussi au moment où elle a eu lieu) mais dont les vecteurs ont
depuis disparu du store actif — typiquement après un changement de
``VECTOR_BACKEND`` en cours de route, le redémarrage d'un processus utilisant
le backend ``memory`` (store perdu avec le processus), ou une réinitialisation
du serveur Qdrant. Le statut ``indexed`` ment alors par accident : plus aucune
recherche ne pourra jamais retrouver ce document.

Ce module ne modifie rien par lui-même : il constate l'écart. L'appelant
(``api/routes/documents.py::verify_all_documents``) décide de marquer le
document ``orphaned`` en conséquence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from agent_tuteur.observability import get_logger, log_event
from agent_tuteur.persistence.models import Document
from agent_tuteur.vectorstore.indexer import Indexer

_logger = get_logger("agent_tuteur.ingestion.consistency")


@dataclass
class DocumentConsistency:
    document_id: str
    filename: str
    status: str
    chunks_in_store: int
    consistent: bool


def check_document_consistency(document: Document, indexer: Indexer) -> DocumentConsistency:
    """Vérifie un document. Seul un statut ``indexed`` peut être incohérent —
    un document ``pending``/``failed``/``orphaned`` n'est pas censé avoir de
    chunks exploitables, donc rien à contrôler pour lui."""
    if document.status != "indexed":
        return DocumentConsistency(
            document_id=document.id,
            filename=document.filename,
            status=document.status,
            chunks_in_store=0,
            consistent=True,
        )

    count = indexer.count_for_source(document.filename)
    consistent = count > 0
    if not consistent:
        log_event(
            _logger,
            "consistency:orphaned_document_detected",
            log_level=logging.WARNING,
            document_id=document.id,
            filename=document.filename,
        )
    return DocumentConsistency(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        chunks_in_store=count,
        consistent=consistent,
    )


def check_documents_consistency(documents: list[Document], indexer: Indexer) -> list[DocumentConsistency]:
    """Vérifie une liste de documents (typiquement tous ceux d'un tenant)."""
    return [check_document_consistency(d, indexer) for d in documents]
