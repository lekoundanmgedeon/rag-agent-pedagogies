"""Motifs de reconnaissance des métadonnées dans les documents du corpus.

Porté de ``backend/app/rag/metadata_extractor/config.py`` (NURU). Ces
expressions régulières ont été mises au point sur les 103 PDF réels du
programme sénégalais : elles encodent la façon dont les enseignants nomment
leurs fichiers et rédigent leurs en-têtes. C'est un savoir empirique, coûteux à
reconstituer — d'où le portage à l'identique plutôt qu'une réécriture.

> **Expression régulière (« regex »)** : petit langage qui décrit une forme de
> texte à rechercher. Ici, par exemple, « le mot *Chapitre* suivi d'un numéro ».

Les motifs restent en constantes de module (et non en champs d'une classe de
configuration comme chez NURU) : ils sont figés, partagés, et personne n'a
besoin d'en instancier une variante.
"""

from __future__ import annotations

import re

# --- Motifs appliqués au NOM DE FICHIER --------------------------------------

#: « Chapitre 3 : Les suites » ou « Chap_3-Suites ». La partie ``(?!itre)``
#: empêche « Chap » de se déclencher au milieu du mot « Chapitre ».
CHAPITRE_FICHIER = re.compile(
    r"(?:Chapitre|Chap(?!itre))\.?[\s_]*([0-9]+|[IVXLCDM]+)[\s_]*[:.\-]?[\s_]*(.*?)(?:\s*\(|$|\.pdf|\.docx)",
    re.IGNORECASE,
)

#: Séries sénégalaises. ``TS1`` = « Terminale S1 », très courant dans les noms
#: de fichiers. Les gardes ``(?<![A-Za-z])`` / ``(?![A-Za-z])`` évitent de
#: reconnaître une série à l'intérieur d'un autre mot : sans elles, le « D1 »
#: de « TD1 » serait pris pour la série D1.
SERIE = re.compile(
    r"(?<![A-Za-z])(TS1|TS2|TS|S1|S2|S3|S4|S5|L1|L2|A1|A2|C1|C2|D1|D2|G1|G2)(?![A-Za-z])",
    re.IGNORECASE,
)

TYPE_DOCUMENT = re.compile(
    r"(cours|exercices?|td|tp|ds|devoir|composition|annales|problème|corrigé|sujet)",
    re.IGNORECASE,
)

ANNEE = re.compile(r"(19|20)\d{2}")

AUTEUR_FICHIER = re.compile(
    r"(?:par|de|Mr|Mme|M\.|Professeur)\s+([A-Z][a-zÀ-ÿ]+\s+[A-Z][a-zÀ-ÿ]+)",
    re.IGNORECASE,
)

ETABLISSEMENT = re.compile(
    r"(Lycée|Collège|École|Groupe Scolaire|IA)\s+([A-Za-zÀ-ÿ\s]+)",
    re.IGNORECASE,
)

# --- Motifs appliqués au CONTENU du document ---------------------------------

TITRE = re.compile(r"^#\s*(.+)$", re.MULTILINE)

#: Groupe 1 = numéro, groupe 2 = titre. Le séparateur ``:``/``.``/``-`` est
#: consommé pour qu'il ne se retrouve pas collé au titre.
CHAPITRE_CONTENU = re.compile(
    r"^#\s*(?:Chapitre|CHAPITRE)\s*([IVXLCDM\d]+)\.?\s*[:.\-]?\s*(.+)$", re.MULTILINE
)

#: « Classe de » est un préfixe optionnel non capturant : le groupe 1 est la
#: classe (« Terminale »), le groupe 2 la série (« S1 »).
CLASSE_CONTENU = re.compile(
    r"(?:Classe de\s+)?(Terminale|Tle|Première|1ère|Seconde|2nde)\s+([A-Z]\d?)", re.MULTILINE
)

