"""Détection de détresse élève et réponse de mise en sécurité.

**Pourquoi un module à part de ``guardrails``.** ``guardrails.moderate`` répond à
la question « ce contenu est-il inapproprié *pour* un mineur ? » (violence,
sexuel, haine). Ici la question est l'inverse : « cet élève est-il *en* danger ou
en souffrance ? ». Ce sont deux axes distincts, et les confondre a produit le
cas QA #7 : « je me fais harceler au lycée » ne déclenche aucun motif de
modération, l'élève est donc parti dans le pipeline d'exercice ordinaire.

**Pourquoi un disjoncteur et non une consigne de prompt.** Le mécanisme existant
(``_MODERATION_OVERRIDE``) est *consultatif* : il préfixe un paragraphe au prompt
et laisse le modèle décider. Sur ce périmètre, cela ne suffit pas — la règle
non-négociable n°1 impose de court-circuiter le pipeline (RAG, contenu
mathématique, continuation de cours). La réponse est donc **écrite ici, en dur**,
et n'est jamais échantillonnée par un modèle : c'est le seul endroit du produit
où la variance de génération est inacceptable, et le seul moyen d'éviter qu'un
modèle invente un numéro d'assistance.

**Détection heuristique regex-first**, dans l'esprit de ``frustration.py``,
``intent.py`` et ``hint_strategy.py`` : rapide, déterministe, sans appel réseau,
donc impossible à mettre en défaut par une panne de fournisseur.

**Frontière avec la frustration scolaire.** « je suis nul en maths », « c'est
trop dur », « j'abandonne » relèvent de ``frustration.py`` et de l'escalade
d'indices, pas de la détresse. Les motifs ci-dessous sont écrits pour ne pas les
capturer : banaliser le message d'aide en le déclenchant à chaque blocage lui
ferait perdre tout son sens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from agent_tuteur.textutil import strip_accents


class MotifDetresse(str, Enum):
    """Nature du signal détecté. Sert à moduler la réponse et à tracer."""

    #: Risque pour la vie ou l'intégrité physique — prime sur tout le reste.
    DANGER_IMMEDIAT = "danger_immediat"
    HARCELEMENT = "harcelement"
    MAL_ETRE = "mal_etre"
    ISOLEMENT = "isolement"
    DECOURAGEMENT_EXTREME = "decouragement_extreme"


#: Marqueur de première personne. Exigé en plus du motif lexical : « c'est quoi
#: le harcèlement ? » est une question sur une notion, pas une confidence.
_PREMIERE_PERSONNE = re.compile(r"(?:\bje\b|\bj'|\bme\b|\bm'|\bmoi\b|\bmon\b|\bma\b|\bmes\b)")

#: Élision tapée sans apostrophe : « j ai envie de pleurer », « je n ai pas d
#: amis ». Mesuré sur ce module, c'était le trou de rappel le plus large — il ne
#: ratait pas un motif exotique mais le **marqueur de première personne**
#: lui-même, donc *toute* confidence saisie ainsi, quelle que soit sa gravité.
#: Restreint à une consonne élidable isolée suivie d'une voyelle, ce qui ne
#: touche aucun mot français plein.
_ELISION_SANS_APOSTROPHE = re.compile(r"\b([cdjlmnst]) (?=[aeiouyh])")

#: Intensifieur intercalé, toléré au milieu d'un motif : « je me sens **tout**
#: seul », « je me sens **vraiment** mal ». Liste fermée à dessein — un « \w+ »
#: générique ferait entrer « je vais **avoir du** mal », c'est-à-dire la
#: difficulté scolaire ordinaire, dans le disjoncteur de sécurité.
_INTENSIFIEUR = r"(?:tout|toute|tres|si|vraiment|trop|super|hyper|tellement)\s+"

#: Motifs par nature, évalués dans l'ordre de gravité décroissante. Le texte est
#: comparé **sans accents et en minuscules** : les motifs sont donc écrits sans
#: accent, ce qui les rend aussi robustes aux saisies non accentuées des élèves.
_MOTIFS: tuple[tuple[MotifDetresse, tuple[str, ...]], ...] = (
    (
        MotifDetresse.DANGER_IMMEDIAT,
        (
            r"me\s+suicider", r"\bsuicide\b", r"me\s+tuer", r"envie\s+de\s+mourir",
            r"je\s+veux\s+mourir", r"me\s+faire\s+du\s+mal", r"automutilation",
            r"me\s+scarifier", r"envie\s+de\s+disparaitre", r"\bme\s+frapper\s+moi\b",
        ),
    ),
    (
        MotifDetresse.HARCELEMENT,
        (
            r"harcel",                       # harcèle, harceler, harcèlement
            r"se\s+moqu\w*\s+de\s+moi", r"on\s+se\s+moque\s+de\s+moi",
            r"me\s+fais\s+(?:frapper|taper|battre|insulter|humilier)",
            r"me\s+(?:frappent|tapent|battent|insultent|humilient|rejettent)",
            r"victime\s+de", r"bouc\s+emissaire", r"souffre.?douleur",
            r"intimid\w+\s+(?:a|au|en)\s+",
            r"me\s+tape\s+dessus", r"racket",
        ),
    ),
    (
        MotifDetresse.MAL_ETRE,
        (
            r"je\s+suis\s+(?:triste|deprim\w*|mal\s+dans\s+ma\s+peau)",
            r"je\s+deprim\w*",               # « je déprime », sans « je suis »
            r"envie\s+de\s+pleurer", r"je\s+pleure\s+(?:tout|tous|souvent|sans)",
            r"plus\s+gout\s+a\s+rien",
            # « mal » adverbe de manière — « je vais mal placer la virgule » —
            # n'est pas « je vais mal ». L'infinitif qui suit trahit le premier.
            rf"je\s+(?:vais|me\s+sens)\s+(?:{_INTENSIFIEUR})?mal\b(?!\s+\w+(?:er|ir|re)\b)",
            r"je\s+n'?ai\s+plus\s+envie\s+de\s+rien", r"je\s+souffre\b",
        ),
    ),
    (
        MotifDetresse.ISOLEMENT,
        (
            r"aucun\s+ami", r"pas\s+d'?amis?\b", r"personne\s+ne\s+(?:veut\s+)?me\s+parle",
            rf"toujours\s+(?:{_INTENSIFIEUR})?seul", rf"je\s+me\s+sens\s+(?:{_INTENSIFIEUR})?seul",
            r"personne\s+ne\s+m'?aime", r"tout\s+le\s+monde\s+m'?ignore",
        ),
    ),
    (
        MotifDetresse.DECOURAGEMENT_EXTREME,
        (
            r"je\s+ne?\s*sers\s+a\s+rien", r"je\s+ne?\s+vaux\s+rien",
            r"ma\s+vie\s+ne\s+vaut\s+rien", r"je\s+suis\s+un\s+rate\b",
            r"(?:veux|voudrais|vais)\s+arreter\s+(?:l'?ecole|les\s+cours|le\s+lycee)",
        ),
    ),
)

_COMPILES: tuple[tuple[MotifDetresse, tuple[re.Pattern, ...]], ...] = tuple(
    (motif, tuple(re.compile(p) for p in motifs)) for motif, motifs in _MOTIFS
)


@dataclass(frozen=True)
class SignalDetresse:
    """Résultat du triage. ``nature is None`` signifie « pipeline normal »."""

    nature: MotifDetresse | None = None
    #: Motif lexical ayant déclenché — utile en journal, jamais montré à l'élève.
    declencheur: str = ""

    @property
    def detectee(self) -> bool:
        return self.nature is not None


def detecter_detresse(question: str) -> SignalDetresse:
    """Triage déterministe d'un message élève.

    Renvoie le premier motif reconnu par ordre de gravité décroissante.
    """
    plat = strip_accents(question.replace("’", "'")).lower()
    plat = _ELISION_SANS_APOSTROPHE.sub(r"\1'", plat)
    if not _PREMIERE_PERSONNE.search(plat):
        return SignalDetresse()
    for nature, motifs in _COMPILES:
        for motif in motifs:
            if motif.search(plat):
                return SignalDetresse(nature=nature, declencheur=motif.pattern)
    return SignalDetresse()


# --- Réponse de mise en sécurité ---------------------------------------------

#: Ressources d'aide affichées en complément de la redirection vers un adulte.
#:
#: ⚠️ **VIDE VOLONTAIREMENT — à compléter et à vérifier par un humain avant toute
#: mise en production.** Un numéro d'assistance erroné est activement nuisible, et
#: aucun numéro ne doit être ajouté ici sans avoir été vérifié auprès de la source
#: officielle sénégalaise. Tant que ce tuple est vide, la réponse s'appuie
#: uniquement sur la redirection vers un adulte de confiance, ce que la règle
#: non-négociable n°1 autorise explicitement (« un adulte de confiance **ou** une
#: ressource d'aide »).
RESSOURCES_AIDE: tuple[str, ...] = ()

_RECONNAISSANCE = (
    "Merci de m'en parler. Ce que tu vis est important, et ce n'est pas de ta faute."
)

_RECONNAISSANCE_URGENTE = (
    "Merci de m'en parler, et je te crois. Ce que tu vis en ce moment est grave, "
    "et tu n'es pas seul."
)

_REDIRECTION = (
    "Je suis un assistant scolaire : je ne suis pas la bonne personne pour t'aider "
    "là-dessus, et surtout, tu ne dois pas rester seul avec ça.\n\n"
    "Parles-en dès que tu peux à un adulte de confiance : un parent, un professeur, "
    "le surveillant général, l'infirmerie de ton établissement, ou n'importe quel "
    "adulte à qui tu te sens capable de le dire. En parler à quelqu'un change "
    "vraiment les choses."
)

_REDIRECTION_URGENTE = (
    "Je suis un assistant scolaire et je ne peux pas t'aider seul sur ce sujet. "
    "Ce qui compte maintenant, c'est que tu en parles à un adulte **aujourd'hui** : "
    "un parent, un professeur, l'infirmerie de ton établissement, ou n'importe quel "
    "adulte de confiance autour de toi. Si tu es en danger immédiat, va voir un "
    "adulte tout de suite, sans attendre."
)

_CLOTURE = "Je reste là pour les mathématiques quand tu en auras envie."


def reponse_detresse(signal: SignalDetresse) -> str:
    """Message déterministe de reconnaissance + redirection.

    Aucun contenu pédagogique, aucune relance socratique : le tour sert
    uniquement à orienter l'élève vers un humain.
    """
    urgent = signal.nature is MotifDetresse.DANGER_IMMEDIAT
    morceaux = [
        _RECONNAISSANCE_URGENTE if urgent else _RECONNAISSANCE,
        _REDIRECTION_URGENTE if urgent else _REDIRECTION,
    ]
    if RESSOURCES_AIDE:
        lignes = "\n".join(f"- {r}" for r in RESSOURCES_AIDE)
        morceaux.append(f"Tu peux aussi contacter :\n{lignes}")
    morceaux.append(_CLOTURE)
    return "\n\n".join(morceaux)
