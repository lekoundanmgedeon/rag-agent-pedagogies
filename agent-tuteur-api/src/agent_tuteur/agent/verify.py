"""Contrôles déterministes sur la réponse générée, avant envoi à l'élève.

Porté de ``VerifierAgent._check_mathematical_consistency`` (NURU). Seuls **deux**
contrôles sont repris, et c'est délibéré : ce sont les seuls qui reposent sur un
fait vérifiable plutôt que sur une intuition.

Ce qui a été écarté du vérificateur de NURU :

- ``_check_coherence`` notait la « cohérence » en comptant les mots « donc »,
  « ainsi », « en effet ». Un texte faux truffé de connecteurs obtenait une
  bonne note, un texte juste et concis une mauvaise ;
- ``_check_hallucinations`` reposait sur des heuristiques du même ordre.

Une mesure qui ne mesure pas ce qu'elle prétend est pire que pas de mesure :
elle donne une confiance injustifiée. Les deux contrôles conservés, eux,
répondent à des questions factuelles — « ce mot est-il présent ? », « ce nombre
est-il présent ? ».

Ce module est du **calcul pur** : aucun appel au modèle de langage, aucune
latence, aucun coût.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

#: Vocabulaire de l'analyse à plusieurs variables — hors programme du secondaire
#: sénégalais. Sa présence dans une explication signale que le modèle a dérivé
#: vers un niveau universitaire.
TERMES_HORS_PROGRAMME: tuple[str, ...] = (
    "derivees partielles",
    "derivee partielle",
    "gradient",
    "f(x,y)",
    "f(x, y)",
    "fonction a deux variables",
    "fonction de deux variables",
)

#: Si la compétence traitée porte elle-même sur plusieurs variables, ce
#: vocabulaire est légitime : le contrôle est alors désactivé.
INDICES_MULTIVARIABLE: tuple[str, ...] = (
    "plusieurs variables",
    "deux variables",
    "gradient",
    "partielle",
)


@dataclass(frozen=True)
class RapportVerification:
    """Résultat des contrôles. ``est_valide`` est vrai s'il n'y a aucun problème."""

    problemes: list[str] = field(default_factory=list)

    @property
    def est_valide(self) -> bool:
        return not self.problemes


def _sans_accents(texte: str) -> str:
    """Compare sur une forme sans accents : « dérivée » ≡ « derivee »."""
    norme = unicodedata.normalize("NFKD", texte.lower())
    return "".join(c for c in norme if not unicodedata.combining(c))


def verifier_coherence_mathematique(
    reponse: str,
    *,
    competence: str | None = None,
    resultat_calcule: str | None = None,
) -> RapportVerification:
    """Deux contrôles factuels sur la réponse générée.

    **1. Niveau du vocabulaire.** Si la réponse parle de dérivées partielles ou
    de gradient alors que la compétence traitée est à une seule variable, le
    modèle est sorti du programme. C'est un signal fiable, pas une intuition.

    **2. Fidélité au calcul.** Quand un calcul exact a été fait par l'outil
    de calcul symbolique, son résultat **doit apparaître tel quel** dans le
    texte. Sinon, c'est que le modèle a refait le calcul de son côté — et il
    se trompe régulièrement. C'est le contrôle le plus utile des deux.

    :param reponse: le texte destiné à l'élève.
    :param competence: la compétence traitée, pour savoir si le vocabulaire
        à plusieurs variables est légitime.
    :param resultat_calcule: le résultat exact produit par l'outil de calcul,
        s'il y en a eu un.
    """
    problemes: list[str] = []
    texte = _sans_accents(reponse)
    competence_normalisee = _sans_accents(competence or "")

    porte_sur_plusieurs_variables = any(
        indice in competence_normalisee for indice in INDICES_MULTIVARIABLE
    )
    if not porte_sur_plusieurs_variables:
        for terme in TERMES_HORS_PROGRAMME:
            if terme in texte:
                problemes.append(
                    f"Vocabulaire hors-programme détecté (« {terme} ») alors que la "
                    f"compétence « {competence or '?'} » ne porte pas sur plusieurs variables."
                )
                break

    if resultat_calcule:
        attendu = str(resultat_calcule).strip()
        if attendu and attendu not in reponse:
            problemes.append(
                f"Le résultat calculé exactement ({attendu}) n'apparaît pas dans la "
                "réponse : le modèle a probablement refait le calcul lui-même."
            )

    return RapportVerification(problemes=problemes)
