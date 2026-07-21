"""Assemblage du prompt final (persona socratique + contexte RAG + indice).

Ce module produit le couple ``(system, user)`` que le LLM reçoit. Il matérialise
la frontière préparation/génération : une fois ce prompt assemblé (fin des nœuds
a→e), l'API n'a plus qu'à streamer ``generate_stream`` — aucune décision
pédagogique ne reste à prendre côté génération.

Le prompt inclut une ligne machine-lisible « Niveau d'indice : N (Label) » que le
LLM mock (et la traçabilité) peuvent relire.
"""

from __future__ import annotations

from agent_tuteur.agent.course_plan import CoursePosition, plan_titles
from agent_tuteur.agent.hint_strategy import HintDecision
from agent_tuteur.domain.models import ScoredChunk

# Contraintes communes aux deux postures (ancrage RAG + rendu LaTeX). Toute
# persona doit les rappeler à l'identique pour un affichage cohérent côté client.
_COMMON_RULES = (
    "Tu t'appuies STRICTEMENT sur les extraits de cours fournis ; si "
    "l'information manque, tu le dis honnêtement plutôt que d'inventer. Tu "
    "t'exprimes en français clair, avec des formules en LaTeX. Utilise "
    "EXCLUSIVEMENT les délimiteurs $...$ (inline) et $$...$$ (bloc) ; n'utilise "
    "JAMAIS \\(...\\) ni \\[...\\], qui ne s'affichent pas correctement ici."
)

SYSTEM_PERSONA = (
    "Tu es un tuteur pédagogique bienveillant pour le programme scolaire "
    "sénégalais (de l'élémentaire au Baccalauréat). Ta posture est socratique : "
    "tu guides l'élève vers la réponse par des indices progressifs plutôt que de "
    "la donner directement. " + _COMMON_RULES + " "
    "Tu ne dépasses jamais le niveau d'indice demandé."
)

#: Posture inverse de la persona socratique : ici on **expose** le cours.
SYSTEM_PERSONA_COURSE = (
    "Tu es un professeur pédagogue pour le programme scolaire sénégalais (de "
    "l'élémentaire au Baccalauréat). Tu construis le cours d'un chapitre PAS À "
    "PAS, une section à la fois. Ta posture est didactique : tu exposes "
    "clairement la section demandée, tu développes, tu illustres, et tu "
    "t'assures d'être compris avant d'avancer. " + _COMMON_RULES + " Tu traites "
    "UNIQUEMENT la section courante indiquée — n'anticipe pas les suivantes. "
    "Tu termines toujours en vérifiant la compréhension et en proposant "
    "explicitement de passer à la section suivante (ou de poser une question)."
)

_MAX_EXCERPT = 600
#: Nombre de messages (élève + tuteur confondus) réinjectés dans le prompt.
_MAX_HISTORY_MESSAGES = 6

_SPEAKER_LABELS = {"user": "Élève", "assistant": "Tuteur"}


def build_context_block(retrieved: list[ScoredChunk]) -> str:
    """Formate les extraits RAG avec attribution, pour ancrer la réponse."""
    if not retrieved:
        return "(Aucun extrait de cours pertinent trouvé.)"
    lines: list[str] = []
    for i, sc in enumerate(retrieved, start=1):
        excerpt = sc.chunk.text.strip()
        if len(excerpt) > _MAX_EXCERPT:
            excerpt = excerpt[:_MAX_EXCERPT].rstrip() + " […]"
        lines.append(f"[Source {i} — {sc.source_label}]\n{excerpt}")
    return "\n\n".join(lines)


def build_history_block(history: list[dict[str, str]] | None) -> str | None:
    """Formate les derniers tours de la conversation, ou ``None`` s'il n'y en a pas.

    Sans ce rappel, une relance courte de l'élève ("un autre indice ?") arrive
    seule dans le prompt : le LLM ne sait plus de quel énoncé il est question
    et improvise hors-sujet. On réinjecte donc le fil récent pour ancrer la
    réponse dans l'exercice réellement discuté.
    """
    if not history:
        return None
    recent = history[-_MAX_HISTORY_MESSAGES:]
    lines = [
        f"{_SPEAKER_LABELS.get(m['role'], m['role'])} : {m['content'].strip()}" for m in recent
    ]
    return "\n".join(lines)


