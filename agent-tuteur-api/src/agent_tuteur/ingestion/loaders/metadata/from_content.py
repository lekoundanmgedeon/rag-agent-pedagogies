"""Métadonnées déduites du contenu du document.

Porté de ``backend/app/rag/metadata_extractor/content_metadata.py`` (NURU).

Seul le **début** du document est analysé : c'est là que les enseignants
placent l'en-tête (classe, chapitre, année, professeur). Aller plus loin
multiplierait les faux positifs — un « Chapitre » cité au milieu d'un exercice
n'est pas le chapitre du document.

Ces métadonnées ne servent qu'à **compléter** celles du nom de fichier : une
valeur déjà connue n'est jamais écrasée (le nom de fichier est plus fiable que
l'en-tête, souvent recopié d'un document à l'autre).
"""

from __future__ import annotations

from agent_tuteur.ingestion.loaders.metadata import patterns

#: Nombre de lignes d'en-tête analysées.
LIGNES_ENTETE = 50

#: Nombre maximal de compétences retenues (au-delà, c'est du bruit).
MAX_COMPETENCES = 5


def extraire(texte: str, deja_connu: dict[str, str] | None = None) -> dict[str, str]:
    """Complète ``deja_connu`` avec ce que dit l'en-tête du document."""
    connu = deja_connu or {}
    trouve: dict[str, str] = {}
    entete = "\n".join(texte.split("\n")[:LIGNES_ENTETE])

    def absent(champ: str) -> bool:
        return champ not in connu and champ not in trouve

    if absent("titre") and (m := patterns.TITRE.search(entete)) is not None:
        trouve["titre"] = m.group(1).strip()

    if absent("chapitre") and (m := patterns.CHAPITRE_CONTENU.search(entete)) is not None:
        trouve["chapitre"] = m.group(2).strip()
        if absent("chapitre_numero"):
            trouve["chapitre_numero"] = m.group(1)

    if absent("classe") and (m := patterns.CLASSE_CONTENU.search(entete)) is not None:
        trouve["classe"] = m.group(1).strip()
        if m.group(2) and absent("serie"):
            trouve["serie"] = m.group(2).strip()

    if absent("annee_scolaire") and (m := patterns.ANNEE_CONTENU.search(entete)) is not None:
        trouve["annee_scolaire"] = m.group(2)

    if absent("auteur") and (m := patterns.AUTEUR_CONTENU.search(entete)) is not None:
        trouve["auteur"] = m.group(2).strip()

    if absent("chapitre_numero") and (m := patterns.CHAPITRE_NUMERO_CONTENU.search(entete)) is not None:
        trouve["chapitre_numero"] = m.group(2)

    # Les compétences sont cherchées dans tout le document : elles apparaissent
    # souvent en tête de chaque partie, pas seulement en première page.
    competences = [m[-1].strip() for m in patterns.COMPETENCE_CONTENU.findall(texte)]
    if competences:
        trouve["competences"] = competences[:MAX_COMPETENCES]

    return trouve
