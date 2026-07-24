"""GET /api/progression/{student_id} — historique et difficultés récurrentes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from agent_tuteur.api.dependencies import get_current_user, progress_repo
from agent_tuteur.api.schemas import ProgressionOut
from agent_tuteur.api.security import Principal
from agent_tuteur.persistence.repositories import ProgressRepository

router = APIRouter(prefix="/api/progression", tags=["progression"])


@router.get("/{student_id}", response_model=ProgressionOut)
async def get_progression(
    student_id: str,
    principal: Principal = Depends(get_current_user),
    repo: ProgressRepository = Depends(progress_repo),
) -> ProgressionOut:
    # Un élève ne peut consulter que sa propre progression ; un admin, celle de
    # n'importe quel élève de son tenant.
    if principal.role == "student" and student_id != (principal.student_id or principal.user_id):
        raise HTTPException(status_code=403, detail="Accès à la progression d'un autre élève refusé.")
    history = await repo.history(student_id, principal.tenant_id)
    difficulties = await repo.recurrent_difficulties(student_id, principal.tenant_id)
    return ProgressionOut(student_id=student_id, history=history, recurrent_difficulties=difficulties)
