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
from agent_tuteur.agent.llm.base import BaseLLM
from agent_tuteur.agent.llm.mock import MockLLM
from agent_tuteur.agent.ports import InMemoryAuditLog, InMemoryStudentMemory
from agent_tuteur.factory import build_llm
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


# --- Même corpus figé, mais encodé par l'embedder de production --------------
# Le seuil de pertinence (cas #5) est une propriété de l'espace vectoriel :
# « light » n'en admet aucun (mesuré — les questions couvertes et les questions
# étrangères s'y recouvrent), donc un cas qui en dépend ne peut pas être jugé
# sur la pile hors-ligne. Ces fixtures rejouent le même corpus avec BGE-M3.
#
# Coût assumé : l'encodage des 36 chunks prend plusieurs minutes sur CPU. D'où
# la portée « session » et le marqueur ``bge``, qui garde la suite ordinaire
# rapide et exécutable sans FlagEmbedding.


@pytest.fixture(scope="session")
def pile_qa_bge() -> PileQA:
    try:
        import FlagEmbedding  # type: ignore  # noqa: F401
    except ImportError:
        pytest.skip("FlagEmbedding non installé : cas jugés sur BGE-M3 ignorés")
    embedder = build_embedder("bge_m3")
    store = build_vector_store("memory", rrf_k=60)
    indexer = Indexer(embedder, store)
    for chemin in sorted(CORPUS_QA.glob("*.md")):
        ingest_and_index(chemin.name, chemin.read_bytes(), indexer)
    return PileQA(store=store, retriever=HybridRetriever(embedder, store, top_k=5))


@pytest.fixture
def agent_qa_bge(pile_qa_bge: PileQA) -> TutorAgent:
    """Agent hors-ligne, seuil de pertinence actif (embedder de production)."""
    return TutorAgent(
        pile_qa_bge.retriever,
        MockLLM(),
        memory=InMemoryStudentMemory(),
        audit=InMemoryAuditLog(),
        top_k=5,
    )


@pytest.fixture
def session_eleve() -> SessionState:
    return SessionState(student_id="eleve-qa", tenant_id="qa")


# --- Couche B : mêmes prompts, fournisseur LLM réel --------------------------
@pytest.fixture
def routeur_llm() -> BaseLLM:
    """Chaîne LLM réelle, composée comme en production (``factory.build_llm``).

    Volontairement construite par la fabrique de l'application plutôt qu'à la
    main : la couche B doit interroger le modèle **tel qu'il est configuré pour
    la démo** (``.env``, ``LLM_BACKEND``, ``LLM_CHAIN``). Un client instancié
    dans les tests testerait une configuration qui n'existe nulle part.

    ``probe_ollama=False`` : la composition automatique sonde Ollama en HTTP au
    démarrage, ce qui n'a rien à faire dans une fixture — le repli reste couvert
    par la chaîne elle-même.

    Portée « fonction » à dessein : ``FallbackRouter.last_used`` porte le
    dernier fournisseur servi, que :func:`assertions.assert_llm_reel` relit. Un
    routeur partagé entre tests conserverait la valeur du test précédent et
    validerait un tour où le modèle n'a pas été appelé.
    """
    routeur = build_llm(probe_ollama=False)
    if routeur.chain == ["mock"]:
        pytest.skip(
            "aucun fournisseur LLM configuré (MISTRAL_API_KEY / GEMINI_API_KEY "
            "absentes, Ollama injoignable) : couche B ignorée."
        )
    return routeur


@pytest.fixture
def agent_qa_llm(pile_qa: PileQA, routeur_llm: BaseLLM) -> TutorAgent:
    """Agent de couche B : index figé de la démo, génération par un vrai modèle.

    Seul le fournisseur change par rapport à :func:`agent_qa` — même corpus,
    mêmes ports, même ``top_k``. C'est ce qui permet d'attribuer une différence
    de verdict au modèle et non au montage.
    """
    return TutorAgent(
        pile_qa.retriever,
        routeur_llm,
        memory=InMemoryStudentMemory(),
        audit=InMemoryAuditLog(),
        top_k=5,
    )
