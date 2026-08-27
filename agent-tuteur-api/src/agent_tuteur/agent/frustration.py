"""Détection de frustration / blocage — **état de session éphémère**.

Cet état (questions récentes) n'est *jamais* persisté dans la mémoire élève :
seul le résultat notable (compétence, niveau d'indice atteint) l'est, plus tard,
au nœud de composition. Le score combine deux signaux : la répétition de la même
question et des marqueurs de ton.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_tuteur.textutil import jaccard

# Seuil de similarité au-delà duquel deux questions sont « la même ».
REPETITION_THRESHOLD = 0.8
# Nombre de questions récentes comparées.
WINDOW = 5

_MARKERS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"je\s+(?:ne\s+)?comprends?\s+pas",
        r"j['e]\s*(?:y\s+)?arrive\s+pas",
        r"donne(?:[\s-]+moi)?\s+(?:la|ta)\s+r[ée]ponse",
        r"je\s+bloque",
        r"c['e]est\s+trop\s+dur",
        r"j['e]\s*abandonne",
        # Même chose que « j'abandonne », dans les mots que les élèves
        # emploient réellement : « je laisse tomber » n'était couvert par aucun
        # marqueur, si bien que le cas QA #21 plafonnait au seul « c'est trop
        # dur ». Deux façons de dire la même chose ne doivent pas produire deux
        # scores.
        r"je\s+laisse\s+tomber",
        r"je\s+(?:ne\s+)?sais\s+pas",
        r"\bchais\s+pas\b",
        r"aide[\s-]+moi",
    )
]

#: Découragement : l'élève ne dit pas qu'il bute sur une notion, il dit qu'il
#: ne vaut rien en maths ou que l'effort est vain. Mesuré (cf. DECISIONS.md, D5)
#: : « Je suis nul en maths, ça sert à rien d'essayer » sortait à **0.0**, quand
#: « c'est trop dur, je laisse tomber » sortait à 0.4 et « je ne comprends pas »
#: à 0.4. Le signal n'était détecté par rien — ni ici, ni par ``securite.py``
#: dont la frontière documentée l'exclut volontairement.
#:
#: Liste tenue **étroite** à dessein, et c'est le corollaire nommé en D5 : un
#: motif large capterait « je suis nul » au sens de « j'ai du mal », c'est-à-dire
#: le message que l'élève envoie précisément *en travaillant*. Chaque motif exige
#: donc le jugement de valeur (« nul », « pas fait pour ») ou la futilité de
#: l'effort (« ça sert à rien d'essayer »), jamais la difficulté seule.
#:
#: Ce que ce module produit s'arrête au **signal**. Ce qu'il faut en faire —
#: disjoncteur déterministe comme le cas #7, ou modulation du ton — reste ouvert
#: (D5, point 1) : le débat portait jusqu'ici sur un signal que rien ne
#: produisait.
_DECOURAGEMENT = [
    re.compile(p, re.IGNORECASE)
    for p in (
        # « nulle part » n'est pas un jugement de valeur.
        r"je\s+suis\s+(?:vraiment\s+|trop\s+|tellement\s+|si\s+)?nul(?:le)?\b(?!\s*part)",
        r"je\s+suis\s+(?:un|une)\s+(?:cas\s+d[ée]sesp[ée]r[ée]|catastrophe|bon\s+[àa]\s+rien)",
        r"je\s+(?:ne\s+)?suis\s+pas\s+fait[e]?\s+pour",
        r"[çc]a\s+(?:ne\s+)?sert\s+[àa]\s+rien\s+(?:d['e]\s*|de\s+)"
        r"(?:essayer|travailler|r[ée]viser|continuer|insister|s['e]\s*accrocher|bosser)",
        r"j['e]\s*(?:y\s+)?arriverai\s+jamais",
        r"je\s+(?:n['e]\s*)?(?:y\s+)?arriverai\s+jamais",
        r"je\s+(?:ne\s+)?comprendrai\s+jamais",
        r"je\s+(?:ne\s+)?serai\s+jamais\s+bon",
    )
]


@dataclass
class SessionState:
    """Contexte conversationnel volatile d'un élève (non persisté)."""

    student_id: str = "anonymous"
    tenant_id: str = "default"
    recent_questions: list[str] = field(default_factory=list)
    #: Série **déclarée par l'élève** au cours de la session, forme canonique.
    #: ``None`` tant qu'il n'a rien dit : l'absence est une information, et la
    #: combler par une valeur par défaut est exactement le bug du cas QA #8.
    #: Écrite par le nœud ``profil_eleve``, elle prime sur la série du profil
    #: pour tout le reste de la session (règle non-négociable n°5).
    serie: str | None = None
    #: Clés des ouvertures de soutien déjà servies dans la session, dans
    #: l'ordre. Éphémère comme le reste : ce n'est pas un fait pédagogique à
    #: persister, seulement de quoi ne pas resservir le même paragraphe au tour
    #: suivant — le reproche exact du cas QA #21.
    ouvertures_soutien: list[str] = field(default_factory=list)

    def add(self, question: str) -> None:
        self.recent_questions.append(question)
        # Ne garde qu'une fenêtre glissante.
        if len(self.recent_questions) > WINDOW * 2:
            self.recent_questions = self.recent_questions[-WINDOW * 2 :]