def assemble_prompt(
    question: str,
    hint: HintDecision,
    retrieved: list[ScoredChunk],
    tool_result: str | None = None,
    curriculum_context: dict | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    """Retourne ``(system_prompt, user_prompt)`` assemblés.

    Le ``user_prompt`` agrège : contexte curriculaire, historique récent,
    extraits RAG, résultat de l'outil de calcul éventuel, la consigne
    d'indice, puis la question élève.
    """
    ctx = curriculum_context or {}
    scope = ", ".join(
        f"{k}={v}" for k in ("niveau", "classe", "serie", "discipline") if (v := ctx.get(k))
    )

    parts: list[str] = []
    if scope:
        parts.append(f"Cadre curriculaire : {scope}.")
    history_block = build_history_block(conversation_history)
    if history_block:
        parts.append(f"Historique récent de la conversation :\n{history_block}")
    parts.append("Extraits de cours disponibles :\n" + build_context_block(retrieved))
    if tool_result:
        parts.append(f"Résultat vérifié par l'outil de calcul : {tool_result}")
    parts.append(
        f"Niveau d'indice : {hint.level} ({hint.label}).\nConsigne : {hint.instruction}"
    )
    parts.append(f"Question de l'élève : {question}")

    return SYSTEM_PERSONA, "\n\n".join(parts)


def _uncovered_topic_block(position: CoursePosition) -> str:
    """Avertissement injecté quand aucun chapitre ne répond à la demande de l'élève.

    Sans ce bloc, le prompt affirmait comme un fait un chapitre déduit du meilleur
    extrait remonté — et le LLM, obéissant, enseignait ce chapitre-là en écartant
    explicitement le sujet demandé. On rend donc l'incertitude visible et on
    impose la vérification avant d'enseigner quoi que ce soit.
    """
    lines = [
        "ATTENTION — le chapitre demandé n'a pas pu être identifié dans le corpus.",
    ]
    if position.topic:
        lines.append(f"Sujet demandé par l'élève : « {position.topic} ».")
    if position.alternatives:
        lines.append(
            "Chapitres réellement disponibles dans les extraits ci-dessous : "
            + ", ".join(position.alternatives)
            + "."
        )
    lines.append(
        "Avant d'enseigner quoi que ce soit, vérifie que les extraits traitent bien "
        "le sujet demandé. S'ils le traitent, fais le cours normalement. S'ils ne le "
        "traitent PAS, dis-le franchement à l'élève et n'enseigne SURTOUT PAS un "
        "autre chapitre à la place : propose-lui plutôt les chapitres disponibles "
        "ci-dessus, ou invite-le à faire indexer la leçon manquante."
    )
    # L'élève ne voit ni les extraits ni leur numérotation : les lui opposer
    # (« les extraits que tu m'as fournis », « Source 1 ») expose la tuyauterie
    # interne et lui impute un corpus qu'il n'a pas choisi.
    lines.append(
        "Formule ce refus du point de vue de l'élève : ne parle jamais d'« extraits », "
        "de « sources » ni de leur numéro, et ne laisse pas entendre que c'est lui qui "
        "les a fournis. Dis simplement que cette leçon n'est pas encore disponible."
    )
    return "\n".join(lines)


def _build_plan_block(position: CoursePosition) -> str:
    """Sommaire du cours avec la section courante repérée (« ▶ »)."""
    titles = plan_titles()
    lines = [
        f"{'▶' if i == position.section_index else ' '} {i + 1}. {title}"
        for i, title in enumerate(titles)
    ]
    return "\n".join(lines)


def assemble_course_prompt(
    question: str,
    position: CoursePosition,
    retrieved: list[ScoredChunk],
    curriculum_context: dict | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    """Retourne ``(system_prompt, user_prompt)`` pour le **mode cours**.

    Le ``user_prompt`` agrège : cadre curriculaire, sommaire du cours avec la
    position courante, historique récent, extraits RAG, puis la consigne de la
    section à enseigner et la relance de l'élève. Aucune notion d'indice ici :
    la progression est portée par ``position`` (cf. ``course_plan.py``).
    """
    ctx = curriculum_context or {}
    scope = ", ".join(
        f"{k}={v}" for k in ("niveau", "classe", "serie", "discipline") if (v := ctx.get(k))
    )
    section = position.section

    parts: list[str] = []
    chapitre = position.chapitre or "(à identifier à partir des extraits)"
    header = f"Cours en cours : {chapitre}."
    if scope:
        header += f" Cadre curriculaire : {scope}."
    parts.append(header)
    if not position.chapitre_confirmed:
        parts.append(_uncovered_topic_block(position))
    parts.append("Plan du cours (▶ = section à traiter maintenant) :\n" + _build_plan_block(position))

    history_block = build_history_block(conversation_history)
    if history_block:
        parts.append(f"Historique récent de la conversation :\n{history_block}")

    parts.append("Extraits de cours disponibles :\n" + build_context_block(retrieved))
    parts.append(
        f"Section à enseigner : {position.section_index + 1}. {section.title}.\n"
        f"Consigne : {section.instruction}"
    )
    parts.append(f"Message de l'élève : {question}")

    return SYSTEM_PERSONA_COURSE, "\n\n".join(parts)
