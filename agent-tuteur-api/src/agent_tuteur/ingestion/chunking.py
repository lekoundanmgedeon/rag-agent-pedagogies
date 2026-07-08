"""Chunking par **structure pédagogique** — jamais par taille fixe.

Un chunk = une compétence complète, un chapitre, ou un exercice **entier**.
L'exercice (énoncé + indice + solution) est **indivisible** : la récupération
pré-réponse doit remonter le trio complet.

Marqueurs de convention (format pivot) :
* ``## `` → chapitre ou compétence (selon l'intitulé) ;
* ``### Exercice`` → exercice indivisible.

Un PDF brut peut n'avoir aucun marqueur : on retombe alors sur une heuristique
conservatrice de détection de titres numérotés.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_tuteur.config.taxonomy import TypeChunk

_HEADING = re.compile(r"^(#{2,3})\s+(.*\S)\s*$", re.MULTILINE)
_EXERCICE = re.compile(r"^exercice\b", re.IGNORECASE)
_COMPETENCE = re.compile(r"^comp[ée]tence\b", re.IGNORECASE)
_CHAPITRE = re.compile(r"^chapitre\b", re.IGNORECASE)

# Heuristique PDF : lignes ressemblant à des titres (numérotation / mots-clés).
_HEURISTIC_TITLE = re.compile(
    r"^\s*(?:"
    r"(?:chapitre|le[çc]on|partie|exercice|activit[ée])\s+[\dIVXLC]+"  # « Chapitre 3 »
    r"|[IVXLC]{1,4}[\.\)]\s+\S"                                        # « II. »
    r"|\d{1,2}[\.\)]\s+\S"                                             # « 3) »
    r")",
    re.IGNORECASE,
)


@dataclass
class ChunkDraft:
    """Brouillon de chunk avant annotation curriculaire."""

    title: str | None
    type_chunk: str
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        body = "\n".join(self.lines).strip()
        if self.title:
            return f"{self.title}\n\n{body}".strip()
        return body

    def is_empty(self) -> bool:
        return not "".join(self.lines).strip()


def _classify_heading(title: str) -> str:
    if _EXERCICE.match(title):
        return TypeChunk.EXERCICE.value
    if _COMPETENCE.match(title):
        return TypeChunk.COMPETENCE_COMPLETE.value
    return TypeChunk.CHAPITRE.value


def _split_markdown(text: str) -> list[ChunkDraft]:
    """Découpe selon les marqueurs ``##`` / ``### Exercice``.

    Un titre de niveau 2 (``##``) démarre toujours un nouveau chunk. Un titre de
    niveau 3 démarre un chunk **seulement** s'il s'agit d'un exercice (pour le
    garder indivisible) ; les autres sous-titres restent dans le chunk parent.
    """
    drafts: list[ChunkDraft] = []
    current: ChunkDraft | None = None

    for line in text.split("\n"):
        m = _HEADING.match(line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            is_exercice = _EXERCICE.match(title) is not None
            if level == 2 or is_exercice:
                if current is not None and not current.is_empty():
                    drafts.append(current)
                current = ChunkDraft(title=title, type_chunk=_classify_heading(title))
                continue
        if current is None:
            current = ChunkDraft(title=None, type_chunk=TypeChunk.CHAPITRE.value)
        current.lines.append(line)

    if current is not None and not current.is_empty():
        drafts.append(current)
    return drafts


def _split_heuristic(text: str) -> list[ChunkDraft]:
    """Repli pour texte sans marqueurs : découpe sur titres numérotés détectés."""
    drafts: list[ChunkDraft] = []
    current: ChunkDraft | None = None

    for line in text.split("\n"):
        if _HEURISTIC_TITLE.match(line) and line.strip():
            if current is not None and not current.is_empty():
                drafts.append(current)
            title = line.strip()
            type_chunk = (
                TypeChunk.EXERCICE.value
                if _EXERCICE.match(title)
                else TypeChunk.SOUS_NOTION.value
            )
            current = ChunkDraft(title=title, type_chunk=type_chunk)
            continue
        if current is None:
            current = ChunkDraft(title=None, type_chunk=TypeChunk.CHAPITRE.value)
        current.lines.append(line)

    if current is not None and not current.is_empty():
        drafts.append(current)
    return drafts


def chunk_document(text: str) -> list[ChunkDraft]:
    """Découpe un document normalisé en chunks structurels.

    Utilise les marqueurs Markdown s'ils existent, sinon l'heuristique de titres.
    En dernier recours (aucun découpage possible), renvoie le document entier.
    """
    if _HEADING.search(text) is not None:
        drafts = _split_markdown(text)
    else:
        drafts = _split_heuristic(text)

    drafts = [d for d in drafts if not d.is_empty()]
    if not drafts and text.strip():
        drafts = [ChunkDraft(title=None, type_chunk=TypeChunk.CHAPITRE.value, lines=text.split("\n"))]
    return drafts
