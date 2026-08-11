"""Fixtures du rejeu QA.

Deux couches de test coexistent ici (cf. la note d'approche) :

* **couche A** — déterministe, hors-ligne, bloquante : ``MockLLM`` + store
  mémoire. On y assère les *décisions du pipeline* (intention, nœuds traversés,
  scores de retrieval, outil routé, texte des réponses court-circuitées), jamais
  la prose du modèle, qui est figée en mode mock ;
* **couche B** — LLM réel, marquée ``@pytest.mark.llm``, ignorée sauf si
  ``QA_LLM=1``. Même patron de saut conditionnel que la fixture
  ``postgres_engine`` du conftest parent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pytest

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.agent.llm.mock import MockLLM
from agent_tuteur.agent.ports import InMemoryAuditLog, InMemoryStudentMemory
from agent_tuteur.ingestion.pipeline import ingest_and_index
from agent_tuteur.vectorstore.embeddings import build_embedder
from agent_tuteur.vectorstore.indexer import Indexer
from agent_tuteur.vectorstore.retriever import HybridRetriever
from agent_tuteur.vectorstore.store import build_vector_store

from .cas import CORPUS_QA


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "llm: rejeu contre un vrai fournisseur LLM (couche B, QA_LLM=1)"
    )


def pytest_collection_modifyitems(config, items):
    if os.environ.get("QA_LLM") == "1":
        return
    saut = pytest.mark.skip(reason="couche B : LLM réel non sollicité (poser QA_LLM=1)")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(saut)


@dataclass
class PileQA:
    store: object
    retriever: HybridRetriever


@pytest.fixture(scope="session")
def pile_qa() -> PileQA:
    """Index figé de la démo (2 chapitres) — partagé, car en lecture seule."""
    embedder = build_embedder("light", dense_dim=256)
    store = build_vector_store("memory", rrf_k=60)
    indexer = Indexer(embedder, store)
    for chemin in sorted(CORPUS_QA.glob("*.md")):
        ingest_and_index(chemin.name, chemin.read_bytes(), indexer)
    return PileQA(store=store, retriever=HybridRetriever(embedder, store, top_k=5))


@pytest.fixture
def agent_qa(pile_qa: PileQA) -> TutorAgent:
    """Agent hors-ligne monté sur l'index de la démo."""
    return TutorAgent(
        pile_qa.retriever,
        MockLLM(),
        memory=InMemoryStudentMemory(),
        audit=InMemoryAuditLog(),
        top_k=5,
    )


@pytest.fixture
def session_eleve() -> SessionState:
    return SessionState(student_id="eleve-qa", tenant_id="qa")
