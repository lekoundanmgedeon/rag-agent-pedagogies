"""GET /api/progression/{student_id} — historique et difficultés récurrentes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agent_tuteur.api.dependencies import get_tenant_id, progress_repo
from agent_tuteur.api.schemas import ProgressionOut
from agent_tuteur.persistence.repositories import ProgressRepository

router = APIRouter(prefix="/api/progression", tags=["progression"])


@router.get("/{student_id}", response_model=ProgressionOut)
async def get_progression(
    student_id: str,
    tenant_id: str = Depends(get_tenant_id),
    repo: ProgressRepository = Depends(progress_repo),
) -> ProgressionOut:
    history = await repo.history(student_id, tenant_id)
    difficulties = await repo.recurrent_difficulties(student_id, tenant_id)
    return ProgressionOut(student_id=student_id, history=history, recurrent_difficulties=difficulties)
