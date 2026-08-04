"""POST /api/quiz — génère un quiz · POST /api/quiz/answer — corrige et enregistre.

**La bonne réponse ne descend jamais dans le navigateur.** Elle voyage scellée
dans ``quiz_token`` (cf. ``api/security.create_quiz_token``) : le client la
transporte sans pouvoir la lire, et seule la route de correction la rouvre. Sans
cette précaution, un élève lirait la réponse dans les outils de développement
avant de répondre, et l'évaluation ne mesurerait plus rien.

La correction est **déterministe** (comparaison de deux identifiants, aucun
appel au modèle) : une même réponse est toujours jugée de la même façon.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from agent_tuteur.agent.graph import TutorAgent
from agent_tuteur.agent.quiz import corriger_quiz, generer_quiz
from agent_tuteur.api.dependencies import (
    badge_repo,
    ensure_can_access_student,
    exercise_repo,
    get_agent,
    get_current_user,
    link_repo,
    mastery_repo,
)
from agent_tuteur.api.schemas import (
    BadgeOut,
    MasteryEntryOut,
    QuizAnswerRequest,
    QuizChoiceOut,
    QuizCorrectionOut,
    QuizOut,
    QuizRequest,
)
from agent_tuteur.api.security import AuthError, Principal, create_quiz_token, decode_quiz_token
from agent_tuteur.domain.mastery import BADGES, badges_merites, score_observe, statut_maitrise
from agent_tuteur.persistence.repositories import (
    BadgeRepository,
    ExerciseResultRepository,
    MasteryRepository,
    StudentLinkRepository,
)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


def _mastery_out(maj: dict) -> MasteryEntryOut:
    """Convertit une ligne de maîtrise en réponse d'API, statut calculé."""
    return MasteryEntryOut(
        competence=maj["competence"],
        chapitre=maj.get("chapitre"),
        mastery_score=maj["mastery_score"],
        attempts=maj["attempts"],
        successes=maj["successes"],
        statut=statut_maitrise(maj["mastery_score"], maj["attempts"]),
        last_seen=maj.get("last_seen"),
    )


def _competence_visee(demande: QuizRequest) -> str:
    """Sur quoi interroger l'élève, quand il ne l'a pas précisé.

    On reprend le chapitre du cadre curriculaire, à défaut la discipline. On
    n'interroge jamais « au hasard » : sans aucune indication, la demande est
    refusée plutôt que de poser une question hors sujet.
    """
    if demande.competence:
        return demande.competence
    ctx = demande.curriculum_context
    for champ in ("chapitre", "competence", "discipline"):
        if valeur := ctx.get(champ):
            return valeur
    raise HTTPException(
        status_code=422,
        detail="Précisez une compétence ou un chapitre pour générer un quiz.",
    )


@router.post("", response_model=QuizOut)
async def generate_quiz(
    payload: QuizRequest,
    principal: Principal = Depends(get_current_user),
    agent: TutorAgent = Depends(get_agent),
) -> QuizOut:
    """Génère un quiz sur une compétence.

    Un quiz indisponible (``available`` faux) n'est **pas** une erreur HTTP :
    c'est le résultat honnête d'un modèle qui n'a rien produit d'exploitable.
    L'interface affiche ``instructions`` et propose de réessayer — jamais un
    questionnaire de remplissage.
    """
    competence = _competence_visee(payload)
    cadre = ", ".join(
        v for k in ("classe", "serie") if (v := payload.curriculum_context.get(k))
    )
    quiz = await generer_quiz(
        agent.llm,
        competence,
        quiz_type=payload.quiz_type,
        contexte_curriculaire=cadre,
    )

    if not quiz.est_utilisable:
        return QuizOut(
            competence=competence,
            quiz_type=payload.quiz_type,
            available=False,
            instructions=quiz.to_dict()["instructions"],
        )

    question = quiz.questions[0]
    return QuizOut(
        competence=competence,
        quiz_type=quiz.quiz_type,
        available=True,
        question=question["question"],
        choices=[QuizChoiceOut(**c) for c in question["choices"]],
        quiz_token=create_quiz_token(
            competence=competence,
            correct_answer=question["correct_answer"],
            explanation=question["explanation"],
        ),
        instructions=quiz.to_dict()["instructions"],
    )


@router.post("/answer", response_model=QuizCorrectionOut)
async def answer_quiz(
    payload: QuizAnswerRequest,
    principal: Principal = Depends(get_current_user),
    links: StudentLinkRepository = Depends(link_repo),
    mastery: MasteryRepository = Depends(mastery_repo),
    results: ExerciseResultRepository = Depends(exercise_repo),
    badges: BadgeRepository = Depends(badge_repo),
) -> QuizCorrectionOut:
    """Corrige une réponse, met à jour la maîtrise, attribue les badges mérités."""
    try:
        scelle = decode_quiz_token(payload.quiz_token)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    student_id = payload.student_id or principal.student_id or principal.user_id
    await ensure_can_access_student(principal, student_id, links)

    correction = corriger_quiz(
        {
            "correct_answer": scelle["correct_answer"],
            "explanation": scelle["explanation"],
        },
        payload.answer,
    )
    competence = scelle["competence"]

    await results.record(
        {
            "tenant_id": principal.tenant_id,
            "student_id": student_id,
            "competence": competence,
            "exercise_type": "quiz",
            "is_correct": correction["is_correct"],
            "score": correction["score"],
        }
    )
    maj = await mastery.record_attempt(
        student_id=student_id,
        competence=competence,
        is_correct=correction["is_correct"],
        tenant_id=principal.tenant_id,
    )

    historique = await results.list_for_student(student_id, principal.tenant_id, limit=100)
    obtenus = []
    for code in badges_merites(
        total_resultats=len(historique),
        observe=score_observe(is_correct=correction["is_correct"]),
        maitrise=maj["mastery_score"],
    ):
        definition = BADGES[code]
        attribue = await badges.award(
            student_id=student_id,
            code=code,
            label=definition["label"],
            description=definition["description"],
            tenant_id=principal.tenant_id,
        )
        if attribue:  # None si le badge était déjà acquis
            obtenus.append(BadgeOut(**attribue))

    return QuizCorrectionOut(
        **correction,
        mastery=_mastery_out(maj),
        badges=obtenus,
    )