ANNEE_CONTENU = re.compile(r"(Année scolaire|Année)\s*[:.]?\s*(\d{4}-\d{4})", re.MULTILINE)

#: Le nom de famille peut être entièrement en majuscules (« M. DJITTE »).
AUTEUR_CONTENU = re.compile(
    r"(Professeur|Prof|Enseignant|Auteur)\s*[:.]?\s*"
    r"((?:M\.|Mme|Mr\.?)?\s*[A-ZÀ-Ÿ][a-zà-ÿ]*\s+[A-Za-zÀ-ÿ]+)",
    re.MULTILINE,
)

CHAPITRE_NUMERO_CONTENU = re.compile(r"(Chapitre|CHAPITRE)\s*[:.]?\s*([IVXLCDM\d]+)", re.MULTILINE)

COMPETENCE_CONTENU = re.compile(
    r"(Compétences?|Capacités?)\s*[:.]?\s*\**\s*(.+?)\**\s*(?:\n|$)", re.MULTILINE
)

# --- Vocabulaire du corpus ----------------------------------------------------

#: Notions du programme reconnues dans un nom de fichier quand celui-ci ne
#: contient pas de « Chapitre N » explicite (cas fréquent : « TD1-Probabilite-TS1.pdf »).
#: L'ordre compte : les motifs les plus spécifiques sont testés en premier.
NOTIONS: tuple[tuple[str, str], ...] = (
    (r"probabilit", "Probabilités"),
    (r"deriv", "Dérivation"),
    (r"integr|primitiv", "Intégration"),
    (r"limite", "Limites"),
    (r"suite", "Suites numériques"),
    (r"complexe", "Nombres complexes"),
    (r"exponentiel", "Fonction exponentielle"),
    (r"logarithm", "Fonction logarithme"),
    (r"geometrie|espace", "Géométrie dans l'espace"),
    (r"statistique", "Statistiques"),
    (r"continuit", "Continuité"),
    (r"equation.*differentiel|differentiel", "Équations différentielles"),
    (r"denombrement|combinatoire", "Dénombrement"),
    (r"matrice", "Matrices"),
    (r"produit.*scalaire", "Produit scalaire"),
)

_NOTIONS_COMPILEES = tuple((re.compile(p), label) for p, label in NOTIONS)

#: Segments de chemin qui décrivent l'organisation des dossiers, pas une notion
#: du programme. Ils ne doivent jamais être pris pour un nom de chapitre.
SEGMENTS_STRUCTURELS = frozenset({
    "cours", "exercices", "td", "tp", "devoir", "composition",
    "raw", "data", "processed", "mathématiques", "maths",
    "physique", "chimie", "svt", "histoire", "géographie",
    "terminale", "tle", "1ère", "première", "2nde", "seconde",
})

#: Segment de chemin -> nature du document.
TYPES_PAR_DOSSIER: frozenset[str] = frozenset({
    "cours", "exercices", "td", "tp", "devoir", "composition",
})

#: Segment de chemin -> discipline.
DISCIPLINES_PAR_DOSSIER: frozenset[str] = frozenset({
    "mathématiques", "maths", "physique", "chimie", "svt", "histoire", "géographie",
})

#: Libellés de classe rencontrés -> forme canonique retenue dans la taxonomie.
CLASSES_CANONIQUES: dict[str, str] = {
    "tle": "Terminale",
    "terminale": "Terminale",
    "1ère": "Première",
    "première": "Première",
    "2nde": "Seconde",
    "seconde": "Seconde",
}


def detecter_notion(texte: str) -> str | None:
    """Reconnaît une notion du programme dans un texte libre.

    Utilisé sur un nom de fichier ou de dossier. Insensible à la casse et aux
    accents les plus courants.
    """
    normalise = texte.lower().replace("é", "e").replace("è", "e").replace("ê", "e")
    for motif, libelle in _NOTIONS_COMPILEES:
        if motif.search(normalise):
            return libelle
    return None
