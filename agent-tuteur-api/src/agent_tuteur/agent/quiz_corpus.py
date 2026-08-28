"""Questions d'évaluation **lues dans le corpus**, jamais générées.

Pourquoi ce module existe (décision **D12**, option 2). La posture *quiz*
demandait ses questions au modèle, et rien ne vérifiait la réponse déclarée.
Mesuré le 2026-08-28 sur la stack réelle, dès le premier essai :

    « u₀ = 2 et u(n+1) = 3u(n) − 4 : quelle est la valeur de u₂ ? »
    Réponse déclarée par le modèle : 14.

Or 2 est le point fixe de cette récurrence : u₁ = u₂ = 2. L'élève qui répondait
juste s'entendait dire qu'il avait tort — pire que pas de quiz du tout, parce
que c'est la confiance dans le tuteur qui se perd là.

Les leçons du corpus portent une section « 18. Auto-évaluation » dont les items
sont **rédigés et corrigés par l'auteur de la leçon**. Les lire plutôt que de
les faire produire rend la question juste *par construction* : il n'y a plus de
réponse à vérifier, il y a une réponse écrite par un humain qui connaît le
programme.

Ce que cela coûte, et qui est assumé : moins de variété (trois items Vrai/Faux
par chapitre aujourd'hui), et une dépendance à des sections qui ne sont pas
toujours remplies. Quand il n'y a rien, on le dit — on ne retombe pas sur la
génération, sinon le défaut reviendrait par la porte de service.
"""

from __future__ import annotations

import random
import re
from collections.abc import Iterable
from dataclasses import dataclass

from agent_tuteur.agent.course_plan import titre_de_section

#: Titre de la section du format pilote qui porte les questions d'évaluation.
TITRE_AUTO_EVALUATION = "Auto-évaluation"

#: Identifiants des deux propositions d'un vrai/faux. Le contrat d'API compare
#: des identifiants (``QuizChoiceOut.id``), pas des libellés.
ID_VRAI, ID_FAUX = "A", "B"

#: Un item vrai/faux : « 1. Énoncé. (Faux — explication) ».
#:
#: La parenthèse de la réponse est reconnue par ce qu'elle n'est **pas** :
#: précédée d'une contre-oblique, elle serait un délimiteur LaTeX (« \\( 2\\pi \\) »).
#: Le lookbehind est donc ce qui empêche de prendre une formule pour un verdict.
_ITEM_VRAI_FAUX = re.compile(
    r"^\s*\d+\.\s*(?P<enonce>.+?)\s*(?<!\\)\((?P<verdict>Vrai|Faux)\b(?P<explication>.*)\)\s*$",
    re.IGNORECASE,
)

#: Énoncé d'un QCM : « 1. Le module de … est : ». Les propositions suivent sur
#: la ligne d'après.
_ENONCE_QCM = re.compile(r"^\s*(?P<numero>\d+)\.\s*(?P<enonce>.+?)\s*$")

#: Propositions d'un QCM : « a) 5 b) 7 c) 1 d) 25 ».
_PROPOSITIONS_QCM = re.compile(r"(?<![\w\\])(?P<lettre>[a-d])\)\s*(?P<texte>.*?)(?=(?:(?<![\w\\])[a-d]\)|$))")

#: Clé de correction d'un QCM, quand l'auteur en fournit une : « (Réponse : b) »
#: ou « → b ». **Aucune leçon n'en porte aujourd'hui** (mesuré sur les 12) : les
#: QCM du corpus sont donc inexploitables tels quels, et ce module les écarte
#: plutôt que d'inventer la réponse. Le motif existe pour que l'ajout d'une clé
#: dans les leçons suffise à les rendre servables, sans toucher au code.
_CLE_QCM = re.compile(
    r"(?:\(\s*r[ée]ponse\s*:?\s*(?P<lettre>[a-d])\s*\)|→\s*(?P<fleche>[a-d])\b)",
    re.IGNORECASE,
)

#: Sous-titres de la section d'auto-évaluation.
_SOUS_TITRE = re.compile(r"^\s*#{2,4}\s*(?P<titre>.+?)\s*$")


@dataclass(frozen=True)
class QuestionCorpus:
    """Une question prête à servir, avec sa réponse — les deux venant du corpus."""

    type: str  #: « qcm » ou « vrai_faux »
    enonce: str
    #: Propositions ``(identifiant, texte)``, dans l'ordre d'affichage.
    choix: tuple[tuple[str, str], ...]
    #: Identifiant de la bonne proposition.
    reponse: str
    explication: str


