"""Fusion des sources de métadonnées et alignement sur la taxonomie du projet.

Porté de ``backend/app/rag/metadata_extractor/metadata_merge.py`` (NURU).

Trois sources, de la moins fiable à la plus fiable :

1. les **valeurs par défaut** fournies par l'appelant (ex. « tout ce lot est du
   Terminale S1 ») ;
2. le **chemin et le nom du fichier** ;
3. le **contenu** du document — qui ne fait que combler les trous ;

puis, par-dessus tout, les métadonnées saisies **à la main** au téléversement,
qui font toujours foi.

## Deux écarts assumés par rapport à NURU

**Aucune classe ni série n'est inventée.** NURU forçait ``classe="Terminale"``
et ``serie="S1"`` quand l'information manquait. C'était sans conséquence chez
eux (leur corpus est entièrement du Terminale S1), mais dangereux ici : ces
deux champs servent à *filtrer* ce qu'un élève voit. Un document mal étiqueté
« Terminale S1 » remonterait dans les réponses faites à un élève de Seconde,
silencieusement. On préfère un champ vide — qui n'exclut rien — à une valeur
fausse. L'appelant peut toujours passer ces valeurs via ``defauts`` quand il
sait de quoi le lot est fait.

**Pas de champ inventé non plus** : NURU ajoutait ``pays``, ``langue`` et un
``document_id`` calculé par empreinte du chemin. Le premier et le deuxième sont
constants dans tout le projet, le troisième fait doublon avec l'identifiant de
document déjà géré en base.

## Ce que devient le résultat

Le dictionnaire renvoyé contient **plus** que la taxonomie : la nature du
document (``type_document``), l'auteur, l'établissement, l'année… Seuls les
champs déclarés par ``CurriculumMetadata`` sont recopiés sur les chunks —
l'annotation s'en charge, et c'est ce modèle qui reste la source de vérité. Le
reste sert aux journaux d'ingestion et sera exploité par le re-ranker
pédagogique (module 2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_tuteur.config.taxonomy import Niveau, canonical_serie
from agent_tuteur.ingestion.loaders.metadata import from_content, from_filename, patterns

#: Discipline retenue quand rien ne permet de la déduire. Le corpus est
#: aujourd'hui exclusivement mathématique ; ce défaut est explicite et se
#: change ici, à un seul endroit.
DISCIPLINE_PAR_DEFAUT = "mathématiques"

#: Classes du secondaire — sert à déduire le ``niveau``, qui est le seul champ
#: obligatoire de la taxonomie.
_CLASSES_SECONDAIRE = frozenset({"Terminale", "Première", "Seconde"})

def _canoniser_classe(valeur: str) -> str:
    """« TLE », « tle », « Terminale » -> « Terminale »."""
    return patterns.CLASSES_CANONIQUES.get(valeur.strip().lower(), valeur.strip())


def _canoniser_serie(valeur: str) -> str:
    """« TS1 » -> « S1 ». Une série inconnue est conservée telle quelle.

    La correspondance vit dans la taxonomie (``SERIE_EQUIVALENCES``), pas ici :
    c'est elle la source de vérité des séries, et c'est elle qui alimente aussi
    ``serie_alias[]`` pour qu'une question mentionnant « TS1 » retrouve un
    document annoté « S1 ».
    """
    return canonical_serie(valeur) or valeur.strip()


def _deduire_niveau(classe: str | None) -> str | None:
    """Niveau du système éducatif correspondant à une classe, si déductible.

    Renvoie ``None`` quand la classe est inconnue : l'annotation applique alors
    son propre défaut. On ne devine pas un niveau à partir de rien, pour la même
    raison qu'on ne devine pas une classe (cf. docstring du module).
    """
    if classe in _CLASSES_SECONDAIRE:
        return Niveau.SECONDAIRE.value
    return None


def extraire_metadonnees(
    chemin: Path,
    contenu: str,
    *,
    defauts: dict[str, Any] | None = None,
    saisies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Métadonnées complètes d'un document, prêtes pour l'annotation.

    :param chemin: emplacement du fichier (le dossier parent est un indice).
    :param contenu: texte déjà extrait et nettoyé.
    :param defauts: valeurs de repli connues de l'appelant (ex. lot homogène).
    :param saisies: valeurs saisies à la main au téléversement — prioritaires.
    """
    fusion: dict[str, Any] = dict(defauts or {})
    fusion.update(from_filename.extraire(chemin))
    fusion.update(from_content.extraire(contenu, fusion))
    fusion.update({k: v for k, v in (saisies or {}).items() if v not in (None, "")})

    # --- Alignement sur la taxonomie -----------------------------------------
    if classe := fusion.get("classe"):
        fusion["classe"] = _canoniser_classe(str(classe))
    if serie := fusion.get("serie"):
        fusion["serie"] = _canoniser_serie(str(serie))
    fusion.setdefault("discipline", DISCIPLINE_PAR_DEFAUT)
    if not fusion.get("niveau") and (niveau := _deduire_niveau(fusion.get("classe"))):
        fusion["niveau"] = niveau

    # Note : « competences » n'alimente **pas** le champ « competence » de la
    # taxonomie. Ce que le document appelle « Compétences » est une liste de
    # verbes d'action (« Calculer, Déterminer, Résoudre »), alors que le champ
    # « competence » du projet désigne une compétence du programme, servant au
    # filtrage. Les confondre dégraderait la recherche. La liste est conservée
    # en provenance, en attendant l'arbitrage noté dans JOURNAL_FUSION.md.
    return fusion
