"""Chargement du backlog QA — ``qa/qa_cases_*.json`` est la source de vérité.

Ces fichiers sont **en lecture seule** pour la suite de tests : ils portent le
``prompt`` exact envoyé par le testeur, qui est la fixture à rejouer telle
quelle (cf. CLAUDE.md, « ne pas paraphraser »). Les *attentes* associées à
chaque cas vivent à côté, dans :mod:`attentes`, parce qu'une assertion est du
code, pas de la donnée.

Le répertoire ``qa/`` est à la racine du dépôt, hors du paquet Python : il est
partagé avec le reste du chantier (suivi de statut, tri du backlog).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

#: tests/qa/cas.py -> tests/qa -> tests -> agent-tuteur-api -> racine du dépôt.
RACINE_DEPOT = Path(__file__).resolve().parents[3]
DOSSIER_QA = RACINE_DEPOT / "qa"

#: Corpus **figé** reproduisant l'index de la démo contre laquelle les testeurs
#: ont travaillé : deux chapitres seulement (Nombres Complexes, Calcul Intégral).
#: C'est une copie et non un lien vers ``lessons/`` : quand le corpus pédagogique
#: s'enrichira, les fixtures QA doivent continuer à décrire l'index réellement
#: testé, sinon des tests se mettraient à changer de verdict sans qu'une ligne de
#: code ait bougé.
CORPUS_QA = Path(__file__).resolve().parent / "corpus_qa"


@dataclass(frozen=True)
class CasQA:
    """Un retour de testeur, tel qu'il figure dans le backlog."""

    id: int
    prompt: str
    category: str
    subtheme: str
    tester: str
    #: Renseigné pour les cas à corriger (``qa_cases_all`` / ``_critical``).
    priority: str | None = None
    observed_issue: str | None = None
    recommended_action: str | None = None
    #: Renseigné pour les fixtures de non-régression (``qa_cases_positive``).
    confirmed_behavior: str | None = None

    @property
    def est_securite(self) -> bool:
        """Vrai si le cas relève de la catégorie « Sécurité, bien-être & garde-fous ».

        Ces cas exigent une validation humaine explicite avant merge, en plus
        des tests verts (cf. CLAUDE.md, Definition of Done).
        """
        return self.category.startswith("9.")

    @property
    def identifiant_test(self) -> str:
        """Identifiant pytest lisible et traçable : ``qa-07-detresse-eleve...``."""
        ardoise = "".join(c if c.isalnum() else "-" for c in self.subtheme.lower())
        return f"qa-{self.id:02d}-{'-'.join(filter(None, ardoise.split('-')))[:48]}"


def _charger(nom_fichier: str) -> list[CasQA]:
    donnees = json.loads((DOSSIER_QA / nom_fichier).read_text(encoding="utf-8"))
    champs = CasQA.__dataclass_fields__.keys()
    return [CasQA(**{k: v for k, v in cas.items() if k in champs}) for cas in donnees]


def cas_critiques() -> list[CasQA]:
    return _charger("qa_cases_critical.json")


def cas_positifs() -> list[CasQA]:
    return _charger("qa_cases_positive.json")


def tous_les_cas() -> list[CasQA]:
    return _charger("qa_cases_all.json")


def cas_par_priorite(priorite: str) -> list[CasQA]:
    """Sous-ensemble du backlog pour un sprint (cf. CLAUDE.md, « Ordre de traitement »).

    Le filtre porte sur le JSON et non sur une liste d'``id`` recopiée dans les
    tests : un cas ajouté ou repriorisé dans le backlog entre donc dans le rejeu
    du sprint correspondant sans qu'on ait à y penser.
    """
    return [cas for cas in tous_les_cas() if cas.priority == priorite]


def cas_hauts() -> list[CasQA]:
    return cas_par_priorite("Haute")


def par_id(cas: list[CasQA]) -> dict[int, CasQA]:
    return {c.id: c for c in cas}
