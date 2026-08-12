"""Profil élève déclaré **en session** — détection et mémorisation de la série.

Cas QA #8 : une élève de S2 s'est vu attribuer la série S1, et l'agent a
persisté après deux corrections explicites. Le diagnostic est que
:class:`~agent_tuteur.agent.frustration.SessionState` ne portait aucune série :
elle transitait uniquement par le ``curriculum_context`` fourni à chaque appel,
c'est-à-dire par le profil du compte. Une correction dite par l'élève n'avait
donc littéralement nulle part où être retenue, et le contexte d'origine
reprenait la main au tour suivant.

Deux règles non-négociables se rencontrent ici, et elles tirent en sens
inverse :

* la n°5 impose qu'une correction explicite soit retenue **immédiatement et
  pour toute la session** — d'où la primauté de la série déclarée sur celle du
  profil, et non l'inverse ;
* la n°3 interdit d'inventer un contexte élève — d'où le refus de deviner. « Je
  suis en classe de terminale » ne nomme aucune série : le module renvoie
  ``None`` et rien n'est écrit. C'est exactement le prompt du cas #8, et c'est
  précisément parce que l'agent avait comblé ce vide par « S1 » que le bug a
  été remonté.

La détection exige une **tournure déclarative** (« je suis en… », « ma série
c'est… », « plutôt… ») et pas seulement la présence d'un libellé : en
mathématiques, « S2 » désigne bien plus souvent le deuxième terme d'une suite
que la série de l'élève. Sans cette exigence, « calcule S2 pour la suite
définie par… » réécrirait le profil de l'élève au milieu d'un exercice.
"""

from __future__ import annotations

import re

from agent_tuteur.config.taxonomy import canonical_serie

#: Tournure par laquelle un élève s'attribue une série, cherchée dans le texte
#: qui **précède** un libellé candidat (d'où l'ancre finale).
#:
#: ``plutôt`` et ``non`` couvrent la forme réellement employée en correction
#: (« non, plutôt S2 »), qui est le cœur du cas #8 : c'est la deuxième et la
#: troisième tentative de l'élève qui n'étaient pas entendues.
_MARQUEUR = re.compile(
    r"(?:je\s+suis|j['’e]\s*[ée]tudie|je\s+fais|nous\s+sommes|on\s+est|"
    r"ma\s+s[ée]rie|ma\s+classe|je\s+passe|je\s+pr[ée]pare|plut[ôo]t|non)"
    r"[^.!?]{0,40}$",
    re.IGNORECASE,
)

#: Négation portant sur la série qui suit : « je ne suis PAS en S1 ». Dire ce
#: qu'on n'est pas ne dit pas ce qu'on est — le libellé nié n'est pas retenu.
_NEGATION = re.compile(
    r"\b(?:pas|jamais|plus|ni)\s+(?:en\s+|dans\s+la\s+|de\s+la\s+|la\s+)?"
    r"(?:s[ée]rie\s+)?(?:terminale\s+|term\.?\s+|tle\s+)?$",
    re.IGNORECASE,
)

#: Forme lexicale d'un libellé de série (« S2 », « TS2 », « STIDD1 », « L'1 »).
_CANDIDAT = re.compile(r"\b([A-Za-z]{1,5}['’]?\d{0,2}[a-z]?)\b")


def _est_un_libelle_plausible(brut: str) -> bool:
    """Écarte les mots français que la taxonomie reconnaîtrait par accident.

    « LA » est une série littéraire ; « la » est un article, et il précède
    justement le mot « série ». Même piège avec « G » (série gestion). La règle
    retenue : un libellé en minuscules n'est accepté que s'il porte un chiffre
    (« s2 », « ts2 », « stidd1 »), sinon il doit comporter une majuscule comme
    on l'écrit partout ailleurs dans le corpus.
    """
    if any(c.isupper() for c in brut):
        return True
    return any(c.isdigit() for c in brut)


def detecter_serie(question: str) -> str | None:
    """Série **explicitement déclarée** par l'élève, sous forme canonique.

    Renvoie ``None`` si aucune déclaration n'est trouvée, ou si le libellé
    capté n'est pas une série connue de la taxonomie — jamais une supposition.
    « TS2 » est ramené à « S2 » (forme canonique) pour qu'une correction dite
    dans une nomenclature soit reconnue comme identique à la même série dite
    dans l'autre.

    Quand plusieurs déclarations coexistent dans un même message (« je suis en
    S1, enfin non plutôt en S2 »), c'est la **dernière** qui gagne : elle se lit
    comme la correction de celle qui précède. Le balayage est fait libellé par
    libellé, et non par une seule expression rationnelle globale : une tournure
    intermédiaire non concluante ne doit pas absorber la déclaration qui suit.
    """
    retenue: str | None = None
    for match in _CANDIDAT.finditer(question):
        brut = match.group(1)
        if not _est_un_libelle_plausible(brut):
            continue
        canonique = canonical_serie(brut)
        if canonique is None:
            continue
        amont = question[: match.start()]
        if _NEGATION.search(amont):
            continue
        if _MARQUEUR.search(amont):
            retenue = canonique
    return retenue


def serie_effective(declaree: str | None, curriculum_context: dict) -> str | None:
    """Série qui doit s'appliquer au tour, entre déclaration et profil.

    La déclaration de l'élève l'emporte sur le profil du compte : c'est la
    règle n°5, et c'est le sens du cas #8 — un profil erroné ne doit pas
    survivre à la correction de l'élève. À défaut de déclaration, le profil
    s'applique tel quel ; à défaut des deux, il n'y a pas de série, et aucune
    n'est inventée.
    """
    if declaree is not None:
        return declaree
    valeur = curriculum_context.get("serie")
    return str(valeur) if valeur else None
