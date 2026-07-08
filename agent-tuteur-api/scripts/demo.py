"""Démonstration end-to-end du cœur (mode hors-ligne : mock + in-memory).

Ingeste le corpus d'exemple, puis exécute un tour d'agent en affichant :
niveau d'indice, sources RAG, outil éventuel, et la réponse **streamée**.

    PYTHONPATH=src python scripts/demo.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.ports import InMemoryAuditLog, InMemoryStudentMemory
from agent_tuteur.factory import build_agent, build_rag_stack, ingest_corpus

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def _print_meta(prep) -> None:
    print(f"\n  Niveau d'indice : {prep.hint_level} ({prep.hint_label})")
    print(f"  Compétence mobilisée : {prep.trace['competence']}")
    print(f"  Outil : {prep.trace['tool_used'] or 'aucun'}")
    print(f"  Frustration : {prep.trace['frustration_score']}")
    print("  Sources RAG :")
    for s in prep.trace["sources"][:3]:
        print(f"    - [{s['score']:.4f}] {s['label']} ({s['type_chunk']})")


async def main() -> int:
    stack = build_rag_stack()
    n = ingest_corpus(stack.indexer, CORPUS)
    memory, audit = InMemoryStudentMemory(), InMemoryAuditLog()
    agent = build_agent(retriever=stack.retriever, memory=memory, audit=audit, probe_ollama=False)

    print(f"Corpus indexé : {n} chunks.")
    print(f"Chaîne LLM : {' -> '.join(agent._llm.chain)}")

    session = SessionState(student_id="eleve_demo", tenant_id="default")
    questions = [
        ("comment dériver un quotient de deux fonctions ?", {"serie": "S1", "discipline": "Mathématiques"}),
        ("calcule la dérivée de x^3 - 3x", {"serie": "S1", "discipline": "Mathématiques"}),
        ("je comprends pas, donne-moi la réponse", {"serie": "S1", "discipline": "Mathématiques"}),
    ]

    for question, ctx in questions:
        print("\n" + "=" * 72)
        print(f"Élève : {question}")
        prep = await agent.prepare(question, ctx, session)   # nœuds a→e (préparation)
        _print_meta(prep)
        print("\n  Tuteur : ", end="", flush=True)
        async for token in agent.stream(prep):                # génération streamée (f)
            print(token, end="", flush=True)
        print()
        await agent.commit_memory(prep)                        # résultat notable persisté

    print("\n" + "=" * 72)
    print(f"Progression élève (mémoire) : {len(await memory.history('eleve_demo'))} entrées")
    print(f"Journal d'audit : {len(await audit.read('eleve_demo'))} interactions tracées")
    difficulties = await memory.recurrent_difficulties("eleve_demo")
    print(f"Difficultés récurrentes détectées : {difficulties or 'aucune'}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
