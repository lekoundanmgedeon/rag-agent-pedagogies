"""Mémoire de la conversation en cours — ce que l'agent sait déjà de cet échange.

**Le problème mesuré.** Le prompt ne portait qu'une fenêtre glissante de six
messages (trois échanges). Tout ce qui précédait disparaissait sans laisser de
trace : l'élève qui donnait son prénom au premier tour ne le retrouvait plus au
cinquième, l'exercice servi trois tours plus tôt n'existait plus, et le chapitre
travaillé depuis le début n'était connu que tant qu'il restait dans la fenêtre.
Ce n'était pas un défaut de modèle : rien de tout cela ne lui était transmis.

**Ce que ce module ajoute, et ce qu'il refuse d'ajouter.** Il construit une
mémoire *déterministe*, écrite par le code à partir de la conversation elle-même
— les messages persistés et les traces des tours précédents. Aucun appel de
modèle, donc aucun résumé échantillonné : la même conversation produit toujours
la même mémoire, et rien ne peut s'y inventer.

La règle non-négociable n°3 gouverne tout le module : **on ne retient que ce qui
a été dit ou fait dans CETTE conversation**. Le prénom vient d'une phrase de
l'élève, les chapitres viennent des traces de tours réellement joués, l'exercice
vient d'un énoncé réellement servi. Rien n'est déduit, rien n'est supposé.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: L'élève se présente. Motifs volontairement étroits : un prénom mal capté est
#: pire que pas de prénom du tout — l'agent s'adresserait à l'élève par un mot
#: qui n'est pas son nom, ce qui est une forme d'hallucination de contexte.
_PRESENTATION = re.compile(
    r"\b(?:je\s+m['’]appelle|moi\s+c['’]est|je\s+me\s+nomme|mon\s+(?:pr[ée]nom|nom)\s+"
    r"(?:c['’]est|est))\s+(?P<nom>[^\W\d_][^\W\d_'’-]{1,29})",
    re.IGNORECASE,
)

#: Mots qui suivent parfois « moi c'est » sans être un prénom.
_FAUX_PRENOMS = frozenset(
    {"pareil", "bon", "bien", "ok", "oui", "non", "moi", "ça", "ca", "vrai", "faux", "compliqué"}
)

#: Nombre de messages (élève + tuteur confondus) réinjectés *intégralement*.
#: Douze au lieu de six : six ne couvrait que trois échanges, et un élève qui
#: travaille un exercice en dépasse trois avant d'avoir posé sa vraie question.
#: Le coût est borné par la troncature par message ci-dessous, pas par le nombre.
MAX_MESSAGES_RECENTS = 12

#: Longueur maximale d'un message réinjecté. Une section de cours fait plusieurs
#: milliers de caractères : sans cette borne, élargir la fenêtre aurait gonflé le
#: prompt sans rien apporter — l'essentiel d'un tour tient dans son début.
MAX_CARACTERES_PAR_MESSAGE = 500


@dataclass
class MemoireSession:
    """Ce que l'agent a appris depuis le début de la conversation."""

    #: Prénom donné par l'élève lui-même, ou ``None``.
    prenom: str | None = None
    #: Chapitres réellement travaillés, dans l'ordre d'apparition.
    chapitres: list[str] = field(default_factory=list)
    #: Dernier énoncé d'exercice servi à l'élève (texte du tour).
    dernier_exercice: str | None = None
    #: Dernière réponse du tuteur, quel qu'en soit le type. Sert aux demandes de
    #: reformatage, où c'est la matière à reprendre (cas QA #34).
    derniere_reponse: str | None = None
    #: Nombre de tours déjà échangés (paires élève/tuteur).
    tours: int = 0

    @property
    def est_vide(self) -> bool:
        return not (self.prenom or self.chapitres or self.dernier_exercice or self.tours)


def _prenom_declare(texte: str) -> str | None:
    correspondance = _PRESENTATION.search(texte)
    if correspondance is None:
        return None
    nom = correspondance.group("nom").strip("'’-")
    if not nom or nom.lower() in _FAUX_PRENOMS:
        return None
    return nom[:1].upper() + nom[1:]


def _chapitre_du_tour(trace: dict) -> str | None:
    """Chapitre effectivement travaillé pendant un tour, lu dans sa trace.

    On lit la décision du pipeline (cours ouvert, entraînement servi) plutôt que
    les sources remontées : un extrait peut être remonté sans être le sujet du
    tour, alors qu'un chapitre confirmé, lui, a bien été enseigné.
    """
    cours = trace.get("course")
    if isinstance(cours, dict) and cours.get("chapitre") and cours.get("chapitre_confirmed"):
        return cours["chapitre"]
    entrainement = trace.get("entrainement")
    if (
        isinstance(entrainement, dict)
        and entrainement.get("chapitre")
        and entrainement.get("chapitre_confirmed")
    ):
        return entrainement["chapitre"]
    return None


def construire(historique: list[dict] | None) -> MemoireSession:
    """Mémoire de session à partir des messages persistés de la conversation.

    ``historique`` est la liste que l'appelant charge déjà pour le prompt :
    ``{"role", "content"}``, plus ``"trace"`` pour les messages du tuteur quand
    elle est disponible (cf. ``api/routes/chat.py``). L'absence de trace n'est
    pas une erreur — la mémoire est simplement moins fine.
    """
    memoire = MemoireSession()
    if not historique:
        return memoire

    for message in historique:
        role, contenu = message.get("role"), message.get("content") or ""
        if role == "user":
            if memoire.prenom is None and (nom := _prenom_declare(contenu)):
                memoire.prenom = nom
            continue
        if role != "assistant":
            continue

        memoire.tours += 1
        memoire.derniere_reponse = contenu
        trace = message.get("trace") or {}
        if not isinstance(trace, dict):
            continue
        if (chapitre := _chapitre_du_tour(trace)) and chapitre not in memoire.chapitres:
            memoire.chapitres.append(chapitre)
        if trace.get("hint_label") == "Exercice proposé":
            memoire.dernier_exercice = contenu

    return memoire
