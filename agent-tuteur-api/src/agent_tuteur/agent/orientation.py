"""Réponses d'orientation **écrites par le code** — le catalogue des chapitres.

Pourquoi pas le modèle. Le cas QA #26 rapporte des réponses « de qualité
variable » à une même question posée trois fois : « liste-moi les chapitres du
cours de maths ». Deux causes s'y superposaient — un mauvais routage (la phrase
tombait en mode *cours* à cause du mot « cours ») et, une fois ce routage
corrigé, la variabilité propre à toute prose échantillonnée.

La doctrine appliquée ici est celle de la décision D5 : quand l'exigence porte
sur **ce qui doit être dit** plutôt que sur la manière, on sort le texte de la
génération. Un inventaire de chapitres n'a aucune raison d'être reformulé à
chaque fois : il doit être exact, complet, et identique d'un tour à l'autre.

Effet de bord recherché : les règles n°3 et n°4 deviennent structurelles sur ce
tour. Le texte ne peut pas inventer un chapitre absent du store, ni taire un
chapitre présent, ni prétendre connaître le programme scolaire de l'élève.
"""

from __future__ import annotations

#: Ouverture commune : ce que l'agent ne sait PAS vient d'abord, parce que c'est
#: la question posée (« mon programme ») et que l'y confondre avec sa
#: couverture serait précisément l'hallucination de contexte élève (règle n°3).
_PREAMBULE = (
    "Je ne connais pas le programme officiel de ton établissement — je ne peux "
    "te parler que des leçons dont je dispose."
)

_SANS_CHAPITRE = (
    f"{_PREAMBULE}\n\n"
    "Et pour l'instant, je n'ai aucune leçon indexée pour ce cadre : je ne peux "
    "donc te proposer aucun chapitre. Signale-le à ton enseignant ou à "
    "l'administrateur de la plateforme, c'est à eux d'ajouter les leçons."
)

_RELANCE = (
    "Sur lequel veux-tu travailler ? Je peux t'en faire le cours section par "
    "section, te donner un exercice à chercher, ou t'interroger dessus."
)


def reponse_catalogue(chapitres: list[str]) -> str:
    """Inventaire des chapitres disponibles, mot pour mot identique à chaque appel.

    ``chapitres`` vient du store vectoriel (``HybridRetriever.catalogue``), déjà
    filtré par le cadre curriculaire : la liste rendue est donc celle que la
    recherche saura réellement servir ensuite. Proposer ici ce qui serait refusé
    au tour suivant recréerait le décalage du cas #28.
    """
    if not chapitres:
        return _SANS_CHAPITRE

    nombre = len(chapitres)
    entete = (
        f"{_PREAMBULE} En voici {nombre} pour l'instant :"
        if nombre > 1
        else f"{_PREAMBULE} J'en ai une pour l'instant :"
    )
    lignes = "\n".join(f"- {chapitre}" for chapitre in chapitres)
    return f"{entete}\n\n{lignes}\n\n{_RELANCE}"
