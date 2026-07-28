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
    "Tu t'appuies STRICTEMENT sur la documentation de cours qui t'est fournie ; "
    "si l'information manque, tu le dis honnêtement plutôt que d'inventer. Cette "
    "documentation est un mécanisme interne, invisible pour l'élève : ne la lui "
    "mentionne JAMAIS (ni « extraits », ni « sources », ni leur numéro) et ne "
    "laisse jamais entendre qu'il te l'a fournie — dis simplement que cette "
    "leçon n'est pas encore disponible. Tu "
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
    """Formate les extraits RAG avec attribution, pour ancrer la réponse.

    L'étiquette dit « Réf. interne » plutôt que « Source » : mesuré sur l'API
    réelle, le LLM reprenait spontanément le vocabulaire du prompt et citait
    « Source 1 » à l'élève, qui ne voit pourtant rien de ce bloc. L'attribution
    affichée côté client vient de ``trace["sources"]``, pas d'ici.
    """
    if not retrieved:
        return "(Aucune documentation de cours pertinente trouvée.)"
    lines: list[str] = []
    for i, sc in enumerate(retrieved, start=1):
        excerpt = sc.chunk.text.strip()
        if len(excerpt) > _MAX_EXCERPT:
            excerpt = excerpt[:_MAX_EXCERPT].rstrip() + " […]"
        lines.append(f"[Réf. interne {i} — {sc.source_label}]\n{excerpt}")
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
    parts.append(
        "Documentation de cours (usage interne, invisible pour l'élève) :\n"
        + build_context_block(retrieved)
    )
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
            "Chapitres réellement disponibles dans la documentation ci-dessous : "
            + ", ".join(position.alternatives)
            + "."
        )
    lines.append(
        "Avant d'enseigner quoi que ce soit, vérifie que la documentation traite bien "
        "le sujet demandé. Si oui, fais le cours normalement. Si NON, "
        "dis-le franchement à l'élève et n'enseigne SURTOUT PAS un "
        "autre chapitre à la place : propose-lui plutôt les chapitres disponibles "
        "ci-dessus, ou invite-le à faire indexer la leçon manquante."
    )
    # Le vocabulaire à tenir face à l'élève (ne pas nommer extraits/sources) est
    # porté par _COMMON_RULES, commun aux deux postures : la même fuite avait été
    # mesurée en mode exercice sur ce même chemin « information manquante ».
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

    parts.append(
        "Documentation de cours (usage interne, invisible pour l'élève) :\n"
        + build_context_block(retrieved)
    )
    parts.append(
        f"Section à enseigner : {position.section_index + 1}. {section.title}.\n"
        f"Consigne : {section.instruction}"
    )
    parts.append(f"Message de l'élève : {question}")

    return SYSTEM_PERSONA_COURSE, "\n\n".join(parts)
