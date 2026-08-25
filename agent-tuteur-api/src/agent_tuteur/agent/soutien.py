"""Ouverture de soutien — ce que l'agent répond au découragement (cas QA #19/#21).

**Ce que ce module est, et ce qu'il n'est pas.** ``securite.py`` traite la
détresse : l'élève est en danger ou en souffrance, le pipeline est court-circuité
et il ne reçoit *que* le message de mise en sécurité. Ici, l'élève va bien mais
il se décourage — « je suis nul en maths », « je laisse tomber ». Il ne faut ni
le renvoyer vers un adulte (ce serait dramatiser un message d'élève au travail,
et banaliser celui du cas #7), ni lui recoller un paragraphe de cours comme si de
rien n'était (le reproche exact du testeur). Décision D5, point 1, tranchée le
2026-08-24 : **on dédramatise en une ouverture, puis le cours reprend.**

**Pourquoi le texte est écrit ici et non demandé au modèle.** Trois raisons, dans
l'ordre d'importance :

1. c'est la seule façon de tenir l'exigence du cas **#21** — « ne pas servir des
   réponses copiées-collées face à des signaux émotionnels différents ». Un texte
   écrit par le code peut être *choisi* : différent selon le signal, et différent
   d'un tour à l'autre. Une consigne de prompt, elle, ne fait qu'espérer ;
2. c'est ce qui rend le correctif jugeable en couche A. La prose du modèle ne
   l'est pas (``MockLLM`` renvoie une constante), et c'est précisément ce qui
   laissait ces deux cas ouverts en attendant D2 ;
3. sur ce registre, la variance de génération ne rend service à personne.

**Ce que ce module ne décide pas.** Il produit une *ouverture*, pas une réponse :
le tour continue son chemin normal (recherche, indice, cours). Le modèle est
prévenu qu'elle a déjà été adressée — ``prompt.CONSIGNE_SOUTIEN_DEJA_ADRESSE`` —
pour qu'il enchaîne sur l'aide concrète au lieu d'ouvrir sur sa propre formule
d'encouragement, ce qui donnerait deux préambules l'un sur l'autre.

**Frontière basse.** La détection du découragement vit dans ``frustration.py`` et
n'est pas redéfinie ici : une seule liste de motifs, déjà bornée contre le faux
positif nommé par D5 (« j'ai du mal en maths » est le message d'un élève qui
travaille, pas un abandon). Ce module n'ajoute qu'un second registre, l'abandon
annoncé, qui appelle une autre réponse que la dévalorisation de soi.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from agent_tuteur.agent.frustration import detecte_un_decouragement


class SignalSoutien(str, Enum):
    """Registre du message de l'élève. Deux signaux, deux réponses.

    Les confondre est exactement ce que le cas #21 reproche : « je suis nul »
    (l'élève met en cause sa valeur) et « je laisse tomber » (il annonce qu'il
    arrête) n'appellent pas la même chose — le premier demande qu'on démente,
    le second qu'on propose un pas plus petit.
    """

    #: L'élève met en cause sa valeur ou l'utilité de l'effort — cas QA #19.
    DECOURAGEMENT = "decouragement"
    #: L'élève annonce qu'il arrête, sans se dévaloriser — cas QA #21.
    ABANDON = "abandon"


#: Abandon annoncé. Volontairement **étroit** et distinct de ``_MARKERS``
#: (frustration) : « je ne comprends pas » ou « c'est trop dur » seuls sont le
#: signal ordinaire d'un élève au travail, qui appelle un indice, pas une
#: ouverture de soutien. Ce qui déclenche ici, c'est l'annonce d'arrêter.
_ABANDON = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"j['e]\s*abandonne",
        r"je\s+laisse\s+tomber",
        r"je\s+(?:vais\s+)?(?:tout\s+)?arr[êe]ter\s+(?:les\s+maths|la\s+le[çc]on|l['e]\s*exercice|tout)\b",
        r"j['e]\s*arr[êe]te\s+(?:les\s+maths|la\s+le[çc]on|l['e]\s*exercice|tout|l[àa])\b",
        r"[çc]a\s+(?:ne\s+)?vaut\s+pas\s+la\s+peine",
        r"je\s+(?:ne\s+)?continue\s+pas",
    )
]


@dataclass(frozen=True)
class OuvertureSoutien:
    """Ce que le tour ajoute en tête de réponse."""

    signal: SignalSoutien
    #: Clé stable de la variante servie. Tracée, et mémorisée dans la session
    #: pour que la suivante soit différente (cas #21).
    variante: str
    texte: str

    def as_trace(self) -> dict:
        return {"signal": self.signal.value, "variante": self.variante, "texte": self.texte}


#: Variantes par signal. Trois chacune : assez pour qu'un élève qui se décourage
#: deux fois dans la même session ne relise pas le même paragraphe, sans faire de
#: ce module un générateur de citations. Contraintes tenues sur chaque texte —
#: pas de mathématiques (le tour s'en charge ensuite), pas de promesse de
#: résultat, pas de redirection vers un adulte (c'est le registre du cas #7, et
#: l'y employer ici le userait), et une sortie qui rend la main au travail.
_VARIANTES: dict[SignalSoutien, tuple[tuple[str, str], ...]] = {
    SignalSoutien.DECOURAGEMENT: (
        (
            "valeur",
            "Je t'arrête tout de suite : être bloqué en maths ne dit rien de ce que tu "
            "vaux. C'est une matière qui s'apprend lentement, et être bloqué en fait "
            "partie. On reprend ensemble, en plus petit.",
        ),
        (
            "personne_ne_nait_bon",
            "Personne ne naît bon en maths — ce qui fait la différence, c'est le nombre "
            "de fois qu'on recommence, pas un talent qu'on aurait ou non. Reprenons "
            "doucement, à ton rythme.",
        ),
        (
            "pas_seul",
            "Ce que tu me dis là, beaucoup d'élèves de terminale le pensent, y compris "
            "ceux qui s'en sortent très bien ensuite. Ça ne me dit pas que tu n'y "
            "arriveras pas : ça me dit qu'on est allés trop vite. On recommence autrement.",
        ),
    ),
    SignalSoutien.ABANDON: (
        (
            "une_seule_etape",
            "Avant de laisser tomber, accorde-moi une étape — une seule, la plus petite "
            "possible. Si elle ne passe pas, on la redécoupe encore.",
        ),
        (
            "trop_vite",
            "Tu as le droit de trouver ça trop dur : le plus souvent, ça veut dire qu'on "
            "a sauté une marche avant. On redescend d'un cran, sur ce qui est déjà "
            "solide chez toi.",
        ),
        (
            "changer_de_chemin",
            "On ne laisse pas tomber tout de suite : on change de chemin. Je reprends "
            "autrement, et tu me dis à quel moment ça décroche.",
        ),
    ),
}


def detecte_un_abandon(question: str) -> bool:
    """Vrai si l'élève annonce qu'il arrête.

    À distinguer de la difficulté déclarée (« c'est trop dur », « je bloque »),
    qui reste le signal normal d'un élève au travail : ici il ne demande plus
    d'aide, il annonce qu'il s'arrête.
    """
    return any(motif.search(question) for motif in _ABANDON)


def detecter_signal_soutien(question: str) -> SignalSoutien | None:
    """Registre du message, ou ``None`` si le tour est ordinaire.

    Le découragement prime sur l'abandon quand les deux sont présents : « je
    suis nul, je laisse tomber » demande d'abord qu'on démente la dévalorisation
    — proposer un pas plus petit ne répond pas à cette phrase-là.
    """
    if detecte_un_decouragement(question):
        return SignalSoutien.DECOURAGEMENT
    if detecte_un_abandon(question):
        return SignalSoutien.ABANDON
    return None


def choisir_ouverture(
    signal: SignalSoutien, deja_servies: Sequence[str] = ()
) -> OuvertureSoutien:
    """Choisit une variante que la session n'a pas déjà servie.

    ``deja_servies`` est la liste des clés déjà employées dans la session, dans
    l'ordre. Quand toutes l'ont été, on repart au début plutôt que de renoncer :
    revenir sur une ouverture vue trois tours plus tôt vaut mieux que répéter
    celle du tour précédent, qui est le défaut exact rapporté par le cas #21.
    """
    variantes = _VARIANTES[signal]
    for cle, texte in variantes:
        if cle not in deja_servies:
            return OuvertureSoutien(signal=signal, variante=cle, texte=texte)
    rang = sum(1 for cle in deja_servies if cle in {c for c, _ in variantes})
    cle, texte = variantes[rang % len(variantes)]
    return OuvertureSoutien(signal=signal, variante=cle, texte=texte)


def ouverture_pour(question: str, deja_servies: Sequence[str] = ()) -> OuvertureSoutien | None:
    """Point d'entrée du graphe : l'ouverture due à ce message, ou ``None``."""
    signal = detecter_signal_soutien(question)
    if signal is None:
        return None
    return choisir_ouverture(signal, deja_servies)
