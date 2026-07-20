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

# Une **leçon** structurée (format pilote `lessons/Lecon_*.md`) se reconnaît à son
# titre de niveau 1 (`# Titre`) — le corpus d'exemple, lui, commence directement
# par des `## Chapitre : …` / `## Compétence : …`. En mode leçon, les 18 sections
# en `##` sont des *sous-notions* d'un même chapitre (porté par le frontmatter),
# et non des chapitres distincts — sinon `chapitre` se pollue avec des titres de
# section (« 2. Introduction ») et une leçon éclate en 18 pseudo-chapitres.
_H1 = re.compile(r"^#\s+\S", re.MULTILINE)

# Sections d'*auteur* d'une leçon (non pédagogiques) — exclues du RAG pour ne pas
# polluer la recherche (« Métadonnées RAG » remontait avec un score maximal).
_LESSON_META_SECTION = re.compile(
    r"^\s*(?:\d+\.\s*)?(?:"
    r"m[ée]tadonn[ée]es(?:\s+rag)?"
    r"|d[ée]coupage\s+pour\s+vectorisation"
    r"|contr[ôo]le\s+qualit[ée]"
    r")",
    re.IGNORECASE,
)

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


def _classify_heading(title: str, *, lesson: bool = False) -> str:
    if _EXERCICE.match(title):
        return TypeChunk.EXERCICE.value
    if _COMPETENCE.match(title):
        return TypeChunk.COMPETENCE_COMPLETE.value
    # En mode leçon, une section `##` est une sous-notion du chapitre (frontmatter),
    # pas un chapitre à part entière.
    return TypeChunk.SOUS_NOTION.value if lesson else TypeChunk.CHAPITRE.value


def _split_markdown(text: str, *, lesson: bool = False) -> list[ChunkDraft]:
    """Découpe selon les marqueurs ``##`` / ``### Exercice``.

    Un titre de niveau 2 (``##``) démarre toujours un nouveau chunk. Un titre de
    niveau 3 démarre un chunk **seulement** s'il s'agit d'un exercice (pour le
    garder indivisible) ; les autres sous-titres restent dans le chunk parent.

    En mode ``lesson``, les sections ``##`` deviennent des *sous-notions* et les
    sections d'auteur (Métadonnées RAG, Découpage vectorisation, Contrôle
    qualité) sont ignorées (leur contenu est absorbé dans un brouillon marqué
    ``_skip`` puis retiré).
    """
    drafts: list[ChunkDraft] = []
    current: ChunkDraft | None = None
    skipping = False

    for line in text.split("\n"):
        m = _HEADING.match(line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            is_exercice = _EXERCICE.match(title) is not None
            if level == 2 or is_exercice:
                if current is not None and not current.is_empty() and not skipping:
                    drafts.append(current)
                skipping = lesson and _LESSON_META_SECTION.match(title) is not None
                if skipping:
                    current = None
                    continue
                current = ChunkDraft(title=title, type_chunk=_classify_heading(title, lesson=lesson))
                continue
        if skipping:
            continue
        if current is None:
            current = ChunkDraft(title=None, type_chunk=TypeChunk.CHAPITRE.value)
        current.lines.append(line)

    if current is not None and not current.is_empty() and not skipping:
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
    Le format **leçon** (présence d'un titre `# `) est détecté automatiquement
    et découpé en sous-notions (cf. ``_split_markdown``).
    """
    if _HEADING.search(text) is not None:
        drafts = _split_markdown(text, lesson=_H1.search(text) is not None)
    else:
        drafts = _split_heuristic(text)

    drafts = [d for d in drafts if not d.is_empty()]
    if not drafts and text.strip():
        drafts = [ChunkDraft(title=None, type_chunk=TypeChunk.CHAPITRE.value, lines=text.split("\n"))]
    return drafts
