"""Annotation curriculaire des chunks.

Fusionne trois sources de métadonnées, par priorité décroissante :
1. l'intitulé du chunk (chapitre / compétence / exercice) ;
2. le *frontmatter* YAML du document (corpus d'exemple) ;
3. les métadonnées du formulaire d'upload (``base_metadata``).

Produit des ``Chunk`` prêts à indexer. ``CurriculumMetadata`` fait foi : aucun
schéma parallèle.
"""

from __future__ import annotations

import re
import unicodedata

import yaml

from agent_tuteur.config.taxonomy import TypeChunk
from agent_tuteur.domain.models import Chunk, CurriculumMetadata
from agent_tuteur.ingestion.chunking import ChunkDraft

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
_TITLE_PREFIX = re.compile(r"^(?:chapitre|comp[ée]tence)\s*:\s*", re.IGNORECASE)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extrait le frontmatter YAML en tête de document -> ``(meta, corps)``."""
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, text[match.end():]


def _slug(text: str, maxlen: int = 60) -> str:
    norm = unicodedata.normalize("NFKD", text)
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    norm = re.sub(r"[^a-zA-Z0-9]+", "-", norm).strip("-").lower()
    return norm[:maxlen] or "chunk"


def _clean_title(title: str) -> str:
    """Retire un préfixe « Chapitre : » / « Compétence : » d'un intitulé."""
    return _TITLE_PREFIX.sub("", title).strip()


def annotate(
    drafts: list[ChunkDraft],
    base_metadata: dict,
    source_document: str,
) -> list[Chunk]:
    """Transforme des brouillons en ``Chunk`` annotés et identifiés.

    Maintient le contexte du dernier chapitre/compétence rencontré pour rattacher
    les exercices à leur cadre pédagogique.
    """
    base = {k: v for k, v in base_metadata.items() if k in CurriculumMetadata.model_fields}
    base.setdefault("source_document", source_document)
    base.setdefault("niveau", base.get("niveau") or "secondaire")

    chunks: list[Chunk] = []
    current_chapitre: str | None = base.get("chapitre")
    current_competence: str | None = base.get("competence")
    slug_base = _slug(source_document)

    for index, draft in enumerate(drafts):
        meta = dict(base)
        meta["type_chunk"] = draft.type_chunk
        title = _clean_title(draft.title) if draft.title else None

        if draft.type_chunk == TypeChunk.COMPETENCE_COMPLETE.value and title:
            current_competence = title
            meta["competence"] = title
        elif draft.type_chunk == TypeChunk.CHAPITRE.value and title:
            current_chapitre = title
            meta["chapitre"] = title
        elif draft.type_chunk in {TypeChunk.EXERCICE.value, TypeChunk.SOUS_NOTION.value}:
            # L'exercice hérite du cadre courant (chapitre/compétence).
            if current_chapitre:
                meta.setdefault("chapitre", current_chapitre)
            if current_competence:
                meta.setdefault("competence", current_competence)
            if title:
                meta["chapitre"] = meta.get("chapitre") or current_chapitre

        chunk = Chunk(
            id=f"{slug_base}::{index:03d}",
            text=draft.text,
            metadata=CurriculumMetadata(**meta),
        )
        chunks.append(chunk)
    return chunks