#: Blocage que l'élève **déclare** lui-même : il signale que l'explication a
#: déjà été donnée, sans reposer la même question. ``count_repetitions`` ne peut
#: pas le voir — il compare la question courante aux précédentes, or « Ça fait
#: 3 fois que tu m'expliques » ne ressemble à aucune d'elles. C'est pourtant le
#: signal le plus fiable dont on dispose : l'élève l'énonce (cas QA #20).
_BLOCAGE_DECLARE = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"[çc]a\s+fait\s+\w+\s+fois",
        r"\b(?:pour|c['e]est)\s+la\s+\w+\s*(?:i[èe]me|e)\s+fois",
        r"tu\s+(?:m['e]\s*)?(?:as\s+)?d[ée]j[àa]\s+(?:dit|expliqu|r[ée]pondu)",
        r"tu\s+(?:me\s+)?r[ée]p[èe]tes?\s+(?:toujours\s+)?la\s+m[êe]me",
        r"(?:tu\s+dis|c['e]est)\s+(?:toujours\s+)?la\s+m[êe]me\s+chose",
        r"je\s+(?:ne\s+)?comprends?\s+toujours\s+pas",
        r"encore\s+une\s+fois",
    )
]


#: Demande explicite de **reformulation simplifiée** (cas QA #39). Distincte du
#: blocage déclaré : l'élève ne dit pas qu'on lui a déjà expliqué, il dit que
#: l'explication reçue est trop compliquée pour lui. Le registre est en cause,
#: pas le nombre de tentatives — et le signal existe dans ses mots, il n'y a
#: rien à inférer.
#:
#: Le motif exige la demande de simplification elle-même (« plus simplement »,
#: « en plus simple », « avec des mots simples », « trop compliqué ») : « je
#: n'ai rien compris » tout seul reste une difficulté ordinaire, déjà couverte
#: par les marqueurs de ton.
_DEMANDE_SIMPLIFICATION = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bplus\s+simple(?:ment)?\b",
        r"\b(?:en|de\s+fa[çc]on|de\s+mani[èe]re)\s+plus\s+simple\b",
        r"\bsimplifie[\s-]?(?:moi|le|la)?\b",
        r"\bavec\s+des\s+mots\s+simples\b",
        r"\bplus\s+facile\s+[àa]\s+comprendre\b",
        r"\bc['’e]est\s+(?:trop\s+)?(?:compliqu[ée]|complexe|dur)\s+[àa]\s+comprendre\b",
        r"\bexplique[\s-]?(?:moi|le|la)?\s+(?:[çc]a\s+)?autrement\b",
        r"\bre(?:formule|explique|prends?)\b[^?.!]{0,20}?\b(?:simple(?:ment)?|autrement|"
        r"plus\s+clair(?:ement)?)\b",
        r"\bje\s+(?:ne\s+)?comprends?\s+rien\s+[àa]\s+tes\s+explications\b",
    )
]