def _nettoyer_explication(brut: str) -> str:
    """Retire le tiret d'introduction : « — c'est z·z̄ » → « c'est z·z̄ »."""
    return brut.strip().lstrip("—–-").strip()


def extraire_les_questions(texte: str) -> list[QuestionCorpus]:
    """Questions exploitables d'une section « Auto-évaluation ».

    « Exploitable » veut dire : la bonne réponse est **écrite dans le corpus**.
    Un QCM sans clé de correction est donc ignoré — c'est le cas de tous ceux
    des 12 leçons actuelles, et c'est exactement ce qu'il ne faut pas combler
    par une génération.
    """
    questions: list[QuestionCorpus] = []
    sous_section = ""
    lignes = texte.splitlines()

    for index, ligne in enumerate(lignes):
        if (entete := _SOUS_TITRE.match(ligne)) and not ligne.lstrip().startswith("1"):
            sous_section = entete.group("titre").lower()
            continue

        if "vrai" in sous_section and (item := _ITEM_VRAI_FAUX.match(ligne)):
            vrai = item.group("verdict").lower() == "vrai"
            questions.append(
                QuestionCorpus(
                    type="vrai_faux",
                    enonce=item.group("enonce").strip(),
                    choix=((ID_VRAI, "Vrai"), (ID_FAUX, "Faux")),
                    reponse=ID_VRAI if vrai else ID_FAUX,
                    explication=_nettoyer_explication(item.group("explication"))
                    or ("Affirmation exacte." if vrai else "Affirmation inexacte."),
                )
            )
            continue

        if sous_section.startswith("qcm") and (enonce := _ENONCE_QCM.match(ligne)):
            suite = lignes[index + 1] if index + 1 < len(lignes) else ""
            if (question := _lire_un_qcm(enonce.group("enonce"), suite)) is not None:
                questions.append(question)

    return questions


def _lire_un_qcm(enonce: str, ligne_propositions: str) -> QuestionCorpus | None:
    """QCM complet, ou ``None`` s'il manque les propositions **ou la clé**."""
    propositions = [
        (m.group("lettre").upper(), m.group("texte").strip())
        for m in _PROPOSITIONS_QCM.finditer(ligne_propositions)
        if m.group("texte").strip()
    ]
    if len(propositions) < 2:
        return None

    cle = _CLE_QCM.search(enonce) or _CLE_QCM.search(ligne_propositions)
    if cle is None:
        return None
    lettre = (cle.group("lettre") or cle.group("fleche")).upper()
    if lettre not in {identifiant for identifiant, _ in propositions}:
        return None

    return QuestionCorpus(
        type="qcm",
        enonce=_CLE_QCM.sub("", enonce).strip(),
        choix=tuple(propositions),
        reponse=lettre,
        explication=f"La bonne réponse est {lettre}.",
    )


def questions_du_chapitre(chunks: Iterable) -> list[QuestionCorpus]:
    """Questions portées par la section d'auto-évaluation de ces extraits.

    ``chunks`` est une suite de ``ScoredChunk`` — typiquement le retour de
    ``HybridRetriever.chunks_du_chapitre``, qui ratisse un chapitre entier par
    filtre de métadonnées et non par similarité : la section voulue est atteinte
    quelle que soit sa ressemblance avec la demande de l'élève.
    """
    questions: list[QuestionCorpus] = []
    for chunk in chunks:
        texte = chunk.chunk.text
        titre = titre_de_section(texte) or ""
        if TITRE_AUTO_EVALUATION.lower() in titre.lower():
            questions.extend(extraire_les_questions(texte))
    return questions


def choisir(
    questions: list[QuestionCorpus], quiz_type: str, *, rng: random.Random | None = None
) -> QuestionCorpus | None:
    """Une question du type demandé, tirée au sort, ou ``None`` s'il n'y en a pas.

    Le tirage porte sur le **choix** de la question, jamais sur son contenu :
    c'est ce qui donne un peu de variété à un corpus fini sans rouvrir la porte
    à une réponse inventée. ``rng`` permet aux tests de fixer le tirage.
    """
    candidates = [question for question in questions if question.type == quiz_type]
    if not candidates:
        return None
    return (rng or random).choice(candidates)
