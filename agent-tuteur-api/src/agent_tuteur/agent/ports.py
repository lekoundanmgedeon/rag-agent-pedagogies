"""Ports (interfaces) mémoire élève & traçabilité + adaptateurs in-memory.

Le cœur agent dépend de ces **protocoles**, pas d'une base. Les interfaces sont
**async** car l'étape 4 les implémente avec SQLAlchemy async + asyncpg, appelées
depuis une API FastAPI async ; les adaptateurs en mémoire ici permettent une
démo et des tests hors-ligne sans latence réelle.

Séparation volontaire : la **mémoire élève** (progression) et le **journal
d'audit** (traçabilité enseignant/institution) sont deux stores distincts, aux
rétentions potentiellement différentes.
"""

from __future__ import annotations

from collections import Counter
from typing import Protocol, runtime_checkable


@runtime_checkable
class StudentMemoryPort(Protocol):
    """Mémoire élève : résultats notables persistés (jamais l'état de session)."""

    async def record(self, entry: dict) -> None: ...
    async def history(self, student_id: str, tenant_id: str = "default") -> list[dict]: ...
    async def recurrent_difficulties(self, student_id: str, tenant_id: str = "default") -> list[str]: ...


@runtime_checkable
class AuditLogPort(Protocol):
    """Journal de traçabilité pédagogique."""

    async def log(self, event: dict) -> None: ...
    async def read(self, student_id: str, tenant_id: str = "default") -> list[dict]: ...


class InMemoryStudentMemory:
    """Adaptateur mémoire élève en RAM (démo/tests)."""

    def __init__(self) -> None:
        self._entries: list[dict] = []

    async def record(self, entry: dict) -> None:
        self._entries.append(dict(entry))

    async def history(self, student_id: str, tenant_id: str = "default") -> list[dict]:
        return [
            e
            for e in self._entries
            if e.get("student_id") == student_id and e.get("tenant_id", "default") == tenant_id
        ]

    async def recurrent_difficulties(self, student_id: str, tenant_id: str = "default") -> list[str]:
        """Compétences où l'élève a eu besoin d'indices poussés (niveau ≥ 3)."""
        history = await self.history(student_id, tenant_id)
        difficult = Counter(
            e.get("competence") for e in history if e.get("competence") and e.get("hint_level", 0) >= 3
        )
        return [competence for competence, _ in difficult.most_common()]


class InMemoryAuditLog:
    """Adaptateur journal d'audit en RAM (démo/tests)."""

    def __init__(self) -> None:
        self._events: list[dict] = []

    async def log(self, event: dict) -> None:
        self._events.append(dict(event))

    async def read(self, student_id: str, tenant_id: str = "default") -> list[dict]:
        return [
            e
            for e in self._events
            if e.get("student_id") == student_id and e.get("tenant_id", "default") == tenant_id
        ]