@dataclass
class FrustrationSignal:
    score: float
    repetitions: int
    markers: int
    #: L'élève signale explicitement qu'on lui a déjà expliqué. Distinct de
    #: ``repetitions``, qui est *observé* : garder les deux séparés permet de
    #: dire dans la trace lequel des deux a déclenché le changement d'approche.
    blocage_declare: bool = False
    #: L'élève met en cause sa valeur ou l'utilité de l'effort, et non la
    #: difficulté d'une notion (cas QA #19). Champ distinct de ``markers`` :
    #: les deux registres appellent des réponses différentes, et les confondre
    #: dans un compteur rendrait le second invisible à qui lit la trace.
    decouragement: bool = False
    #: L'élève demande explicitement une explication plus simple (cas QA #39).
    #: Troisième registre distinct, pour la même raison que les deux précédents :
    #: la réponse attendue n'est ni un cran d'indice de plus, ni un changement
    #: d'angle, mais un exemple concret et des mots plus simples.
    demande_simplification: bool = False


def count_repetitions(question: str, recent: list[str]) -> int:
    """Nombre de questions récentes très similaires à la question courante."""
    window = recent[-WINDOW:]
    return sum(1 for prev in window if jaccard(question, prev) >= REPETITION_THRESHOLD)


def count_markers(question: str) -> int:
    return sum(1 for pattern in _MARKERS if pattern.search(question))


def detecte_un_blocage_declare(question: str) -> bool:
    """Vrai si l'élève dit lui-même que l'explication a déjà été donnée."""
    return any(pattern.search(question) for pattern in _BLOCAGE_DECLARE)


def detecte_un_decouragement(question: str) -> bool:
    """Vrai si l'élève met en cause sa valeur ou l'utilité de l'effort.

    À distinguer de la difficulté déclarée (« je ne comprends pas », « c'est
    trop dur »), qui est le signal normal d'un élève au travail : ici l'élève ne
    parle plus de la notion mais de lui.
    """
    return any(pattern.search(question) for pattern in _DECOURAGEMENT)


def demande_une_simplification(question: str) -> bool:
    """Vrai si l'élève demande explicitement une explication plus simple."""
    return any(pattern.search(question) for pattern in _DEMANDE_SIMPLIFICATION)


def detect_frustration(question: str, session: SessionState) -> FrustrationSignal:
    """Score : ``min(1, 0.3*rep + 0.4*marqueurs + 0.3*blocage + 0.4*découragement)``.

    Le terme de blocage déclaré pèse autant qu'une répétition observée, et pour
    la même raison : dans les deux cas l'élève a déjà reçu l'explication. Sans
    lui, « Ça fait 3 fois que tu m'expliques, je comprends pas » plafonnait à
    0,4 — juste sous le seuil d'escalade de 0,5 — et l'agent repartait sur un
    « Rappel de notion », c'est-à-dire le même registre une fois de plus.

    Le terme de découragement pèse comme **un** marqueur de ton, ni plus ni
    moins, et c'est délibéré : seul, il porte le tour à 0,4, donc sous le seuil
    d'escalade de ``hint_strategy``. Le signal existe et se lit dans la trace
    sans que ce module décide à la place de D5 ce qu'il faut en faire — ce qui
    était exactement l'ordre demandé (« combler la détection d'abord »). Il
    pousse au-dessus du seuil dès qu'un second signal l'accompagne, ce qui est
    le comportement déjà appliqué à tous les autres cumuls.
    """
    repetitions = count_repetitions(question, session.recent_questions)
    markers = count_markers(question)
    blocage = detecte_un_blocage_declare(question)
    decouragement = detecte_un_decouragement(question)
    simplification = demande_une_simplification(question)
    score = min(1.0, 0.3 * repetitions + 0.4 * markers + 0.3 * blocage + 0.4 * decouragement)
    return FrustrationSignal(
        score=round(score, 4),
        repetitions=repetitions,
        markers=markers,
        blocage_declare=blocage,
        decouragement=decouragement,
        # Volontairement HORS du score : une demande de simplification ne dit
        # rien de plus sur ce qu'il faut dévoiler à l'élève, elle dit comment le
        # dire. La faire peser sur la graduation socratique reviendrait à
        # répondre « voilà un cran de solution de plus » à quelqu'un qui demande
        # des mots plus simples. Son effet propre est décidé dans
        # ``hint_strategy.ajuster_pour_simplification``.
        demande_simplification=simplification,
    )
