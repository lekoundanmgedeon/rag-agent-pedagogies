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

**Fonctions exposées (utilisées par ``validation_agent.ValidationAgent``) :**

- ``verifier_coherence_mathematique``  — contrôles vocab + fidélité calcul SymPy
- ``verifier_coherence_etude_fonction`` — cohérence étude SymPy vs réponse du LLM
- ``verifier_coherence_exercice``       — détection heuristique de solution complète non autorisée
- ``verifier_pedagogie``               — juge LLM basique (conservé pour rétrocompatibilité)
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
    texte_norm = texte.replace('×', '*').replace('÷', '/').replace('−', '-')
    texte = texte_norm
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

    # 3. Contrôle du format KaTeX (déterministe)
    if "\\(" in reponse or "\\[" in reponse:
        problemes.append(
            "Format mathématique incorrect : utilisation de \\( ou \\[ au lieu des "
            "délimiteurs KaTeX autorisés ($ et $$)."
        )

    if resultat_calcule:
        attendu = str(resultat_calcule).strip()
        attendu_alt = attendu.replace("*", "")
        # Normalise les opérateurs Unicode dans la chaîne attendue
        attendu_norm = attendu.replace('×', '*').replace('÷', '/').replace('−', '-')
        attendu_norm_alt = attendu_norm.replace("*", "")
        if attendu_norm and attendu_norm not in texte_norm and (attendu_norm_alt and attendu_norm_alt not in texte_norm):
            problemes.append(
                f"Le résultat calculé exactement ({attendu}) n'apparaît pas dans la "
                "réponse : le modèle a probablement refait le calcul lui-même."
            )

    return RapportVerification(problemes=problemes)


# ---------------------------------------------------------------------------
# Nouveau contrôle : cohérence de l'étude de fonction SymPy
# ---------------------------------------------------------------------------

#: Mots-clés heuristiques qui signalent qu'un résultat d'étude de fonction
#: est discuté dans la réponse. Si ces mots sont présents mais que les valeurs
#: calculées sont absentes, il y a probablement incohérence.
_MOTS_ETUDE = (
    "domaine",
    "dérivée",
    "derivee",
    "limite",
    "variation",
    "tableau de signe",
    "tableau de variation",
    "croissant",
    "décroissant",
    "decroissant",
)


def verifier_coherence_etude_fonction(
    reponse: str,
    etude: dict,
) -> RapportVerification:
    """Vérifie que la réponse reprend fidèlement les résultats SymPy de l'étude de fonction.

    Contrôle **déterministe** : on ne fait que chercher si des valeurs calculées
    (dérivée, domaine, limites numériques) apparaissent dans la réponse.

    :param reponse: Texte généré par le LLM.
    :param etude: Dictionnaire produit par ``etude_fonction`` dans le state
                  (clés : ``expression``, ``domaine``, ``derivee``, ``limites``,
                  ``variations``).
    """
    if not etude:
        return RapportVerification()

    problemes: list[str] = []
    texte = _sans_accents(reponse)
    texte_norm = texte.replace('×', '*').replace('÷', '/').replace('−', '-')
    texte = texte_norm
    # Contrôle 1 : la dérivée calculée doit apparaître
    derivee = etude.get("derivee")
    if derivee:
        # Normalise dérivée : accents + opérateurs Unicode → * / -
        d_normalise = _sans_accents(str(derivee)).replace("×", "*").replace("÷", "/").replace("−", "-")
        d_alt = d_normalise.replace("*", "")
        if (d_normalise and d_normalise not in texte) and (d_alt and d_alt not in texte):
            # On vérifie qu'on parle bien de dérivée dans la réponse avant de
            # signaler l'absence — évite les faux positifs sur des réponses
            # qui ne touchent pas à la dérivée.
            if any(mot in texte for mot in ("derivee", "derive", "f'")):
                problemes.append(
                    f"La dérivée calculée ({derivee}) n'apparaît pas dans la réponse. "
                    "Le modèle a peut-être recalculé sa propre valeur."
                )

    # Contrôle 2 : les limites numériques exactes doivent apparaître
    limites: list = etude.get("limites") or []
    for point, valeur in limites:
        val_str = _sans_accents(str(valeur))
        if val_str and val_str not in texte and len(val_str) > 1:
            # Même logique : on ne signale que si la réponse parle de limites
            if "limite" in texte:
                problemes.append(
                    f"La limite en {point} ({valeur}) calculée par SymPy "
                    "n'apparaît pas dans la réponse."
                )
                break  # Un seul signal suffit

    return RapportVerification(problemes=problemes)


