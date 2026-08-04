"""GET /api/evaluation/{student_id} — historique des exercices et quiz d'un élève.

L'identifiant de l'élève est dans l'URL, mais **il n'ouvre aucun droit** :
``ensure_can_access_student`` vérifie en base, pour le compte connecté, que la
consultation est permise. C'est précisément la correction de la faille de NURU,
où l'identifiant fourni par le client valait autorisation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from agent_tuteur.api.dependencies import (
    ensure_can_access_student,
    exercise_repo,
    get_current_user,
    link_repo,
)
from agent_tuteur.api.schemas import EvaluationHistoryOut, ExerciseResultOut
from agent_tuteur.api.security import Principal
from agent_tuteur.persistence.repositories import ExerciseResultRepository, StudentLinkRepository

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/{student_id}", response_model=EvaluationHistoryOut)
async def get_evaluation_history(
    student_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(get_current_user),
    links: StudentLinkRepository = Depends(link_repo),
    results: ExerciseResultRepository = Depends(exercise_repo),
) -> EvaluationHistoryOut:
    """Résultats d'exercices et de quiz, du plus récent au plus ancien."""
    await ensure_can_access_student(principal, student_id, links)

    lignes = await results.list_for_student(student_id, principal.tenant_id, limit=limit)
    return EvaluationHistoryOut(
        student_id=student_id,
        results=[
            ExerciseResultOut(
                id=r["id"],
                competence=r["competence"],
                chapitre=r["chapitre"],
                exercise_type=r["exercise_type"],
                difficulty=r["difficulty"],
                is_correct=r["is_correct"],
                score=r["score"],
                created_at=r["created_at"],
            )
            for r in lignes
        ],
    )
