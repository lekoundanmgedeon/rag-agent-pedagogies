"""GET /api/progression/{student_id} — historique et difficultés récurrentes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agent_tuteur.api.dependencies import (
    ensure_can_access_student,
    get_current_user,
    link_repo,
    progress_repo,
)
from agent_tuteur.api.schemas import ProgressionOut
from agent_tuteur.api.security import Principal
from agent_tuteur.persistence.repositories import ProgressRepository, StudentLinkRepository

router = APIRouter(prefix="/api/progression", tags=["progression"])


@router.get("/{student_id}", response_model=ProgressionOut)
async def get_progression(
    student_id: str,
    principal: Principal = Depends(get_current_user),
    repo: ProgressRepository = Depends(progress_repo),
    links: StudentLinkRepository = Depends(link_repo),
) -> ProgressionOut:
    # Qui a le droit de voir quoi est décidé au même endroit pour toutes les
    # routes (cf. ``dependencies.ensure_can_access_student``) : un élève ne voit
    # que lui-même, un parent ou un enseignant seulement les élèves qui lui sont
    # rattachés en base, un admin tous ceux de son établissement.
    await ensure_can_access_student(principal, student_id, links)

    history = await repo.history(student_id, principal.tenant_id)
    difficulties = await repo.recurrent_difficulties(student_id, principal.tenant_id)
    return ProgressionOut(student_id=student_id, history=history, recurrent_difficulties=difficulties)
