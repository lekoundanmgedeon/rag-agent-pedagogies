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
    "leçon n'est pas encore disponible. Cette documentation décrit un "
    "CHAPITRE, jamais l'élève : le niveau, la série ou la classe qui y "
    "figurent sont ceux du document, et n'apprennent RIEN sur lui. Ne lui "
    "attribue jamais une série, une classe, un établissement, un historique "
    "de cours ni des notions « déjà vues » que tu y aurais lus — tu ne sais de "
    "l'élève que ce qu'il t'a dit lui-même dans cette conversation. Tu "
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

#: Posture d'évaluation : ni indices, ni exposé — on interroge.
#: Volontairement sèche : la sortie attendue est un objet JSON, pas un discours.
#: Les règles communes n'y figurent pas car elles portent sur la façon de
#: s'adresser à l'élève, ce qui n'a pas de sens ici.
SYSTEM_PERSONA_QUIZ = (
    "Tu es un concepteur de sujets d'évaluation pour le programme scolaire "
    "sénégalais. Tu produis des questions justes, sans ambiguïté, dont une "
    "seule proposition est correcte. Tu réponds EXCLUSIVEMENT par l'objet JSON "
    "demandé, sans aucun texte avant ni après, sans balise markdown."
)

#: Posture d'orientation : l'élève interroge le service, pas une notion.
#: Les règles communes ne s'appliquent pas telles quelles — il n'y a pas de
#: documentation de cours à citer ici — mais la contrainte LaTeX est reprise
#: pour que le rendu reste homogène si une formule apparaît malgré tout.
SYSTEM_PERSONA_META = (
    "Tu es l'assistant d'orientation d'un tuteur pédagogique pour le programme "
    "scolaire sénégalais. L'élève te pose une question sur le service lui-même "
    "(ce que tu couvres, comment travailler avec toi, comment progresser) et non "
    "sur une notion de cours. Tu réponds brièvement, concrètement et "
    "chaleureusement. "
    "Tu ne prétends JAMAIS connaître le programme personnel de l'élève, son "
    "établissement, sa classe ou ce qu'il a déjà étudié : tu ne sais que ce qu'il "
    "vient de te dire. Tu n'annonces QUE les chapitres listés ci-dessous comme "
    "disponibles, et tu n'en inventes aucun autre ; si la liste est vide, tu le "
    "dis franchement. Tu t'exprimes en français clair ; si une formule est "
    "nécessaire, utilise EXCLUSIVEMENT $...$ (inline) et $$...$$ (bloc)."
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

    L'attribution écrite ici est ``libelle_interne`` (le chapitre) et non
    ``source_label`` (qui porte le nom de fichier) : ce nom encode la série du
    document, que le modèle attribuait ensuite à l'élève (cas QA #16).
    """
    if not retrieved:
        return "(Aucune documentation de cours pertinente trouvée.)"
    lines: list[str] = []
    for i, sc in enumerate(retrieved, start=1):
        excerpt = sc.chunk.text.strip()
        if len(excerpt) > _MAX_EXCERPT:
            excerpt = excerpt[:_MAX_EXCERPT].rstrip() + " […]"
        lines.append(f"[Réf. interne {i} — {sc.libelle_interne}]\n{excerpt}")
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


#: Consigne ajoutée quand l'élève demande un calcul que l'outil symbolique n'a
#: pas pu vérifier. Sans elle, l'échec de l'outil est invisible pour le modèle,
#: qui refait le calcul de son côté et se trompe — c'est le cas QA #1, où un
#: résultat faux a été annoncé avec l'assurance d'un résultat vérifié.
#: La règle non-négociable n°2 impose de refuser ou de rediriger.
AVERTISSEMENT_CALCUL_NON_VERIFIE = (
    "ATTENTION : l'élève demande un calcul, mais celui-ci n'a PAS pu être vérifié "
    "par l'outil de calcul symbolique. Tu ne dois donc annoncer AUCUN résultat "
    "chiffré ni aucune expression finale — tu te tromperais peut-être sans "
    "pouvoir le savoir. Explique la méthode pas à pas, demande à l'élève de "
    "réécrire son expression plus simplement s'il y a une ambiguïté de notation, "
    "et invite-le à poser le calcul lui-même."
)


#: Injectée quand l'élève signale que l'explication a déjà été donnée (cas QA
#: #20). Monter d'un cran dans la graduation socratique ne suffit pas : le
#: reproche du testeur ne portait pas sur le *niveau* de l'explication mais sur
#: sa **forme**, restée identique aux trois précédentes. La consigne nomme donc
#: des registres alternatifs plutôt que de demander vaguement « autre chose ».
CONSIGNE_VARIATION_APPROCHE = (
    "ATTENTION : l'élève signale que cette explication lui a déjà été donnée et "
    "qu'elle ne passe pas. Ne la reformule PAS dans les mêmes termes — répéter "
    "le même angle une fois de plus est précisément ce qu'il te reproche. Change "
    "de registre : pars d'un exemple numérique concret, ou décompose en étapes "
    "élémentaires vérifiables une par une, ou propose une analogie, ou décris la "
    "situation géométriquement. Commence par reconnaître que ton explication "
    "précédente n'a pas fonctionné, puis demande-lui quel point précis bloque."
)


def consigne_etude_de_fonction(etude: dict) -> str:
    """Consigne d'étude de fonction, adossée aux résultats SymPy (cas QA #9).

    Deux exigences tenues ensemble, et c'est leur conjonction qui fait la
    consigne. D'une part le livrable doit être **complet et direct** : l'élève
    demandait une étude et recevait une relance socratique. D'autre part les
    valeurs sont **déjà vérifiées** et ne doivent pas être recalculées par le
    modèle — les recalculer, c'est rouvrir la porte au résultat faux annoncé
    avec assurance que la règle n°2 interdit.

    Les champs absents (SymPy n'a pas conclu) ne sont simplement pas listés :
    le modèle n'a alors rien à en dire, ce qui vaut mieux qu'une approximation.
    """
    lignes = [
        "L'élève demande une ÉTUDE DE FONCTION. Voici les éléments établis par "
        f"l'outil de calcul symbolique pour f(x) = {etude['expression']} — ils sont "
        "vérifiés : reprends-les tels quels, ne les recalcule pas."
    ]
    lignes.append(f"- Domaine de définition : {etude['domaine']}")
    lignes.append(f"- Dérivée : f'(x) = {etude['derivee']}")
    if etude.get("limites"):
        limites = " ; ".join(f"lim en {borne} = {valeur}" for borne, valeur in etude["limites"])
        lignes.append(f"- Limites aux bornes : {limites}")
    if etude.get("variations"):
        variations = " ; ".join(
            f"{sens} sur {intervalle}" for intervalle, sens in etude["variations"]
        )
        lignes.append(f"- Sens de variation : {variations}")
    lignes.append(
        "Rédige l'étude complète dans cet ordre : domaine, limites aux bornes, "
        "dérivée et son signe, puis tableau de variation. Donne-la DIRECTEMENT et "
        "en entier — ne commence pas par une question, ne demande pas à l'élève de "
        "retrouver le domaine ou la dérivée. Tu peux terminer par une question "
        "d'approfondissement, une fois l'étude fournie."
    )
    return "\n".join(lignes)


def consigne_complexe(analyse: dict) -> str:
    """Éléments vérifiés d'un nombre complexe défini par l'énoncé (cas QA #6).

    Même contrat que :func:`consigne_etude_de_fonction` : les valeurs sont
    établies par SymPy et ne doivent pas être recalculées. La différence tient
    à ce qui était en jeu — ici l'agent disposait des bons extraits de cours et
    s'interdisait quand même tout résultat, faute d'avoir pu vérifier quoi que
    ce soit sur une expression où ``i`` n'était pas l'unité imaginaire.
    """
    nom = analyse["nom"]
    lignes = [
        f"L'élève travaille sur le nombre complexe {nom} = {analyse['forme']}. "
        "Les éléments suivants sont établis par l'outil de calcul symbolique — "
        "ils sont vérifiés : reprends-les tels quels, ne les recalcule pas.",
        f"- Partie réelle : Re({nom}) = {analyse['partie_reelle']}",
        f"- Partie imaginaire : Im({nom}) = {analyse['partie_imaginaire']}",
        f"- Conjugué : {nom}̄ = {analyse['conjugue']}",
        f"- Module : |{nom}| = {analyse['module']}",
    ]
    if analyse.get("argument"):
        lignes.append(f"- Argument : arg({nom}) = {analyse['argument']} (modulo 2π)")
    lignes.append(
        "Réponds à chaque question posée par l'énoncé, en t'appuyant sur ces "
        "valeurs et en expliquant la méthode qui y mène. Note que « I » est "
        "l'écriture de l'outil pour l'unité imaginaire : écris « i » à l'élève."
    )
    return "\n".join(lignes)


def consigne_correction_affirmation(operation: str, sujet: str, affirme: str, attendu: str) -> str:
    """Consigne de correction d'une affirmation fausse de l'élève (cas QA #15).

    Le texte porte le résultat **déjà vérifié symboliquement** : le modèle n'a
    donc rien à recalculer, seulement à corriger explicitement. Laisser la
    correction à sa charge, c'est risquer qu'il valide l'erreur — ce qui est
    exactement ce que le testeur a observé.
    """
    return (
        f"ATTENTION : l'élève affirme que la {operation} de {sujet} est {affirme}. "
        f"C'est FAUX — la vérification symbolique donne {attendu}. Tu dois corriger "
        "cette erreur explicitement et sans détour, avant toute autre chose : dis "
        "clairement que ce n'est pas le bon résultat, donne le résultat correct, puis "
        "explique brièvement d'où vient la confusion. Ne réponds surtout pas par une "
        "question ouverte qui laisserait l'élève croire qu'il avait raison."
    )


#: Consigne posée quand la recherche n'a remonté aucun extrait — soit le seuil
#: de pertinence les a tous écartés, soit le corpus ne couvre pas le cadre
#: demandé (cas QA #5).
#:
#: Le repli **divulgue puis aide** (décision D6) : taire l'absence de cours
#: laisserait croire à l'élève que la réponse s'appuie sur son programme, et
#: refuser tout net dégraderait des comportements déjà validés — les fixtures
#: positives #54 et #55 portent sur des dérivées, absentes des chapitres
#: indexés, et leur comportement confirmé est une réponse correcte.
#:
#: L'interdiction d'inventer reste entière : elle est portée par la vérification
#: symbolique et par :data:`AVERTISSEMENT_CALCUL_NON_VERIFIE`, pas par le
#: silence.
CONSIGNE_HORS_PERIMETRE = (
    "AUCUN extrait de cours ne correspond à cette question : ce point n'est pas "
    "couvert par les chapitres dont tu disposes. Dis-le à l'élève simplement et "
    "sans détour, en une phrase et sans t'excuser longuement — il doit savoir "
    "que ce qui suit ne vient pas de son programme. Puis aide-le quand même "
    "avec ce que tu sais, en restant prudent. N'invente AUCUNE référence à une "
    "leçon, à un chapitre ou à un cours que tu aurais consulté, et ne prétends "
    "pas que cette notion figure au programme."
)


def assemble_prompt(
    question: str,
    hint: HintDecision,
    retrieved: list[ScoredChunk],
    tool_result: str | None = None,
    curriculum_context: dict | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    *,
    calcul_non_verifie: bool = False,
    correction_affirmation: str | None = None,
    varier_approche: bool = False,
    etude_fonction: str | None = None,
    complexe: str | None = None,
) -> tuple[str, str]:
    """Retourne ``(system_prompt, user_prompt)`` assemblés.

    Le ``user_prompt`` agrège : contexte curriculaire, historique récent,
    extraits RAG, résultat de l'outil de calcul éventuel, la consigne
    d'indice, puis la question élève.

    ``calcul_non_verifie`` vient de ``route_tool`` : à vrai, l'interdiction
    :data:`AVERTISSEMENT_CALCUL_NON_VERIFIE` est ajoutée au prompt.

    ``varier_approche`` vient de ``detect_frustration`` : à vrai, la consigne
    :data:`CONSIGNE_VARIATION_APPROCHE` est ajoutée **avant** la consigne
    d'indice, qu'elle contraint sans la remplacer — le niveau reste la
    graduation socratique, la variation porte sur la forme.
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
    # Juste après le bloc d'extraits, dont elle explique le vide.
    if not retrieved:
        parts.append(CONSIGNE_HORS_PERIMETRE)
    if tool_result:
        parts.append(f"Résultat vérifié par l'outil de calcul : {tool_result}")
    if calcul_non_verifie:
        parts.append(AVERTISSEMENT_CALCUL_NON_VERIFIE)
    # Placée après le résultat d'outil et avant la consigne d'indice : corriger
    # une erreur de l'élève prime sur la graduation socratique (cas QA #15).
    if correction_affirmation:
        parts.append(correction_affirmation)
    if varier_approche:
        parts.append(CONSIGNE_VARIATION_APPROCHE)
    # Placée juste avant la consigne d'indice, qu'elle précise : l'étude est le
    # livrable, la graduation ne règle plus que le ton (cas QA #9).
    if etude_fonction:
        parts.append(etude_fonction)
    if complexe:
        parts.append(complexe)
    parts.append(
        f"Niveau d'indice : {hint.level} ({hint.label}).\nConsigne : {hint.instruction}"
    )
    parts.append(f"Question de l'élève : {question}")

    return SYSTEM_PERSONA, "\n\n".join(parts)


#: Consigne d'accueil (cas QA #38 et #41). Nommer ce qu'il ne faut PAS faire est
#: ici aussi utile que l'inverse : les deux testeurs ont reçu, l'un une question
#: de vérification de compréhension, l'autre une reformulation générique — deux
#: façons de répondre à un bonsoir par un exercice.
CONSIGNE_ACCUEIL = (
    "L'élève te salue, sans rien demander d'autre. Réponds d'abord à la "
    "salutation, simplement et chaleureusement, en une phrase. Présente-toi en "
    "une ligne, puis propose les chapitres ci-dessus et demande-lui sur quoi il "
    "veut travailler. N'enchaîne PAS sur une question de vérification de "
    "compréhension, ne reformule PAS sa salutation, et ne lance aucun exercice : "
    "il n'a encore rien demandé."
)


def assemble_accueil_prompt(
    question: str,
    catalogue: list[str],
    curriculum_context: dict | None = None,
) -> tuple[str, str]:
    """Retourne ``(system_prompt, user_prompt)`` pour une **salutation seule**.

    Même ancrage que le tour méta, et pour la même raison : proposer des
    chapitres suppose de savoir lesquels existent. Les lire dans le store plutôt
    que de les laisser au modèle évite d'accueillir un élève en lui proposant un
    chapitre absent — ce que le cas #28 reproche précisément à l'écran d'accueil.

    Aucun historique n'est réinjecté : une salutation ouvre un échange, et lui
    adjoindre le fil précédent inviterait à évoquer un passé que l'élève n'a pas
    convoqué (règle non-négociable n°3).
    """
    ctx = curriculum_context or {}
    parts: list[str] = []

    if catalogue:
        parts.append(
            "Chapitres réellement disponibles dans ta documentation "
            f"({len(catalogue)}) :\n" + "\n".join(f"- {c}" for c in catalogue)
        )
    else:
        parts.append(
            "Ta documentation ne contient actuellement AUCUN chapitre indexé. "
            "Accueille l'élève et dis-le franchement au lieu d'en citer un."
        )

    declare = ", ".join(
        f"{k}={v}" for k in ("niveau", "classe", "serie", "discipline") if (v := ctx.get(k))
    )
    if declare:
        parts.append(f"Cadre déclaré par l'élève (ne rien supposer au-delà) : {declare}.")

    parts.append(CONSIGNE_ACCUEIL)
    parts.append(f"Message de l'élève : {question}")
    return SYSTEM_PERSONA_META, "\n\n".join(parts)


def assemble_meta_prompt(
    question: str,
    catalogue: list[str],
    curriculum_context: dict | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    """Retourne ``(system_prompt, user_prompt)`` pour un tour **méta**.

    Aucun extrait RAG : la question porte sur la couverture du service, pas sur
    son contenu. L'ancrage factuel est le ``catalogue`` — la liste des chapitres
    réellement indexés, lue dans le store et non déduite d'une recherche.

    Le cadre curriculaire est réinjecté **en tant que déclaration de l'élève**,
    jamais comme un fait connu de l'agent : la règle « ne pas halluciner de
    contexte élève » interdit de prétendre savoir en quelle série il est si
    personne ne l'a dit.
    """
    ctx = curriculum_context or {}
    parts: list[str] = []

    if catalogue:
        parts.append(
            "Chapitres réellement disponibles dans ta documentation "
            f"({len(catalogue)}) :\n" + "\n".join(f"- {c}" for c in catalogue)
        )
    else:
        parts.append(
            "Ta documentation ne contient actuellement AUCUN chapitre indexé. "
            "Dis-le franchement à l'élève au lieu d'en citer un."
        )

    declare = ", ".join(
        f"{k}={v}" for k in ("niveau", "classe", "serie", "discipline") if (v := ctx.get(k))
    )
    if declare:
        parts.append(
            f"Cadre déclaré par l'élève (ne rien supposer au-delà) : {declare}."
        )

    history_block = build_history_block(conversation_history)
    if history_block:
        parts.append(f"Historique récent de la conversation :\n{history_block}")

    parts.append(f"Question de l'élève : {question}")
    return SYSTEM_PERSONA_META, "\n\n".join(parts)


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


#: Consigne ajoutée quand la recherche n'a remonté aucun chunk de cours.
#: Reprise de la doctrine du ``CoursAgent`` de NURU : sur un corpus fait
#: surtout de TD, il est fréquent qu'aucun cours n'existe sur une notion. Le
#: modèle doit alors le **dire**, pas combler le vide de lui-même — un cours
#: inventé est bien plus nuisible qu'un « je ne l'ai pas ».
AVERTISSEMENT_SANS_COURS = (
    "ATTENTION : les extraits fournis sont des TD et des exercices, sans cours "
    "explicite. N'extrais que les éléments de cours réellement présents "
    "(rappels en tête de TD, énoncés de propriétés). Indique clairement en "
    "introduction que le cours complet n'est pas disponible dans le corpus. "
    "N'invente sous aucun prétexte le contenu manquant."
)


def assemble_course_prompt(
    question: str,
    position: CoursePosition,
    retrieved: list[ScoredChunk],
    curriculum_context: dict | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    *,
    has_course: bool = True,
) -> tuple[str, str]:
    """Retourne ``(system_prompt, user_prompt)`` pour le **mode cours**.

    Le ``user_prompt`` agrège : cadre curriculaire, sommaire du cours avec la
    position courante, historique récent, extraits RAG, puis la consigne de la
    section à enseigner et la relance de l'élève. Aucune notion d'indice ici :
    la progression est portée par ``position`` (cf. ``course_plan.py``).

    ``has_course`` vient du re-ranker pédagogique : à faux, la consigne
    d'honnêteté :data:`AVERTISSEMENT_SANS_COURS` est ajoutée au prompt.
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
    # Décision D6, sur cette branche aussi. Elle n'y était pas, alors que c'est
    # ici qu'atterrissent « explique-moi les dérivées » et les « c'est quoi… » :
    # l'aveu de hors-périmètre ne partait donc jamais sur les tours qui en
    # avaient le plus besoin. Même placement qu'en mode exercice, juste après le
    # bloc d'extraits dont elle explique le vide.
    if not retrieved:
        parts.append(CONSIGNE_HORS_PERIMETRE)
    if not has_course:
        parts.append(AVERTISSEMENT_SANS_COURS)
    parts.append(
        f"Section à enseigner : {position.section_index + 1}. {section.title}.\n"
        f"Consigne : {section.instruction}"
    )
    parts.append(f"Message de l'élève : {question}")

    return SYSTEM_PERSONA_COURSE, "\n\n".join(parts)
