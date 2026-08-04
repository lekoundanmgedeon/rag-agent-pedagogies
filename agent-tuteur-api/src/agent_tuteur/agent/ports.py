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

from agent_tuteur.domain.mastery import (
    est_une_reussite,
    maitrise_mise_a_jour,
    score_observe,
)


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


@runtime_checkable
class MasteryPort(Protocol):
    """Niveau de maîtrise par compétence (« mastery learning »).

    Séparé de ``StudentMemoryPort`` à dessein : la mémoire élève enregistre des
    *événements* (telle question a été posée avec tel niveau d'indice), la
    maîtrise porte un *état* dérivé (cette compétence est acquise à 72 %).
    """

    async def record_attempt(
        self,
        *,
        student_id: str,
        competence: str,
        is_correct: bool | None = None,
        score: float | None = None,
        chapitre: str | None = None,
        tenant_id: str = "default",
    ) -> dict: ...

    async def list_for_student(self, student_id: str, tenant_id: str = "default") -> list[dict]: ...

    async def weakest(
        self, student_id: str, tenant_id: str = "default", limit: int = 3
    ) -> list[dict]: ...


@runtime_checkable
class EvaluationPort(Protocol):
    """Historique brut des exercices et quiz terminés."""

    async def record(self, entry: dict) -> dict: ...
    async def list_for_student(
        self, student_id: str, tenant_id: str = "default", limit: int = 50
    ) -> list[dict]: ...


class InMemoryMastery:
    """Adaptateur maîtrise en RAM (démo/tests).

    Applique **les mêmes règles de calcul** que le dépôt PostgreSQL, puisque
    toutes deux appellent ``domain/mastery.py`` : un test hors-ligne mesure donc
    le vrai comportement, pas une approximation.
    """

    def __init__(self) -> None:
        self._lignes: dict[tuple[str, str, str], dict] = {}

    async def record_attempt(
        self,
        *,
        student_id: str,
        competence: str,
        is_correct: bool | None = None,
        score: float | None = None,
        chapitre: str | None = None,
        tenant_id: str = "default",
    ) -> dict:
        observe = score_observe(is_correct=is_correct, score=score)
        cle = (tenant_id, student_id, competence)
        ligne = self._lignes.get(cle)
        if ligne is None:
            ligne = {
                "student_id": student_id,
                "competence": competence,
                "chapitre": chapitre,
                "mastery_score": maitrise_mise_a_jour(None, observe),
                "attempts": 0,
                "successes": 0,
            }
            self._lignes[cle] = ligne
        else:
            ligne["mastery_score"] = maitrise_mise_a_jour(ligne["mastery_score"], observe)

        ligne["attempts"] += 1
        ligne["successes"] += 1 if est_une_reussite(observe) else 0
        if chapitre and not ligne.get("chapitre"):
            ligne["chapitre"] = chapitre
        return dict(ligne)

    async def list_for_student(self, student_id: str, tenant_id: str = "default") -> list[dict]:
        lignes = [
            dict(v)
            for (t, s, _), v in self._lignes.items()
            if s == student_id and t == tenant_id
        ]
        return sorted(lignes, key=lambda m: m["mastery_score"])

    async def weakest(
        self, student_id: str, tenant_id: str = "default", limit: int = 3
    ) -> list[dict]:
        tentees = [m for m in await self.list_for_student(student_id, tenant_id) if m["attempts"] > 0]
        return tentees[:limit]


class InMemoryEvaluation:
    """Adaptateur historique d'exercices en RAM (démo/tests)."""

    def __init__(self) -> None:
        self._entrees: list[dict] = []

    async def record(self, entry: dict) -> dict:
        enregistre = dict(entry)
        enregistre.setdefault("tenant_id", "default")
        enregistre.setdefault("exercise_type", "exercice")
        self._entrees.append(enregistre)
        return enregistre

    async def list_for_student(
        self, student_id: str, tenant_id: str = "default", limit: int = 50
    ) -> list[dict]:
        retenues = [
            dict(e)
            for e in self._entrees
            if e.get("student_id") == student_id and e.get("tenant_id", "default") == tenant_id
        ]
        return list(reversed(retenues))[:limit]
