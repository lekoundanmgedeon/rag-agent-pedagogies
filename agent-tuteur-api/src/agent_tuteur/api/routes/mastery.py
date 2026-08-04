"""GET /api/mastery/{student_id} — niveau de maîtrise, priorités de révision, badges.

C'est la vue « où en suis-je ? » de l'élève, et « où en est-il ? » de son
enseignant ou de son parent. Comme partout, l'identifiant dans l'URL n'ouvre
aucun droit : l'autorisation est vérifiée en base pour le compte connecté.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from agent_tuteur.api.dependencies import (
    badge_repo,
    ensure_can_access_student,
    get_current_user,
    link_repo,
    mastery_repo,
)
from agent_tuteur.api.schemas import BadgeOut, MasteryEntryOut, MasteryOut
from agent_tuteur.api.security import Principal
from agent_tuteur.domain.mastery import statut_maitrise
from agent_tuteur.persistence.repositories import (
    BadgeRepository,
    MasteryRepository,
    StudentLinkRepository,
)

router = APIRouter(prefix="/api/mastery", tags=["mastery"])


def _entree(ligne: dict) -> MasteryEntryOut:
    """Ligne de maîtrise -> réponse d'API, avec son statut lisible.

    Le statut (« maitrise », « en_cours », « faible », « non_commence ») est
    calculé ici et non stocké : c'est un affichage dérivé du score, et le
    stocker créerait deux vérités à maintenir en accord.
    """
    return MasteryEntryOut(
        competence=ligne["competence"],
        chapitre=ligne.get("chapitre"),
        mastery_score=ligne["mastery_score"],
        attempts=ligne["attempts"],
        successes=ligne["successes"],
        statut=statut_maitrise(ligne["mastery_score"], ligne["attempts"]),
        last_seen=ligne.get("last_seen"),
    )


@router.get("/{student_id}", response_model=MasteryOut)
async def get_mastery(
    student_id: str,
    weakest_limit: int = Query(default=3, ge=1, le=20),
    principal: Principal = Depends(get_current_user),
    links: StudentLinkRepository = Depends(link_repo),
    mastery: MasteryRepository = Depends(mastery_repo),
    badges: BadgeRepository = Depends(badge_repo),
) -> MasteryOut:
    """Niveau par compétence, compétences à retravailler, badges obtenus.

    ``weakest`` ne contient que des compétences **réellement tentées** : une
    compétence jamais travaillée n'est pas « non maîtrisée », elle est inconnue,
    et la proposer en priorité de révision serait trompeur.
    """
    await ensure_can_access_student(principal, student_id, links)

    competences = await mastery.list_for_student(student_id, principal.tenant_id)
    faibles = await mastery.weakest(student_id, principal.tenant_id, limit=weakest_limit)
    obtenus = await badges.list_for_student(student_id, principal.tenant_id)

    return MasteryOut(
        student_id=student_id,
        competences=[_entree(c) for c in competences],
        weakest=[_entree(f) for f in faibles],
        badges=[BadgeOut(**b) for b in obtenus],
    )