# ---------------------------------------------------------------------------
# Nouveau contrôle : heuristique solution complète non autorisée (exercice)
# ---------------------------------------------------------------------------

#: Expressions qui signalent que le tuteur a donné la solution finale
#: d'un exercice au lieu de guider l'élève. Ce sont des marqueurs linguistiques
#: courants dans les corrigés, pas dans les explications socratiques.
_MARQUEURS_SOLUTION = (
    "la solution est",
    "la réponse est",
    "la reponse est",
    "le résultat est",
    "le resultat est",
    "on obtient donc",
    "la valeur de x est",
    "x =",          # court, on le cherche entre espaces ou ponctuation
    "donc x =",
    "d'où x =",
    "la réponse finale",
    "la reponse finale",
    "en conclusion, x",
    "en conclusion la solution",
    "la solution complète",
    "la solution complete",
    "voici la solution",
    "voici la réponse",
    "voici la reponse",
)

#: Nombre minimum de marqueurs détectés pour déclencher l'alerte.
#: Un seul « x = » peut être une reformulation de l'énoncé ; trois signaux
#: ensemble indiquent fortement une solution complète.
_SEUIL_MARQUEURS_SOLUTION = 2


def verifier_coherence_exercice(reponse: str) -> RapportVerification:
    """Détecte heuristiquement si le tuteur a donné la solution complète.

    Ce contrôle est **intentionnellement souple** : il ne lève une erreur que
    si au moins ``_SEUIL_MARQUEURS_SOLUTION`` marqueurs de solution sont
    présents dans la réponse. Cela évite les faux positifs sur des reformulations
    bénignes. Le juge LLM (couche 2 du ``ValidationAgent``) est plus précis
    sur ce critère — ce contrôle déterministe sert de filet de sécurité rapide.

    :param reponse: Texte généré par le LLM (mode exercice uniquement).
    """
    texte = _sans_accents(reponse)
    detectes = sum(1 for m in _MARQUEURS_SOLUTION if m in texte)
    if detectes >= _SEUIL_MARQUEURS_SOLUTION:
        return RapportVerification(problemes=[
            f"La réponse contient {detectes} marqueur(s) de solution complète "
            "(ex. « la solution est », « on obtient donc »). En mode exercice, "
            "le tuteur doit guider sans révéler la réponse finale."
        ])
    return RapportVerification()


import json
from agent_tuteur.agent.llm.base import BaseLLM

JUDGE_PROMPT = """Tu es un expert pédagogique supervisant un tuteur IA.
Ta mission est de vérifier que la réponse du tuteur respecte les consignes pédagogiques.
Question de l'élève : {question}
Réponse du tuteur : {answer}
Intention détectée : {intent}
Niveau d'indice autorisé (0 à 4) : {hint_level} (0 = juste reformuler, 4 = donner la réponse)

Règles :
1. Si l'intention est "exercice" et que le niveau d'indice est strictement inférieur à 4, le tuteur NE DOIT PAS donner la réponse directe ou la solution complète de l'exercice. Il doit guider.
2. Si le tuteur donne la réponse alors qu'il n'y est pas autorisé, c'est une erreur grave.
3. Le ton doit rester bienveillant et approprié.

Analyse la réponse du tuteur. Renvoie UNIQUEMENT un objet JSON valide avec ce format exact (sans blocs markdown) :
{{
    "valide": true/false,
    "raison": "explication courte de l'erreur si false, sinon vide"
}}
"""

async def verifier_pedagogie(
    llm: BaseLLM,
    question: str,
    answer: str,
    intent: str,
    hint_level: int
) -> RapportVerification:
    """Évaluation de la pédagogie par un LLM-as-a-judge.
    
    Intercepte les cas où le modèle donne la réponse au lieu de faire réfléchir,
    ce que les contrôles déterministes ne peuvent pas détecter.
    """
    if intent not in ("exercice", "cours"):
        return RapportVerification() # On ne juge pas les salutations ou les quiz
        
    prompt = JUDGE_PROMPT.format(
        question=question,
        answer=answer,
        intent=intent,
        hint_level=hint_level
    )
    
    try:
        raw = await llm.generate(prompt)
        if raw.startswith("```json"):
            raw = raw.strip()[7:-3]
        elif raw.startswith("```"):
            raw = raw.strip()[3:-3]
            
        data = json.loads(raw.strip())
        if not data.get("valide", True):
            raison = data.get("raison", "Le juge LLM a détecté une erreur pédagogique.")
            return RapportVerification(problemes=[f"Erreur pédagogique : {raison}"])
            
    except Exception as e:
        # En cas d'échec du parsing ou du LLM, on laisse passer le tour pour ne pas bloquer.
        pass
        
    return RapportVerification()
