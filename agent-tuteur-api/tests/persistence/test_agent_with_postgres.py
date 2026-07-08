"""L'agent (in-memory RAG + LLM mock) écrit sa mémoire/audit dans Postgres réel.

Valide l'intégration bout en bout de l'injection de ports **par requête** :
un même ``TutorAgent`` (construit une seule fois) reçoit des repositories liés
à des sessions Postgres différentes selon l'appel, sans état partagé.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker

from agent_tuteur.agent.frustration import SessionState
from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.agent.llm.mock import MockLLM
from agent_tuteur.persistence.repositories import AuditLogRepository, ProgressRepository


async def test_agent_persists_to_real_postgres_per_request(postgres_engine, rag_stack):
    agent = TutorAgent(rag_stack.retriever, MockLLM(), top_k=5)  # pas de ports par défaut
    factory = async_sessionmaker(postgres_engine, expire_on_commit=False)

    async with factory() as session:
        memory = ProgressRepository(session)
        audit = AuditLogRepository(session)
        session_state = SessionState(student_id="pg_eleve", tenant_id="pg_tenant")

        result = await agent.respond(
            "comment dériver un quotient de fonctions ?",
            {"serie": "S1", "discipline": "Mathématiques"},
            session_state,
            memory=memory,
            audit=audit,
        )
        await session.commit()
        assert result.answer

    # Nouvelle session : les écritures doivent être visibles (déjà commitées).
    async with factory() as session2:
        memory2 = ProgressRepository(session2)
        audit2 = AuditLogRepository(session2)
        history = await memory2.history("pg_eleve", "pg_tenant")
        events = await audit2.read("pg_eleve", "pg_tenant")
        assert len(history) == 1
        assert history[0]["competence"]
        assert len(events) == 1
        assert events[0]["hint_level"] == result.hint_level

        # Nettoyage (le smoke test ne doit pas laisser de résidus).
        from sqlalchemy import delete

        from agent_tuteur.persistence.models import AuditLog, Progress

        await session2.execute(delete(Progress).where(Progress.student_id == "pg_eleve"))
        await session2.execute(delete(AuditLog).where(AuditLog.student_id == "pg_eleve"))
        await session2.commit()
