import pytest
from sqlalchemy.exc import IntegrityError

from agent_tuteur.persistence.repositories import (
    AuditLogRepository,
    ConversationRepository,
    DocumentRepository,
    FeedbackRepository,
    MessageRepository,
    ProgressRepository,
)


async def test_progress_record_and_history(session):
    repo = ProgressRepository(session)
    await repo.record(
        {"student_id": "eleve1", "tenant_id": "t1", "competence": "Dérivées", "hint_level": 2, "question": "q1"}
    )
    await repo.record(
        {"student_id": "eleve1", "tenant_id": "t1", "competence": "Dérivées", "hint_level": 4, "question": "q2"}
    )
    await session.commit()

    history = await repo.history("eleve1", "t1")
    assert len(history) == 2
    assert history[0]["question"] == "q1"
    assert history[1]["hint_level"] == 4


async def test_progress_tenant_isolation(session):
    repo = ProgressRepository(session)
    await repo.record({"student_id": "s1", "tenant_id": "ecoleA", "hint_level": 1, "question": "q"})
    await repo.record({"student_id": "s1", "tenant_id": "ecoleB", "hint_level": 1, "question": "q"})
    await session.commit()

    assert len(await repo.history("s1", "ecoleA")) == 1
    assert len(await repo.history("s1", "ecoleB")) == 1


async def test_recurrent_difficulties_orders_by_frequency(session):
    repo = ProgressRepository(session)
    for _ in range(3):
        await repo.record(
            {"student_id": "s1", "tenant_id": "t1", "competence": "Dérivées", "hint_level": 3, "question": "q"}
        )
    for _ in range(1):
        await repo.record(
            {"student_id": "s1", "tenant_id": "t1", "competence": "Intégrales", "hint_level": 4, "question": "q"}
        )
    # Un niveau bas (< 3) ne doit pas compter comme difficulté.
    await repo.record(
        {"student_id": "s1", "tenant_id": "t1", "competence": "Suites", "hint_level": 1, "question": "q"}
    )
    await session.commit()

    difficulties = await repo.recurrent_difficulties("s1", "t1")
    assert difficulties == ["Dérivées", "Intégrales"]


async def test_audit_log_record_and_read(session):
    repo = AuditLogRepository(session)
    await repo.log(
        {
            "student_id": "s1",
            "tenant_id": "t1",
            "question": "q",
            "competence": "Dérivées",
            "sources": [{"id": "c1", "score": 0.9}],
            "hint_level": 2,
            "hint_label": "Indice ciblé",
            "frustration_score": 0.3,
            "tool_used": "sympy_calculator",
        }
    )
    await session.commit()

    events = await repo.read("s1", "t1")
    assert len(events) == 1
    assert events[0]["rag_sources"] == [{"id": "c1", "score": 0.9}]
    assert events[0]["tool_used"] == "sympy_calculator"


async def test_audit_log_tenant_isolation(session):
    repo = AuditLogRepository(session)
    await repo.log({"student_id": "s1", "tenant_id": "t1", "question": "q", "hint_level": 1, "hint_label": "x"})
    await session.commit()
    assert await repo.read("s1", "t2") == []


async def test_conversation_message_feedback_flow(session):
    conv_repo = ConversationRepository(session)
    msg_repo = MessageRepository(session)
    fb_repo = FeedbackRepository(session)

    conv = await conv_repo.create("t1", "eleve1")
    await session.commit()
    assert await conv_repo.get(conv.id, "t1") is not None
    assert await conv_repo.get(conv.id, "t2") is None  # mauvais tenant -> invisible

    msg = await msg_repo.add(conv.id, "t1", "assistant", "voici ta réponse", trace={"hint_level": 1})
    await session.commit()
    msgs = await msg_repo.list_for_conversation(conv.id, "t1")
    assert len(msgs) == 1
    assert msgs[0].trace == {"hint_level": 1}

    fb = await fb_repo.add(msg.id, "t1", 1)
    await session.commit()
    assert fb.value == 1


async def test_feedback_value_constraint_rejected(session):
    conv_repo = ConversationRepository(session)
    msg_repo = MessageRepository(session)
    fb_repo = FeedbackRepository(session)

    conv = await conv_repo.create("t1", "eleve1")
    msg = await msg_repo.add(conv.id, "t1", "user", "question")
    await session.commit()

    with pytest.raises(ValueError):
        await fb_repo.add(msg.id, "t1", 0)


async def test_document_lifecycle(session):
    repo = DocumentRepository(session)
    doc = await repo.create_pending("t1", "cours.pdf", "pdf", metadata={"niveau": "secondaire"})
    await session.commit()
    assert doc.status == "pending"

    await repo.update_status(doc.id, "indexed")
    await session.commit()
    fetched = await repo.get(doc.id, "t1")
    assert fetched.status == "indexed"
    assert fetched.metadata_ == {"niveau": "secondaire"}

    docs = await repo.list("t1")
    assert len(docs) == 1

    deleted = await repo.delete(doc.id, "t1")
    assert deleted is True
    assert await repo.get(doc.id, "t1") is None


async def test_document_tenant_isolation_on_get(session):
    repo = DocumentRepository(session)
    doc = await repo.create_pending("ecoleA", "a.pdf", "pdf")
    await session.commit()
    assert await repo.get(doc.id, "ecoleB") is None
    assert await repo.delete(doc.id, "ecoleB") is False
