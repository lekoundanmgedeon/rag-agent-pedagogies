"""POST /api/quiz — sert un quiz · POST /api/quiz/answer — corrige et enregistre.

**Les questions viennent du corpus, elles ne sont plus générées** (décision D12,
tranchée le 2026-08-28). Le modèle produisait des questions dont la réponse
déclarée pouvait être fausse — mesuré dès le premier essai sur la stack réelle —
et rien ne la vérifiait. Les sections « 18. Auto-évaluation » des leçons portent
des items rédigés et corrigés par l'auteur : les lire rend la question juste par
construction. Quand le chapitre n'en a pas, on le dit (``available`` faux) plutôt
que de retomber sur la génération, qui ramènerait le défaut par la porte de
service.

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

from agent_tuteur.agent import quiz_corpus
from agent_tuteur.agent.quiz import corriger_quiz
from agent_tuteur.api.dependencies import (
    badge_repo,
    ensure_can_access_student,
    exercise_repo,
    get_current_user,
    get_retriever,
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
from agent_tuteur.vectorstore.retriever import HybridRetriever

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
    retriever: HybridRetriever = Depends(get_retriever),
) -> QuizOut:
    """Sert une question d'évaluation **tirée du corpus** sur une compétence.

    L'absence de question n'est **pas** une erreur HTTP : c'est le résultat
    honnête d'un chapitre dont la section d'auto-évaluation est vide, absente,
    ou dont les QCM ne portent pas de clé de correction. L'interface affiche
    alors ``instructions`` — jamais un questionnaire de remplissage, jamais une
    question inventée pour l'occasion.
    """
    competence = _competence_visee(payload)

    # Ratissage par métadonnées, pas par similarité : la section d'évaluation
    # doit être atteinte même si son texte ressemble peu à la demande.
    extraits = retriever.chunks_du_chapitre(competence, payload.curriculum_context)
    question = quiz_corpus.choisir(
        quiz_corpus.questions_du_chapitre(extraits), payload.quiz_type
    )

    if question is None:
        return QuizOut(
            competence=competence,
            quiz_type=payload.quiz_type,
            available=False,
            instructions=(
                f"Je n'ai pas encore de question d'évaluation corrigée pour « {competence} ». "
                "Mes questions sont tirées des leçons elles-mêmes, jamais inventées : quand la "
                "leçon n'en fournit pas, je préfère te le dire plutôt que de risquer de te "
                "corriger à tort. Essaie un autre chapitre, ou reviens au cours."
            ),
        )

    return QuizOut(
        competence=competence,
        quiz_type=question.type,
        available=True,
        question=question.enonce,
        choices=[QuizChoiceOut(id=identifiant, text=texte) for identifiant, texte in question.choix],
        quiz_token=create_quiz_token(
            competence=competence,
            correct_answer=question.reponse,
            explanation=question.explication,
        ),
        instructions=(
            "Choisis la proposition qui te paraît juste, puis valide : la correction est "
            "immédiate."
        ),
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
