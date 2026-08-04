"""Règles de la maîtrise progressive (« mastery learning »).

Porté de ``backend/app/memory/student_profile.py`` (NURU). Ce module est du
**calcul pur** : aucune base de données, aucun framework. C'est ce qui permet de
le tester sans rien démarrer, et de le réutiliser aussi bien depuis les
repositories que depuis le graphe de l'agent.

## L'idée

On ne compte pas les exercices faits : on suit, pour chaque compétence, un
**niveau de maîtrise** entre 0.0 et 1.0. Il monte quand l'élève réussit,
descend quand il échoue, et — c'est le point important — **les résultats
récents pèsent plus que les anciens**. Un élève qui a raté ses cinq premiers
essais puis réussi les cinq suivants est en train de progresser : sa maîtrise
doit le refléter, pas rester bloquée à la moyenne.

## Ce que cela implique

Le score dépend de l'**ordre** des tentatives, donc il ne peut pas être
recalculé à partir des seuls compteurs `attempts`/`successes`. Il reste
néanmoins reconstituable : chaque tentative est archivée dans
``exercise_results``, et rejouer cet historique redonne exactement le même
score. C'est pour cela que les deux tables coexistent.
"""

from __future__ import annotations

#: Poids de la nouvelle observation dans la moyenne mobile (valeur de NURU).
#: Plus il est élevé, plus la maîtrise réagit vite — et plus elle est instable.
#: À 0.3, il faut environ trois réussites consécutives pour effacer un échec.
TAUX_APPRENTISSAGE = 0.3

#: Au-dessus de ce score, une tentative est comptée comme une réussite. Un quiz
#: noté 0.6 est donc « réussi », même s'il n'est pas parfait.
SEUIL_REUSSITE = 0.5

#: Seuils d'affichage du niveau de maîtrise.
SEUIL_MAITRISE = 0.8
SEUIL_EN_COURS = 0.5


def score_observe(*, is_correct: bool | None, score: float | None = None) -> float:
    """Ramène un résultat d'exercice à une note entre 0.0 et 1.0.

    Un quiz fournit une note partielle (``score``) ; un exercice fournit
    seulement un vrai/faux. Le premier prime quand les deux sont donnés.
    """
    if score is not None:
        return max(0.0, min(1.0, score))
    return 1.0 if is_correct else 0.0


def maitrise_mise_a_jour(precedente: float | None, observe: float) -> float:
    """Nouveau niveau de maîtrise après une tentative.

    À la première tentative, la maîtrise **est** le résultat observé. Ensuite,
    c'est une moyenne mobile exponentielle : on garde 70 % de l'acquis et on
    intègre 30 % du nouveau résultat.
    """
    if precedente is None:
        return observe
    return (1 - TAUX_APPRENTISSAGE) * precedente + TAUX_APPRENTISSAGE * observe


def est_une_reussite(observe: float) -> bool:
    return observe >= SEUIL_REUSSITE


def statut_maitrise(score: float, attempts: int = 1) -> str:
    """Libellé du niveau atteint, pour l'affichage.

    ``non_commence`` est réservé à une compétence **jamais tentée** : un score
    de 0 après un échec n'est pas la même chose qu'une absence de données, et
    les confondre ferait disparaître un élève en difficulté des statistiques.
    """
    if attempts <= 0:
        return "non_commence"
    if score >= SEUIL_MAITRISE:
        return "maitrise"
    if score >= SEUIL_EN_COURS:
        return "en_cours"
    return "faible"


# --- Badges ------------------------------------------------------------------

#: Catalogue des badges. La clé est l'identifiant stable stocké en base ; le
#: libellé et la description sont l'habillage, modifiables sans migration.
BADGES: dict[str, dict[str, str]] = {
    "premier_pas": {
        "label": "🌱 Premier pas",
        "description": "Premier exercice ou quiz terminé.",
    },
    "dix_exercices": {
        "label": "🔥 Persévérant·e",
        "description": "10 exercices ou quiz terminés.",
    },
    "cinquante_exercices": {
        "label": "🏆 Marathonien·ne",
        "description": "50 exercices ou quiz terminés.",
    },
    "notion_maitrisee": {
        "label": "✅ Notion maîtrisée",
        "description": "Une compétence atteint 80 % de maîtrise.",
    },
    "sans_faute": {
        "label": "🎯 Sans-faute",
        "description": "Score parfait sur un quiz.",
    },
}


def badges_merites(
    *, total_resultats: int, observe: float, maitrise: float | None = None
) -> list[str]:
    """Codes des badges auxquels ce résultat donne droit.

    La fonction ne sait pas lesquels sont **déjà** acquis : c'est au dépôt de
    ne pas les attribuer deux fois. Elle répond seulement à « qu'est-ce que ce
    résultat mérite ? », ce qui la rend testable sans base de données.
    """
    merites: list[str] = []
    if total_resultats >= 1:
        merites.append("premier_pas")
    if total_resultats >= 10:
        merites.append("dix_exercices")
    if total_resultats >= 50:
        merites.append("cinquante_exercices")
    if observe >= 1.0:
        merites.append("sans_faute")
    if maitrise is not None and maitrise >= SEUIL_MAITRISE:
        merites.append("notion_maitrisee")
    return merites
